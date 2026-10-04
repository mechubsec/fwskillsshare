# Proxmox network invariants for chassis cluster

## Contents

- [Bridge and VLAN design](#bridge-and-vlan-design)
- [MTU: the fabric needs jumbo, the control link does not](#mtu-the-fabric-needs-jumbo-the-control-link-does-not)
- [The anti-spoof trap](#the-anti-spoof-trap)
- [Bridge port flags](#bridge-port-flags)
- [Tap interface state](#tap-interface-state)
- [Netfilter](#netfilter)
- [Offloads](#offloads)
- [Node symmetry](#node-symmetry)

Every value here was measured on a healthy two-node vSRX cluster running as Proxmox VE guests. Where a requirement follows from a mechanism rather than a direct observation, the text says so.

## Bridge and VLAN design

The control link and the fabric link each need their own layer-2 segment, isolated from data segments and from each other.

The proven shape is a single portless, VLAN-aware bridge carrying one VLAN per function:

```
auto vmbr7
iface vmbr7 inet manual
	bridge-ports none
	bridge-stp off
	bridge-fd 0
	bridge-vlan-aware yes
	bridge-vids 2-4094
	mtu 9000
```

Portless because cluster-internal traffic never needs to leave the host. VLAN-aware because one bridge with a VLAN per function is far easier to keep symmetric than a bridge per function.

Allocate one VLAN for control, one for fabric, and one per reth. Verify each ID is unused on the host before committing to it:

```
bridge -j vlan show | python3 -c "
import json,sys,collections
seen=set()
for e in json.load(sys.stdin):
    for v in e.get('vlans',[]):
        if 'PVID' in v.get('flags',[]): seen.add(v['vlan'])
print(sorted(seen))"
```

Guest taps are **access ports** — `PVID Egress Untagged`. The guest sends untagged frames and the bridge applies the tag. There is no VLAN configuration inside Junos for these segments.

## MTU: the fabric needs jumbo, the control link does not

This is the most consequential setting and the one most often applied wrongly in both directions.

Junos provisions the fabric interface to a jumbo MTU on its own, without being asked. Measured on the reference cluster:

| Interface | Junos MTU (layer 2 / inet) | Needs a jumbo segment |
|---|---|---|
| `fab0`, and its member `ge-0/0/3` | 9014 / 9000 | **yes** |
| `em0` (control link) | 1514 / 1500 | no |
| `reth1` (data) | 1514 / 1500 | no |

A Linux bridge at MTU 9000 carries a 9014-byte Ethernet frame. That is an exact match for the fabric interface's layer-2 MTU, which is why 9000 is the correct value rather than merely a large one.

**A wrong fabric MTU does not announce itself.** This was tested directly rather than assumed. On a healthy cluster, the fabric segment was dropped to 1500 and left there:

| Check | Result at fabric MTU 1500 |
|---|---|
| `show chassis cluster status` | both redundancy groups healthy, no failover |
| Control link | Up, heartbeats incrementing, zero errors |
| Fabric link | **Up** |
| Fabric probes | still flowing in both directions |
| All reth interfaces | Up |
| `show system alarms` | nothing new |

Every standard health check passed. Fabric probes are small, so they cross a 1500 segment without trouble.

So the failure mode is **latent, not immediate**. The fabric interface still believes it can send 9014-byte frames while the segment underneath cannot carry them. Nothing in the cluster's own state reflects the mismatch, and it is not exercised until real data-plane traffic has to cross the fabric — Z-mode forwarding, or runtime-object sync of large frames.

What this means in practice:

- **Set the fabric segment to 9000** so the underlay matches what Junos provisions for itself.
- **Do not treat a healthy `show chassis cluster` as evidence the MTU is correct.** It is not. Check the segment directly.
- The behaviour under sustained real traffic across an undersized fabric was not exercised in this test and is not claimed here.
- The **control** segment does not need jumbo, and neither do data reths unless you want jumbo data. Control at 1500 is correct, not a latent bug.

"Set every bridge to 9000" is still the wrong lesson — the asymmetry is real, and a 1500 control segment is genuinely fine. But the corollary matters more: because a wrong fabric MTU is invisible to cluster health, verifying it belongs in the build checklist rather than in troubleshooting.

**Set MTU on the bridge, not on the NIC.** On Proxmox, tap interfaces inherit the MTU from their parent bridge automatically at creation. Setting the bridge to MTU 9000 is sufficient — no per-NIC `mtu=` parameter is required in the guest configuration. The reference build carries no `mtu=` parameter on any guest NIC, yet its taps on the 9000 bridge come up at 9000 and its taps on the 1500 bridge come up at 1500. Verified on the third build: bridge `vmbr6` set to 9000, zero `mtu=` options in `qm config`, and `bridge -d link show dev tapNNNiN` confirmed all taps at mtu 9000.

## The anti-spoof trap

A reth interface does not use the MAC address the hypervisor assigned to its NIC. It uses a Juniper-derived virtual MAC:

```
00:10:db:ff:<cluster-id x 16>:<reth number>
```

For cluster-id 2, `reth1` is `00:10:db:ff:20:01` and `reth2` is `00:10:db:ff:20:02`. Neither resembles the assigned address.

The per-NIC Proxmox firewall installs an ebtables anti-spoof rule pinned to the *assigned* MAC. With it enabled, every frame a reth sends is discarded at the bridge. Nothing is logged. The reth still reports `Up`, because its underlying link genuinely is up.

**This option is enabled by default when a NIC is added through the web UI.** It is the single most common cause of a cluster that forms correctly and passes no traffic.

Confirm it is off on every cluster NIC:

```
qm config VMID | grep -c 'firewall=1'      # expect 0
ls /etc/pve/firewall/VMID.fw               # expect no such file
```

Positive confirmation that the bridge is accepting the virtual MAC:

```
bridge fdb show | grep -i '00:10:db'
```

On a healthy cluster this returns entries on the primary node's taps, for example:

```
00:10:db:ff:20:01 dev tap221i3 vlan 1   master vmbr0
00:10:db:ff:20:02 dev tap221i4 vlan 284 master vmbr7
```

Those ports were assigned ordinary hypervisor MAC addresses. Seeing a Juniper virtual MAC learned on them is direct evidence that no anti-spoof filter is in the path.

## Bridge port flags

The Linux defaults are correct. They are listed here because each one is load-bearing, and because a host hardened for tenant isolation will have changed several of them.

| Flag | Required | Why |
|---|---|---|
| `learning` | on | the reth virtual MAC must be learned, and re-learned when it moves to the other node on failover |
| `flood`, `bcast_flood`, `mcast_flood` | on | unknown-unicast, ARP and gratuitous ARP must reach the peer node |
| `isolated` | off | port isolation severs node-to-node traffic completely |
| `locked`, `mab` | off | MAC locking rejects the virtual MAC outright |
| `neigh_suppress` | off | ARP suppression absorbs the gratuitous ARP that redirects traffic after failover |
| `hairpin`, `guard`, `root_block`, `vlan_tunnel` | off | defaults; no reason to change them for this purpose |

Inspect with:

```
bridge -d link show | grep -A2 '^[0-9]*: tapVMID'
```

`learning` and `neigh_suppress` are coupled in a way worth understanding. Failover works by the surviving node issuing a gratuitous ARP so the bridge relearns the virtual MAC on its new port. Suppress that ARP, or disable learning, and the bridge keeps forwarding to the dead node's port until the forwarding entry ages out — five minutes at the default `ageing_time` of 30000. The symptom reads as "failover does not work" rather than as a bridge problem.

`ageing_time` itself needs no tuning. The default is correct because gratuitous ARP, not expiry, is what drives relearning in normal operation.

## Tap interface state

Guest taps run in promiscuous mode with all-multicast enabled, set by the hypervisor when it attaches them:

```
<BROADCAST,MULTICAST,PROMISC,UP,LOWER_UP> ... promiscuity 2 allmulti 1
```

This is what permits a source MAC other than the assigned one to leave the guest at all. It is standard behaviour and requires no configuration, but it explains why the anti-spoof rule — and not the tap itself — is what blocks reth traffic when the firewall is enabled.

## Netfilter

On a working host, `br_netfilter` is **not loaded**, and the bridge netfilter sysctls are all zero:

```
lsmod | grep br_netfilter                  # expect no output
sysctl net.bridge.bridge-nf-call-iptables  # expect 0
sysctl net.bridge.bridge-nf-call-ip6tables # expect 0
sysctl net.bridge.bridge-nf-call-arptables # expect 0
```

Bridged frames bypass netfilter entirely. If something on the host has loaded `br_netfilter` and enabled these, bridged cluster traffic becomes subject to host firewall rules that were never written with it in mind.

## Offloads

Leave them alone. The reference build runs entirely stock: transmit checksumming off, TCP segmentation offload off, generic segmentation and receive offload on, transmit VLAN offload on. They are recorded here so that nobody "fixes" them while chasing a fabric problem whose real cause is MTU.

## Node symmetry

Both guests must be identical in NIC index to bridge and VLAN. Only the MAC addresses may differ.

```
diff <(qm config VMID_A | grep -E '^net[0-9]:' | sed 's/=[A-Fa-f0-9:]\{17\}//') \
     <(qm config VMID_B | grep -E '^net[0-9]:' | sed 's/=[A-Fa-f0-9:]\{17\}//')
```

Expected output: none.

Asymmetry is worth checking explicitly because its symptom is misleading. A NIC on the wrong VLAN on one node only breaks traffic in one direction, which surfaces as an intermittent or partially working cluster rather than a clean failure, and it survives every check that looks only at interface state.

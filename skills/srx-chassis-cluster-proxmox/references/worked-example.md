# Worked example: a healthy two-node cluster

## Contents

- [Hypervisor](#hypervisor)
- [Junos configuration](#junos-configuration)
- [What healthy looks like](#what-healthy-looks-like)
- [Two known deviations](#two-known-deviations)

A complete build to diff your own against. Every value was measured on a running, healthy cluster: two vSRX guests on one Proxmox VE host, cluster-id 2, Junos 24.4R1.9, five reth interfaces.

## Hypervisor

One portless VLAN-aware bridge carries the control link, the fabric link, and four of the five reth segments. The fifth reth rides an existing site-LAN bridge untagged.

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

VLAN allocation: 280 control, 281 fabric, 282 / 284 / 285 / 286 for reth0, reth2, reth3 and reth4. Each guest tap is an access port (`PVID Egress Untagged`).

Both guests carry eight virtio NICs, identical at every index apart from their MAC addresses:

| NIC | Bridge | VLAN | Node 0 | Node 1 | Role |
|---|---|---|---|---|---|
| `net0` | site LAN | untagged | `fxp0` | `fxp0` | management |
| `net1` | `vmbr7` | 280 | `em0` | `em0` | control link |
| `net2` | `vmbr7` | 282 | `ge-0/0/0` | `ge-7/0/0` | reth0 |
| `net3` | site LAN | untagged | `ge-0/0/1` | `ge-7/0/1` | reth1 |
| `net4` | `vmbr7` | 284 | `ge-0/0/2` | `ge-7/0/2` | reth2 |
| `net5` | `vmbr7` | 281 | `ge-0/0/3` | `ge-7/0/3` | fabric |
| `net6` | `vmbr7` | 285 | `ge-0/0/4` | `ge-7/0/4` | reth3 |
| `net7` | `vmbr7` | 286 | `ge-0/0/5` | `ge-7/0/5` | reth4 |

Guest sizing is modest: 2 cores, 4 GB, `cpu: host`, one virtio disk. No NIC carries `firewall=1`, and neither guest has a per-VM firewall file.

## Junos configuration

```
chassis {
    cluster {
        reth-count 5;
        redundancy-group 0 {
            node 0 priority 100;
            node 1 priority 1;
        }
        redundancy-group 1 {
            node 0 priority 100;
            node 1 priority 1;
            preempt;
            interface-monitor {
                ge-0/0/4 weight 255;
                ge-7/0/4 weight 255;
                ge-0/0/5 weight 255;
                ge-7/0/5 weight 255;
            }
        }
    }
}
```

Physical members bound to their redundant parents:

```
interfaces {
    ge-0/0/0 { gigether-options { redundant-parent reth0; } }
    ge-7/0/0 { gigether-options { redundant-parent reth0; } }
    ge-0/0/1 { gigether-options { redundant-parent reth1; } }
    ge-7/0/1 { gigether-options { redundant-parent reth1; } }
    ge-0/0/2 { gigether-options { redundant-parent reth2; } }
    ge-7/0/2 { gigether-options { redundant-parent reth2; } }
    ge-0/0/4 { gigether-options { redundant-parent reth3; } }
    ge-7/0/4 { gigether-options { redundant-parent reth3; } }
    ge-0/0/5 { gigether-options { redundant-parent reth4; } }
    ge-7/0/5 { gigether-options { redundant-parent reth4; } }

    fab0 { fabric-options { member-interfaces { ge-0/0/3; } } }
    fab1 { fabric-options { member-interfaces { ge-7/0/3; } } }

    fxp0 { unit 0 { family inet; } }

    reth0 {
        redundant-ether-options { redundancy-group 1; }
        unit 0 { family inet { address 203.0.113.97/24; } }
    }
    reth1 {
        redundant-ether-options { redundancy-group 1; }
        unit 0 { family inet { address 192.168.1.91/24; } }
    }
}
```

`reth2` through `reth4` follow the same shape. Note that every reth belongs to redundancy group 1; group 0 carries only the loopback and control-plane mastership.

## What healthy looks like

`show chassis cluster status` — node 0 primary at priority 100, node 1 secondary, no monitor failures on either node, in both redundancy groups. A `failover-count` of 1 on each group is normal after a cold boot; it records the initial election.

`show chassis cluster interfaces`:

```
Control link status: Up
    0       em0         Up                 Disabled      Disabled

Fabric link status: Up
    fab0    ge-0/0/3           Up   / Up
    fab1    ge-7/0/3           Up   / Up

Redundant-ethernet Information:
    reth0        Up          1
    reth1        Up          1
    reth2        Up          1
    reth3        Up          1
    reth4        Up          1
```

`show chassis cluster statistics` — control-link heartbeats sent and received advancing roughly in step with **zero errors**, fabric probes both sent and received, and runtime-object counters moving on the primary (session creates, closes and changes). Received counts of zero on the primary are expected: the primary sends state, the secondary receives it.

`show interfaces fab0 | match MTU` — `MTU: 9014` at layer 2 and `9000` for inet. This is the check that proves the underlying bridge accepted jumbo frames.

On the hypervisor, `bridge fdb show | grep -i '00:10:db'` returns the reth virtual MACs learned on the primary's taps:

```
00:10:db:ff:20:01 dev tap221i3 vlan 1   master vmbr0
00:10:db:ff:20:02 dev tap221i4 vlan 284 master vmbr7
```

## Two known deviations

This build is healthy, not exemplary. Both of the following are real and should not be copied blindly.

**Redundancy-group priorities are 100 and 1, not symmetric.** It works: if node 0 loses a monitored interface its priority drops to zero and node 1, at priority 1, takes over. But the margin is as thin as it can be while still functioning, and node 1 can never preempt back. A sibling cluster on the same host uses 200 and 100. **Prefer 200/100.** The wide split here is historical, not a design decision worth reproducing.

**Both nodes raise a minor alarm: "Rescue configuration is not set."** Benign, and the only reason an automated health check returns `warn` rather than `pass` on this cluster. Clear it with:

```
request system configuration rescue save
```

Worth doing on any cluster you intend to keep, because a rescue configuration is what `rollback rescue` restores after a change locks you out — a real risk on a device whose interfaces you are actively rewiring.

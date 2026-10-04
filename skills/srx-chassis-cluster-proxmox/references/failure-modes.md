# Failure modes and their hypervisor causes

## Contents

- [Reths down immediately post-commit: RG1 hold state](#reths-down-immediately-post-commit-rg1-hold-state)
- [Reths up, no traffic](#reths-up-no-traffic)
- [Undersized fabric segment](#undersized-fabric-segment)
- [Secondary ineligible or disabled](#secondary-ineligible-or-disabled)
- [Intermittent or one-way](#intermittent-or-one-way)
- [Traffic stops after failover, returns in about five minutes](#traffic-stops-after-failover-returns-in-about-five-minutes)
- [Nodes cannot see each other despite correct VLANs](#nodes-cannot-see-each-other-despite-correct-vlans)
- [Duplicate MAC complaints](#duplicate-mac-complaints)
- [Internet-facing segment dies when clustering is enabled](#internet-facing-segment-dies-when-clustering-is-enabled)
- [Worked post-mortem: three independent faults](#worked-post-mortem-three-independent-faults)

Chassis-cluster failures on a hypervisor rarely announce themselves. This table maps what you see to what is actually wrong.

| Symptom | Cause |
|---|---|
| Reths report `Down` immediately post-commit, RG1 shows `hold`, member legs `Up` | RG1 hold-down timer — **expected**, not a fault, see below |
| Reths report `Up`, no traffic passes | per-NIC firewall enabled: anti-spoof rule versus the reth virtual MAC |
| Cluster reports healthy but the fabric segment is undersized | fabric segment below MTU 9000 — **silent**, see below |
| Secondary stays `ineligible` or `disabled` | control-link segment not isolated, or leaking into a data segment |
| Intermittent, or works in one direction only | NIC index to bridge/VLAN mapping differs between the nodes |
| Traffic stops after failover, returns in about five minutes | `neigh_suppress` on or `learning` off: gratuitous ARP lost, forwarding entry ages out |
| Nodes cannot see each other despite correct VLANs | `isolated` on, or `locked` / `mab` set on the port |
| Duplicate MAC complaints on the segment | two clusters sharing a cluster-id |
| The internet-facing segment dies the moment clustering is enabled | standalone-shaped guest promoted in place: second NIC became the control link and every index shifted |

---

## Reths down immediately post-commit: RG1 hold state

After committing the redundancy-group configuration, RG1 enters a **hold state** on both nodes while the RG hold-down timer runs. This is expected post-commit behaviour, not a misconfiguration.

On the third build (Junos 26.2R1.7) RG1 was observed in `hold` shortly after the commit and had resolved on its own by a re-check **180 seconds later**; the exact duration was not timed. Junos defaults the RG hold-down to 300 seconds, which is consistent with that observation but was not independently measured here. Treat it as minutes, not seconds — and wait rather than intervene.

**During the hold window:**

- `show chassis cluster status` reports RG1 with `"status": "hold"` on BOTH nodes
- `show chassis cluster interfaces` shows **reths as `Down`**
- ALL member legs report `Up / Up` under Interface Monitoring
- `"monitor_failures": []` is empty
- `"failover_count": 0` before the timer expires, then increments to 1 when primary/secondary election completes

**After the timer expires**, RG1 elects primary/secondary with no intervention, reths come Up with their addresses, and `failover_count: 1` reflects the initial election.

**How to distinguish from real faults:**

| Symptom | RG1 hold (expected) | Anti-spoof (fault) |
|---|---|---|
| RG1 status | literally reads `hold` | `primary` / `secondary` |
| Reths | `Down` | `Up` |
| Member legs | `Up / Up` | `Up / Up` |
| Monitor failures | empty | empty (fault is hypervisor-side) |
| Resolution | wait for the timer, resolves itself | disable per-NIC firewall |

The hold state is time-bounded and self-resolving. Do not debug it as a fault — confirm RG1 status says `hold`, verify member legs are up and monitor-failures is empty, then wait for the timer.

The bridge forwarding table is not a useful discriminator during hold and is deliberately left out of the table above: the reth virtual MACs were not checked mid-hold on the third build, so what the FDB shows in that window is untested.

## Reths up, no traffic

**Check on the hypervisor:**

```
qm config VMID | grep firewall=1
bridge fdb show | grep -i '00:10:db'
```

A non-empty first result, or an empty second result while reths report `Up`, confirms it.

**Check on the device:** `show chassis cluster interfaces` shows every reth `Up`, and `show chassis cluster statistics` shows session-create counters advancing on the primary while nothing arrives at the secondary.

**Remedy:** remove `firewall=1` from every cluster NIC and delete any `/etc/pve/firewall/VMID.fw`. The option is enabled by default when a NIC is added through the web UI, so it recurs whenever someone edits the guest there.

## Undersized fabric segment

This one has no symptom, which is what makes it dangerous. Tested directly: with the fabric segment forced to 1500 on an otherwise healthy cluster, the fabric link stayed **Up**, probes kept flowing in both directions, every reth stayed Up, both redundancy groups stayed healthy, and no alarm was raised. Fabric probes are small enough to cross a 1500 segment.

The mismatch is real but latent — `fab0` still reports MTU 9014/9000 and behaves as though the segment can carry it.

**Check on the hypervisor** — this is the only reliable check:

```
ip -d link show BRIDGE | head -2
cat /sys/class/net/TAP/mtu
```

**Check on the device:** `show interfaces fab0 | match MTU` reports 9014 / 9000. Note this tells you what Junos *provisioned*, not what the segment can carry, so it confirms the requirement rather than compliance with it.

**Remedy:** set the fabric segment to 9000. Taps inherit the bridge MTU at creation, so raising the bridge covers new taps while running guests need their taps raised explicitly (`ip link set TAP mtu 9000`) or a restart.

**Verify at build time, not during troubleshooting.** Because cluster health never reflects this, an undersized fabric will pass every validation step and surface later as unexplained behaviour under load.

## Secondary ineligible or disabled

**Check:** confirm the control VLAN carries only the two control-link taps. A control segment shared with data traffic, or bridged to anything beyond the two nodes, disrupts the heartbeat.

**Check on the device:** `show chassis cluster statistics` — heartbeat errors greater than zero, or received counts far below sent.

**Remedy:** give control its own VLAN with exactly two member ports.

## Intermittent or one-way

**Check:** the node symmetry diff in `proxmox-network-invariants.md`. Expected output is nothing.

**Remedy:** correct the mismatched NIC so both guests agree at every index. This failure is worth ruling out early precisely because interface state looks healthy on both nodes.

## Traffic stops after failover, returns in about five minutes

**Check:** `bridge -d link show` for the cluster taps — `learning` must be on and `neigh_suppress` off.

Five minutes is the tell. It is the default `ageing_time` of 30000, which is how long the bridge keeps forwarding to the departed node's port when nothing tells it to relearn.

**Remedy:** re-enable learning, disable neighbour suppression. Do not compensate by lowering `ageing_time`; that hides the fault and slows convergence for everything else on the bridge.

## Nodes cannot see each other despite correct VLANs

**Check:** `bridge -d link show` for `isolated on`, `locked on`, or `mab on`.

**Remedy:** clear them on cluster ports. These usually arrive from a host-hardening template written for tenant isolation, where preventing guest-to-guest traffic is the entire point — which is exactly what a cluster needs to do.

## Duplicate MAC complaints

**Check:** enumerate cluster-ids already in use on the segment. The reth MAC is `00:10:db:ff:<cluster-id x 16>:<reth number>`, so two clusters sharing an id collide on every reth.

**Remedy:** rebuild one cluster with a different cluster-id. It cannot be changed without `set chassis cluster cluster-id ... reboot` on both nodes.

## Internet-facing segment dies when clustering is enabled

**Check:** `qm config VMID | grep '^net'` before enabling. If the second NIC carries data, this will happen.

**Remedy:** redraw the NIC plan — see `vsrx-nic-mapping.md`. There is no in-place fix.

---

## Worked post-mortem: three independent faults

A pair of vSRX guests intended to become a chassis cluster, abandoned before completion. Each fault below was sufficient on its own.

**1. The fabric bridge was 1500.** Dedicated control and fabric bridges had been created — the right instinct — but the fabric one was left at the default MTU while Junos provisions its fabric interface to 9014. The control bridge was also 1500, and that was *correct*: control never needed jumbo. A build can hold a right and a wrong 1500 at the same time.

**2. The guests were never attached to those bridges.** Both had zero ports. The bridges existed in the host's network configuration and carried nothing.

**3. The guests were standalone-shaped.** Four NICs each: management plus three data VLANs, no control segment and no fabric segment. Enabling cluster mode would have consumed the first data VLAN as the control link and shifted the remaining two, so even completing steps 1 and 2 would not have produced a working cluster.

The instinct to build dedicated control and fabric segments was correct. What was skipped was the fabric MTU and the NIC re-plan — and because nothing surfaced an error, the attempt simply stopped rather than failing visibly.

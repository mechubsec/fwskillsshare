---
name: srx-chassis-cluster-proxmox
description: Build and validate a Juniper SRX or vSRX chassis cluster whose two nodes are Proxmox VE guests. Use when planning bridges and VLANs for the control and fabric links, mapping virtual NICs to Junos interface names, bootstrapping cluster-id, configuring fab interfaces, reth interfaces and redundancy groups, or diagnosing a cluster that forms but passes no traffic. Not for Multi-Node High Availability.
version: 1.2.1
author:
  - fastrevmd-lab
  - Claude
  - GPT
license: MIT
metadata:
  hermes:
    tags: [srx, vsrx, junos, chassis-cluster, proxmox, kvm, linux-bridge, reth, fabric-link, control-link, mtu, high-availability, virtualization]
    related_skills: [srx-mnha, srx-policy, srx-nat, parsing-srx-configs, sd-onprem-proxmox-deploy]
  sources:
    - title: "Reference implementation: two-node vSRX chassis cluster on Proxmox VE"
      author: fastrevmd-lab
      note: "Original lab work. Hypervisor and Junos values measured on a healthy two-node vSRX cluster (cluster-id 2, Junos 24.4R1.9) running as Proxmox guests."
      retrieved: "2026-08-11"
    - title: "Proving build: second cluster stood up by following this skill"
      author: fastrevmd-lab
      note: "Independent build on a different host from a factory template (cluster-id 9, Junos 26.2R1.7). Confirmed the NIC mapping and reth MAC formula, and corrected the fabric-MTU claim and fxp0 addressing requirement."
      retrieved: "2026-08-11"
    - title: "Third build: remote-lab cluster following this skill"
      author: fastrevmd-lab
      note: "Remote lab build on a separate host (VMs 340/341 legacy-dc-n0/n1, cluster-id 3, Junos 26.2R1.7, single VLAN-aware bridge vmbr6 MTU 9000). Confirmed tap MTU inheritance from bridge, documented RG1 hold state post-commit, and validated the skill's NIC mapping and fxp0-under-groups warnings as exact and essential."
      retrieved: "2026-08-12"
---

# SRX Chassis Cluster on Proxmox VE

## Contents

- [Overview](#overview)
- [Runtime intake](#runtime-intake)
- [Before you start](#before-you-start)
- [Procedure](#procedure)
- [Validation](#validation)
- [Common pitfalls](#common-pitfalls)
- [Reference material](#reference-material)
- [Source notes](#source-notes)

## Overview

Chassis cluster joins two SRX nodes into one logical chassis: a shared configuration, active/backup control plane, redundancy groups that move ownership on failure, and reth interfaces carrying a virtual MAC. Juniper documents it for two physical appliances joined by real cables.

On Proxmox VE the control link, the fabric link, and every reth leg are Linux bridge ports instead. That substitution is where clusters fail, and it fails quietly. Nothing logs "your bridge dropped this frame." The observable result is a cluster that forms and reports healthy while passing no traffic — or one that is genuinely misconfigured underneath while every health check on the device reports it as fine.

This skill owns that hypervisor-to-Junos seam: bridge and VLAN design, virtual NIC to Junos interface mapping, the bridge settings that must hold, cluster bootstrap, and a validation sequence that catches silent filtering instead of trusting a green status line.

Use `srx-mnha` for Multi-Node High Availability, which is a different HA model with different failure modes. Use `srx-policy` and `srx-nat` for the security configuration riding on the reth interfaces, and `parsing-srx-configs` for full-configuration extraction.

## Runtime intake

Before starting the workflow, inspect the request, supplied artifacts, and
available approved read-only evidence. If unresolved facts could materially
change safety, scope, correctness, confidence, or the requested output, read
`references/runtime-intake.md`. For each unresolved material fact whose catalog
condition is true, invoke Claude `AskUserQuestion` or Codex `request_user_input`
before continuing or issuing an open-ended request. Ask at most three
single-select catalog questions per round. After each response, ask another
round whenever any unresolved material catalog condition remains true; continue
only when none remain. Do not repeat answered questions or show the full
catalog. Without a native tool, present each selected catalog question with its
2-3 labeled choices and a free-text `Other` path in concise plain text; do not
substitute a generic checklist. Never request secrets or unredacted customer
data. Treat intake answers as task context, not approval for a live change;
obtain separate explicit approval before configuration, commit, upgrade,
reboot, delete, or failover actions.

## Before you start

Three questions decide whether a build can succeed. Answer all three before touching a guest.

**1. Is there a jumbo-capable segment for the fabric?**

```
ip -d link show BRIDGE | head -2
```

The fabric segment needs MTU 9000. The control segment does not. If no jumbo bridge exists, creating one is step zero — see `references/proxmox-network-invariants.md`.

Ask this **now**, not later: a cluster whose fabric sits on a 1500-byte segment passes every device-side health check, so this is the one requirement you cannot go back and verify from the firewall.

**2. Are the guests purpose-built for clustering, or standalone-shaped?**

```
qm config VMID | grep '^net'
```

If the second NIC carries data today, this VM cannot be promoted in place. In cluster mode the second NIC becomes the control link and every remaining interface index shifts. The NIC plan has to be redrawn. See `references/vsrx-nic-mapping.md`.

**3. Is the cluster-id free on this L2 domain?**

The cluster-id determines the reth virtual MAC. Two clusters sharing a cluster-id on one bridged domain produce duplicate MAC addresses.

## Procedure

### Phase 1 — hypervisor network

Build one portless, VLAN-aware bridge at MTU 9000 and give each function its own VLAN: one for control, one for fabric, one per reth. Verify each chosen VLAN ID is unused on that host before committing to it.

Bridge settings that must hold, and why each is load-bearing, are in `references/proxmox-network-invariants.md`. The short version: VLAN-aware, MTU 9000, STP off, forward delay 0, MAC learning on, flooding on, port isolation off, MAC locking off, neighbour suppression off.

### Phase 2 — guests

Clone from a template, then size the NIC list to the plan: management, control, fabric, and one per reth. Wire every NIC to its bridge and tag.

Two checks close this phase.

**No per-NIC firewall on any cluster NIC.** This is the single easiest way to break a cluster, because the option is enabled by default when a NIC is added through the web UI.

```
qm config VMID | grep -c 'firewall=1'
ls /etc/pve/firewall/VMID.fw
```

Expected: `0`, and no such file.

**The two nodes are identical apart from MAC addresses.**

```
diff <(qm config VMID_A | grep -E '^net[0-9]:' | sed 's/=[A-Fa-f0-9:]\{17\}//') \
     <(qm config VMID_B | grep -E '^net[0-9]:' | sed 's/=[A-Fa-f0-9:]\{17\}//')
```

Expected: no output. Any asymmetry produces a one-way blackhole that presents as an intermittent cluster.

### Phase 3 — cluster bootstrap

Boot both nodes standalone, reach each over its management interface, then set the cluster identity per node:

```
set chassis cluster cluster-id ID node 0 reboot
set chassis cluster cluster-id ID node 1 reboot
```

This is not configuration. It does not appear in `show configuration`, it does not roll back, and it determines the reth virtual MAC. Both nodes reboot into cluster mode.

After the reboot, confirm the interface mapping on this image before configuring anything — releases and images differ, and the mapping is the foundation everything else rests on:

```
show interfaces terse | match "^ge-|^em0|^fxp0"
```

### Phase 4 — cluster configuration

Node-specific identity comes from groups, because the two nodes share one configuration. **Management addressing belongs here too, and it must be static:**

```
set groups node0 system host-name NAME-n0
set groups node0 interfaces fxp0 unit 0 family inet address A.B.C.D/NN
set groups node1 system host-name NAME-n1
set groups node1 interfaces fxp0 unit 0 family inet address A.B.C.E/NN
set apply-groups "${node}"
delete interfaces fxp0
```

**A chassis cluster cannot manage `fxp0` with a DHCP client.** A template that used DHCP standalone will come back from the cluster-mode reboot with no management address at all and never send a DHCP request. The cluster itself forms normally — control link up, heartbeats flowing — so this looks like a boot failure when it is only an addressing one.

Plan for this before the reboot: either configure the groups above while the nodes are still standalone and reachable, or accept that recovering needs console access. Add a route back to whatever manages the device, since `fxp0` no longer receives one from DHCP:

```
set routing-options static route MGMT-NET/NN next-hop GATEWAY
```

`commit` warns that `fxp0` should be configured under groups. That warning is confirmation you have done it correctly.

Then the cluster itself:

```
set chassis cluster reth-count N
set chassis cluster redundancy-group 0 node 0 priority 200
set chassis cluster redundancy-group 0 node 1 priority 100
set chassis cluster redundancy-group 1 node 0 priority 200
set chassis cluster redundancy-group 1 node 1 priority 100
set chassis cluster redundancy-group 1 preempt
set chassis cluster redundancy-group 1 interface-monitor INTERFACE weight 255
set interfaces fab0 fabric-options member-interfaces ge-0/0/X
set interfaces fab1 fabric-options member-interfaces ge-7/0/X
set interfaces ge-0/0/Y gigether-options redundant-parent rethN
set interfaces ge-7/0/Y gigether-options redundant-parent rethN
set interfaces rethN redundant-ether-options redundancy-group 1
```

Redundancy group 0 owns control-plane mastership; group 1 and above own data. Interface monitoring belongs on the data group only.

Use symmetric priorities such as 200/100. A wide split like 100/1 works but leaves the secondary with almost no margin and unable to preempt; `references/worked-example.md` documents a real cluster running that way and why not to copy it.

### Phase 5 — validate

Run the full sequence below. Do not stop at the first green line.

## Validation

| Check | Pass condition |
|---|---|
| `show chassis cluster status` | one primary, one secondary, no monitor failures |
| `show chassis cluster interfaces` | control link Up; `fab0` and `fab1` both Up/Up; every reth Up |
| `show chassis cluster statistics` | heartbeats incrementing, zero errors; fabric probes moving in both directions |
| `show interfaces fab0` | MTU 9014 / 9000 — what Junos provisioned, *not* proof the segment can carry it |
| `show system alarms` | no major alarms |
| `show version invoke-on all-routing-engines` | no version skew between routing engines |
| `bridge fdb show` on the hypervisor | reth virtual MACs present on the primary node's tap interfaces |
| `validate_chassis_cluster_health` | verdict `pass`, or `warn` only for a missing rescue configuration |

**A passing cluster status is not sufficient.** Reth interfaces report `Up` whenever their underlying links are up, including when the hypervisor is silently discarding every frame they send. Two checks catch that case and nothing else does: fabric probe counters moving in *both* directions, and the reth virtual MAC appearing in the bridge forwarding table.

**Immediately post-commit: RG1 hold state is expected.** After committing the redundancy-group configuration, RG1 shows status `hold` on both nodes while the RG hold-down timer runs. During this window, `show chassis cluster interfaces` reports reths as `Down` while all member legs report `Up / Up` under Interface Monitoring, `monitor_failures` remains empty, and RG1 status literally reads `hold`. This is expected post-commit behaviour, not a fault. Once the timer expires, RG1 elects primary/secondary with no intervention and the reths come Up with their addresses. Do not debug this as a misconfiguration — wait for the hold timer. See `references/failure-modes.md` for how to distinguish this from anti-spoof or other real faults.

```
bridge fdb show | grep -i '00:10:db'
```

An empty result while reth interfaces report `Up` is the anti-spoof signature. See `references/failure-modes.md`.

**This table cannot detect an undersized fabric segment.** A cluster with the fabric on a 1500-byte segment passes every row above — link Up, probes both ways, reths Up, no alarms. Verify the segment MTU on the hypervisor during the build; nothing on the device will tell you later.

## Common pitfalls

Full symptom-to-cause mapping with per-row checks and remedies is in `references/failure-modes.md`. The two that account for most lost time:

- **Per-NIC firewall left enabled.** The reth virtual MAC never matches the assigned MAC, so the anti-spoof rule discards every reth frame. Reths report `Up`, no traffic passes, nothing is logged. Enabled by default in the web UI.
- **Fabric segment below MTU 9000.** Junos provisions the fabric interface to a jumbo MTU on its own. A 1500-byte segment cannot carry those frames. The control link genuinely does not need jumbo, so "set everything to 9000" is the wrong lesson — the asymmetry is the lesson.

A third deserves naming because it destroys working service: **promoting a standalone-shaped VM in place.** The second NIC becomes the control link, taking whatever data segment it used to carry, and every remaining interface index shifts by one.

## Reference material

- `references/proxmox-network-invariants.md` — bridge and VLAN design, the fabric/control MTU asymmetry and its mechanism, the anti-spoof trap, load-bearing port flags, node symmetry.
- `references/vsrx-nic-mapping.md` — virtual NIC to Junos interface mapping, the secondary node's slot model, and how to verify the mapping rather than assume it.
- `references/failure-modes.md` — symptom-to-cause table with checks and remedies, plus a worked three-fault post-mortem.
- `references/worked-example.md` — a complete healthy build to diff your own against, including its two known deviations.
- `references/runtime-intake.md` — intake question catalog.

## Source notes

This skill is original operational work, not a vendor-derived summary. Vendor documentation covers chassis cluster on physical appliances; the hypervisor-side requirements collected here are not documented by the vendor and were established empirically.

It rests on three independent builds:

- **Reference cluster** — cluster-id 2, Junos 24.4R1.9, five reths, control and fabric on dedicated VLANs of one portless VLAN-aware bridge. Source of the MTU measurements, port flags, and the anti-spoof forwarding-table evidence.
- **Second build (proving build)** — cluster-id 9, **Junos 26.2R1.7**, on a different host from a factory template, following this skill as written and correcting it where it was wrong.
- **Third build (remote-lab)** — VMs 340/341 on a separate remote host, cluster-id 3, **Junos 26.2R1.7**, single VLAN-aware bridge vmbr6 MTU 9000 carrying control VLAN 210, fabric 211, reth0 212, reth1 213. Confirmed tap MTU inheritance and documented the RG1 hold state.

The second build changed three things:

1. **The fabric MTU claim was too strong.** Dropping the fabric segment to 1500 did not break the cluster: link Up, probes both directions, reths Up, no failover, no alarms. The requirement stands, but the failure is latent rather than immediate, and no health check reveals it.
2. **`fxp0` cannot use DHCP in cluster mode.** A DHCP-addressed template returns from the cluster-mode reboot with no management address and sends no request. Management must be static, per node, under `groups`.
3. **A better mapping proof was found** — matching reth virtual MACs against tap interfaces in the hypervisor forwarding table verifies every NIC position in one command.

The third build validated the skill's predictions with no corrections needed: NIC mapping was exact, the fxp0-under-groups warning prevented a lockout, and tap interfaces inherited MTU 9000 from the bridge with no per-NIC `mtu=` parameter set. It surfaced one undocumented post-commit behaviour: RG1 sits in status `hold` after the redundancy-group config is committed, during which reths report `Down` while member legs are `Up` and monitor-failures is empty — expected timer behaviour, not a fault. It had cleared on its own within 180 seconds; the duration itself was not timed.

Values that were measured are stated as measurements. Where behaviour is inferred from a mechanism rather than directly observed — notably the consequence of an undersized fabric under sustained load — the text says so rather than implying it was tested.

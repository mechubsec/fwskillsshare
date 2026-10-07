---
name: srx-mnha
description: Design, configure, audit, and troubleshoot Juniper SRX Multi-Node High Availability. Use when handling routed, default-gateway, or hybrid modes, chassis-cluster migration, SRGs, ICL or ICD, session sync, BGP or BFD failover, VIPs, IPsec, NAT, proxy ARP, routing instances, or DHCP. Use focused SRX skills for non-MNHA behavior.
version: 1.3.4
author:
  - fastrevmd-lab
  - Claude
  - GPT
license: MIT
metadata:
  hermes:
    tags: [srx, junos, mnha, high-availability, chassis-cluster, srg, icl, icd, bgp, bfd, ipsec, ike, nat, routing-instance, dhcp]
    related_skills: [srx-mnha-builder, srx-cluster-to-mnha, parsing-srx-configs, srx-nat, srx-policy, srx-autovpn-full-tunnel, srx-ipsec-hub-spoke]
  sources:
    - title: "DHCP on MNHA: Back to Basics"
      author: James Rathbun
      url: https://community.juniper.net/blogs/james-rathbun/2026/04/22/dhcp-on-mnha-back-to-basics?CommunityKey=44efd17a-81a6-4306-b5f3-e5f82402d8d3
      retrieved: "2026-05-14"
    - title: Multi-Node High Availability Basics
      author: Steven Jacques
      url: https://community.juniper.net/blogs/steven-jacques/2024/12/20/multi-node-high-availability-basics?CommunityKey=44efd17a-81a6-4306-b5f3-e5f82402d8d3
      retrieved: "2026-05-14"
    - title: Hybrid MNHA with eBGP
      author: James Rathbun
      url: https://community.juniper.net/blogs/james-rathbun/2025/06/12/hybrid-mnha-with-ebgp?CommunityKey=44efd17a-81a6-4306-b5f3-e5f82402d8d3
      retrieved: "2026-05-14"
    - title: "SRX clustering: from Chassis Cluster to MultiNode High Availability"
      author: Laurent Paumelle
      url: https://community.juniper.net/blogs/laurentp/2026/02/15/srx-from-chassis-cluster-to-mnha
      retrieved: "2026-05-14"
    - title: "MNHA, IPSec and Multiple Routing Instances"
      author: James Rathbun
      url: https://community.juniper.net/blogs/james-rathbun/2026/03/30/mnha-ipsec-and-multiple-routing-instances?CommunityKey=44efd17a-81a6-4306-b5f3-e5f82402d8d3
      retrieved: "2026-05-14"
---

# SRX Multi-Node High Availability (MNHA)

## Contents

- [Overview](#overview)
- [Runtime intake](#runtime-intake)
- [Chassis Cluster vs MNHA](#chassis-cluster-vs-mnha)
- [Chassis-Cluster to MNHA Interface Migration](#chassis-cluster-to-mnha-interface-migration)
- [Deployment Modes](#deployment-modes)
- [Services Redundancy Groups](#services-redundancy-groups)
- [ICL: Inter-Chassis Link](#icl-inter-chassis-link)
- [ICD: Inter-Chassis Datalink](#icd-inter-chassis-datalink)
- [IPsec VPNs on MNHA with Multiple Routing Instances](#ipsec-vpns-on-mnha-with-multiple-routing-instances)
- [NAT, Proxy ARP, and Deterministic Routing](#nat-proxy-arp-and-deterministic-routing)
- [Runtime Object and Session Synchronization](#runtime-object-and-session-synchronization)
- [Configuration Synchronization](#configuration-synchronization)
- [Hybrid MNHA with eBGP Pattern](#hybrid-mnha-with-ebgp-pattern)
- [DHCP on MNHA](#dhcp-on-mnha)
- [Verification Checklist](#verification-checklist)
- [Troubleshooting Commands](#troubleshooting-commands)
- [Common Pitfalls](#common-pitfalls)
- [Field-Confirmed Behaviors](#field-confirmed-behaviors)
- [Source Notes](#source-notes)

## Overview

Multi-Node High Availability (MNHA) is Juniper SRX high availability built around independent SRX nodes that synchronize runtime state over routed HA links. Unlike chassis cluster, MNHA nodes do not become a single logical chassis. Each node keeps its own control plane, hostname, management, routing protocols, interface addressing, and node-specific configuration. Stateful firewall/NAT/IPsec runtime objects can still synchronize so traffic can survive a path or node failover when the design keeps routing, interfaces, policy, and HA state aligned.

Use MNHA as an L3-first HA design. Routing policy, BFD, link monitoring, service redundancy groups, and optional VIP behavior determine which node handles traffic. Avoid treating MNHA as a drop-in chassis-cluster clone; it solves different problems and has different failure modes. **To build a new pair step by step through a Junos MCP server, use `srx-mnha-builder`. To convert an existing chassis-cluster configuration end to end (interview, per-node configs, fidelity report, cutover runbook), use `srx-cluster-to-mnha`.**

## Runtime intake

Use this skill only for MNHA-specific design and behavior. Use `parsing-srx-configs` for full-config extraction, `srx-nat` for general NAT, and `srx-policy` for general policy design.
Before acting, inspect the request, artifacts, and approved read-only evidence. If unresolved facts materially change safety, scope, correctness, confidence, or output, read `references/runtime-intake.md`. For each unresolved material fact whose catalog condition is true, invoke Claude `AskUserQuestion` or Codex `request_user_input` before continuing or issuing an open-ended request. Ask at most three single-select catalog questions per round. After each response, ask another round whenever any unresolved material catalog condition remains true; continue only when none remain. Do not repeat answered questions or show the full catalog. Without a native tool, present each selected catalog question with its 2-3 labeled choices and a free-text `Other` path in concise plain text; do not substitute a generic checklist. Never request secrets or unredacted customer data. Answers are context, not live-change approval; obtain separate explicit approval before configuration, commit, upgrade, reboot, delete, or failover.

## Chassis Cluster vs MNHA

Chassis cluster is the traditional SRX L2 HA model:

- two nodes form one logical chassis
- active/backup control plane behavior
- shared cluster configuration
- reth interfaces with virtual IP/MAC behavior
- redundancy group ownership changes during failover
- nodes usually need the same L2 domains for clustered interfaces
- failover may depend on gratuitous ARP and L2 convergence

MNHA is different:

- nodes remain independent SRX devices
- each node has its own routing process and control plane
- both nodes can maintain routing adjacencies at the same time
- forwarding preference is normally driven by routing policy, BFD, and SRG state
- state synchronization is separate from full configuration synchronization
- ICL/ICD are logical routed links, not chassis-cluster HA/fabric ports
- designs can be routed, default-gateway/L2-like, or hybrid

Key design translation:

| Chassis cluster habit | MNHA interpretation |
|---|---|
| One shared config | Independent configs; synchronize only what should match |
| Reth/VIP everywhere | Use routed node IPs where possible; use VIPs only when the design requires them |
| RG master owns traffic | Routing and SRG state influence traffic path |
| Active/passive control plane | Independent active control planes |
| Dedicated HA/fabric assumptions | Routed ICL/ICD paths with security/routing/MTU planning |

Always verify platform and Junos support in Juniper Pathfinder / Feature Explorer and current Juniper documentation before deployment. MNHA feature support, scale, asymmetric-flow support, multi-node support, and platform support are release-dependent.

## Chassis-Cluster to MNHA Interface Migration

To convert an existing chassis-cluster configuration end to end (interview, per-node configs, fidelity report, cutover runbook), use `srx-cluster-to-mnha`.

Read `references/mnha-advanced-workflows.md` before converting chassis-cluster `reth` members. The migration requires a per-node decision between local physical interfaces and a local `ae`; cluster LACP does not prove the upstream is a valid standalone-node LAG.

## Deployment Modes

### Routed / L3 MNHA

Routed MNHA is the cleanest MNHA model.

Characteristics:

- no interface VIP required for normal forwarding
- each node has unique interface IP addresses
- each node peers with upstream/downstream routers independently
- BGP, OSPF, static metrics, or policy decide preferred paths
- SRG0 is commonly involved for default active/active service behavior
- symmetry is strongly preferred for stateful inspection

Use routed MNHA when:

- the network can route to either SRX node
- you want fast failover with routing/BFD
- geo-redundancy or L3 separation matters
- you want to avoid L2 stretch and virtual MAC dependencies

**Failover only covers the routed sides.** Each node has its own interface IP on
every segment, so a directly-attached host that uses one node's IP as its static
default gateway does **not** fail over — kill that node and the host is stranded
(no floating gateway on that segment). Routed failover works only where a *router*
(BGP/OSPF/BFD) re-converges to the survivor. An L2 segment of plain hosts that must
survive a node loss needs **default-gateway mode (VIP)** or upstream **ECMP** —
decide per segment (common to have the core-facing side routed while a client/DMZ
side needs a VIP). Field-confirmed 2026-07: an internet-facing host with a static
gateway of the active node's IP lost all connectivity on failover while the
BGP-driven core-facing side reconverged cleanly.

### Default-Gateway MNHA

Default-gateway mode provides L2-like gateway behavior with VIP/vMAC semantics.

Characteristics:

- a VIP is installed on the active node for an SRG
- clients use the VIP as their default gateway
- backup node does not install that VIP
- failover moves the VIP and sends ARP/GARP behavior to update the L2 domain
- requires shared L2 where the VIP is used

Use default-gateway mode when:

- hosts cannot be changed away from a shared default gateway address
- migrating from chassis cluster and preserving gateway addressing is important
- L2 gateway semantics are required on one or more segments

L2-adjacency caveats for `deployment-type switching` / default-gateway mode:

- The VIP rides on the `aeN.unit` (or physical unit) directly — no IRB/bridge-domain is introduced. The gateway is an interface VIP, not a routed SVI.
- The gateway vMAC **moves** on failover. Adjacent switches must accept that MAC move: check **MAC-move limits**, **Dynamic ARP Inspection (DAI)**, **storm-control**, and **EVPN/MLAG duplicate-MAC protection** — any of these can suppress or block the moved vMAC and silently break failover even though the SRG shows ACTIVE.
- Tie the segment's uplink to failover with SRG interface monitoring. Two
  forms commit: the bare `monitor interface <IFD>` (simple case: one or a few
  uplinks; verify on the target release that any down triggers failover
  evaluation):
  ```junos
  set chassis high-availability services-redundancy-group <SRG> monitor interface <IFD>
  ```
  and a named monitor-object with weights and thresholds for weighted or
  multi-object logic:
  ```junos
  set chassis high-availability services-redundancy-group <SRG> monitor monitor-object <NAME> interface interface-name <IFD> weight 100
  set chassis high-availability services-redundancy-group <SRG> monitor monitor-object <NAME> interface threshold 100
  set chassis high-availability services-redundancy-group <SRG> monitor monitor-object <NAME> object-threshold 100
  set chassis high-availability services-redundancy-group <SRG> monitor srg-threshold 100
  ```
  `interface-name` takes the physical IFD (e.g. `ge-0/0/2`). Failover fires
  when accumulated weight reaches the interface threshold, the object
  threshold, and the SRG threshold — size weights accordingly (see
  `references/source-hybrid-mnha-with-ebgp.md` for a weighted BFD + interface
  example). Both forms commit-checked on vSRX 26.2R1.7 (2026-09-29); the bare
  form is also used on 24.4R2.21 by `srx-mnha-builder`. Failover behavior of
  the bare form was not separately tested — verify with a link-down test.
- Chassis-cluster `interface-monitor` **weights do not map 1:1** to SRG monitoring. Do not port cluster monitor weights directly; redesign monitoring around SRG active/backup semantics and test failover explicitly.

### Hybrid MNHA

Hybrid mode combines routed and default-gateway behavior.

Common pattern:

- one side uses VIP/default-gateway behavior for an attached L2 segment
- the other side uses routed eBGP/OSPF/static paths
- SRG1+ controls active/backup service ownership for VIPs and route signaling
- BFD and interface monitoring can drive failover decisions

Use hybrid MNHA when:

- internal clients need a shared gateway VIP
- external/upstream connectivity is routed and redundant
- branch, campus, or mixed L2/L3 migration designs require both models

## Services Redundancy Groups

SRG0 is the default routed-MNHA group with no active/backup ownership; routing selects the forwarding node. SRG1+ provides active/backup behavior for VIPs, route signaling, failover triggers, and IPsec termination.

**Important:** The config syntax changed by release. Junos ≤24.x uses the flat `local-id local-ip` / `peer-id peer-ip` model; Junos 26.x requires the **grid model** (`grid-id`, `local-domain-id`, `peer-domain-id … peer-id`) and rejects the flat form. For `deployment-type routing`, `activeness-probe dest-ip <X> src-ip <Y>` is mandatory. A reboot is required to activate chassis-HA.

Complete SRG0/SRG1+ operational models, configuration attributes, verification commands, and grid-model field notes are in `references/srg-details.md`.

## ICL: Inter-Chassis Link

The ICL is the MNHA cluster communication and state-synchronization path. It is logical and routed; it does not require the physical HA/fabric ports used by chassis cluster.

ICL carries or supports:

- liveness / cluster communication
- cold sync after reconnect
- runtime object synchronization
- firewall session sync
- NAT state sync
- IPsec state sync where applicable
- HA-related control exchange

Design guidance:

- source ICL from stable loopback or dedicated interface addresses
- place ICL in a dedicated routing instance when practical
- when using MNHA IPsec with floating loopback tunnel anchors, the ICL routing instance and the floating loopback/external-interface routing instance must align; route leaking is not a safe substitute for IKE gateway lookup
- allow HA-related host-inbound services on the ICL zone
- if encrypting ICL, allow IKE and use the Junos HA link encryption model
- keep ICL RTT under the platform/release requirement for geo designs; the supplied sources use less than 100 ms as the design bound
- use redundant paths where possible
- do not assume ICL must be back-to-back; it can traverse routed infrastructure
- size the encrypted ICL for RTO/session-sync bursts, not just steady state; James Rathbun's field rule of thumb is roughly 1 Gbps per 100,000 concurrent sessions and keeping utilization below about 75% for resync and connection-per-second bursts

Minimal conceptual stanza:

```junos
set chassis high-availability local-id local-ip <LOCAL_ICL_IP>
set chassis high-availability peer-id <PEER_ID> peer-ip <PEER_ICL_IP>
set chassis high-availability peer-id <PEER_ID> interface <ICL_SOURCE_INTERFACE>
set chassis high-availability peer-id <PEER_ID> routing-instance <ICL_RI>
set chassis high-availability peer-id <PEER_ID> liveness-detection minimum-interval <MS>
set chassis high-availability peer-id <PEER_ID> liveness-detection multiplier <COUNT>
set chassis high-availability services-redundancy-group 0 peer-id <PEER_ID>
```

Security-zone example for an ICL interface:

```junos
set security zones security-zone ICL interfaces <ICL_INTERFACE>
set security zones security-zone ICL host-inbound-traffic system-services high-availability
set security zones security-zone ICL host-inbound-traffic system-services ssh
set security zones security-zone ICL host-inbound-traffic protocols all
```

For production, restrict host-inbound services and protocols to the exact required set. Do not copy broad lab `all` permissions without review.

## ICD: Inter-Chassis Datalink

ICD is an optional datapath used when asymmetric routing can deliver packets for one flow to different SRX nodes.

Use ICD when:

- ECMP or routed topology can produce asymmetry
- hybrid designs may send one direction to one node and return traffic to the other
- L7 inspection needs one node to see enough packets to classify or inspect a flow
- you cannot guarantee symmetric routing during normal or failure states
- multiple SRGs can be active on different nodes and create sustained cross-node, Z-mode-like forwarding

Design notes:

- prefer symmetric routing first
- use ICD deliberately when asymmetry is part of the design
- account for encapsulation overhead and MTU
- validate platform/release support for asymmetric flow and ICD behavior
- test with real application traffic, not only ping
- ICD may be used during the initial TCP 3-way handshake and while advanced inspection services need bidirectional visibility; do not assume every packet of every asymmetric flow will traverse ICD forever
- sustained cross-node flows with advanced inspection/plugin services are not a good steady-state design; engineer traffic so complete bidirectional flows normally land on one active node
- if ICD is down, asymmetric SYN/SYN-ACK or return traffic can fail even while synchronized sessions appear valid; check `show chassis high-availability data-plane statistics` and packet drops

ICD configuration pattern:

```junos
set chassis high-availability local-id local-forwarding-ip <LOCAL_ICD_IP>
set chassis high-availability peer-id <PEER_ID> peer-forwarding-ip <PEER_ICD_IP>
set chassis high-availability peer-id <PEER_ID> peer-forwarding-ip interface <ICD_INTERFACE.UNIT>
set chassis high-availability peer-id <PEER_ID> peer-forwarding-ip liveness-detection minimum-interval <MS>
set chassis high-availability peer-id <PEER_ID> peer-forwarding-ip liveness-detection multiplier <COUNT>
```

ICD verification:

```text
show chassis high-availability data-plane statistics
show security flow session source-prefix <SRC> destination-prefix <DST> pretty
show log messages | match "MNHA forward|re-route failed|reject NH|ICD"
```

(these strings come from flow traceoptions output — they appear in the configured security flow trace file, not the default messages log, unless traceoptions target messages)

Look for `ICD Data` counters when traffic is actually crossing the ICD. A valid Active/Warm session with packet counters split across nodes does not by itself prove the ICD is forwarding every packet.

## IPsec VPNs on MNHA with Multiple Routing Instances

Read the IPsec section of `references/mnha-advanced-workflows.md` before configuring synchronized VPNs. SRG1+, the floating loopback, physical underlay, security zone, routing instance, ICL context, and route advertisement must align; route leaking alone may not fix control-plane IKE gateway lookup.

## NAT, Proxy ARP, and Deterministic Routing

Read the NAT section of `references/mnha-advanced-workflows.md` before using translated addresses in an MNHA design. Keep policy and pools equivalent for stateful failover, prefer routed reachability over proxy ARP, and verify that egress selection and return routing remain deterministic on both nodes.

## Runtime Object and Session Synchronization

Read the runtime synchronization section of `references/mnha-advanced-workflows.md`. Confirm that important sessions appear as Active/Warm across the peers, and test takeover through the intended forwarding path before declaring stateful failover ready.

## Configuration Synchronization

Read the configuration synchronization section of `references/mnha-advanced-workflows.md`. Keep node-local interfaces and routing intentionally distinct while maintaining equivalent security policy, objects, NAT logic, profiles, and shared SRG behavior. Use the peer-sync pattern in `references/mnha-config-patterns.md`; never store real secrets in skill files, tickets, or chat.

## Hybrid MNHA with eBGP Pattern

Read the hybrid-routing section of `references/mnha-advanced-workflows.md` before coupling SRG state to route preference. Validate signal-route tables, route filters, metrics, BFD behavior, VIP ownership, ARP refresh, and both failover and failback convergence. Use the complete route-filtered examples in `references/mnha-config-patterns.md`.

## DHCP on MNHA

Read the DHCP section of `references/mnha-advanced-workflows.md`. Prefer relay to an external service; if local DHCP is required, use non-overlapping pools and node-local server identifiers because lease databases are not assumed to synchronize. Complete patterns are in `references/mnha-config-patterns.md`.

## Verification Checklist

Before production cutover:

- [ ] Platform and Junos release support verified in current Juniper docs.
- [ ] Deployment mode selected: routed, default-gateway, or hybrid.
- [ ] SRG usage documented: SRG0 only, SRG1+, or multiple SRGs.
- [ ] ICL reachability verified in the intended routing instance.
- [ ] ICL zone host-inbound services are restricted but sufficient.
- [ ] If ICL encryption is required, IKED/IPsec HA link encryption is validated before cutover.
- [ ] Shared security policy, NAT, application, and profile config are equivalent where stateful failover is expected.
- [ ] Node-specific routing/interface configuration is intentionally different and documented.
- [ ] Forwarding interface/logical-unit design is compatible with stateful failover expectations.
- [ ] Symmetric routing is preferred or ICD/asymmetric-flow design is explicitly validated.
- [ ] If advanced inspection services are in policy, steady-state cross-node/Z-mode forwarding has been eliminated or explicitly validated against Juniper support guidance.
- [ ] IPsec on MNHA uses SRG1+, has `managed-services ipsec`, and IKED/package requirements are verified for the Junos release.
- [ ] VPN floating loopbacks, ICL context, physical underlay interfaces, security zones, and routing instances align; IKE gateway lookup has been tested from both nodes.
- [ ] Intra-zone IKE/ESP policy exists when VPN traffic is received on a physical interface and terminates on a loopback in the same zone.
- [ ] Remote-access pools are common per SRG or split per active/active SRG design to prevent address collisions after failover.
- [ ] NAT/SNAT pools, route advertisements, and upstream next hops produce deterministic return paths; proxy ARP is avoided unless explicitly tested.
- [ ] Sessions show Active/Warm state across both nodes.
- [ ] BGP/OSPF/static route preference selects the intended node.
- [ ] BFD sessions are stable and timers are realistic for the platform.
- [ ] SRG1+ VIPs install only on the active node.
- [ ] Signal-route export policy uses explicit route filters.
- [ ] Failover tests cover single-link, dual-link, node reboot, ICL loss, and failback/preemption if used.
- [ ] DHCP uses relay when possible; if local DHCP is used, pools are split and non-overlapping.

## Troubleshooting Commands

MNHA state:

```text
show chassis high-availability information
show chassis high-availability services-redundancy-group 0
show chassis high-availability services-redundancy-group <SRG>
show configuration chassis high-availability | display set
```

ICL and HA liveness:

```text
show route <PEER_ICL_IP>
ping routing-instance <ICL_RI> <PEER_ICL_IP>
show security ipsec security-associations    # only when ICL encryption is enabled
show security ike security-associations      # only when ICL encryption is enabled
```

Session, IPsec, routing, VIP, and DHCP checks are listed inline in their sections above.

## Common Pitfalls

1. Treating MNHA like chassis cluster. MNHA nodes are independent devices with synchronized runtime state, not one logical chassis.

2. Forgetting configuration synchronization. Security policy and NAT differences can break stateful failover even when sessions synchronize.

3. Building routed MNHA but allowing asymmetric flows accidentally. Prefer symmetry; use ICD only when planned and tested.

4. Using broad lab security settings in production. Avoid `default-policy permit-all`, `host-inbound all`, or broad direct-route export unless explicitly intended.

5. Exporting too many routes from signal-route policy. Put route filters on every accept term.

6. Using production prefixes as signal routes. Use reserved, non-routed, non-conflicting prefixes.

7. Assuming BFD timers from a lab are safe everywhere. Tune timers per hardware, topology, and operational tolerance.

8. Enabling preemption without testing routing readiness. Failback can blackhole traffic if SRG ownership returns before BGP/forwarding is converged.

9. Assuming DHCP state is shared. For local DHCP, split pools and use node-specific server identifiers; prefer relay when possible.

10. Ignoring ICL security and reachability. If ICL fails, sync fails; if ICL is exposed, HA state can become a security risk.

11. Anchoring MNHA IPsec on a floating loopback in a different routing instance from the ICL/MNHA context. IKE gateway lookup is control-plane/self-traffic behavior; route leaking that fixes transit traffic may not fix IKE.

12. Putting the VPN loopback and receiving physical interface in different security zones. The tunnel can fail with reroute errors even when basic IP reachability exists.

13. Assuming `process-packet-on-backup` or ICD makes all asymmetric designs safe. Advanced inspection services need bidirectional visibility; sustained cross-node flows should be engineered out of steady state.

14. Using proxy ARP for NAT pool reachability as if MNHA were chassis cluster. Both independent nodes can answer ARP, and return traffic can land on the wrong node.

15. Reusing the same remote-access address pool across independently active SRGs without splitting ranges. Failover may preserve a pool, but active/active SRGs can collide.

16. Forgetting to dissolve `groups node0` / `groups node1`. On a chassis cluster those per-node groups carried node-specific config; on MNHA each node is a standalone device, so that config must become direct `system`/interface configuration on the respective node. Leaving it as `apply-groups node0/node1` (which has no cluster context to key on) drops the settings.

17. Forgetting that management/enrollment identity is per-node. `outbound-ssh`, EMS, and Security Director Cloud `device-id` are node-local: after migration each SRX re-enrolls as a **separate** managed device. Plan the re-enrollment and update inventory/licensing per node rather than expecting the cluster's single managed-device identity to carry over.

18. Leaving a stray static default route via an unzoned management/extra leg — black-holes transit return traffic. See Field-Confirmed Behaviors below.

19. Using the flat `local-id local-ip` / `peer-id peer-ip` config on Junos 26.x. It commits but never activates (*mode not configured*); 26.x needs the grid model plus a reboot. See "Config model: flat vs grid".

20. Omitting `activeness-probe dest-ip <X> src-ip <Y>` on an SRG with `deployment-type routing` — commit fails `activeness-probe … mandatory`. `src-ip` is a sub-field of `dest-ip`, one statement.

21. A signal-route export policy that re-advertises only learned routes and forgets the node's own **connected transit subnets** — the far side can't route back to on-transit sources (SNAT addresses, downstream transit IPs) and return traffic black-holes. Add a `from protocol direct … route-filter <transit> exact accept` term.

22. Assuming a configured SRG1 always elects a single active. If cold-sync doesn't converge, both nodes self-elect ACTIVE (active/active); routing failover still works but stateful sync does not. Check `Conn State`/`Cold Sync Status`, not just `Node Status`. **Before accepting non-convergence, rule out the ICL zone missing `host-inbound-traffic protocols bfd`** — BFD is a protocol, not a system-service, so a zone permitting `system-services high-availability` passes ICMP and silently drops the liveness BFD, producing identical symptoms.

23. Leaving `fxp0` on DHCP on a node whose failover depends on a BGP-learned default — the DHCP default (Access-internal, pref 12) beats BGP (170) and black-holes transit. Make `fxp0` static.

## Field-Confirmed Behaviors

Full write-ups live in `references/mnha-grid-model-field-notes.md`; the pitfalls
above index them. Confirmed on live pairs:

- vSRX3 24.4R1.9 hybrid pair ([issue #7](https://github.com/mechubsec/fwskillsshare/issues/7)):
  an unzoned-leg static default black-holes transit (pitfall 18); the backup node
  does not service SRG data traffic (`Process Packet In Backup State: NO` is
  expected, not a fault); the `high-availability` host-inbound knob commit-checks
  clean.
- vSRX 26.2R1.7 routed pairs (grid model, eBGP + signal-route MED steering):
  grid model + reboot required on 26.x (pitfall 19); failed cold-sync leaves both
  nodes self-elected ACTIVE — routing failover survives, stateful sync does not
  (pitfall 22); signal-route export must include connected transit subnets
  (pitfall 21); active/active SNAT wants per-node pools + proxy-ARP addresses;
  `fxp0` on DHCP black-holes transit (pitfall 23); on KVM/Proxmox a soft reboot
  can leave the vSRX dataplane un-enumerated and chassis-cluster mode never forms
  its control link — MNHA was the only workable HA model there.

## Source Notes

This original operational playbook was informed by five attributed Juniper
Community TechPosts by James Rathbun, Steven Jacques, and Laurent Paumelle.
Concise `Inspired by` notes under `references/` preserve source links,
release-specific cautions, and verification implications without reproducing
the articles.

Sections on chassis-cluster interface migration, SRG monitor-object syntax, and pitfalls 16-23 are field/QA additions beyond the five source articles; live-verified items are called out in Field-Confirmed Behaviors. The "Config model: flat vs grid" section, the routed-mode single-gateway caveat, and the vSRX-26.2 behaviors come from a 2026-07 deployment of two routed MNHA pairs on vSRX 26.2R1.7 (grid model, SRG1 deployment-type routing, eBGP + signal-route MED steering); the grid syntax is release-dependent, so verify against the target release.

Per user instruction, ambiguous or conflicting article details were not encoded as hard guidance. Where support depends on platform or Junos release, this skill points operators to current Juniper documentation instead of freezing a source-specific matrix.

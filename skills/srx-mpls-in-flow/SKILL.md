---
name: srx-mpls-in-flow
description: Design, configure, audit, and troubleshoot Juniper SRX MPLS L3VPN in flow mode. Use when handling Junos 24.2R1+ family mpls with inet or inet6 flow, secure PE or CPE, VRFs, LDP, MP-BGP, l3vpn vrf-group policy, VRF-to-zone mapping, VRF-aware NAT or AppID, PowerMode or RFP, MTU, labels, or policy matching.
version: 1.0.5
author:
  - fastrevmd-lab
  - Claude
  - GPT
license: MIT
metadata:
  hermes:
    tags: [srx, junos, mpls, l3vpn, flow-mode, vrf, vrf-to-zone, bgp, ldp, nat, appid, powermode]
    related_skills: [parsing-srx-configs, srx-policy, srx-nat]
  sources:
    - title: SRX MPLS in Flow
      author: Karel Hendrych
      url: https://community.juniper.net/blogs/karel-hendrych/2025/08/01/srx-mpls-in-flow
      retrieved: "2026-05-14"
    - title: SRX MPLS in Flow - Part 2
      author: Karel Hendrych
      url: https://community.juniper.net/blogs/karel-hendrych/2026/04/22/srx-mpls-in-flow-part-2?CommunityKey=44efd17a-81a6-4306-b5f3-e5f82402d8d3
      retrieved: "2026-05-14"
---

# SRX MPLS in Flow

## Contents

- [Overview](#overview)
- [Scope and routing](#scope-and-routing)
- [Runtime intake](#runtime-intake)
- [Version and Platform Notes](#version-and-platform-notes)
- [Forwarding Mode Baselines](#forwarding-mode-baselines)
- [Minimal MPLS L3VPN Building Blocks](#minimal-mpls-l3vpn-building-blocks)
- [Security Zones and Host-Inbound](#security-zones-and-host-inbound)
- [Security Policy Models](#security-policy-models)
- [VRF-Aware NAT and AppID](#vrf-aware-nat-and-appid)
- [PowerMode / RFP Guidance](#powermode--rfp-guidance)
- [Verification Workflow](#verification-workflow)
- [Troubleshooting Matrix](#troubleshooting-matrix)
- [Common Pitfalls](#common-pitfalls)
- [Verification Checklist](#verification-checklist)
- [Source Notes](#source-notes)

## Overview

Junos 24.2R1 introduced a cleaner SRX forwarding model for MPLS security use cases: keep `family mpls` in packet mode while processing `family inet` and `family inet6` in SRX flow mode. That lets an SRX act as an MPLS L3VPN PE/CPE and still apply stateful firewall, NAT, AppID, IPS/IDP, and other flow services to customer IPv4/IPv6 traffic.

The operational pattern is:

1. Configure the SRX to process `family mpls` packet-based, leaving inet/inet6 flow-based.
2. Build the MPLS underlay with larger MTU, loopbacks, IGP, LDP or RSVP/BGP-LU, and MP-BGP `family inet-vpn`.
3. Define VRFs with route distinguisher, vrf-target, and SRX-required `vrf-table-label` when local VRF interfaces exist.
4. Bind customer interfaces into VRFs.
5. Apply SRX security policy and NAT using either:
   - Junos 24.2 style L3VPN VRF group match conditions, or
   - Junos 25.4R1+ VRF-to-zone mapping where supported.
6. Verify forwarding mode, MPLS labels, VPN routes, policy hits, sessions, NAT/AppID, and packet captures.

Do not treat this as "global packet mode MPLS." The value is that only MPLS label switching remains packet-based while the inner customer traffic can enter normal SRX flow processing.

## Scope and routing

Use this skill only for MPLS or VRF flow-mode behavior. Use `parsing-srx-configs` for full-config extraction, `srx-policy` for non-VRF policy design, and `srx-nat` for NAT outside MPLS contexts.

## Runtime intake

Before starting the workflow, inspect the request, supplied artifacts, and
available approved read-only evidence. If unresolved facts could materially
change safety, scope, correctness, confidence, or the requested output, read
`references/runtime-intake.md`.

For each unresolved material fact whose catalog condition is true, invoke Claude `AskUserQuestion` or Codex `request_user_input` before continuing or issuing an open-ended request.
Ask at most three single-select catalog questions per round. After each response, ask another round whenever any unresolved material catalog condition remains true; continue only when none remain. Do not repeat answered questions or show the full catalog.
Without a native tool, present each selected catalog question with its 2-3 labeled choices and a free-text `Other` path in concise plain text; do not substitute a generic checklist.

Never request secrets or unredacted customer data. Treat intake answers as task
context, not approval for a live change; obtain separate explicit approval
before configuration, commit, upgrade, reboot, delete, or failover actions.

## Version and Platform Notes

Always verify the current Junos release notes, Feature Explorer, and platform documentation before committing a production design. Based on the source articles:

- Junos 24.2R1 introduced the decoupled treatment of `family mpls` versus `family inet` and `family inet6` for selected SRX platforms.
- The older explicit flow mode for `family mpls` use cases on vSRX3, available from Junos 21.4 for specific PE cases, is deprecated in favor of decoupled family controls.
- Platforms called out for the new MPLS/flow model include SRX300 series, SRX1500, SRX4100/4200, SRX1600/SRX2300/SRX4120/SRX4300, SRX4600/SRX4700 as of Junos 25.4, and vSRX.
- As of the source articles, global packet mode is not supported on newer mid-range SRX1600/SRX2300/SRX4120/SRX4300, SRX4600/4700, and SRX5K platforms.
- Per the community blog source (Karel Hendrych, "SRX MPLS in flow"; Juniper's release note does not list platforms), global packet mode remains supported on SRX300 series, SRX1500, vSRX, and SRX4100/4200. Verify platform support in Juniper Feature Explorer before relying on it.
- **Upgrade trap (24.2R1+):** before 24.2R1, `set security forwarding-options family mpls mode packet-based` also put IPv4 into packet mode. From 24.2R1 each family is set separately and IPv4/IPv6 default to flow mode. Per the 24.2R1 SRX known limitations: "to restore IPv4 to packet mode, you must configure `set security forwarding-options family inet mode packet-based`. Commit the configuration and reboot the device for the change to take effect." Do this only if packet-mode IPv4 is intended; a commit alone is not enough. Source (HTTP 200, checked 2026-10-09): https://www.juniper.net/documentation/us/en/software/junos/release-notes/24.2/junos-release-notes-24.2r1/topics/known-limitations/srx-known-limitations-24.2r1.html
- Junos 25.4R1 adds SRX4600/SRX4700 MPLS L3VPN support and VRF-to-zone mapping support used by Part 2 of the source material.
- On SRX4600/SRX4700, MPLS traffic is not Express Path accelerated as of 25.4R1, but the hardware PFE can load-balance toward SPU resources by hashing on inner IP/L4 headers rather than only MPLS labels.

## Forwarding Mode Baselines

### MPLS-in-flow PE / secure CPE

Use this model when the SRX must be a PE/CPE and inspect or NAT customer traffic:

```junos
set security forwarding-options family mpls mode packet-based
```

Expected status:

```text
show security flow status

Flow forwarding mode:
Inet forwarding mode: flow based
Inet6 forwarding mode: flow based
MPLS forwarding mode: packet based
ISO forwarding mode: drop
```

This means MPLS label handling is packet-based while IPv4/IPv6 payload traffic can be statefully processed.

### Pure MPLS router / P node

Use packet mode for all relevant families when the SRX is being used as a lab or transit router and should not statefully inspect traffic:

```junos
set security forwarding-options family inet mode packet-based
set security forwarding-options family inet6 mode packet-based
set security forwarding-options family mpls mode packet-based
set security forwarding-options family iso mode packet-based
```

A classical P-router usually does not need VRFs; it can transit VPN labels through `inet.3`, `mpls.0`, and `bgp.l3vpn.0`. The source lab used VRFs on the transit vSRX for visibility, not because a normal P-router requires them.

## Minimal MPLS L3VPN Building Blocks

### Interfaces and MTU

Increase the MPLS-facing MTU so labeled traffic fits. In virtual labs, also increase the VM NIC and Linux bridge MTU.

```junos
set interfaces ge-0/0/0 mtu 1600
set interfaces ge-0/0/0 unit 0 family inet address 10.0.1.1/24
set interfaces ge-0/0/0 unit 0 family mpls
set interfaces lo0 unit 0 family inet address 1.1.1.1/32
```

Customer-facing interfaces can be normal routed or VLAN-tagged units and may reuse overlapping addresses when placed in different VRFs:

```junos
set interfaces ge-0/0/1 vlan-tagging
set interfaces ge-0/0/1 unit 10 vlan-id 10
set interfaces ge-0/0/1 unit 10 family inet address 10.0.0.1/24
set interfaces ge-0/0/1 unit 11 vlan-id 11
set interfaces ge-0/0/1 unit 11 family inet address 10.0.0.1/24
```

### VRFs

For each L3VPN VRF on SRX, configure instance type, interface binding, route distinguisher, route target, and `vrf-table-label`:

```junos
set routing-instances vrf-1 instance-type vrf
set routing-instances vrf-1 interface ge-0/0/1.10
set routing-instances vrf-1 route-distinguisher 65500:1
set routing-instances vrf-1 vrf-target target:65500:1
set routing-instances vrf-1 vrf-table-label

set routing-instances vrf-2 instance-type vrf
set routing-instances vrf-2 interface ge-0/0/1.11
set routing-instances vrf-2 route-distinguisher 65500:2
set routing-instances vrf-2 vrf-target target:65500:2
set routing-instances vrf-2 vrf-table-label
```

On SRX, `vrf-table-label` is required for these MPLS L3VPN local-interface use cases. Together with route targets, it lets traffic to and from local VRF interfaces be processed in the correct VRF.

### IGP, LDP/MPLS, and MP-BGP

Use an IGP to carry loopbacks, LDP or other label distribution for transport labels, and MP-BGP for VPNv4 routes.

```junos
set protocols ospf area 0.0.0.0 interface lo0.0 passive
set protocols ospf area 0.0.0.0 interface ge-0/0/0.0 interface-type p2p
set protocols ldp interface ge-0/0/0.0
set protocols mpls interface ge-0/0/0.0

set protocols bgp group mp-bgp type internal
set protocols bgp group mp-bgp local-address 1.1.1.1
set protocols bgp group mp-bgp family inet-vpn unicast
# add for IPv6 (VPNv6) L3VPN:
set protocols bgp group mp-bgp family inet6-vpn unicast
set protocols bgp group mp-bgp neighbor 1.1.1.2
set routing-options autonomous-system 65500
```

RSVP-signaled LSPs and BGP-LU are possible alternatives, but the source examples focus on LDP-signaled MPLS.

## Security Zones and Host-Inbound

For Junos 24.2 style policy matching, the MPLS underlay interface is commonly in an `mpls` zone. Local VRF interfaces can be placed in VRF-specific zones.

```junos
set security zones security-zone mpls interfaces lo0.0 host-inbound-traffic system-services ping
set security zones security-zone mpls interfaces lo0.0 host-inbound-traffic protocols ldp
set security zones security-zone mpls interfaces lo0.0 host-inbound-traffic protocols bgp
set security zones security-zone mpls interfaces ge-0/0/0.0 host-inbound-traffic system-services ping
set security zones security-zone mpls interfaces ge-0/0/0.0 host-inbound-traffic protocols ospf
set security zones security-zone mpls interfaces ge-0/0/0.0 host-inbound-traffic protocols ldp

set security zones security-zone vrf-1 interfaces ge-0/0/1.10 host-inbound-traffic system-services ping
set security zones security-zone vrf-2 interfaces ge-0/0/1.11 host-inbound-traffic system-services ping
```

Do not over-permit host-inbound services in production. The examples are intentionally minimal lab scaffolding; restrict source prefixes and protocols for real deployments.

## Security Policy Models

### Junos 24.2 style: L3VPN VRF group policy matching

Create L3VPN VRF groups for use in policy and NAT match conditions:

```junos
set security l3vpn vrf-group vrf-1 vrf vrf-1
set security l3vpn vrf-group vrf-2 vrf vrf-2
```

Permit customer traffic from local VRF interface zone toward MPLS only when the destination VPN context matches:

```junos
set security policies from-zone vrf-1 to-zone mpls policy vrf-1 match source-address any
set security policies from-zone vrf-1 to-zone mpls policy vrf-1 match destination-address any
set security policies from-zone vrf-1 to-zone mpls policy vrf-1 match application any
set security policies from-zone vrf-1 to-zone mpls policy vrf-1 match dynamic-application any
set security policies from-zone vrf-1 to-zone mpls policy vrf-1 match destination-l3vpn-vrf-group vrf-1
set security policies from-zone vrf-1 to-zone mpls policy vrf-1 then permit
```

Permit return or remote-originated VPN traffic from MPLS toward the local VRF interface only when the source VPN context matches:

```junos
set security policies from-zone mpls to-zone vrf-1 policy vrf-1 match source-address any
set security policies from-zone mpls to-zone vrf-1 policy vrf-1 match destination-address any
set security policies from-zone mpls to-zone vrf-1 policy vrf-1 match application any
set security policies from-zone mpls to-zone vrf-1 policy vrf-1 match dynamic-application any
set security policies from-zone mpls to-zone vrf-1 policy vrf-1 match source-l3vpn-vrf-group vrf-1
set security policies from-zone mpls to-zone vrf-1 policy vrf-1 then permit
```

Repeat for each VRF. This prevents accidental cross-VRF traffic from being permitted even if route leaking is configured elsewhere.

Keep a final deny/reject policy with counters/logging appropriate to the environment:

```junos
set security policies global policy reject match source-address any
set security policies global policy reject match destination-address any
set security policies global policy reject match application any
set security policies global policy reject match dynamic-application any
set security policies global policy reject then reject
```

### Junos 25.4R1+ style: VRF-to-zone mapping

Where supported, bind a VRF directly to a security zone. This sets VRF context by zone and simplifies policy construction.

```junos
set security zones security-zone vrf-1-ext vrf vrf-1
set security zones security-zone vrf-2-ext vrf vrf-2
```

Use normal zone policies between internal interface zones and external VRF-bound zones:

```junos
set security policies from-zone vrf-1-int to-zone vrf-1-ext policy vrf-1-int-ext match source-address any
set security policies from-zone vrf-1-int to-zone vrf-1-ext policy vrf-1-int-ext match destination-address any
set security policies from-zone vrf-1-int to-zone vrf-1-ext policy vrf-1-int-ext match application any
set security policies from-zone vrf-1-int to-zone vrf-1-ext policy vrf-1-int-ext then permit

set security policies from-zone vrf-1-ext to-zone vrf-1-int policy vrf-1-ext-int match source-address any
set security policies from-zone vrf-1-ext to-zone vrf-1-int policy vrf-1-ext-int match destination-address any
set security policies from-zone vrf-1-ext to-zone vrf-1-int policy vrf-1-ext-int match application any
set security policies from-zone vrf-1-ext to-zone vrf-1-int policy vrf-1-ext-int then permit
```

Important limitation from the source article: as of 25.4R1, VRF-to-zone mapping does not permit mixing interfaces and VRFs inside the same zone, so you cannot always collapse the policy to a simple intrazone match.

For NAT use cases, the VRF-groups approach still applies as of 25.4R1.

## VRF-Aware NAT and AppID

Use VRF-aware NAT when overlapping spaces or per-VRF translation are required.

Source NAT example:

```junos
set security nat source pool pool-1 address 10.10.3.10/32
set security nat source rule-set snat-1 from zone vrf-1
set security nat source rule-set snat-1 to routing-group vrf-1
set security nat source rule-set snat-1 rule src-nat-1 match source-address 10.0.3.0/24
set security nat source rule-set snat-1 rule src-nat-1 then source-nat pool pool-1
```

Static NAT example pattern:

```junos
set security nat static rule-set static-1 from routing-group vrf-2
set security nat static rule-set static-1 rule static-1 match destination-address 10.10.3.10/32
set security nat static rule-set static-1 rule static-1 then static-nat prefix 10.0.3.10/32
set security nat static rule-set static-1 rule static-1 then static-nat prefix routing-instance vrf-2
```

When using AppID, the source material recommends logging sessions that cannot be identified and remain in the pre-identification stage:

```junos
set security policies pre-id-default-policy then log session-close
set security policies pre-id-default-policy then log session-update 1
```

Verify with the session/NAT/hit-count commands in Verification Workflow steps 4 and 6, looking for:

- policy name and zone direction
- `L3VPN VRF Group` or `VRF Zone` annotations
- translated source/destination IP and port behavior
- `Dynamic application: junos:<APP>`
- packet and byte counters on both wings

## PowerMode / RFP Guidance

Traffic subjected to MPLS handling is processed in SRX Regular Flow Path (RFP), not PowerMode (PM). On x86-based SRX platforms, PM is enabled by default since Junos 21.3. If the device is dedicated to MPLS-in-flow traffic, disabling PM can avoid the overhead of checking whether traffic is eligible for PM:

```junos
set security flow power-mode-disable
```

Do not apply this blindly. Keep PM enabled if the SRX also carries non-MPLS workloads that benefit from it, especially IPsec where PowerMode IPsec may materially improve performance.

Verify whether a session is in PM:

```text
show security flow status
show security flow session destination-port <PORT> extensive
```

In extensive session output, check each wing for:

```text
Power-Mode Active: False
```

Part 2 observed that SRX4600 MPLS L3VPN throughput can approach the platform PFE-SPU interlink limit for large frames in controlled testing, and single-flow packet rate depends on CPU/SPU limits and PM status. Treat those figures as lab data, not a deployment guarantee. Real-world performance depends on packet size mix, connection setup/teardown rate, enabled services, AppID/IPS/NAT/logging, and traffic symmetry.

For arbitrary performance tests, disabling drop-flow may avoid misleading log/session load from denied tester traffic:

```junos
set security flow drop-flow max-sessions 0
```

## Verification Workflow

### 1. Forwarding mode

```text
show security flow status
```

Expected: the MPLS-in-flow baseline shown in Forwarding Mode Baselines (inet/inet6 flow based, MPLS packet based, ISO drop).

### 2. MPLS and label distribution

```text
show mpls interface
show mpls lsp
show ldp neighbor
show route table inet.3
show route table mpls.0
```

Check that MPLS-facing interfaces are up, labels are installed, and transport labels resolve toward PE loopbacks.

### 3. MP-BGP VPN routes

```text
show bgp summary
show route advertising-protocol bgp <PEER> table bgp.l3vpn.0
show route table bgp.l3vpn.0
show route table vrf-1.inet.0
show route table vrf-2.inet.0
```

Check route distinguishers, route targets, next-hop recursion, and imported/exported VRF routes.

### 4. Policy and NAT

```text
show security policies hit-count
show security flow session
show security flow session extensive
show security nat source rule all
show security nat static rule all
```

Check that traffic matches the intended VRF-aware policy and NAT rule, not a broad fallback.

### 5. Packet capture

On Junos or attached lab bridges, confirm MPLS labels on the underlay and plain customer packets on access-facing links:

```text
monitor traffic interface <MPLS_IFL> matching "mpls" no-resolve
monitor traffic interface <ACCESS_IFL> no-resolve
```

In Linux/KVM labs:

```bash
tcpdump -n -i <bridge> mpls
tcpdump -n -i <bridge> host <customer-ip>
```

### 6. Application identification

```text
show security flow session dynamic-application junos:SSH
show services application-identification statistics applications
show log messages | match pre-id
```

Verify unidentified or pre-ID sessions are not silently bypassing intended controls.

## Troubleshooting Matrix

| Symptom | Likely cause | Checks / fix |
|---|---|---|
| `MPLS forwarding mode` is not packet based | Missing forwarding-options stanza or wrong platform/release | Configure `set security forwarding-options family mpls mode packet-based`; confirm platform/Junos support |
| Customer traffic bypasses policy | Device is in global packet mode or traffic is not entering flow path | Check `show security flow status`; ensure inet/inet6 are flow based |
| IPv4 traffic unexpectedly flow-processed (or bypassing flow) after upgrade to 24.2R1+ | Pre-24.2 `family mpls mode packet-based` silently set IPv4 to packet mode too; 24.2R1+ defaults inet/inet6 to flow | If packet-mode IPv4 is intended, set `family inet mode packet-based`, commit, and reboot (24.2R1 SRX known limitations); otherwise leave inet in flow |
| VRF local interface traffic fails | Missing `vrf-table-label`, route target mismatch, interface not bound to VRF | Check VRF config and `show route table <vrf>.inet.0` |
| VPN routes are absent | MP-BGP not established, missing `family inet-vpn`, next-hop unresolved, route-target mismatch | Check `show bgp summary`, `bgp.l3vpn.0`, `inet.3`, route targets |
| MPLS labels absent on wire | LDP/MPLS not enabled on interface, IGP loopback reachability broken, MTU problem | Check `show ldp neighbor`, `show mpls interface`, captures, MTU |
| Policy does not match expected VRF | Missing L3VPN VRF group match or wrong VRF-to-zone mapping | Inspect policy terms and session annotations for `L3VPN VRF Group` / `VRF Zone` |
| Cross-VRF traffic unexpectedly works | Broad global policy, route leaking plus no VRF match condition | Add source/destination L3VPN VRF group constraints or VRF-to-zone separation |
| NAT in VRF context fails | Missing routing-instance/l3vpn-vrf-group condition or missing route export for NAT pool | Check NAT rule-set match conditions and exported NAT pool routes |
| AppID remains unknown/pre-ID | Signatures/licensing/software missing, short flows, resource pressure | Check AppID package/license, pre-ID logging, session details |
| Poor MPLS performance | PM eligibility overhead, services enabled, small packets, flow setup load, platform bottleneck | Compare PM on/off carefully; check SPU/core load and feature set |
| Denied test traffic creates excessive load | Drop-flow/logging behavior during synthetic tests | Consider `set security flow drop-flow max-sessions 0` for testing only |
| VRF-to-zone policy cannot be simplified | 25.4R1 limitation: no mixing VRFs and interfaces in one zone | Keep separate internal interface zones and external VRF-bound zones |

## Common Pitfalls

1. Confusing MPLS packet-based forwarding with global packet mode. The design relies on MPLS being packet-based and inet/inet6 staying flow-based.

2. Forgetting `vrf-table-label` on SRX VRFs with local interfaces. This is mandatory in the source SRX L3VPN examples.

3. Treating route leaking as policy permission. Routing reachability and security policy permission are separate; use VRF-aware policy matches to prevent accidental cross-VRF access.

4. Copying lab-wide `any` policies into production. The source configs are demonstration scaffolding. Replace broad source/destination/application matches with real controls.

5. Assuming VRF-to-zone mapping eliminates VRF-aware NAT needs. As of 25.4R1, NAT use cases still use the VRF-groups approach.

6. Forgetting MTU outside Junos. In virtual labs, configure the vSRX interface, VM NIC, and Linux bridge for MPLS headroom.

7. Disabling PowerMode without considering other workloads. PM may not help MPLS RFP traffic, but it can help non-MPLS and IPsec traffic.

8. Using SRX4600/SRX4700 performance numbers as guaranteed sizing. The source figures are controlled lab results; production sizing must include services, traffic mix, concurrent sessions, logging, and failure modes.

## Verification Checklist

- [ ] Confirm Junos release and SRX platform support for MPLS L3VPN in flow mode.
- [ ] Confirm `show security flow status` has inet/inet6 flow based and MPLS packet based.
- [ ] Confirm MPLS-facing interfaces have sufficient MTU and `family mpls`.
- [ ] Confirm loopback reachability through IGP and LDP/transport-label state.
- [ ] Confirm MP-BGP `family inet-vpn` is established and VPN routes import/export correctly.
- [ ] Confirm each VRF has the intended RD, route target, interface binding, and `vrf-table-label`.
- [ ] Confirm security policy uses L3VPN VRF group matching or supported VRF-to-zone mapping.
- [ ] Confirm NAT rules include the correct VRF/routing-instance context when NAT is used.
- [ ] Confirm policy hit counters, session details, NAT translations, and AppID output match the intended VRF.
- [ ] Confirm packet capture shows MPLS labels on the underlay and customer packets on access interfaces.
- [ ] Confirm PowerMode/drop-flow choices are deliberate and documented for the workload.

## Source Notes

This skill is synthesized from two Juniper Community TechPosts by Karel Hendrych:

- `references/source-srx-mpls-in-flow-part-1.md` - Junos 24.2R1 MPLS/flow-mode behavior, vSRX L3VPN lab, VRF-aware policy, NAT/AppID, verification, and appendices.
- `references/source-srx-mpls-in-flow-part-2.md` - Junos 25.4R1 SRX4600/SRX4700 platform support, VRF-to-zone mapping, SRX4600 performance testing, PowerMode observations, and physical-lab configs.
- `references/source-index.md` - reference index.

The main playbook intentionally extracts reusable operational guidance instead of mirroring the full articles.

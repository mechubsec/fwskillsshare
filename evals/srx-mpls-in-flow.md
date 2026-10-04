# srx-mpls-in-flow evals

Run each scenario in a fresh agent session with the skill installed, then again without it as a baseline. A scenario passes only when every "Must" holds and no "Must not" occurs.

## Scenario 1: Forwarding mode verification

**Prompt:** Verify this SRX is correctly configured for MPLS PE with flow-based security.

**Input:**
```
show security flow status:
Flow forwarding mode:
Inet forwarding mode: packet based
Inet6 forwarding mode: packet based
MPLS forwarding mode: packet based
```

**Must:**
- Identify that inet/inet6 are in packet mode (wrong for flow-based security)
- State the correct MPLS-in-flow mode requires: inet flow-based, inet6 flow-based, MPLS packet-based
- Recommend `set security forwarding-options family mpls mode packet-based` only (leave inet/inet6 default flow-based)
- Explain that this decoupled treatment keeps MPLS label switching packet-based while customer traffic uses flow services
- Reference "MPLS-in-flow PE / secure CPE" baseline

**Must not:**
- Claim this is correct MPLS-in-flow configuration (inet/inet6 must be flow-based)
- Suggest global packet mode for PE/CPE use case (loses stateful inspection)
- Recommend setting inet/inet6 to packet-based when flow services are needed

## Scenario 2: VRF-table-label requirement

**Prompt:** VRF routes are installed but local VRF interface traffic fails. Why?

**Input:**
```
VRF config:
set routing-instances vrf-1 instance-type vrf
set routing-instances vrf-1 interface ge-0/0/1.10
set routing-instances vrf-1 route-distinguisher 65500:1
set routing-instances vrf-1 vrf-target target:65500:1

MP-BGP shows VPNv4 routes exchanged.
Local traffic to/from ge-0/0/1.10 fails.
```

**Must:**
- Identify missing `vrf-table-label` statement
- State that `vrf-table-label` is REQUIRED on SRX for MPLS L3VPN local-interface use cases
- Explain it lets traffic to/from local VRF interfaces be processed in correct VRF
- Recommend adding `set routing-instances vrf-1 vrf-table-label`
- Reference "VRFs" minimal building blocks section

**Must not:**
- Claim route-target or RD is wrong (those are correctly configured)
- Suggest this is a routing issue (it's VRF label allocation for local interfaces)
- Skip the requirement for PE/CPE with local VRF interfaces

## Scenario 3: VRF-to-zone policy matching

**Prompt:** Configure security policy for VRF-1 traffic egressing to MPLS core on Junos 24.2.

**Input:**
```
VRF: vrf-1
Customer interface zone: vrf-1
MPLS core zone: mpls
Junos: 24.2R1
```

**Must:**
- Use L3VPN VRF group policy matching (Junos 24.2 style)
- Create `set security l3vpn vrf-group vrf-1 vrf vrf-1`
- Add policy with `match destination-l3vpn-vrf-group vrf-1` (vrf-1 to mpls) and `match source-l3vpn-vrf-group vrf-1` (mpls to vrf-1)
- Explain this prevents accidental cross-VRF traffic even if route leaking exists
- Reference "Junos 24.2 style: L3VPN VRF group policy matching" section

**Must not:**
- Use VRF-to-zone mapping (requires Junos 25.4R1+, not available on 24.2)
- Omit VRF group match conditions (allows cross-VRF leakage)
- Claim zone matching alone is sufficient (must also match VPN context)

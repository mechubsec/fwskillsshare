# srx-autovpn-full-tunnel evals

Run each scenario in a fresh agent session with the skill installed, then again without it as a baseline. A scenario passes only when every "Must" holds and no "Must not" occurs.

## Scenario 1: Spoke default route recursion

**Prompt:** My AutoVPN tunnel shows UP but all spoke traffic stops after setting `0.0.0.0/0 → st0.0`. What broke?

**Input:**
```
Spoke config:
set routing-options static route 0.0.0.0/0 next-hop st0.0
set security ipsec vpn SPOKE-VPN ike gateway SPOKE-GW

Hub WAN IP: 203.0.113.1
Spoke WAN: 198.51.100.2/30, next-hop 198.51.100.1

show security ike security-associations (shows tunnel DOWN or flapping)
```

**Must:**
- Identify missing anti-recursion host route as the #1 gotcha
- Explain that ESP packets to hub WAN must NOT follow default into st0 (infinite recursion)
- Recommend adding `203.0.113.1/32 → 198.51.100.1` more-specific than default
- State this host route is CRITICAL for full-tunnel backhaul
- Reference the "Anti-recursion is the #1 gotcha" section

**Must not:**
- Suggest removing the st0.0 default route (full tunnel requires it)
- Recommend lowering MTU/MSS as the fix (it's a routing loop, not fragmentation)
- Commit configuration without explicit approval per runtime-intake

## Scenario 2: Version constraint PSK commit error

**Prompt:** Configure AutoVPN full-tunnel on vSRX 24.4R1.9 with one hub and three spokes using PSK.

**Input:** None

**Must:**
- State that `dynamic ike-user-type` (group-ike-id or shared-ike-id) + IKEv2 + PSK does NOT commit on 24.4R1+/25.4R1
- Cite the commit error: "When dynamic ike-user-type is configured, IKEv2 with authentication-method pre-shared-key is not allowed"
- Offer two paths: (1) per-spoke IKEv2 gateways on hub (PSK, no zero-touch) OR (2) certificate auth with group-ike-id
- Note the original reference lab (Junos 23.2R2) committed group-ike-id + PSK; treat as legacy-image-only
- Reference the version-constraint callout in the skill

**Must not:**
- Provide group-ike-id + PSK configuration without warning it will fail commit
- Claim this is a bug (it's a documented version constraint)
- Suggest downgrading Junos without explicit risk acknowledgment

## Scenario 3: NAT-T 4500 retransmit loop

**Prompt:** Hub shows tunnel UP; spoke IKE_SA_INIT (port 500) completes but IKE_AUTH on port 4500 retransmits forever. Single NAT hop (carrier PAT only). What's wrong?

**Input:**
```
Spoke config:
set security zones security-zone untrust interfaces ge-0/0/0.0

IKE trace shows:
IKE_SA_INIT succeeded
Switching to NAT-T port 4500
IKE_AUTH request sent, no response
IKE_AUTH retransmit…
```

**Must:**
- Identify that spoke `untrust` zone is missing `host-inbound-traffic system-services ike`
- Explain that NAT-T port-4500 return is dropped at host-inbound even on the initiator
- State this is a field-verified prerequisite (both AutoVPN and ADVPN skills document it)
- Recommend adding `host-inbound-traffic system-services ike` to spoke untrust zone
- Reference the troubleshooting matrix NAT-T row

**Must not:**
- Suggest this is a double-NAT issue (prompt states single NAT hop)
- Recommend disabling NAT-T (not the root cause; host-inbound blocking is)
- Claim the hub is misconfigured (symptom is spoke-side return path)

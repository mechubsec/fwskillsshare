# srx-ipsec-hub-spoke evals

Run each scenario in a fresh agent session with the skill installed, then again without it as a baseline. A scenario passes only when every "Must" holds and no "Must not" occurs.

## Scenario 1: Anti-recursion host route

**Prompt:** Static IPsec full-tunnel spoke shows tunnel UP but all traffic stops. What's wrong?

**Input:**
```
Spoke config:
set routing-options static route 0.0.0.0/0 next-hop st0.0
set security ipsec vpn SPOKE-VPN bind-interface st0.0

Hub WAN IP: 203.0.113.1
Spoke WAN: 198.51.100.2/30, underlay next-hop 198.51.100.1
No host route to hub WAN configured.
```

**Must:**
- Identify missing anti-recursion host route `203.0.113.1/32 → 198.51.100.1`
- Explain that default points into st0.0, but ESP packets destined to hub WAN must use underlay
- State this is the #1 gotcha (infinite recursion, instant black-hole)
- Recommend host route more-specific than default
- Reference "Anti-recursion is the #1 gotcha" section

**Must not:**
- Suggest removing st0.0 default (full tunnel requires it)
- Claim tunnel is broken (recursion breaks underlay, not IKE/IPsec negotiation itself initially)
- Recommend MTU/MSS changes as fix (it's a routing loop)

## Scenario 2: Management default ECMP trap

**Prompt:** Hub full-tunnel NAT has zero hits. Half the de-encapsulated spoke traffic appears on fxp0 instead of untrust. Why?

**Input:**
```
show route 0.0.0.0/0:
inet.0:
0.0.0.0/0 *[Static/5] via 203.0.113.1
          [Static/5] via <mgmt-gw> via fxp0.0
```

**Must:**
- Identify ECMP between WAN default and management default
- Explain that adding second `0.0.0.0/0` does NOT override mgmt default; Junos installs both as ECMP
- State that half traffic egresses fxp0 where NAT/untrust policy never applies
- Recommend putting fxp0 in dedicated management routing-instance (production fix)
- Offer lab shortcut: route specific internet destination more-specific than mgmt default

**Must not:**
- Claim NAT config is broken (NAT rule never sees half the traffic)
- Suggest deleting management default without recovery path consideration
- Recommend wide metric manipulation instead of management routing-instance

## Scenario 3: Spoke-to-spoke hairpin zone mismatch

**Prompt:** Spoke A can reach hub LAN. Spoke A to spoke B times out. Hub logs show policy deny.

**Input:**
```
Hub config:
All st0 units in zone VPN.
VPN→VPN policy missing.
VPN→trust policy permits.
```

**Must:**
- Identify that spoke-to-spoke hairpin is intra-zone VPN→VPN flow
- Explain all st0 units are in same VPN zone, so hairpin stays in that zone
- Note that missing VPN→VPN policy causes deny
- Recommend adding VPN→VPN permit policy
- State NAT is NOT needed for spoke-to-spoke (source stays private, no translation)

**Must not:**
- Suggest adding source NAT for spoke-to-spoke (skill explicitly states it's un-NAT'd)
- Claim routing is broken (policy deny is the issue)
- Recommend separate zones per spoke (defeats the hairpin design)

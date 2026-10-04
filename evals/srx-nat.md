# srx-nat evals

Run each scenario in a fresh agent session with the skill installed, then again without it as a baseline. A scenario passes only when every "Must" holds and no "Must not" occurs.

## Scenario 1: NAT processing order destination before source

**Prompt:** Why does my destination NAT not match even though the rule looks correct?

**Input:**
```
Inbound: source 203.0.113.50 → destination 198.51.100.10:443
Destination NAT pool: 192.168.1.20/32
Source NAT: trust to untrust, interface NAT
Policy: from-zone untrust to-zone trust, destination-address 192.168.1.20, permit

show security nat destination rule all: 0 hits
show security flow session: no sessions
```

**Must:**
- Review NAT processing order: static NAT, destination NAT, route lookup, policy lookup, reverse static, source NAT
- Identify that destination NAT happens BEFORE route/policy lookup
- Verify destination NAT rule-set matches source interface/zone/routing-instance (NOT destination)
- Check that security policy matches POST-DNAT destination (192.168.1.20) and translated egress zone (trust)
- State that policy must permit translated path

**Must not:**
- Claim policy is wrong without checking NAT first (NAT changes what policy sees)
- Suggest destination NAT can match destination zone (it's resolved after NAT, not before)
- Recommend changing source NAT when destination NAT is the issue

## Scenario 2: Proxy ARP vs route decision

**Prompt:** Destination NAT pool is 203.0.113.20/32. Upstream router doesn't have route to it. Should I use proxy ARP?

**Input:**
```
SRX untrust interface: ge-0/0/0.0, 203.0.113.1/24
Upstream router: 203.0.113.254, owns 203.0.113.0/24
Pool: 203.0.113.20/32 for inside server 192.168.1.20
```

**Must:**
- State that proxy ARP is an option but routing the pool prefix to SRX is preferred
- Explain proxy ARP makes SRX answer ARP for pool addresses on directly connected segment
- Recommend `set security nat proxy-arp interface ge-0/0/0.0 address 203.0.113.20/32` if using proxy ARP
- Note that if pool is off-segment or routed, proxy ARP is NOT needed
- Reference "Proxy ARP Decision" section

**Must not:**
- Claim proxy ARP is always required (depends on whether pool is directly connected and routed)
- Suggest proxy ARP when the pool is already routed to SRX
- Skip the routing question (proxy ARP vs route is design decision)

## Scenario 3: Hairpin NAT same-zone return

**Prompt:** Inside host 192.168.1.10 tries to reach public IP 203.0.113.20 (which DNATs to 192.168.1.20, same subnet). Connection times out.

**Input:**
```
DNAT: 203.0.113.20 → 192.168.1.20
Source: 192.168.1.10 (trust zone)
Destination: 203.0.113.20 → translates to 192.168.1.20 (trust zone)
Policy: trust to untrust permits, trust to trust missing
```

**Must:**
- Identify this as hairpin NAT (internal host reaching NATed internal server via public IP)
- Explain traffic enters trust, DNATs, re-routes to trust (same zone)
- Identify missing trust-to-trust or intra-zone policy
- Recommend permitting trust to trust for hairpin flows
- May also need source NAT for return symmetry (server sees SRX as source, not original client)

**Must not:**
- Claim DNAT is broken (translation happens; routing sends it back to trust)
- Suggest this is impossible (hairpin is a supported pattern)
- Skip same-zone policy requirement (zone pair must be permitted)

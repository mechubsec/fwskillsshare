# srx-mnha evals

Run each scenario in a fresh agent session with the skill installed, then again without it as a baseline. A scenario passes only when every "Must" holds and no "Must not" occurs.

## Scenario 1: Routed failover vs static gateway

**Prompt:** My MNHA pair failed over but the internet-facing host lost connectivity. BGP-facing side reconverged fine. Why?

**Input:**
```
Deployment: routed MNHA (deployment-type routing)
Internet-facing host: 203.0.113.10, static default gateway = Node0 IP (203.0.113.1)
Core-facing side: eBGP with upstream routers
Failover: Node0 down, Node1 became ACTIVE for all SRGs
```

**Must:**
- Identify that routed failover covers only routed sides (BGP/OSPF/BFD reconvergence)
- Explain that static-gateway host is stranded (no floating gateway on that segment in routed mode)
- State this is field-confirmed 2026-07 behavior
- Recommend default-gateway mode (VIP) for that segment OR upstream ECMP
- Reference routed MNHA "Failover only covers the routed sides" warning

**Must not:**
- Claim routed MNHA is broken (it works as designed; per-segment failover varies)
- Suggest VIP on all segments (routed mode is clean where routing handles failover)
- Ignore the deployment-mode consequences (this is a mode-selection issue)

## Scenario 2: VIP vMAC move blocked by switch

**Prompt:** MNHA failover shows SRG1 ACTIVE on Node1, but clients can't reach the gateway VIP. Switch logs show MAC-move violation.

**Input:**
```
Deployment: default-gateway (deployment-type switching) with VIP
Switch: Cisco with port-security and DAI enabled
SRG status: failover completed, Node1 is ACTIVE
Gateway vMAC moved to Node1's port per design
Switch: blocked MAC move, violation counter incremented
```

**Must:**
- Identify that VIP vMAC move is blocked by switch protection (MAC-move limits, DAI, storm-control, or EVPN duplicate-MAC)
- Explain that adjacent switches must accept MAC moves for failover to work
- List L2-adjacency caveats: MAC-move limits, DAI, storm-control, MLAG duplicate-MAC protection
- Note that SRG showing ACTIVE does not prove L2 convergence
- Reference default-gateway L2-adjacency caveats in skill

**Must not:**
- Claim MNHA is broken (the switch is enforcing its own MAC protection)
- Suggest disabling all switch security without understanding impact
- Ignore that "SRG ACTIVE" and "traffic working" are different things

## Scenario 3: Chassis-cluster monitor weights vs SRG

**Prompt:** Convert this chassis-cluster interface-monitor config to MNHA SRG monitoring.

**Input:**
```
Cluster config:
set chassis cluster redundancy-group 1 interface-monitor ge-0/0/2 weight 255
set chassis cluster redundancy-group 1 interface-monitor ge-0/0/3 weight 200
```

**Must:**
- State that chassis-cluster interface-monitor weights do NOT map 1:1 to SRG monitoring
- Recommend redesigning monitoring around SRG active/backup semantics
- Offer both bare `monitor interface <IFD>` and named monitor-object with weights/thresholds
- Warn against porting cluster weights directly
- Reference "Chassis-cluster interface-monitor weights do not map 1:1" warning

**Must not:**
- Port weight values directly without redesign
- Claim SRG monitoring is identical to RG monitoring
- Skip failover testing after conversion (must verify behavior)

# Architect interview

Phase 3 of the workflow. The user asked for this explicitly: prompt for the
needs, including which mode (routed, default-gateway, hybrid) and the deciding
factors for SRGs, as an SRX architect would.

## Persona and rules

Act as a senior SRX architect interviewing the user about what MNHA must do for
them. You have read the inventory ([cluster-inventory.md](cluster-inventory.md));
the user knows their business, you know the platform.

1. **One topic per round.** Never batch topics. Within a round, ask at most three questions, all on that topic.
2. **Propose, then confirm.** Lead each topic with a recommendation derived from the inventory ("reth1 carries a single OSPF neighbor, so I propose routed mode"), then ask the user to confirm or change it.
3. **Never infer a mode silently.** Even when the evidence is overwhelming, the mode, SRG layout and detection method are recorded as user-confirmed or the row stays unresolved.
4. **Explain consequences before asking**: one or two sentences on why the choice matters, then the question.
5. **Multiple choice where possible.** Use Claude `AskUserQuestion` or Codex `request_user_input` with 2-3 options, recommended first, plus free-text `Other`. Without a native tool, render the same labeled options in plain text. Do not repeat answered questions.
6. **Go segment by segment** inside topics 1 and 3: one reth or one SRG at a time when answers differ.
7. Cite evidence as `(E#)` from [vendor-evidence.md](vendor-evidence.md); label anything from `## Uncertain` as uncertain, never as fact. Send concept depth to the `srx-mnha` skill instead of restating it.

## Topics, in order

### 1. Per-segment purpose and mode

Why: the mode decides who owns the gateway on a segment. MNHA supports Layer 3
route mode, Layer 2 default-gateway mode, and hybrid (E1). Routed mode gives
each node its own interface address, so a host with a static gateway pointing at
one node is stranded on failover; routed failover only works where a router
(not a static-gateway host) sits on the segment. See the `srx-mnha` routed-mode
warning on directly-attached static-gateway hosts.

Ask, per reth: "What sits on this segment?"
- Routers or L3 switches running a routing protocol (recommend routed)
- Hosts or servers with a static default gateway (recommend default-gateway with a VIP)
- Mixed, or unsure (hybrid, or split the segment)

Changes in output: interface addressing (per-node address vs VIP), whether an
SRG1+ owns a VIP on that segment, routing protocol config, and the translation
row for the reth.

### 2. Upstream LAG and vMAC tolerance

Why (per the `srx-mnha` skill, not a TechLibrary fact): default-gateway mode moves a virtual MAC on failover. Adjacent switches
with MAC-move limits, dynamic ARP inspection, port-security, storm control or
EVPN/MLAG duplicate-MAC protection can block it and silently break failover.
The `srx-mnha` skill's default-gateway section lists these checks.

Ask:
- "Does each node connect to the upstream with its own LAG, or one link?" (own LAG per node / single link / other)
- "Can the adjacent switch accept a gateway MAC moving between ports?" (yes, verified / not checked / no, port-security or DAI is on)

Changes in output: reth LACP becomes a per-node `ae` interface; a "no" forces
routed mode or a switch change item in the runbook.

### 3. SRG design

Why: SRG0 is active/active and "Manages security service from Layer 4-Layer 7
except IPsec VPN services"; SRG1+ is active/backup and manages IPsec and virtual
IPs, with activeness priority and preemption (E2). IPsec VPN therefore needs an
SRG1+ (E3). Each former redundancy group is a candidate SRG1+; ask rather than assume a
numbering. vSRX in public cloud is limited to SRG0 and SRG1 (E9); vSRX on
KVM/Proxmox is uncertain.

Ask, per candidate group:
- "Should this group be active/backup (SRG1+) or can both nodes forward (SRG0 behavior)?" (active/backup / active-active)
- "Which node should normally own it, and should it preempt back after recovery?" (node0 no preempt / node0 preempt / node1)
- "Which VIPs and IPsec gateways follow this group?" (list from inventory)

If one redundancy group owns reths whose segments got different modes in topic 1
(for example routed upstream plus default-gateway hosts), propose splitting it
into one SRG per mode, because `deployment-type` is per SRG, and say that the
split lets ownership of the two SRGs diverge.

Changes in output: SRG ids, priorities and preempt, VIP-to-SRG ownership, IPsec
anchor SRG, and RG priority translation rows.

### 4. Failure detection

Why: chassis cluster used interface-monitor and IP monitoring; MNHA needs an
explicit detection method per SRG. Exact monitor and signal-route syntax is in
the `srx-mnha` skill.

Ask: "How should a node decide it is unhealthy?"
- BFD to the upstream router (recommend where routed)
- IP monitoring or interface monitoring (carry over the cluster's monitors)
- Signal routes steering the upstream routing protocol

Changes in output: monitor objects, BFD timers (`<PLACEHOLDER>` unless supplied),
signal-route prefixes (reserved, non-routed; never production prefixes).

### 5. ICL, ICD and HA link encryption

Why: the ICL is a routed path, not a dedicated L2 link, and must be encrypted
with IPsec (E4). Binding it to a loopback with more than one physical link is
recommended; encryption needs the IKE package and IKEv2 (E5, E6). ICD (data
link for asymmetric flows) has no TechLibrary definition located; treat as
uncertain and see `srx-mnha`.

Ask:
- "Dedicated ICL ports, or share revenue ports?" (dedicated LAG / shared)
- "Certificates or pre-shared key for HA link encryption?" (PKI, documented from Junos 22.3R1 (E5) / pre-shared key, unsourced here: verify against TechLibrary before offering)
- "Do you expect asymmetric flows, and do you want to evaluate an ICD? (ICD semantics are uncertain here; follow `srx-mnha`.)" (no / yes / unsure)

Changes in output: ICL interface or loopback, addressing `<PLACEHOLDER>`, HA
VPN stanza, and the former fab/control rows (replaced, not mapped).

### 6. Config-sync split

Why: nodes keep independent configuration; common configuration can be
replicated with `commit peers-synchronize` and logical/tenant system names must
match (E8). Node groups from the cluster become node-local sections.

Ask: "Which configuration should be identical on both nodes?" (policy/NAT/objects common, interfaces/routing/hostname node-local, recommended / everything node-local / other)

Changes in output: the common and node-local layout of `node0.set` and `node1.set`.

### 7. Platform and release support

Why: per-platform minimum release and model support is not in the overview (E7);
the Layer 3 example states 22.4R1 as its prerequisite (E6), which is an example
requirement, not a matrix. Platform support is otherwise uncertain.

Ask: "What model and Junos release will run MNHA, and is the IKE package installed?" (model + release / not yet decided)

Changes in output: a support verdict marked supported-by-example or uncertain,
and a Feature Explorer follow-up item. Transparent-mode segments are
unsupported (E10).

## Decision record

After topic 7, write this table, one row per segment or reth. It is consumed by
translation and output generation verbatim.

```
| Segment / reth | Purpose | Mode | Upstream | SRG | Detection | Decision source |
|---|---|---|---|---|---|---|
| reth1 (trust) | Routers, OSPF | routed | per-node LAG ae1 | SRG0 | BFD | user-confirmed (round 1) |
| reth2 (dmz) | Static-gateway servers | default-gateway | per-node LAG ae2, vMAC ok | SRG1 | IP monitoring | user-confirmed (round 3) |
```

`Decision source` is `user-confirmed (round N)`, `inventory-default
(unconfirmed)`, or `unresolved`. Unconfirmed or unresolved rows block
generation.

### SRG ownership

One row per SRG chosen in topic 3. Translation takes node priorities and
preemption from here, not from the per-segment table. Start from the cluster's
RG priorities as the proposal; the user confirms them.

```
| SRG | Segments | Deployment type | Priority node0 / node1 | Preempt | Decision source |
|---|---|---|---|---|---|
| SRG1 | reth1, reth2 | switching | 200 / 100 | no | user-confirmed (round 3) |
```

### Global decisions

Topics 5-7 are not per-segment. Record them under the table (columns above are
unchanged):

```
| Decision | Answer | Decision source |
|---|---|---|
| ICL (ports or loopback, addressing) | <PLACEHOLDER> | user-confirmed (round 5) |
| ICD | none / evaluate (uncertain) | user-confirmed (round 5) |
| HA link encryption | PKI / other | user-confirmed (round 5) |
| Config-sync split (common vs node-local) | <summary> | user-confirmed (round 6) |
| Platform / release verdict | supported-by-example / uncertain | user-confirmed (round 7) |
```

**The user confirms the per-segment table and the global decisions before any
configuration is generated.** Present both, ask "Confirm, or change which
row?", and apply changes before moving to translation.

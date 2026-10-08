# Architect interview

Phase 3 of the workflow. The user asked for this explicitly: prompt for the
needs, including which mode (routed, default-gateway, hybrid) and the deciding
factors for SRGs, as an SRX architect would.

## Persona and rules

Act as a senior SRX architect interviewing the user about what MNHA must do for
them. You have read the inventory ([cluster-inventory.md](cluster-inventory.md));
the user knows their business, you know the platform.

1. **One topic per round.** Never batch topics. Within a round, ask at most three questions, all on that topic (the native tool also allows at most four options per question). If a topic does not fit, carry the leftovers into the next round of the same topic before moving on. Segments that would get identical answers are asked once together ("reth1 and reth3 are both routers: routed for both?"); ask per reth only when answers differ.
2. **Propose, then confirm.** Lead each topic with a recommendation derived from the inventory ("reth1 carries a single OSPF neighbor, so I propose routed mode"), then ask the user to confirm or change it.
3. **Never infer a mode silently.** Even when the evidence is overwhelming, the mode, SRG layout and detection method are recorded as user-confirmed or the row stays unresolved.
4. **Explain consequences before asking**: one or two sentences on why the choice matters, then the question.
5. **Multiple choice where possible.** Use Claude `AskUserQuestion` or Codex `request_user_input` with 2-3 options, recommended first, plus free-text `Other`. Without a native tool, render the same labeled options in plain text. Do not repeat answered questions.
6. **Go segment by segment** inside topics 1 and 3 when answers differ; batch identical ones (rule 1).
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

Edge cases to raise here, one question each when present: a router with only
static routes pointing at the reth address behaves like a static-gateway host
(recommend default-gateway); a segment to retire (record `retired`, T25; its
monitors and references go too); a secondary address or an unnumbered reth
(T26); source or destination NAT pools inside a reth subnet with no proxy ARP
configured, or interface NAT that depends on the reth address (T15).

**Per-node addresses and IPAM.** Default-gateway mode needs a per-node address
plus the VIP on each segment, and every routed segment needs one address per
node. The skill never chooses them: ask the operator to supply them from their
IPAM, or leave `<PLACEHOLDER>`s. When an address sits on a shared LAN, also ask
for the IPAM record update and for any DHCP reservation, ARP binding or static
neighbor entry tied to the old cluster reth MAC (the lab VIP used the active
node's physical MAC instead, L10).

If the inventory shows NAT proxy ARP or DHCP on the reth (T15, T16), ask here
too, one question each: "Should the translated pool be reached by a routed
next-hop (recommended), or answered by proxy ARP on the active node only?" and
"Relay to an external DHCP server, or split local pools per node?"

Changes in output: interface addressing (per-node address vs VIP), whether an
SRG1+ owns a VIP on that segment, routing protocol config, and the translation
row for the reth.

### 2. Upstream LAG and MAC-move tolerance

Why (per the `srx-mnha` skill, not a TechLibrary fact): in default-gateway mode the gateway MAC changes on failover (a virtual MAC per the skill; the lab VIP answered with the active node's physical MAC and relied on gratuitous ARP, L10). Adjacent switches
with MAC-move limits, dynamic ARP inspection, port-security, storm control or
EVPN/MLAG duplicate-MAC protection can block it and silently break failover.
The `srx-mnha` skill's default-gateway section lists these checks.

Ask:
- "Does each node connect to the upstream with its own LAG, or one link?" (own LAG per node / single link / other)
- "Can the adjacent switch accept a gateway MAC moving between ports?" (yes, verified / not checked / no, port-security or DAI is on)
- "What will each node's ports be called once it leaves the cluster?" On vSRX the answer is known (lab-verified, L1): the former control NIC becomes `ge-0/0/0`, and cluster `ge-0/0/N` and `ge-7/0/N` both become `ge-0/0/(N+1)`; propose that and require the MAC map before load. On a physical SRX the FPC renumbering is uncertain: ask the operator for the names (same on both nodes / differ, user lists them / not known yet) and use placeholders until given.

Virtual-switch branch (hypervisor guests): ask which bridge and VLAN carries
each NIC, whether the hypervisor firewall or MAC filtering is enabled on the
guest NICs, and whether both nodes share a bridge. A shared segment MAC learned
on a virtual bridge follows the NIC that sent the gratuitous ARP.

Changes in output: reth LACP becomes a per-node `ae` interface; a "no" forces
routed mode or a switch change item in the runbook.

### 3. SRG design

Why: SRG0 is active/active and "Manages security service from Layer 4-Layer 7
except IPsec VPN services"; SRG1+ is active/backup and manages IPsec and virtual
IPs, with activeness priority and preemption (E2). IPsec VPN therefore needs an
SRG1+ (E3). Each former redundancy group is a candidate SRG1+; ask rather than assume a
numbering. vSRX in public cloud is limited to SRG0 and SRG1 (E9); vSRX on
KVM/Proxmox is uncertain beyond one lab (formed and failed over on 24.4R1.9, L8, L11). SRG0 alone suffices only for active/active L4-L7 with no VIP and no IPsec; a VIP or signal route needs an SRG1+.
Priorities: the cluster's 100/1 means nothing as `activeness-priority` (values are relative, T6). Propose a pair such as 200/100 as an unconfirmed proposal and record it only once the user confirms; do not write it as an inventory value.

Ask, per candidate group:
- "Should this group be active/backup (SRG1+) or can both nodes forward (SRG0 behavior)?" (active/backup / active-active)
- "Which node should normally own it, and should it preempt back after recovery?" (node0 no preempt / node0 preempt / node1)
- "Which VIPs and IPsec gateways follow this group?" (list from inventory)

If the user wants SRG0 only but the inventory has an IKE gateway, do not accept it: state that IPsec cannot anchor on SRG0 (E2, E3), propose an SRG1+ for the IPsec anchor, and generate nothing for IPsec under SRG0.

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
  - Warn the user: interface monitoring yields generated config (T8), but IP
    monitoring yields none (T9 is `manual`; syntax unverified) and BFD
    monitoring is a candidate to verify, not generated output.
- `none` (no failure detection; record Detection as `none`)

Signal routes are not a detection method: they publish SRG state to the
upstream routing protocol, they do not detect failure. Ask route steering as a
separate follow-up: "Should the upstream routing protocol follow SRG state with
signal routes (needed for hybrid and routed segments)?" The decision record
keeps Detection and route steering as separate answers.

Where a monitored interface belongs to a retired segment, drop the monitor (T25). Where no upstream target exists (static next hops that do not answer, a non-routing neighbor), BFD and IP monitoring have no valid target: offer interface monitoring or `none` (record Detection as `none`).

Changes in output: interface monitors, BFD timer placeholders in the fidelity report only (BFD is unconfirmed, not emitted; `<PLACEHOLDER>` unless supplied),
signal-route prefixes (reserved, non-routed; never production prefixes).

### 5. ICL, ICD and HA link encryption

Why: the ICL is a routed path, not a dedicated L2 link. Juniper recommends
encrypting it with IPsec (E4); encryption is a recommended-but-optional choice
per the operator, not yet lab-confirmed. Binding it to a loopback with more than one physical link is
recommended; encryption needs the IKE package and IKEv2 (E5, E6). ICD (data
link for asymmetric flows) has no TechLibrary definition located; treat as
uncertain and see `srx-mnha`.

Ask:
- "Dedicated ICL ports, or share revenue ports?" (dedicated LAG / single link / shared). Offer the freed fab NIC and, on vSRX, the freed former control NIC (`ge-0/0/0` after disable, L1) as ICL candidates; a lab or vSRX may use one link, with the E5 recommendation of more than one link stated as a caveat. A routed ICL needs addressing from the operator's IPAM and routing on that NIC; the loopback is optional on a single link (E5 recommends it).
- "Encrypt the ICL? Recommended for production." (PKI / PSK / none). `none` is an accepted, recorded choice: it formed HA in the lab (L8), but Juniper's docs say "must" (E4); record `none (user-declined, contradicts E4 wording; works in lab L8)`. First check `show version` for the IKE package before offering encryption.
- If encrypting, "Certificates or pre-shared key?" (PKI, documented from Junos 22.3R1 (E5), needs a device certificate and enrolment this skill does not cover / pre-shared key, unsourced here: verify against TechLibrary before offering)
- "Do you expect asymmetric flows, and do you want to evaluate an ICD? (ICD semantics are uncertain here; follow `srx-mnha`.)" (no / yes / unsure)

Changes in output: ICL interface or loopback, addressing `<PLACEHOLDER>`, HA
VPN stanza (only if encryption is chosen), and the former fab/control rows (replaced, not mapped).

### 6. Config-sync split

Why: nodes keep independent configuration; MNHA can replicate configuration
with `commit peers-synchronize` (E8); which statements it replicates and whether
node-local statements are protected is unverified (see vendor-evidence.md
Uncertain); this skill's output does not depend on it. Logical/tenant system
names must match for common sync (E8). Node groups from the cluster become node-local sections.

Ask: "Which configuration should be identical on both nodes?" (policy/NAT/objects common, interfaces/routing/hostname node-local, recommended / everything node-local / other)

Changes in output: the common and node-local layout of `node0.set` and `node1.set`.

### 7. Platform and release support

Why: per-platform minimum release and model support is not in the overview (E7);
the Layer 3 example states 22.4R1 as its prerequisite (E6), which is an example
requirement, not a matrix. Platform support is otherwise uncertain.

Do not re-ask the model and release already captured at intake (`show version`); this topic is a verdict. For a vSRX on KVM or Proxmox, say in round 1 that support is uncertain (single-lab evidence only, L8) rather than waiting until here.

Ask only if still unknown: "What model and Junos release will run MNHA, and is the IKE package installed?" (model + release / not yet decided)

Changes in output: a support verdict marked supported-by-example or uncertain,
and a Feature Explorer follow-up item. Transparent-mode segments are
unsupported (E10).

## Decision record

After topic 7, write this table, one row per segment or reth. It is consumed by
translation and output generation verbatim.

```
| Segment / reth | Purpose | Mode | Upstream | SRG | Detection | Decision source |
|---|---|---|---|---|---|---|
| reth1 (trust) | Routers, OSPF | routed | per-node LAG ae1 | SRG2 | BFD | user-confirmed (round 1) |
| reth2 (dmz) | Static-gateway servers | default-gateway | per-node LAG ae2, vMAC ok | SRG1 | IP monitoring | user-confirmed (round 3) |
```

Per-node addresses, VIPs and retired segments are rows too: add a
`Per-node addresses / VIP` cell (`<PLACEHOLDER>`s unless supplied) and a row
with Mode `retired` for a retired segment. `Detection` may be `none`.

`Decision source` is `user-confirmed (round N)`, `user-confirmed, verification
open` (the operator asserts it and an open check remains), `inventory-default
(unconfirmed)`, or `unresolved`. Unconfirmed or unresolved rows block
generation.

### SRG ownership

One row per SRG chosen in topic 3. Translation takes node priorities and
preemption from here, not from the per-segment table. Start from the cluster's
RG priorities as the proposal; the user confirms them.

```
| SRG | Segments | Deployment type | Priority node0 / node1 | Preempt | Decision source |
|---|---|---|---|---|---|
| SRG1 | reth2 | switching | 200 / 100 | no | user-confirmed (round 3) |
| SRG2 | reth1 | routing | 200 / 100 | no | user-confirmed (round 3) |
```

SRG0 (active/active L4-L7 services, no IPsec) is chosen per topic 3 and gets a
row here only when the user opts into it; the decision-record example above
uses SRG1 and SRG2 only.

### Global decisions

Topics 5-7 are not per-segment. Record them under the table (columns above are
unchanged):

```
| Decision | Answer | Decision source |
|---|---|---|
| ICL (ports or loopback, addressing) | <PLACEHOLDER> | user-confirmed (round 5) |
| ICD | none / evaluate (uncertain) | user-confirmed (round 5) |
| HA link encryption | none (user-declined) / PSK / PKI | user-confirmed (round 5) |
| Post-disable port names | vSRX: shift by one (L1); physical: operator-supplied | user-confirmed (round 2) |
| NAT proxy ARP / DHCP handling | routed next-hop / pinned proxy ARP; relay / split pools | user-confirmed (round 1) |
| Config-sync split (common vs node-local) | <summary> | user-confirmed (round 6) |
| Platform / release verdict | supported-by-example / uncertain | user-confirmed (round 7) |
```

**The user confirms the per-segment table and the global decisions before any
configuration is generated.** Present both, ask "Confirm, or change which
row?", and apply changes before moving to translation.

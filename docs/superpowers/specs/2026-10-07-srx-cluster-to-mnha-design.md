# srx-cluster-to-mnha — design

- **Date:** 2026-10-07
- **Origin:** JNPRAutomate/fw-skills-share issue #1 ("Add skill for chassis
  cluster to MNHA config conversion")
- **Status:** approved design, pre-plan

## Problem

No skill turns an existing SRX chassis-cluster configuration into MNHA
configuration. `srx-mnha` covers MNHA concepts and has a short reth→node-local
interface section plus a summary of the LaurentP TechPost. `srx-mnha-builder`
builds greenfield pairs and **stops** when it detects a cluster.
`srx-chassis-cluster-proxmox` builds clusters and is "Not for MNHA".

## Scope

In scope (v0.1.0): offline conversion plus a written cutover runbook.

- Input: cluster `display set` config, `show chassis cluster status`,
  `show chassis cluster interfaces`, platform and Junos release.
- Output: per-node MNHA set configs (`node0.set`, `node1.set`), fidelity
  report, cutover runbook with rollback, verification commands.

Out of scope (deferred): live cutover execution over the Junos MCP. When the
user wants to push configs, hand off to `srx-mnha-builder`'s staged, approval-
gated flow. Device-touching actions stay with that skill.

## Approach

A new standalone skill package `skills/srx-cluster-to-mnha/`, rather than
expanding `srx-mnha` (already 459 lines). It defers MNHA concept detail to
`srx-mnha` by skill-name handoff, not by duplicating references.

## Workflow

1. **Intake** — collect inputs above. `parsing-srx-configs` is optional for
   normalized output; the skill works directly on `display set`.
2. **Cluster inventory** — extract and show the user before asking anything:
   reths and per-node child links, LACP on reths, redundancy groups (priority,
   preempt, interface-monitor, ip-monitoring), fab and control links,
   `groups node0`/`node1` and `apply-groups "${node}"`, fxp0 management,
   per-reth services (routing protocols, IPsec gateways, NAT proxy-ARP, DHCP
   server/relay), and anything cluster-only.
3. **Architect interview** — the skill acts as an SRX architect interviewing
   the user, one topic at a time, and never infers a mode silently:
   - per-segment purpose → MNHA mode: routing, default-gateway (switching, VIP),
     or hybrid;
   - upstream: true LAG to each standalone node? switch tolerance for vMAC
     move (port-security, DAI, MAC-move limits)?
   - SRG design: SRG0-only vs SRG1+ (IPsec requires SRG1+), active/backup vs
     active/active, which services/VIPs each SRG owns, preemption intent;
   - failure detection: BFD, ip-monitoring, interface monitoring, signal routes;
   - ICL (dedicated vs shared, addressing, HA link encryption) and ICD;
   - config sync strategy (common vs node-local split);
   - platform/release support for each choice.
   Output: a decision record the user confirms before any config is generated.
4. **Translation** — mapping table, one row per cluster construct, each
   classified `converted`, `caveat`, `manual`, or `unsupported` (matching the
   `firewall-config-conversion` fidelity vocabulary).
5. **Output** — `node0.set` / `node1.set` with common and node-local sections;
   any value the user did not supply is a `<PLACEHOLDER>`, never an invented
   address; fidelity report; cutover runbook (pre-checks, isolate one node,
   break cluster, standalone reboot, ICL up, move traffic, convert second node,
   form HA, failover test; rollback point at every step); verification
   commands.

## Package layout

```
skills/srx-cluster-to-mnha/
  SKILL.md
  agents/openai.yaml
  references/
    runtime-intake.md
    architect-interview.md
    translation-map.md
    cutover-runbook.md
    output-format.md
    worked-example.md
  fixtures/
    cluster-sample.set
evals/srx-cluster-to-mnha.md
```

Markdown and non-executable fixtures only (AGENTS.md rule).

## Cross-skill edits

- `srx-mnha`: "chassis-cluster migration" now points to the new skill.
- `srx-mnha-builder`: the clustered-node stop points to the new skill.
- `inventory.json`, installer inventory, README catalog, `CHECKSUMS.sha256`.

## Evals (~5 scenarios)

1. Reth with LACP but no upstream LAG to each node → must not emit `ae` blindly.
2. Routed mode chosen for a segment with static-gateway hosts → must flag
   stranding and offer default-gateway/hybrid.
3. IPsec on reth with SRG0-only design → must require SRG1+.
4. User asks it to "just fill in the IPs" → must use placeholders, not invent.
5. User asks it to execute the migration → must decline in this skill and hand
   off to `srx-mnha-builder` with approval gates.

## Evidence

Vendor claims (mode support per platform/release, SRG constraints, IPsec
requirements, cluster-disable procedure) need Juniper TechLibrary citations
recorded in SKILL.md frontmatter sources. Anything unsourced is marked
uncertain/unsupported.

## Validation

`just fmt lint test guard security release-check`, all offline.

## Delivery

Small commits (Codex review gate): spec → skill skeleton + intake → interview
reference → translation map → runbook + output format → worked example +
fixture → evals → cross-skill edits + inventory/checksums.

## Risks

- Translation correctness for complex clusters (logical systems, multiple RIs,
  multicast) — classify as `manual` rather than guess.
- Description budget: combined warning may fire; per AGENTS.md prefer
  consolidation over trimming `Use when` clauses.

---
name: firewall-config-diff
description: Compare two parsed firewall configurations by semantic intent rather than text. Use when checking drift, HA parity, pre/post-change results, migration fidelity, or round-trip conversion. Parse raw configs first; use a text diff for literal line changes.
version: 1.0.4
author:
  - fastrevmd-lab
  - Claude
  - GPT
license: MIT
metadata:
  hermes:
    tags: [firewall, ngfw, diff, compare, drift, parity, ha-pair, migration-validation, round-trip, cross-vendor, intermediate-schema, semantic-diff]
    related_skills: [parsing-cisco-configs, parsing-fortinet-configs, parsing-palo-configs, parsing-srx-configs, firewall-config-conversion, firewall-best-practices-audit]
---

# Firewall Config Diff

## Contents

- [Overview](#overview)
- [Scope and routing](#scope-and-routing)
- [Runtime intake](#runtime-intake)
- [Input Handling](#input-handling)
- [Semantic Identity](#semantic-identity)
- [Diff Workflow](#diff-workflow)
- [Output & Verdict](#output--verdict)
- [Reference Material (load on demand)](#reference-material-load-on-demand)
- [Common Pitfalls](#common-pitfalls)
- [Verification Checklist](#verification-checklist)

## Overview

Use this skill to compare two firewall or NGFW configurations and report how they differ, by pivoting both through the `parsing-*` intermediate JSON schema. Each side is normalized to the same vendor-neutral sections — `address_objects`, `address_groups`, `service_objects`, `service_groups`, `security_policies`, `nat_rules`, `zones`, `interfaces`, `static_routes` / `virtual_routers` / routing, `vpn_tunnels`, `ha_config`, `admin_users`, and `system` — and then compared section by section. Because the comparison happens on the schema pivot rather than the raw text, same-vendor and cross-vendor diffs are one mechanism: the only cross-vendor addition is a normalization step for constructs that two vendors model differently.

The comparison is always semantic, never textual. Items are paired by what they mean — an address object by its value, a policy by its match-and-action tuple — so a rename, a reorder, or a different vendor's syntax does not register as a difference. A plain `diff` of two config files would flag every cosmetic and ordering change and miss the fact that two differently-named objects describe the same subnet; it would add nothing here and actively mislead. This skill compares meaning; it does not emit a target config (that is `firewall-config-conversion`) and does not judge the rulebase against best practice (that is `firewall-best-practices-audit`).

The output is always two parts: a per-section report listing what was added, removed, and changed, followed by a single parity verdict (`EQUIVALENT` or `DIFFERENCES FOUND`). Where a feature on one side has no equivalent on the other — common in cross-vendor comparisons — it is flagged `not-comparable` and excluded from the diff rather than reported as a false difference. The report never claims more than the schema supports and always lists what could not be compared.

## Scope and routing

Compare two normalized parser outputs. Use a text-diff tool for literal line changes, `firewall-config-conversion` to emit target syntax, and `firewall-best-practices-audit` to assess one rulebase.

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

## Input Handling

There are two inputs, **A** and **B**. Route each side independently on what you were given:

- **Parsed intermediate schema** (the vendor-neutral JSON produced by any `parsing-*` skill; the schema definition lives in the `parsing-srx-configs` skill) — diff directly. Read each side's source vendor from `metadata.source_vendor` (the canonical schema field); for robustness also accept a legacy `metadata.vendor` key if a non-conformant parse provides one — read whichever is present, and label the two sides A and B by their vendors.
- **Raw config** — identify the vendor from the syntax, run the matching `parsing-*` skill (`parsing-cisco-configs`, `parsing-fortinet-configs`, `parsing-palo-configs`, `parsing-srx-configs`) to produce the intermediate schema, then diff the result. Never re-implement parsing in this skill.

A and B may be the same vendor (drift, HA-pair, pre/post-change) or different vendors (migration parity, round-trip). The two sides may arrive in different forms — one parsed schema and one raw config — in which case parse the raw side first so both are schema before any comparison begins.

## Semantic Identity

```
Items pair across A and B by MEANING, not order. Identity is value/tuple-based by default;
a stable name is a valid anchor only in the same-vendor case (see the convention below):
- address objects: by value (e.g. 10.0.1.10/32), not object name.
- service objects: by protocol + port(s). applications: by canonical app name.
- address/service groups: by their expanded member set.
- security policies: by the tuple (src_addresses, dst_addresses, service/app, action, src_zones, dst_zones), addresses compared by value.
- nat_rules: by (match addresses/zones + translation).
- interfaces: by name/unit + address. static routes: by prefix + next-hop. OSPF/BGP: by area/AS + neighbor.
- system / admin_users / dhcp_config / ha_config / screen_config / schedules / security_services: by their natural key (name or the field identity).
A matched pair is `unchanged` (all attributes equal) or `changed` (same identity, ≥1 differing attribute — e.g. logging, profile, description). Unmatched in A only = `removed`; in B only = `added`.
Security-policy ORDER differences are reported separately (order affects shadowing) and do NOT count as add/remove.

Name-anchoring convention (resolves how value changes are reported):
- CROSS-vendor → identity is strictly value/tuple-based (names differ across platforms), so a
  value change is a `removed` + `added` pair.
- SAME-vendor drift → when object/policy NAMES are stable you MAY anchor pairs by name and
  report the value/attribute delta as `changed` (applies to address objects, service objects,
  address/service groups, AND security policies). A policy whose referenced object value
  shifts stays paired by name; the shift is noted on the `changed` pair, not as add+remove.
```

## Diff Workflow

1. **Normalize both sides to schema.** Confirm A and B are each the intermediate schema (parse any raw side first), and record each side's source vendor.
2. **Pair items per section.** For every schema section, pair items between A and B by their semantic identity from the rules above — by value, member set, or match-and-action tuple. This is the cross-vendor default; for same-vendor drift a stable name is a valid anchor (see the Name-anchoring convention). Never pair by position.
3. **Classify each pairing.** Mark each pair `unchanged` (all attributes equal) or `changed` (same identity, differing attributes); items unmatched in A are `removed`, in B are `added`. Note `security_policies` rule-order differences separately, since order affects shadowing — a reorder is not an add/remove.
4. **Normalize cross-vendor constructs.** When A and B are different vendors, normalize the constructs that the two vendors model differently using `references/equivalence-rules.md` before pairing, and flag any feature with no equivalent on the other side as `not-comparable` — never let a non-isomorphic feature surface as a false diff.
5. **Emit the report and verdict.** Produce the per-section report and the single parity verdict in the templates below, and list everything that could not be compared.

## Output & Verdict

```text
Section: <name>   unchanged <n>  added <n>  removed <n>  changed <n>[  | order: <n> reordered]
  + [B] <added item — semantic summary>
  - [A] <removed item — semantic summary>
  ~ [A→B] <identity>: <attribute change, e.g. logging off → on>
Not comparable: <sections/features with no cross-vendor equivalent>
Parity verdict: <EQUIVALENT | DIFFERENCES FOUND (<n>)>  (A=<vendor>, B=<vendor>)
```

The per-section report comes first; the single `Parity verdict:` line is always last (the
worked examples follow this order). `<n>` in the verdict equals the total
added + removed + changed across all sections (comparable items only — `not-comparable`
entries are listed but never counted).

Framings: **drift** (A=old, B=new → what changed) and **parity** (A vs B → equivalent?) — same mechanism. Never claim more than the schema supports; always list what could not be compared.

## Reference Material (load on demand)

- `references/equivalence-rules.md` — the cross-vendor normalization rules: how constructs that two vendors model differently (zones vs security-levels, App-ID vs port-based services, address/service representations, NAT models) are reduced to a common form before pairing, and which features are inherently `not-comparable`.
- `references/example-diff.md` — a worked diff against parsing-* fixtures, including a same-vendor drift case and a cross-vendor round-trip case with its parity verdict.

## Common Pitfalls

- Doing a textual or line diff — this skill compares by MEANING over the schema; never diff raw text.
- Treating a rename or a reorder as add+remove — match by semantic identity, and report order separately.
- Emitting false diffs on cross-vendor non-isomorphic features — flag them `not-comparable` instead.
- Re-implementing parsing instead of delegating to the matching `parsing-*` skill.
- Comparing object NAMES instead of VALUES across vendors — two configs can use different names for the same subnet (same-vendor drift may anchor by stable name — see Name-anchoring convention).
- Forgetting that NAT can change the effective meaning of traffic when reasoning about policy equivalence.
- Path-referencing another skill's files in the round-trip example — keep this skill self-contained with inline snippets.

## Verification Checklist

- [ ] Confirm both inputs are intermediate schema (parse raw first); note each side's vendor.
- [ ] Items paired by semantic identity (value/tuple), not name or order.
- [ ] Each section reports unchanged/added/removed/changed; rule-order changes reported separately.
- [ ] Cross-vendor non-isomorphic features flagged not-comparable, not as false diffs.
- [ ] Output has a parity verdict and lists everything that could not be compared.
- [ ] No textual line-diff; no secrets surfaced in the report.

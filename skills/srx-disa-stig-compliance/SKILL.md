---
name: srx-disa-stig-compliance
description: Assess Juniper SRX evidence against the source-pinned DISA STIG and produce conservative rule-level findings. Use when reviewing NDM, ALG, IDPS, or VPN profiles, CAT I/II/III results, CKL preparation, evidence gaps, Junos compatibility, remediation plans, or assessor-ready SRX STIG reports. Parse raw configs first.
version: 1.0.1
author:
  - fastrevmd-lab
  - Claude
  - GPT
license: MIT
metadata:
  hermes:
    tags: [srx, junos, disa, stig, y25m01, ndm, alg, idps, vpn, compliance, assessment, evidence, cat-i, cat-ii, cat-iii, ckl]
    related_skills: [parsing-srx-configs, firewall-best-practices-audit, srx-policy, srx-nat, srx-ipsec-hub-spoke]
  sources:
    - title: "NIST National Checklist Program: Juniper SRX Services Gateway Security Technical Implementation Guide"
      author: National Institute of Standards and Technology
      url: https://ncp.nist.gov/checklist/657
      retrieved: "2026-07-22"
    - title: "Juniper SRX Services Gateway Y25M01 STIG Package"
      author: Defense Information Systems Agency
      url: https://dl.dod.cyber.mil/wp-content/uploads/stigs/zip/U_Juniper_SRX_SG_Y25M01_STIG.zip
      retrieved: "2026-07-22"
    - title: "STIG Viewer 3.x User Guide"
      author: Defense Information Systems Agency
      url: https://dl.dod.cyber.mil/wp-content/uploads/stigs/pdf/U_STIG_Viewer_3-x_User_Guide_V1R7.pdf
      retrieved: "2026-07-22"
---

# SRX DISA STIG Compliance

## Contents

- [Purpose and nonclaim](#purpose-and-nonclaim)
- [Runtime intake](#runtime-intake)
- [Source lock](#source-lock)
- [Scope intake](#scope-intake)
- [Profile routing](#profile-routing)
- [Evidence contract](#evidence-contract)
- [Status contract](#status-contract)
- [Assessment workflow](#assessment-workflow)
- [Compatibility and remediation boundary](#compatibility-and-remediation-boundary)
- [Output contract](#output-contract)
- [Common failure modes](#common-failure-modes)
- [Pre-Return Self-Check](#pre-return-self-check)

## Purpose and nonclaim

Use this skill to assess Juniper SRX evidence against the pinned DISA Y25M01
benchmark at rule level. It selects the applicable SRX component catalogs,
preserves V-ID/SV-ID/JUSX identifiers and CAT severity, distinguishes four
evidence classes, and produces conservative STIG Viewer statuses.

This is assessment support, not a certification or authorization decision. Never
state that an SRX, enclave, or organization is DISA compliant. Say which selected
Y25M01 rules the supplied evidence supports, which are Open, and which remain Not
Reviewed. Final scope, applicability, risk acceptance, and authorization belong
to the assessor and Authorizing Official (AO).

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

## Source lock

Read `references/source-pin.md` before assessment. Version 1.0.0 uses only NIST
NCP checklist 657 / DISA Y25M01 with the recorded SHA-256. Report the release and
checksum in every result.

Fail closed if the supplied checklist, CKL, XCCDF, or source metadata has another
release or checksum. Do not mix identifiers, severities, checks, or fixes across
revisions. A different source requires the documented refresh and reconciliation
process before evaluation.

## Scope intake

Collect and label these facts before assigning status:

1. Device model, Junos release, FIPS mode where relevant, serial/asset identifier
   or a safe pseudonym, and assessment date.
2. Root, logical-system, tenant, routing-instance, cluster-node, and management
   scope represented by each input.
3. Device roles: firewall, IDPS, network IPsec VPN, router, switch, remote access,
   or another function.
4. Input inventory: raw configuration, normalized parse, operational commands,
   diagrams/authorized-flow records, policy/process evidence, and collection
   timestamps.
5. Whether each evidence source is complete and current for its claimed scope.

Do not infer that an unmentioned role is unused. Record unknown role evidence as
a scope gap.

## Profile routing

Read `references/profile-router.md` and select components before loading rule
catalogs:

- Always select NDM and ALG for an SRX firewall assessment.
- Add IDPS when the SRX supplies the IDPS function.
- Add VPN when it supplies network IPsec VPN.
- Load only the selected files:
  - `references/profiles/ndm.md`
  - `references/profiles/alg.md`
  - `references/profiles/idps.md`
  - `references/profiles/vpn.md`
- Report router, switching, remote-access, or other applicable STIGs as an
  out-of-scope handoff; do not pretend this package covers them.

Omit an evidenced-unused component from selected scope. Do not populate an
unselected component with mass Not Applicable results.

## Evidence contract

Read `references/status-evidence-model.md` before evaluating rules. Evidence is
classified as:

- **N — normalized configuration:** facts represented by the shared parser.
- **R — raw configuration:** syntax or semantics not fully normalized.
- **O — operational evidence:** running release, licenses, state, counters,
  packages, logs, alerts, sessions, or health.
- **M — manual/environment evidence:** roles, topology, approvals, authorized
  flows, organization-defined values, retention, recipients, processes, or AO
  decisions.

Record evidence identifier, provenance, device/context scope, collection time,
freshness, and completeness. Parse raw configuration with
`parsing-srx-configs`, but retain raw and operational evidence separately.

Never equate missing input with missing configuration. Parser-generated values,
including `_implicit: true` defaults, do not independently prove an explicit
STIG requirement.

## Status contract

Use only these statuses:

- **Not Reviewed** — default for missing, partial, ambiguous, stale, unsupported,
  or unobservable evidence required by a selected rule. This does not authorize
  results for an unselected component.
- **Open** — complete applicable evidence proves the rule is not satisfied.
- **Not a Finding** — complete applicable evidence proves every required
  predicate is satisfied.
- **Not Applicable** — the rule explicitly permits N/A and complete evidence
  proves its applicability condition false.

Do not use N/A as a substitute for missing evidence. Do not change CAT or status
because of mitigation, POA&M entry, compensating control, or risk acceptance;
record those separately.

## Assessment workflow

1. **Pin the source.** Verify Y25M01 and the recorded digest.
2. **Establish scope.** Record device/context identity, roles, inputs,
   completeness, and collection dates.
3. **Parse without discarding provenance.** Use `parsing-srx-configs` for
   normalized facts and keep raw/residual evidence visible.
4. **Select profiles.** Route NDM+ALG and conditional IDPS/VPN.
5. **Load selected catalogs.** Preserve source order and all three identifiers.
6. **Evaluate required evidence.** Apply each row's applicability, evidence,
   decision, and compatibility fields.
7. **Assign conservative status.** Incomplete proof remains Not Reviewed.
8. **Separate compatibility.** Read `references/junos-compatibility.md`; formal
   STIG status and current Junos support are different axes.
9. **Prepare remediation only.** Hand configuration design to the relevant SRX
   skill after target release/platform verification. Use the catalog's
   component/V-ID source pointer to locate exact check/fix prose in the pinned
   XCCDF; the catalog summary is not a substitute for that source.
10. **Report and self-check.** Use `references/reporting.md` and the checklist
    below.

## Compatibility and remediation boundary

The benchmark includes legacy, inconsistent, or release-sensitive guidance.
`verification_required` means preserve the formal rule outcome while requiring
current primary Juniper evidence before recommending syntax. Never silently
modernize the benchmark or treat a stronger vendor recommendation as a different
formal status.

Default operations are read-only: read, parse, analyze, report, plan, and
dry-run. Do not configure, commit, upgrade, reboot, delete, fail over, or clear
device state. A later device change requires explicit approval, exact target
validation, a reviewed diff, rollback protection, and post-change verification.
Do not expose credentials, PSKs, private keys, customer configuration, or
unredacted assessment evidence.

## Output contract

Use the templates and field definitions in `references/reporting.md`. Every
assessment must include:

- benchmark release/checksum and selected component releases;
- device/context and role scope;
- evidence inventory and completeness/freshness limitations;
- totals by component, CAT, and status;
- one result per selected rule with V-ID, SV-ID, JUSX ID, CAT, status, evidence,
  rationale, and compatibility;
- Not Reviewed/evidence-gap and unsupported queues;
- remediation candidates and assessor/AO decisions kept separate from status;
  and
- the explicit compliance nonclaim.

## Common failure modes

1. Treating a clean config review as proof of operational or manual controls.
2. Marking missing configuration when only the input is missing.
3. Marking entire unused profiles N/A instead of excluding them from scope.
4. Applying N/A without the rule's explicit condition and proof.
5. Mixing Y25M01 identifiers with another CKL or XCCDF release.
6. Copying legacy fix examples to a modern SRX without release validation.
7. Letting `_implicit: true` or a Junos default satisfy an explicit/logged rule.
8. Collapsing logical systems, tenants, nodes, or roles into one evidence scope.
9. Changing severity or status because a risk was accepted.
10. Claiming that the device or environment is compliant.

## Pre-Return Self-Check

- [ ] Source is NIST checklist 657 / DISA Y25M01 and checksum matches the pin.
- [ ] Device/context, release, roles, evidence dates, and completeness are stated.
- [ ] NDM+ALG are selected; IDPS/VPN selection is supported by role evidence.
- [ ] Rule counts match the selected component catalogs.
- [ ] Every result preserves V-ID, SV-ID, JUSX ID, and CAT.
- [ ] Missing, stale, ambiguous, unsupported, or partial evidence is Not Reviewed.
- [ ] Open and Not a Finding use complete proof; N/A follows the rule condition.
- [ ] Formal status is separate from compatibility, mitigation, POA&M, and AO decisions.
- [ ] No legacy remediation syntax is presented as current without verification.
- [ ] No secrets or sensitive raw evidence appear in the output.
- [ ] The report does not claim device, environment, authorization, or product compliance.

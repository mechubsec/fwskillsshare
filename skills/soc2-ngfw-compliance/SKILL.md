---
name: soc2-ngfw-compliance
description: Map firewall controls, evidence, and gaps to SOC 2 Trust Services Criteria. Use when assessing Type I or II, logical access, operations, change management, logging, vendor access, incident response, operating-effectiveness samples, or CC6.1, CC6.6, CC7.2, and CC8.1. Parse raw configs first.
version: 1.0.0
author:
  - fastrevmd-lab
  - Claude
  - GPT
license: MIT
metadata:
  hermes:
    tags: [soc2, trust-services-criteria, compliance, firewall, ngfw, audit, evidence, logical-access, system-operations, change-management, availability, confidentiality]
    related_skills: [srx-policy, srx-nat, parsing-srx-configs, parsing-palo-configs, parsing-fortinet-configs, parsing-cisco-configs, firewall-best-practices-audit, pci-ngfw-compliance, hipaa-ngfw-compliance, cmmc-nist-800-171-ngfw-compliance, cis-controls-ngfw-compliance, iso27001-ngfw-compliance]
  sources:
    - title: "SOC Suite of Services"
      author: AICPA & CIMA
      url: https://www.aicpa-cima.com/resources/landing/system-and-organization-controls-soc-suite-of-services
      retrieved: "2026-06-27"
    - title: "Trust Services Criteria"
      author: AICPA & CIMA
      url: https://www.aicpa-cima.com/resources/download/2017-trust-services-criteria-with-revised-points-of-focus-2022
      retrieved: "2026-06-27"
---

# SOC 2 NGFW Compliance Research

## Contents

- [Overview](#overview)
- [Scope and routing](#scope-and-routing)
- [Runtime intake](#runtime-intake)
- [Baseline Interpretation](#baseline-interpretation)
- [Reference Material (load on demand)](#reference-material-load-on-demand)
- [NGFW Feature Expectations](#ngfw-feature-expectations)
- [Output Templates](#output-templates)
- [Common Pitfalls](#common-pitfalls)
- [Verification Checklist](#verification-checklist)

## Overview

Use this skill to answer questions like “what firewall evidence do we need for SOC 2?” or “how should our NGFW controls map to Trust Services Criteria?” The core answer is: SOC 2 reports cover controls over a defined system, criteria, and period of time. A firewall or NGFW is not “SOC 2 compliant” by itself. It can support the service organization’s controls for logical access, system operations, change management, risk mitigation, monitoring, incident response, availability, confidentiality, and privacy-supporting restrictions when it is configured, monitored, reviewed, and evidenced consistently.

SOC 2 work is especially common for SaaS, MSP, MSSP, cloud-hosted services, platforms that process customer data, and organizations preparing for Type I or Type II examinations. Firewall evidence must align to the service description, system boundaries, applicable Trust Services Categories, control design, control owners, and operating effectiveness samples.

Treat this as audit-readiness and control-mapping guidance, not legal advice and not an auditor’s opinion. For formal reporting, defer to the organization’s CPA firm, audit lead, control owners, legal/compliance team, and customer commitments.

## Scope and routing

Parse raw configurations with the matching `parsing-*` skill first. Use this skill when findings must map to SOC 2 criteria and examination evidence; use `firewall-best-practices-audit` for framework-neutral hygiene.

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

## Baseline Interpretation

### What “SOC 2-Ready Firewall” Means

Use precise language:

- “This firewall estate supports controls that may be included in the SOC 2 system description and mapped to Trust Services Criteria.”
- “This design appears aligned with logical access, system operations, change management, monitoring, and availability/confidentiality objectives, subject to auditor and evidence review.”
- “Firewall evidence must show both design and operation for the examination period, especially for Type II reports.”

Avoid saying:

- “This NGFW is SOC 2 certified.”
- “The firewall makes the service SOC 2 compliant.”
- “A single screenshot is enough for a Type II control.”

### Scope, Criteria, and Report Type Come First

Before assessing firewall controls, establish:

1. report type: Type I design at a point in time or Type II design and operating effectiveness over a period;
2. Trust Services Categories in scope: Security is common to all SOC 2 reports; Availability, Confidentiality, Processing Integrity, and Privacy may be added;
3. system description boundaries, production services, customer data flows, cloud accounts, regions, and supporting systems;
4. whether firewall managers, cloud security groups, WAFs, VPN/ZTNA, identity, SIEM, monitoring, vulnerability management, and managed service providers are part of the system;
5. control matrix/control IDs used by the audit team;
6. evidence period, sample size expectations, and exceptions process.

If scope and criteria are unknown, provide a typical SOC 2 firewall evidence baseline and label assumptions.

## Reference Material (load on demand)

Detailed lookup material lives in `references/` to keep this skill lean; read these when you need them:

- `references/control-mapping.md` — SOC 2 Criteria Mapping for Firewall Work (full control-by-control matrix).
- `references/assessment-workflow.md` — step-by-step assessment workflow, config evidence markers, and the evidence request checklist:
  1. Establish SOC 2 Scope and Control Matrix
  2. Build a Firewall-to-SOC 2 Matrix
  3. Review Firewall Policy for SOC 2 Control Operation
  4. Add SOC 2 Evidence Markers to Firewall Configs
  5. Validate Type II Operating Effectiveness

## NGFW Feature Expectations

Core expectations for a firewall estate supporting SOC 2 controls, per the system description and control matrix:

- Stateful filtering aligned to the described system boundaries, with a documented zone/segment model
- Default deny between segments, with explicit, owner-attributed allow rules
- Description/tag marker fields populated on policies, NAT, zones, VPNs, objects, and profiles
- Management-plane hardening: encrypted admin access, MFA/named accounts, restricted management sources
- Centralized logging to the SIEM with synchronized NTP time sources, retained across the report period
- Configuration backup, restore testing, and change control tied to the change-management control set

NGFW-feature-to-TSC mapping is in `references/control-mapping.md`.

## Output Templates

### Short Assessment Summary

```text
Summary: The NGFW/firewall estate can support SOC 2 controls for the scoped service system, but SOC 2 reporting covers control design and operating effectiveness over a defined period, not certification of the firewall product alone. Evidence reviewed supports [strong/partial/weak] alignment with logical access, system operations, change management, risk mitigation, and [Availability/Confidentiality/Privacy if applicable]. Key gaps are [gaps]. Recommended remediation is [actions]. Final conclusions depend on the system description, criteria in scope, control matrix, period, sample results, and CPA auditor judgment.
```

### Firewall Finding

```text
Finding: Production firewall changes lack validation evidence
SOC 2 mapping: CC8 change management; supporting CC6 logical access and CC7 system operations
Evidence: Sampled changes CHG-22011 and CHG-22042 include approval but no implementation validation, peer review, or rollback notes.
Risk: Unauthorized or erroneous firewall changes could affect production security or availability without sufficient evidence of controlled change operation.
Recommendation: Require pre-approval, documented implementation plan, peer review or automated validation, rollback plan, post-change verification, and evidence attachment for production firewall changes. Sample changes during the SOC 2 period to confirm operation.
```

### Evidence Marker Recommendation

```text
Recommended description:
SOC2:ACCESS CTRL:NET-01 OWNER:NetSec REF:CHG-22119 PURPOSE:Prod app to DB least privilege

Do not include customer data, personal data, secrets, credentials, vulnerability details, incident detail, or sensitive architecture. Store detailed support in the audit evidence repository.
```

## Common Pitfalls

1. **Calling a firewall SOC 2 compliant.** SOC 2 reports cover system controls, criteria, and period. The firewall supports those controls.

2. **Ignoring Type I vs Type II.** Type I focuses on design at a point in time; Type II needs operating evidence across a period.

3. **Collecting only current screenshots.** Auditors often need sampled tickets, reviews, logs, and alerts from the report period.

4. **Mapping every firewall feature to SOC 2.** Start with the control matrix and system description, then map evidence.

5. **Forgetting customer-data paths.** Confidentiality and Privacy support require data-flow and access-path evidence, not just perimeter rules.

6. **Overlooking subservice organizations.** Cloud providers, MSSPs, MSPs, SOC providers, and managed firewall providers may require carve-out/inclusive treatment and responsibility evidence.

7. **Treating broad production access as normal.** Broad access needs documented business need, compensating controls, monitoring, and review.

8. **Leaving temporary/vendor rules open.** SOC 2 samples often expose missing expiry, review, or access-removal evidence.

9. **Assuming logs prove monitoring.** Verify alert logic, routing, triage, retention, and review evidence.

10. **Putting sensitive information in descriptions.** Use short control markers and stable references only.

## Verification Checklist

Before finalizing a SOC 2 NGFW answer:

- [ ] Confirm report type, period, system boundary, Trust Services Categories, and control matrix when possible.
- [ ] State that SOC 2 covers system controls over a defined scope/period, not the NGFW product alone.
- [ ] Identify firewall/security infrastructure assets supporting the scoped service.
- [ ] Map claims to control IDs and criteria such as CC6, CC7, CC8, CC9, Availability, Confidentiality, or Privacy as applicable.
- [ ] Check inbound, outbound, east-west, admin, VPN/ZTNA, vendor, cloud, WAF, backup, logging, and public-exposure paths separately.
- [ ] Verify owner, business purpose, approval, logging, review date, evidence reference, and expiry for important rules.
- [ ] Verify change-management evidence for firewall changes across the report period.
- [ ] Verify admin/VPN/vendor access reviews and MFA/AAA/RBAC evidence.
- [ ] Verify log forwarding, alerting, triage, incident response, retention, and review evidence.
- [ ] Verify availability/confidentiality/privacy evidence where those categories are in scope.
- [ ] Label assumptions and distinguish design adequacy from Type II operating effectiveness.

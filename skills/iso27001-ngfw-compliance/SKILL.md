---
name: iso27001-ngfw-compliance
description: Map firewall controls, evidence, and gaps to ISO/IEC 27001:2022 and ISO 27002. Use when assessing ISMS scope, Annex A.8.20-A.8.23, secure configuration, logging, supplier access, change or incident evidence, the Statement of Applicability, audits, or corrective actions. Parse raw configs first.
version: 1.0.0
author:
  - fastrevmd-lab
  - Claude
  - GPT
license: MIT
metadata:
  hermes:
    tags: [iso27001, iso-27001-2022, compliance, firewall, ngfw, isms, annex-a, audit, evidence, access-control, network-security, logging]
    related_skills: [srx-policy, srx-nat, parsing-srx-configs, parsing-palo-configs, parsing-fortinet-configs, parsing-cisco-configs, firewall-best-practices-audit, pci-ngfw-compliance, hipaa-ngfw-compliance, cmmc-nist-800-171-ngfw-compliance, cis-controls-ngfw-compliance, soc2-ngfw-compliance]
  sources:
    - title: "ISO/IEC 27001:2022 Information security management systems"
      author: International Organization for Standardization
      url: https://www.iso.org/standard/27001
      retrieved: "2026-06-27"
    - title: "ISO/IEC 27002:2022 Information security controls"
      author: International Organization for Standardization
      url: https://www.iso.org/standard/75652.html
      retrieved: "2026-06-27"
---

# ISO 27001 NGFW Compliance Research

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

Use this skill to answer questions like “how does our firewall support ISO 27001?” or “what NGFW evidence should we collect for an ISO/IEC 27001:2022 audit?” The core answer is: ISO 27001 certification applies to the organization’s Information Security Management System (ISMS) and its defined scope. A firewall or NGFW is not “ISO 27001 compliant” by itself. It is a technical and operational control that can help implement and evidence selected Annex A controls when the ISMS has selected those controls through risk assessment, the Statement of Applicability (SoA), policies, procedures, ownership, monitoring, review, and continual improvement.

Firewall evidence is usually most relevant to Annex A control themes around access control, secure authentication, information access restriction, network security, configuration management, logging, monitoring, supplier/service-provider access, ICT readiness, backup/recovery, change management, incident management, and secure operations. The exact mapping depends on the organization’s ISMS scope and SoA; do not assume every Annex A control is applicable.

Treat this as control-mapping and audit-preparation guidance, not legal advice and not a certification determination. For formal work, cite the organization’s SoA control IDs, audit scope, risk-treatment plan, and internal policy references. Avoid quoting ISO control text verbatim unless the user provides licensed text.

## Scope and routing

Parse raw configurations with the matching `parsing-*` skill first. Use this skill when findings must map to ISO 27001 controls, ISMS scope, or audit evidence; use `firewall-best-practices-audit` for framework-neutral hygiene.

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

### What “ISO 27001-Aligned Firewall” Means

Use precise language:

- “This firewall estate supports selected ISO/IEC 27001:2022 Annex A controls within the ISMS scope.”
- “The design appears aligned with the organization’s network security, access control, logging, monitoring, supplier access, change, and incident-management controls, subject to SoA and evidence review.”
- “The firewall is one technical control within the ISMS; certification depends on the scoped ISMS, risk assessment, SoA, policies, operating records, internal audit, management review, and continual improvement.”

Do not say:

- “This firewall is ISO 27001 certified.”
- “Enabling NGFW features makes the organization ISO compliant.”
- “Annex A requires this exact vendor feature.”

### ISMS Scope and SoA Come First

Before assessing firewall controls, establish:

1. the ISMS scope, sites, systems, cloud environments, business processes, customers, and services covered;
2. whether firewalls, firewall managers, SIEM, identity services, VPN/ZTNA, WAF, IDS/IPS, DNS security, cloud firewalls, and managed service providers are inside the ISMS scope;
3. the SoA controls selected as applicable, not applicable, or risk-treated through alternative controls;
4. the risk assessment and risk-treatment actions that drive firewall requirements;
5. the policies and procedures governing network access, secure configuration, logging, change management, supplier access, backups, and incident response;
6. the evidence period for the audit and required operating effectiveness samples.

If the user does not provide ISMS scope or SoA context, state assumptions and provide a “typical firewall evidence package for an ISO 27001:2022 ISMS,” not a definitive compliance conclusion.

## Reference Material (load on demand)

Detailed lookup material lives in `references/` to keep this skill lean; read these when you need them:

- `references/control-mapping.md` — ISO 27001 / Annex A practical theme mapping for firewall work (by category, with key 2022 Annex A control IDs).
- `references/assessment-workflow.md` — step-by-step assessment workflow, config evidence markers, and the evidence request checklist:
  1. Establish ISMS Context
  2. Build an ISO Firewall Evidence Matrix
  3. Review Firewall Policy Against ISMS Intent
  4. Add ISO Evidence Markers to Firewall Configs
  5. Validate Operations and Operating Effectiveness

## NGFW Feature Expectations

Core expectations for a firewall estate supporting ISMS network-security controls:

- Stateful filtering aligned to the ISMS network-segregation policy, with a documented zone model
- Default deny between zones, with explicit, owner-attributed allow rules
- Description/tag marker fields populated on policies, NAT, zones, VPNs, objects, and profiles
- Management-plane hardening: encrypted admin access, MFA/named accounts, restricted management sources
- Centralized logging to the SIEM with synchronized NTP time sources
- Configuration backup, restore testing, and change control tied to ISMS change management

NGFW-feature-to-Annex-A mapping is in `references/control-mapping.md`.

## Output Templates

### Short Assessment Summary

```text
Summary: The NGFW/firewall estate can support ISO/IEC 27001:2022 Annex A controls within the ISMS scope, but ISO 27001 certification applies to the ISMS, not to the firewall product alone. Evidence reviewed supports [strong/partial/weak] alignment with the organization’s SoA controls for access control, network security, configuration management, logging/monitoring, supplier access, incident management, and resilience. Key gaps are [gaps]. Recommended corrective actions are [actions]. Final conclusions depend on ISMS scope, SoA applicability, audit period, and auditor review.
```

### Firewall Finding

```text
Finding: Vendor firewall access lacks periodic review
ISO mapping: SoA controls for supplier relationships, access control, logging/monitoring, and network security
Evidence: Rule VENDOR-REMOTE permits vendor VPN subnet to production management service. No expiry, quarterly access review, named-user evidence, or contract/shared-responsibility link was provided.
Risk: Supplier access may persist beyond business need and weaken ISMS access-control and supplier-governance objectives.
Recommendation: Restrict vendor access by named identity, MFA, source, service, time window, and approval; add owner/ref/purpose marker; log and alert usage; review quarterly or per ISMS policy; document supplier responsibility and risk treatment.
```

### Evidence Marker Recommendation

```text
Recommended description:
ISO:LOGGING SOA:A8.15 OWNER:SecOps REF:SIEM-FW-01 PURPOSE:Forward firewall/threat logs to SIEM

Do not include secrets, personal data, customer data, vulnerability detail, incident detail, or sensitive architecture. Store detailed support in the GRC/ticket/evidence repository.
```

For alert-review/monitoring evidence use `ISO:MONITOR SOA:A8.16` instead.

## Common Pitfalls

1. **Calling a firewall ISO certified.** ISO 27001 certification applies to the scoped ISMS. The firewall supports selected controls.

2. **Ignoring the SoA.** The SoA is the bridge from risk assessment to selected controls. Do not map firewall evidence to controls the organization has not selected without explaining why.

3. **Treating Annex A as a checklist only.** ISO 27001 is management-system driven. Evidence must show policy, ownership, risk treatment, operation, review, and improvement.

4. **Reviewing only production Internet edge firewalls.** Scoped cloud firewalls, security groups, WAFs, VPN/ZTNA, internal segmentation, admin networks, logging paths, backup paths, and supplier paths can matter.

5. **Overlooking operating effectiveness.** Auditors often need samples across the audit period, not just a current config export.

6. **Leaving firewall changes unlinked to ISMS records.** Rules should tie to tickets, owners, purposes, and risk/control references.

7. **Putting sensitive data in descriptions.** Use stable IDs and short markers only.

8. **Ignoring provider/inherited controls.** Cloud and managed-service controls need responsibility matrices and provider evidence.

9. **Assuming logging exists because syslog is configured.** Verify delivery, time sync, retention, alerting, review, and incident use.

10. **Forgetting corrective action.** ISO audits care about nonconformities, corrective actions, management review, and continual improvement.

## Verification Checklist

Before finalizing an ISO 27001 NGFW answer:

- [ ] Confirm ISMS scope, audit period, and SoA context when possible.
- [ ] State that ISO 27001 certification applies to the ISMS, not the NGFW product alone.
- [ ] Identify firewall/security infrastructure assets and whether they are in-scope or supporting scoped services.
- [ ] Tie firewall claims to SoA/risk-treatment/policy references, not only generic Annex A themes.
- [ ] Check inbound, outbound, east-west, admin, VPN/ZTNA, supplier, cloud, backup, logging, and public-exposure paths separately.
- [ ] Verify owners, business purpose, approvals, review dates, and evidence markers for important rules.
- [ ] Verify secure baselines, change management, vulnerability/firmware tracking, backups, and periodic rule reviews.
- [ ] Verify logging, monitoring, NTP, retention, alert triage, incident response, and evidence samples.
- [ ] Verify supplier/provider access governance and shared responsibility evidence.
- [ ] Label assumptions and separate design adequacy from operating effectiveness.

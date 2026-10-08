---
name: pci-ngfw-compliance
description: Map firewall controls, evidence, and gaps to PCI DSS v4.0.1. Use when assessing CDE scope, segmentation, Requirement 1, traffic restrictions, six-month rule review, logging, IDS/IPS, admin access, change control, or QSA, ROC, and SAQ evidence. Treat compliance as an environment assessment, not an NGFW certification.
version: 1.0.0
author:
  - fastrevmd-lab
  - Claude
  - GPT
license: MIT
metadata:
  hermes:
    tags: [pci-dss, compliance, firewall, ngfw, network-security-controls, cde, segmentation, audit, evidence, ids, ips, waf, logging]
    related_skills: [srx-policy, srx-nat, parsing-srx-configs, parsing-palo-configs, parsing-fortinet-configs, parsing-cisco-configs, firewall-best-practices-audit, hipaa-ngfw-compliance, cmmc-nist-800-171-ngfw-compliance, cis-controls-ngfw-compliance, iso27001-ngfw-compliance, soc2-ngfw-compliance]
  sources:
    - title: "Payment Card Industry Data Security Standard: Requirements and Testing Procedures, v4.0.1"
      author: PCI Security Standards Council
      url: https://docs-prv.pcisecuritystandards.org/PCI%20DSS/Standard/PCI-DSS-v4_0_1.pdf
      retrieved: "2026-06-27"
    - title: PCI Security Standards Council Document Library metadata
      author: PCI Security Standards Council
      url: https://docs-pub.pcisecuritystandards.org/doc_library.json
      retrieved: "2026-06-27"
---

# PCI NGFW Compliance Research

## Contents

- [Overview](#overview)
- [Runtime intake](#runtime-intake)
- [Scope and routing](#scope-and-routing)
- [Baseline Interpretation](#baseline-interpretation)
- [Reference Material (load on demand)](#reference-material-load-on-demand)
- [NGFW Feature Expectations](#ngfw-feature-expectations)
- [Output Templates](#output-templates)
- [Common Pitfalls](#common-pitfalls)
- [Verification Checklist](#verification-checklist)

## Overview

Use this skill to answer questions like “what does an NGFW need to do to be PCI compliant?” or “is this firewall design sufficient for PCI DSS?” The core answer is: a next-generation firewall is not PCI compliant by itself. PCI DSS compliance is assessed for the entity, the cardholder data environment (CDE), connected-to/security-impacting systems, processes, people, evidence, and compensating or customized controls. An NGFW can be a major network security control (NSC), but it must be configured, maintained, monitored, reviewed, and evidenced as part of the whole PCI DSS program.

For PCI DSS v4.0.1, the most directly relevant NGFW areas are Requirement 1 (Install and Maintain Network Security Controls), Requirement 2 (secure configuration of system components), Requirement 4 (strong cryptography over open/public networks), Requirement 6.4.2 (automated technical solution for public-facing web applications), Requirement 8 (unique IDs, authentication, and MFA for administrative, remote, and CDE access), Requirement 10 (logging and monitoring), Requirement 11 (vulnerability scanning, penetration testing, segmentation testing, IDS/IPS), and Requirement 12 (policies, risk, incident response, and operational governance).

Treat this as research and assessment guidance, not legal advice and not a QSA decision. When producing final compliance language, cite PCI DSS v4.0.1 requirement IDs and defer final interpretation to the entity’s QSA/ISA, acquirer, or payment brand.

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

## Scope and routing

Parse raw configurations with the matching `parsing-*` skill first. Use this skill when findings must map to PCI DSS requirements or assessor evidence; use `firewall-best-practices-audit` for framework-neutral hygiene.

## Baseline Interpretation

### What “PCI compliant NGFW” Really Means

Avoid saying “this NGFW is PCI compliant” unless you mean a narrow vendor marketing claim that still needs validation in the entity’s environment. More accurate phrasing:

- “This NGFW can support PCI DSS network security control requirements if configured and operated correctly.”
- “This firewall design appears aligned with PCI DSS Requirement 1, subject to evidence review and validation.”
- “The device is one control in the PCI DSS scope; compliance depends on rules, segmentation, logging, review, change control, vulnerability management, monitoring, and incident response.”

A compliant firewall estate needs more than product features. It needs:

1. defined CDE scope and connected networks;
2. accurate network and data-flow diagrams;
3. approved business need for every allowed service, protocol, and port;
4. segmentation controls that are tested if used for scope reduction;
5. evidence showing the above is implemented and maintained (see NGFW Feature Expectations and the Verification Checklist for the full operational list).

### PCI DSS Scope Comes First

Before evaluating firewall controls, determine what is in scope:

- systems that store, process, or transmit account data;
- systems in the CDE;
- systems connected to the CDE;
- systems that can impact CDE security, including management, logging, identity, vulnerability scanning, jump hosts, backup, monitoring, virtualization/cloud control planes, and firewall managers;
- networks or devices that can reach the CDE unless segmentation is strong enough and tested.

If segmentation is used to reduce PCI scope, the firewall must be treated as a segmentation control and validated by penetration testing. Do not assume VLANs, zones, tags, security groups, or “internal” labels reduce scope without evidence.

## Reference Material (load on demand)

Detailed lookup material lives in `references/` to keep this skill lean; read these when you need them:

- `references/control-mapping.md` — Requirement Mapping for NGFW Controls (full control-by-control matrix).
- `references/assessment-workflow.md` — step-by-step assessment workflow, config evidence markers, and the evidence request checklist:
  1. Establish Scope and Architecture
  2. Build a Firewall-to-Requirement Matrix
  3. Review Rulebase for PCI Intent
  4. Add PCI Evidence Markers to Firewall Configs
  5. Validate Inbound Controls
  6. Validate Outbound Controls
  7. Validate Segmentation
  8. Validate Logging and Monitoring
  9. Validate IDS/IPS and Web-App Protection

## NGFW Feature Expectations

A PCI-supporting NGFW does not need every feature enabled everywhere, but the design should clearly explain which control covers each PCI need.

### Core Network Security Control Features

Minimum expectations:

- stateful traffic filtering between CDE and non-CDE networks;
- zone/interface/segment model aligned to CDE scope;
- explicit inbound and outbound allowlists;
- specific source, destination, application/service, user/device, and zone criteria where technically possible;
- final explicit deny/reject with logging where operationally appropriate;
- NAT rules documented so assessor can understand actual exposure and policy match behavior;
- configuration standards and secure baseline for every firewall platform;
- PCI evidence markers in supported description/comment/tag fields for policies, NAT rules, zones/segments, objects, and security profiles that are in PCI scope or enforce PCI segmentation;
- management-plane isolation, MFA where applicable, admin RBAC, and encrypted admin protocols;
- backup, restore, and config-integrity controls;
- centralized logging and time synchronization.

### NGFW “Next-Generation” Features

Useful features that may support PCI evidence:

- application identification / App-ID to reduce broad port-only permits;
- URL/category filtering for controlled outbound access;
- threat prevention, IPS, anti-malware, DNS security, sandboxing, or equivalent controls;
- TLS inspection where justified, documented, lawful, and operationally supportable;
- user identity integration for administrative or controlled access paths;
- geolocation or reputation blocking as defense-in-depth, not a substitute for allowlisting;
- dynamic address groups/tags for cloud or endpoint-driven segmentation, provided evidence shows correctness and change control;
- WAF/WAAP functions for public-facing web applications if they satisfy PCI DSS 6.4.2 expectations.

Do not overclaim NGFW features. PCI DSS Requirement 1 can be met with firewalls and other NSCs; “next-generation” functions often support Requirements 5, 6, 10, 11, and 12, but only if configured, monitored, updated, and evidenced.

## Output Templates

### Short Assessment Summary

Use language like:

```text
An NGFW is not PCI DSS compliant by itself; PCI DSS compliance is assessed for the entity and its in-scope environment. This NGFW can support PCI DSS if it is configured and operated as an effective network security control: documented CDE scope, least-privilege inbound and outbound rules, explicit deny, secure management, change control, six-month rule reviews, centralized logging, IDS/IPS or equivalent monitoring where required, segmentation testing if used for scope reduction, and evidence tying each rule to business need.
```

### Firewall Finding

```text
Finding: Broad outbound CDE Internet access
PCI DSS mapping: 1.3.2, 1.2.5, 10.2/10.4 if logs are insufficient
Evidence: Rule 220 allows CDE-SERVERS to Internet on any service; no owner/justification; 90-day hit count active.
Risk: Compromised CDE hosts can establish arbitrary outbound sessions, increasing exfiltration and command-and-control risk.
Recommendation: Replace with documented egress allowlist for payment processor, DNS, NTP, update, logging, and proxy paths; add explicit deny logging; record owner/business need; process through change control.
Assessor note: Validate with QSA whether any customized or compensating control is required for residual broad egress.
```

### Assessor-Ready Summary Format

```text
Control area: PCI DSS Requirement 1 - Network Security Controls
Scope: Firewalls FW-A/FW-B protect CDE zones CARD-APP, CARD-DB, CARD-MGMT and DMZ-PAYMENT.
Design: Inbound and outbound CDE access is default-deny with explicit business-approved permits. Public services terminate in DMZ-PAYMENT. No systems storing cardholder data are directly reachable from untrusted networks.
Evidence reviewed: network diagram v2026-06, data-flow diagram v2026-05, policy export 2026-06-20, change tickets CHG001-CHG017, six-month review record 2026-Q2, SIEM log samples, segmentation test report 2026-04.
Open gaps: Rule 145 lacks owner; IPS signature update evidence missing for FW-B; outbound update rule needs destination narrowing.
Conclusion: Substantially aligned with Requirement 1 pending remediation/evidence for listed gaps; final determination belongs to the assessor.
```

### Evidence Marker Recommendation

```text
Recommended description:
PCI:CDE REQ:1.3.1 OWNER:Payments REF:CHG12345 PURPOSE:Payment API inbound from DMZ
```

Do not include PAN, cardholder names, customer data, secrets, or incident detail in the description. Put detailed justification in the ticket/evidence repository.

## Common Pitfalls

1. **Saying a product is “PCI compliant.”** Prefer “supports PCI DSS controls when properly configured and operated.”
2. **Starting with firewall rules before establishing CDE scope and data flows.**
3. **Treating segmentation as valid without penetration test evidence.**
4. **Ignoring outbound CDE traffic.** PCI DSS v4.0.1 explicitly addresses outbound restriction from the CDE.
5. **Assuming an NGFW IPS profile automatically satisfies 11.5.1** without verifying traffic coverage, alerting, update status, and response.
6. **Assuming a firewall URL filtering or IPS feature automatically satisfies 6.4.2** for public-facing web applications. Confirm WAF/WAAP or equivalent web-attack detection/prevention.
7. **Reviewing only Internet edge firewalls** while ignoring internal segmentation, cloud security groups, VPN, wireless, management, and third-party paths.
8. **Ignoring NAT.** Published services and translated addresses often change what is actually exposed.
9. **Keeping broad object groups without expanding them during audit.**
10. **Accepting “business need: required” as justification.** Every allowed service/protocol/port needs a specific business purpose.
11. **Relying on hit counts alone.** Unused rules may still be required for DR or seasonal processing, but they need owner approval and documented rationale.
12. **Forgetting management-plane controls:** admin encryption, RBAC, MFA, AAA, management interface exposure, logging, and backups.
13. **Logging too little for audit or too much for operations.** Align logging to detection and review processes.
14. **Missing service-provider/shared-responsibility boundaries** for managed firewalls, cloud firewalls, WAF, SIEM, or SOC.
15. **Producing compliance conclusions without evidence IDs, dates, and open gaps.**
16. **Leaving PCI-relevant firewall config unmarked.** Where possible, policy, NAT, zone/segment, object, and security-profile descriptions/tags should carry concise `PCI:`/`REQ:` evidence markers.
17. **Putting sensitive data in descriptions.** Markers should reference evidence IDs and business purpose, never PAN, customer data, credentials, or incident details.

## Verification Checklist

Before finalizing a PCI/NGFW answer:

- [ ] Confirm the PCI DSS version being used, defaulting to v4.0.1 when current.
- [ ] State that PCI compliance applies to the entity/environment, not the NGFW alone.
- [ ] Identify CDE scope and whether segmentation is used for scope reduction.
- [ ] Map claims to PCI DSS requirement IDs, especially 1.x, 2.2.7, 4.2.1, 6.4.2, 8.x, 10.x, 11.x, and 12.x.
- [ ] Check inbound and outbound restrictions separately.
- [ ] Verify all allowed services/protocols/ports have business need and approval.
- [ ] Verify PCI-relevant policy, NAT, zone/segment, object, and profile entries include concise PCI evidence markers where the platform supports descriptions/tags/comments.
- [ ] Verify change control and six-month NSC review evidence.
- [ ] Verify logging, alerting, review, and incident response evidence.
- [ ] Verify IDS/IPS placement, signatures/baselines, and alert response where claimed.
- [ ] Verify WAF/WAAP or equivalent controls for public-facing web applications where applicable.
- [ ] Verify segmentation testing evidence if scope reduction is claimed.
- [ ] Label assumptions and defer final determination to QSA/ISA/acquirer/payment brand when appropriate.

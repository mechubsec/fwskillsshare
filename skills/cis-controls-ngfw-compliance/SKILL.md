---
name: cis-controls-ngfw-compliance
description: Map firewall controls, evidence, and gaps to CIS Controls v8/v8.1 safeguards. Use when assessing IG1/IG2/IG3, inventory, secure configuration, access, logging, threat prevention, or safeguard IDs such as 4.2 and 13.3. Excludes product-specific CIS Benchmarks.
version: 1.0.0
author:
  - fastrevmd-lab
  - Claude
  - GPT
license: MIT
metadata:
  hermes:
    tags: [cis-controls, cis-v8, compliance, firewall, ngfw, safeguards, audit, evidence, network-infrastructure, logging, access-control, incident-response]
    related_skills: [srx-policy, srx-nat, parsing-srx-configs, parsing-palo-configs, parsing-fortinet-configs, parsing-cisco-configs, firewall-best-practices-audit, pci-ngfw-compliance, hipaa-ngfw-compliance, cmmc-nist-800-171-ngfw-compliance, iso27001-ngfw-compliance, soc2-ngfw-compliance]
  sources:
    - title: "CIS Critical Security Controls v8"
      author: Center for Internet Security
      url: https://www.cisecurity.org/controls/v8
      retrieved: "2026-06-27"
    - title: "CIS Critical Security Controls List"
      author: Center for Internet Security
      url: https://www.cisecurity.org/controls/cis-controls-list
      retrieved: "2026-06-27"
---

# CIS Controls NGFW Compliance Research

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

Use this skill to answer questions like “how should my firewall support CIS Controls v8?” or “is this NGFW design aligned with CIS Critical Security Controls?” This skill maps firewall technical controls and evidence to CIS Controls v8 / v8.1 safeguards (primarily Controls 3-8, 10-13, 15, 17, and 18; see references/control-mapping.md) but cannot attest to the organization’s broader processes, asset management, IAM, monitoring, incident response, or operational practices. CIS Controls v8.1 (June 2024) preserves the Control/Safeguard numbering while adding a Governance security function aligned to NIST CSF 2.0; confirm which version the organization uses.

Treat this as security-control assessment guidance, not legal advice and not a certification claim. When producing final language, cite CIS Control and Safeguard IDs where known, label assumptions, and distinguish “supports CIS Controls” from “fully implemented across the enterprise.”

## Scope and routing

Parse raw configurations with the matching `parsing-*` skill first. Use this skill when findings must map to CIS Controls safeguards and evidence; use `firewall-best-practices-audit` for framework-neutral hygiene. Keep CIS Controls distinct from product-specific CIS Benchmarks.

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

### What “CIS-Aligned NGFW” Really Means

Avoid saying “this firewall is CIS compliant” as a standalone product claim. More accurate phrasing:

- “This firewall estate can support CIS Controls safeguards if configured and operated according to documented policy.”
- “This NGFW design appears aligned with selected CIS Controls around secure configuration, network infrastructure management, audit logging, monitoring, and incident response, subject to evidence review.”
- “The device is one technical safeguard; CIS alignment depends on inventory, configuration standards, access management, monitoring, vulnerability management, incident response, testing, and service-provider governance.”

A CIS-supporting firewall estate needs more than product features. It needs:

1. an inventory of network infrastructure assets and enforcement points;
2. documented network diagrams and data-flow paths for important systems;
3. secure baseline configuration standards for each firewall platform;
4. least-privilege inbound, outbound, east-west, management, VPN, and service-provider access rules;
5. protected administrative accounts, MFA/AAA/RBAC where appropriate, and encrypted management protocols;
6. centralized logs, time synchronization, alerting, and review;
7. IDS/IPS, threat prevention, DNS/URL security, anti-malware, or equivalent monitoring where justified;
8. change management, configuration backups, and periodic rule review;
9. vulnerability management for firewall software, exposed services, and management planes;
10. incident response playbooks that use firewall, VPN, IPS, and SIEM evidence;
11. penetration/segmentation testing and remediation evidence.

### Implementation Group Awareness

CIS Controls are organized into Implementation Groups (IG1, IG2, IG3). Do not assume every safeguard applies equally to every organization. When answering, ask or infer from context whether the organization is targeting IG1, IG2, or IG3:

- IG1: essential cyber hygiene; focus on inventory, secure configuration, basic logging, patching, backups, and clear incident response.
- IG2: adds more mature governance, monitoring, access control, vulnerability management, and service-provider control.
- IG3: adds advanced monitoring, automation, segmentation, threat detection, and testing for higher-risk environments.

If the user does not specify, provide a practical baseline and label it as “CIS-aligned firewall baseline; tailor by Implementation Group.” Do not overburden small environments with IG3-only expectations unless risk justifies it.

## Reference Material (load on demand)

Detailed lookup material lives in `references/` to keep this skill lean; read these when you need them:

- `references/control-mapping.md` — CIS Control Mapping for NGFW Controls (full control-by-control matrix).
- `references/assessment-workflow.md` — step-by-step assessment workflow, config evidence markers, and the evidence request checklist:
  1. Establish Scope, Inventory, and Implementation Group
  2. Build a Firewall-to-CIS Matrix
  3. Review Rulebase for CIS Intent
  4. Add CIS Evidence Markers to Firewall Configs
  5. Validate Secure Configuration and Network Infrastructure Management
  6. Validate Access Control and Data Protection
  7. Validate Logging, Monitoring, and Malware Defense
  8. Validate Vulnerability Management, Incident Response, and Testing

## NGFW Feature Expectations

A CIS-aligned firewall estate does not need every feature enabled everywhere, but the design should explain which safeguard covers each risk and how firewall evidence proves operation.

### Core Firewall and Network Infrastructure Features

Minimum expectations:

- complete inventory of firewall, VPN, WAF/WAAP, IDS/IPS, cloud firewall, security group, SASE/ZTNA, and management-plane assets;
- documented zone/interface/segment model for Internet, DMZ, user, server, management, cloud, remote-access, vendor, guest, wireless, OT/IoT, backup, and logging networks;
- explicit allowlists for critical systems and sensitive data paths;
- default deny behavior between trust zones unless a documented business need exists;
- rule descriptions or external records containing owner, business purpose, ticket/reference, review date, and control marker;
- NAT rules documented so reviewers can understand actual exposure and policy match behavior;
- management-plane isolation, encrypted protocols, MFA/AAA/RBAC where applicable, and no direct untrusted management exposure;
- time synchronization, centralized logging, protected log storage, and alert/review workflow;
- backup/restore procedures, HA/failover validation, and protected configuration repositories;
- vulnerability, firmware, content/signature, and end-of-life tracking for firewall platforms.

### NGFW “Next-Generation” Features

Useful features that may support CIS safeguards:

- application identification to reduce broad port-only permits;
- user and device identity integration for VPN, admin, and controlled access paths;
- IDS/IPS, anti-malware, sandboxing, DNS security, URL filtering, and reputation controls;
- TLS inspection where lawful, documented, risk-justified, and operationally supportable;
- DLP or exfiltration detection features for sensitive-data egress where available;
- geolocation/reputation blocking as defense-in-depth, not a substitute for least privilege;
- dynamic address groups/tags for cloud, endpoint, or identity-driven segmentation, provided tag sources are governed and evidenced;
- WAF/WAAP or API protection for public-facing applications, while recognizing application security remains broader than the firewall.

Do not overclaim NGFW features. CIS Controls describe safeguards and outcomes, not a requirement to buy a specific firewall brand or feature license.

## Output Templates

### Short Assessment Summary

```text
Summary: The NGFW/firewall estate can support CIS Controls v8 safeguards, but CIS alignment is assessed across the implemented environment and security program, not by the NGFW alone. The firewall evidence reviewed supports [strong/partial/weak] alignment with secure configuration, access control, audit logging, network infrastructure management, monitoring/defense, incident response, and testing controls. Key gaps are [gaps]. Recommended next steps are [actions]. Tailor final priority by CIS Implementation Group and organizational risk.
```

### Firewall Finding

```text
Finding: Broad server Internet egress
CIS mapping: Controls 3, 4, 6, 8, 12, 13
Evidence: Rule SERVER-OUT permits SERVER-NETS to Internet on any service. No owner, business purpose, review date, egress proxy path, or alerting evidence was provided.
Risk: Compromised servers could establish arbitrary outbound command-and-control or exfiltration sessions, weakening data protection and network monitoring objectives.
Recommendation: Replace broad egress with documented allowlist for DNS, NTP, update, logging, backup, proxy, and approved application paths; log denied attempts; add owner/ref/purpose markers; track exception approvals.
```

### Evidence Marker Recommendation

```text
Recommended description:
CIS:MONITOR CTRL:13 OWNER:SecOps REF:SIEM-FW-01 PURPOSE:Forward firewall threat logs to SIEM

Do not include secrets, customer data, vulnerability details, incident detail, or sensitive architecture in the description. Put detailed justification in the ticket/evidence repository.
```

## Common Pitfalls

1. **Saying the firewall is CIS compliant.** Say it supports CIS Controls safeguards when configured and operated as part of the environment.

2. **Ignoring Implementation Groups.** IG1/IG2/IG3 affect depth and priority. Tailor recommendations instead of treating every safeguard as equally mandatory.

3. **Starting with rule cleanup before inventory.** CIS-aligned firewall work needs asset inventory, ownership, diagrams, baselines, and scope first.

4. **Reviewing only Internet-edge firewalls.** Internal segmentation, cloud security groups, VPN, WAF, SASE/ZTNA, management, backup, logging, and service-provider paths also matter.

5. **Ignoring outbound egress.** Data protection, malware defense, and network monitoring often depend on controlling outbound paths.

6. **Treating logging as enabled/disabled only.** Validate forwarding, time sync, protection, retention, alerting, review, and incident use.

7. **Assuming IDS/IPS profile attachment equals monitoring.** Verify placement, traffic visibility, signature updates, alert routing, and response.

8. **Forgetting firewall backups and recovery.** Firewall configs are part of resilient network enforcement and should be protected and restorable.

9. **Ignoring service providers.** Managed firewall providers, MSSPs, SOCs, cloud providers, and support vendors need access governance and responsibility evidence.

10. **Putting sensitive data in descriptions.** Use short markers and stable evidence IDs, not customer data, secrets, vulnerabilities, or incident detail.

11. **Leaving CIS-relevant config unmarked.** Where possible, policy, NAT, zone/segment, object, VPN, and security-profile descriptions/tags should carry concise `CIS:`/`CTRL:` evidence markers.

12. **Producing control conclusions without evidence dates.** CIS assessment output should include artifacts, owners, dates, open gaps, and assumptions.

## Verification Checklist

Before finalizing a CIS Controls NGFW answer:

- [ ] Confirm target CIS Controls version and Implementation Group when possible.
- [ ] State that CIS alignment applies to the implemented environment/security program, not the NGFW alone.
- [ ] Identify network infrastructure assets, firewall roles, sensitive systems, data flows, and management paths.
- [ ] Map claims to CIS Controls/Safeguards, especially Controls 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 15, 17, and 18.
- [ ] Check inbound, outbound, east-west, remote-access, admin, service-provider, logging, and public-exposure paths separately.
- [ ] Verify all allowed services/protocols/ports have business need, owner, approval, and review evidence.
- [ ] Verify CIS-relevant policy, NAT, zone/segment, VPN, object, and profile entries include concise evidence markers where the platform supports descriptions/tags/comments.
- [ ] Verify secure baseline, change control, firmware/content update, backup, and periodic rule review evidence.
- [ ] Verify logging, time sync, alerting, review, log protection, and incident response evidence.
- [ ] Verify IDS/IPS/threat monitoring placement, update status, and alert response where claimed.
- [ ] Verify vulnerability scan, penetration test, and segmentation test evidence where applicable.
- [ ] Label assumptions and prioritize remediation by risk and Implementation Group.

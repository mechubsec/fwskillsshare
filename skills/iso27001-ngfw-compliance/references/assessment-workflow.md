# ISO 27001 NGFW Compliance Research — Assessment Workflow & Evidence

## Contents

- [Assessment Workflow](#assessment-workflow)
- [Evidence Request Checklist](#evidence-request-checklist)

> Reference material for the `iso27001-ngfw-compliance` skill, moved out of SKILL.md for token-efficient progressive disclosure. Load this when running an assessment, adding config evidence markers, or requesting evidence.

## Assessment Workflow

### 1. Establish ISMS Context

Collect:

- ISMS scope statement and boundaries;
- Statement of Applicability and selected Annex A controls;
- risk assessment and risk-treatment plan entries that mention network security, remote access, monitoring, suppliers, cloud, or sensitive systems;
- network diagrams and data-flow diagrams for scoped services;
- firewall/security infrastructure inventory;
- policy documents for access control, network security, secure configuration, logging, change management, supplier access, incident management, backup, and business continuity;
- audit period and sample expectations.

Questions to answer:

- Are firewall platforms and management systems inside the ISMS scope or supporting scoped services from outside the boundary?
- Which services, customers, data classes, regions, and cloud accounts are covered?
- Which Annex A controls are selected in the SoA and why?
- Which firewall controls are risk-treatment controls vs inherited service-provider controls?
- Which logs and review records demonstrate control operation across the audit period?

### 2. Build an ISO Firewall Evidence Matrix

For each firewall or enforcement point, capture:

- device/control-plane name;
- platform/version/manager;
- role: perimeter, internal segmentation, cloud, WAF/WAAP, VPN/ZTNA, IDS/IPS, DNS/web security, management-plane enforcement;
- ISMS scope relationship and protected service/process;
- SoA control references;
- owner/team and backup owner;
- change-management system;
- logging destination, retention, and alert owner;
- backup/restore and HA/DR status;
- supplier/provider access paths;
- last rule review and last configuration baseline review;
- exceptions, accepted risks, corrective actions, or audit findings.

Example:

```text
Firewall: FGT-PROD-EDGE-01
ISMS scope: SaaS production platform
ISO mapping: SoA controls for access control, network security, configuration management, logging/monitoring, supplier access, incident management
Evidence: ISMS-SOA-2026, NET-STD-001, CHG-18821, SIEM-FW-PROD, RULE-REVIEW-2026Q2, DR-FW-RESTORE-2026
Gap: Vendor VPN rule has no expiry/review record; corrective action CA-027 due 2026-08-15
```

### 3. Review Firewall Policy Against ISMS Intent

For each rule affecting scoped services, sensitive information, administration, vendors, remote access, backups, logging, monitoring, identity, updates, or Internet exposure, verify:

- owner and business purpose;
- source/destination zone, network, user, device, and service/application;
- NAT relationship and true exposure;
- logging enabled where appropriate;
- security profiles and inspection where justified;
- change ticket and approval;
- link to SoA/control/risk/treatment/evidence ID;
- expiry/review date for temporary/vendor access;
- hit count/last-hit and stale-rule handling;
- exception or risk acceptance where policy does not meet baseline.

### 4. Add ISO Evidence Markers to Firewall Configs

Where supported, use descriptions, comments, tags, labels, or external metadata to make audit evidence visible in config exports.

Pattern:

```text
ISO:<scope-or-theme> SOA:<control-id> OWNER:<team> REF:<ticket-or-evidence-id> PURPOSE:<short-purpose>
```

Examples:

```text
ISO:NETSEC SOA:A8.22 OWNER:NetSec REF:NET-STD-001 PURPOSE:Production edge segmentation   (A.8.22 Segregation of networks; use SOA:A8.20 for the umbrella Networks-security control)
ISO:ACCESS SOA:A5.15 OWNER:AppOps REF:CHG-18821 PURPOSE:App to database least privilege
ISO:LOGGING SOA:A8.15 OWNER:SecOps REF:SIEM-FW-01 PURPOSE:Forward firewall logs to SIEM   (A.8.15 Logging; use ISO:MONITOR SOA:A8.16 for monitoring activities)
ISO:SUPPLIER SOA:A5.19 OWNER:NetOps REF:MSP-ACCESS-02 PURPOSE:Time-bound MSSP access
ISO:CONFIG SOA:A8.9 OWNER:NetSec REF:BASELINE-FW-01 PURPOSE:Approved secure firewall baseline
ISO:IR SOA:A5.26 OWNER:SecOps REF:IR-FW-01 PURPOSE:Containment path for incidents
```

Marker rules:

- Use the organization’s actual SoA/control identifiers if they differ from generic Annex A labels.
- Keep markers short enough for platform field limits.
- Never put regulated data, customer data, personal data, credentials, secrets, private keys, vulnerability details, incident details, or sensitive architecture in descriptions.
- Treat markers as evidence pointers, not proof of compliance.
- Keep detailed justification in ticketing, GRC, CMDB, or evidence repositories.

### 5. Validate Operations and Operating Effectiveness

For ISO audits, design is not enough. Validate operation over the evidence period:

- sampled firewall changes show approval, testing, implementation, rollback awareness, and post-change validation;
- rule reviews occurred on schedule and included owner, business purpose, unused rules, broad rules, expired rules, and remediation tracking;
- admin access reviews removed stale accounts and confirmed RBAC/MFA/AAA;
- logging and SIEM forwarding operated continuously or had documented exceptions;
- alerts were triaged and incidents were escalated according to procedures;
- backups completed and at least one restore/failover exercise was tested;
- supplier access was reviewed and aligned to contract/shared responsibility records;
- vulnerabilities, firmware advisories, and end-of-support issues were tracked and remediated;
- internal audit or management review captured exceptions and corrective actions.

## Evidence Request Checklist

Ask for:

- ISMS scope statement;
- Statement of Applicability and relevant risk assessment/risk treatment entries;
- firewall/security infrastructure inventory and ownership/RACI;
- current network diagrams, data-flow diagrams, and cloud/security group diagrams;
- firewall policy, NAT, zone/interface, VPN/ZTNA, object, routing, and security-profile exports;
- secure firewall baseline, configuration management standard, rule naming/description/tagging standard, and backup procedure;
- change tickets, emergency changes, rollback plans, and sampled policy diffs;
- access reviews for firewall admins, VPN users, vendors, MSP/MSSP users, and service accounts;
- logging/SIEM configuration, NTP settings, sample firewall/VPN/admin/threat logs, alert workflows, retention settings, and review records;
- rule recertification records with owner, purpose, hit count, last-hit, expiry, and remediation notes;
- vulnerability/advisory tracking, firmware/content update records, and remediation tickets;
- supplier/provider contracts, shared responsibility matrices, and access review evidence;
- firewall configuration backup records, restore/failover test evidence, and DR/BCP references;
- incident response runbooks, firewall-related investigation samples, containment changes, and lessons learned;
- internal audit findings, corrective actions, risk acceptances, and management-review records.

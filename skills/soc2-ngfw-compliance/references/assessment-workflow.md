# SOC 2 NGFW Compliance Research — Assessment Workflow & Evidence

## Contents

- [Assessment Workflow](#assessment-workflow)
- [Evidence Request Checklist](#evidence-request-checklist)

> Reference material for the `soc2-ngfw-compliance` skill, moved out of SKILL.md for token-efficient progressive disclosure. Load this when running an assessment, adding config evidence markers, or requesting evidence.

## Assessment Workflow

### 1. Establish SOC 2 Scope and Control Matrix

Collect:

- system description and service boundaries;
- Trust Services Categories in scope;
- Type I or Type II report period;
- control matrix with control IDs and mapped criteria;
- network diagrams, data-flow diagrams, cloud architecture, and customer-data paths;
- production firewall/WAF/VPN/ZTNA/security-group inventory;
- firewall/network/security policies and procedures;
- audit evidence request list and sampling expectations.

Questions to answer:

- Which firewall controls are explicit controls in the matrix, and which are supporting evidence for broader controls?
- Which systems and customer data flows are in scope?
- Which service commitments mention availability, confidentiality, security, privacy, or incident response?
- Which providers operate or can access firewall controls?
- What evidence proves the control operated across the full period?

### 2. Build a Firewall-to-SOC 2 Matrix

For each firewall or enforcement point, capture:

- device/control name and platform/version;
- role: production perimeter, internal segmentation, cloud security group, WAF/WAAP, VPN/ZTNA, IDS/IPS, DNS/web security, management-plane enforcement;
- SOC 2 system boundary relationship;
- protected services and customer-data paths;
- control IDs and Trust Services Criteria mapping;
- control owner and reviewer;
- change ticket system and evidence repository;
- logging/SIEM destination, alert owner, retention;
- rule review cadence and last review;
- admin/vendor access review cadence;
- HA/DR/backup role;
- open exceptions, deviations, or audit findings.

Example:

```text
Firewall: PA-SAAS-PROD-EDGE
SOC 2 scope: Production SaaS platform, Security + Availability + Confidentiality
SOC 2 mapping: NET-01 / CC6, NET-02 / CC7, CHG-04 / CC8, AV-03 / Availability
Evidence: CHG-22119, SIEM-FW-PROD, RULE-REVIEW-2026Q2, VPN-ACCESS-2026Q2, DR-FAILOVER-2026
Open exception: Temporary support rule lacks expiry; exception EXC-044 expires 2026-07-31
```

### 3. Review Firewall Policy for SOC 2 Control Operation

For each in-scope or supporting rule, verify:

- owner, reviewer, and business purpose;
- customer-data path or production service protected;
- source/destination zone/network/user/device;
- application/service/port and whether broad access is justified;
- NAT/public exposure relationship;
- logging and alerting expectations;
- attached security profiles or compensating controls;
- change ticket and approval;
- control ID/evidence reference;
- temporary/vendor access expiry;
- hit count/last-hit and stale-rule review;
- exceptions, deviations, or risk acceptance.

### 4. Add SOC 2 Evidence Markers to Firewall Configs

Where the platform supports descriptions, comments, tags, or labels, add concise markers that help auditors connect config exports to control evidence.

Pattern:

```text
SOC2:<theme> CTRL:<control-id> OWNER:<team> REF:<ticket-or-evidence-id> PURPOSE:<short-purpose>
```

Examples:

```text
SOC2:ACCESS CTRL:NET-01 OWNER:NetSec REF:CHG-22119 PURPOSE:Prod app to DB least privilege
SOC2:MONITOR CTRL:SEC-07 OWNER:SecOps REF:SIEM-FW-01 PURPOSE:Forward firewall threat logs
SOC2:CHANGE CTRL:CHG-04 OWNER:NetOps REF:CHG-22119 PURPOSE:Approved production firewall change
SOC2:AVAIL CTRL:AV-03 OWNER:SRE REF:DR-FW-2026 PURPOSE:HA firewall path for SaaS production
SOC2:VENDOR CTRL:VND-02 OWNER:IT REF:SUPPORT-2026Q2 PURPOSE:Time-bound vendor support access
SOC2:CONF CTRL:CONF-01 OWNER:AppOps REF:DATAFLOW-07 PURPOSE:Restrict confidential data path
```

Marker rules:

- Use the organization’s actual SOC 2 control IDs where available.
- Keep markers short enough for platform field limits and exports.
- Do not include customer names, personal data, confidential customer data, credentials, secrets, vulnerability detail, incident detail, or sensitive architecture.
- Treat markers as evidence pointers, not auditor conclusions.
- Keep detailed evidence in tickets, GRC, audit folders, CMDB, or source-of-truth systems.

### 5. Validate Type II Operating Effectiveness

For Type II reports, collect samples over the examination period:

- sampled firewall changes show authorization, testing/validation, implementation, and approval;
- emergency changes have post-implementation review;
- rule reviews happened at the required cadence and tracked remediation;
- admin/VPN/vendor access reviews were completed and exceptions resolved;
- logs were forwarded continuously or exceptions were documented;
- alerts were triaged according to procedure;
- incidents involving firewall/VPN/WAF/IDS were documented and resolved;
- backups, HA, failover, or DR tests support availability commitments;
- vulnerabilities and firmware/security advisories were tracked;
- deviations have management review and remediation.

## Evidence Request Checklist

Ask for:

- SOC 2 report type, period, Trust Services Categories, and system description;
- control matrix with control IDs and criteria mappings;
- production firewall/WAF/VPN/ZTNA/security group inventory;
- architecture, network, data-flow, and customer-data diagrams;
- firewall/network security policies, secure configuration standards, rule standards, and change procedures;
- firewall policy, NAT, zone/interface, object, routing, VPN/ZTNA, WAF, IDS/IPS, DNS/security-profile, and cloud security group exports;
- sampled firewall change tickets, approvals, diffs, validation notes, and emergency-change reviews;
- rule review/recertification evidence, stale-rule remediation, exception lists, and risk acceptances;
- admin, VPN, privileged, vendor, MSP/MSSP, and service-account access review evidence;
- MFA/AAA/RBAC evidence for firewall admin and remote access;
- syslog/SIEM forwarding configuration, NTP, sample firewall/VPN/admin/threat logs, alert rules, triage records, retention settings, and review records;
- incident response tickets and firewall-related investigations;
- vulnerability/advisory tracking, firmware/content update evidence, and remediation tickets;
- HA/failover, backup/restore, DR, monitoring, capacity, or DDoS/WAF evidence when Availability is in scope;
- confidentiality/privacy data-flow restrictions and third-party access evidence when those categories are in scope;
- subservice organization/provider shared responsibility evidence and complementary user entity controls if applicable.

# CIS Controls NGFW Compliance Research — Assessment Workflow & Evidence

## Contents

- [Assessment Workflow](#assessment-workflow)
- [Evidence Request Checklist](#evidence-request-checklist)

> Reference material for the `cis-controls-ngfw-compliance` skill, moved out of SKILL.md for token-efficient progressive disclosure. Load this when running an assessment, adding config evidence markers, or requesting evidence.

## Assessment Workflow

### 1. Establish Scope, Inventory, and Implementation Group

Collect:

- target CIS Controls version and Implementation Group;
- network infrastructure asset inventory;
- firewall/NSC inventory, including physical, virtual, cloud-native, host-based, VPN, ZTNA/SASE, WAF/WAAP, IDS/IPS, and firewall managers;
- network diagrams and critical data-flow diagrams;
- sensitive data systems and high-value services protected by firewalls;
- external service-provider, vendor, remote-access, cloud, backup, logging, monitoring, and administration paths;
- configuration baseline standards and change-control process.

Questions to answer:

- Which CIS Implementation Group is the organization targeting?
- Which firewalls enforce critical boundaries or sensitive data paths?
- Which systems can administer or bypass firewall controls?
- Which external providers have access to firewall management or protected networks?
- Which logs and alerts prove controls are operating?
- Which firewalls, rules, firmware versions, or signatures are out of support, unreviewed, or unmanaged?

### 2. Build a Firewall-to-CIS Matrix

For each in-scope firewall/NSC, map:

- hostname/device ID;
- platform and version;
- owner/team;
- role: perimeter, internal segmentation, cloud control, VPN/ZTNA, WAF/WAAP, IDS/IPS, DNS/web security, management-plane control;
- protected systems or segments;
- relevant CIS Controls/Safeguards;
- log destination and retention;
- change-control system;
- backup/config repository;
- HA/DR role;
- last rule review date;
- last firmware/content update date;
- last vulnerability scan/pen test coverage;
- known exceptions, accepted risks, or remediation items.

Output example:

```text
Firewall: PA-EDGE-01
Scope: Internet edge, DMZ, remote access, critical server segmentation
CIS mapping: Controls 4, 6, 7, 8, 12, 13, 15, 17, 18
Evidence: FWSTD-001, CHG-10421, SIEM-FW-EDGE, RULE-REVIEW-2026Q2, PEN-2026-04
Open gap: Vendor VPN rule lacks expiry and recent access review; remediation NET-242 due 2026-08-30
```

### 3. Review Rulebase for CIS Intent

For each policy/rule touching sensitive systems, critical services, management paths, remote access, vendor access, or Internet exposure, capture:

- rule name and UUID;
- source zone/interface/network/user/device;
- destination zone/interface/network/object;
- application/service/port;
- action and security profile;
- NAT relationship;
- logging setting;
- owner and business purpose;
- ticket/change reference;
- CIS evidence marker;
- expiry or review date for temporary/vendor access;
- hit count and last-hit timestamp if available;
- whether the rule supports inbound exposure, outbound egress, internal segmentation, remote access, admin/management, vendor/service-provider, backup, logging, monitoring, DNS/NTP/update, or incident-response emergency access;
- whether the rule violates the baseline, requires remediation, or has documented risk treatment.

### 4. Add CIS Evidence Markers to Firewall Configs

Where the firewall platform supports descriptions, comments, annotations, labels, or tags, mark CIS-relevant configuration directly in the firewall. This makes audits easier because policy exports, NAT exports, zone lists, VPN lists, object inventories, and security-profile exports carry visible evidence markers instead of requiring reviewers to infer CIS relevance from spreadsheets alone.

Use markers as configuration hygiene and audit-evidence pointers, not proof of compliance. The marker should point to evidence; it does not replace policies, diagrams, change tickets, rule recertification, vulnerability management, incident records, or security leadership review.

Recommended marker pattern:

```text
CIS:<control-or-scope> CTRL:<control-id> OWNER:<team-or-app> REF:<ticket-or-evidence-id> PURPOSE:<short-business-purpose>
```

Examples:

```text
CIS:BOUNDARY CTRL:12 OWNER:NetSec REF:FWSTD-001 PURPOSE:Internet edge default deny
CIS:MONITOR CTRL:13 OWNER:SecOps REF:SIEM-FW-01 PURPOSE:Forward traffic/threat logs to SIEM
CIS:ACCESS CTRL:6 OWNER:IT REF:VPN-2026Q2 PURPOSE:MFA VPN to admin jump host
CIS:DATA CTRL:3 OWNER:DataEng REF:CHG12345 PURPOSE:Restrict sensitive DB access
CIS:VENDOR CTRL:15 OWNER:NetOps REF:MSP-ACCESS-01 PURPOSE:Time-bound MSP firewall admin access
CIS:BACKUP CTRL:11 OWNER:NetOps REF:BKUP-FW-01 PURPOSE:Encrypted config backup path
```

Apply markers where possible:

- security policies/rules that permit, deny, inspect, log, or segment critical or sensitive traffic;
- final explicit deny rules at important boundaries;
- NAT rules that publish services or translate traffic from sensitive systems;
- zones, interfaces, VRFs, virtual routers, VPC/VNet constructs, address books, dynamic groups, security groups, and NAC segments representing important boundaries;
- VPN, ZTNA, remote-access, third-party, service-provider, vendor, backup, logging, monitoring, DNS, NTP, update, and emergency access paths;
- IDS/IPS, WAF/WAAP, URL filtering, anti-malware, TLS inspection, DLP, DNS security, or threat profiles.

Marker rules:

- Keep markers short enough to survive platform field-length limits and exports.
- Never put regulated data, customer data, secrets, credentials, private keys, vulnerability details, incident details, or sensitive architecture detail in descriptions.
- Prefer stable references: change ticket, CMDB CI, control ID, risk ID, application ID, evidence package ID, service-provider ID, or rule-review ID.
- Use consistent tokens (`CIS:BOUNDARY`, `CTRL:12`, `CIS:MONITOR`) so exports can be searched deterministically.
- If the platform has both a tag field and a description field, use tags for machine filtering and descriptions for human audit context.
- If the platform lacks descriptions for a construct, maintain the marker in the adjacent object/rule name, tag, external source-of-truth, or rule-review export.
- Do not let markers justify bad policy. A rule with `CIS:ACCESS` still needs least privilege, approval, logging, and periodic review.

Red flags:

- broad `any any allow` into or out of sensitive or critical segments;
- unrestricted server or sensitive-data Internet egress;
- direct Internet exposure of databases, file shares, backups, management interfaces, or identity services;
- management access from untrusted or general user networks;
- vendor/MSP access without MFA, named users, source restriction, approval, monitoring, or expiry;
- unlogged high-risk access or disabled logging on important boundary rules;
- rules with no owner, business purpose, ticket, control reference, review date, or hit data;
- temporary rules without expiry;
- NAT exposing more services than policy intent suggests;
- unsupported firewall software, stale threat signatures, or missing advisory tracking;
- firewall backups missing, unencrypted, untested, or accessible to too many users;
- policy shadowing or rule order that bypasses intended controls;
- IDS/IPS/threat profiles attached but disabled, outdated, or alert-only without rationale;
- service-provider access paths not covered by contract, responsibility matrix, or access review.

### 5. Validate Secure Configuration and Network Infrastructure Management

For Controls 4 and 12, validate:

- firewall secure baselines exist and are platform-specific;
- insecure management services such as Telnet, plaintext HTTP, weak SNMP, or broad API access are disabled or justified;
- management access is restricted to approved networks and named roles;
- default accounts, weak local accounts, and stale admins are removed or controlled;
- rule naming, description/tagging, logging, and review standards are implemented;
- configuration changes are approved and traceable;
- firewall firmware/content/signatures are supported and tracked;
- backups are protected and restore procedures are tested.

### 6. Validate Access Control and Data Protection

For Controls 3, 5, and 6, validate:

- sensitive systems are reachable only from authorized user, app, service, admin, vendor, and remote-access segments;
- outbound egress from sensitive systems is restricted to approved destinations and protocols;
- admin and remote access use MFA/AAA/RBAC where appropriate;
- user identity, group, or device posture is used where it materially improves least privilege;
- service-provider access is named, approved, monitored, restricted, and reviewed;
- data-flow diagrams match policy paths;
- exceptions and compensating controls are documented.

### 7. Validate Logging, Monitoring, and Malware Defense

For Controls 8, 10, and 13, validate:

- allow and deny logs are enabled for important boundaries where operationally appropriate;
- admin login, failed login, configuration change, VPN, NAT, threat, IDS/IPS, malware, DNS, and URL events are logged;
- logs are forwarded to centralized log management/SIEM with reliable time synchronization;
- logs are protected from unauthorized modification and retained according to policy;
- alerting covers high-risk events such as new public exposure, admin failures, vendor VPN access, malware callbacks, IPS critical events, unexpected egress, and boundary deny spikes;
- threat prevention, IPS, anti-malware, DNS security, URL filtering, and sandboxing are updated where used;
- sample events can be retrieved and tied to investigations.

### 8. Validate Vulnerability Management, Incident Response, and Testing

For Controls 7, 17, and 18, validate:

- firewall management interfaces and exposed services are in vulnerability scan scope;
- firmware, content/signature, and end-of-life risks are tracked;
- remediation tickets exist for firewall vulnerabilities, broad rules, exposed services, and weak protocols;
- incident response runbooks include firewall, VPN, IPS, DNS, URL, WAF, and SIEM alert handling;
- containment procedures can rapidly block indicators, quarantine segments, disable vendor access, or tighten egress;
- penetration tests and segmentation tests validate important firewall boundaries;
- findings are tracked to closure or documented risk acceptance.

## Evidence Request Checklist

Ask for:

- target CIS Controls version and Implementation Group;
- network infrastructure inventory and CMDB export;
- current network diagrams and sensitive data-flow diagrams;
- firewall inventory and management-plane architecture;
- firewall configuration standards, secure baselines, rule naming/description/tagging standard, and change procedure;
- firewall policy exports, NAT exports, zone/interface/object exports, VPN/ZTNA exports, routing exports, and security-profile exports;
- evidence that CIS markers/descriptions exist for relevant policies, NAT, zones, VPNs, objects, and profiles where supported;
- admin account list, AAA/MFA/RBAC evidence, local account review, and service account controls;
- remote-access and service-provider/vendor access records;
- change tickets, approvals, emergency changes, and policy diffs for sampled rules;
- rule review/recertification evidence, including owner, business purpose, hit count, last-hit, expiry, and remediation notes;
- syslog/SIEM forwarding configuration, time synchronization, sample firewall/VPN/admin/threat logs, and alert workflow evidence;
- vulnerability scan reports, firmware/advisory tracking, content/signature update evidence, and remediation tickets;
- firewall backup, restore, HA/failover, and DR evidence;
- incident response runbooks and sample firewall-related investigations;
- penetration test and segmentation test methodology/results/remediation;
- service-provider contracts, shared responsibility matrices, and provider evidence where managed firewalls/SOC/cloud controls are used.

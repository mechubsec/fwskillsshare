# CMMC / NIST 800-171 NGFW Compliance Research — Assessment Workflow & Evidence

## Contents

- [Assessment Workflow](#assessment-workflow)
- [Evidence Request Checklist](#evidence-request-checklist)

> Reference material for the `cmmc-nist-800-171-ngfw-compliance` skill, moved out of SKILL.md for token-efficient progressive disclosure. Load this when running an assessment, adding config evidence markers, or requesting evidence.

## Assessment Workflow

### 1. Establish CUI Scope and Architecture

Collect:

- CUI asset inventory and CUI data-flow diagrams;
- SSP boundary description and diagrams;
- network diagrams showing CUI, non-CUI, public/DMZ, cloud, wireless, management, logging, backup, remote-access, and vendor/customer networks;
- firewall/NSC inventory, including physical, virtual, cloud-native, host-based, VPN, ZTNA/SASE, IDS/IPS, WAF/WAAP, microsegmentation, and firewall managers;
- external connection inventory: customers, primes, subcontractors, vendors, cloud services, MSP/MSSP/SOC, remote users, support paths, file exchanges, APIs, and email/file transfer paths;
- Security Protection Assets that provide boundary, identity, logging, monitoring, and management functions; note also Contractor Risk Managed Assets (CRMA), Specialized Assets, and Out-of-Scope Assets as defined by the CMMC Level 2 scoping guidance.

Questions to answer:

- Where is CUI stored, processed, or transmitted?
- Which systems provide security protection for CUI systems?
- Which firewalls enforce the CUI boundary?
- Which networks can initiate access to CUI systems?
- Which CUI egress paths are approved and why?
- Which external systems connect to the environment, and are those connections authorized and documented?
- Are cloud security groups, Kubernetes policies, service meshes, NAC, endpoint firewalls, ZTNA policies, or SDN constructs part of the evidence set?

### 2. Build a Firewall-to-Requirement Matrix

For each in-scope firewall/NSC, map:

- hostname/device ID;
- platform and version;
- owner/team;
- role: CUI enclave boundary, Internet edge, internal segmentation, VPN/ZTNA, public DMZ, cloud security control, management-plane control, IDS/IPS, WAF/WAAP, logging path;
- CUI systems or segments protected;
- relevant NIST 800-171 / CMMC practices;
- log destination and retention;
- change-control system;
- backup/config repository;
- HA/DR role;
- last rule review date;
- last assessment/test date;
- known exceptions, accepted risks, or POA&M items.

Output example:

```text
Firewall: SRX-CUI-EDGE-01
Scope: CUI engineering enclave, VPN remote access, vendor SFTP DMZ
NIST/CMMC mapping: 3.1.3, 3.1.12, 3.1.13, 3.1.20, 3.3.1, 3.4.7, 3.13.1, 3.13.8, 3.14.6
Evidence: SSP-SEC-BOUNDARY-02, CHG-20441, SIEM-CUI-FW, VPN-MFA-2026Q2, RULE-REVIEW-2026Q2
Open gap: Legacy vendor tunnel uses broad destination group; remediation POAM-117 narrows access by 2026-08-15
```

### 3. Review Rulebase for CUI Intent

For each policy/rule touching CUI systems, CUI security protection assets, or external CUI paths, capture:

- rule name and UUID;
- source zone/interface/network/user/device;
- destination zone/interface/network/object;
- application/service/port;
- action and security profile;
- NAT relationship;
- logging enabled/disabled;
- owner and business purpose;
- ticket/change reference;
- SSP/control/evidence reference;
- CMMC/CUI evidence marker;
- expiry or review date for temporary/vendor access;
- hit count and last-hit timestamp if available;
- whether the rule is CUI inbound, CUI outbound, CUI enclave segmentation, remote access, admin/management, vendor/customer, backup, logging, monitoring, update, public DMZ, cloud, or incident-response emergency access;
- whether the rule violates the standard, requires remediation, or has documented risk treatment.

### 4. Add CMMC/CUI Evidence Markers to Firewall Configs

Where the firewall platform supports descriptions, comments, annotations, labels, or tags, mark CMMC/CUI-relevant configuration directly in the firewall. This makes assessments easier because policy exports, NAT exports, zone lists, VPN lists, object inventories, and security-profile exports carry visible evidence markers instead of requiring a reviewer to infer CUI relevance from spreadsheets alone.

Use markers as configuration hygiene and audit-evidence pointers, not proof of compliance. The marker should point to evidence; it does not replace the SSP, diagrams, change tickets, assessment evidence, rule recertification, incident records, or assessor review.

Recommended marker pattern:

```text
CMMC:<scope-or-control> NIST:<req-id> OWNER:<team-or-app> REF:<ticket-or-evidence-id> PURPOSE:<short-business-purpose>
```

Examples:

```text
CMMC:CUI NIST:3.1.3 OWNER:Engineering REF:CHG12345 PURPOSE:CUI app to license server
CMMC:BOUNDARY NIST:3.13.1 OWNER:NetSec REF:SSP-BND-02 PURPOSE:CUI enclave default deny boundary
CMMC:REMOTE NIST:3.1.12 OWNER:IT REF:VPN-2026Q2 PURPOSE:MFA VPN to CUI jump host
CMMC:EXTERNAL NIST:3.1.20 OWNER:Contracts REF:IAA-CUST01 PURPOSE:Customer CUI SFTP exchange
CMMC:AUDIT NIST:3.3.1 OWNER:SecOps REF:SIEM-CUI-01 PURPOSE:Forward firewall and VPN logs
CMMC:EGRESS NIST:3.13.8 OWNER:Build REF:CHG45678 PURPOSE:Encrypted artifact upload to approved cloud
```

Apply markers where possible:

- security policies/rules that permit, deny, inspect, log, or segment CUI traffic;
- final explicit deny rules protecting CUI segments;
- NAT rules that publish CUI-adjacent services, DMZ services, remote-access endpoints, or translate CUI-system traffic;
- zones, interfaces, VRFs, virtual routers, VPC/VNet constructs, address books, dynamic groups, security groups, and NAC segments representing CUI, public, guest, wireless, vendor, management, backup, logging, or monitoring segments;
- VPN, ZTNA, remote-access, third-party, customer, subcontractor, vendor, backup, logging, monitoring, DNS, NTP, update, and emergency access paths involving CUI systems;
- IDS/IPS, WAF/WAAP, URL filtering, anti-malware, TLS inspection, DLP, DNS security, or threat profiles attached to CUI-relevant traffic.

Marker rules:

- Keep markers short enough to survive platform field-length limits and exports.
- Never put CUI content, export-controlled technical data, contract details beyond a stable reference, customer-sensitive data, secrets, credentials, private keys, vulnerability details, or incident details in descriptions.
- Prefer stable references: change ticket, CMDB CI, SSP section, NIST requirement ID, CMMC practice ID, POA&M item, application ID, customer/contract evidence ID, interconnection agreement ID, or rule-review ID.
- Use consistent tokens (`CMMC:CUI`, `CMMC:BOUNDARY`, `NIST:3.13.1`) so exports can be searched deterministically.
- If the platform has both a tag field and a description field, use tags for machine filtering and descriptions for human assessment context.
- If the platform lacks descriptions for a construct, maintain the marker in the adjacent object/rule name, tag, external source-of-truth, or rule-review export.
- Do not let markers justify bad policy. A rule with `CMMC:CUI` still needs authorized access, least privilege, logging, approval, and periodic review.

Red flags:

- broad `any any allow` into or out of CUI segments;
- unrestricted CUI-system Internet egress;
- direct Internet access to CUI file shares, repositories, databases, engineering systems, backup systems, or management interfaces;
- CUI enclave reachable from guest, public, wireless, lab, dev/test, OT/manufacturing, or general user networks without documented need;
- vendor/customer/subcontractor VPN access without MFA, source restriction, named owner, approval, monitoring, or expiry;
- remote access that bypasses managed access points or uses weak encryption;
- split tunneling that permits unmanaged paths to CUI without documented control rationale;
- unlogged high-risk access or disabled logging on CUI-relevant rules;
- firewall admins using shared accounts or management access from untrusted networks;
- rules with no owner, business purpose, ticket, SSP/control reference, or review date;
- temporary rules without expiry;
- NAT exposing more services than policy intent suggests;
- CMMC/CUI-relevant policies, NAT rules, zones, VPNs, or objects with no description/tag/marker and no external evidence reference;
- object groups hiding broad networks or shadowing intended restrictions;
- policy shadowing or rule order that bypasses intended controls;
- IDS/IPS/threat profiles attached but disabled, outdated, or alert-only without documented rationale.

### 5. Validate Access Control and CUI Flow

For 3.1.x practices, validate:

- CUI systems are reachable only from authorized user, app, service, management, remote-access, and vendor/customer segments;
- source and destination objects are specific enough to support authorized access decisions;
- traffic from non-CUI to CUI is default-deny except documented business paths;
- outbound CUI egress is restricted to approved destinations and secure protocols;
- CUI data flows match the SSP and diagrams;
- administrative paths are separated from user traffic and protected by MFA/AAA/RBAC;
- emergency access paths exist only if documented, logged, reviewed, and cleaned up;
- guest, public, wireless, lab, OT/manufacturing, and general user networks cannot initiate CUI access without explicit approval.

### 6. Validate Remote Access and External Connections

For 3.1.12, 3.1.13, 3.1.14, 3.1.20, and 3.13.8, validate:

- remote access terminates through managed access points such as VPN, ZTNA, bastion/jump host, or SASE control;
- remote users and admins use MFA where required by the environment and assessment basis;
- remote access uses approved secure protocols and current cryptographic settings;
- routes and split-tunnel behavior do not bypass monitoring or boundary controls;
- external connections to customers, primes, subcontractors, cloud services, vendors, and MSP/MSSP/SOC providers are documented and authorized;
- third-party and vendor access is least privilege, named, logged, approved, time-bound, and periodically reviewed;
- customer or contractual connection requirements are captured as evidence references, not embedded as sensitive details in firewall descriptions.

### 7. Validate Boundary Protection and Public Systems

For 3.13.1 and 3.13.5, validate:

- communications at CUI enclave boundaries are monitored, controlled, and protected;
- public-facing systems are isolated in DMZ or equivalent segments;
- public systems do not directly expose internal CUI stores unless a documented architecture and compensating controls justify the path;
- NAT and security policy together reflect intended exposure;
- IDS/IPS, WAF/WAAP, reverse proxy, or threat prevention is placed where the design relies on those controls;
- boundary deny logs and high-risk permit logs feed monitoring and incident response;
- cloud security groups/NACLs/firewalls and on-prem firewalls are considered together for hybrid environments.

### 8. Validate Audit Logging and Monitoring

For 3.3.x and 3.14.x, validate:

- allow and deny logs are enabled for CUI-relevant boundaries where operationally appropriate;
- VPN authentication, admin logins, failed logins, policy changes, threat events, NAT hits, IDS/IPS events, and denied CUI access are logged;
- logs are sent to centralized SIEM/log management with reliable time synchronization;
- log retention and protection align to organizational policy and assessment needs;
- review or alerting covers high-risk events such as CUI-boundary denies, unexpected egress, vendor VPN access, malware/IPS hits, admin login failures, policy changes, and new public exposure;
- sample events can be retrieved for the assessment period and tied to named users or systems where possible;
- log pipelines avoid leaking CUI content into analyst tools or tickets unless authorized and protected.

### 9. Validate Configuration Management and Assessment Evidence

For 3.4.x and 3.12.x, validate:

- firewall configuration baselines exist and are implemented;
- changes are approved, reviewed, and traceable;
- startup/running or candidate/active configs are protected and backed up;
- unnecessary management services and insecure protocols are disabled;
- broad rules, stale rules, and unused objects are reviewed and remediated;
- rule review findings become tracked remediation or accepted-risk items;
- SSP narratives accurately describe the implemented firewall architecture;
- assessment evidence is organized by requirement/objective with dates, owners, artifacts, and open gaps.

## Evidence Request Checklist

Ask for:

- current SSP sections covering system boundary, network architecture, remote access, external connections, logging, incident response, and configuration management;
- CUI asset inventory and CUI data-flow diagrams;
- network diagrams with CUI, non-CUI, public/DMZ, cloud, wireless, vendor/customer, management, logging, backup, and remote-access boundaries;
- firewall inventory and management-plane architecture;
- firewall/security standards, secure baselines, and rule naming/description/tagging standard;
- firewall policy exports, NAT exports, zone/interface/object exports, VPN/ZTNA exports, routing exports, and security-profile exports;
- evidence that CMMC/CUI markers/descriptions exist for relevant policies, NAT, zones, VPNs, objects, and profiles where supported;
- change tickets, approvals, emergency changes, and policy diffs for sampled rules;
- rule review/recertification evidence, including owner, business purpose, hit count, last-hit, expiry, and remediation notes;
- external connection inventory, customer/prime/subcontractor/vendor connection approvals, and interconnection evidence;
- remote-access MFA, admin RBAC, certificate, and authentication evidence;
- syslog/SIEM forwarding configuration, time synchronization, sample firewall/VPN/admin/threat logs, and alert workflow evidence;
- vulnerability scan, penetration test, segmentation test, and remediation evidence where available;
- incident response runbooks and sample firewall-related investigations;
- firewall backup, restore, HA/failover, and DR evidence;
- cloud shared-responsibility evidence for cloud firewalls/security groups/WAF/SASE/ZTNA/SIEM providers;
- POA&M/gap register entries for firewall-related findings, with owner, target date, status, and compensating controls where applicable.

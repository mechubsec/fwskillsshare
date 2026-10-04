# HIPAA NGFW Compliance Research — Assessment Workflow & Evidence

## Contents

- [Assessment Workflow](#assessment-workflow)
- [Evidence Request Checklist](#evidence-request-checklist)

> Reference material for the `hipaa-ngfw-compliance` skill, moved out of SKILL.md for token-efficient progressive disclosure. Load this when running an assessment, adding config evidence markers, or requesting evidence.

## Assessment Workflow

### 1. Establish ePHI Scope and Architecture

Collect:

- ePHI application and system inventory;
- network diagrams showing all ePHI-connected networks;
- ePHI data-flow diagrams, including external exchanges, patient portals, APIs, claims/billing, labs, imaging, telehealth, remote access, and backups;
- firewall/NSC inventory, including physical, virtual, cloud-native, host-based, VPN concentrators, WAF/WAAP, IDS/IPS, and firewall managers;
- clinical/biomedical/IoT/medical-device networks and their relationship to ePHI systems;
- third-party, vendor, business associate, backup, monitoring, logging, and administration paths;
- Internet-facing services and DMZ design.

Questions to answer:

- Where is ePHI created, received, maintained, or transmitted?
- Which systems can impact ePHI confidentiality, integrity, or availability?
- Which firewalls enforce ePHI boundaries?
- Which boundaries are trusted/untrusted or high/low sensitivity?
- Which remote-access and vendor paths can reach ePHI systems?
- Are cloud security groups, Kubernetes policies, service meshes, NAC, EDR firewall rules, or SDN constructs part of the evidence set?

### 2. Build a Firewall-to-Safeguard Matrix

For each in-scope firewall/NSC, map:

- hostname/device ID;
- platform and version;
- owner/team;
- ePHI systems or segments protected;
- business process supported;
- HIPAA safeguard areas supported;
- log destination and retention;
- change-control system;
- backup/config repository;
- HA/DR role;
- last review date;
- known exceptions or accepted risks.

Output example:

```text
Firewall: PA-EDGE-01
Scope: Patient portal DMZ, EHR API ingress, vendor VPN
HIPAA mapping: 164.312(a), 164.312(b), 164.312(d), 164.312(e), 164.308(a)(6)
Evidence: FWSTD-001, CHG-10421, SIEM-HIPAA-DMZ, VPN-MFA-2026Q2
Open risk: Legacy lab partner still requires source NAT exception; risk acceptance RA-882 expires 2026-09-30
```

### 3. Review Rules for Least Privilege and Authorized Access

For each policy/rule touching ePHI systems, capture:

- rule name and UUID;
- source zone/interface/network/user/device;
- destination zone/interface/network/object;
- application/service/port;
- action and security profile;
- logging enabled/disabled;
- owner and business purpose;
- ticket/change reference;
- HIPAA safeguard marker;
- expiry or review date for temporary/vendor access;
- hit count and last-hit timestamp if available;
- whether the rule is clinical access, administrative access, vendor access, remote access, backup, monitoring, logging, update, Internet-facing, or east-west segmentation;
- whether the rule violates the standard or requires documented risk treatment.

### 4. Add HIPAA Evidence Markers to Firewall Configs

Where the firewall platform supports descriptions, comments, annotations, labels, or tags, mark HIPAA/ePHI-relevant configuration directly in the firewall. This makes audits easier because policy exports, NAT exports, zone lists, VPN lists, object inventories, and security-profile exports carry visible evidence markers instead of requiring a reviewer to infer HIPAA relevance from spreadsheets alone.

Use this as configuration hygiene and audit-evidence support, not as the only source of truth. The marker should point to evidence; it does not replace policies, risk analysis, change tickets, access review, incident response records, or legal/compliance review.

Recommended marker pattern:

```text
HIPAA:<scope-or-control> CFR:<section-or-safeguard> OWNER:<team-or-app> REF:<ticket-or-evidence-id> PURPOSE:<short-business-purpose>
```

Examples:

```text
HIPAA:EPHI CFR:164.312(a) OWNER:EHR REF:CHG12345 PURPOSE:EHR API access from clinical app tier
HIPAA:TRANSMISSION CFR:164.312(e) OWNER:Telehealth REF:VPN-2026Q2 PURPOSE:Encrypted telehealth vendor tunnel
HIPAA:AUDIT CFR:164.312(b) OWNER:SecOps REF:SIEM-HIPAA-01 PURPOSE:Forward firewall and VPN logs to SIEM
HIPAA:SEGMENTATION CFR:164.308(a)(1) OWNER:NetSec REF:RA-2026Q2 PURPOSE:Limit guest/IoT access to ePHI systems
HIPAA:VENDOR CFR:164.314(a) OWNER:Biomed REF:BAA-VEND123 PURPOSE:Vendor support access to imaging system
```

Apply markers where possible:

- security policies/rules that permit, deny, inspect, log, or segment traffic involving ePHI systems;
- final explicit deny rules protecting ePHI segments;
- NAT rules that publish healthcare portals, APIs, VPNs, telehealth services, or translate ePHI-system traffic;
- zones, interfaces, VRFs, virtual routers, VPC/VNet constructs, address books, dynamic groups, security groups, and NAC segments representing ePHI, clinical, guest, IoT, medical-device, vendor, management, backup, or monitoring segments;
- VPN, remote-access, third-party, business associate, vendor, backup, logging, monitoring, DNS, NTP, update, and emergency access paths involving ePHI systems;
- IDS/IPS, WAF/WAAP, URL filtering, anti-malware, TLS inspection, DLP, DNS security, or threat profiles attached to HIPAA-relevant traffic.

Marker rules:

- Keep markers short enough to survive platform field-length limits and exports.
- Never put PHI, patient names, medical record numbers, diagnoses, treatment details, claim details, secrets, credentials, private keys, or sensitive incident detail in descriptions.
- Prefer stable references: change ticket, CMDB CI, risk ID, control ID, application ID, BAA/vendor ID, evidence package ID, or rule-review ID.
- Use consistent tokens (`HIPAA:EPHI`, `HIPAA:TRANSMISSION`, `CFR:164.312(e)`) so exports can be searched deterministically.
- If the platform has both a tag field and a description field, use tags for machine filtering and descriptions for human audit context.
- If the platform lacks descriptions for a construct, maintain the marker in the adjacent object/rule name, tag, external source-of-truth, or rule-review export.
- Do not let markers justify bad policy. A rule with `HIPAA:EPHI` still needs authorized access, least privilege, logging, approval, and periodic review.

Red flags:

- broad `any any allow` into or out of ePHI segments;
- unrestricted ePHI-system Internet access;
- direct Internet access to EHR, database, file-share, imaging, or backup systems;
- vendor VPN access without MFA, source restriction, expiry, or owner;
- medical-device or IoT networks with broad reach to ePHI systems;
- guest, public, or user networks able to initiate access to ePHI systems without clear business need;
- unlogged high-risk access or disabled logging on HIPAA-relevant rules;
- rules with no owner, business purpose, ticket, or risk reference;
- temporary rules without expiry;
- NAT exposing more services than policy intent suggests;
- HIPAA-relevant policies, NAT rules, zones, VPNs, or objects with no description/tag/marker and no external evidence reference;
- object groups hiding broad networks or shadowing intended restrictions;
- default vendor services enabled on management interfaces;
- policy shadowing or rule order that bypasses intended controls;
- IDS/IPS/WAF profiles attached but disabled or set to alert-only without documented rationale.

### 5. Validate Access Control

HIPAA 164.312(a) requires technical policies and procedures that allow access only to persons or software programs granted access rights. For firewall work, validate:

- ePHI systems are reachable only from authorized user, app, service, management, and vendor segments;
- source and destination objects are specific enough to support authorized access decisions;
- user identity or device posture is used where appropriate for VPN/remote/admin access;
- application controls reduce broad port-based access where feasible;
- emergency access paths exist but are controlled, logged, and documented;
- privileged/admin access uses separate management paths, MFA, and encrypted protocols;
- access from guest, public, IoT, biomedical, and general user networks is denied unless explicitly justified.

### 6. Validate Audit Controls and Log Review

HIPAA 164.312(b) requires mechanisms to record and examine activity in systems that contain or use ePHI. Firewalls often provide critical supporting logs. Validate:

- allow and deny logs are enabled for HIPAA-relevant boundaries where operationally appropriate;
- VPN authentication, admin changes, policy changes, threat events, NAT hits, and denied access are logged;
- logs are sent to a centralized SIEM or log platform with reliable time synchronization;
- log retention aligns with organizational policy and HIPAA documentation needs;
- regular, risk-based review or alerting (HIPAA requires regular information-system-activity review, not a prescribed daily cadence) covers high-risk events such as ePHI-segment denies, vendor VPN access, malware/IPS hits, geo-anomalies, admin login failures, and policy changes;
- log integrity and access controls prevent unauthorized alteration or deletion;
- sample events can be retrieved for an audit period.

### 7. Validate Transmission Security

HIPAA 45 CFR 164.312(e) requires technical security measures to guard against unauthorized access to ePHI being transmitted over electronic communications networks. Validate:

- ePHI over untrusted networks uses TLS, IPsec, SSH/SFTP, HTTPS, or other approved secure protocols;
- weak protocols such as Telnet, FTP, plaintext HTTP for ePHI, insecure SNMP, or weak VPN ciphers are disabled or documented with alternatives;
- partner, business associate, telehealth, patient portal, claims, lab, imaging, and backup connections use approved encryption;
- VPN and TLS profiles are reviewed for current cipher/protocol standards;
- firewall rules do not permit plaintext alternatives around approved encrypted paths;
- decryption/inspection policy is documented and does not create improper PHI exposure in logs or analyst workflows.

### 8. Validate Integrity, Threat Prevention, and Incident Response

For 164.312(c), 164.308(a)(1), and 164.308(a)(6), validate:

- firewall configuration changes are approved, reviewed, and traceable;
- admin roles prevent unauthorized policy alteration;
- backups and config exports are protected;
- IPS, anti-malware, DNS security, URL filtering, WAF/WAAP, and sandbox controls are updated where used;
- ePHI-relevant threat events create actionable alerts;
- incident response runbooks include firewall, VPN, IPS, WAF, and SIEM escalation paths;
- firewall evidence can support containment, investigation, and post-incident improvement.

### 9. Validate Business Associate and Vendor Paths

For 164.308(b) and 164.314(a), validate:

- managed firewall providers, cloud firewall providers, MSSPs, VPN vendors, and support vendors that create, receive, maintain, transmit, or can access ePHI are evaluated for business associate status;
- BAAs or equivalent required arrangements exist where applicable;
- vendor remote access is least privilege, named, authenticated, logged, approved, time-bound, and monitored;
- subcontractor and incident notification obligations are captured in contracts;
- firewall evidence differentiates covered entity, business associate, and subcontractor responsibilities.

## Evidence Request Checklist

Ask for:

- current ePHI asset inventory and data-flow diagrams;
- current network diagrams with ePHI systems and firewall boundaries;
- firewall inventory and management-plane architecture;
- firewall/security standards and rule naming/description/tagging standard;
- firewall policy exports, NAT exports, zone/interface/object exports, VPN exports, and security-profile exports;
- evidence that HIPAA markers/descriptions exist for relevant policies, NAT, zones, VPNs, objects, and profiles where supported;
- change tickets, approvals, emergency changes, and policy diffs for sampled rules;
- risk analysis entries that discuss network/firewall/ePHI threats and vulnerabilities;
- risk treatment plans, accepted risks, exception records, and review dates;
- SIEM/syslog forwarding configuration and sample logs;
- VPN MFA, admin RBAC, certificate, and authentication evidence;
- vulnerability scan, pen test, segmentation test, and remediation evidence where available;
- incident response runbooks and sample firewall-related investigations;
- firewall backup, restore, HA/failover, and DR evidence;
- BAA/vendor/shared-responsibility evidence for managed firewall/cloud/security providers;
- documentation retention and update records.

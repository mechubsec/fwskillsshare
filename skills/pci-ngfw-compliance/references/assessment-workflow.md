# PCI NGFW Compliance Research — Assessment Workflow & Evidence

## Contents

- [Assessment Workflow](#assessment-workflow)
- [Evidence Request Checklist](#evidence-request-checklist)

> Reference material for the `pci-ngfw-compliance` skill, moved out of SKILL.md for token-efficient progressive disclosure. Load this when running an assessment, adding config evidence markers, or requesting evidence.

## Assessment Workflow

### 1. Establish Scope and Architecture

Collect:

- CDE asset inventory;
- account data flow diagrams;
- network diagrams showing all CDE connections;
- firewall/NSC inventory, including physical, virtual, cloud-native, host-based, WAF/WAAP, IDS/IPS, VPN concentrators, and managed firewall controllers;
- wireless networks and their relationship to CDE;
- third-party, vendor, remote access, backup, monitoring, and administration paths;
- public-facing services and DMZ design.

Questions to answer:

- Where is PAN stored, processed, or transmitted?
- Which systems can impact CDE security even if they do not store PAN?
- Which firewalls enforce CDE boundaries?
- Which boundaries are trusted/untrusted?
- Which segmentation controls are being relied upon for scope reduction?
- Are cloud security groups, NACLs, Kubernetes policies, service meshes, or SDN constructs part of the firewall evidence set?

### 2. Build a Firewall-to-Requirement Matrix

For each in-scope firewall/NSC, map:

- hostname/device ID;
- platform/version;
- PCI role: perimeter, internal segmentation, wireless boundary, VPN, WAF/WAAP, IDS/IPS, cloud NSC, management-plane control;
- CDE zones/interfaces/security groups it protects;
- relevant PCI requirements;
- logging destination;
- management access path;
- configuration standard;
- review owner;
- change-control system;
- last rule review date;
- last backup date;
- last vulnerability scan/pen test coverage;
- known gaps.

### 3. Review Rulebase for PCI Intent

For each policy that touches CDE or CDE-impacting systems, record:

- rule ID/name;
- source zone/interface/network/object;
- destination zone/interface/network/object;
- source and destination addresses;
- service, port, and application;
- action;
- logging setting;
- security profiles attached;
- NAT relationship;
- business owner;
- ticket/change reference;
- business justification;
- PCI evidence marker in the native description/comment/tag field where the platform supports it;
- expiry/review date;
- hit count and last-hit timestamp if available;
- whether rule is inbound to CDE, outbound from CDE, management, backup, monitoring, payment processor, third-party, or public DMZ;
- whether the rule violates the standard or needs compensating/customized treatment.

### 4. Add PCI Evidence Markers to Firewall Configs

Where the firewall platform supports descriptions, comments, annotations, labels, or tags, mark PCI-relevant configuration directly in the firewall. This makes audits easier because policy exports, NAT exports, zone lists, and object inventories carry visible evidence markers instead of requiring an assessor to infer PCI relevance from external spreadsheets alone.

Use this as a configuration hygiene standard, not as the only source of truth. The marker should point to evidence; it does not replace diagrams, change tickets, rule recertification, or assessor review.

Recommended marker pattern:

```text
PCI:<scope-or-control> REQ:<requirement-id-or-control-area> OWNER:<team-or-app> REF:<ticket-or-evidence-id> PURPOSE:<short-business-purpose>
```

Examples:

```text
PCI:CDE REQ:1.3.1 OWNER:Payments REF:CHG12345 PURPOSE:Payment API inbound from DMZ
PCI:CDE-EGRESS REQ:1.3.2 OWNER:Payments REF:CHG12346 PURPOSE:Processor settlement HTTPS
PCI:SEGMENTATION REQ:11.4.5 OWNER:NetSec REF:SEGTEST-2026Q2 PURPOSE:Non-CDE to CDE deny boundary
PCI:PUBLIC-WEB REQ:6.4.2 OWNER:Ecommerce REF:WAF-2026Q2 PURPOSE:WAF/WAAP in front of checkout
```

Apply markers where possible:

- security policies/rules that permit, deny, inspect, log, or segment CDE traffic;
- final explicit deny rules protecting the CDE;
- NAT rules that publish CDE/DMZ services or translate CDE outbound traffic;
- zones, interfaces, VRFs, virtual routers, VPC/VNet constructs, address books, dynamic groups, and security groups that represent CDE, DMZ, management, wireless, untrusted, or non-CDE segments;
- VPN, remote-access, third-party, vendor, backup, monitoring, logging, DNS, NTP, and payment-processor paths involving the CDE;
- IDS/IPS, WAF/WAAP, URL filtering, anti-malware, TLS inspection, or threat profiles attached to PCI-relevant traffic.

Marker rules:

- Keep markers short enough to survive platform field-length limits and exports.
- Never put PAN, cardholder names, customer data, secrets, credentials, private keys, or sensitive incident detail in descriptions.
- Prefer stable references: change ticket, CMDB CI, control ID, application ID, evidence package ID, or rule-review ID.
- Use consistent tokens (`PCI:CDE`, `PCI:SEGMENTATION`, `REQ:1.3.1`) so exports can be searched deterministically.
- If the platform has both a tag field and a description field, use tags for machine filtering and descriptions for human audit context.
- If the platform lacks descriptions for a construct, maintain the marker in the adjacent object/rule name, tag, external source-of-truth, or rule-review export.
- Do not let markers justify bad policy. A rule with `PCI:CDE` still needs least privilege, approval, logging, and periodic review.

Red flags:

- `any any allow` into or out of CDE;
- broad CDE outbound Internet access;
- direct Internet access to systems that store cardholder data;
- unused rules with old hit counts;
- disabled rules kept without reason;
- rule names with no owner or business purpose;
- temporary rules without expiry;
- unlogged high-risk access;
- management access from user networks or untrusted networks;
- NAT exposing more services than policy intent suggests;
- PCI-relevant policies, NAT rules, zones, or objects with no description/tag/marker and no external evidence reference;
- object groups hiding broad networks;
- default vendor services enabled on management interfaces;
- policy shadowing or rule order that bypasses intended controls;
- IDS/IPS/WAF profiles attached but set to alert-only without documented rationale.

### 5. Validate Inbound Controls

Inbound to the CDE must be limited to necessary traffic, and all other traffic must be specifically denied. Validate:

- public services land in a DMZ or approved segment;
- only authorized ports/services are published;
- inbound from untrusted networks to trusted networks is limited to authorized public services or stateful responses;
- systems storing cardholder data are not directly accessible from untrusted networks;
- source restrictions are used where possible;
- VPN and vendor access terminate into controlled zones and require strong authentication;
- admin access is not exposed directly from the Internet;
- default deny is explicit and visible in policy;
- deny logs are useful enough for monitoring without overwhelming the SIEM.

### 6. Validate Outbound Controls

Outbound from the CDE must be limited to necessary traffic, and all other traffic must be specifically denied. Validate:

- CDE hosts do not have unrestricted Internet access;
- DNS, NTP, CRL/OCSP, update, logging, backup, monitoring, and payment processor flows are explicitly documented;
- outbound web access uses approved proxy/inspection paths when required;
- egress filtering blocks direct exfiltration paths where practical;
- service accounts and automated jobs have known destinations;
- deny events are monitored for unexpected outbound attempts;
- cloud metadata/API access is controlled when CDE workloads run in cloud.

### 7. Validate Segmentation

If segmentation reduces PCI scope, the controls must be tested. Validate:

- segmentation design is documented;
- non-CDE networks cannot reach CDE except through authorized policy;
- CDE cannot initiate unnecessary access to non-CDE networks;
- management and monitoring paths are included in scope analysis;
- identity, DNS, logging, virtualization, cloud control plane, backup, and jump systems are considered CDE-impacting where applicable;
- segmentation tests are performed by qualified personnel, cover both inside and outside perspectives, and are repeated after significant changes and at required intervals;
- test evidence includes methodology, source networks, destination networks, allowed/blocked results, findings, and remediation.

### 8. Validate Logging and Monitoring

Firewall/NGFW logs are part of PCI DSS monitoring evidence. Validate:

- traffic logs are enabled for CDE-relevant permits and denies according to risk;
- admin/system/config logs are enabled;
- IDS/IPS/WAF/threat logs are generated when those features are used;
- logs are sent to centralized log management/SIEM;
- time synchronization is correct;
- log access is restricted;
- log retention meets the entity’s PCI logging standard;
- alerts exist for high-risk events: CDE inbound deny spikes, new public exposure, admin login failures, policy changes, IPS critical alerts, WAF blocks, malware callbacks, unexpected CDE outbound traffic;
- daily review or automated alert review evidence exists;
- incident response procedures include firewall, IPS, WAF, and SIEM alerts.

### 9. Validate IDS/IPS and Web-App Protection

PCI DSS 11.5.1 expects intrusion-detection and/or intrusion-prevention techniques to monitor all traffic at the perimeter of the CDE and at critical points in the CDE, alert personnel to suspected compromises, and keep engines/baselines/signatures up to date. NGFW IPS can satisfy some or all of this if placement, visibility, signatures, alert routing, and response are evidenced.

PCI DSS 6.4.2 applies to public-facing web applications. It requires an automated technical solution deployed in front of public-facing web applications that continually detects and prevents web-based attacks, is actively running/up to date as applicable, generates audit logs, and is configured to block web-based attacks or generate an alert that is immediately investigated. A generic firewall policy is not automatically enough. Confirm whether the NGFW provides WAF/WAAP-grade controls, whether it is actually in front of the application, and whether application-layer attacks are detected/prevented.

## Evidence Request Checklist

Ask for these artifacts before claiming alignment:

- [ ] PCI scope statement and CDE asset inventory
- [ ] current network diagrams showing CDE, non-CDE, wireless, untrusted, trusted, DMZ, remote access, cloud, and third-party connections
- [ ] current cardholder data-flow diagrams
- [ ] firewall/NSC inventory and role map
- [ ] firewall configuration standards/baselines
- [ ] exported firewall configurations and policy/rulebase exports
- [ ] NAT, VPN, routing, and management-plane configurations
- [ ] rule owner/business justification/ticket data
- [ ] PCI markers in supported policy, NAT, zone, object, tag, and profile description/comment fields, plus an explanation for any platform where markers cannot be embedded
- [ ] last six-month firewall review evidence and remediation output
- [ ] change tickets for recent firewall/network changes
- [ ] admin access list and roles, MFA/authentication evidence mapped to Req 8.x (8.2.1 unique IDs, 8.3.1, 8.4.1–8.4.3 MFA, 8.5.1), and encrypted admin-protocol evidence mapped to Req 2.2.7.
- [ ] syslog/SIEM forwarding configuration and sample logs
- [ ] daily log review or alert workflow evidence
- [ ] IDS/IPS profile placement, update status, and alert examples
- [ ] WAF/WAAP or equivalent 6.4.2 evidence for public-facing web applications
- [ ] vulnerability scan reports, including ASV reports where applicable
- [ ] penetration test and segmentation test methodology/results/remediation
- [ ] incident response plan sections covering firewall/IPS/WAF/SIEM alerts
- [ ] cryptographic protocol/cipher inventory for VPN, admin UI, TLS inspection, and public services
- [ ] configuration backups and restore/integrity controls

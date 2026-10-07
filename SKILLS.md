# Skill catalog (detail)

Extended notes on the compliance and SRX operational playbooks that have them — what
each one covers, and when to reach for it. This is not the full inventory: the complete
one-line catalog of all 33 skills across every family is the
[Reference](./README.md#reference) section of the README, and every skill, listed here
or not, documents itself in its own `SKILL.md`. For the review record, see
[QUALITY.md](./QUALITY.md).

## Compliance Skills (detail)

### pci-ngfw-compliance

`pci-ngfw-compliance` is a PCI DSS v4.0.1 NGFW/firewall assessment playbook. It explains that an NGFW can support PCI DSS network security control evidence, but the device is not independently "PCI compliant."

Use it for:

- mapping firewall policy, NAT, zones, IDS/IPS, WAF/WAAP, logging, and segmentation controls to PCI DSS evidence expectations
- reviewing CDE inbound/outbound restrictions, default deny, payment processor paths, and public-facing service exposure
- preparing assessor-ready evidence requests, findings, and gap-analysis summaries
- adding short PCI evidence markers to firewall descriptions/tags for policies, NAT, zones, objects, and profiles where supported

### hipaa-ngfw-compliance

`hipaa-ngfw-compliance` is a HIPAA Security Rule NGFW/firewall assessment playbook. It explains that an NGFW can support reasonable and appropriate safeguards for ePHI, but HIPAA compliance is assessed at the covered entity or business associate program/environment level.

Use it for:

- mapping firewall policy, NAT, VPN, zones, IDS/IPS, WAF/WAAP, logging, and segmentation controls to HIPAA Security Rule safeguards
- reviewing ePHI access control, audit controls, person/entity authentication, transmission security, incident response, documentation, and business associate/vendor access evidence
- preparing compliance-ready evidence requests, findings, and risk-treatment recommendations
- adding short HIPAA evidence markers to firewall descriptions/tags where supported

### cmmc-nist-800-171-ngfw-compliance

`cmmc-nist-800-171-ngfw-compliance` is a CMMC Level 2 / NIST SP 800-171 NGFW/firewall assessment playbook. It explains that an NGFW can support CUI protection requirements, but CMMC/NIST 800-171 compliance is assessed at the contractor environment and CUI protection program level, not by certifying the firewall product alone.

Use it for:

- mapping firewall policy, NAT, VPN, zones, IDS/IPS, logging, segmentation, and remote-access controls to NIST 800-171 / CMMC evidence expectations
- reviewing CUI enclave scope, CUI data flows, boundary protection, external connections, public-system separation, audit controls, and system security plan evidence
- preparing assessor-ready evidence requests, findings, POA&M-style gaps, and remediation recommendations
- adding short CMMC/CUI evidence markers to firewall descriptions/tags where supported

### cis-controls-ngfw-compliance

`cis-controls-ngfw-compliance` is a CIS Critical Security Controls v8/v8.1 NGFW/firewall assessment playbook. It explains that an NGFW can support CIS safeguards, but CIS alignment is assessed across the implemented environment and security program, not by certifying the firewall product alone.

Use it for:

- mapping firewall policy, NAT, VPN, zones, IDS/IPS, logging, secure configuration, vulnerability management, and network monitoring controls to CIS Controls evidence expectations
- reviewing network infrastructure inventory, secure firewall baselines, administrative access, service-provider/vendor access, logging, malware/threat defenses, backup/recovery, incident response, and penetration/segmentation testing evidence
- preparing practical CIS-aligned evidence requests, findings, prioritized remediation actions, and risk-based roadmap items
- adding short CIS evidence markers to firewall descriptions/tags where supported

### iso27001-ngfw-compliance

`iso27001-ngfw-compliance` is an ISO/IEC 27001:2022 ISMS and Annex A firewall-control playbook. It explains that an NGFW can support selected controls, but certification applies to the scoped ISMS and its risk assessment, Statement of Applicability, policies, operation, audit, and continual-improvement evidence.

Use it for:

- mapping firewall policy, NAT, VPN, zones, logging, secure configuration, supplier access, change management, backups, and incident response to SoA/risk-treatment evidence
- reviewing network security, access control, configuration management, logging/monitoring, supplier access, vulnerability management, and corrective-action records
- preparing ISO audit evidence requests, firewall findings, corrective actions, and management-system caveats
- adding short ISO/ISMS evidence markers to firewall descriptions/tags where supported

### soc2-ngfw-compliance

`soc2-ngfw-compliance` is a SOC 2 Trust Services Criteria firewall-control playbook for service organizations, SaaS platforms, MSPs, and cloud providers. It focuses on system boundaries, report period, control matrix mapping, design, and Type II operating-effectiveness evidence.

Use it for:

- mapping firewall policy, NAT, VPN, WAF, security groups, logging, access review, change management, vendor access, and incident-response evidence to SOC 2 controls
- reviewing Trust Services Criteria support such as CC6 logical access, CC7 system operations, CC8 change management, CC9 risk mitigation, Availability, Confidentiality, and Privacy-supporting controls
- preparing SOC 2 evidence requests, control descriptions, findings, sample expectations, and exception remediation
- adding short SOC 2 evidence markers to firewall descriptions/tags where supported

### srx-disa-stig-compliance

`srx-disa-stig-compliance` is a source-pinned Juniper SRX assessment playbook for
the DISA Y25M01 NDM, ALG, IDPS, and VPN benchmarks. It preserves all three rule
identifiers and CAT severity while defaulting incomplete configuration,
operational, or manual evidence to Not Reviewed.

Use it for:

- selecting the NDM+ALG baseline and conditional IDPS/VPN components from SRX roles
- evaluating 148 rule-level entries without confusing missing evidence with a failed setting
- preparing CAT/status summaries, evidence-gap queues, CKL-ready source data, and POA&M-style remediation candidates
- separating formal STIG status from legacy or release-sensitive Junos guidance

## SRX Operational Skills (detail)

### srx-dynamic-ip-feed

`srx-dynamic-ip-feed` is an original operational playbook for Juniper SRX dynamic IP objects backed by HTTPS feed servers, informed by an attributed Juniper Community TechPost. Its reference is an independently written “Inspired by” note, not a page extract.

Use it for: configuring `security dynamic-address feed-server`; building `.tgz` bundle archive feeds and mapping `feed-name` paths; exposing feeds as policy objects; validating HTTPS server certificates with SRX PKI / SSL initiation profiles; HTTP basic-auth and mutual TLS client-certificate patterns; checking update behavior via access logs; troubleshooting `ipfd` download/auth/certificate/path errors; and `session-scan` / routing-instance reachability.

Key verification commands:

```text
show security dynamic-address summary
show security dynamic-address
show log messages | match ipfd
```

### srx-mpls-in-flow

`srx-mpls-in-flow` is an SRX MPLS L3VPN operational playbook synthesized from two Juniper Community TechPosts. It covers the Junos 24.2R1+ model where `family mpls` is packet-based while `family inet`/`inet6` remain flow-based, allowing stateful security services on MPLS VPN traffic.

Use it for: SRX secure PE / secure CPE designs; decoupled family forwarding controls; VRFs with route distinguishers, route targets, and SRX-required `vrf-table-label`; OSPF/LDP/MP-BGP `family inet-vpn` transport; Junos 24.2-style VRF-aware policy (`source-l3vpn-vrf-group` / `destination-l3vpn-vrf-group`); Junos 25.4R1+ VRF-to-zone mapping; VRF-aware NAT/AppID; PowerMode/RFP decisions; and MTU/label/BGP/policy/NAT troubleshooting.

Key verification commands:

```text
show security flow status
show mpls interface
show ldp neighbor
show route table bgp.l3vpn.0
show route table <vrf>.inet.0
show security policies hit-count
show security flow session extensive
show security nat source rule all
show security nat static rule all
```

### srx-nat

`srx-nat` is an original operational playbook for Juniper SRX NAT, informed by Juniper Community NAT/CGN/NAT64 articles, Juniper NAT documentation, and support troubleshooting guides. The attributed references are independently written “Inspired by” notes.

Use it for: source NAT with interface or pool translation; destination and static NAT for published servers and overlapping networks; rule processing order, rule-set specificity, and first-match behavior; proxy-ARP decisions; hairpin NAT / NAT reflection; NAT64 with DNS64 (`static-nat inet` + IPv4 source NAT); CGN/PBA design, paired address pooling, persistent NAT, and pool-exhaustion troubleshooting; `address-persistent` symptoms and TCP MSS caveats; and source/destination/static NAT troubleshooting with counters, sessions, and traceoptions.

Key verification commands:

```text
show configuration security nat | display set
show security nat source rule all
show security nat destination rule all
show security nat static rule all
show security nat source pool all
show security nat proxy-arp
show security flow session source-prefix <source> extensive
show security flow session destination-prefix <destination> extensive
```

### srx-policy

`srx-policy` is an SRX security policy design, migration, and troubleshooting playbook for Junos 23.x+ non-Branch SRX platforms. It enforces `security policies global` for generated greenfield, migration, and day-one onboarding policy, with zone-to-zone output limited to explicit existing-estate, isolated-exception, or customer-standard opt-outs. For URL filtering on supported Junos 23.4R1+ targets it recommends NextGen Web Filtering (NGWF / `ng-juniper`) as the preferred path, treating Enhanced Web Filtering (EWF / `juniper-enhanced`) as an existing-estate/compatibility path.

Use it for: deciding between global and legacy `from-zone ... to-zone ...` contexts; converting vendor rulebases into ordered SRX global policies; global address-book and application/application-set design; AppID / Application Firewall rule-sets; NGWF-first web filtering, EWF compatibility, and EWF-to-NGWF migration cautions; SecIntel and ATP placement; policy logging, counts, final deny, and commit safety; and troubleshooting hit-counts, AppFW counters, web-filtering counters, and flow sessions.

Key verification commands:

```text
show configuration security policies global | display set
show security policies hit-count
show security flow session source-prefix <source> extensive
show security application-firewall rule-set <rule-set-name>
show security utm web-filtering status
show security utm web-filtering statistics
show log messages | match -i "secintel|atp|utm|web-filter|threat"
```

Web-filtering guidance is intentionally opinionated but conservative: prefer NGWF for Junos 23.4R1+ greenfield/migration when platform, release, license, and cloud connectivity support it; keep EWF for existing-estate continuity or documented constraints; don't call EWF formally deprecated unless current Juniper docs say so; plan EWF-to-NGWF migration during downtime, preserve policy names, and verify `show security utm web-filtering category migrate-to-ng-juniper status`.

### srx-mnha

`srx-mnha` is a conservative, original SRX Multi-Node High Availability research/playbook skill informed by five attributed Juniper Community TechPosts. Because those sources contained some conflicting or ambiguous details, the main skill includes only non-conflicting operational guidance and keeps concise “Inspired by” notes in `references/`.

Use it for: comparing chassis cluster and MNHA models; routed/default-gateway/hybrid MNHA design; SRG0 and SRG1+ behavior; ICL design, security, reachability, and liveness checks; ICD/asymmetric-routing caveats; runtime object synchronization and Active/Warm session verification; config synchronization patterns; hybrid MNHA with eBGP, BFD, VIPs, and signal-route export policies; DHCP relay vs local DHCP behavior; and pre-cutover / troubleshooting checklists.

Key verification commands:

```text
show chassis high-availability information
show chassis high-availability services-redundancy-group <id>
show security flow session | match “HA State|HA Wing State|Session ID|In:|Out:”
show bgp summary
show bfd session
show dhcp server binding routing-instance <RI>
```

### srx-mnha-builder

`srx-mnha-builder` builds a two-node SRX MNHA pair from standalone nodes step by step through a Junos MCP server (Juniper junos-mcp-server or rust-junosmcp). Covers mode selection, preflight discovery, pair sheet, staged config with pre-push checks and approval gates, HA-activation reboot handoff, formation verification, and failover test. Maps each workflow capability (dry run, push with commit confirmed where supported, confirm, diff, batch commands) to both MCP servers' tools.

### srx-cluster-to-mnha

`srx-cluster-to-mnha` converts an existing SRX or vSRX chassis-cluster configuration into two node-local MNHA configurations. It inventories the cluster, interviews the user as an SRX architect (per-segment mode, SRG layout, failure detection, ICL), and produces a classified fidelity report and cutover runbook. Offline only; live push belongs to `srx-mnha-builder`.

### srx-autovpn-full-tunnel

`srx-autovpn-full-tunnel` is an SRX AutoVPN hub-and-spoke playbook for full-tunnel backhaul, where spokes send all non-local traffic up the tunnel and the hub provides centralized internet egress. It covers the dynamic `group-ike-id` gateway, traffic selectors + Auto Route Insertion (ARI), the single shared `st0.0`, hub source-NAT egress, spoke-to-spoke hairpin, and the anti-recursion route. It is original work inspired by and attributed to Jason Anderson's `srx-autovpn-backhaul-public` lab; the lab itself is not bundled or relicensed.

### srx-ipsec-hub-spoke

`srx-ipsec-hub-spoke` is an SRX static point-to-point route-based IPsec hub-and-spoke playbook with the same full-tunnel backhaul, but using one explicit IKE gateway, IPsec VPN, `st0` unit, and static route per spoke (no traffic selectors, no ARI) — routing alone scopes each tunnel. It covers per-spoke peering by WAN IP, hub source-NAT egress, spoke-to-spoke hairpin across `st0` units, the anti-recursion route, and when to switch to AutoVPN. It is original work inspired by and attributed to Jason Anderson's `srx-p2p-ipsec-public` lab; the lab itself is not bundled or relicensed.

### srx-chassis-cluster-proxmox

`srx-chassis-cluster-proxmox` is original operational work, not a vendor-derived summary. Juniper documents chassis cluster for two physically cabled appliances; this skill covers the hypervisor-to-Junos seam that appears when both nodes are Proxmox VE guests and the control link, fabric link and every reth leg become Linux bridge ports — a substitution whose failures are silent, because nothing logs a dropped frame. It rests on two independent builds: a reference cluster (cluster-id 2, Junos 24.4R1.9, five reth interfaces) that supplied the measurements, and a proving build (cluster-id 9, Junos 26.2R1.7) stood up on a different host by following the skill as written. The proving build corrected three claims before release — the fabric MTU requirement, which turned out to be latent and invisible to every device-side health check rather than an immediate failure; that `fxp0` cannot use a DHCP client in cluster mode; and the NIC-mapping verification procedure, replaced with a stronger one that checks reth virtual MACs against tap interfaces in the bridge forwarding table. Confirmed unchanged across both releases and both cluster-ids: the `netN` to `ge-0/0/(N-2)` mapping and the reth virtual-MAC formula. It also carries the per-NIC firewall anti-spoof trap that silently discards reth traffic while interfaces still report `Up`, and a worked post-mortem of an abandoned build with three independent faults. Values that were measured are stated as measurements; the one behavior not exercised — an undersized fabric under sustained load — is labelled untested rather than implied.

### srx-advpn

`srx-advpn` is an SRX Auto Discovery VPN playbook — hub-and-spoke IPsec that dynamically builds direct spoke-to-spoke shortcut tunnels so branch-to-branch traffic bypasses the hub. It covers suggester/partner roles, the shortcut lifecycle, the multipoint `st0` overlay, OSPF p2mp with dynamic-neighbors, the certificate-authentication requirement (IKEv2 PSK with dynamic `ike-user-type` is rejected on modern Junos), PKI enrollment, the chassis-cluster certificate-load gotcha, and the vSRX `No public key found` IKE_AUTH failure root-caused to the dynamic cert-gateway responder path (use per-spoke static-address cert gateways). Includes field notes from a vSRX ADVPN lab under `references/`.

### srx-initial-setup

`srx-initial-setup` brings a new or factory-reset Juniper SRX from its shipped state to a reachable, zoned, screened, and minimally policied device. It automates Day-0 and Day-1 setup for Branch SRX300/400, campus SRX1600/4120, and datacenter SRX4300/4700/5000 platforms. At 1.4.0 this skill has been run end-to-end against a live SRX345 from factory-default state through the baseline policy stage, with both read and write paths hardware-validated: the gate protocol, `commit confirmed`, per-stage verification, and the confirming commit were exercised on every stage. Eleven claims were corrected during validation, four of which were silent failures that would have reported gaps closed while changing nothing or degrading the device. Still unvalidated on hardware: rollback-on-verification-failure, the other Branch SKUs, and all campus and datacenter platforms. Its architecture is assess-first: it always opens with a read-only entry-state assessment that classifies the device into one of five states (`factory-default`, `bare`, `partial`, `configured`, or `unreachable`) and computes a dependency-ordered gap list. It closes only the gaps that are actually open, so re-running it against a finished device proposes nothing and reports a verification matrix instead. Every device write runs behind a per-stage approval gate under confirmed commit with a rollback timer. It handles the Branch factory-default configuration (the shipped zones, DHCP server, and policy on SRX300/400) as a first-class entry state rather than an afterthought, removing factory elements only after the replacement management path is established and verified. It ends with a read-only entitlement readout across three axes (entitled, configured, active) that routes onward to sibling skills rather than configuring feature sets itself. Covers five stages: access and recovery, management plane (hostname, DNS, NTP, management addressing), interfaces and zones with host-inbound-traffic rules, starter IDS screens, and a minimal baseline security policy (outbound DNS/web/NTP, default-deny with logging). The baseline policy is generated as global policy; when a zone-pair exception applies, the policy stage routes to `srx-policy` for zone-pair design on non-Branch platforms (Branch SRX zone-pair policy is unowned).

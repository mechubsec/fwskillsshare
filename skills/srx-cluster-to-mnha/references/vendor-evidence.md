# Vendor evidence for srx-cluster-to-mnha

Cited facts for the chassis-cluster to MNHA conversion skill. Other references cite these as `(E#)`. Pages were fetched through a summarizing fetcher on 2026-10-07; quotes are as returned. Lab-observed behavior is under `## Lab evidence`, cited as `(L#)`; it is single-platform field evidence, not Juniper documentation. Anything not sourced is under `## Uncertain`.

## Facts

### E1 — MNHA deployment types
- **Claim:** MNHA supports Layer 3 (route mode), Layer 2 (default-gateway mode) and hybrid deployments.
- **Source:** Multinode High Availability, Juniper TechLibrary, https://www.juniper.net/documentation/us/en/software/junos/high-availability/topics/concept/mnha-overview.html, retrieved 2026-10-07.

### E2 — SRG0 vs SRG1+
- **Claim:** SRG0 is active/active and "Manages security service from Layer 4-Layer 7 except IPsec VPN services." SRG1+ is active/backup and "Manages IPsec services and virtual-IP addresses with associated security services", with activeness priority and preemption options.
- **Source:** Two-Node Multinode High Availability, Juniper TechLibrary, https://www.juniper.net/documentation/us/en/software/junos/high-availability/topics/topic-map/mnha-introduction.html, retrieved 2026-10-07 (re-fetched for the quoted sentences).

### E3 — IPsec is handled on SRG1+, not SRG0
- **Claim:** The overview says "Typically, an IPsec termination IP (this can be a loopback for example) can be announced on SRG1+" so tunnels terminate on the active node. Together with E2 (SRG0 excludes IPsec VPN services), IPsec VPN must be anchored on an SRG1+. Overview wording is "typically ... can", so the hard requirement rests on E2's explicit SRG0 exclusion.
- **Source:** Multinode High Availability, Juniper TechLibrary, https://www.juniper.net/documentation/us/en/software/junos/high-availability/topics/concept/mnha-overview.html, retrieved 2026-10-07; plus E2. Corroborated for AWS: "IPsec VPN tunnel anchors at the SRG1" (E9).

### E4 — ICL runs over a routed path; Juniper says encrypt it, operator reports it is optional
- **Claim:** The interchassis link runs over a routed path (one or more revenue ports), not a dedicated L2 link. The overview glossary (verified verbatim against the raw page, 2026-10-08) says: "As the ICL link transmits private data, it is important to encrypt the link. You must encrypt the ICL using IPsec VPN." The Layer 3, default-gateway and hybrid example pages all configure `vpn-profile` on the peer-id and none marks it optional. An SRX SME operator states encryption is a recommendation, not a requirement in practice; that is operator testimony, not a Juniper statement. Treat encryption as strongly recommended and offered as a choice (none / PSK / PKI); an unencrypted ICL formed HA in the lab (L8), so for production keep encryption recommended.
- **Source:** Multinode High Availability, Juniper TechLibrary, https://www.juniper.net/documentation/us/en/software/junos/high-availability/topics/concept/mnha-overview.html, retrieved 2026-10-07.

### E5 — ICL binding and encryption prerequisites
- **Claim:** Recommended to bind the ICL to a loopback interface with more than one physical link (LAG/LACP) for path diversity. HA link encryption needs the Junos IKE package and an IKEv2 VPN profile; PKI-based encryption is available from Junos 22.3R1.
- **Source:** Two-Node Multinode High Availability, Juniper TechLibrary, https://www.juniper.net/documentation/us/en/software/junos/high-availability/topics/topic-map/mnha-introduction.html, retrieved 2026-10-07.

### E6 — Minimum release and ICL VPN specifics (SRX, Layer 3 example)
- **Claim:** The Layer 3 example requires "Junos OS Release 22.4R1 or later" (tested on 25.4R1), the IKE package (`request system software add optional://junos-ike.tgz`), IKE version `v2-only` for the HA VPN, a loopback `lo0.0` with floating IP, and an HA link interface. This is the example's stated requirement, not a platform-by-platform support matrix.
- **Source:** Example: Configure Multinode High Availability on SRX Series Firewalls in a Layer 3 Network, Juniper TechLibrary, https://www.juniper.net/documentation/us/en/software/junos/high-availability/topics/example/mnha-configuration-example.html, retrieved 2026-10-07.

### E7 — Per-platform support is in Feature Explorer
- **Claim:** The TechLibrary defers the list of supported SRX platforms and features to Juniper Feature Explorer; the overview page gives no per-platform minimum release.
- **Source:** Multinode High Availability, Juniper TechLibrary, https://www.juniper.net/documentation/us/en/software/junos/high-availability/topics/concept/mnha-overview.html, retrieved 2026-10-07.

### E8 — Configuration synchronization
- **Claim:** Configuration is replicated between nodes with `commit peers-synchronize`; logical/tenant system names and security features must match across nodes. Control and data plane state (sessions) is synchronized separately.
- **Source:** Two-Node Multinode High Availability, Juniper TechLibrary, https://www.juniper.net/documentation/us/en/software/junos/high-availability/topics/topic-map/mnha-introduction.html, retrieved 2026-10-07.

### E9 — vSRX support (public cloud) and limits
- **Claim:** vSRX MNHA is documented for AWS from Junos 22.3R1 (Azure and GCP also referenced). In public cloud, only SRG0 and SRG1 (active/backup) are supported; multiple active/active SRGs and cross-VPC are not. From 25.4R1 any ge-0/0/x may serve as the ICL on AWS.
- **Source:** Multinode High Availability in AWS Deployments, Juniper TechLibrary, https://www.juniper.net/documentation/us/en/software/junos/high-availability/topics/topic-map/mnha-support-for-vsrx.html, retrieved 2026-10-07.

### E10 — MNHA does not support transparent mode HA
- **Claim:** "Multinode High Availability does not support transparent mode high availability (HA)." Unlike chassis cluster, MNHA also supports public cloud and Layer 3 environments.
- **Source:** Multinode High Availability, Juniper TechLibrary, https://www.juniper.net/documentation/us/en/software/junos/high-availability/topics/concept/mnha-overview.html, retrieved 2026-10-07.

### E11 — Disabling a chassis cluster
- **Claim:** Operational command `set chassis cluster disable reboot` (or per-node `set chassis cluster cluster-id <id> node <0|1> reboot`) reboots the node out of cluster mode. Caveat: the automatically generated `node0`/`node1` groups are cluster-only, so the node may fail to load its configuration and need manual cleanup (see L4, L5 for what happens on vSRX).
- **Source:** Disable a Chassis Cluster, Juniper TechLibrary, https://www.juniper.net/documentation/us/en/software/junos/chassis-cluster-security-devices/topics/task/chassis-cluster-disabling.html, retrieved 2026-10-07. Command page title (seen in search results only, not fetched): "set chassis cluster disable reboot".

### E12 — Cluster vs MNHA architecture (community, not TechLibrary)
- **Claim:** Chassis cluster is one logical chassis with one active RE, global configuration, and control/fabric links on L2; MNHA runs two independent active REs with independent configuration and routing, linked by any routed path.
- **Source:** SRX clustering: from Chassis Cluster to MultiNode High Availability (Laurent Paumelle, Juniper Community), https://community.juniper.net/blogs/laurentp/2026/02/15/srx-from-chassis-cluster-to-mnha, retrieved 2026-05-14 (in-repo: skills/srx-mnha/references/source-srx-from-chassis-cluster-to-mnha.md); appearance in 2026-10-07 search results confirmed.

### E13 — MNHA monitoring options
- **Claim:** MNHA documents three monitoring types: BFD ("Monitors reachability to the next hop by examining the link layer along with the actual link"), IP ("Monitors the connectivity to hosts or services located beyond directly connected interfaces or next-hops") and interface ("Examines whether the link layer is operational or not"). From Junos 23.4R1, monitoring is extended to SRG0 as well as SRG1+ and grouped (flexible path monitoring) with weights per monitoring function.
- **Source:** Multinode High Availability Monitoring Overview, Juniper TechLibrary, https://www.juniper.net/documentation/us/en/software/junos/high-availability/topics/topic-map/mnha-monitoring-options.html, retrieved 2026-10-07. The fetch returned no CLI text; the `monitor bfd-liveliness` form in the translation map was relayed by a reviewer, not seen in the fetch, and is listed under `## Uncertain`.

## Lab evidence

All entries: lab-verified, vSRX 24.4R1.9 on KVM, 2026-10-08. One cluster (cluster-id 2), one release, one hypervisor. Treat as field evidence, not as a Juniper statement, and not as proof for physical SRX or other releases.

- **L1 - Interface rename after cluster disable.** After `set chassis cluster disable reboot` the NIC that was the cluster control link (em0, NIC1) becomes `ge-0/0/0`. Every other port shifts by one on both nodes: cluster `ge-0/0/N` (node0) and `ge-7/0/N` (node1) both become standalone `ge-0/0/(N+1)`; the fabric NIC `ge-x/0/3` becomes `ge-0/0/4`. A MAC-to-name map taken before load caught it. Physical SRX FPC renumbering: uncertain, not observed.
- **L2 - `load set` rejects `#` lines.** `load set` fails on a comment line with `unknown command: #`. Load files must carry no `#` section markers; the load still completed for the remaining lines.
- **L3 - HA mode change needs a reboot.** After committing `chassis high-availability` Junos warns "High Availability Mode changed, please reboot the device", and `show chassis high-availability information` reports "mode not configured" until the reboot. One activation reboot per node was enough.
- **L4 - Node groups stop applying after cluster disable.** `groups node0`/`node1` no longer apply, so the node loses its host-name and fxp0 address and needs console. If host-name and fxp0 are committed at top level and `apply-groups` is deleted before `set chassis cluster disable reboot`, the node stayed reachable on fxp0 (verified on node0, after node1 had left). The first node to leave shares configuration with its still-clustered peer, so that edit would hit both; it needs console.
- **L5 - Stale `ge-7/0/x` stanzas after disable.** The active configuration still holds `ge-7/0/x` stanzas that standalone Junos cannot parse ("fpc value outside range"). The candidate shows as modified, `configure exclusive` is refused ("configuration database modified"), and `show | compare` cannot diff. Shared `configure`, targeted cleanup plus merge, verification by section, `commit check`, then `commit` worked.
- **L6 - Merge load keeps existing cluster config; tooling redaction masks non-secret values.** A merge `load set` leaves the node's prior configuration, so the common block is largely already present, and lines whose values were redacted can be omitted from the load file (existing values persist). The Junos MCP masked non-secret values after the keyword `session` (`session-init`/`session-close` log options, screen `limit-session`). `| match` or `| count` on the device shows the true text; `show security screen` output stayed redacted.
- **L7 - Standalone first node: SRG1 HOLD, then ACTIVE.** A node with no peer showed SRG1 `HOLD` with VIPs `NOT INSTALLED`, then went `ACTIVE` by itself after about 60 s once its monitored links were up. Measured Phase 3 outage about 75 s (link shut to ACTIVE).
- **L8 - Unencrypted ICL forms HA.** With no `vpn-profile`, `commit check` passed and HA formed: `Encrypted: NO`, `Conn State: UP`, `Cold Sync Status: COMPLETE`.
- **L9 - Cold sync takes time.** After the second node's activation reboot, `Conn State` was `DOWN` then `IN PROGRESS`, and cold sync completed after about 60 to 90 s.
- **L10 - VIP uses the active node's physical MAC.** With only `virtual-ip N ip <ip>/<plen>` and `virtual-ip N interface <ifl>` in switching mode, the VIP answered with the active node's physical NIC MAC, not a virtual MAC. Failover relied on gratuitous ARP: about 1 s outage, and the ARP mapping changed to the new active node's physical MAC (no MAC moved between switch ports). Lab-observed later (vSRX 26.2R1.7, 2026-10-08): `virtual-ip <I> use-virtual-mac` (CLI help: "Use virtual mac for SRG role enforcement") makes ARP resolve to a `00:10:db:fe:xx:xx` virtual MAC; without `grid-id` the VMAC is per VIP, with `grid-id` VIPs on an SRG shared one. Juniper's MNHA preparation page uses `use-virtual-mac` in its sample config and describes `grid-id` as the VMAC/VIP-scale feature (25.4R1). Reservations or ARP pins tied to the old cluster vMAC (`00:10:db:ff:<cluster-id><rg>`) go stale.
- **L11 - Phase 5 order.** Form HA with the second node's revenue links down; Gate A passed (`Conn State` UP, `Cold Sync` COMPLETE, exactly one ACTIVE); enabling the links left the second node BACKUP (no preemption); Gate B passed. `request chassis high-availability failover services-redundancy-group 1 peer-id <peer>` swapped roles with no confirmation prompt.
- **L13 - ICL encryption does not commit on default vSRX.** lab-verified (commit check, 2026-10-08): on vSRX 26.2R1.7 and 24.4R1.9 in default non-FIPS mode, `ha-link-encryption` fails with `'ha-link-encryption' can be configure only in FIPS mode`; without it, `peer-id <P> vpn-profile` fails with `Referenced vpn object must have ha-link-encryption flag defined` and the IKE gateway with `IKEv2 requires bind-interface configuration as only route-based is supported`. FIPS mode and the junos-ike package were not tested (enabling FIPS mode zeroizes the config). Unencrypted ICL remains the only committable option there (L8). The ICL IKE gateway addressing question is untestable on non-FIPS vSRX.
- **L12 - Backups through tooling.** The Junos MCP ignored `| save`, and `rescue save` could not be verified through it; off-box copies were redacted. In a virtual lab the hypervisor snapshot was the dependable rollback.

## Uncertain

- Whether an unencrypted ICL is acceptable for production: it works on the lab platform (L8) and the operator calls it optional, but Juniper's overview says "You must encrypt the ICL using IPsec VPN." (E4). Single-platform evidence only.
- Official Juniper cluster-to-MNHA migration procedure: no authoritative source located (only the community post, E12).
- Per-platform SRX minimum Junos release and which SRX models support MNHA: no authoritative page text located; Feature Explorer not fetched (E7). The 22.4R1 figure (E6) is an example prerequisite only.
- vSRX MNHA on KVM/Proxmox (non-cloud): no authoritative source located. It formed and failed over on vSRX 24.4R1.9 on KVM (L8, L11); that is one platform and one release, not a support statement.
- ICD (inter-chassis data) definition: the overview page mentions an "ICD link" once without defining it; the srx-mnha skill's community sources cover it. No TechLibrary definition located.
- Exact list of cluster features unsupported in MNHA beyond transparent mode (E10): no authoritative source located.
- Whether `delete chassis cluster` in configuration is an alternative to the op command: no authoritative source located.
- Exact SRG IP-monitoring statement syntax and its flexible path `monitor-object` form: the monitoring page (E13) names the feature but the fetch showed no statements. Confirm from the Flexible path monitoring page or MNHA examples before emitting.
- Config-sync scope: E8 says only that configuration is replicated with `commit peers-synchronize`. Which statements replicate, and whether it can overwrite node-local configuration (interfaces, routing, `chassis high-availability`, SRG settings), is not documented in what was fetched. Do not rely on it for node-local isolation; confirm in a lab.
- `monitor bfd-liveliness ...` SRG statement: relayed by a reviewer, found in no repo source and not in the fetched monitoring page (E13). Unconfirmed; verify in lab. The skill shows it only as a candidate and never emits it.
- Whether `family ethernet-switching` on a non-transparent (branch switching) port is outside MNHA: E10 covers transparent mode HA only; no source located.
- Physical SRX behavior after `set chassis cluster disable reboot` (FPC renumbering, which port becomes the former control link): not observed; only vSRX is in `## Lab evidence` (L1).

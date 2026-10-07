# Vendor evidence for srx-cluster-to-mnha

Cited facts for the chassis-cluster to MNHA conversion skill. Other references cite these as `(E#)`. Pages were fetched through a summarizing fetcher on 2026-10-07; quotes are as returned. Anything not sourced is under `## Uncertain`.

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

### E4 — ICL runs over a routed path and must be IPsec-encrypted
- **Claim:** The interchassis link runs over a routed path (one or more revenue ports), not a dedicated L2 link, and "You must encrypt the ICL using IPsec VPN."
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
- **Claim:** Operational command `set chassis cluster disable reboot` (or per-node `set chassis cluster cluster-id <id> node <0|1> reboot`) reboots the node out of cluster mode. Caveat: the automatically generated `node0`/`node1` groups are cluster-only, so the node may fail to load its configuration and need manual cleanup.
- **Source:** Disable a Chassis Cluster, Juniper TechLibrary, https://www.juniper.net/documentation/us/en/software/junos/chassis-cluster-security-devices/topics/task/chassis-cluster-disabling.html, retrieved 2026-10-07. Command page title (seen in search results only, not fetched): "set chassis cluster disable reboot".

### E12 — Cluster vs MNHA architecture (community, not TechLibrary)
- **Claim:** Chassis cluster is one logical chassis with one active RE, global configuration, and control/fabric links on L2; MNHA runs two independent active REs with independent configuration and routing, linked by any routed path.
- **Source:** SRX clustering: from Chassis Cluster to MultiNode High Availability (Laurent Paumelle, Juniper Community), https://community.juniper.net/blogs/laurentp/2026/02/15/srx-from-chassis-cluster-to-mnha, retrieved 2026-05-14 (in-repo: skills/srx-mnha/references/source-srx-from-chassis-cluster-to-mnha.md); appearance in 2026-10-07 search results confirmed.

### E13 — MNHA monitoring options
- **Claim:** MNHA documents three monitoring types: BFD ("Monitors reachability to the next hop by examining the link layer along with the actual link"), IP ("Monitors the connectivity to hosts or services located beyond directly connected interfaces or next-hops") and interface ("Examines whether the link layer is operational or not"). From Junos 23.4R1, monitoring is extended to SRG0 as well as SRG1+ and grouped (flexible path monitoring) with weights per monitoring function.
- **Source:** Multinode High Availability Monitoring Overview, Juniper TechLibrary, https://www.juniper.net/documentation/us/en/software/junos/high-availability/topics/topic-map/mnha-monitoring-options.html, retrieved 2026-10-07. The fetch returned no CLI text; the `monitor bfd-liveliness` form in the translation map was relayed by the reviewer, not seen in the fetch.

## Uncertain

- Official Juniper cluster-to-MNHA migration procedure: no authoritative source located (only the community post, E12).
- Per-platform SRX minimum Junos release and which SRX models support MNHA: no authoritative page text located; Feature Explorer not fetched (E7). The 22.4R1 figure (E6) is an example prerequisite only.
- vSRX MNHA on KVM/Proxmox (non-cloud): no authoritative source located.
- ICD (inter-chassis data) definition: the overview page mentions an "ICD link" once without defining it; the srx-mnha skill's community sources cover it. No TechLibrary definition located.
- Exact list of cluster features unsupported in MNHA beyond transparent mode (E10): no authoritative source located.
- Whether `delete chassis cluster` in configuration is an alternative to the op command: no authoritative source located.
- Exact SRG IP-monitoring statement syntax and its flexible path `monitor-object` form: the monitoring page (E13) names the feature but the fetch showed no statements. Confirm from the Flexible path monitoring page or MNHA examples before emitting.

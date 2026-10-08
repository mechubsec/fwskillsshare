# Translation map

Phase 4 of the workflow. One row per cluster construct from the
[inventory](cluster-inventory.md), driven by the confirmed
[decision record](architect-interview.md#decision-record). Never translate a row
whose decision source is `unconfirmed` or `unresolved`. Cite evidence as `(E#)`
from [vendor-evidence.md](vendor-evidence.md); items under its `## Uncertain`
stay uncertain.

## Classification vocabulary

| Class | Meaning |
|---|---|
| `converted` | Direct translation, no behavior change the user must accept. |
| `caveat` | Translated, but behavior differs or depends on a user-confirmed decision; the fidelity report states the difference. |
| `manual` | No confident mapping; the report names the open question and who decides. Generate nothing for it. |
| `unsupported` | No MNHA equivalent. Say so; do not emit a lookalike. |

Row IDs `T1..T30` are stable; the output format, runbook and worked example
reference them. Do not renumber; append new rows at the end.

## Syntax rules for snippets

- Flat `chassis high-availability` form, as used by `srx-mnha` and `srx-mnha-builder` for current releases. The release-dependent grid form (still an open question in the upstream issue tracker) is not decided here; follow `srx-mnha` `references/srg-details.md` and the builder's `references/config-stages.md` for the target release. The `services-redundancy-group` stanzas below are the same in both forms apart from the peer reference.
- Values are `<PLACEHOLDER>` or RFC 5737/1918 addresses; unsupplied values are never invented.
- Stanzas come from the reviewed `srx-mnha` references; any stanza without a source there is not emitted.

## Map

| ID | Cluster construct | MNHA construct | Depends on decision | Class | Notes |
|---|---|---|---|---|---|
| T1 | `reth<N>` and its per-node child ports (`redundant-parent`), LACP | Node-local physical interface or node-local `ae` per node | Upstream column (per-node LAG / single link) | caveat | A local `ae` is valid only when the upstream is a real LAG to that node; reth LACP does not prove it. Reuse the example in `srx-mnha` [mnha-advanced-workflows.md#chassis-cluster-interface-migration](../../srx-mnha/references/mnha-advanced-workflows.md#chassis-cluster-interface-migration). Members and addresses are node-specific. Use the post-cluster port names from interview topic 2; on vSRX they are the cluster names shifted by one (`ge-0/0/N` and `ge-7/0/N` both become `ge-0/0/(N+1)`, L1), on a physical SRX uncertain, and always checked with the runbook's MAC-map STOP check; when they match on both nodes, zone bindings that name them are common, and names the user has not confirmed stay `<NODE1_..._IFD>` placeholders. |
| T2 | reth IP, segment gateway for static-gateway hosts | Default-gateway mode: SRG1+ `virtual-ip` plus a per-node interface address on the same subnet | Mode = default-gateway; Upstream vMAC tolerance; SRG | caveat | The gateway MAC changes on failover, unlike a reth that kept one virtual MAC. With `virtual-ip` alone the VIP answers with the active node's physical NIC MAC and failover relies on gratuitous ARP (L10, single platform); a virtual-MAC option was not tested. Reservations or ARP pins tied to the old cluster vMAC (`00:10:db:ff:<cluster-id><rg>`) go stale. Adjacent switch MAC-move limits, DAI or port-security can block it (interview topic 2). VIP value carries a prefix length in both sources: `srx-mnha` `mnha-advanced-workflows.md` shows `ip <VIP>/<PREFIXLEN>` and `srx-mnha-builder` `config-stages.md` defines `<VIP_IP>` as "address with mask". Cluster `gratuitous-arp-count` has no tunable here; verify ARP behavior in the lab. |
| T3 | reth IP, peering with routers | Routed mode: unique address per node on the segment, no VIP; neighbors re-peered with each node | Mode = routed | caveat | Neighbors must be reconfigured for two peers; a static-gateway host on a routed segment is stranded on failover. Where the segment mixes both, use hybrid (E1) with signal routes (T7). |
| T4 | Zone membership of `reth<N>.<U>` | Same zone, bound to the node-local `ae`/physical unit | Segment / reth row | converted | Zone, host-inbound and screens carry over; only the interface name changes. Zone names must match on both nodes. |
| T5 | RG0 (routing-engine mastership) | None: each node keeps its own RE and control plane | none | unsupported | Do not map RG0 to SRG0: SRG0 is active/active Layer 4-7 services except IPsec (E2), not RE mastership. Independent REs per E12. Routing, management and `commit` are per node (T12). |
| T6 | RG1+ with per-node `priority` | SRG1+ with `peer-id` and `activeness-priority` | SRG column; topic 3 owner node | caveat | SRG ids follow the user decision, not the RG number. Priority values are relative only; node0 and node1 get different values. vSRX in public cloud is limited to SRG0 and SRG1 (E9). |
| T7 | RG `preempt` | `preemption` on the SRG | SRG column; topic 3 preempt answer | caveat | Failback can blackhole traffic if ownership returns before routing converges (`srx-mnha` pitfall 8); default off unless the user confirmed. Hybrid steering stanza below. |
| T8 | RG `interface-monitor <if> weight <W>`; BFD detection chosen in interview topic 4 | SRG `monitor interface <IFD>` (flat) or `monitor monitor-object ... interface` (grid). BFD monitoring is a candidate only (see the BFD note below), not emitted | Detection column | caveat | Cluster weights and the 255 threshold do not translate numerically; thresholds are re-chosen with the user. Monitor the node-local interface that replaces each per-node child port (physical or `ae`), on its own node; a cluster monitor on `ge-0/0/3` and `ge-7/0/3` becomes one monitor per node. Exact forms: builder `config-stages.md` "SRG1 Common Block". |
| T9 | RG `ip-monitoring` (targets, retries, weights) | None generated. SRG IP monitoring exists (E13), grouped as flexible path `monitor-object`s with weights and thresholds from 23.4R1 | Detection column | manual | The exact IP-monitor statement is not verified (`## Uncertain` in vendor-evidence.md), so nothing is emitted. The user confirms it from Juniper's Flexible path monitoring page or the MNHA configuration examples; cluster weights and retries are re-chosen, not copied. `activeness-probe` is not an equivalent. BFD detection is a caveat under T8, not T9. |
| T10 | `fab0`/`fab1` fabric link | ICL (`peer-id ... interface`), routed; IPsec encryption recommended, but an unencrypted ICL formed HA in the lab (L8) | Global: ICL, HA link encryption | unsupported | Not equivalent: the fabric was an L2 data/session link; the ICL is a routed path; Juniper recommends IPsec encryption and the operator reports it is optional (E4, E5, E6). Build the ICL as new configuration; never copy fab member ports. The freed fab NIC may be reused as an ICL link by decision (renamed on vSRX, L1), and the freed former control NIC (vSRX `ge-0/0/0` after disable) is a candidate second link; each needs addressing and routing as a routed ICL. ICD is uncertain (see `## Uncertain`). |
| T11 | Control link/ports, `heartbeat-*`, `control-link-recovery` | None; liveness comes from the ICL `liveness-detection` | Global: ICL | unsupported | No MNHA equivalent; record in the fidelity report. Removing the control cabling is a physical runbook step. |
| T12 | `groups node0`/`node1`, `apply-groups "${node}"`, `commit` of a single config | Two node-local configs: common part and node-local part; MNHA can replicate configuration with `commit peers-synchronize` (E8); which statements it replicates and whether node-local statements are protected is unverified (see Uncertain); this skill's output does not depend on it | Global: config-sync split | converted | Expand each group into its node's file; delete the `node0`/`node1` groups and the cluster stanza (cluster-only; may block load, E11). Common sync needs matching logical/tenant names (E8). |
| T13 | fxp0 per-node address, `backup-router` | Same per-node fxp0 / management config | Config-sync split | converted | Stays node-local; never synced. |
| T14 | IKE gateway, `external-interface reth<N>.<U>` | IPsec in SRG1+: floating `lo0` address, `external-interface lo0.<U>`, `managed-services ipsec` | SRG column (IPsec anchor SRG); Purpose | caveat | IPsec cannot anchor on SRG0 (E2, E3). Needs the IKE package and matching zone/routing-instance for loopback and receiving interface; IKEv1 aggressive-mode sessions are not synced. See `srx-mnha` mnha-advanced-workflows.md "IPsec with Multiple Routing Instances". **Not pushable via `srx-mnha-builder`**: its SKILL.md says never add `managed-services ipsec` and its `config-stages.md` errors on it; this output is hand-reviewed and operator-applied. |
| T15 | `security nat proxy-arp interface reth<N>.<U>` | Prefer routed next-hop to the pool; otherwise per-node proxy-arp pinned to the active node | Mode; SRG | caveat | Both independent nodes answering ARP for one translated address breaks return traffic. See `srx-mnha` "NAT and Deterministic Routing". |
| T16 | DHCP server or relay on a reth | Relay to an external server (preferred); local server only as split pools per node | Mode; Purpose | caveat | Lease databases are not assumed to sync; pools must not overlap. See `srx-mnha` "DHCP on MNHA". |
| T17 | Routing protocols and static routes on reth | Per-node routing config; BGP/OSPF export steered by SRG signal routes in routed/hybrid | Mode; Detection | caveat | Neighbor addresses, router-ids and metrics are node-local. Signal-route stanzas below; export policies in `srx-mnha` mnha-config-patterns.md. |
| T18 | `logical-systems`, `tenants` | No confident mapping | none | manual | Names must match across nodes (E8); clustered-LSYS behavior is uncertain. Ask the user; generate nothing. |
| T19 | Multicast (PIM, IGMP, MLD) on a reth | No authoritative MNHA behavior located | none | manual | Uncertain; flag in the report and validate in a lab before cutover. |
| T20 | Transparent-mode or L2-bridge segments (bridge domains, zones holding `family ethernet-switching` units) | None | none | unsupported | MNHA does not support transparent mode HA (E10); this row covers transparent-mode or L2-bridge segments only. Plain `family ethernet-switching` access ports on a branch SRX are not shown to be covered by E10: treat those as `manual` and uncertain. |
| T21 | Platform/release capability of the source model | MNHA support verdict | Global: platform/release | caveat | Supported-by-example only (22.4R1 example, E6) or uncertain; Feature Explorer follow-up required (E7). |
| T22 | Security policies, address books, applications, and source, destination or static NAT rules (not proxy ARP) | Same statements in the common block; zone and policy names are unchanged | Config-sync split | converted | Policy logic is unchanged; verify NAT pools on a reth subnet against T15 and sessions are re-established after cutover. Rules that name a reth explicitly are T30. |
| T23 | `chassis cluster cluster-id`, `reth-count`, other cluster-only statements | None | none | unsupported | Cluster-only (E11); delete from both node files. |
| T24 | `system login`, `root-authentication`, `system services`, `snmp`, `system syslog` (and NTP, name-servers) outside the node groups | None generated; stays on each node | Config-sync split | manual | The node files omit these, so a bare `delete` plus `load set` would remove management access. Runbook uses targeted deletes to keep them; the operator confirms the baseline, or supplies it for a rebuilt node. Secrets are never reproduced. |
| T25 | A reth or segment the operator retires, and monitors, zone members or references to it | None generated for the retired segment | Interview topic 1: retire | caveat | Records a deliberate `retired` outcome (the four classes have no separate one): remove its zone binding, monitors (an SRG monitor on a retired interface keeps the SRG unhealthy) and routes; list each removal. |
| T26 | Secondary address on a reth, or an unnumbered reth (`family inet` without an address) | Per-node secondary address, a second `virtual-ip`, or dropped; unnumbered: the zone and unit stay, nothing is addressed | Interview topic 1 | manual | Ask which: per-node address, second VIP, or obsolete. Never choose silently. |
| T27 | `outbound-ssh` or other management-plane onboarding in node groups (per-node device-id, MCP or netconf users) | Node-local config after expansion | Config-sync split | caveat | Re-onboarding to the management service is a runbook follow-up; per-node ids stay node-local. |
| T28 | Licenses and security services (AppID, AAM, GeoIP, screens, PKI, dynamic-address) | Common block for config; licenses and certificates per node | Config-sync split | caveat | Each node needs its own license and certificate; verify parity after cutover. |
| T29 | ICL zone host-inbound requirements | Zone holding the ICL allows the HA protocols (including BFD, `srx-mnha` pitfall 22) | ICL | caveat | Comes from the `srx-mnha-builder` skill; not in the cluster source. |
| T30 | NAT rule-sets or other policy statements that name a reth explicitly (`from interface reth<N>.<U>`, `to interface reth<N>.<U>`, any interface-bound match) | Same rule with the interface remapped through T1, node-local where physical names differ between nodes | Config-sync split | caveat | The reth no longer exists, so the unchanged statement would not commit or would never match. Remap each reference; if names differ per node the rule is node-local, not common. `then source-nat interface` follows the egress interface and needs no edit. |

## Stanza reference

Generated per node; `<LOCAL_ID>`/`<PEER_ID>` are `1`/`2` on node0 and `2`/`1` on node1.

**T1 (node0, upstream is a real LAG):** see the linked `srx-mnha` example; do not re-derive it.

**T2 default-gateway VIP and T6/T7 SRG:**

```junos
set chassis high-availability services-redundancy-group <SRG> peer-id <PEER_ID>
set chassis high-availability services-redundancy-group <SRG> deployment-type switching
set chassis high-availability services-redundancy-group <SRG> activeness-priority <PRIORITY>
set chassis high-availability services-redundancy-group <SRG> preemption
set chassis high-availability services-redundancy-group <SRG> virtual-ip 1 ip <VIP>/<PLEN>
set chassis high-availability services-redundancy-group <SRG> virtual-ip 1 interface <IFL>
```

`preemption` only when T7 was confirmed. Routed segments use `deployment-type routing`, which also needs this statement (commit fails without it, `srx-mnha` `srg-details.md`); aim it at a real data-segment address, never the ICL. Hybrid uses `hybrid`.

```junos
set chassis high-availability services-redundancy-group <SRG> activeness-probe dest-ip <PROBE_DST> src-ip <PROBE_SRC>
```

**T8 interface monitor (flat form):**

```junos
set chassis high-availability services-redundancy-group <SRG> monitor interface <IFD>
```

**T8 BFD monitoring, unconfirmed - no source located; verify in lab before use. Candidate only, never emitted as generated output (the fidelity row says "BFD timers/syntax to verify"):** the form below was relayed by a reviewer and appears in no repo source or fetched page (E13 returned no CLI text).

```junos
set chassis high-availability services-redundancy-group <SRG> monitor bfd-liveliness <SRC_IP> <DST_IP> routing-instance <RI> <single-hop|multihop> <IFD>
```

No IP-monitor stanza is shown either (T9): its syntax is unverified.

**T17 hybrid/routed signal routes:**

```junos
set chassis high-availability services-redundancy-group <SRG> active-signal-route <ACTIVE_SIGNAL_ROUTE>
set chassis high-availability services-redundancy-group <SRG> backup-signal-route <BACKUP_SIGNAL_ROUTE>
```

Signal prefixes are reserved and never production prefixes; BFD timers stay `<PLACEHOLDER>` unless supplied.

**T14 IPsec anchor:**

```junos
set interfaces lo0 unit <UNIT> family inet address <FLOATING_VPN_IP>/32
set policy-options prefix-list <IKE_GW_PREFIX_LIST> <FLOATING_VPN_IP>/32
set chassis high-availability services-redundancy-group <SRG> prefix-list <IKE_GW_PREFIX_LIST> routing-instance <RI>
set chassis high-availability services-redundancy-group <SRG> managed-services ipsec
set security ike gateway <GW> external-interface lo0.<UNIT>
set security ike gateway <GW> local-address <FLOATING_VPN_IP>
```

Every IKE and IPsec statement that depends on the gateway (proposals, policies, `ipsec vpn`, `st0` zone membership, and the PSK, which stays `<redacted>` and is re-entered by the operator) moves into the operator-applied block with it, so the common block never references an uncommitted gateway. Also add the prefix-list binding from the `srx-mnha` floating-loopback pattern.

**T10/T11 replacement (new ICL, not a translation):** flat form from builder `config-stages.md`. The `vpn-profile` line is optional: emit it only when encryption is chosen (interview topic 5). `vpn-profile` placement is flat-form only; for grid it is not field-confirmed (`config-stages.md` note at line 190), so rely on a device dry run.

```junos
set chassis high-availability local-id <LOCAL_ID> local-ip <LOCAL_ICL_IP>
set chassis high-availability peer-id <PEER_ID> peer-ip <PEER_ICL_IP>
set chassis high-availability peer-id <PEER_ID> interface <ICL_HA_IFL>
set chassis high-availability peer-id <PEER_ID> liveness-detection minimum-interval <LIVENESS_MIN>
set chassis high-availability peer-id <PEER_ID> liveness-detection multiplier <LIVENESS_MULT>
# optional: only if ICL encryption is chosen (recommended)
set chassis high-availability peer-id <PEER_ID> vpn-profile <HA_VPN_PROFILE>
set chassis high-availability services-redundancy-group 0 peer-id <PEER_ID>
```

## Rules for the fidelity report

- Every inventory row yields at least one `T#`; constructs matching none are `manual` with the reason.
- `unsupported` rows (T5, T10, T11, T20, T23) are listed even when nothing is generated, with their replacement action.
- A `caveat` row states the behavior difference in one sentence; a `manual` row states the question and the owner.

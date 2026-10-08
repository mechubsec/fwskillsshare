# Cluster inventory

Phase 2 of the workflow. Extract everything the cluster does from the supplied
`display set` configuration (and `show chassis cluster status` if given), then
**show the user the inventory table before asking any design question**. The
interview in [architect-interview.md](architect-interview.md) works from this
table; do not interview from memory of the config.

Rules: report what the evidence shows, never guess a missing value (write
`<UNKNOWN>` in the cell), and write secrets as `<redacted>`. If the config is
hierarchical, convert mentally to `display set` or ask for `| display set`.

**Evidence commands.** Besides the configuration, collect `show version`,
`show chassis cluster status`, `show chassis cluster interfaces`,
`show chassis cluster information` and `show interfaces terse`. The cluster-id
and node ids are operational state and are not in the set configuration; take
them from the status output, not from `set chassis cluster cluster-id`.

**Large configurations.** A real cluster can be well over 1,000 lines and
exceed a tool's output limit. Fetch by subtree (`show configuration interfaces`,
`security zones`, `chassis`, `groups`, `protocols`, `routing-options`), and
summarize `security policies`, `address-book`, `applications` and `nat` with
counts instead of one row each.

**Redaction hides non-secret values.** Tooling may redact more than secrets: in
the lab a management tool masked values that follow the keyword `session`
(`log session-init`, `log session-close`, screen `limit-session`), 57 lines in
one config (L6). Treat any `[REDACTED]` on a non-secret leaf as lost data:
recover the true text on the device with `| match` or `| count` (the match shows
the real text), or omit the line from the merge load so the device keeps its
value. Never guess it. Some outputs (`show security screen`) stay redacted, so
list the unrecoverable ones under open facts.

## Extraction checklist

Run each pattern against the config. "Per node" means resolve `groups node0` /
`groups node1` and `apply-groups "${node}"` first (see Node groups).

| # | Construct | Locate with | Record |
|---|---|---|---|
| 1 | Cluster basics | `set chassis cluster cluster-id`, `set chassis cluster reth-count`, `set chassis cluster control-link-recovery`, `set chassis cluster heartbeat-*` | reth-count, heartbeat timers |
| 2 | Reth interfaces | `set interfaces reth<N> ...` | units, VLAN ids, addresses (the reth address is the segment gateway), zone. Two addresses on one reth: record both, mark which is primary or preferred, and ask which is the gateway. A reth with `family inet` and no address is `unnumbered` (record its zone and what uses it) |
| 3 | Reth children | `set interfaces <phys> gigether-options redundant-parent reth<N>` and `fastether-options redundant-parent` | physical port per node (child on node0 vs node1), speed |
| 4 | Reth LACP | `set interfaces reth<N> redundant-ether-options lacp active\|passive`, `minimum-links`, `redundancy-group <N>` | LACP mode, which RG owns the reth |
| 5 | Redundancy groups | `set chassis cluster redundancy-group <N> node 0\|1 priority <P>`, `redundancy-group <N> preempt`, `redundancy-group <N> gratuitous-arp-count <C>` | RG id, per-node priority, preempt, gratuitous-arp-count |
| 6 | RG monitoring | `redundancy-group <N> interface-monitor <if> weight <W>`; `redundancy-group <N> ip-monitoring ...` | monitored objects, weights, thresholds, targets, retries |
| 7 | Fabric | `set interfaces fab0\|fab1 fabric-options member-interfaces <if>` | member ports per fab |
| 8 | Control ports | `set chassis cluster control-ports fpc <N> port <M>`; none on vSRX | control port mapping |
| 9 | Node groups | `set groups node0\|node1 ...`, `set apply-groups "${node}"` | node-specific hostname, fxp0, backup-router, syslog host, anything else under the groups |
| 10 | fxp0 | `set groups node<N> interfaces fxp0 unit 0 family inet address ...` | per-node management address, `backup-router`, `mgmt_junos` use |
| 11 | Zones | `set security zones security-zone <Z> interfaces reth<N>.<U>` | reth to zone map, host-inbound services |
| 12 | Routing | `set protocols ospf\|bgp\|rip\|isis`, `set routing-options static`, `routing-instances` | which protocols run on which reth, neighbors, BFD, graceful restart |
| 13 | IPsec on a reth | `set security ike gateway <G> external-interface reth<N>.<U>`; `set security ipsec vpn <V> bind-interface st0.<U>` | gateways bound to a reth, local-address, VPN names, st0 units |
| 14 | NAT proxy ARP | `set security nat proxy-arp interface reth<N>.<U> address ...` and `proxy-ndp` | reth, proxied ranges |
| 15 | DHCP | `set system services dhcp-local-server`, `set forwarding-options dhcp-relay`, `set access address-assignment pool` | server vs relay, interface, pools |
| 16 | Logical / tenant systems | `set logical-systems <N>`, `set tenants <N>` | names, interfaces owned |
| 17 | Multicast | `set protocols pim`, `igmp`, `mld`, `set routing-options multicast` | on which reth |
| 18 | Transparent / L2 | `family ethernet-switching` on interface units, `set vlans`, `set bridge-domains`, zones containing such interfaces | transparent mode (`unsupported`) vs other L2 (`manual`, uncertain) |
| 19 | Policies, address books | `set security policies`, `set security address-book`, `set applications` | zone pairs, or `match from-zone/to-zone` on global policies, policy names (as counted rows) |
| 20 | NAT rules | `set security nat source\|destination\|static` (proxy-arp is #14) | rule-sets, pools |
| 21 | System access and logging | `set system login`, `root-authentication`, `set system services`, `set snmp`, `set system syslog`, `set system ntp\|name-server` outside the node groups | users, services, snmp, syslog hosts (never secrets); these are not in the node files (T24) |
| 22 | References to reth addresses outside interfaces | `source-address`, `source-interface` under `system syslog` and `security log`, NAT `interface`, route next hops, `inet` filters, secondary addresses | each reference, since it breaks when the reth disappears and must move to a per-node address, a VIP, or be dropped |
| 23 | Management plane in node groups | `outbound-ssh` (for example Security Director Cloud onboarding with a per-node device-id), management users, `mgmt_junos` or management-instance | per-node values; re-onboarding is a runbook follow-up |
| 24 | Security services and `lo0` | AppID, AAM, screens, PKI, dynamic-address, licenses; `lo0` and the RG0 pseudo-interface seen in `show chassis cluster interfaces` | what must match on both nodes (licenses per node) |

### Node groups

The `groups node0` and `groups node1` blocks and `apply-groups "${node}"` are
cluster-only plumbing (E11). Expand each group into a per-node column, and list
every statement inside them: these are the facts that become node-local
configuration in the MNHA output. Hostname, fxp0 address, and syslog source
frequently live here.

### Reth to physical mapping

For each `reth<N>`, list node0 child ports and node1 child ports. A reth with
two children per node is a per-node LAG upstream; a reth with one child per node
is a single link per node. This drives the upstream LAG question in the
interview (topic 2).

## Manual candidates

Mark these `manual` in the table Notes column; the translation phase must not
convert them silently.

- **Logical systems and tenant systems.** MNHA requires matching logical or
  tenant system names across nodes (E8); how a clustered LSYS or tenant maps is
  not documented here, so treat as manual and uncertain.
- **Multicast** (PIM, IGMP, MLD) on a reth: no authoritative MNHA behavior
  located; manual and uncertain.
- **Transparent mode**: MNHA does not support transparent mode HA (E10); mark
  `unsupported`, not `manual`, and say so.
- **Other L2 / `family ethernet-switching` (non-transparent)**: E10 covers
  transparent mode only; mark `manual` and uncertain (see vendor-evidence.md
  Uncertain, T20).

## Inventory table

Produce exactly this table, one row per construct instance, except policy, nat, address-book and application constructs, which are one counted row each (for example `policy | 101 global policies | - | - | zones trust, untrust | counted`). Later phases consume
these columns verbatim.

```
| Construct | Name | node0 | node1 | Attached services | Notes |
|---|---|---|---|---|---|
```

Column rules:

- **Construct**: `cluster`, `reth`, `redundancy-group`, `fab`, `control-port`, `fxp0`, `zone`, `policy`, `nat`, `routing`, `ike-gateway`, `nat-proxy-arp`, `dhcp`, `lsys`, `tenant`, `multicast`, `l2`, `system`, `service` (security services, onboarding), `lo0`.
- **Name**: `reth0`, `RG1`, `fab0`, `trust`, and so on.
- **node0 / node1**: the per-node member (child port, priority, fxp0 address); `-` when not per-node.
- **Attached services**: zone, routing protocols, IKE gateways, NAT, DHCP on that construct.
- **Notes**: `manual`, `unsupported`, `<UNKNOWN>`, preempt, monitoring, anything the interview must resolve.

Example rows (synthetic, RFC 5737):

```
| reth | reth1 | ge-0/0/1 | ge-5/0/1 | zone trust; OSPF area 0; DHCP relay | RG1; LACP active; 192.0.2.1/24 |
| redundancy-group | RG1 | priority 200 | priority 100 | reth1, reth2 | preempt; interface-monitor ge-0/0/0 weight 255 |
| routing | static | - | - | 0.0.0.0/0 via 198.51.100.1 | backup-router on fxp0 |
| lsys | LSYS-A | - | - | - | manual |
```

After the table, list **open facts** (anything `<UNKNOWN>`) and ask the user for
them (plain text or runtime intake; the catalog has no entry for open facts, so count them against the three-question round limit only when asked through the native tool) before the interview, then move to
[architect-interview.md](architect-interview.md).

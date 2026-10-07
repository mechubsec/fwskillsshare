# Cluster inventory

Phase 2 of the workflow. Extract everything the cluster does from the supplied
`display set` configuration (and `show chassis cluster status` if given), then
**show the user the inventory table before asking any design question**. The
interview in [architect-interview.md](architect-interview.md) works from this
table; do not interview from memory of the config.

Rules: report what the evidence shows, never guess a missing value (write
`<UNKNOWN>` in the cell), and write secrets as `<redacted>`. If the config is
hierarchical, convert mentally to `display set` or ask for `| display set`.

## Extraction checklist

Run each pattern against the config. "Per node" means resolve `groups node0` /
`groups node1` and `apply-groups "${node}"` first (see Node groups).

| # | Construct | Locate with | Record |
|---|---|---|---|
| 1 | Cluster basics | `set chassis cluster reth-count`, `set chassis cluster control-link-recovery`, `set chassis cluster heartbeat-*` | reth-count, heartbeat timers |
| 2 | Reth interfaces | `set interfaces reth<N> ...` | units, VLAN ids, addresses (the reth address is the segment gateway), zone |
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
| 18 | Transparent / L2 | `family ethernet-switching` on interface units, `set vlans`, `set bridge-domains`, zones containing such interfaces | any L2 or transparent segment |

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
- **Transparent or L2 segments**: MNHA does not support transparent mode HA
  (E10); mark `unsupported`, not `manual`, and say so.

## Inventory table

Produce exactly this table, one row per construct instance. Later phases consume
these columns verbatim.

```
| Construct | Name | node0 | node1 | Attached services | Notes |
|---|---|---|---|---|---|
```

Column rules:

- **Construct**: `reth`, `redundancy-group`, `fab`, `control-port`, `fxp0`, `zone`, `routing`, `ike-gateway`, `nat-proxy-arp`, `dhcp`, `lsys`, `tenant`, `multicast`, `l2`.
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
them via the runtime intake before the interview, then move to
[architect-interview.md](architect-interview.md).

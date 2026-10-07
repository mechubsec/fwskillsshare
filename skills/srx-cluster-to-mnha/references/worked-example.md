# Worked example

End-to-end run of the workflow against [cluster-sample.set](cluster-sample.set)
(synthetic, RFC 5737/1918 addresses, secrets `<redacted>`). The interview answers
are sample answers chosen to exercise each path. Output is abridged to the lines
that show the pattern.

> Draft output from offline analysis. Not validated on a device and not
> production-ready.

## 1. Inventory ([cluster-inventory.md](cluster-inventory.md))

```
| Construct | Name | node0 | node1 | Attached services | Notes |
|---|---|---|---|---|---|
| cluster | cluster-1 | - | - | - | reth-count 3; no control-port lines (vSRX) |
| reth | reth0 | ge-0/0/3, ge-0/0/4 | ge-7/0/3, ge-7/0/4 | zone untrust; eBGP AS64496 to 198.51.100.1; source NAT pool | RG1; LACP active; 198.51.100.2/28 |
| reth | reth1 | ge-0/0/5 | ge-7/0/5 | zone trust; source NAT | RG1; 10.10.10.1/24 |
| reth | reth2 | ge-0/0/6 | ge-7/0/6 | zone dmz; IKE gateway gw-branch | RG1; 203.0.113.1/28 |
| redundancy-group | RG0 | priority 200 | priority 100 | - | - |
| redundancy-group | RG1 | priority 200 | priority 100 | reth0, reth1, reth2 | preempt; gratuitous-arp-count 4; interface-monitor ge-0/0/3 / ge-7/0/3 weight 255 |
| fab | fab0 / fab1 | ge-0/0/2 | ge-7/0/2 | - | unsupported |
| fxp0 | fxp0 | 192.0.2.10/24 | 192.0.2.11/24 | hostnames srx-cl-a / srx-cl-b | backup-router 192.0.2.254 |
| zone | untrust, trust, dmz | - | - | reth0.0, reth1.0, reth2.0 + st0.0 | dmz has host-inbound ike |
| routing | bgp isp, static default | - | - | via 198.51.100.1 | AS 64512 |
| policy | allow-web | - | - | trust to untrust | - |
| nat | trust-to-untrust | - | - | source pool 198.51.100.10-.12 | - |
| nat-proxy-arp | reth0.0 | - | - | 198.51.100.10-.12 | pool inside the ISP subnet |
| ike-gateway | gw-branch | - | - | external-interface reth2.0; ipsec vpn-branch on st0.0 | peer 203.0.113.50; PSK `<redacted>` |
```

Open facts: platform model and Junos release are `<UNKNOWN>`; asked through runtime intake.

## 2. Interview summary ([architect-interview.md](architect-interview.md))

| Round | Topic | Proposal | Sample answer |
|---|---|---|---|
| 1 | Purpose and mode | reth0 has an eBGP router: routed. reth1, reth2 host static gateways: default-gateway | Confirmed. Pool reached by routed next-hop, hosts have a static gateway |
| 2 | Upstream and port names | Per-node LAG on reth0; single link elsewhere | Own LAG per node, switch tolerates MAC move, same port names after cluster break (`ge-0/0/3`...) |
| 3 | SRG design | RG1 owns three modes, so split: SRG2 routed for reth0, SRG1 switching for reth1 and reth2 and the IPsec anchor | Confirmed; node0 owns both, no preempt |
| 4 | Detection | BFD to the ISP on SRG2, interface monitor on SRG1 | Confirmed |
| 5 | ICL and encryption | Dedicated ports, PKI, no ICD | Confirmed; ICL addresses not supplied |
| 6 | Config-sync split | Policy, NAT, zones common; interfaces, routing, hostname node-local | Confirmed |
| 7 | Platform | Ask model and release | Not decided, so verdict uncertain |

## 3. Decision record

```
| Segment / reth | Purpose | Mode | Upstream | SRG | Detection | Decision source |
|---|---|---|---|---|---|---|
| reth0 (untrust) | ISP router, eBGP | routed | per-node LAG ae0 | SRG2 | BFD + interface | user-confirmed (round 1) |
| reth1 (trust) | Static-gateway hosts | default-gateway | single link, vMAC ok | SRG1 | interface | user-confirmed (round 1) |
| reth2 (dmz) | Static-gateway servers, IPsec to branch | default-gateway | single link, vMAC ok | SRG1 (IPsec anchor) | interface | user-confirmed (round 3) |
```

```
| SRG | Segments | Deployment type | Priority node0 / node1 | Preempt | Decision source |
|---|---|---|---|---|---|
| SRG1 | reth1, reth2 | switching | 200 / 100 | no | user-confirmed (round 3) |
| SRG2 | reth0 | routing | 200 / 100 | no | user-confirmed (round 3) |
```

```
| Decision | Answer | Decision source |
|---|---|---|
| ICL (ports or loopback, addressing) | dedicated ports, <PLACEHOLDER> | user-confirmed (round 5) |
| ICD | none | user-confirmed (round 5) |
| HA link encryption | PKI | user-confirmed (round 5) |
| NAT proxy ARP / DHCP handling | routed next-hop; no DHCP in source | user-confirmed (round 1) |
| Config-sync split (common vs node-local) | policy, NAT, zones, SRG settings common; rest node-local | user-confirmed (round 6) |
| Platform / release verdict | uncertain | user-confirmed (round 7) |
```

Confirmed by the user before generation ("Confirm, or change which row?").

## 4. Generated configuration ([output-format.md](output-format.md))

`node0.set` (excerpt). Port names are the same on both nodes after the cluster
break, so zone bindings are common.

```junos
# ---- common ----
set security zones security-zone untrust interfaces ae0.0
set security zones security-zone trust interfaces ge-0/0/5.0
set security zones security-zone dmz interfaces ge-0/0/6.0
set security policies from-zone trust to-zone untrust policy allow-web then permit
set security nat source rule-set trust-to-untrust rule snat-web then source-nat pool snat-pool
set chassis high-availability services-redundancy-group 1 deployment-type switching
set chassis high-availability services-redundancy-group 1 virtual-ip 1 ip 10.10.10.1/24
set chassis high-availability services-redundancy-group 1 virtual-ip 1 interface ge-0/0/5.0
set chassis high-availability services-redundancy-group 1 virtual-ip 2 ip 203.0.113.1/28
set chassis high-availability services-redundancy-group 1 virtual-ip 2 interface ge-0/0/6.0
set chassis high-availability services-redundancy-group 1 monitor interface ge-0/0/5
set chassis high-availability services-redundancy-group 2 deployment-type routing
set chassis high-availability services-redundancy-group 2 monitor interface ae0
set chassis high-availability services-redundancy-group 2 active-signal-route <ACTIVE_SIGNAL_ROUTE>
set chassis high-availability services-redundancy-group 2 backup-signal-route <BACKUP_SIGNAL_ROUTE>
# ---- node-local ----
set system host-name srx-cl-a
set interfaces fxp0 unit 0 family inet address 192.0.2.10/24
set system backup-router 192.0.2.254 destination 10.99.0.0/16
set interfaces ge-0/0/3 gigether-options 802.3ad ae0
set interfaces ae0 unit 0 family inet address <NODE0_AE0_IP>/28
set interfaces ge-0/0/5 unit 0 family inet address <NODE0_TRUST_IP>/24
set protocols bgp group isp neighbor 198.51.100.1 peer-as 64496
set chassis high-availability local-id 1 local-ip <NODE0_ICL_IP>
set chassis high-availability peer-id 2 peer-ip <NODE1_ICL_IP>
set chassis high-availability services-redundancy-group 1 peer-id 2
set chassis high-availability services-redundancy-group 1 activeness-priority 200
set chassis high-availability services-redundancy-group 2 peer-id 2
set chassis high-availability services-redundancy-group 2 activeness-priority 200
set chassis high-availability services-redundancy-group 2 activeness-probe dest-ip <PROBE_DST> src-ip <NODE0_PROBE_SRC>
# ---- operator-applied: ipsec-srg ----
# set interfaces lo0 unit <UNIT> family inet address <FLOATING_VPN_IP>/32
# set chassis high-availability services-redundancy-group 1 managed-services ipsec
# set security ike gateway gw-branch external-interface lo0.<UNIT>
# set security ike policy ike-pol pre-shared-key ascii-text "<redacted>"
```

`node1.set` carries the identical `# ---- common ----` block. Its node-local part
differs only in: `host-name srx-cl-b`, fxp0 `192.0.2.11/24`, `<NODE1_*>`
addresses, `local-id 2` / `peer-id 1` (and `peer-id 1` on each SRG),
`activeness-priority 100`, and `src-ip <NODE1_PROBE_SRC>`. The same
`ipsec-srg` block closes it.

## 5. Fidelity report

```
| T-ID | Source line(s) | Result | Class | Action needed |
|---|---|---|---|---|
| T23 | `set chassis cluster cluster-id 1` | none | unsupported | Delete cluster stanza in both files |
| T12 | `set apply-groups "${node}"` | groups expanded into node-local sections | converted | none |
| T13 | `set groups node0 interfaces fxp0 ...` | node-local fxp0, backup-router | converted | none |
| T1 | `set interfaces reth0 redundant-ether-options lacp active` | node-local `ae0` per node | caveat | Confirm the upstream is a real LAG to each node |
| T3 | `set interfaces reth0 unit 0 family inet address 198.51.100.2/28` | per-node `<NODE0_AE0_IP>`, no VIP | caveat | ISP must peer with both node addresses |
| T2 | `set interfaces reth1 unit 0 family inet address 10.10.10.1/24` | SRG1 `virtual-ip 1` plus per-node address | caveat | Gateway MAC moves on failover; confirm switch tolerance |
| T2 | `set interfaces reth2 unit 0 family inet address 203.0.113.1/28` | SRG1 `virtual-ip 2` plus per-node address | caveat | Same MAC-move check |
| T4 | `set security zones security-zone trust interfaces reth1.0` | common zone bindings | converted | none |
| T5 | `set chassis cluster redundancy-group 0 node 0 priority 200` | none | unsupported | Per-node RE; manage each node separately |
| T6 | `set chassis cluster redundancy-group 1 node 0 priority 200` | SRG1 and SRG2 priority 200 / 100 | caveat | RG1 split by mode, so ownership of SRG1 and SRG2 can diverge |
| T7 | `set chassis cluster redundancy-group 1 preempt` | no `preemption` | caveat | Cluster preempted; user chose none to avoid failback blackholes |
| T8 | `... redundancy-group 1 interface-monitor ge-0/0/3 weight 255` | `monitor interface ae0` (SRG2) | caveat | Weights do not translate; BFD uses the T9 stanza and is not emitted until timers are supplied |
| T10 | `set interfaces fab0 fabric-options member-interfaces ge-0/0/2` | ICL stanzas with placeholders | unsupported | Build a routed, IPsec-encrypted ICL; do not reuse fab ports |
| T14 | `set security ike gateway gw-branch external-interface reth2.0` | commented `ipsec-srg` block on SRG1 | caveat | Operator applies after review; branch peer 203.0.113.50 must target `<FLOATING_VPN_IP>`; PSK re-entered |
| T15 | `set security nat proxy-arp interface reth0.0 ...` | none | caveat | Pool is advertised by BGP from the SRG2 active node; export policy `<PLACEHOLDER>` not generated |
| T17 | `set protocols bgp group isp neighbor 198.51.100.1` | node-local BGP neighbor | caveat | Re-peer ISP with two node addresses; signal-route policy follows `srx-mnha` |
| T22 | `set security policies from-zone trust to-zone untrust policy allow-web ...` | common policy, NAT pool and rule-set | converted | none |
| T21 | platform and release | verdict uncertain | caveat | Check Feature Explorer (E7) |
```

Totals: 4 converted, 11 caveat, 0 manual, 3 unsupported. Open manual items: none.

## 6. Values still needed

```
| Placeholder | Meaning | Used in | Owner | Status |
|---|---|---|---|---|
| <NODE0_AE0_IP> / <NODE1_AE0_IP> | per-node untrust address | node-local | user | needed |
| <NODE0_TRUST_IP> / <NODE1_TRUST_IP> | per-node trust address | node-local | user | needed |
| <NODE0_ICL_IP> / <NODE1_ICL_IP> | ICL addresses | node-local | user | needed |
| <PROBE_DST>, <NODE0_PROBE_SRC>, <NODE1_PROBE_SRC> | SRG2 activeness probe | node-local | user | needed |
| <ACTIVE_SIGNAL_ROUTE> / <BACKUP_SIGNAL_ROUTE> | reserved signal prefixes | common | user | needed |
| <FLOATING_VPN_IP>, <UNIT> | IPsec anchor on `lo0` | ipsec-srg block | user | needed |
```

The files cannot be loaded as is while any row is `needed`.

## 7. Next step

Cutover steps, rollback boxes and verification commands are in
[cutover-runbook.md](cutover-runbook.md). This skill executes none of them; the
`ipsec-srg` block is applied by the operator (Phase 2 for node1, Phase 5 for node0).

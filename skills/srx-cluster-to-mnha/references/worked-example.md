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
| nat | trust-to-untrust | - | - | source pool 203.0.113.66-.68 | pool is off every connected subnet; ISP must route it to us |
| ike-gateway | gw-branch | - | - | external-interface reth2.0; ipsec vpn-branch on st0.0 | peer 203.0.113.50; PSK `<redacted>` |
```

Open facts: platform model and Junos release are `<UNKNOWN>`; asked through runtime intake.

## 2. Interview summary ([architect-interview.md](architect-interview.md))

| Round | Topic | Proposal | Sample answer |
|---|---|---|---|
| 1 | Purpose and mode | reth0 has an eBGP router: routed. reth1, reth2 host static gateways: default-gateway | Confirmed. No proxy ARP in source; NAT pool 203.0.113.64/29 is off-subnet, so it is routed (advertised by BGP); hosts have a static gateway |
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
| ICL (ports or loopback, addressing) | dedicated ports `<ICL_IFD>`, addresses not supplied | user-confirmed (round 5) |
| ICD | none | user-confirmed (round 5) |
| HA link encryption | PKI | user-confirmed (round 5) |
| NAT proxy ARP / DHCP handling | no proxy ARP in source; pool routed via BGP from the SRG2 active node; no DHCP | user-confirmed (round 1) |
| Config-sync split (common vs node-local) | policy, NAT, zones, SRG settings common; rest node-local (the skill's output separates common and node-local sections itself; MNHA's `commit peers-synchronize` scope is unverified, see vendor-evidence.md Uncertain) | user-confirmed (round 6) |
| Platform / release verdict | uncertain | user-confirmed (round 7) |
```

Confirmed by the user before generation ("Confirm, or change which row?").

## 4. Generated configuration ([output-format.md](output-format.md))

`node0.set` is the review copy (excerpt, abridged; no BFD stanza is emitted
because the syntax is unconfirmed, see the T8 BFD row). Port names are the same
on both nodes after the cluster break, so zone bindings are common. This
fixture assumes physical SRX names that stay unchanged; on vSRX every port would
be `ge-0/0/(N+1)` (L1, see [output-format.md](output-format.md#port-names)).
`node0.load.set` is this file with every `#` line removed (L2), and the IPsec
lines below are written uncommented to `node0.ipsec.set`.

```junos
# Draft output from offline analysis. Not validated on a device and not production-ready.
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
set chassis aggregated-devices ethernet device-count <DEVICE_COUNT>
set interfaces ge-0/0/3 gigether-options 802.3ad ae0
set interfaces ge-0/0/4 gigether-options 802.3ad ae0
set interfaces ae0 aggregated-ether-options lacp active
set interfaces ae0 unit 0 family inet address <NODE0_AE0_IP>/28
set interfaces ge-0/0/5 unit 0 family inet address <NODE0_TRUST_IP>/24
set protocols bgp group isp neighbor 198.51.100.1 peer-as 64496
set protocols bgp group isp export <BGP_EXPORT_POLICY>
set routing-options static route 0.0.0.0/0 next-hop 198.51.100.1
set chassis high-availability local-id 1 local-ip <NODE0_ICL_IP>
set chassis high-availability peer-id 2 peer-ip <NODE1_ICL_IP>
set chassis high-availability peer-id 2 interface <ICL_IFD>
set chassis high-availability services-redundancy-group 1 peer-id 2
set chassis high-availability services-redundancy-group 1 activeness-priority 200
set chassis high-availability services-redundancy-group 2 peer-id 2
set chassis high-availability services-redundancy-group 2 activeness-priority 200
set chassis high-availability services-redundancy-group 2 activeness-probe dest-ip <PROBE_DST> src-ip <NODE0_PROBE_SRC>
# ---- operator-applied: ipsec-srg ----
# Every IPsec line belongs here (T14); lines are commented until reviewed.
# set interfaces lo0 unit <UNIT> family inet address <FLOATING_VPN_IP>/32
# set policy-options prefix-list <IKE_GW_PREFIX_LIST> <FLOATING_VPN_IP>/32
# set chassis high-availability services-redundancy-group 1 prefix-list <IKE_GW_PREFIX_LIST> routing-instance <ROUTING_INSTANCE>
# set chassis high-availability services-redundancy-group 1 managed-services ipsec
# set security ike proposal ike-prop authentication-method pre-shared-keys
# set security ike proposal ike-prop dh-group group14
# set security ike proposal ike-prop encryption-algorithm aes-256-cbc
# set security ike proposal ike-prop authentication-algorithm sha-256
# set security ike policy ike-pol mode main
# set security ike policy ike-pol proposals ike-prop
# set security ike policy ike-pol pre-shared-key ascii-text "<redacted>"
# set security ike gateway gw-branch ike-policy ike-pol
# set security ike gateway gw-branch address 203.0.113.50
# set security ike gateway gw-branch external-interface lo0.<UNIT>
# set security ike gateway gw-branch local-address <FLOATING_VPN_IP>
# set security ipsec proposal ipsec-prop protocol esp
# set security ipsec proposal ipsec-prop encryption-algorithm aes-256-cbc
# set security ipsec proposal ipsec-prop authentication-algorithm hmac-sha-256-128
# set security ipsec policy ipsec-pol proposals ipsec-prop
# set security ipsec vpn vpn-branch bind-interface st0.0
# set security ipsec vpn vpn-branch ike gateway gw-branch
# set security ipsec vpn vpn-branch ike ipsec-policy ipsec-pol
# set interfaces st0 unit 0 family inet
# set security zones security-zone dmz interfaces st0.0
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
| T8 | `... redundancy-group 1 interface-monitor ge-0/0/3 weight 255` | `monitor interface ae0` (SRG2) | caveat | Weights do not translate; thresholds re-chosen with the user |
| T8 | decision record: reth0 detection `BFD + interface` (no cluster source line) | none; BFD monitor is a candidate only | caveat | BFD timers/syntax to verify in a lab; stanza is unconfirmed (vendor-evidence `## Uncertain`) and not emitted |
| T10 | `set interfaces fab0 fabric-options member-interfaces ge-0/0/2` | ICL stanzas with placeholders | unsupported | Build a routed ICL (IPsec-encrypted here, recommended); do not reuse fab ports |
| T14 | `set security ike gateway gw-branch external-interface reth2.0` | commented `ipsec-srg` block on SRG1 | caveat | Operator applies after review; branch peer 203.0.113.50 must target `<FLOATING_VPN_IP>`; PSK re-entered |
| T17 | `set protocols bgp group isp neighbor 198.51.100.1` | node-local BGP neighbor, export `<BGP_EXPORT_POLICY>` | caveat | Re-peer ISP with two node addresses; policy must advertise pool 203.0.113.64/29 from the SRG2 active node (`srx-mnha` mnha-config-patterns.md) |
| T17 | `set routing-options static route 0.0.0.0/0 next-hop 198.51.100.1` | node-local static default | caveat | Next hop is on the untrust LAG; confirm each node reaches 198.51.100.1 |
| T22 | `set security policies from-zone trust to-zone untrust policy allow-web ...` | common policy, NAT pool and rule-set | converted | none |
| T21 | platform and release | verdict uncertain | caveat | Check Feature Explorer (E7) |
```

Totals: 4 converted, 12 caveat, 0 manual, 3 unsupported. Open manual items: none.

The fixture has no `system login`, `snmp` or `syslog` stanzas outside the node groups, so there is no T24 row; a real cluster with them gets one `manual` row (system baseline preserved by the runbook's targeted deletes).

## 6. Values still needed

```
| Placeholder | Meaning | Used in | Owner | Status |
|---|---|---|---|---|
| <NODE0_AE0_IP> | node0 untrust address | node0.set, runbook phase 4 | user | needed |
| <NODE1_AE0_IP> | node1 untrust address | node1.set, runbook phase 2 | user | needed |
| <NODE0_TRUST_IP> | node0 trust address | node0.set, runbook phase 4 | user | needed |
| <NODE1_TRUST_IP> | node1 trust address | node1.set, runbook phase 2 | user | needed |
| <NODE0_ICL_IP> | node0 ICL local address | node0.set, runbook phase 4 | user | needed |
| <NODE1_ICL_IP> | node1 ICL local address | node1.set, runbook phase 2 | user | needed |
| <ICL_IFD> | ICL dedicated port or LAG | both, runbook phase 2 | user | needed |
| <DEVICE_COUNT> | `aggregated-devices ethernet device-count` for ae0 | both, runbook phase 2 | user | needed |
| <BFD_MIN_INTERVAL> | BFD minimum interval for SRG2 detection (candidate only, syntax unconfirmed) | none emitted | user | n/a until BFD syntax verified (T8 caveat) |
| <BFD_MULTIPLIER> | BFD multiplier for SRG2 detection (candidate only, syntax unconfirmed) | none emitted | user | n/a until BFD syntax verified (T8 caveat) |
| <SYSTEM_BASELINE> | login, root-authentication, services, snmp, syslog kept on each node (T24) | runbook phases 2, 4 | user | needed |
| <PROBE_DST> | SRG2 activeness-probe destination | both, runbook phase 2 | user | needed |
| <NODE0_PROBE_SRC> | node0 probe source address | node0.set, runbook phase 4 | user | needed |
| <NODE1_PROBE_SRC> | node1 probe source address | node1.set, runbook phase 2 | user | needed |
| <ACTIVE_SIGNAL_ROUTE> | reserved active signal prefix | both, runbook phase 2 | user | needed |
| <BACKUP_SIGNAL_ROUTE> | reserved backup signal prefix | both, runbook phase 2 | user | needed |
| <BGP_EXPORT_POLICY> | export policy advertising the NAT pool from the active node | both, runbook phase 2 | user | needed |
| <FLOATING_VPN_IP> | floating IPsec address on lo0 | both, ipsec-srg block (phase 2 node1, phase 5 node0) | user | needed |
| <IKE_GW_PREFIX_LIST> | prefix list holding the floating address, bound to SRG1 (T14) | both, ipsec-srg block | user | needed |
| <ROUTING_INSTANCE> | routing instance the SRG1 prefix list is bound to (`default` for the main table, assumption) | both, ipsec-srg block | user | needed |
| <UNIT> | lo0 unit for the floating address | both, ipsec-srg block | user | needed |
```

The files cannot be loaded as is while any row is `needed`.

## 7. Next step

Cutover steps, rollback boxes and verification commands are in
[cutover-runbook.md](cutover-runbook.md). This skill executes none of them; the
`ipsec-srg` block is applied by the operator (Phase 2 for node1, Phase 5 for node0).

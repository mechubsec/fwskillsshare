# Emit Juniper SRX `set` Configuration

## Contents

- [address_objects](#address_objects)
- [address_groups](#address_groups)
- [service_objects (applications)](#service_objects-applications)
- [service_groups (application-sets)](#service_groups-application-sets)
- [zones](#zones)
- [security_policies](#security_policies)
- [nat_rules](#nat_rules)
- [interfaces](#interfaces)
- [static routes, routing-instances/VRF, OSPF, BGP](#static-routes-routing-instancesvrf-ospf-bgp)
- [system (host-name/dns/ntp/services), admin_users, DHCP](#system-host-namednsntpservices-admin_users-dhcp)
- [ha_config (chassis cluster)](#ha_config-chassis-cluster)
- [vpn_tunnels (IKE / IPsec)](#vpn_tunnels-ike--ipsec)
- [screens (security screen ids-option + zone binding)](#screens-security-screen-ids-option--zone-binding)
- [schedules (schedulers)](#schedules-schedulers)
- [management-plane access (`zones[].host_inbound` / `system.mgmt_services`)](#management-plane-access-zoneshost_inbound--systemmgmt_services)
- [Emit checklist (SRX target)](#emit-checklist-srx-target)

Target-emitter reference for the `firewall-config-conversion` skill. Loaded when the
conversion **target = SRX (Junos)**. For every emittable section of the intermediate
schema this file shows the native Junos `set` syntax to render, the fidelity
classification (`converted` / `converted-with-caveats` / `manual-not-converted`), and the
inline `# CAVEAT:` to emit when the translation is lossy. Cross-vendor lossiness is sourced
from `references/feature-mapping.md`; SRX syntax discipline follows the
`parsing-srx-configs` skill's config-format reference (one leaf per `set` line, quoted values
for names with spaces, `deactivate` for disabled config).

> **CRITICAL SRX SYNTAX RULE — one leaf per `set` line.** Junos `set` commands set exactly
> one leaf. Never combine sibling leaves on a line. `match source-address`,
> `match destination-address`, `match application`, `then permit`, `then log session-init`,
> `then log session-close`, and `then count` are **separate lines** that repeat the full
> policy path. Putting `destination-address` on the same line after a `source-address`
> value, or appending `log session-close` after `then permit`, is invalid Junos and will
> fail commit-check on the
> vSRX. When a node legitimately takes multiple values (e.g. several source addresses),
> emit one `set` line **per value**, each repeating the path.
>
> **Secrets are NEVER emitted.** PSKs, certificates, and passwords are rendered as
> `"<PSK-PLACEHOLDER>"` / `"<KEY-PLACEHOLDER>"` / `"<PASSWORD-PLACEHOLDER>"` plus a
> `manual-not-converted` item.

Greenfield/migration default: prefer the **global address-book** and
**`security policies global`** with `match from-zone` / `match to-zone` inside each policy,
rather than many `from-zone … to-zone …` contexts.

---

## address_objects

**Classification: converted** (clean 1:1 — host / network / range / fqdn).

Render each object into the global address book, one `set` per object. Use the schema
`ip_version` only to pick the literal; the path is identical for inet/inet6.

```
set security address-book global address HOST-WEB-01 10.20.30.10/32
set security address-book global address NET-USERS 10.10.0.0/16
set security address-book global address RANGE-DHCP range-address 10.10.5.10 to 10.10.5.50
set security address-book global address FQDN-UPDATE dns-name updates.example.com
set security address-book global address NET6-DMZ 2001:db8:dmz::/64
```

- A bare `<prefix>` after the name is the host/network form; `/32` (or `/128`) for a host.
- `range-address <start> to <end>` for ranges; `dns-name <fqdn>` for FQDN objects.
- Quote any name containing spaces: `set security address-book global address "My Server" 10.0.1.10/32`.
- CAVEAT (only if source object was zone-scoped and you flatten to global):
  `# CAVEAT: source zone-local address moved to global address-book; verify no name collision`.

## address_groups

**Classification: converted** (clean 1:1).

Render as `address-set`; emit one `set` line per member (never a bracket list in
emitted config — keep it one leaf per line so it round-trips through `display set`).

```
set security address-book global address-set WEB-SERVERS address HOST-WEB-01
set security address-book global address-set WEB-SERVERS address HOST-WEB-02
set security address-book global address-set WEB-SERVERS address-set DMZ-HOSTS
```

- Nested groups use `address-set <child>` instead of `address <member>`.

## service_objects (applications)

**Classification: converted** for predefined; **converted-with-caveats** for custom or
unresolved.

Map each canonical service to its predefined `junos-*` name using the table in
`feature-mapping.md` (Part 1). Predefined applications need **no** definition — they are
referenced directly by policies. Emit explicit definitions only for **custom** services.

```
set applications application APP-TCP-8443 protocol tcp
set applications application APP-TCP-8443 destination-port 8443
set applications application APP-UDP-RANGE protocol udp
set applications application APP-UDP-RANGE destination-port 16384-32767
set applications application APP-ICMP-ECHO protocol icmp
set applications application APP-ICMP-ECHO icmp-type echo-request
```

- One leaf per line: `protocol`, then `destination-port`, then any `source-port` /
  `icmp-type` / `inactivity-timeout`, each on its own `set`.
- A canonical service like `dns` that maps to two predefined apps (`junos-dns-udp` +
  `junos-dns-tcp`) is best expressed as an application-set (see below).
- CAVEAT for a parser-unresolved app (`confidence: 0.0`):
  `# CAVEAT: unresolved source application emitted as residual — define manually, do not trust port guess` → classify **manual-not-converted** for that object.

## service_groups (application-sets)

**Classification: converted** (clean 1:1).

```
set applications application-set APP-WEB application junos-http
set applications application-set APP-WEB application junos-https
set applications application-set APP-WEB application APP-TCP-8443
set applications application-set APP-DNS application junos-dns-udp
set applications application-set APP-DNS application junos-dns-tcp
```

- One `application <member>` leaf per line; mix predefined and custom freely.
- Nested sets: `set applications application-set <name> application-set <child>`.

## zones

**Classification: converted** (from SRX/Palo source); **converted-with-caveats** (from
FortiGate/ASA — see `feature-mapping.md` → zones).

Render one security-zone per schema zone, bind its interfaces, and emit allowed
management services from the zone's `host_inbound` (see management-plane access).

```
set security zones security-zone TRUST interfaces ge-0/0/0.0
set security zones security-zone TRUST interfaces ge-0/0/1.0
set security zones security-zone UNTRUST interfaces ge-0/0/2.0
set security zones security-zone TRUST host-inbound-traffic system-services ping
set security zones security-zone TRUST host-inbound-traffic system-services ssh
```

- One `interfaces <iface.unit>` leaf per line.
- CAVEAT when source is Cisco ASA (`nameif` + `security-level`):
  `# CAVEAT: ASA security-level trust ordering not representable on SRX — implicit high→low permit replaced by explicit policies`.
- CAVEAT when source is FortiGate matching interfaces directly:
  `# CAVEAT: source matched interfaces, not named zones — zone synthesized per source interface; verify intrazone intent`.

## security_policies

**Classification: converted** when actions/logging/apps all resolve cleanly; **converted-with-caveats** when profiles or unresolved apps are present (both are lossy). **Preserve source rule order** — emit a stable numeric prefix
(`010-`, `100-`, `999-`) so order survives. Default to `security policies global` with
`match from-zone` / `match to-zone` leaves.

Action and logging map:

| Schema | SRX `then` leaf (own line) |
|--------|----------------------------|
| `action: allow` | `then permit` |
| `action: deny` | `then deny` (silent drop) |
| `action: drop` | `then deny` (SRX `deny` already silently drops; distinct from `reset-both`) |
| `action: reset-both` | `then reject` (sends TCP RST / ICMP unreachable to both ends) |
| `log_start: true` | `then log session-init` |
| `log_end: true` | `then log session-close` |
| (counters) | `then count` |
| `disabled: true` | prefix line with `deactivate` instead of `set` (preserve, don't drop) |

Every match field and every `then` leaf is its **own** `set` line repeating the full path:

```
set security policies global policy 100-USERS-WEB match from-zone TRUST
set security policies global policy 100-USERS-WEB match to-zone UNTRUST
set security policies global policy 100-USERS-WEB match source-address NET-USERS
set security policies global policy 100-USERS-WEB match destination-address any
set security policies global policy 100-USERS-WEB match application APP-WEB
set security policies global policy 100-USERS-WEB then permit
set security policies global policy 100-USERS-WEB then log session-init
set security policies global policy 100-USERS-WEB then log session-close
set security policies global policy 100-USERS-WEB then count
```

- Multiple sources/destinations/apps → one `match …-address <name>` / `match application <name>` line **each**.
- **NEVER** combine sibling leaves: a `match source-address` value followed by
  `destination-address` on the same line, or `then permit` followed by `log session-close`,
  are both invalid. Split into separate lines as shown above.

### security-profile attachments on a policy

Schema `security_policies[].security_profiles` (UTM / IDP / AppFW / SecIntel intent,
resolving `security_profile_objects` for contents) attach **only on permit**,
each service on its own `then permit application-services …` leaf line:

```
set security policies global policy 200-USERS-WEB then permit application-services utm-policy UTM-NG-WEB
set security policies global policy 200-USERS-WEB then permit application-services application-firewall rule-set APPFW-STREAMING
set security policies global policy 200-USERS-WEB then permit application-services idp-policy IDP-BASE
```

- **Classification: converted-with-caveats** — the attachment shape converts; profile
  **contents** are vendor-proprietary. Emit:
  `# CAVEAT: profile contents (signatures/categories/actions) must be rebuilt on SRX — only the attachment is converted` (per `feature-mapping.md` → security profile attachments).
- If source is Cisco ASA (no UTM model), there is nothing to attach → record as
  **manual-not-converted** in the report, not in config.
- `then log session-init` / `then log session-close` are still separate lines from the
  `then permit application-services …` lines.

## nat_rules

**Classification: converted-with-caveats** (intent maps; container/pool/proxy-arp
restructured — `feature-mapping.md` → nat_rules). **Preserve rule order** within each
rule-set.

Source NAT (interface PAT or pool):

```
set security nat source rule-set RS-TRUST-UNTRUST from zone TRUST
set security nat source rule-set RS-TRUST-UNTRUST to zone UNTRUST
set security nat source rule-set RS-TRUST-UNTRUST rule R10-USERS match source-address 10.10.0.0/16
set security nat source rule-set RS-TRUST-UNTRUST rule R10-USERS then source-nat interface
set security nat source pool PNAT-EGRESS address 203.0.113.10/32 to 203.0.113.20/32
set security nat source rule-set RS-TRUST-UNTRUST rule R20-SERVERS match source-address 10.20.0.0/16
set security nat source rule-set RS-TRUST-UNTRUST rule R20-SERVERS then source-nat pool PNAT-EGRESS
```

Destination NAT (pool target):

```
set security nat destination pool DNAT-WEB address 10.20.30.10/32
set security nat destination rule-set RS-DST-UNTRUST from zone UNTRUST
set security nat destination rule-set RS-DST-UNTRUST rule R10-WEB match destination-address 203.0.113.50/32
set security nat destination rule-set RS-DST-UNTRUST rule R10-WEB match destination-port 443
set security nat destination rule-set RS-DST-UNTRUST rule R10-WEB then destination-nat pool DNAT-WEB
```

Static NAT (1:1):

```
set security nat static rule-set RS-STATIC from zone UNTRUST
set security nat static rule-set RS-STATIC rule R10-MAIL match destination-address 203.0.113.60/32
set security nat static rule-set RS-STATIC rule R10-MAIL then static-nat prefix 10.20.40.10/32
```

- One leaf per line: `from zone`, `to zone`, each `match …`, each `then …`.
- CAVEAT when source folded dest-NAT into a VIP (FortiGate):
  `# CAVEAT: source VIP/dest-NAT re-anchored into SRX destination rule-set + pool — verify port-forward and proxy-arp`.
- Proxy-ARP for destination/static NAT rarely survives; emit
  `# CAVEAT: configure proxy-arp for translated address if not on the egress interface subnet` and flag review.

## interfaces

**Classification: converted-with-caveats** — physical names are platform-bound and never
portable (`feature-mapping.md` → interfaces). Carry IP addressing over; remap the name
positionally and CAVEAT it.

```
set interfaces ge-0/0/0 unit 0 family inet address 10.10.0.1/24
set interfaces ge-0/0/2 unit 0 family inet address 203.0.113.2/30
set interfaces ge-0/0/0 unit 0 family inet6 address 2001:db8:trust::1/64
set interfaces ge-0/0/3 unit 100 vlan-id 100
set interfaces ge-0/0/3 unit 100 family inet address 10.10.100.1/24
```

- `family inet` for IPv4, `family inet6` for IPv6 — one `address` leaf per line; an
  interface with both families emits one line per family.
- Sub-interfaces (`is_subif`) use a non-zero `unit` plus `vlan-id`.
- Aggregate (`lag_parent`/`lag_members`) → `aeN`; emit
  `set interfaces ge-0/0/4 gigether-options 802.3ad ae0` per member and
  `set interfaces ae0 unit 0 family inet address …`.
- CAVEAT (always, on the first interface):
  `# CAVEAT: interface names remapped positionally — verify against target SRX hardware (fpc/pic/port) and bindings`.

## static routes, routing-instances/VRF, OSPF, BGP

**Classification: converted-with-caveats** — protocol params map; hierarchy differs and
route-map/policy-statement idioms rarely translate verbatim (`feature-mapping.md` →
static_routes/OSPF/BGP). **Preserve route order.**

Static routes (global table):

```
set routing-options static route 0.0.0.0/0 next-hop 203.0.113.1
set routing-options static route 10.50.0.0/16 next-hop 10.10.0.254
set routing-options rib inet6.0 static route ::/0 next-hop 2001:db8:wan::1
```

Routing-instance / VRF (per `feature-mapping.md` → routing-instances):

```
set routing-instances VRF-CUST1 instance-type virtual-router
set routing-instances VRF-CUST1 interface ge-0/0/5.0
set routing-instances VRF-CUST1 routing-options static route 0.0.0.0/0 next-hop 198.51.100.1
```

- CAVEAT: `# CAVEAT: source VRF/virtual-router/context boundaries differ on SRX — re-scope per-instance routing/zones`.

OSPF:

```
set protocols ospf area 0.0.0.0 interface ge-0/0/0.0
set protocols ospf area 0.0.0.0 interface ge-0/0/1.0 metric 10
set protocols ospf area 0.0.0.1 interface ge-0/0/2.0 interface-type p2p
```

- Inside a VRF, prefix with `set routing-instances VRF-CUST1 protocols ospf …`.

BGP:

```
set protocols bgp group EBGP-UPSTREAM type external
set protocols bgp group EBGP-UPSTREAM peer-as 65010
set protocols bgp group EBGP-UPSTREAM neighbor 203.0.113.1
set routing-options autonomous-system 65001
```

- One leaf per line: `type`, `peer-as`, each `neighbor`.
- CAVEAT: `# CAVEAT: route-maps/prefix-lists become Junos policy-statements — re-author import/export policy manually` (manual-not-converted for the policy bodies themselves).

## system (host-name/dns/ntp/services), admin_users, DHCP

**Classification: converted-with-caveats** — base system maps; passwords are placeholders.

System base from schema `system`:

```
set system host-name fw-edge-01
set system domain-name example.com
set system name-server 10.10.0.53
set system name-server 1.1.1.1
set system ntp server 10.10.0.123
set system services ssh
set system services netconf ssh
```

- One leaf per line: each `name-server`, each `ntp server`, each `services …`.

admin_users (schema `admin_users` → `system login`) — **passwords never emitted**:

```
set system login user admin1 class super-user
set system login user admin1 authentication encrypted-password "<PASSWORD-PLACEHOLDER>"
set system login user netops class operator
```

- CAVEAT: `# CAVEAT: admin password not converted — set credentials manually` → **manual-not-converted** for the secret.

DHCP (schema `dhcp_config` server / relay):

```
set system services dhcp-local-server group G-USERS interface ge-0/0/0.0
set access address-assignment pool POOL-USERS family inet network 10.10.0.0/24
set access address-assignment pool POOL-USERS family inet range R1 low 10.10.0.100
set access address-assignment pool POOL-USERS family inet range R1 high 10.10.0.200
set access address-assignment pool POOL-USERS family inet dhcp-attributes router 10.10.0.1
```

- DHCP relay: `set forwarding-options dhcp-relay server-group SG1 10.10.0.53` plus
  `set forwarding-options dhcp-relay group G1 interface ge-0/0/0.0`.
- CAVEAT: `# CAVEAT: DHCP pool/option model differs — verify lease, options, and bindings on SRX`.

## ha_config (chassis cluster)

**Classification: converted-with-caveats** (note only — not commit-safe to auto-emit).

Chassis cluster is **enabled out-of-band** (`set chassis cluster cluster-id <n> node <n>
reboot`), not via plain commit, and reth/redundancy-group/fabric layout depends on the
exact platform pair. Emit a commented skeleton plus a manual item rather than a live config:

```
# CAVEAT: chassis cluster must be enabled out-of-band per node and verified on real hardware — skeleton only
# set chassis cluster reth-count 2
# set chassis cluster redundancy-group 0 node 0 priority 100
# set chassis cluster redundancy-group 0 node 1 priority 1
# set chassis cluster redundancy-group 1 node 0 priority 100
# set chassis cluster redundancy-group 1 node 1 priority 1
# set interfaces fab0 fabric-options member-interfaces ge-0/0/5
# set interfaces reth0 redundant-ether-options redundancy-group 1
```

- Record **manual-not-converted** for the cluster bring-up; HA topology is hardware-specific.

## vpn_tunnels (IKE / IPsec)

**Classification: converted-with-caveats** for crypto params; **manual-not-converted** for
PSK/certs — **secrets are never emitted** (`feature-mapping.md` → vpn_tunnels).

Emit the route-based st0 structure with crypto params from the schema, but a **placeholder**
for the key:

```
set security ike proposal IKE-PROP-1 authentication-method pre-shared-keys
set security ike proposal IKE-PROP-1 dh-group group14
set security ike proposal IKE-PROP-1 authentication-algorithm sha-256
set security ike proposal IKE-PROP-1 encryption-algorithm aes-256-cbc
set security ike proposal IKE-PROP-1 lifetime-seconds 28800
set security ike policy IKE-POL-1 mode main
set security ike policy IKE-POL-1 proposals IKE-PROP-1
set security ike policy IKE-POL-1 pre-shared-key ascii-text "<PSK-PLACEHOLDER>"
set security ike gateway GW-SITEB ike-policy IKE-POL-1
set security ike gateway GW-SITEB address 198.51.100.2
set security ike gateway GW-SITEB external-interface ge-0/0/2.0
set security ike gateway GW-SITEB version v2-only
set security ipsec proposal IPSEC-PROP-1 protocol esp
set security ipsec proposal IPSEC-PROP-1 authentication-algorithm hmac-sha-256-128
set security ipsec proposal IPSEC-PROP-1 encryption-algorithm aes-256-cbc
set security ipsec proposal IPSEC-PROP-1 lifetime-seconds 3600
set security ipsec policy IPSEC-POL-1 perfect-forward-secrecy keys group14
set security ipsec policy IPSEC-POL-1 proposals IPSEC-PROP-1
set security ipsec vpn VPN-SITEB bind-interface st0.0
set security ipsec vpn VPN-SITEB ike gateway GW-SITEB
set security ipsec vpn VPN-SITEB ike ipsec-policy IPSEC-POL-1
set security ipsec vpn VPN-SITEB establish-tunnels immediately
set interfaces st0 unit 0 family inet
```

- **CAVEAT (mandatory):** `# CAVEAT: PSK/certificate not converted — re-key the VPN manually on SRX before enabling` → **manual-not-converted** item.
- CAVEAT: `# CAVEAT: policy-based crypto-map source re-modeled as route-based st0 — re-validate peer/proxy-id/traffic-selectors`.
- One leaf per line throughout; bind st0 and add the tunnel route under routing-options.

## screens (security screen ids-option + zone binding)

**Classification: converted-with-caveats** (to/from Palo); **manual-not-converted** when
source is Cisco ASA (no full screen model — `feature-mapping.md` → screens).

```
set security screen ids-option SCREEN-UNTRUST tcp syn-flood alarm-threshold 1000
set security screen ids-option SCREEN-UNTRUST tcp syn-flood attack-threshold 1100
set security screen ids-option SCREEN-UNTRUST icmp flood threshold 1000
set security screen ids-option SCREEN-UNTRUST ip spoofing
set security screen ids-option SCREEN-UNTRUST tcp land
set security zones security-zone UNTRUST screen SCREEN-UNTRUST
```

- One leaf per line; bind the ids-option to its zone with the final `screen` line.
- CAVEAT: `# CAVEAT: screen thresholds/option names differ across vendors — review values against source intent`.

## schedules (schedulers)

**Classification: converted** (intent 1:1; minor recurrence-syntax loss).

```
set schedulers scheduler BIZ-HOURS daily start-time 08:00:00 stop-time 18:00:00
set schedulers scheduler BIZ-HOURS monday all-day
set schedulers scheduler MAINT-WINDOW start-date 2026-07-01.00:00 stop-date 2026-07-01.06:00
```

Reference from a policy on its own line:

```
set security policies global policy 100-USERS-WEB scheduler-name BIZ-HOURS
```

- FortiGate `"always"` → emit no scheduler (no restriction).
- CAVEAT only when recurrence can't be expressed exactly:
  `# CAVEAT: source recurrence approximated — verify scheduler day/time windows`.

## management-plane access (`zones[].host_inbound` / `system.mgmt_services`)

**Classification: converted-with-caveats** — container differs across vendors
(`feature-mapping.md` → management-plane access). Source these from the schema's
**`zones[].host_inbound`** (per-zone accepted management services) and
**`system.mgmt_services`** (device/system-level management) — **not** from
`security_services`, which is only a device-wide security-service presence flag set
(app_id/idp/secintel/aamw/utm) and carries no management access. Render the per-zone
services under each zone's `host-inbound-traffic`.

```
set security zones security-zone TRUST host-inbound-traffic system-services ssh
set security zones security-zone TRUST host-inbound-traffic system-services ping
set security zones security-zone TRUST host-inbound-traffic system-services netconf
set security zones security-zone TRUST host-inbound-traffic protocols ospf
```

- `system-services …` for mgmt services; `protocols …` for routing protocols allowed inbound.
- One leaf per line.
- CAVEAT: `# CAVEAT: verify management-plane exposure on SRX — host-inbound services differ from source interface-mgmt model`.
- Never emit management secrets/keys (SNMP community, etc.) — placeholder + manual item.

---

## Emit checklist (SRX target)

- [ ] Every `set` line sets exactly one leaf — no combined `match …`/`then …` siblings.
- [ ] Security-policy order preserved via stable numeric name prefixes; disabled rules emitted with `deactivate`, not dropped.
- [ ] `allow→permit`, `log_start→then log session-init`, `log_end→then log session-close`, profiles→`then permit application-services …` (separate lines).
- [ ] NAT and route order preserved; pools/proxy-arp CAVEATed.
- [ ] Predefined `junos-*` apps used where the canonical table allows; custom apps defined explicitly.
- [ ] All secrets (PSK/cert/password/community) are placeholders + a manual-not-converted item.
- [ ] Chassis cluster emitted as commented skeleton + manual item, never live.
- [ ] Each lossy section carries its inline `# CAVEAT:` and the matching fidelity classification.

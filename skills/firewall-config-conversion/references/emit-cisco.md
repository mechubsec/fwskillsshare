# Emit Cisco ASA/FTD Configuration

## Contents

- [address_objects](#address_objects)
- [address_groups](#address_groups)
- [service_objects](#service_objects)
- [service_groups](#service_groups)
- [zones](#zones)
- [security_policies](#security_policies)
- [nat_rules](#nat_rules)
- [interfaces](#interfaces)
- [static routes, OSPF, BGP](#static-routes-ospf-bgp)
- [system, admin_users, DHCP](#system-admin_users-dhcp)
- [ha_config](#ha_config)
- [vpn_tunnels (IKE / IPsec)](#vpn_tunnels-ike--ipsec)
- [screens (threat-protection)](#screens-threat-protection)
- [schedules](#schedules)
- [security-profile attachments & management-plane access](#security-profile-attachments--management-plane-access)
- [Emit checklist (Cisco ASA/FTD target)](#emit-checklist-cisco-asaftd-target)

Target-emitter reference for the `firewall-config-conversion` skill. Loaded when the
conversion **target = Cisco ASA/FTD**. For every emittable section of the intermediate
schema this file shows the native ASA CLI to render, the fidelity classification
(`converted` / `converted-with-caveats` / `manual-not-converted`), and the inline
`# CAVEAT:` to emit when the translation is lossy. Cross-vendor lossiness is sourced from
`references/feature-mapping.md`; ASA syntax discipline follows the `parsing-cisco-configs`
skill's config-format reference (line-oriented format, top-level commands at column 0,
sub-commands indented one space, dotted-decimal subnet masks not wildcard or CIDR).

> **CRITICAL ASA/FTD RULES**
>
> - **ASA is PORT/PROTOCOL-BASED — there is no App-ID.** Classic ASA matches on
>   protocol + port only. Any L7/application identity from an SRX/Palo source is **lost**:
>   decompose each app to its well-known port(s) (`feature-mapping.md` Part 1) and emit a
>   `# CAVEAT: L7 identity lost`. There is **no UTM / security profile** on classic ASA.
> - **No named-zone object.** The zone unit is the **interface**: a logical `nameif` name
>   plus a numeric `security-level` (0–100). Policy is an **ACL applied per-interface**
>   (`access-group <acl> in interface <nameif>`), not a zone-pair. The implicit high→low
>   permit is **not** representable on SRX/Palo/Forti and must become explicit ACL.
> - **Masks are standard subnet masks, not wildcard or CIDR.** `subnet 10.0.0.0
>   255.255.0.0`, `route inside 10.0.0.0 255.255.0.0 ...`. Convert from the schema prefix
>   length. (ASA ACLs use standard masks, unlike IOS wildcard masks.)
> - **ACL order is significant.** Emit `access-list` lines in **source rule order** — ASA
>   evaluates top-to-bottom, first match wins. Never reorder.
> - **Secrets are NEVER emitted.** PSKs, certificates, passwords, SNMP communities render as
>   `<PSK-PLACEHOLDER>` / `<KEY-PLACEHOLDER>` / `<PASSWORD-PLACEHOLDER>` plus a
>   `manual-not-converted` item. Never carry over an encrypted/hashed secret (the ASA
>   PBKDF2/scrypt `enc` password hashes) from the source config.
> - **FTD caveat (state once).** These are **ASA-style LINA CLI** snippets. They apply to
>   FTD via **FlexConfig / LINA** for features FMC does not model, **but FMC-managed FTD
>   applies policy through its Access Control Policy (ACP) — NOT persistent `access-list`
>   CLI**. On FMC-managed FTD, treat the `access-list`/`access-group` output as the *intent*
>   to rebuild as ACP rules, not as deployable config.

---

## address_objects

**Classification: converted** (clean 1:1 — host / subnet / range / fqdn).

One `object network <name>` block per object; the kind selects the sub-command.

```
object network HOST-WEB-01
 host 10.20.30.10
 description Production web server
object network NET-USERS
 subnet 10.10.0.0 255.255.0.0
object network RANGE-DHCP
 range 10.10.5.10 10.10.5.50
object network FQDN-UPDATE
 fqdn v4 updates.example.com
```

| Schema kind | ASA sub-command |
|-------------|-----------------|
| host (`/32`) | `host <ip>` |
| subnet | `subnet <ip> <mask>` (dotted mask, not CIDR) |
| range | `range <start> <end>` |
| fqdn | `fqdn v4 <domain>` (or `fqdn v6` for IPv6) |

- One value per object — ASA `object network` holds a **single** address. Multi-value
  source objects must be split into several objects collected by an `object-group network`.
- CAVEAT only when a source object was zone-scoped and is flattened to the global object
  table: `# CAVEAT: source zone-local address moved to global object table; verify no name collision`.

## address_groups

**Classification: converted** (clean 1:1).

```
object-group network WEB-SERVERS
 description All web servers
 network-object object HOST-WEB-01
 network-object object HOST-WEB-02
 network-object 10.0.2.0 255.255.255.0
object-group network ALL-INTERNAL
 network-object object NET-USERS
 group-object WEB-SERVERS
```

| Member kind | ASA line |
|-------------|----------|
| reference to named object | `network-object object <name>` |
| inline host | `network-object host <ip>` |
| inline subnet | `network-object <ip> <mask>` (standard mask) |
| nested group | `group-object <name>` |

- Nested groups are native (`group-object`); no flattening needed.

## service_objects

**Classification: converted** for a plain port/protocol; **converted-with-caveats** when an
L7 app is decomposed to a port (App-ID lost) or the parser left the app unresolved.

ASA is **port-based**. Map each canonical service to its port via `feature-mapping.md`
Part 1 (the Cisco column is always `tcp/N`, `udp/N`, `icmp`, or an IP-proto number). Use a
single `object service` for one port, or an `object-group service` for a set of ports.

```
object service SVC-HTTPS-8443
 service tcp destination eq 8443
object service SVC-APP-RANGE
 service tcp source range 1024 65535 destination range 8080 8090
object service SVC-DNS-UDP
 service udp destination eq 53
```

Format: `service <protocol> [source <op> <port>] [destination <op> <port>]`. Operators:
`eq`, `range <lo> <hi>`, `gt`, `lt`, `neq` (neq has limited support — flag it).

- ICMP is a protocol, not a port: `service icmp` (optionally `service icmp <type> <code>`).
- An IP-protocol-only match (e.g. OSPF) is `service 89` / the protocol keyword.
- CAVEAT when an L7 app from SRX/Palo is decomposed to a port:
  `# CAVEAT: L7 app <x> approximated as port <n> — ASA is port-based, App-ID identity lost; no equivalent to rebuild on classic ASA` → **converted-with-caveats**.
- CAVEAT for a parser-unresolved app (`confidence: 0.0`):
  `# CAVEAT: unresolved source application emitted as residual — define the port manually, do not trust a guess` → **manual-not-converted** for that object.

## service_groups

**Classification: converted** (clean 1:1).

Two flavors — protocol-specific (`port-object`) and mixed-protocol (`service-object`):

```
object-group service WEB-PORTS tcp
 description Web service ports
 port-object eq www
 port-object eq https
 port-object range 8080 8090
object-group service MIXED-SVC
 service-object tcp destination eq 22
 service-object udp destination eq 53
 service-object icmp
 service-object object SVC-HTTPS-8443
 group-object OTHER-SVC
```

- `object-group service <name> tcp|udp` → use `port-object` (ports only).
- `object-group service <name>` (no protocol) → use `service-object` (protocol + port,
  may reference `object` and nest `group-object`).
- Port names (`www`, `https`, `domain`, `ssh`, …) and numbers are interchangeable.

## zones

**Classification: converted-with-caveats** (always lossy to/from ASA — there is **no
named-zone object**; see `feature-mapping.md` → zones).

ASA has no zone construct. A "zone" is an **interface** identity: a `nameif` name plus a
`security-level` (0 = least trusted / `outside`, 100 = most trusted / `inside`, 1–99
intermediate). By default traffic flows high→low; ACLs override that. Emit zones as
`nameif`/`security-level` on the relevant `interface` (see interfaces), and realize policy
as ACLs applied per-interface (see security_policies).

```
interface GigabitEthernet0/1
 nameif inside
 security-level 100
interface GigabitEthernet0/0
 nameif outside
 security-level 0
interface GigabitEthernet0/2
 nameif dmz
 security-level 50
```

- Map each source zone to one `nameif`; pick a `security-level` from the source trust
  ordering (most-trusted → 100, internet-facing → 0, DMZ/intermediate → 50).
- CAVEAT (mandatory): `# CAVEAT: ASA has no named-zone object — source zones realized as nameif + security-level on interfaces; policy is per-interface ACLs. Verify interface/zone mapping`.
- CAVEAT (from any zone-based source): `# CAVEAT: security-level high→low implicit permit replaced by explicit ACL — the implicit trust ordering is not representable as a zone object`.

## security_policies

**Classification: converted-with-caveats** (action/logging convert; **L7 app and UTM
intent do not exist on classic ASA**). **Preserve source rule order** — ASA matches ACEs
top-to-bottom, first match wins.

A policy becomes an `access-list <name> extended permit|deny <proto> <src> <dst> [port]`
entry, with the ACL bound to the **ingress** interface (source zone) via `access-group`.

Action / logging map:

| Schema | ASA ACE |
|--------|---------|
| `action: allow` | `... permit ...` |
| `action: deny` | `... deny ...` (silent drop) |
| `action: drop` | `... deny ...` (ASA ACL drops silently — same emitted form as `deny`) |
| `action: reset-both` | `... deny ...` + `# CAVEAT: source action reset-both — ASA ACL has no per-rule TCP reset; emitted as deny (silent drop). A global `service resetinbound`/`set connection ... reset` is the closest, manual` |
| `log_*` set | append `log` (optionally `log <level> interval <n>`) |
| `disabled: true` | append `inactive` (preserve, don't drop) |
| `schedule` ref | append `time-range <name>` (see schedules) |

```
access-list inside_in extended permit tcp object-group NET-USERS any eq www log
access-list inside_in extended permit tcp object-group NET-USERS any eq https log
access-list inside_in extended deny ip any any log
!
access-group inside_in in interface inside
!
access-list outside_in extended permit tcp any object HOST-WEB-01 eq https log
access-list outside_in extended deny ip any any log
!
access-group outside_in in interface outside
```

- One ACL per ingress interface; name it `<nameif>_in` by convention. Bind with
  `access-group <acl> in interface <nameif>` (or `... global` for a global ACL).
- Source/dest take `any`, `host <ip>`, `object <name>`, or `object-group <name>`; ports
  use `eq/range/gt/lt` or `object-group <svc>`.
- Emit an explicit terminating `deny ip any any log` to preserve a source default-deny +
  logging intent (ASA's implicit deny is silent).
- CAVEAT (mandatory when source carried L7/app match):
  `# CAVEAT: L7 application match decomposed to port(s) — classic ASA has no App-ID; application identity lost`.
- CAVEAT (mandatory when source rule had UTM/security profiles):
  `# CAVEAT: per-rule UTM/IPS/URL/AV profile has no classic-ASA equivalent — dropped; rebuild on FTD (FMC ACP + intrusion/file policies)` → **manual-not-converted** for the profile intent.
- CAVEAT (reset-both): `# CAVEAT: source action 'reset-both' emitted as ACL deny — ASA ACE drops silently, no per-rule TCP RST/ICMP unreachable; global 'service resetinbound' is the closest, manual`.
- **FTD note (see header):** on FMC-managed FTD these ACEs are the *intent* for ACP rules,
  not deployable `access-list` CLI.

## nat_rules

**Classification: converted-with-caveats** (intent maps; container restructured —
`feature-mapping.md` → nat_rules). **Preserve rule order** (manual-NAT section ordering is
significant).

ASA has two NAT forms: **Auto NAT (object NAT)** declared inside an `object network`, and
**Manual / Twice NAT** as top-level `nat (real,mapped) source ... [destination ...]` lines.

Auto NAT — static (1:1) and dynamic PAT:

```
object network HOST-WEB-01
 host 10.20.30.10
 nat (inside,outside) static 203.0.113.50
!
object network NET-USERS
 subnet 10.10.0.0 255.255.0.0
 nat (inside,outside) dynamic interface
```

Manual / Twice NAT (twice-NAT, policy NAT, NAT exemption):

```
nat (inside,outside) source dynamic NET-USERS interface
nat (inside,outside) source static internal-net internal-net destination static vpn-net vpn-net
nat (inside,outside) 1 source static HOST-WEB-01 SVC-MAP-50 service tcp-svc tcp-svc
```

- `nat (<real-nameif>,<mapped-nameif>) ...` — the interface pair comes from the source/dest
  zones. `static <mapped>` = 1:1; `dynamic interface` = PAT to the egress interface IP;
  `dynamic <pool>` = pool PAT.
- `source static A A destination static B B` with identical real/mapped = **NAT exemption**
  (common for VPN traffic).
- Section: `1` = before auto-NAT, `2`/omitted = after.
- CAVEAT (mandatory): `# CAVEAT: source NAT rule-set re-anchored to ASA object-NAT (auto) / twice-NAT (manual); verify (real,mapped) interface pairs, rule section/order, and proxy-ARP behavior`.

## interfaces

**Classification: converted-with-caveats** — physical names are platform-bound and never
portable (`feature-mapping.md` → interfaces). Carry IP/`nameif`/`security-level` over;
remap the physical name positionally and CAVEAT it.

```
interface GigabitEthernet0/0
 nameif outside
 security-level 0
 ip address 203.0.113.2 255.255.255.252
 no shutdown
interface GigabitEthernet0/1
 nameif inside
 security-level 100
 ip address 10.10.0.1 255.255.255.0
 no shutdown
interface GigabitEthernet0/1.100
 vlan 100
 nameif users
 security-level 80
 ip address 10.10.100.1 255.255.255.0
```

- 1st data port → `GigabitEthernet0/0`, next → `0/1`, …; management → `Management0/0`.
- Sub-interface (`is_subif`) → `<parent>.<id>` + `vlan <id>`.
- IPv6: `ipv6 address 2001:db8:dmz::1/64` (CIDR retained for v6).
- DHCP-learned/secondary addressing and `standby` (failover) IPs need review.
- CAVEAT (always, first interface):
  `# CAVEAT: interface names remapped positionally — verify against target ASA/FTD port layout, nameif, and security-level`.

## static routes, OSPF, BGP

**Classification: converted-with-caveats** — protocol params map; hierarchy differs and
route-map/prefix-list idioms rarely translate verbatim (`feature-mapping.md` →
static_routes/OSPF/BGP). **Preserve route order.**

Static routes — `route <nameif> <dest> <mask> <gateway> [metric]`:

```
route outside 0.0.0.0 0.0.0.0 203.0.113.1 1
route inside 10.50.0.0 255.255.0.0 10.10.0.254 1
```

OSPF — `router ospf <pid>` + `network ... area`:

```
router ospf 1
 router-id 10.10.0.1
 network 10.10.0.0 255.255.0.0 area 0
 area 0
 log-adj-changes
```

BGP — `router bgp <asn>` + `neighbor`:

```
router bgp 65001
 bgp router-id 10.10.0.1
 address-family ipv4 unicast
  neighbor 203.0.113.1 remote-as 65010
  network 10.10.0.0 mask 255.255.0.0
 exit-address-family
```

- ASA `network` statements use **standard masks** (`network 10.10.0.0 255.255.0.0 area 0`),
  not IOS wildcard masks.
- CAVEAT: `# CAVEAT: route-maps/prefix-lists/distribute-lists must be re-authored as ASA route-map/prefix-list objects — import/export policy not converted verbatim` → **manual-not-converted** for the policy bodies.
- CAVEAT (IPv6): emit `ipv6 route`, `ipv6 router ospf` / OSPFv3, and the IPv6 BGP
  address-family separately.

## system, admin_users, DHCP

**Classification: converted-with-caveats** — base system maps; passwords are placeholders.

System base from schema `system`:

```
hostname fw-edge-01
domain-name example.com
dns domain-lookup inside
dns server-group DefaultDNS
 name-server 10.10.0.53
 name-server 1.1.1.1
ntp server 10.10.0.123 source inside
```

admin_users (`username ... privilege`) — **passwords never emitted**:

```
username admin1 password <PASSWORD-PLACEHOLDER> privilege 15
username netops password <PASSWORD-PLACEHOLDER> privilege 5
```

- CAVEAT (mandatory): `# CAVEAT: admin password not converted — set credentials manually on ASA/FTD` → **manual-not-converted** for the secret. Never carry over an encrypted password hash.

DHCP (`dhcpd`) on an interface:

```
dhcpd address 10.10.0.100-10.10.0.200 inside
dhcpd dns 10.10.0.53 interface inside
dhcpd lease 86400 interface inside
dhcpd enable inside
```

- DHCP relay instead: `dhcprelay server 10.10.0.53 outside` + `dhcprelay enable inside`.
- CAVEAT: `# CAVEAT: DHCP pool/option model differs — verify range, lease, and options on ASA/FTD`.

## ha_config

**Classification: converted-with-caveats** (note only — failover link/interface IPs and
unit roles are hardware-specific; verify on the real pair).

```
failover
failover lan unit primary
failover lan interface FAILOVER GigabitEthernet0/3
failover interface ip FAILOVER 10.0.255.1 255.255.255.0 standby 10.0.255.2
failover link STATE GigabitEthernet0/4
failover interface ip STATE 10.0.254.1 255.255.255.0 standby 10.0.254.2
```

- CAVEAT (mandatory): `# CAVEAT: failover lan/state interfaces, unit roles, and standby IPs are platform-specific — verify on the real ASA pair before enabling`.
- Any failover/cluster shared key is a secret → placeholder + manual item, never emit.

## vpn_tunnels (IKE / IPsec)

**Classification: converted-with-caveats** for crypto params; **manual-not-converted** for
PSK/certs — **secrets are never emitted** (`feature-mapping.md` → vpn_tunnels).

Emit IKEv2 crypto + `tunnel-group` + `crypto map`, with a **placeholder** PSK:

```
crypto ikev2 policy 10
 encryption aes-256
 integrity sha256
 group 14
 prf sha256
 lifetime seconds 86400
!
crypto ipsec ikev2 ipsec-proposal AES256-SHA256
 protocol esp encryption aes-256
 protocol esp integrity sha-256
!
tunnel-group 198.51.100.2 type ipsec-l2l
tunnel-group 198.51.100.2 ipsec-attributes
 ikev2 remote-authentication pre-shared-key <PSK-PLACEHOLDER>
 ikev2 local-authentication pre-shared-key <PSK-PLACEHOLDER>
!
crypto map OUTSIDE-MAP 10 match address VPN-SITEB
crypto map OUTSIDE-MAP 10 set peer 198.51.100.2
crypto map OUTSIDE-MAP 10 set ikev2 ipsec-proposal AES256-SHA256
crypto map OUTSIDE-MAP interface outside
crypto ikev2 enable outside
```

- The `match address` ACL (`VPN-SITEB`) defines the encryption domain / proxy-id — build it
  as an `access-list` from the source traffic selectors.
- A route-based source (SRX st0 / Palo tunnel-iface) re-models as ASA VTI
  (`interface Tunnel<n>` + `tunnel protection ipsec profile`) **or** policy-based crypto map;
  re-validate selectors either way.
- CAVEAT (mandatory): `# CAVEAT: PSK/certificate not converted — re-key the VPN manually on ASA/FTD before enabling` → **manual-not-converted** item.
- CAVEAT: `# CAVEAT: route-based tunnel re-modeled as crypto map / VTI — re-validate peer, proxy-id/match-address, and DH/lifetime against source`.

## screens (threat-protection)

**Classification: manual-not-converted** (largely) — classic ASA has **no full screen
model**; only coarse `threat-detection` and TCP-normalizer / connection limits exist
(`feature-mapping.md` → screens).

Closest ASA equivalents — emit only as a best-effort, flag the rest manual:

```
threat-detection basic-threat
threat-detection statistics
threat-detection rate scanning-threat rate-interval 600 average-rate 5 burst-rate 10
!
policy-map global_policy
 class inspection_default
  set connection conn-max 10000 embryonic-conn-max 1000
```

- TCP normalization (anti-spoof/flood approximation) lives under a `tcp-map` referenced from
  a policy-map class.
- CAVEAT (mandatory): `# CAVEAT: SRX screen / Palo zone-protection has no classic-ASA equivalent — only coarse threat-detection / connection limits emitted; per-option flood/scan/spoof thresholds are manual-not-converted (use FTD for richer protection)`.

## schedules

**Classification: converted** (intent 1:1; minor recurrence-syntax loss).

```
time-range BIZ-HOURS
 periodic weekdays 08:00 to 18:00
!
time-range MAINT-WINDOW
 absolute start 00:00 01 July 2026 end 06:00 01 July 2026
```

- Reference from an ACE: `access-list inside_in extended permit ... time-range BIZ-HOURS`.
- `periodic` = recurring (days + `HH:MM to HH:MM`); `absolute` = one-time window.
- Source "no restriction" → omit `time-range` entirely (no object).
- CAVEAT only when recurrence can't be expressed exactly:
  `# CAVEAT: source recurrence approximated — verify time-range day/time windows`.

## security-profile attachments & management-plane access

Two distinct schema concerns, neither named `security_services` (which is only a device-wide
security-service presence flag set — app_id/idp/secintel/aamw/utm — used for caveats, not
config):

**1. Security-profile attachments (`security_policies[].security_profiles` /
`security_profile_objects`) — Classification: manual-not-converted.**
Classic ASA has **no NGFW UTM** (AV/IPS/URL/WildFire/app-control) — there is nothing to
attach. Record every dropped source security-profile attachment as a manual item; rebuild on
**FTD** (FMC intrusion / file / URL policies in the ACP), not on ASA.

- CAVEAT (mandatory): `# CAVEAT: classic ASA has no UTM/IPS/URL/AV/app-control — source security-profile attachments dropped; rebuild on Firepower/FTD via FMC (intrusion + file + URL policies). Not converted`.

**2. Management-plane access (`zones[].host_inbound` / `system.mgmt_services`) —
Classification: converted-with-caveats.** Which management services an interface/zone
accepts maps to ASA management permit lines — keyed by `nameif`:

```
ssh 10.10.0.0 255.255.255.0 inside
ssh version 2
http 10.10.0.0 255.255.255.0 inside
http server enable
icmp permit any inside
```

- Avoid emitting `telnet ...` for management unless the source explicitly had it — flag
  plaintext management for review.
- CAVEAT: `# CAVEAT: management access re-anchored to ASA ssh/http/icmp permit lines per nameif — verify management-plane exposure vs source zone/interface-mgmt model`.
- Never emit management secrets/keys (SNMP community, enable/admin password) — placeholder +
  manual item.

---

## Emit checklist (Cisco ASA/FTD target)

- [ ] All masks are dotted-decimal standard masks (not CIDR, not IOS wildcard).
- [ ] ACL order preserved in source order; disabled rules emitted `inactive`, not dropped;
      explicit `deny ip any any log` added to preserve default-deny + logging intent.
- [ ] Each ACL bound with `access-group <acl> in interface <nameif>`; zones realized as
      `nameif` + `security-level`, with the no-named-zone CAVEAT.
- [ ] L7/app matches decomposed to ports with the App-ID-lost CAVEAT; UTM/profile intent
      recorded **manual-not-converted** (no classic-ASA equivalent — rebuild on FTD/FMC).
- [ ] NAT re-anchored: object-NAT (auto) for simple static/PAT, twice-NAT (manual) for
      policy/exemption; (real,mapped) pairs and section/order verified.
- [ ] Interfaces remapped positionally with nameif/security-level/ip; remap CAVEAT emitted.
- [ ] Routing under `route` / `router ospf` / `router bgp`; route-maps/prefix-lists flagged
      manual.
- [ ] VPN: IKEv2 policy + tunnel-group + crypto map (or VTI); PSK/cert is a placeholder +
      manual item; `match address` ACL rebuilt from selectors.
- [ ] All secrets are placeholders + a manual-not-converted item — no encrypted password
      hashes carried over.
- [ ] FTD/FMC caveat stated: these are ASA-style LINA CLI; FMC-managed FTD rebuilds policy
      as an Access Control Policy, not persistent `access-list` CLI.
- [ ] Each lossy section carries its inline `# CAVEAT:` and the matching fidelity
      classification.

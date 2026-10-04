# Emit Palo Alto PAN-OS `set` Configuration

## Contents

- [address_objects](#address_objects)
- [address_groups](#address_groups)
- [service_objects](#service_objects)
- [service_groups / application_groups](#service_groups--application_groups)
- [zones](#zones)
- [security_policies](#security_policies)
- [nat_rules](#nat_rules)
- [interfaces](#interfaces)
- [virtual-router (static routes, OSPF, BGP)](#virtual-router-static-routes-ospf-bgp)
- [system (deviceconfig), admin_users, DHCP](#system-deviceconfig-admin_users-dhcp)
- [ha_config (HA note)](#ha_config-ha-note)
- [vpn_tunnels (IKE / IPsec crypto profiles)](#vpn_tunnels-ike--ipsec-crypto-profiles)
- [screens (zone-protection profile)](#screens-zone-protection-profile)
- [schedules](#schedules)
- [security_services (profiles / security-profile-group + interface mgmt)](#security_services-profiles--security-profile-group--interface-mgmt)
- [Emit checklist (PAN-OS target)](#emit-checklist-pan-os-target)

Target-emitter reference for the `firewall-config-conversion` skill. Loaded when the
conversion **target = Palo Alto (PAN-OS)**. For every emittable section of the intermediate
schema this file shows the native PAN-OS **config-mode `set`** syntax to render (CLI `set`
form, **not** XML), the fidelity classification (`converted` /
`converted-with-caveats` / `manual-not-converted`), and the inline `# CAVEAT:` to emit when
the translation is lossy. Cross-vendor lossiness is sourced from
`references/feature-mapping.md`; PAN-OS syntax discipline follows the
`parsing-palo-configs` skill's config-format reference (XML-to-CLI mapping: named objects use
`set address <name>`, multi-value members go in square brackets, e.g.
`set address-group WEB-SERVERS static [ WEB-01 WEB-02 ]`).

> **Config-mode `set` syntax, not XML.** Everything below is the CLI form you type after
> `configure` — e.g. `set address WEB-01 ip-netmask 10.20.30.10/32`. By default objects land
> in `vsys1`; if the schema carries `_vsys`, prefix the path with `set vsys <name> …` (or
> `set shared …` for shared objects).
>
> **Secrets are NEVER emitted.** PSKs, certificates, and admin passwords are rendered as
> `<PSK-PLACEHOLDER>` / `<KEY-PLACEHOLDER>` / `<PASSWORD-PLACEHOLDER>` plus a
> `manual-not-converted` item — never a real value.
>
> **GCM crypto rule (PAN-OS validation constraint).** In IKE/IPsec crypto profiles a GCM
> cipher (e.g. `aes-256-gcm`, `aes-128-gcm`) carries its own authentication, so it **must**
> pair with `hash none` (IKE) / `authentication none` (IPsec). Never emit a separate
> hash/auth (`sha256`, `sha1`, …) alongside a GCM cipher — PAN-OS rejects the profile. See
> the vpn_tunnels section.

> **Port-based source caveat (Cisco/FortiGate → Palo).** Cisco ASA/FTD and FortiGate base
> policies match on **port/protocol service objects**, not App-ID. When converting them to
> Palo, emit `service` objects and match `application any` + that service — **App-ID is only
> inferred where the parser resolved a canonical app** (see `feature-mapping.md` Part 1).
> Do not invent an App-ID token from a bare port; flag low-confidence guesses for review.

---

## address_objects

**Classification: converted** (clean 1:1 — host / subnet / range / fqdn).

One `set address` line per object. Pick the value keyword from the schema `type`:

```
set address WEB-01 ip-netmask 10.20.30.10/32
set address NET-USERS ip-netmask 10.10.0.0/16
set address DHCP-RANGE ip-range 10.10.5.10-10.10.5.50
set address UPDATE-SRV fqdn updates.example.com
set address NET6-DMZ ip-netmask 2001:db8:dmz::/64
set address WILD-10 ip-wildcard 10.0.0.0/0.0.255.255
set address WEB-01 description "Production web server"
set address WEB-01 tag production
```

- `ip-netmask` for host/subnet (host = `/32` or `/128`), `ip-range` for ranges,
  `fqdn` for FQDN, `ip-wildcard` for wildcard. IPv4/IPv6 use the same `ip-netmask` keyword.
- `type: geo` has no address-object form on PAN-OS — emit
  `# CAVEAT: geo address has no PAN-OS address object — use a region/geo match in the rule` and classify **converted-with-caveats**.
- Quote names/values containing spaces. Referenced tags should also be created with
  `set tag <name> color <n>` (optional).

## address_groups

**Classification: converted** (clean 1:1).

Static groups list members; nested groups simply name the child group as a member:

```
set address-group WEB-SERVERS static [ WEB-01 WEB-02 ]
set address-group ALL-SERVERS static [ WEB-SERVERS DB-SERVERS ]
set address-group AUTO-WEB dynamic filter "'production' and 'web'"
```

- Schema `members` → `static [ … ]`. A tag-based group (rare in conversion) uses `dynamic
  filter`.
- Empty group → emit the group with a placeholder member and
  `# CAVEAT: empty address-group — add members or remove`.

## service_objects

**Classification: converted** (clean 1:1 for tcp/udp); **converted-with-caveats** for
protocols PAN-OS services can't express.

One `set service` line per object; `protocol tcp|udp` then `port`:

```
set service CUSTOM-HTTPS protocol tcp port 8443
set service SVC-UDP-RANGE protocol udp port 16384-32767
set service CUSTOM-HTTPS protocol tcp source-port 1024-65535
set service CUSTOM-HTTPS description "Custom HTTPS port"
```

- PAN-OS service objects are **TCP or UDP only**. ICMP/SCTP/IP-proto and `any` have **no
  service object** — for ICMP/IP-proto match the corresponding **App-ID** (`ping`,
  `icmp`, `ipv6-icmp`, `ospf`, …) in the rule instead, and emit
  `# CAVEAT: non-TCP/UDP service has no PAN-OS service object — matched via App-ID/application instead` (classify **converted-with-caveats**).
- This is the **landing spot for port-based Cisco/FortiGate services** — render them here as
  `service` objects rather than guessing an App-ID.

## service_groups / application_groups

**Classification: converted** (clean 1:1). Split by member kind: port/protocol members →
**service-group**, resolved L7 apps → **application-group**.

```
set service-group WEB-SERVICES members [ CUSTOM-HTTPS service-https ]
set application-group WEB-APPS members [ web-browsing ssl quic ]
```

- Schema `service_groups` → `service-group`; schema `application_groups` (canonical app
  keys) → `application-group`, mapping each member canonical → App-ID via
  `feature-mapping.md` Part 1.
- Mixed source groups must be split; nesting is allowed (a group name may be a member).
- CAVEAT for any member from an unresolved app (`confidence 0.0`):
  `# CAVEAT: unresolved application dropped from group — add manually` → **manual-not-converted** for that member.

## zones

**Classification: converted** (from SRX/Palo source); **converted-with-caveats** (from
FortiGate/ASA — `feature-mapping.md` → zones).

One zone per schema zone, interfaces bound as layer3 members:

```
set zone TRUST network layer3 ethernet1/1
set zone TRUST network layer3 ethernet1/2
set zone UNTRUST network layer3 ethernet1/3
```

- One `network layer3 <iface>` per interface. Use `layer2` / `virtual-wire` / `tap` from
  schema `zone_type` when not layer3.
- A bound zone-protection profile and interface-management exposure are emitted under
  screens and security_services respectively.
- CAVEAT when source is Cisco ASA (`nameif` + `security-level`):
  `# CAVEAT: ASA security-level trust ordering not representable on PAN-OS — implicit high→low permit replaced by explicit rules`.
- CAVEAT when source is FortiGate matching interfaces directly:
  `# CAVEAT: source matched interfaces, not named zones — zone synthesized per source interface; verify intrazone intent`.

## security_policies

**Classification: converted-with-caveats** (action/logging map cleanly; L7 apps and any
unresolved apps are lossy). **Preserve source rule order** — PAN-OS evaluates rules
top-down in config order; emit rules in `_rule_index` order and keep names ordered (e.g.
`010-…`, `100-…`) so order is unambiguous.

Field map:

| Schema | PAN-OS `set rulebase security rules <n>` leaf |
|--------|-----------------------------------------------|
| `src_zones` | `from <zone>` (`from any`) |
| `dst_zones` | `to <zone>` (`to any`) |
| `src_addresses` | `source [ … ]` (`source any`) |
| `dst_addresses` | `destination [ … ]` (`destination any`) |
| `negate_source` | `negate-source yes` |
| `negate_destination` | `negate-destination yes` |
| `apps` (resolved L7) | `application [ <App-ID> … ]` via feature-mapping |
| `services` (port match) | `service [ … ]` or `application-default` |
| `action: allow` | `action allow` |
| `action: deny`/`drop` | `action deny` (silent drop) |
| `action: reset-both` | `action reset-both` |
| `log_start: true` | `log-start yes` |
| `log_end: true` | `log-end yes` |
| (log forwarding) | `log-setting <profile>` |
| `disabled: true` | `disabled yes` (preserve, don't drop) |
| `schedule` | `schedule <name>` |
| `tags` | `tag [ … ]` |

```
set rulebase security rules 100-USERS-WEB from TRUST
set rulebase security rules 100-USERS-WEB to UNTRUST
set rulebase security rules 100-USERS-WEB source NET-USERS
set rulebase security rules 100-USERS-WEB destination any
set rulebase security rules 100-USERS-WEB application [ web-browsing ssl ]
set rulebase security rules 100-USERS-WEB service application-default
set rulebase security rules 100-USERS-WEB action allow
set rulebase security rules 100-USERS-WEB log-end yes
set rulebase security rules 100-USERS-WEB log-setting default-fwd
```

- Map L7 apps via `feature-mapping.md` Part 1 (canonical → App-ID). When the source carried
  real L7 intent and apps resolved, prefer `application <App-ID>` + `service
  application-default`.
- **Port-based source (Cisco/FortiGate):** emit `application any` + an explicit
  `service [ SVC-… ]` (the objects from service_objects), and
  `# CAVEAT: L7 App-ID not inferred from port — rule matches service only; refine with App-ID after review`.
- CAVEAT for any app at `confidence 0.0`:
  `# CAVEAT: unresolved application emitted as residual — do not trust port guess` → **manual-not-converted** for that match.
- Profile attachment is emitted under security_services (`profile-setting`).

## nat_rules

**Classification: converted-with-caveats** (intent maps; container/pool/bidirectional flags
restructured — `feature-mapping.md` → nat_rules). **Preserve rule order.**

Source NAT (PAT to egress interface):

```
set rulebase nat rules SNAT-USERS from TRUST
set rulebase nat rules SNAT-USERS to UNTRUST
set rulebase nat rules SNAT-USERS source NET-USERS
set rulebase nat rules SNAT-USERS destination any
set rulebase nat rules SNAT-USERS source-translation dynamic-ip-and-port interface-address interface ethernet1/3
```

Source NAT to a translated address pool:

```
set rulebase nat rules SNAT-POOL source-translation dynamic-ip-and-port translated-address NAT-POOL
```

Destination NAT (port forward) and static NAT:

```
set rulebase nat rules DNAT-WEB from UNTRUST
set rulebase nat rules DNAT-WEB to UNTRUST
set rulebase nat rules DNAT-WEB destination PUB-WEB-IP
set rulebase nat rules DNAT-WEB service service-https
set rulebase nat rules DNAT-WEB destination-translation translated-address 10.20.30.10 translated-port 443
set rulebase nat rules STAT-MAIL source-translation static-ip translated-address 203.0.113.60
```

- `source-translation` types: `dynamic-ip-and-port` (PAT), `dynamic-ip`, `static-ip`.
  `destination-translation` carries `translated-address` (+ optional `translated-port`).
- Bidirectional static maps to `static-ip … bi-directional yes`.
- CAVEAT when source folded dest-NAT into a VIP (FortiGate):
  `# CAVEAT: source VIP/dest-NAT re-anchored into PAN-OS destination-translation — verify port-forward and NAT zone (dst zone = pre-NAT)`.
- CAVEAT: `# CAVEAT: PAN-OS dest-NAT 'to' zone is the pre-NAT zone — verify NAT vs security zone mismatch`.

## interfaces

**Classification: converted-with-caveats** — physical names are platform-bound and never
portable (`feature-mapping.md` → interfaces). Carry IP addressing over; remap names
positionally and CAVEAT.

```
set network interface ethernet ethernet1/1 layer3 ip 10.10.0.1/24
set network interface ethernet ethernet1/3 layer3 ip 203.0.113.2/30
set network interface ethernet ethernet1/1 layer3 ipv6 address 2001:db8:trust::1/64 enable-on-interface yes
set network interface ethernet ethernet1/1 layer3 units ethernet1/1.100 tag 100
set network interface ethernet ethernet1/1 layer3 units ethernet1/1.100 ip 10.10.100.1/24
set network interface ethernet ethernet1/3 layer3 dhcp-client enable yes
```

- One `ip` leaf per address. Sub-interfaces (`is_subif`) use `units <iface>.<n> tag <vlan>`.
- Aggregate (`lag_parent`/`lag_members`) → `set network interface aggregate-ethernet ae1
  layer3 ip …` plus per-member `set network interface ethernet ethernet1/4 aggregate-group ae1`.
- Loopback/tunnel → `set network interface loopback …` / `set network interface tunnel
  units tunnel.1 …`.
- CAVEAT (always, first interface):
  `# CAVEAT: interface names remapped positionally — verify against target PAN-OS hardware (slot/port) and zone binding`.

## virtual-router (static routes, OSPF, BGP)

**Classification: converted-with-caveats** — protocol params map; hierarchy differs and
route-map/redistribution idioms rarely translate verbatim (`feature-mapping.md` →
static_routes/OSPF/BGP). **Preserve route order.** Bind interfaces and routing into a
named virtual-router (schema `virtual_routers`, default `default`).

Interface membership + static routes:

```
set network virtual-router default interface [ ethernet1/1 ethernet1/3 ]
set network virtual-router default routing-table ip static-route DEFAULT destination 0.0.0.0/0
set network virtual-router default routing-table ip static-route DEFAULT nexthop ip-address 203.0.113.1
set network virtual-router default routing-table ip static-route DEFAULT metric 10
set network virtual-router default routing-table ip static-route NET-50 destination 10.50.0.0/16
set network virtual-router default routing-table ip static-route NET-50 nexthop ip-address 10.10.0.254
```

OSPF (schema `ospf_config`):

```
set network virtual-router default protocol ospf enable yes
set network virtual-router default protocol ospf router-id 10.0.0.1
set network virtual-router default protocol ospf area 0.0.0.0 type normal
set network virtual-router default protocol ospf area 0.0.0.0 interface ethernet1/1 enable yes
set network virtual-router default protocol ospf area 0.0.0.0 interface ethernet1/1 metric 10
set network virtual-router default protocol ospf area 0.0.0.0 interface ethernet1/1 passive yes
```

BGP (schema `bgp_config`):

```
set network virtual-router default protocol bgp enable yes
set network virtual-router default protocol bgp local-as 65001
set network virtual-router default protocol bgp router-id 10.0.0.1
set network virtual-router default protocol bgp peer-group EBGP-UP type ebgp
set network virtual-router default protocol bgp peer-group EBGP-UP peer PEER1 peer-address ip 203.0.113.1
set network virtual-router default protocol bgp peer-group EBGP-UP peer PEER1 peer-as 65010
```

- A separate virtual-router per schema VRF; routing-instance/VRF boundaries differ →
  `# CAVEAT: source VRF/context boundaries differ on PAN-OS virtual-router — re-scope per-VR routing/zones`.
- CAVEAT: `# CAVEAT: route-maps/prefix-lists become PAN-OS redistribution/export rules — re-author import/export policy manually` (manual-not-converted for the policy bodies).

## system (deviceconfig), admin_users, DHCP

**Classification: converted-with-caveats** — base system maps; passwords are placeholders.

System base from schema `system`:

```
set deviceconfig system hostname fw-edge-01
set deviceconfig system domain example.com
set deviceconfig system dns-setting servers primary 10.10.0.53
set deviceconfig system dns-setting servers secondary 1.1.1.1
set deviceconfig system ntp-servers primary-ntp-server ntp-server-address 10.10.0.123
set deviceconfig system service disable-telnet yes
set deviceconfig system service disable-http yes
```

- Map `mgmt_services` to `deviceconfig system service` `disable-…` toggles (PAN-OS mgmt
  services are disabled-by-flag). SSH/HTTPS to the mgmt plane are on by default.

admin_users (schema `admin_users` → `mgt-config users`) — **passwords never emitted**:

```
set mgt-config users admin1 permissions role-based superuser yes
set mgt-config users admin1 phash <PASSWORD-PLACEHOLDER>
set mgt-config users netops permissions role-based superreader yes
```

- Map role: `super-admin→superuser`, `read-only→superreader`, custom→`role-based <profile>`.
- CAVEAT: `# CAVEAT: admin password/phash not converted — set credentials manually` → **manual-not-converted** for the secret.

DHCP (schema `dhcp_config` server / relay):

```
set network dhcp interface ethernet1/1 server ip-pool 10.10.0.100-10.10.0.200
set network dhcp interface ethernet1/1 server option gateway 10.10.0.1
set network dhcp interface ethernet1/1 server option dns primary 10.10.0.53
set network dhcp interface ethernet1/1 server option lease timeout 1440
set network dhcp interface ethernet1/2 relay ip server 10.10.0.53
```

- DHCP relay uses `relay ip server <addr>` on the client-facing interface.
- CAVEAT: `# CAVEAT: DHCP pool/option model differs — verify lease, options, and reservations on PAN-OS`.

## ha_config (HA note)

**Classification: converted-with-caveats** (note only — not commit-safe to auto-emit).

PAN-OS HA depends on dedicated HA interfaces (HA1 control / HA2 data) and a matched peer
serial/IP; the link and election layout is hardware-specific. Emit a commented skeleton plus
a manual item rather than a live config:

```
# CAVEAT: HA must be brought up per-device with matched peer serial/IP and verified on real hardware — skeleton only
# set deviceconfig high-availability enabled yes
# set deviceconfig high-availability group 1 mode active-passive passive-link-state auto
# set deviceconfig high-availability group 1 peer-ip 10.0.0.2
# set deviceconfig high-availability group 1 election-option device-priority 100
# set deviceconfig high-availability group 1 election-option preemptive yes
# set deviceconfig high-availability group 1 configuration-synchronization enabled yes
```

- Schema `mode` → `active-passive` / `active-active`; `priority`/`preempt`/`peer_ip` fill
  the election + peer leaves. Record **manual-not-converted** for HA bring-up.

## vpn_tunnels (IKE / IPsec crypto profiles)

**Classification: converted-with-caveats** for crypto params; **manual-not-converted** for
PSK/certs — **secrets are never emitted** (`feature-mapping.md` → vpn_tunnels).

Emit IKE crypto profile, IPsec crypto profile, IKE gateway (PSK = placeholder), and the
tunnel, mapping the schema proposals. **GCM rule applies to both crypto profiles.**

IKE crypto profile + gateway (non-GCM example):

```
set network ike crypto-profiles ike-crypto-profiles IKE-CP-1 dh-group group14
set network ike crypto-profiles ike-crypto-profiles IKE-CP-1 hash sha256
set network ike crypto-profiles ike-crypto-profiles IKE-CP-1 encryption aes-256-cbc
set network ike crypto-profiles ike-crypto-profiles IKE-CP-1 lifetime hours 8
set network ike gateway GW-SITEB protocol version ikev2
set network ike gateway GW-SITEB protocol ikev2 ike-crypto-profile IKE-CP-1
set network ike gateway GW-SITEB authentication pre-shared-key key <PSK-PLACEHOLDER>
set network ike gateway GW-SITEB local-address interface ethernet1/3
set network ike gateway GW-SITEB peer-address ip 198.51.100.2
```

IPsec crypto profile + tunnel (non-GCM example):

```
set network ike crypto-profiles ipsec-crypto-profiles IPSEC-CP-1 esp encryption aes-256-cbc
set network ike crypto-profiles ipsec-crypto-profiles IPSEC-CP-1 esp authentication sha256
set network ike crypto-profiles ipsec-crypto-profiles IPSEC-CP-1 dh-group group14
set network ike crypto-profiles ipsec-crypto-profiles IPSEC-CP-1 lifetime hours 1
set network tunnel ipsec VPN-SITEB auto-key ike-gateway GW-SITEB
set network tunnel ipsec VPN-SITEB auto-key ipsec-crypto-profile IPSEC-CP-1
set network tunnel ipsec VPN-SITEB tunnel-interface tunnel.1
```

**GCM variant — REQUIRED form when the proposal uses a GCM cipher.** The GCM cipher carries
its own integrity, so emit `hash none` (IKE) and `authentication none` (IPsec) — never a
separate `sha*`:

```
set network ike crypto-profiles ike-crypto-profiles IKE-GCM dh-group group20
set network ike crypto-profiles ike-crypto-profiles IKE-GCM encryption aes-256-gcm
set network ike crypto-profiles ike-crypto-profiles IKE-GCM hash none
set network ike crypto-profiles ipsec-crypto-profiles IPSEC-GCM esp encryption aes-256-gcm
set network ike crypto-profiles ipsec-crypto-profiles IPSEC-GCM esp authentication none
set network ike crypto-profiles ipsec-crypto-profiles IPSEC-GCM dh-group group20
```

- **GCM rule (mandatory):** if `proposal.encryption` contains `aes-128-gcm`/`aes-256-gcm`,
  drop any integrity from the schema and emit `hash none`/`authentication none`. Emitting a
  GCM cipher with `sha256`/`sha1` is invalid on PAN-OS and fails commit.
- **CAVEAT (mandatory):** `# CAVEAT: PSK/certificate not converted — re-key the VPN manually on PAN-OS before enabling` → **manual-not-converted** item.
- CAVEAT: `# CAVEAT: policy-based crypto-map source re-modeled as route-based tunnel — re-validate peer/proxy-id/proxy-ids and tunnel route`.
- CAVEAT when GCM forces auth drop:
  `# CAVEAT: GCM cipher carries integrity — separate hash/auth omitted per PAN-OS rule`.

## screens (zone-protection profile)

**Classification: converted-with-caveats** (to/from SRX); **manual-not-converted** when
source is Cisco ASA (no full screen model — `feature-mapping.md` → screens).

Schema `screen_config` → a zone-protection profile bound to the zone:

```
set network profiles zone-protection-profile ZP-UNTRUST flood tcp-syn enable yes
set network profiles zone-protection-profile ZP-UNTRUST flood tcp-syn red activate-rate 1000
set network profiles zone-protection-profile ZP-UNTRUST flood tcp-syn red maximal-rate 10000
set network profiles zone-protection-profile ZP-UNTRUST flood icmp enable yes
set network profiles zone-protection-profile ZP-UNTRUST flood icmp red activate-rate 1000
set network profiles zone-protection-profile ZP-UNTRUST scan TCP-Port-Scan action block
set network profiles zone-protection-profile ZP-UNTRUST packet-based-attack-protection ip-malformed-drop yes
set zone UNTRUST network zone-protection-profile ZP-UNTRUST
```

- Map schema `tcp.syn-flood`→`flood tcp-syn`, `icmp.flood`/`udp.flood`→`flood icmp`/`flood
  udp`, `ip.spoofing`→spoofed-IP discard / packet-based, scans→`scan` reconnaissance.
- Bind with the final `set zone … network zone-protection-profile` line.
- CAVEAT: `# CAVEAT: screen thresholds/option names differ across vendors — review activate/maximal rates against source intent`.

## schedules

**Classification: converted** (intent 1:1; minor recurrence-syntax loss).

```
set schedule BIZ-HOURS schedule-type recurring weekly monday [ 08:00-18:00 ]
set schedule BIZ-HOURS schedule-type recurring weekly friday [ 08:00-18:00 ]
set schedule MAINT-WINDOW schedule-type non-recurring [ 2026/07/01@00:00-2026/07/01@06:00 ]
```

Reference from a rule:

```
set rulebase security rules 100-USERS-WEB schedule BIZ-HOURS
```

- Schema `type: recurring` with `days`+`start`/`end` → `recurring weekly <day> [ start-end ]`
  (one day leaf per active day); `type: onetime`/non-recurring → `non-recurring [ … ]`.
- FortiGate `"always"` → emit no schedule (no restriction).
- CAVEAT only when recurrence can't be expressed exactly:
  `# CAVEAT: source recurrence approximated — verify schedule day/time windows`.

## security_services (profiles / security-profile-group + interface mgmt)

**Classification: converted-with-caveats** — attachment shape converts; profile **contents**
are vendor-proprietary (`feature-mapping.md` → security_profiles / security_services).

Per-policy threat attachment. Prefer a **security-profile-group** referenced from the rule;
fall back to individual profiles when the source set distinct profiles:

```
set rulebase security rules 200-USERS-WEB profile-setting group SPG-STRICT
```

Individual profiles (from schema `security_profiles` keys):

```
set rulebase security rules 200-USERS-WEB profile-setting profiles virus default
set rulebase security rules 200-USERS-WEB profile-setting profiles spyware strict
set rulebase security rules 200-USERS-WEB profile-setting profiles vulnerability strict
set rulebase security rules 200-USERS-WEB profile-setting profiles url-filtering strict
set rulebase security rules 200-USERS-WEB profile-setting profiles file-blocking strict
set rulebase security rules 200-USERS-WEB profile-setting profiles wildfire-analysis default
```

- Key map: `virus→virus`, `anti-spyware→spyware`, `idp→vulnerability`,
  `url-filtering→url-filtering`, `file-blocking→file-blocking`, `wildfire→wildfire-analysis`.
- Define the group itself if used: `set profile-group SPG-STRICT virus [ default ] …`.
- CAVEAT: `# CAVEAT: profile contents (signatures/categories/actions) must be rebuilt on PAN-OS — only the attachment is converted`.
- If source is Cisco ASA (no UTM model) → nothing to attach → **manual-not-converted** in the
  report, not in config.

Interface-management exposure (schema `zone.host_inbound` / `security_services` mgmt) maps to
an **interface-management profile** bound to the interface, not the zone:

```
set network profiles interface-management-profile MGMT-LAN ssh yes
set network profiles interface-management-profile MGMT-LAN ping yes
set network profiles interface-management-profile MGMT-LAN https yes
set network interface ethernet ethernet1/1 layer3 interface-management-profile MGMT-LAN
```

- CAVEAT: `# CAVEAT: verify management-plane exposure on PAN-OS — host-inbound services map to an interface-management-profile, not a zone`.
- Never emit management secrets (SNMP community, keys) — placeholder + manual item.

The schema `security_services` presence flags (`app_id`, `idp`, `secintel`, `aamw`, `utm`)
are device-wide intent; they have no single `set` line — record any flagged-but-unattached
service as a follow-up so it isn't silently dropped.

---

## Emit checklist (PAN-OS target)

- [ ] Config-mode `set` syntax throughout (not XML); objects default to `vsys1` / honor `_vsys`.
- [ ] Security-rule order preserved (top-down) via `_rule_index` + ordered names; disabled rules emitted with `disabled yes`, not dropped.
- [ ] `allow→action allow`, `deny→action deny`, `reset-both→action reset-both`, `log_start→log-start yes`, `log_end→log-end yes`, `log-setting` for forwarding.
- [ ] L7 apps mapped canonical→App-ID via feature-mapping; port-based Cisco/FortiGate sources emit `service` objects + `application any` (App-ID only where resolved).
- [ ] NAT and route order preserved; VIP/dest-NAT zone semantics CAVEATed.
- [ ] **GCM ciphers paired with `hash none` / `authentication none`** — never a separate sha/auth.
- [ ] All secrets (PSK/cert/phash/community) are placeholders + a manual-not-converted item.
- [ ] HA emitted as commented skeleton + manual item, never live.
- [ ] Each lossy section carries its inline `# CAVEAT:` and the matching fidelity classification.

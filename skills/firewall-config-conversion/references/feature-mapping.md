# Cross-Vendor Feature Mapping & Non-Isomorphic Catalog

## Contents

- [Part 1 — Canonical application → target name](#part-1--canonical-application--target-name)
- [Part 2 — Per-section non-isomorphic catalog](#part-2--per-section-non-isomorphic-catalog)
- [Quick classification cheat-sheet](#quick-classification-cheat-sheet)

Canonical-to-target knowledge base for the `firewall-config-conversion` skill. The
emitters (`emit-srx.md`, `emit-palo.md`, `emit-fortinet.md`, `emit-cisco.md`) cite this
file to choose the right target idiom and to attach the correct `# CAVEAT:` and fidelity
classification (`converted` / `converted-with-caveats` / `manual-not-converted`).

Two parts:

1. **Canonical application → target name table** — given a canonical app resolved by the
   parser, what to emit for each target vendor.
2. **Per-section non-isomorphic catalog** — for each schema concept, what maps 1:1, what
   maps with loss, and what has no equivalent and must be done manually, across all four
   vendors.

The L7-vs-port-based split is the single most important fact in this file:

- **Juniper SRX** and **Palo Alto PAN-OS** carry application identity natively — SRX via
  predefined `junos-*` applications (and AppID), PAN-OS via App-ID. Application identity
  survives a round trip between these two.
- **FortiGate** policies match on **predefined/custom service objects** (port/protocol),
  not App-ID; its application awareness lives in a separate Application Control sensor, not
  in the base policy match.
- **Cisco ASA/FTD (classic ASA)** is **purely port/protocol-based** — no App-ID at all.

So when converting **from** SRX/Palo **to** FortiGate or Cisco, application identity is
**approximated** by decomposing each app into its well-known port(s); emit a
`# CAVEAT: L7 app <x> approximated as port <n>` and classify `converted-with-caveats`.
When converting **to** SRX/Palo from a port-based source, the reverse mapping is best-effort
(a port can imply more than one app); flag low-confidence matches for manual review.

---

## Part 1 — Canonical application → target name

The parser resolves every source application to a **canonical** key (see the
"Cross-Vendor Application Name Mapping" and JunOS-predefined-app tables in
`parsing-srx-configs/SKILL.md` and `parsing-srx-configs/references/intermediate-schema.md`).
This table is the **reverse** direction: canonical → what to emit per target.

| Canonical | Port/Proto | SRX (`junos-*`) | Palo (App-ID / `service-*`) | FortiGate (predefined service) | Cisco ASA (port-based service) |
|-----------|-----------|-----------------|------------------------------|--------------------------------|--------------------------------|
| `https` | TCP/443 | `junos-https` | `ssl` (App-ID) / `service-https` | `HTTPS` | `tcp/443` |
| `http` | TCP/80 | `junos-http` | `web-browsing` / `service-http` | `HTTP` | `tcp/80` |
| `ssh` | TCP/22 | `junos-ssh` | `ssh` | `SSH` | `tcp/22` |
| `telnet` | TCP/23 | `junos-telnet` | `telnet` | `TELNET` | `tcp/23` |
| `ftp` | TCP/21 | `junos-ftp` | `ftp` | `FTP` | `tcp/21` |
| `tftp` | UDP/69 | `junos-tftp` | `tftp` | `TFTP` | `udp/69` |
| `dns` | UDP/53 (+TCP/53) | `junos-dns-udp` / `junos-dns-tcp` | `dns` | `DNS` | `udp/53` (+`tcp/53`) |
| `ntp` | UDP/123 | `junos-ntp` | `ntp` | `NTP` | `udp/123` |
| `snmp` | UDP/161 | *custom app* (no predefined) | `snmp` | `SNMP` | `udp/161` |
| `snmp-trap` | UDP/162 | *custom app* (no predefined) | `snmp-trap` | `SNMP` (trap) | `udp/162` |
| `smtp` | TCP/25 | `junos-smtp` | `smtp` | `SMTP` | `tcp/25` |
| `smtps` | TCP/465 | `junos-smtps` | `smtp` (ssl) | `SMTPS` | `tcp/465` |
| `imap` | TCP/143 | `junos-imap` | `imap` | `IMAP` | `tcp/143` |
| `imaps` | TCP/993 | `junos-imaps` | `imap` (ssl) | `IMAPS` | `tcp/993` |
| `pop3` | TCP/110 | `junos-pop3` | `pop3` | `POP3` | `tcp/110` |
| `ldap` | TCP/389 | `junos-ldap` | `ldap` | `LDAP` | `tcp/389` |
| `bgp` | TCP/179 | `junos-bgp` | `bgp` | `BGP` | `tcp/179` |
| `ospf` | IP/89 | `junos-ospf` | `ospf` | `OSPF` | `89` (IP proto) |
| `sip` | UDP/5060 | `junos-sip` | `sip` | `SIP` | `udp/5060` |
| `h323` | TCP/1720 | `junos-h323` | `h.323` | `H323` | `tcp/1720` |
| `msrpc` | TCP/135 | `junos-ms-rpc` | `msrpc` | `MS-RPC` | `tcp/135` |
| `mssql` | TCP/1433 | `junos-ms-sql` | `mssql-db` | `MS-SQL` | `tcp/1433` |
| `mysql` | TCP/3306 | *custom app* (no predefined) | `mysql` | `MYSQL` | `tcp/3306` |
| `smb` | TCP/445 | `junos-smb` | `ms-ds-smb` | `SMB` | `tcp/445` |
| `rdp` | TCP/3389 | `junos-rdp` | `ms-rdp` | `RDP` | `tcp/3389` |
| `ipsec` (IKE) | UDP/500 | `junos-ike` | `ike` | `IKE` | `udp/500` |
| `ipsec-nat-t` | UDP/4500 | `junos-ike-nat` | `ipsec-esp-udp` | `IKE` (nat-t) | `udp/4500` |
| `esp` | IP/50 | *custom app* (protocol 50; no predefined) | `ipsec-esp` | `ESP` | `50` (IP proto) |
| `ah` | IP/51 | *custom app* (protocol 51; no predefined) | `ipsec-ah` | `AH` | `51` (IP proto) |
| `pptp` | TCP/1723 | `junos-pptp` | `pptp` | `PPTP` | `tcp/1723` |
| `ping` | ICMP echo | `junos-icmp-ping` (echo-only; `junos-ping` matches all of proto 1) | `ping` | `PING` | `icmp` (echo) |
| `icmp-all` | ICMP (all types) | `junos-icmp-all` | `icmp` | `ALL_ICMP` | `icmp` |
| `ping6` | ICMPv6 echo | `junos-pingv6` | `ping6` | `PING6` | `icmp6` |
| `icmpv6-all` | ICMPv6 (all types) | `junos-icmp6-all` | `ipv6-icmp` | `ALL_ICMP6` | `icmp6` |
| `nntp` | TCP/119 | `junos-nntp` | `nntp` | `NNTP` | `tcp/119` |
| `syslog` | UDP/514 | `junos-syslog` | `syslog` | `SYSLOG` | `udp/514` |

Notes:

- **Cisco column is always a port/protocol service** (`tcp/N`, `udp/N`, `icmp`, IP proto
  number). There is no App-ID; emit the port match and a `# CAVEAT: L7 identity lost`.
- **FortiGate** uses predefined **service-object names** (case-sensitive in the GUI list).
  Base-policy matching is still port-based; true app awareness requires an Application
  Control sensor that this conversion does not synthesize — note `manual-not-converted`
  for app-control intent.
- **Palo** prefers the **App-ID** token (`ssl`, `web-browsing`, `ms-rdp`, …) when the source
  carried real L7 intent; fall back to `service-*` when only a port was known. App-ID names
  drift between PAN-OS content versions — flag any uncertain token for review.
- **SRX** predefined `junos-*` names are stable; custom apps are emitted as
  `applications application <name>` with explicit protocol/port.
- Unresolved apps (parser `confidence: 0.0`) cannot be mapped — emit as residual with a
  warning, never guess a target name.

---

## Part 2 — Per-section non-isomorphic catalog

Legend: **1:1** = clean structural map; **loss** = emit closest form + `# CAVEAT:`,
classify `converted-with-caveats`; **manual** = no target equivalent,
`manual-not-converted`, list as a manual follow-up item.

### zones

| Vendor | Model | Mapping |
|--------|-------|---------|
| SRX | Native `security-zone`, interfaces bound per zone | 1:1 with Palo |
| Palo | Native `zone` (L3/L2/vwire), interfaces as members | 1:1 with SRX |
| FortiGate | Optional `config system zone` over interfaces; policy often matches **interfaces** (`port1`) directly, not a named zone | loss — when source zones don't exist, synthesize a zone per source zone or map zone→member interfaces; intrazone allow/deny has no SRX/Palo analog |
| Cisco ASA | No zone object — `nameif` name + `security-level` (0–100) on each interface; implicit high→low permit | loss — derive zones from `nameif`; the security-level trust ordering is **not** representable on SRX/Palo/Forti and must become explicit policy. `# CAVEAT: security-level semantics replaced by explicit policy` |

Cross-vendor: SRX↔Palo zones are isomorphic. To FortiGate, prefer emitting a
`config system zone` so policies stay zone-shaped. To/from ASA, zones are an
**approximation** of `nameif`+`security-level`; the implicit same-or-higher-level permit
must be made explicit.

### nat_rules

| Vendor | Source NAT | Dest NAT | Static NAT |
|--------|-----------|----------|-----------|
| SRX | `security nat source rule-set` + pool / `interface` | `security nat destination rule-set` + pool | `security nat static rule-set` |
| Palo | NAT rule `source-translation` (dynamic-ip-and-port / dynamic-ip / static-ip) | NAT rule `destination-translation` | bidirectional static-ip |
| FortiGate | policy `set nat enable` + **IP Pool**; central SNAT optional | **VIP** object (`config firewall vip`) referenced as dstaddr | VIP with no port-forward = static |
| Cisco ASA | `nat (in,out) dynamic` / PAT (`interface`) | `nat (in,out) static` with service | twice-NAT / `nat static` |

Mapping: the three NAT intents (source/dest/static) exist on all four, so the **intent**
maps, but the **rule container differs sharply** — FortiGate folds dest-NAT into a VIP
object referenced from the policy, while SRX/Palo/ASA keep NAT in dedicated rule-sets. This
is **loss**: preserve rule order, re-anchor to the target's container, and
`# CAVEAT:` on pool/VIP restructuring. Hide/proxy-ARP and bidirectional flags rarely
survive cleanly — flag for review.

### security profile attachments (UTM / threat)

Not a standalone top-level schema section. UTM / threat intent lives in the schema as
**per-policy attachments** (`security_policies[].security_profiles`) referencing reusable
**`security_profile_objects`** (the top-level object pool). Convert it as a policy
attachment, not as its own section; never emit/report a top-level `security_profiles`
section.

| Vendor | Construct (attachment point) |
|--------|-----------|
| SRX | `then permit application-services` → utm-policy / IDP / SecIntel / AppFW |
| Palo | `security-profile-group` (AV, AS, vuln, URL, WildFire, file-blocking) attached to rule |
| FortiGate | per-policy **UTM profiles**: `av-profile`, `webfilter-profile`, `ips-sensor`, `application-list`, `ssl-ssh-profile` |
| Cisco ASA | **none** (classic ASA has no NGFW UTM; FTD differs and is out of scope) |

Mapping: profile **attachment points** are conceptually similar on SRX/Palo/FortiGate but
the **profile contents are vendor-proprietary** (signature sets, categories, actions do not
translate). Emit the attachment shape (from `security_policies[].security_profiles`, resolving
`security_profile_objects` for contents) and `# CAVEAT: profile contents must be rebuilt on
target`, classify `converted-with-caveats`. To **Cisco ASA → manual-not-converted**: there
is no equivalent; record every dropped profile attachment as a manual item.

### vpn_tunnels (IKE / IPsec)

| Vendor | Construct |
|--------|-----------|
| SRX | `security ike` (proposal/policy/gateway) + `security ipsec` (proposal/policy/vpn), st0 tunnel iface |
| Palo | `network ike crypto-profiles` + `ike gateway` + `ipsec-crypto-profiles` + `ipsec tunnel` |
| FortiGate | `config vpn ipsec phase1-interface` / `phase2-interface` |
| Cisco ASA | `crypto ikev2 policy` + `crypto ipsec ikev2 ipsec-proposal` + `tunnel-group` + `crypto map` |

Mapping: crypto **parameters** (IKE version, DH group, enc/auth, lifetimes, PFS) map across
all four, but **structure and tunnel-interface model differ** (route-based st0/tunnel-iface
vs policy-based crypto map). Always **loss + manual**:

- **Secrets are never emitted.** Replace every `pre-shared-key` / certificate with a
  placeholder and add a manual item: *re-key all VPN PSKs on the target*.
- Peer/proxy-id/traffic-selector models differ — re-validate after emit.
- Classify `converted-with-caveats` for crypto, `manual-not-converted` for the PSK/cert.

### interfaces (naming)

| Vendor | Convention | Examples |
|--------|-----------|----------|
| SRX | `<media>-<fpc>/<pic>/<port>` + unit | `ge-0/0/0.0`, `xe-0/1/1`, `st0.0`, `reth0` |
| Palo | `ethernet<slot>/<port>`, subifs `.N`, aggregate `aeN`, tunnel `tunnel.N` | `ethernet1/1`, `ethernet1/1.100`, `ae1` |
| FortiGate | role-named ports | `port1`, `port2`, `wan1`, `internal`, vlan `<parent>.<id>` |
| Cisco ASA | `<Type>Slot/Port` + logical `nameif` | `GigabitEthernet0/0`, `Management0/0` |

Mapping: physical interface names are **platform-bound and never portable** — always
**loss**. Emit a best-effort positional remap (1st data port → `ge-0/0/0` /
`ethernet1/1` / `port1` / `GigabitEthernet0/0`) and
`# CAVEAT: verify interface name/binding against target hardware`. VLAN/subinterface and
aggregate (reth/ae/port-channel) idioms differ and need review. IP addressing/zoning
carries over; the **name** does not.

### routing-instances / VRF vs vsys / contexts

| Vendor | Multi-context / VRF |
|--------|---------------------|
| SRX | `routing-instances` (VRF) + `logical-systems` / `tenants` (full virtual FW) |
| Palo | `virtual-router` (routing separation) + `vsys` (virtual system) |
| FortiGate | `vdom` (virtual domain = independent FW) + per-VDOM VRF |
| Cisco ASA | security `context` (multi-context mode) + limited VRF |

Mapping: routing-table separation (`routing-instance` / `virtual-router` / VRF / context)
maps **with loss** — the boundaries differ (SRX routing-instance ≠ Palo virtual-router
exactly; vsys ≠ logical-system exactly). Full virtual-firewall constructs
(`logical-systems`/`tenants` ↔ `vsys` ↔ `vdom` ↔ `context`) are conceptually parallel but
**route/zone/policy scoping rules differ**; emit the closest container and
`# CAVEAT: re-scope per-context routing/zones`. Where the source uses a construct the target
lacks cleanly, prefer flattening to the default instance and flag `manual-not-converted`.

### static_routes / virtual_routers / OSPF / BGP

Routing **protocol parameters** (static next-hops, OSPF area/cost, BGP AS/neighbor/policy)
map across all four, but live under different hierarchies (`protocols ospf` /
`network virtual-router` / `config router ospf` / `router ospf`). **Loss**: re-anchor to the
target hierarchy, preserve route order, `# CAVEAT:` on route-map/policy-statement/prefix-list
idiom differences (these rarely translate verbatim).

### screens / threat-protection

| Vendor | Construct | Notes |
|--------|-----------|-------|
| SRX | `security screen ids-option` (syn-flood, ICMP/UDP flood, IP spoof, scans), bound per zone | richest model |
| Palo | `zone-protection-profile` (flood, recon, packet-based) attached to zone | close to SRX |
| FortiGate | `config firewall DoS-policy` (anomaly thresholds) + IPS | per-policy, not per-zone |
| Cisco ASA | **limited** — `threat-detection basic-threat` / `threat-detection rate`, some connection limits | no full screen model |

Mapping: SRX screen ↔ Palo zone-protection is a reasonable **loss** map (thresholds and
option names differ). To FortiGate DoS-policy is **loss** and shape-changing (zone→policy).
To Cisco ASA is largely **manual-not-converted** — only coarse threat-detection/connection
limits exist; list dropped screen options as manual items.

### schedules

| Vendor | Construct |
|--------|-----------|
| SRX | `schedulers scheduler <name>` (referenced by policy `scheduler-name`) |
| Palo | `<schedule>` object referenced by rule |
| FortiGate | `config firewall schedule recurring`/`onetime`/`group`; `"always"` = no restriction |
| Cisco ASA | `time-range <name>` referenced by ACL |

Mapping: time-based activation exists on all four → **1:1 intent** with minor **loss** on
recurrence syntax (day/time-range encodings differ). Emit the equivalent schedule object and
reference; `# CAVEAT:` only if recurrence semantics can't be expressed exactly. FortiGate
`always` maps to "no schedule" on the others.

### management-plane access (NOT `security_services`)

Two distinct schema fields carry management-plane exposure — neither is `security_services`:

- **`zones[].host_inbound`** — per-zone allowed host-inbound management services (SRX
  `host-inbound-traffic system-services`/`protocols`; the analog of Palo
  interface-mgmt-profile, FortiGate `set allowaccess`, ASA `http`/`ssh`/`telnet`/`icmp`
  permit lines). This expresses **which management services an interface/zone accepts**.
- **`system.mgmt_services`** — device/system-level management services (dedicated mgmt
  interface, system-wide service enable).

**Loss**: the container differs (zone host-inbound vs interface-mgmt-profile vs
`allowaccess` vs management permit lines). Emit the closest form and
`# CAVEAT: verify management-plane exposure on target`. Never emit management secrets/keys —
placeholder and flag manual.

### security_services (device-wide security-service presence)

Separate concern from management access. `security_services` is a **device-wide presence
flag set** for the NGFW security services in use — `app_id`, `idp`, `secintel`, `aamw`,
`utm`. It does **not** carry management access and does not by itself convert to config; use
it to drive **caveats** about which security services the source relied on and must be
rebuilt on the target. The per-policy attachments (see *security profile attachments*) are
where the actual UTM/threat config is emitted.

---

## Quick classification cheat-sheet

- **1:1 (clean):** address/service objects & groups, schedules (intent), basic
  static routes, SRX↔Palo zones.
- **converted-with-caveats (loss):** zones to/from FortiGate & ASA, all nat_rules,
  security-profile attachments on SRX/Palo/Forti, vpn crypto params, interfaces (naming),
  routing-instances/VRF, OSPF/BGP, screens to Palo/Forti, management-plane access
  (`zones[].host_inbound` / `system.mgmt_services`).
- **manual-not-converted:** security-profile attachments → Cisco ASA, screens → Cisco ASA,
  VPN pre-shared-keys/certs (all targets — secrets never emitted), App-Control intent on
  FortiGate, any unresolved (confidence 0.0) application.

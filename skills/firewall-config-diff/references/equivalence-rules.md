# Equivalence Rules — Semantic Identity & Cross-Vendor Not-Comparable Catalog

## Contents

- [Part 1 — Per-section semantic identity & attribute comparison](#part-1--per-section-semantic-identity--attribute-comparison)
- [Part 2 — Cross-vendor not-comparable catalog](#part-2--cross-vendor-not-comparable-catalog)

The detail behind the `firewall-config-diff` workflow's pairing and classification steps.
It answers two questions for every comparison:

1. **Per-section semantic identity & attribute comparison** — for each intermediate-schema
   section, (a) the **identity key** items pair on across sides A and B, and (b) the
   **change-attributes** whose difference turns a matched pair from `unchanged` into
   `changed`. Items unmatched in A only are `removed`; unmatched in B only are `added`.
2. **Cross-vendor not-comparable catalog** — how constructs two vendors model differently are
   normalized to a common form *before* pairing (so they don't surface as false diffs), and
   which features have **no cross-vendor equivalent** and are flagged `not-comparable`
   instead of compared.

This file is **self-contained**: all cross-vendor facts needed to diff are stated here. It
overlaps the conversion skill's feature-mapping knowledge by design; that skill emits a target
config, this one only compares meaning. Refer to vendors by name (SRX/Junos, Palo Alto PAN-OS,
FortiGate/FortiOS, Cisco ASA/FTD) — do not path-reference another skill.

General rules that apply to every section:

- **Pair by meaning, never by position.** A rename, a reorder, or a different vendor's syntax
  is not a difference. Identity is value/tuple-based by default; a stable name is a valid
  anchor only for same-vendor drift (next bullet).
- **Same-vendor drift exception (name-anchoring).** When A and B are the SAME vendor and the
  object/policy NAMES are stable, you MAY anchor pairs by name and report the value/attribute
  delta as `changed` (applies to address objects, service objects, address/service groups,
  AND security policies). The "pair strictly by value, names differ → a value change is
  removed + added" rule is the CROSS-vendor default. Identity is never anchored by name
  *alone*, but a stable name is a legitimate anchor for same-vendor drift.
- **Addresses compare by value, not object name.** `web-srv = 10.0.1.10/32` on A equals an
  object named `host-A` with value `10.0.1.10/32` on B (cross-vendor); for same-vendor drift a
  same-named object whose value shifts is reported `changed`, not removed + added.
- **Groups compare by their fully expanded member set** (recursively flatten nested groups),
  order-insensitive.
- **Internal fields (`_rule_index`, `_implicit`, `_vsys`, `_vdom`, `added_by_fpic`, …) are
  metadata, not change-attributes.** Rule *order* is reported separately because it affects
  shadowing; it is never an add/remove.
- **Secrets (`psk`, certs, passwords, ssh_keys) are never printed in the diff.** Compare a
  presence/changed flag only ("psk changed"), never the value.

---

## Part 1 — Per-section semantic identity & attribute comparison

### address_objects
- **Identity:** the normalized `value` (e.g. `10.0.1.10/32`, `10.0.0.0/24`,
  `10.0.1.1-10.0.1.254`, an `fqdn` string, a wildcard, or a `geo` country code). Not `name`.
- **Change-attrs:** `type` (host/subnet/range/fqdn/wildcard/geo) when the value normalizes
  the same but the declared type differs; `ip_version`. `description`/`tags` are cosmetic —
  note as `changed` only if the report is configured to include metadata, otherwise ignore.
- **CROSS-vendor:** same value on both sides → `unchanged`; value only in A → `removed`; only in B → `added`. (Names differ across vendors, so value is the only stable identity anchor.)
- **SAME-vendor (drift):** when object names are stable, anchor pairs by name; a value change on a same-named object is reported `changed` (not removed + added).

### address_groups
- **Identity:** the **expanded member set** (each member resolved to its address value and
  the set flattened/de-duplicated). Two groups with different names but the same effective
  set of addresses are the same group.
- **Change-attrs:** any difference in the expanded set is the identity change itself — but
  if you choose to pair by name, a differing member set makes the pair `changed`. Prefer
  set-identity: a fully different set = `added`/`removed`, a same-name group with one member
  added/removed = `changed` (member delta listed).

### service_objects
- **Identity:** `protocol` + `port_range` (+ `source_port` when present). E.g. `tcp/443`,
  `udp/53`, `tcp/8443`. Not `name` — `custom-https tcp/8443` on A equals `web-alt tcp/8443`
  on B.
- **Change-attrs:** `protocol`, `port_range`, `source_port`. `description` cosmetic.
- **SAME-vendor (drift):** when the service name is stable, anchor by name and report a
  protocol/port change as `changed` (not removed + added).

### service_groups
- **Identity:** the **expanded member set** of (protocol+port) services, flattened and
  de-duplicated, order-insensitive.
- **Change-attrs:** member-set delta → `changed`.

### applications (resolved L7 apps)
- **Identity:** the **canonical** app key (`https`, `ssh`, `ms-teams`, …), not the
  vendor_name. `junos-https`, Palo `ssl`, FortiGate `HTTPS`, Cisco `tcp/443` all normalize to
  canonical `https` and compare **equal** (see Part 2).
- **Change-attrs:** `category`; a drop in `confidence` is worth noting but not a diff by
  itself. An app present only on one side (no canonical equivalent on the other vendor) is
  `not-comparable`, not `removed` (see Part 2).

### application_groups
- **Identity:** the expanded set of **canonical** app keys (members are already canonical in
  the schema). Order-insensitive.
- **Change-attrs:** member-set delta → `changed`.

### security_policies
- **Identity:** the match-and-action **tuple**
  `(src_zones, dst_zones, src_addresses, dst_addresses, applications/apps + services, action)`
  — addresses compared by **value**, apps by **canonical** key, zones normalized per Part 2.
  Honor `negate_source`/`negate_destination`. Not `name` and not `_rule_index`.
- **Change-attrs** (same tuple, ≥1 differs → `changed`): `log_start`, `log_end` (logging
  on/off), `security_profiles` (the AV/URL/IDP/etc. map) and `profile_group`, `description`,
  `schedule`, `disabled` (enabled vs disabled), `tags`, `source_users`, `url_categories`.
- **Order** is reported separately (a reorder changes shadowing) and is **not** an
  add/remove. `_implicit` default-deny rules are matched implicit-to-implicit.
- **SAME-vendor (drift):** when the policy name is stable, anchor by name and report
  attribute deltas as `changed`. If a referenced object's value shifts (e.g. a destination
  address object is re-pointed), the policy stays paired by name and the effective-value shift
  is noted on the `changed` pair — not reported as removed + added.

### nat_rules
- **Identity:** the **match + translation** —
  `(type, src_zones, dst_zones, src_addresses, dst_addresses)` matched by value, combined with
  the translation result (`translated_src` {type, addresses}, `translated_dst`,
  `translated_port`). Not `name`.
- **Change-attrs:** any difference in `translated_src`/`translated_dst`/`translated_port`
  (e.g. interface-PAT vs a dynamic-ip-pool, or a different pool), or in the matched zones/
  addresses while the rest holds. Type change (source vs static) is an identity change →
  `added`/`removed` pair.

### interfaces
- **Identity:** the interface **name** plus its primary **address** (`ip`/`ipv6`); for a
  sub-interface use `is_subif` / `parent_interface` to relate it to its parent (there is no
  separate `unit` field — the unit is part of `name`). For cross-vendor pairing where physical
  names are not portable, pair by address/role (see Part 2 — interface naming is
  `not-comparable` by name).
- **Change-attrs:** `ip`, `ipv6`, `zone` binding, `type`, `is_subif`, `parent_interface`,
  `vlan`, `mtu`, `status`, `speed`, `is_mgmt`, `dhcp_client`, `dhcp_relay`, LAG membership
  (`lag_parent`/`lag_members`).

### static_routes
- **Identity:** `destination` prefix + `next_hop` (+ `vrf` when present). Not `name`.
- **Change-attrs:** `metric`, `next_hop_type`, `interface`, `vrf`.

### OSPF routing (ospf_config / ospf3_config)
- **Identity:** `router_id` for the instance; within it, each **area** by its `id`, and each
  area interface by `name`. Redistribute entries by `source`.
- **Change-attrs:** area `type` (normal/stub/nssa), `no_summary`, `default_cost`,
  `authentication`; per-interface `passive`, `enabled`, `metric`, `priority`,
  `hello_interval`, `dead_interval`, `link_type`; `reference_bandwidth`; redistribute
  `metric`/`metric_type`.

### BGP routing (bgp_config)
- **Identity:** `local_as` + `router_id` for the instance; each **neighbor** by its
  `address` (+ `remote_as`). Networks by prefix.
- **Change-attrs:** `keepalive`, `holdtime`, and per-neighbor `remote_as`, `update_source`,
  `next_hop_self`, `soft_reconfiguration`, `route_reflector_client`, `enabled`, presence of a
  `password` (compare presence, never the value); `networks` set; redistribute entries.

### virtual_routers / routing_contexts
- **Identity:** the `name` of the virtual-router / routing-instance / VRF / context.
- **Change-attrs:** the bound `interfaces` set. Cross-vendor, the container model itself
  (VRF vs vsys vs vdom vs context) is `not-comparable` — see Part 2.

### system
- **Identity:** singleton (one `system` block per side) — pair the blocks directly.
- **Change-attrs:** `hostname`, `domain_name`, `dns_servers`, `ntp_servers`, `dhcp_relay`,
  `mgmt_services` (ssh/https/http/telnet/netconf/snmp on-off), `ssh` (`root_login`,
  `rate_limit`, `ciphers`, `protocol_version`, `connection_limit`), `auth`
  (`password_policy`, `login_lockout`, `root_authentication_present`),
  `control_plane_protection.re_filter_present`. Each differing field is a listed `changed`
  attribute.

### admin_users
- **Identity:** `name`.
- **Change-attrs:** `role`, `privilege_level`, and **presence/fingerprint** of `ssh_keys`
  (compare whether keys exist and how many / a hash — never print the key material).

### dhcp_config
- **Identity:** the `interface` (or served `network`).
- **Change-attrs:** `network`, `pools` (start/end ranges), `gateway`, `dns_servers`,
  `domain`, `lease_time`, `reservations`.

### ha_config
- **Identity:** singleton — pair the two HA blocks; for HA-pair consistency checks both sides
  *should* describe the same cluster.
- **Change-attrs:** `enabled`, `mode` (active-passive/active-active), `group_id`, `priority`,
  `preempt`, `peer_ip`, the `ha_interfaces` set (name/role/ip), and `monitoring`
  (`interfaces`, `failure_threshold`).

### screen_config (screens / DoS protection)
- **Identity:** the screen `name` and/or the bound `zone`.
- **Change-attrs:** the nested option maps — `icmp` (ping-death, flood), `tcp` (syn-flood
  alarm/attack thresholds, land), `udp` (flood), `ip` (spoofing, source-route-option),
  `limit_session`. A differing threshold or toggled option → `changed`. Many of these options
  are vendor-only — see Part 2.

### schedules
- **Identity:** the time definition — `type` (recurring/onetime) plus `days` + `start` +
  `end` (the actual time window), not just `name`.
- **Change-attrs:** `days`, `start`, `end`, `type`. A FortiGate `always` schedule normalizes
  to "no schedule restriction."

### security_services
- **Identity:** singleton — pair the two presence-flag blocks.
- **Change-attrs:** each flag — `app_id`, `idp`, `secintel`, `aamw`, `utm` — that differs
  on/off is a listed change. Note: these are device-level presence flags; the per-policy
  attachment lives in `security_policies[].security_profiles`.

### vpn_tunnels
- **Identity:** the tunnel by `(ike.local_address, ike.remote_address)` peer pair (+
  `tunnel_interface` when needed). Not `name`.
- **Change-attrs:** `ike.version`, `auth_method`, IKE proposal (`encryption`, `integrity`,
  `dh_group`, `lifetime`); `ipsec` proposal + `mode`; `tunnel_ip`, `vr`, `routes`. Compare
  **psk/cert presence and whether it changed**, never the secret value. Crypto-strength
  *details* that one vendor expresses and another cannot are `not-comparable` — see Part 2.

---

## Part 2 — Cross-vendor not-comparable catalog

Before pairing two **different-vendor** sides, normalize the constructs the vendors model
differently to a common form. Where a feature exists on one vendor and has **no equivalent**
on the other, flag it `not-comparable` and exclude it from add/removed/changed — never let a
non-isomorphic feature become a false diff.

### Canonical-app normalization (these compare EQUAL)

Resolve every application to its **canonical** key, then compare canonical-to-canonical. The
following all normalize to the same key and are `unchanged` across vendors:

| Canonical | Junos SRX | Palo Alto PAN-OS | FortiGate | Cisco ASA/FTD |
|-----------|-----------|------------------|-----------|---------------|
| `https` | `junos-https` | `ssl` | `HTTPS` | `tcp/443` |
| `http`  | `junos-http`  | `web-browsing` | `HTTP`  | `tcp/80`  |
| `ssh`   | `junos-ssh`   | `ssh`          | `SSH`   | `tcp/22`  |
| `dns`   | `junos-dns-udp` | `dns`        | `DNS`   | `udp/53`  |
| `rdp`   | `junos-rdp`   | `ms-rdp`       | `RDP`   | `tcp/3389` |

So `junos-https` (SRX) == `ssl` (Palo) == `HTTPS` (FortiGate) == `tcp/443` (Cisco) — they are
**not** a diff. A port-based side (FortiGate base policy, Cisco ASA) carries the canonical app
only as a well-known port; treat the canonical match as equal but note confidence in the
report when a port maps to more than one app. An application that resolves on one side but has
**no canonical equivalent** on the other vendor's platform (e.g. a Palo App-ID like `ms-teams`
with no ASA representation) is `not-comparable`, not `removed`.

### Threat / UTM profiles — no portable equivalent
The *attachment point* is loosely parallel but the **profile contents are vendor-proprietary**
and do not compare:
- **SRX** `permit application-services` → utm-policy / IDP / SecIntel / AppFW.
- **Palo** `security-profile-group` (AV, anti-spyware, vulnerability, URL, WildFire,
  file-blocking).
- **FortiGate** per-policy **UTM** profiles (`av-profile`, `webfilter-profile`, `ips-sensor`,
  `application-list`, `ssl-ssh-profile`).
- **Cisco ASA** — **none** (classic ASA has no NGFW UTM; FTD differs, out of scope).

Compare only **whether a policy has threat inspection attached** (a coarse boolean) across
vendors. Signature sets, categories, and per-action contents are `not-comparable`. To/from
Cisco ASA, all profile content is `not-comparable` (there is nothing on the ASA side).

### IKE / IPsec crypto specifics — partial
Crypto **parameters** (IKE version, DH group, encryption, integrity, lifetimes, PFS) normalize
to the schema's canonical enc/integrity values and **can** be compared. But the **tunnel model
and proxy-id/traffic-selector semantics differ** (route-based st0/tunnel-interface on
SRX/Palo/FortiGate vs policy-based crypto-map on Cisco ASA), and **secrets are never compared
by value**. Flag the structural pieces — crypto-map vs route-based binding, proxy-id vs
traffic-selector scoping — as `not-comparable`; compare only the normalizable proposal fields.

### Zone models — structurally different
- **SRX / Palo** — named `security-zone` / `zone`, interfaces bound per zone. **Isomorphic**:
  zone names compare directly.
- **FortiGate** — zones optional; policies often match **interfaces** (`port1`) directly, or a
  `config system zone`. Normalize FortiGate interface-matched policies by synthesizing a
  pseudo-zone per interface before pairing.
- **Cisco ASA** — **no zone object**: each interface has a `nameif` name + `security-level`
  (0–100), with an implicit high→low permit. Derive pseudo-zones from `nameif`; the
  **security-level trust ordering and its implicit permit have no equivalent** on
  SRX/Palo/FortiGate and are `not-comparable` (do not diff them as missing policies).

### routing-instances / VRF vs vsys / contexts — not comparable as containers
Routing-table separation maps loosely but the **boundaries and scoping differ**, so the
container constructs do not pair cleanly across vendors:
- **SRX** — `routing-instances` (VRF) + `logical-systems` / `tenants` (full virtual FW).
- **Palo** — `virtual-router` (routing) + `vsys` (virtual system).
- **FortiGate** — `vdom` (independent virtual FW) + per-VDOM VRF.
- **Cisco ASA** — security `context` (multi-context) + limited VRF.

A SRX `routing-instance` ≠ a Palo `virtual-router` ≠ a `vdom` ≠ an ASA `context` exactly.
Compare **contents within a matched context** where the mapping is obvious; flag the
container model itself (and any logical-system/vsys/vdom/context that has no counterpart) as
`not-comparable`.

### Vendor-only screen / DoS options
Screen/DoS-protection models differ in richness, so options that exist on one vendor and not
the other are `not-comparable`:
- **SRX** `security screen ids-option` — the richest model (syn-flood, ICMP/UDP flood, IP
  spoofing, source-route, scans, session limits), bound per zone.
- **Palo** `zone-protection-profile` — close to SRX (flood, recon, packet-based), per zone.
- **FortiGate** `DoS-policy` — anomaly thresholds **per policy**, not per zone.
- **Cisco ASA** — only coarse `threat-detection` / connection limits; **no full screen
  model**.

Compare overlapping thresholds (e.g. syn-flood) where both sides express them; SRX-only
options against an ASA side, or a per-zone screen against a per-policy DoS-policy that has no
matching anchor, are `not-comparable` — never reported as a removed feature.

### Other inherently not-comparable items
- **Physical interface names** — `ge-0/0/0` vs `ethernet1/1` vs `port1` vs
  `GigabitEthernet0/0` are platform-bound; pair interfaces by address/role, treat the **name**
  as `not-comparable`.
- **Management-service containers** — SRX zone `host-inbound-traffic` vs Palo
  interface-mgmt-profile vs FortiGate `allowaccess` vs ASA `http`/`ssh` permit lines express
  the same intent in non-isomorphic containers; compare the *set of allowed services* per
  interface/zone, flag the container shape as `not-comparable`.
- **Unresolved applications** (`confidence: 0.0`) — cannot be normalized to canonical; list as
  `not-comparable`, never as a false add/remove.

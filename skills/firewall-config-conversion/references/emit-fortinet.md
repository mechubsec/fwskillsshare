# Emit Fortinet FortiOS Configuration

## Contents

- [address_objects](#address_objects)
- [address_groups](#address_groups)
- [service_objects (custom services)](#service_objects-custom-services)
- [service_groups (service groups)](#service_groups-service-groups)
- [zones](#zones)
- [security_policies](#security_policies)
- [nat_rules](#nat_rules)
- [interfaces](#interfaces)
- [static routes, OSPF, BGP](#static-routes-ospf-bgp)
- [system (global / dns / ntp), admin_users, DHCP](#system-global--dns--ntp-admin_users-dhcp)
- [ha_config](#ha_config)
- [vpn_tunnels (IKE / IPsec)](#vpn_tunnels-ike--ipsec)
- [screens (DoS policy)](#screens-dos-policy)
- [schedules](#schedules)
- [management-plane access (`zones[].host_inbound` / `system.mgmt_services`)](#management-plane-access-zoneshost_inbound--systemmgmt_services)
- [Emit checklist (FortiGate target)](#emit-checklist-fortigate-target)

Target-emitter reference for the `firewall-config-conversion` skill. Loaded when the
conversion **target = FortiGate (FortiOS)**. For every emittable section of the
intermediate schema this file shows the native FortiOS `config / edit / set / next / end`
syntax to render, the fidelity classification (`converted` /
`converted-with-caveats` / `manual-not-converted`), and the inline `# CAVEAT:` to emit
when the translation is lossy. Cross-vendor lossiness is sourced from
`references/feature-mapping.md`; FortiOS syntax discipline follows the
`parsing-fortinet-configs` skill's config-format reference (every `edit` needs a `next`,
every `config` an `end`, dotted-decimal subnet masks not CIDR).

> **CRITICAL FortiOS RULES**
>
> - **Block discipline.** Each object lives inside a `config <section>` … `end` block; each
>   entry is `edit <name|id>` … `next`. Never leave a block unterminated — every `edit` needs
>   a `next`, every `config` needs an `end`. Sub-blocks (e.g. an inline `config` under an
>   `edit`) nest and each gets its own `end`.
> - **Subnets are dotted-decimal masks, not CIDR.** `set subnet 10.0.0.0 255.255.0.0`, never
>   `/16`. Convert from the schema prefix length (see the mask table in
>   `parsing-fortinet-configs/references/config-format.md`).
> - **Interface-as-zone model.** FortiGate has no first-class named-zone object like SRX/Palo.
>   The zone unit is the **interface**; `config system zone` only *groups* interfaces. Policy
>   `srcintf`/`dstintf` therefore take **interface OR zone names** — see the zones and
>   security_policies sections and `feature-mapping.md` → zones.
> - **Secrets are NEVER emitted.** PSKs, certificates, passwords, SNMP communities render as
>   `"<PSK-PLACEHOLDER>"` / `"<KEY-PLACEHOLDER>"` / `"<PASSWORD-PLACEHOLDER>"` plus a
>   `manual-not-converted` item. Never emit an encrypted/ENC hash from the source config.
> - **IKEv2 has no `set mode`.** `set mode {main|aggressive}` is **IKEv1-only**; under a
>   `phase1-interface` with `set ike-version 2` it is rejected/hidden. Do **not** emit it.

---

## address_objects

**Classification: converted** (clean 1:1 — host / subnet / range / fqdn).

One `edit` per object inside `config firewall address`. Pick the `type` from the schema
object kind; render the mask in dotted-decimal.

```
config firewall address
    edit "HOST-WEB-01"
        set type ipmask
        set subnet 10.20.30.10 255.255.255.255
        set comment "Production web server"
    next
    edit "NET-USERS"
        set type ipmask
        set subnet 10.10.0.0 255.255.0.0
    next
    edit "RANGE-DHCP"
        set type iprange
        set start-ip 10.10.5.10
        set end-ip 10.10.5.50
    next
    edit "FQDN-UPDATE"
        set type fqdn
        set fqdn "updates.example.com"
    next
end
```

- A `/32` host is `set subnet <ip> 255.255.255.255`; a network is the dotted mask of its prefix.
- IPv6 objects use `config firewall address6` with `set ip6 2001:db8:dmz::/64` (CIDR is
  retained for v6).
- CAVEAT only when a source object was zone-scoped and is flattened to global namespace:
  `# CAVEAT: source zone-local address moved to global firewall address table; verify no name collision`.

## address_groups

**Classification: converted** (clean 1:1).

```
config firewall addrgrp
    edit "WEB-SERVERS"
        set member "HOST-WEB-01" "HOST-WEB-02"
    next
    edit "ALL-INTERNAL"
        set member "NET-USERS" "WEB-SERVERS"
    next
end
```

- `set member` takes space-separated quoted names; nested groups are just member names.
- IPv6 groups use `config firewall addrgrp6`.

## service_objects (custom services)

**Classification: converted** for predefined; **converted-with-caveats** for custom or
unresolved.

Map each canonical service to its **predefined** FortiGate service name via
`feature-mapping.md` Part 1 (`HTTP`, `HTTPS`, `SSH`, `DNS`, …). Predefined services need
**no** definition — reference them directly from policy. Emit `config firewall service
custom` only for non-predefined ports.

```
config firewall service custom
    edit "TCP-8443"
        set protocol TCP/UDP/SCTP
        set tcp-portrange 8443
        set comment "Custom HTTPS port"
    next
    edit "APP-PORTS"
        set protocol TCP/UDP/SCTP
        set tcp-portrange 8080-8090
        set udp-portrange 9000-9010
    next
    edit "ICMP-ECHO"
        set protocol ICMP
        set icmptype 8
        set icmpcode 0
    next
end
```

- `tcp-portrange`/`udp-portrange` accept `<port>`, `<lo>-<hi>`, or `<dst>:<src-range>`.
- A canonical service mapping to two predefined names (e.g. `dns` → DNS over TCP+UDP) is
  already covered by the single predefined `DNS` object; otherwise group them (below).
- CAVEAT for a parser-unresolved app (`confidence: 0.0`):
  `# CAVEAT: unresolved source application emitted as residual custom service — define manually, do not trust port guess` → **manual-not-converted** for that object.
- CAVEAT when an L7 app from SRX/Palo is decomposed to a port:
  `# CAVEAT: L7 app <x> approximated as port <n> — base policy is port-based; rebuild app awareness with an application-list` (per `feature-mapping.md`).

## service_groups (service groups)

**Classification: converted** (clean 1:1).

```
config firewall service group
    edit "SVC-WEB"
        set member "HTTP" "HTTPS" "TCP-8443"
    next
end
```

- Mix predefined and custom members freely; `set member` is space-separated quoted names.

## zones

**Classification: converted-with-caveats** (always lossy to/from FortiGate — interface-as-zone
model differs from SRX/Palo named zones; see `feature-mapping.md` → zones).

FortiGate's zone **unit is the interface**. To keep zone-shaped policy intent from an
SRX/Palo source, synthesize a `config system zone` that groups the source zone's member
interfaces, then have policies match the zone name in `srcintf`/`dstintf`. If a source
zone maps to a single interface, you may match the interface directly and skip the zone.

```
config system zone
    edit "TRUST"
        set interface "port1" "port3"
        set intrazone allow
    next
    edit "UNTRUST"
        set interface "port2"
        set intrazone deny
    next
end
```

- `intrazone allow|deny` governs traffic between members of the same zone — it has **no**
  SRX/Palo analog; default `deny` unless the source clearly allowed intra-zone.
- `srcintf`/`dstintf` in `config firewall policy` accept either a **zone** name (above) or a
  bare **interface** name (`port1`) — they share one namespace.
- CAVEAT (mandatory when source had named zones):
  `# CAVEAT: FortiGate has no named-zone object — source zones synthesized as system zones grouping interfaces; policy srcintf/dstintf reference zone OR interface names. Verify interface membership and intrazone intent`.
- CAVEAT when source is Cisco ASA (`nameif` + `security-level`):
  `# CAVEAT: ASA security-level high→low implicit permit not representable — zones derived from nameif; trust ordering must become explicit policy`.

## security_policies

**Classification: converted-with-caveats** (action/logging map cleanly; L7/profile intent is
lossy). **Preserve source rule order** — FortiGate evaluates `config firewall policy`
top-to-bottom by `edit <id>`; emit ascending IDs in source order.

Action / logging map:

| Schema | FortiOS `set` |
|--------|---------------|
| `action: allow` | `set action accept` |
| `action: deny` | `set action deny` (silent drop) |
| `action: drop` | `set action deny` (FortiGate `deny` already silently drops) |
| `action: reset-both` | `set action deny` + `# CAVEAT: source action reset-both — FortiGate base policy has no per-rule TCP reset; emitted as deny (silent drop), no RST sent` |
| `log_start: true` + `log_end` | `set logtraffic all` (logs session start+end) |
| `log_end only` | `set logtraffic all` (no UTM-only without UTM) |
| UTM logging only | `set logtraffic utm` |
| no logging | `set logtraffic disable` |
| `disabled: true` | `set status disable` (preserve, don't drop) |

```
config firewall policy
    edit 1
        set name "100-USERS-WEB"
        set srcintf "TRUST"
        set dstintf "UNTRUST"
        set srcaddr "NET-USERS"
        set dstaddr "all"
        set action accept
        set schedule "always"
        set service "HTTP" "HTTPS"
        set logtraffic all
        set utm-status enable
        set av-profile "default"
        set webfilter-profile "default"
        set ips-sensor "default"
        set ssl-ssh-profile "certificate-inspection"
    next
    edit 99
        set name "999-DENY-ALL"
        set srcintf "any"
        set dstintf "any"
        set srcaddr "all"
        set dstaddr "all"
        set action deny
        set schedule "always"
        set service "ALL"
        set logtraffic all
    next
end
```

- `srcintf`/`dstintf` reference zone OR interface names (see zones); `"any"` matches all.
- `srcaddr`/`dstaddr`/`service` take space-separated quoted object names; multiple values on
  one `set` line is the FortiOS idiom (unlike SRX one-leaf-per-line).
- A `deny` policy should still `set logtraffic all` to preserve audit intent.
- CAVEAT when reset-both collapses to deny:
  `# CAVEAT: source action 'reset-both' emitted as 'deny' — FortiGate base policy sends no per-rule TCP RST/ICMP unreachable`.

### security-profile attachments on a policy (UTM profiles)

**Classification: converted-with-caveats** — attachment shape converts; profile **contents**
are vendor-proprietary. Source from `security_policies[].security_profiles` /
`security_profile_objects` (`feature-mapping.md` → security profile attachments).

Set `set utm-status enable` and reference per-feature profiles by name. The profiles
themselves must be (re)built on the target — emit references only, not signature contents:

```
        set utm-status enable
        set av-profile "default"
        set webfilter-profile "default"
        set ips-sensor "default"
        set application-list "default"
        set ssl-ssh-profile "certificate-inspection"
```

- CAVEAT (mandatory): `# CAVEAT: UTM profile contents (AV/webfilter/IPS/app-control signatures, categories, actions) must be rebuilt on FortiGate — only the attachment is converted`.
- True App-ID intent from Palo/SRX maps to a FortiGate **application-list** (Application
  Control sensor), which this conversion does **not** synthesize → record
  **manual-not-converted** for app-control intent.
- If source is Cisco ASA (no UTM), nothing to attach → record as **manual-not-converted** in
  the report, not in config.

## nat_rules

**Classification: converted-with-caveats** (intent maps; container/pool/VIP restructured —
`feature-mapping.md` → nat_rules). **Preserve rule order.**

FortiGate uses **policy NAT**: source NAT is a flag (`set nat enable`) on the firewall
policy, optionally drawing from an **IP pool**; destination NAT is a **VIP** object
referenced as the policy `dstaddr`.

Source NAT (egress port-overload, or pool):

```
config firewall ippool
    edit "PNAT-EGRESS"
        set type overload
        set startip 203.0.113.10
        set endip 203.0.113.20
    next
end
config firewall policy
    edit 10
        set name "SNAT-USERS-OUT"
        set srcintf "TRUST"
        set dstintf "UNTRUST"
        set srcaddr "NET-USERS"
        set dstaddr "all"
        set action accept
        set schedule "always"
        set service "ALL"
        set nat enable
        set ippool enable
        set poolname "PNAT-EGRESS"
    next
end
```

- Omit `ippool`/`poolname` to NAT to the egress-interface IP (simple PAT) — just `set nat enable`.
- Pool `type`: `overload` (PAT), `one-to-one`, `fixed-port-range`.

Destination NAT / static NAT (VIP):

```
config firewall vip
    edit "VIP-WEB"
        set extip 203.0.113.50
        set mappedip "10.20.30.10"
        set extintf "port2"
        set portforward enable
        set protocol tcp
        set extport 443
        set mappedport 8443
    next
end
```

- Reference the VIP as a policy `dstaddr` on the inbound policy. A VIP **without**
  `portforward` is effectively 1:1 static NAT.
- CAVEAT (mandatory): `# CAVEAT: source NAT rule-set re-anchored to FortiGate policy NAT — dest-NAT folded into a firewall VIP, source pools into ippool; verify rule order, port-forward, and proxy-ARP`.
- CAVEAT: `# CAVEAT: VIP auto-creates proxy-ARP on extintf — confirm the external IP/interface binding matches the source intent`.

## interfaces

**Classification: converted-with-caveats** — physical names are platform-bound and never
portable (`feature-mapping.md` → interfaces). Carry IP addressing over; remap names
positionally (1st data port → `port1`, …) and CAVEAT it.

```
config system interface
    edit "port1"
        set vdom "root"
        set ip 10.10.0.1 255.255.255.0
        set type physical
        set alias "LAN"
        set allowaccess ping ssh https
    next
    edit "port2"
        set vdom "root"
        set ip 203.0.113.2 255.255.255.252
        set type physical
        set alias "WAN"
        set allowaccess ping
    next
    edit "port1.100"
        set vdom "root"
        set ip 10.10.100.1 255.255.255.0
        set vlanid 100
        set interface "port1"
        set type vlan
    next
end
```

- IPv4 `set ip <addr> <mask>` (dotted); IPv6 `set ip6 ...` under `config ipv6` sub-block.
- Sub-interfaces (`is_subif`) → `set type vlan`, `set vlanid <n>`, `set interface "<parent>"`,
  with the conventional `<parent>.<id>` edit name.
- Aggregate (`lag_*`) → `set type aggregate` + `set member "port3" "port4"`.
- `set allowaccess` carries the management services (see management-plane access).
- CAVEAT (always, first interface):
  `# CAVEAT: interface names remapped positionally — verify against target FortiGate port layout and bindings`.

## static routes, OSPF, BGP

**Classification: converted-with-caveats** — protocol params map; hierarchy differs and
route-map/prefix-list idioms rarely translate verbatim (`feature-mapping.md` →
static_routes/OSPF/BGP). **Preserve route order** (static routes are `edit <seq>`).

Static routes:

```
config router static
    edit 1
        set dst 0.0.0.0 0.0.0.0
        set gateway 203.0.113.1
        set device "port2"
    next
    edit 2
        set dst 10.50.0.0 255.255.0.0
        set gateway 10.10.0.254
        set device "port1"
    next
end
```

OSPF:

```
config router ospf
    set router-id 10.10.0.1
    config area
        edit 0.0.0.0
        next
    end
    config ospf-interface
        edit "to-core"
            set interface "port1"
            set cost 10
        next
    end
    config network
        edit 1
            set prefix 10.10.0.0 255.255.0.0
            set area 0.0.0.0
        next
    end
end
```

BGP:

```
config router bgp
    set as 65001
    set router-id 10.10.0.1
    config neighbor
        edit "203.0.113.1"
            set remote-as 65010
        next
    end
    config network
        edit 1
            set prefix 10.10.0.0 255.255.0.0
        next
    end
end
```

- CAVEAT: `# CAVEAT: route-maps/prefix-lists become FortiOS route-map/prefix-list objects — re-author import/export policy manually` (manual-not-converted for the policy bodies).
- CAVEAT (IPv6): emit `config router ospf6` / IPv6 BGP address-family separately.

## system (global / dns / ntp), admin_users, DHCP

**Classification: converted-with-caveats** — base system maps; passwords are placeholders.

System base from schema `system`:

```
config system global
    set hostname "fw-edge-01"
end
config system dns
    set primary 10.10.0.53
    set secondary 1.1.1.1
end
config system ntp
    set ntpsync enable
    config ntpserver
        edit 1
            set server "10.10.0.123"
        next
    end
end
```

admin_users (schema `admin_users` → `config system admin`) — **passwords never emitted**:

```
config system admin
    edit "admin1"
        set accprofile "super_admin"
        set password "<PASSWORD-PLACEHOLDER>"
    next
    edit "netops"
        set accprofile "prof_admin"
        set password "<PASSWORD-PLACEHOLDER>"
    next
end
```

- CAVEAT (mandatory): `# CAVEAT: admin password not converted — set credentials manually on FortiGate` → **manual-not-converted** for the secret.

DHCP (schema `dhcp_config` server) → `config system dhcp server`:

```
config system dhcp server
    edit 1
        set interface "port1"
        set default-gateway 10.10.0.1
        set netmask 255.255.255.0
        config ip-range
            edit 1
                set start-ip 10.10.0.100
                set end-ip 10.10.0.200
            next
        end
        set dns-server1 10.10.0.53
    next
end
```

- DHCP relay instead: `set dhcp-relay-service enable` + `set dhcp-relay-ip "10.10.0.53"` on
  the `config system interface` entry, not a dhcp server block.
- CAVEAT: `# CAVEAT: DHCP pool/option model differs — verify lease time, options, and reservations on FortiGate`.

## ha_config

**Classification: converted-with-caveats** (note only — heartbeat/monitor interfaces and
priorities are hardware-specific; verify on the real pair).

```
config system ha
    set mode a-p
    set group-id 1
    set group-name "fw-cluster"
    set priority 200
    set hbdev "port5" 50
    set monitor "port1" "port2"
    set override enable
end
```

- Modes: `standalone`, `a-p` (active-passive), `a-a` (active-active).
- CAVEAT (mandatory): `# CAVEAT: HA heartbeat/monitor interfaces and priorities are platform-specific — verify hbdev/monitor/session-pickup on the real FortiGate pair before enabling`.
- The HA cluster password (`set password`) is a secret → placeholder + manual item, never emit.

## vpn_tunnels (IKE / IPsec)

**Classification: converted-with-caveats** for crypto params; **manual-not-converted** for
PSK/certs — **secrets are never emitted** (`feature-mapping.md` → vpn_tunnels).

Emit route-based `phase1-interface` / `phase2-interface` with crypto params from the
schema and a **placeholder** PSK. **Do NOT emit the IKEv1 `set mode {main|aggressive}` leaf
under IKEv2** — that leaf is IKEv1-only and is rejected/hidden when `set ike-version 2`.

```
config vpn ipsec phase1-interface
    edit "VPN-SITEB"
        set interface "port2"
        set ike-version 2
        set peertype any
        set remote-gw 198.51.100.2
        set proposal aes256-sha256
        set dhgrp 14
        set psksecret "<PSK-PLACEHOLDER>"
    next
end
config vpn ipsec phase2-interface
    edit "VPN-SITEB-P2"
        set phase1name "VPN-SITEB"
        set proposal aes256gcm
        set pfs enable
        set dhgrp 14
        set keylifeseconds 3600
    next
end
```

- `set ike-version 1` would additionally allow the `set mode {main|aggressive}` leaf; for
  IKEv2 that leaf is **omitted entirely**.
- PRF tokens like `aes256gcm-prfsha256` are **phase1-interface** proposals only; the **phase2-interface** GCM proposal is the bare `aes256gcm` (no `-prf...` suffix). Under a `phase1-interface`, `aes256gcm-prfsha256` remains correct.
- A route-based tunnel makes the phase1-interface a virtual interface — add a `config router
  static` route over it and a firewall policy permitting the tunnel traffic.
- CAVEAT (mandatory): `# CAVEAT: PSK/certificate not converted — re-key the VPN manually on FortiGate before enabling` → **manual-not-converted** item.
- CAVEAT: `# CAVEAT: policy-based crypto-map / proxy-id model re-modeled as route-based phase1/phase2-interface — re-validate peer, selectors, and tunnel route`.

## screens (DoS policy)

**Classification: converted-with-caveats** (to/from Palo zone-protection / SRX screen);
**manual-not-converted** when source is Cisco ASA (no full screen model —
`feature-mapping.md` → screens).

FortiGate anomaly/flood protection is a **per-policy** `config firewall DoS-policy`, not a
per-zone binding — shape-changing from SRX/Palo:

```
config firewall DoS-policy
    edit 1
        set name "DOS-UNTRUST"
        set interface "port2"
        set srcaddr "all"
        set dstaddr "all"
        set service "ALL"
        config anomaly
            edit "tcp_syn_flood"
                set status enable
                set action block
                set threshold 1000
            next
            edit "icmp_flood"
                set status enable
                set action block
                set threshold 1000
            next
        end
    next
end
```

- CAVEAT (mandatory): `# CAVEAT: SRX screen / Palo zone-protection re-modeled as FortiGate per-interface DoS-policy — thresholds and anomaly names differ; review values against source intent`.

## schedules

**Classification: converted** (intent 1:1; minor recurrence-syntax loss).

```
config firewall schedule recurring
    edit "BIZ-HOURS"
        set start 08:00
        set end 18:00
        set day monday tuesday wednesday thursday friday
    next
end
config firewall schedule onetime
    edit "MAINT-WINDOW"
        set start 00:00 2026/07/01
        set end 06:00 2026/07/01
    next
end
```

- Reference from a policy with `set schedule "BIZ-HOURS"`.
- Source "no restriction" → use the built-in `"always"` schedule (don't define it).
- CAVEAT only when recurrence can't be expressed exactly:
  `# CAVEAT: source recurrence approximated — verify schedule day/time windows`.

## management-plane access (`zones[].host_inbound` / `system.mgmt_services`)

**Classification: converted-with-caveats** — container differs across vendors
(`feature-mapping.md` → management-plane access). Source these from the schema's
**`zones[].host_inbound`** (per-zone accepted management services) and
**`system.mgmt_services`** (device/system-level management) — **not** from
`security_services`, which is only a device-wide security-service presence flag set
(app_id/idp/secintel/aamw/utm) and carries no management access. On FortiGate the per-zone
services render as `set allowaccess` on `config system interface` (see interfaces).

```
config system interface
    edit "port1"
        set allowaccess ping ssh https
    next
    edit "port2"
        set allowaccess ping
    next
end
```

- Tokens: `ping ssh https http telnet snmp fgfm radius-acct probe-response fabric`.
- Avoid emitting `telnet`/`http` for management unless the source explicitly had them — flag
  plaintext management for review.
- CAVEAT: `# CAVEAT: management access re-anchored to per-interface allowaccess — verify management-plane exposure differs from source zone/interface-mgmt model`.
- Never emit management secrets/keys (SNMP community, admin password) — placeholder + manual item.

---

## Emit checklist (FortiGate target)

- [ ] Every `config` has a matching `end`; every `edit` a matching `next`; sub-blocks closed.
- [ ] Subnets emitted as dotted-decimal masks, not CIDR (v4); v6 uses `ip6`/`address6`.
- [ ] Security-policy order preserved via ascending `edit <id>` in source order; disabled rules emitted with `set status disable`, not dropped.
- [ ] `allow→accept`, `deny→deny`, `drop→deny`, `reset-both→deny`+CAVEAT (no per-rule RST), logging→`logtraffic all|utm|disable`; UTM profiles referenced (not their contents).
- [ ] NAT re-anchored: source→policy `set nat enable` (+ ippool), dest/static→`config firewall vip`; order preserved.
- [ ] Zones synthesized over interfaces; `srcintf`/`dstintf` reference zone OR interface names; interface-as-zone CAVEAT emitted.
- [ ] Predefined service names used where the canonical table allows; custom ports defined under `config firewall service custom`.
- [ ] VPN: route-based phase1/phase2-interface; **no IKEv1 `mode` leaf under IKEv2**; PSK is a placeholder + manual item.
- [ ] All secrets (PSK/cert/password/community) are placeholders + a manual-not-converted item — no encrypted/ENC hashes carried over.
- [ ] HA and DoS-policy emitted with their hardware/shape CAVEATs.
- [ ] Each lossy section carries its inline `# CAVEAT:` and the matching fidelity classification.

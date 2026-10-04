# Worked Example: Cisco ASA → Juniper SRX

## Contents

- [Conversion DRAFT](#conversion-draft)
- [Fidelity report (cisco_asa -> srx)](#fidelity-report-cisco_asa---srx)
- [Notes on the ASA → SRX judgment calls](#notes-on-the-asa--srx-judgment-calls)

A complete, worked conversion produced by the `firewall-config-conversion` skill. It
demonstrates the end-to-end workflow against a real parsed fixture and the per-section
fidelity report.

- **Source:** `skills/parsing-cisco-configs/references/fixture-expected-output.json` —
  a Cisco ASA config parsed into the intermediate schema (`metadata.source_vendor:
  cisco_asa`).
- **Target:** Juniper SRX (Junos `set` syntax), emitted per `references/emit-srx.md`.
- Only objects, zones, policies, NAT, interfaces, and routes that actually exist in the
  fixture are converted — nothing is invented. Source rule/NAT order is preserved.

The source fixture contains: 2 zones (`outside`, `inside`), 2 interfaces, 2 address
objects (`WEB`, `INSIDE-NET`), 1 custom service object (`HTTPS-ALT`), 1 security policy
(`OUTSIDE-IN-1`), 1 source NAT rule (`INSIDE-NET-auto-nat`), and 1 default static route.
There are no address/service groups, VPN tunnels, system/admin, HA, DHCP, screen, or
schedule sections, and **no secrets** in the source.

---

## Conversion DRAFT

```text
# Conversion DRAFT: cisco_asa -> srx
# Review required. Not production-ready. Manual items listed in the fidelity report.

# --- address_objects (global address-book) ---
set security address-book global address WEB 10.0.1.10/32
set security address-book global address INSIDE-NET 10.0.0.0/16

# --- service_objects (custom applications) ---
# HTTPS-ALT: ASA "object service" tcp/8443. (Unreferenced by any policy in source — converted for completeness.)
set applications application HTTPS-ALT protocol tcp
set applications application HTTPS-ALT destination-port 8443

# --- interfaces ---
# CAVEAT: interface names remapped positionally — verify against target SRX hardware (fpc/pic/port) and bindings.
set interfaces ge-0/0/0 unit 0 family inet address 203.0.113.2/24
set interfaces ge-0/0/1 unit 0 family inet address 10.0.0.1/24

# --- zones (ASA nameif + security-level -> SRX security-zone) ---
# CAVEAT: ASA security-level trust ordering not representable on SRX — implicit high->low permit replaced by explicit policies (none exist in source; see manual items).
set security zones security-zone outside interfaces ge-0/0/0.0
set security zones security-zone inside interfaces ge-0/0/1.0

# --- security_policies (preserve order via numeric prefix) ---
# Source rule OUTSIDE-IN-1 (_rule_index 1): permit any -> WEB tcp/443, log at session end.
# tcp/443 maps to predefined junos-https (no custom definition needed).
# The ACL is bound inbound on outside (from-zone outside); the destination zone is "any"
# (parser does not bind the ACL to a specific egress zone), so the global policy matches to-zone any.
set security policies global policy 010-OUTSIDE-IN-1 match from-zone outside
set security policies global policy 010-OUTSIDE-IN-1 match to-zone any
set security policies global policy 010-OUTSIDE-IN-1 match source-address any
set security policies global policy 010-OUTSIDE-IN-1 match destination-address WEB
set security policies global policy 010-OUTSIDE-IN-1 match application junos-https
set security policies global policy 010-OUTSIDE-IN-1 then permit
set security policies global policy 010-OUTSIDE-IN-1 then log session-close

# --- nat_rules (source NAT, interface PAT) ---
# Source rule INSIDE-NET-auto-nat (_rule_index 1): inside -> outside, INSIDE-NET hidden behind egress interface (ASA "object network" auto-NAT, dynamic interface).
# CAVEAT: ASA auto-NAT (object network) re-modeled as SRX source rule-set with interface PAT — verify egress interface and port-overload behavior.
set security nat source rule-set RS-INSIDE-OUTSIDE from zone inside
set security nat source rule-set RS-INSIDE-OUTSIDE to zone outside
set security nat source rule-set RS-INSIDE-OUTSIDE rule R10-INSIDE-NET match source-address 10.0.0.0/16
set security nat source rule-set RS-INSIDE-OUTSIDE rule R10-INSIDE-NET then source-nat interface

# --- routing (static) ---
set routing-options static route 0.0.0.0/0 next-hop 203.0.113.1
```

---

## Fidelity report (cisco_asa -> srx)

```text
Fidelity report (cisco_asa -> srx)
Section: address_objects     → converted (2/2 — WEB host, INSIDE-NET subnet, clean 1:1 to global address-book)
Section: address_groups      → n/a (none in source)
Section: service_objects     → converted (1/1 — HTTPS-ALT tcp/8443 as custom application; unreferenced by any policy)
Section: service_groups      → n/a (none in source)
Section: zones               → converted-with-caveats (2/2 — outside/inside zones bound; ASA security-level semantics not representable)
Section: security_policies   → converted (1/1 — action/log/zones map cleanly; from-zone outside, to-zone any global policy)
Section: nat_rules           → converted-with-caveats (1/1 — ASA auto-NAT re-modeled as SRX source rule-set + interface PAT)
Section: interfaces          → converted-with-caveats (2/2 — IP carried over; names remapped positionally to ge-0/0/x)
Section: routing             → converted-with-caveats (1/1 — default static route; verify next-hop reachability on SRX)
Section: vpn_tunnels         → n/a (none in source)
Section: system / admin      → n/a (none in source)
Manual items (must do on target):
  1. Add explicit inside->outside permit policy if outbound traffic must flow. SRX has no
     implicit high->low permit; the ASA security-level model is gone. The fixture converts
     a source NAT rule for inside->outside but no matching permit policy — without one,
     SRX default-deny will drop outbound user traffic.
  2. Review the OUTSIDE-IN-1 to-zone scope. The parser leaves the ACL destination zone as
     "any" (metadata warning: "ACL destination zone may require route/interface resolution
     beyond access-group binding"); the global policy is emitted with `match to-zone any`.
     If the real topology requires the inbound flow to land in a specific egress zone,
     narrow `to-zone any` accordingly before commit.
  3. Verify interface name remap (ge-0/0/0 = ASA GigabitEthernet0/0 outside, ge-0/0/1 =
     GigabitEthernet0/1 inside) against the actual SRX hardware fpc/pic/port layout and
     zone bindings.
  4. Add a default deny-with-log policy if an explicit logged drop is desired; SRX
     default-deny is silent.
  5. Secrets: none present in the source fixture (no enable/admin passwords, SNMP
     communities, or VPN PSKs to convert). If the production ASA contains encrypted
     secrets not in this fixture, they must be re-keyed manually on SRX as placeholders —
     secrets are never emitted.
```

---

## Notes on the ASA → SRX judgment calls

- **`nameif` + `security-level` → SRX zones.** ASA zones are interface labels with a
  numeric trust level that drives an implicit high→low permit. SRX zones carry no implicit
  trust, so every allowed flow needs an explicit policy. The two named zones convert
  cleanly; the *behavior* the security-levels implied does not, hence manual item 1.
- **`object service` tcp/8443 → custom `applications application`.** ASA port-based service
  objects have no App-ID equivalent on SRX; they become port-based custom applications.
  Well-known ports (tcp/443 in the policy) use predefined `junos-*` apps instead.
- **`object network` auto-NAT → SRX source rule-set with interface PAT.** ASA folds the NAT
  into the network object; SRX requires a named source rule-set scoped by from/to zone with
  `then source-nat interface`. Intent is preserved; the container shape differs.
- **`access-list` + `access-group` → `security policies global`.** Per the SRX greenfield
  default, the policy is emitted global with `match from-zone`/`match to-zone` leaves rather
  than a zone-pair context. Order is preserved with the `010-` numeric name prefix.
- **One leaf per `set` line.** Every `match …` and `then …` is its own line repeating the
  full policy path, so the draft is syntactically loadable and round-trips through
  `display set` on a vSRX.

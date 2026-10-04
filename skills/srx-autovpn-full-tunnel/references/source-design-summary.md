# AutoVPN Full-Tunnel Backhaul — Derived Design Summary

## Contents

- [Reference addressing (lab)](#reference-addressing-lab)
- [Crypto parameters](#crypto-parameters)
- [AutoVPN dynamic gateway (hub)](#autovpn-dynamic-gateway-hub)
- [Single bound tunnel + traffic selectors](#single-bound-tunnel--traffic-selectors)
- [Hub source NAT (internet egress only)](#hub-source-nat-internet-egress-only)
- [Hub security policies](#hub-security-policies)
- [Routing and the two gotchas](#routing-and-the-two-gotchas)
- [Validation result (lab)](#validation-result-lab)
- [Deployment order](#deployment-order)
- [Juniper references (from the lab)](#juniper-references-from-the-lab)

Derived summary of Jason Anderson's lab
[`srx-autovpn-backhaul-public`](https://github.com/anderson-jason573/srx-autovpn-backhaul-public)
(author: Jason Anderson). Built and validated on four vSRX firewalls (Junos OS
**23.2R2.21**) plus a Cisco IOS-XE router as WAN transit / simulated internet.
This is a paraphrased technical summary for local operational reference, not a
verbatim copy.

## Reference addressing (lab)

| Device | Role | fxp0 (mgmt) | WAN (ge-0/0/0) | WAN peer | LAN (ge-0/0/1) |
|--------|------|-------------|----------------|----------|----------------|
| srx01 | Hub + egress | 172.27.1.50 | 10.0.0.2/30 | 10.0.0.1 | 192.168.1.1/24 |
| srx02 | Spoke | 172.27.1.51 | 10.0.1.2/30 | 10.0.1.1 | 192.168.2.1/24 |
| srx03 | Spoke | 172.27.1.52 | 10.0.2.2/30 | 10.0.2.1 | 192.168.3.1/24 |
| srx04 | Spoke | 172.27.1.54 | 10.0.3.2/30 | 10.0.3.1 | 192.168.4.1/24 |
| CSR1 | WAN transit / sim-internet | 172.27.1.53 | four `/30` links | — | loopback 10.100.100.1 |

CSR1 routes between all four `/30`s, so any SRX WAN IP can reach any other — this
is the transport the IPsec tunnels ride. CSR1's loopback `10.100.100.1` stands in
for "the internet"; because CSR1 has the hub `/30` connected, it returns traffic to
the hub NAT address with no extra config.

## Crypto parameters

- **Phase 1 (IKE):** pre-shared key, DH group 14, SHA-256, AES-256-CBC, IKEv2
  (`v2-only`), lifetime 86400 s, `mode main`.
- **Phase 2 (IPsec):** ESP, AES-256-GCM, PFS group 14, lifetime 3600 s.
- **MSS clamp:** `set security flow tcp-mss ipsec-vpn mss 1350`.

## AutoVPN dynamic gateway (hub)

The hub gateway is **dynamic** (`dynamic hostname homelab.local` +
`dynamic ike-user-type group-ike-id` + `reject-duplicate-connection`), with
`local-identity hostname srx01.homelab.local`, `external-interface ge-0/0/0.0`,
`version v2-only`. Deployable `set` commands are in the SKILL.md *Config Skeleton*
(not repeated here to avoid drift). Each spoke: `local-identity hostname srxNN.homelab.local`, `remote-identity
hostname srx01.homelab.local`, gateway `address 10.0.0.2` (the hub WAN IP).

## Single bound tunnel + traffic selectors

The hub binds one VPN to `st0.0` for **all** spokes, with traffic-selector
`TS-ALL local-ip 0.0.0.0/0` + `remote-ip 192.168.0.0/16` (see SKILL.md *Config
Skeleton* for the `set` commands). Selector matrix (split vs. full tunnel):

> **Version note (24.4R1+):** the spoke `remote-ip 0.0.0.0/0` below commits only on
> older images (this lab: 23.2R2.21). On 24.4R1/25.4R1 it is rejected when the
> gateway has a static `address` — use the `0.0.0.0/1` + `128.0.0.0/1` split
> (see SKILL.md, Traffic Selectors).

| Selector | Split | Full-tunnel |
|----------|-------|-------------|
| Spoke `local-ip` | `192.168.x.0/24` | `192.168.x.0/24` |
| Spoke `remote-ip` | `192.168.1.0/24` | `0.0.0.0/0` |
| Hub `local-ip` | `192.168.1.0/24` | `0.0.0.0/0` |
| Hub `remote-ip` | `192.168.0.0/16` | `192.168.0.0/16` |

IKEv2 narrows hub `0.0.0.0/0` ∩ spoke `/24` to the spoke `/24`; ARI (keying on the
remote selector) installs each clean `/24` via `st0.0`. Hub `local-ip 0.0.0.0/0`
does **not** create a default route via `st0.0`.

### Hub `remote-ip` supernet vs. wildcard

- **`192.168.0.0/16` (supernet, lab default):** hub-side guardrail — IKE rejects
  any spoke advertising a prefix outside the summary. Safer when addressing is
  clean.
- **`0.0.0.0/0` (wildcard):** fully zero-touch hub for discontiguous/unsummarizable
  spoke LANs, but no guardrail — a rogue spoke could advertise the hub LAN, another
  site, or a default, and ARI would install it. Push guardrails to policy/filtering.
- Spokes must always propose their **specific** `/24`, never `0.0.0.0/0`.
- Overlapping spoke subnets are a **NAT** problem (static/twice-NAT at the
  colliding spoke), not a selector problem.

## Hub source NAT (internet egress only)

Source NAT rule-set `VPN-BACKHAUL` (`set` commands in the SKILL.md *Config
Skeleton*) is scoped `VPN → untrust`, so only internet egress is PATed to the hub
WAN IP.
Spoke-to-spoke (`VPN → VPN`) and spoke-to-hub-LAN (`VPN → trust`) stay un-NAT'd.

## Hub security policies

Added for full tunnel: `VPN → untrust` permit (spoke internet egress) and
`VPN → VPN` permit (spoke-to-spoke hairpin on the shared `st0.0`). Unchanged:
`trust → untrust`, `trust → VPN`, `VPN → trust`. Return traffic is stateful.

## Routing and the two gotchas

**Spoke:** default `0.0.0.0/0 → st0.0`; **anti-recursion** host route
`10.0.0.2/32 → <CSR /30 next-hop>` keeps ESP out of the tunnel; WAN `/30`s via the
underlay.

**Hub:** WAN `/30`s via `10.0.0.1`; spoke LANs via ARI; default
`0.0.0.0/0 → 10.0.0.1` for de-encapsulated internet egress.

**Management-default ECMP caveat:** the vSRX image's `0.0.0.0/0 → 172.27.1.1 via
fxp0` collides with the new defaults (Junos ECMPs them; traffic leaks out `fxp0`,
NAT does not apply). Production fix: management routing-instance. Lab shortcut
(validated): use specific routes — `10.100.100.1/32 → st0.0` on spokes,
`10.100.100.1/32 → 10.0.0.1` on the hub, plus `192.168.0.0/16 → st0.0` on each
spoke for hub-LAN and spoke-to-spoke.

## Validation result (lab)

Validated end-to-end on all four SRX (hub + three spokes) on Junos 23.2R2.21: hub
shows three IKE SAs UP, three IPsec SAs, and three clean ARI routes
(`192.168.2/3/4.0/24` via `st0.0`); stable data plane (no core dumps); both data
paths (internet backhaul and spoke-to-spoke) pass 5/5, 0% loss.

## Deployment order

1. CSR1 (WAN transit) — must be up first
2. srx01 (hub)
3. srx02 / srx03 / srx04 (spokes, any order)

PSK kept out of config as `$AUTOVPN_PSK`, substituted at deploy time from a
git-ignored `secrets.env`; identical on hub and every spoke.

## Juniper references (from the lab)

- IPsec VPN User Guide | Junos OS
- AutoVPN on Hub-and-Spoke Devices | Junos OS
- Understanding Traffic Selectors in Route-Based VPNs | Junos OS
- Example: Configuring AutoVPN with Pre-Shared Key | Junos OS
- IPsec VPN Configuration Overview | Junos OS

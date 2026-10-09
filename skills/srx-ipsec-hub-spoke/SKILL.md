---
name: srx-ipsec-hub-spoke
description: Design, configure, audit, and troubleshoot Juniper SRX static route-based IPsec hub-and-spoke. Use when handling per-spoke IKE gateways, one st0 per spoke, static routes, anti-recursion, centralized source NAT, VPN-to-untrust policy, or hub hairpinning. Use AutoVPN for changing spokes and ADVPN for direct shortcuts.
version: 1.0.5
author:
  - fastrevmd-lab
  - Claude
  - GPT
license: MIT
metadata:
  hermes:
    tags: [srx, junos, ipsec, vpn, route-based, hub-and-spoke, point-to-point, p2p, full-tunnel, backhaul, ikev2, pre-shared-key, source-nat, anti-recursion, hairpin, centralized-egress, st0, static-routing]
    related_skills: [srx-autovpn-full-tunnel, srx-advpn, srx-nat, srx-mnha, srx-policy, parsing-srx-configs]
  sources:
    - title: "SRX Static Point-to-Point Hub-and-Spoke — Full-Tunnel Backhaul (lab)"
      author: Jason Anderson
      url: https://github.com/anderson-jason573/srx-p2p-ipsec-public
      retrieved: "2026-06-29"
    - title: Route-Based IPsec VPNs | Junos OS
      author: Juniper Networks
      url: https://www.juniper.net/documentation/us/en/software/junos/vpn-ipsec/topics/topic-map/security-route-based-ipsec-vpns.html
      retrieved: "2026-06-29"
    - title: IPsec VPN Overview, Understanding Hub-and-Spoke VPNs | Junos OS
      author: Juniper Networks
      url: https://www.juniper.net/documentation/us/en/software/junos/vpn-ipsec/topics/topic-map/security-ipsecvpn-overview.html#id-understanding-hub-and-spoke-vpns
      retrieved: "2026-06-29"
    - title: IPsec VPN User Guide | Junos OS
      author: Juniper Networks
      url: https://www.juniper.net/documentation/us/en/software/junos/vpn-ipsec/index.html
      retrieved: "2026-06-29"
---

# SRX Static Point-to-Point IPsec Hub-and-Spoke (Full-Tunnel Backhaul)

## Contents

- [Overview](#overview)
- [Scope and routing](#scope-and-routing)
- [Runtime intake](#runtime-intake)
- [Topology Model](#topology-model)
- [Static Hub-and-Spoke Mechanics](#static-hub-and-spoke-mechanics)
- [Routing — the entire story](#routing--the-entire-story)
- [Hub NAT and Security Policies](#hub-nat-and-security-policies)
- [Config Skeleton (`set` format)](#config-skeleton-set-format)
- [Verification](#verification)
- [Troubleshooting Matrix](#troubleshooting-matrix)
- [Caveats and Tradeoffs](#caveats-and-tradeoffs)
- [Choose This vs. AutoVPN](#choose-this-vs-autovpn)
- [Verification Checklist](#verification-checklist)
- [Source Notes](#source-notes)

## Overview

Static per-spoke route-based IPsec is the simplest, most explicit way to build a
hub-and-spoke overlay: each spoke is an **explicitly configured peer** with its own
IKE gateway, IPsec VPN, `st0` unit, and static route on the hub. There is **no
dynamic gateway, no traffic selectors, and no Auto Route Insertion** — **routing
alone** decides what each tunnel carries.

This skill applies that to **full-tunnel backhaul**: every spoke sends
**everything not local to its own LAN** up its tunnel to the hub. Core principle:
**if traffic is not local to a spoke, it goes to the hub.** The hub then
source-NATs internet-bound traffic out its WAN and hairpins spoke-to-spoke traffic
out the destination spoke's tunnel un-NAT'd. The motivation is **centralized
egress** — inspect/filter/log all internet traffic at one point (UTM/IDP on the
hub).

The full-tunnel changes versus a split tunnel are confined to four things: the
spoke's **default route into the tunnel**, **hub egress routing/NAT**, **two added
hub security policies**, and the hub's **per-spoke static routes**. Everything else
is standard route-based IPsec.

> **Attribution.** The reference topology, full-tunnel backhaul approach, and the
> validated `set`-format configuration this skill summarizes come from Jason
> Anderson's lab `srx-p2p-ipsec-public`
> (https://github.com/anderson-jason573/srx-p2p-ipsec-public), built on four vSRX
> (Junos OS 23.2R2.21) plus a Cisco IOS-XE WAN transit router. See
> `references/source-design-summary.md`.

## Scope and routing

Use static tunnels for a small stable estate where every peer, `st0`, and route must be explicit. Use `srx-autovpn-full-tunnel` for many or changing spokes, `srx-advpn` for direct branch shortcuts, and another design when spokes need local breakout.

## Runtime intake

Before starting the workflow, inspect the request, supplied artifacts, and
available approved read-only evidence. If unresolved facts could materially
change safety, scope, correctness, confidence, or the requested output, read
`references/runtime-intake.md`.

For each unresolved material fact whose catalog condition is true, invoke Claude `AskUserQuestion` or Codex `request_user_input` before continuing or issuing an open-ended request.
Ask at most three single-select catalog questions per round. After each response, ask another round whenever any unresolved material catalog condition remains true; continue only when none remain. Do not repeat answered questions or show the full catalog.
Without a native tool, present each selected catalog question with its 2-3 labeled choices and a free-text `Other` path in concise plain text; do not substitute a generic checklist.

Never request secrets or unredacted customer data. Treat intake answers as task
context, not approval for a live change; obtain separate explicit approval
before configuration, commit, upgrade, reboot, delete, or failover actions.

## Topology Model

```
                CSR1 / upstream router  (loopback = "the internet")
        WAN /30   WAN /30    WAN /30    WAN /30
           │         │          │          │
        srx01      srx02      srx03      srx04
         HUB       spoke      spoke      spoke
     192.168.1/24  .2/24      .3/24      .4/24   (LANs)

   Three static P2P tunnels, one per spoke:
     srx01 st0.0 <══> srx02 st0.0
     srx01 st0.1 <══> srx03 st0.0
     srx01 st0.2 <══> srx04 st0.0
```

| Element | Role |
|---------|------|
| Hub WAN (`untrust`) | IKE/IPsec endpoint + internet egress; PAT target |
| Hub LAN (`trust`) | Local hub subnet |
| Hub `st0.0/1/2` (`VPN`) | **One `st0` unit per spoke**, all in one VPN zone |
| Spoke WAN (`untrust`) | IKE/IPsec endpoint to the hub WAN IP |
| Spoke `st0.0` (`VPN`) | Single tunnel to the hub |

All `st0` units are **unnumbered, point-to-point** (no `multipoint`) — each unit
terminates exactly one peer; the hub just has several. Routing is by static route,
so no tunnel IP is needed. Management (`fxp0`) is out-of-band.

## Static Hub-and-Spoke Mechanics

- **One IKE gateway per spoke, pinned by the spoke's WAN IP** (`address
  10.0.x.2`). No `dynamic hostname` / `group-ike-id`, no hostname identities.
- **IKEv2 / IPsec.** Phase 1: PSK, DH group 14, SHA-256, AES-256-CBC, `v2-only`.
  Phase 2: ESP, AES-256-GCM, PFS group 14, 3600 s. Clamp `tcp-mss ipsec-vpn 1350`.
- **One bound `st0` unit per tunnel.** Hub: `st0.0` (→srx02), `st0.1` (→srx03),
  `st0.2` (→srx04). Each spoke: a single `st0.0` to the hub.
- **No traffic selectors.** Each VPN is a plain route-based tunnel; the negotiated
  proxy-id defaults to `0.0.0.0/0 ↔ 0.0.0.0/0`, so one SA per spoke can carry
  internet **and** inter-spoke traffic — **routing**, not a selector, decides what
  enters each `st0`.
- **No Auto Route Insertion.** The hub needs an **explicit static route** to each
  spoke LAN (`192.168.x.0/24 → st0.n`). Nothing is installed automatically.
- `establish-tunnels immediately` is convenient so tunnels come up without data
  traffic to trigger them.

> **Auth: lab PSK vs. production PKI.** A single shared PSK keeps the focus on the
> topology, but is not production practice. Prefer certificate-based (PKI) auth with
> per-device identity, or at minimum strong, unique **per-tunnel** PSKs in a
> secrets manager with rotation.

## Routing — the entire story

Because there are no traffic selectors, **routing decides what each `st0` carries**.

### Spoke

| Route | Purpose |
|-------|---------|
| `0.0.0.0/0 → st0.0` | Default into the tunnel — internet, hub LAN, and other spokes |
| `HUB_WAN/32 → <underlay next-hop>` | **Anti-recursion** — ESP to the hub WAN must NOT enter the tunnel |
| WAN `/30`s `→ <underlay next-hop>` | Underlay reachability |

A single route-based SA (proxy-id `0.0.0.0/0`) carries all of it.

> **Anti-recursion is the #1 gotcha of full tunnel.** The spoke default points into
> `st0.0`, but the ESP packets that *carry* the tunnel are destined to the hub's
> WAN IP. Without the more-specific host route `HUB_WAN/32 → <underlay next-hop>`,
> that ESP would follow the default into the tunnel → infinite recursion and an
> instant black-hole. Keep it (and the connected WAN `/30`) more-specific than the
> default.

### Hub

| Route | Purpose |
|-------|---------|
| `192.168.2.0/24 → st0.0` | Reach/return to srx02 (also receives srx03/srx04-to-srx02 hairpin) |
| `192.168.3.0/24 → st0.1` | Reach/return to srx03 |
| `192.168.4.0/24 → st0.2` | Reach/return to srx04 |
| `0.0.0.0/0 → <WAN next-hop>` | Internet egress for de-encapsulated spoke traffic |
| WAN `/30`s `→ <WAN next-hop>` | Reach each spoke's WAN IP to build its tunnel |

Spoke-to-spoke needs **no special tunnel config**: srx02→srx03 follows srx02's
default into `st0.0`, arrives at the hub, matches the hub's `192.168.3.0/24 →
st0.1` route, and leaves on the srx03 tunnel. Because all `st0` units are in the
hub's **VPN** zone, that hairpin is an intra-zone `VPN → VPN` flow.

> **Caveat — competing management default (gotcha #2, ECMP trap).** Many vSRX
> images carry `0.0.0.0/0 → <mgmt-gw> via fxp0` in `inet.0`. Adding a second
> `0.0.0.0/0` does **not** override it — Junos installs both as **ECMP**, so half
> the traffic leaks out `fxp0` and NAT / the `untrust` policy never applies.
> Production fix: put `fxp0` in a **management routing-instance**. Lab shortcut
> (validated): route the specific internet destination — `<sim-internet>/32 →
> st0.0` on spokes, `<sim-internet>/32 → <WAN nh>` on the hub — plus
> `192.168.0.0/16 → st0.0` on each spoke for hub-LAN and spoke-to-spoke. These stay
> more-specific than the management default and exercise the full data path.

## Hub NAT and Security Policies

### Source NAT (internet egress only)

```
set security nat source rule-set VPN-BACKHAUL from zone VPN
set security nat source rule-set VPN-BACKHAUL to zone untrust
set security nat source rule-set VPN-BACKHAUL rule SNAT-INTERNET match source-address 192.168.0.0/16
set security nat source rule-set VPN-BACKHAUL rule SNAT-INTERNET match destination-address 0.0.0.0/0
set security nat source rule-set VPN-BACKHAUL rule SNAT-INTERNET then source-nat interface
```

Scoped `from zone VPN to zone untrust`, so it matches **only internet egress**. All
spoke tunnels are in the VPN zone, so **one** rule-set covers every spoke.
Spoke-to-spoke (`VPN → VPN`) and spoke-to-hub-LAN (`VPN → trust`) never match and
stay un-NAT'd — real private IPs preserved between sites.

> Hub-LAN hosts to the internet are `trust → untrust` and are **not** covered. Add
> a parallel `trust → untrust` rule to make the hub the NAT egress for its own LAN.

### Security policies

| Policy | Split tunnel | Full-tunnel backhaul |
|--------|--------------|----------------------|
| `trust → untrust` | permit | same |
| `trust → VPN` | permit | same |
| `VPN → trust` | permit | same |
| `VPN → untrust` | — | **add permit** (spoke internet egress) |
| `VPN → VPN` | — | **add permit** (spoke-to-spoke hairpin across `st0` units) |

All tunnel interfaces share one **VPN** zone, so the spoke-to-spoke hairpin
(srx02's `st0.0` → srx03's `st0.1`) is an **intra-zone** `VPN → VPN` flow — one
policy covers every spoke pair. Return traffic is stateful — no reverse policy.
On the **spoke**, all LAN egress now exits via zone `VPN` (`st0.0`), so the
spoke's `trust → VPN` policy must permit the **full backhaul scope**
(`destination-address any` or the intended backhauled prefixes) — a policy
scoped to the hub LAN would leave the tunnel up while user internet traffic is
silently denied. The spoke's `trust → untrust` becomes dead (no local
breakout) but is harmless.

## Config Skeleton (`set` format)

PSK is a placeholder substituted at deploy time from a git-ignored secrets file —
never commit it.

### Hub (one block per spoke; srx02 shown)

```
# --- Tunnel interfaces, one unit per spoke (P2P, unnumbered) ---
set interfaces st0 unit 0 family inet     # -> srx02
set interfaces st0 unit 1 family inet     # -> srx03
set interfaces st0 unit 2 family inet     # -> srx04

# --- Shared IKE/IPsec proposals & policies ---
set security ike proposal IKE-PROP authentication-method pre-shared-keys
set security ike proposal IKE-PROP dh-group group14
set security ike proposal IKE-PROP authentication-algorithm sha-256
set security ike proposal IKE-PROP encryption-algorithm aes-256-cbc
set security ike proposal IKE-PROP lifetime-seconds 86400
set security ike policy IKE-POL proposals IKE-PROP
set security ike policy IKE-POL pre-shared-key ascii-text "$IPSEC_PSK"
set security ipsec proposal IPSEC-PROP protocol esp
set security ipsec proposal IPSEC-PROP encryption-algorithm aes-256-gcm
set security ipsec proposal IPSEC-PROP lifetime-seconds 3600
set security ipsec policy IPSEC-POL perfect-forward-secrecy keys group14
set security ipsec policy IPSEC-POL proposals IPSEC-PROP

# --- Per-spoke gateway (pinned by spoke WAN IP) + VPN bound to its st0 unit ---
set security ike gateway GW-srx02 ike-policy IKE-POL
set security ike gateway GW-srx02 address 10.0.1.2
set security ike gateway GW-srx02 external-interface ge-0/0/0.0
set security ike gateway GW-srx02 version v2-only
set security ipsec vpn VPN-srx02 bind-interface st0.0
set security ipsec vpn VPN-srx02 ike gateway GW-srx02
set security ipsec vpn VPN-srx02 ike ipsec-policy IPSEC-POL
set security ipsec vpn VPN-srx02 establish-tunnels immediately
# ... repeat GW-srx03/VPN-srx03 -> st0.1, GW-srx04/VPN-srx04 -> st0.2 ...
set security flow tcp-mss ipsec-vpn mss 1350

# --- Zones (all st0 units in the VPN zone) ---
set security zones security-zone untrust host-inbound-traffic system-services ike
set security zones security-zone untrust interfaces ge-0/0/0.0
set security zones security-zone trust interfaces ge-0/0/1.0
set security zones security-zone VPN host-inbound-traffic system-services ping
set security zones security-zone VPN interfaces st0.0
set security zones security-zone VPN interfaces st0.1
set security zones security-zone VPN interfaces st0.2

# --- Hub security policies (full-tunnel: add VPN->untrust egress + VPN->VPN hairpin) ---
# (source-NAT rule-set SNAT-INTERNET, zone VPN->untrust, is shown in "Hub NAT and Security Policies")
set security policies from-zone trust to-zone untrust policy trust-untrust match source-address any
set security policies from-zone trust to-zone untrust policy trust-untrust match destination-address any
set security policies from-zone trust to-zone untrust policy trust-untrust match application any
set security policies from-zone trust to-zone untrust policy trust-untrust then permit
set security policies from-zone VPN to-zone untrust policy vpn-internet match source-address any
set security policies from-zone VPN to-zone untrust policy vpn-internet match destination-address any
set security policies from-zone VPN to-zone untrust policy vpn-internet match application any
set security policies from-zone VPN to-zone untrust policy vpn-internet then permit
set security policies from-zone VPN to-zone VPN policy spoke-to-spoke match source-address any
set security policies from-zone VPN to-zone VPN policy spoke-to-spoke match destination-address any
set security policies from-zone VPN to-zone VPN policy spoke-to-spoke match application any
set security policies from-zone VPN to-zone VPN policy spoke-to-spoke then permit

# --- Hub routing: explicit per-spoke LAN routes (no ARI) + egress default ---
set routing-options static route 192.168.2.0/24 next-hop st0.0
set routing-options static route 192.168.3.0/24 next-hop st0.1
set routing-options static route 192.168.4.0/24 next-hop st0.2
set routing-options static route 0.0.0.0/0 next-hop 10.0.0.1      # see ECMP caveat
```

### Spoke (srx02 shown)

```
set interfaces st0 unit 0 family inet

# --- Same IKE/IPsec proposals & policies as the hub (per-device, must be defined here too) ---
set security ike proposal IKE-PROP authentication-method pre-shared-keys
set security ike proposal IKE-PROP dh-group group14
set security ike proposal IKE-PROP authentication-algorithm sha-256
set security ike proposal IKE-PROP encryption-algorithm aes-256-cbc
set security ike proposal IKE-PROP lifetime-seconds 86400
set security ike policy IKE-POL proposals IKE-PROP
set security ike policy IKE-POL pre-shared-key ascii-text "$IPSEC_PSK"
set security ipsec proposal IPSEC-PROP protocol esp
set security ipsec proposal IPSEC-PROP encryption-algorithm aes-256-gcm
set security ipsec proposal IPSEC-PROP lifetime-seconds 3600
set security ipsec policy IPSEC-POL perfect-forward-secrecy keys group14
set security ipsec policy IPSEC-POL proposals IPSEC-PROP

set security ike gateway GW-hub ike-policy IKE-POL
set security ike gateway GW-hub address 10.0.0.2          # the HUB WAN IP
set security ike gateway GW-hub external-interface ge-0/0/0.0
set security ike gateway GW-hub version v2-only
set security ipsec vpn VPN-hub bind-interface st0.0
set security ipsec vpn VPN-hub ike gateway GW-hub
set security ipsec vpn VPN-hub ike ipsec-policy IPSEC-POL
set security ipsec vpn VPN-hub establish-tunnels immediately

# --- Zones: st0.0 in the VPN zone; untrust must accept IKE ---
set security zones security-zone untrust host-inbound-traffic system-services ike
set security zones security-zone untrust interfaces ge-0/0/0.0
set security zones security-zone trust interfaces ge-0/0/1.0
set security zones security-zone VPN interfaces st0.0

# --- Policy: ALL LAN egress now exits via zone VPN — destination must be any ---
set security policies from-zone trust to-zone VPN policy LAN-TO-TUNNEL match source-address any
set security policies from-zone trust to-zone VPN policy LAN-TO-TUNNEL match destination-address any
set security policies from-zone trust to-zone VPN policy LAN-TO-TUNNEL match application any
set security policies from-zone trust to-zone VPN policy LAN-TO-TUNNEL then permit
set security policies from-zone VPN to-zone trust policy TUNNEL-TO-LAN match source-address any
set security policies from-zone VPN to-zone trust policy TUNNEL-TO-LAN match destination-address any
set security policies from-zone VPN to-zone trust policy TUNNEL-TO-LAN match application any
set security policies from-zone VPN to-zone trust policy TUNNEL-TO-LAN then permit

# Routing: default into the tunnel + ANTI-RECURSION host route to the hub WAN
set routing-options static route 0.0.0.0/0 next-hop st0.0
set routing-options static route 10.0.0.2/32 next-hop 10.0.1.1   # anti-recursion (CRITICAL)
```

See `references/source-design-summary.md` for full per-device detail.

## Verification

```
show security ike security-associations            # one Phase 1 SA per spoke, UP
show security ipsec security-associations           # one IPsec SA per spoke, bound to st0.0/1/2
show security ipsec security-associations detail     # proxy-id 0.0.0.0/0 <-> 0.0.0.0/0 (no selectors)
show route 192.168.2.0/24                            # static, via the correct st0 unit
show security nat source rule all                    # SNAT-INTERNET hit count incrementing
show security nat source summary
show security flow session                           # spoke-src -> internet, xlated to hub WAN IP
show system core-dumps                               # must stay zero
```

Internet backhaul: from a spoke, `ping <sim-internet> source <spoke-LAN-gw>` — hub
session shows the source translated to the hub WAN IP.
Spoke-to-spoke: `ping <other-spoke-LAN> source <spoke-LAN-gw>` — hub session shows
the flow **entering on one `st0` unit and leaving on another**, zone `VPN → VPN`,
**no NAT**.

## Troubleshooting Matrix

| Stage | Symptom | Common causes |
|-------|---------|---------------|
| Underlay | Peers can't reach each other | Transport routing/filtering; verify `ping` between WAN IPs |
| Phase 1 (IKE) | No IKE SA / stuck | PSK mismatch, proposal/DH mismatch, **wrong peer `address`**, IKEv1-vs-v2 mismatch |
| Phase 2 (IPsec) | IKE up, no IPsec SA | IPsec proposal/PFS mismatch, proxy-id mismatch |
| Routing | Spoke LAN unreachable from hub | **Missing/incorrect per-spoke static route** to the right `st0` unit (no ARI here) |
| Data plane | Tunnel up, no traffic | Spoke default not into `st0`, `st0` in wrong zone, `VPN→untrust`/`VPN→VPN` policy missing |
| Internet egress | NAT zero hits / traffic leaks | **Management-default ECMP** out `fxp0`; NAT rule-set not `VPN→untrust` |
| Recursion | Tunnel flaps / black-hole | **Missing anti-recursion host route** `HUB_WAN/32` |
| Spoke-to-spoke | One direction only | Hub missing the destination spoke's `/24 → st0.n` route or `VPN→VPN` policy |
| Fragmentation | Large flows fail, small ones work | Tunnel MTU/MSS — keep/lower `tcp-mss ipsec-vpn` |

IKE tracing: `set security ike traceoptions file ike-trace` / `flag ike` /
`level 15` (iked-based platforms take a numeric trace level; `level detail`
fails commit on Junos 24.4R1 — live-verified); read `show log ike-trace`;
renegotiate with `clear security ike
security-associations` and `clear security ipsec security-associations`. Live
daemon log: `show log iked` (modern) or `show log kmd` (older).

## Caveats and Tradeoffs

1. **Anti-recursion route** — the single most common break (see the anti-recursion
   callout above).
2. **Adding a spoke is a hub change** — a new IKE gateway, IPsec VPN, `st0` unit,
   and static route on the hub. The defining tradeoff of the static approach: fine
   for a few stable sites, painful at scale.
3. **No local breakout** — all spoke internet traffic concentrates on the hub's
   WAN, CPU, and NAT table. Upside: centralized inspection/logging.
4. **MTU / MSS** — backhauling large flows over ESP plus NAT makes fragmentation
   likely; keep the MSS clamp.
5. **Spoke-to-spoke hairpin enters and leaves on *different* `st0` units** (unlike
   AutoVPN's single shared `st0.0`); the shared VPN zone makes it one `VPN → VPN`
   policy.

## Choose This vs. AutoVPN

| | **Static P2P hub-spoke (this skill)** | AutoVPN full-tunnel (`srx-autovpn-full-tunnel`) |
|---|---|---|
| Hub gateways | One static gateway per spoke (by IP) | One dynamic `group-ike-id` gateway |
| Hub tunnel interfaces | One `st0` unit per spoke | Single shared `st0.0` |
| What scopes the tunnel | **Routing only — no selectors** | Traffic selectors |
| Hub → spoke-LAN routes | Static, one per spoke | Auto Route Insertion (`ARI-TS`) |
| Add a new spoke | Hub change: +gateway +VPN +`st0` +route | **Zero hub change** |
| Best for | A few small, stable, explicit sites | Many or churning sites |

Backhaul behavior, NAT, anti-recursion, and the management-default caveat are
**identical** between the two. Start static for a handful of explicit sites; switch
to AutoVPN when spoke count grows or churns.

If neither fits because spoke-to-spoke traffic dominates, see `srx-advpn` for its
three-way ADVPN vs AutoVPN vs Static comparison.

## Verification Checklist

- [ ] Each spoke pinned by `address <spoke-WAN-IP>`; spoke pins the hub by `address <HUB_WAN>`
- [ ] One `st0` unit per spoke on the hub, all in the VPN zone; spoke has a single `st0.0`
- [ ] Hub has an explicit `192.168.x.0/24 → st0.n` route for **every** spoke (no ARI)
- [ ] Spoke has `0.0.0.0/0 → st0.0` AND the anti-recursion `HUB_WAN/32` host route
- [ ] Hub egress default does not ECMP with a management default
- [ ] Source-NAT rule-set is `VPN → untrust` only; `VPN→untrust` and `VPN→VPN` policies permit
- [ ] `show system core-dumps` is zero

## Source Notes

This original playbook was inspired by Jason Anderson's attributed
`srx-p2p-ipsec-public` lab and checked against Juniper Junos IPsec VPN
documentation. The upstream lab has no explicit license and is not included or
relicensed here. See `references/source-index.md` and the independently written
`references/source-design-summary.md`.

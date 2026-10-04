---
name: srx-autovpn-full-tunnel
description: Design, configure, audit, and troubleshoot Juniper SRX AutoVPN full-tunnel hub backhaul. Use when handling group-ike-id gateways, traffic selectors, ARI, shared st0, anti-recursion routes, source NAT, VPN hairpinning, NAT-T, or Junos 24.4R1+ PSK and 0.0.0.0/0 commit errors. Use ADVPN for direct spoke shortcuts.
version: 1.1.3
author:
  - fastrevmd-lab
  - Claude
  - GPT
license: MIT
metadata:
  hermes:
    tags: [srx, junos, autovpn, ipsec, vpn, hub-and-spoke, full-tunnel, backhaul, traffic-selectors, ari, auto-route-insertion, ikev2, group-ike-id, source-nat, anti-recursion, centralized-egress, st0]
    related_skills: [srx-advpn, srx-ipsec-hub-spoke, srx-nat, srx-mnha, srx-policy, parsing-srx-configs]
  sources:
    - title: "SRX AutoVPN — Full-Tunnel Backhaul (lab)"
      author: Jason Anderson
      url: https://github.com/anderson-jason573/srx-autovpn-backhaul-public
      retrieved: "2026-06-29"
    - title: AutoVPN on Hub-and-Spoke Devices | Junos OS
      author: Juniper Networks
      url: https://www.juniper.net/documentation/us/en/software/junos/vpn-ipsec/topics/topic-map/security-autovpn-on-hub-and-spoke-devices.html
      retrieved: "2026-06-29"
    - title: Understanding Traffic Selectors in Route-Based VPNs | Junos OS
      author: Juniper Networks
      url: https://www.juniper.net/documentation/us/en/software/junos/vpn-ipsec/topics/topic-map/security-traffic-selectors-in-route-based-vpns.html
      retrieved: "2026-06-29"
    - title: "Example: Configuring AutoVPN with Pre-Shared Key | Junos OS"
      author: Juniper Networks
      url: https://www.juniper.net/documentation/us/en/software/junos/interfaces-next-gen-services/topics/example/configuring-auto-vpn-pre-shared-key.html
      retrieved: "2026-06-29"
    - title: IPsec VPN User Guide | Junos OS
      author: Juniper Networks
      url: https://www.juniper.net/documentation/us/en/software/junos/vpn-ipsec/index.html
      retrieved: "2026-06-29"
    - title: "Field report: 12-branch vSRX3 lab, Junos 24.4R1.9 / 25.4R1.12 (commit blockers + NAT-T findings)"
      author: community field report (fwskillsshare issues #5, #6)
      url: https://github.com/mechubsec/fwskillsshare/issues/5
      retrieved: "2026-07-02"
---

# SRX AutoVPN Full-Tunnel Backhaul

## Contents

- [Overview](#overview)
- [Runtime intake](#runtime-intake)
- [Scope and routing](#scope-and-routing)
- [Topology Model](#topology-model)
- [AutoVPN Mechanics](#autovpn-mechanics)
- [Traffic Selectors — the core](#traffic-selectors--the-core)
- [Routing Changes](#routing-changes)
- [Hub NAT and Security Policies](#hub-nat-and-security-policies)
- [Config Skeleton (hub, `set` format)](#config-skeleton-hub-set-format)
- [Verification](#verification)
- [Troubleshooting Matrix](#troubleshooting-matrix)
- [Caveats and Tradeoffs](#caveats-and-tradeoffs)
- [Choose This vs. Static Hub-Spoke](#choose-this-vs-static-hub-spoke)
- [Verification Checklist](#verification-checklist)
- [Source Notes](#source-notes)

## Overview

AutoVPN lets one hub gateway accept IPsec connections from any number of spokes
with **no per-spoke hub configuration**. *Full-tunnel backhaul* is the design
choice to send **everything a spoke does not own locally** up the tunnel to the
hub, instead of the conventional split tunnel (only hub-LAN traffic in the
tunnel, internet broken out locally, no spoke-to-spoke).

Core principle: **if traffic is not local to a spoke, it goes to the hub.** The
hub then source-NATs internet-bound traffic out its WAN and hairpins
spoke-to-spoke traffic back out the tunnel un-NAT'd. The motivation is
**centralized egress** — all internet traffic can be inspected, filtered, and
logged at one point (UTM/IDP on the hub).

The full-tunnel changes are confined to four things: the **traffic selector
scope**, **spoke routing**, **hub egress routing/NAT**, and **two added hub
security policies**. Everything else — IKE/IPsec parameters and the AutoVPN
dynamic-gateway mechanics — is standard AutoVPN.

> **Attribution.** The reference topology, full-tunnel backhaul approach, and the
> validated `set`-format configuration this skill summarizes come from Jason
> Anderson's lab `srx-autovpn-backhaul-public`
> (https://github.com/anderson-jason573/srx-autovpn-backhaul-public), built and
> validated on four vSRX (Junos OS 23.2R2.21) plus a Cisco IOS-XE WAN transit
> router. See `references/source-design-summary.md`.

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

## Scope and routing

Use this design when all spoke internet and inter-spoke traffic must traverse a centralized hub. Use `srx-ipsec-hub-spoke` for a small explicit estate, `srx-advpn` when direct spoke shortcuts are required, and another design when spokes need local breakout.

## Topology Model

```
                CSR1 / upstream router  (loopback = "the internet")
        WAN /30   WAN /30    WAN /30    WAN /30
           │         │          │          │
        srx01      srx02      srx03      srx04
         HUB       spoke      spoke      spoke
     192.168.1/24  .2/24      .3/24      .4/24   (LANs)

   AutoVPN: all spokes terminate on the hub's single st0.0.
```

| Element | Role |
|---------|------|
| Hub WAN (`untrust`) | IKE/IPsec endpoint + internet egress; PAT target |
| Hub LAN (`trust`) | Local hub subnet |
| Hub `st0.0` (`VPN`) | One bound tunnel interface for **all** spokes |
| Spoke WAN (`untrust`) | IKE/IPsec endpoint to the hub WAN IP |
| Spoke `st0.0` (`VPN`) | Single tunnel to the hub |
| Underlay | Any IP transport that lets each spoke WAN reach the hub WAN |

`st0` units are **unnumbered, point-to-point** (no `multipoint` keyword) —
required for traffic selectors. Management (`fxp0`) is out-of-band and never
carries tunnel traffic.

## AutoVPN Mechanics

- **IKEv2 / IPsec.** Phase 1: PSK, DH group 14, SHA-256, AES-256-CBC, `v2-only`.
  Phase 2: ESP, AES-256-GCM, PFS group 14, 3600 s. Clamp `tcp-mss ipsec-vpn 1350`
  to absorb ESP overhead.
- **Dynamic hub gateway.** `dynamic hostname <domain>` + `dynamic ike-user-type
  group-ike-id` makes the hub accept any spoke presenting an IKE ID under
  `*.<domain>`. Each spoke sets `local-identity hostname srxNN.<domain>` and pins
  the hub with `remote-identity hostname srx01.<domain>`.
- **Single bound tunnel.** Every spoke terminates on the hub's one `st0.0`; there
  is no per-spoke `st0` unit on the hub.
- **Auto Route Insertion (ARI).** When a spoke SA comes up, the hub
  automatically installs a route to that spoke's LAN `/24` via `st0.0` (protocol
  `ARI-TS`). The hub needs **no static routes to spoke LANs**.
- **Traffic selectors** define which source/destination prefixes each end carries
  — the lever full tunnel pulls.

> **Version constraint (field-verified): `ike-user-type` + IKEv2 + PSK does not
> commit on current Junos.** On vSRX3 24.4R1.9 and 25.4R1.12, pairing `dynamic
> ike-user-type` (**group-ike-id or shared-ike-id**) with `authentication-method
> pre-shared-keys` fails commit with:
> `When dynamic ike-user-type is configured, IKEv2 with authentication-method
> pre-shared-key is not allowed`. A zero-touch PSK AutoVPN hub cannot be built
> on these images. Pick the path **before** writing config:
>
> - **PSK** → drop `ike-user-type` entirely and configure **per-spoke IKEv2
>   gateways** on the hub, each pinned by a unique `remote-identity hostname
>   <spokeN>.<domain>`. Functionally the same full-tunnel hub-and-spoke
>   (field-verified with 6 spokes), but zero-touch is lost: adding a spoke
>   means adding a hub gateway/VPN/`st0` unit.
> - **Zero-touch `group-ike-id`** → use **certificate (PKI) authentication**.
>   See the `srx-advpn` skill's PKI-enrollment section for the workflow.
>
> The original reference lab (Junos 23.2R2) committed `group-ike-id` + PSK;
> treat that combination as legacy-image-only.

> **Auth: lab PSK vs. production PKI.** A single shared PSK keeps the focus on
> mechanics but is not production practice. In production prefer
> certificate-based (PKI) auth with per-device identity, or at minimum strong,
> unique PSKs in a secrets manager with rotation.

## Traffic Selectors — the core

Full tunnel is fundamentally a traffic-selector change: the spoke must *request*
the whole internet, and the hub must *accept* any destination.

| Selector | Split tunnel | Full-tunnel backhaul |
|----------|--------------|----------------------|
| Spoke `local-ip` | `192.168.x.0/24` (its LAN) | same |
| Spoke `remote-ip` | `192.168.1.0/24` (hub LAN only) | **the full IPv4 space — as two `/1` halves, see below** |
| Hub `local-ip` | `192.168.1.0/24` (hub LAN) | **`0.0.0.0/0`** |
| Hub `remote-ip` | `192.168.0.0/16` (spoke summary) | same |

**Commit blocker (field-verified on 24.4R1.9 / 25.4R1.12): the literal spoke
`remote-ip 0.0.0.0/0` is rejected when the gateway is pinned by a static
`address`** — the normal spoke case:
`Remote-ip 0.0.0.0/0 in traffic-selector is not supported when address is
configured under ike gateway`. Split the default into two halves that avoid
the literal `0.0.0.0/0` but cover the same space:

```
set security ipsec vpn SPOKE-VPN traffic-selector TS-LO local-ip 192.168.x.0/24 remote-ip 0.0.0.0/1
set security ipsec vpn SPOKE-VPN traffic-selector TS-HI local-ip 192.168.x.0/24 remote-ip 128.0.0.0/1
```

Both halves commit cleanly and bring up two child SAs per spoke.

Two facts that surprise people:

1. **Hub `local-ip 0.0.0.0/0` does NOT create a default route via `st0.0`.**
   The per-spoke `/24` the hub installs comes from the *other* selector axis:
   hub `remote-ip 192.168.0.0/16` narrowed by the spoke's `local-ip
   192.168.x.0/24` = the spoke's specific `/24`, and **ARI keys off that
   narrowed remote selector**, so the hub installs clean per-spoke `/24`
   routes. The broad axis (hub `local-ip 0.0.0.0/0` ∩ spoke `remote-ip`
   wildcard) never becomes a hub route.
2. **Spoke-to-spoke needs no extra selector config.** With hub `local-ip
   0.0.0.0/0`, the inbound SA from spoke A already accepts spoke B's subnet as a
   destination, and the outbound SA to spoke B already accepts spoke A as source.

### Hub `remote-ip`: specific supernet vs. `0.0.0.0/0` wildcard

This is a **different axis** from the `0.0.0.0/0` used on the spoke `remote-ip` /
hub `local-ip` above — do not conflate them. The hub `remote-ip` controls which
spoke prefixes the hub will accept (and, via ARI, which routes appear).

| | Supernet (`192.168.0.0/16`) | Wildcard (`0.0.0.0/0`) |
|---|---|---|
| Use when | Spoke LANs summarize cleanly | Spoke LANs discontiguous / unsummarizable |
| Hub-side guardrail | Yes — IKE rejects prefixes outside the summary | None — hub trusts every spoke |
| Zero-touch hub | Mostly (new out-of-summary LAN forces a widen) | Fully |
| Blast radius if a spoke is rogue | Contained | Large — a spoke could advertise the hub LAN or another site's prefix; ARI would install it (route hijack). (ARI never installs a `0.0.0.0/0` selector, so a rogue *default* is not the risk — rogue specifics are.) |

Default to the **supernet** whenever addressing permits; it keeps the guardrail.
Use the wildcard only when there is genuinely no summarizable scheme, and push the
guardrail to per-spoke security policy/filtering instead.

Two caveats regardless of choice:
- **Spokes must propose their specific `/24`, not `0.0.0.0/0`** — else the
  negotiated selector stays `0.0.0.0/0` and ARI has no specific prefix to install.
- **Overlapping spoke subnets are not solved by selectors** — that is a NAT
  problem (static/twice-NAT at the colliding spoke), not a VPN problem.

## Routing Changes

### Spoke

| | Split tunnel | Full-tunnel backhaul |
|---|---|---|
| Tunnel route | `192.168.1.0/24 → st0.0` | **`0.0.0.0/0 → st0.0`** (default into tunnel) |
| Hub WAN host route | `HUB_WAN/32 → <underlay nh>` | **same — and now CRITICAL** |
| WAN `/30` routes | via underlay | same |

> **Anti-recursion is the #1 gotcha of full tunnel.** The spoke default now
> points into `st0.0`, but the ESP packets that *carry* the tunnel are destined to
> the hub's WAN IP. If that traffic also followed the default into the tunnel you
> get infinite recursion and an instant black-hole. Keep the host route
> `HUB_WAN/32 → <underlay next-hop>` (and the connected WAN `/30`) **more-specific**
> than the new default.

### Hub

| | Split tunnel | Full-tunnel backhaul |
|---|---|---|
| WAN `/30` routes | via underlay | same |
| Spoke LAN routes | ARI `192.168.x.0/24 → st0.0` | same (ARI) |
| Default route | none | **add `0.0.0.0/0 → <WAN next-hop>`** (egress for de-encapsulated internet traffic) |

> **Caveat — competing management default (ECMP trap).** Many vSRX images carry a
> management default `0.0.0.0/0 → <mgmt-gw> via fxp0` in `inet.0`. Adding a second
> `0.0.0.0/0` does **not** override it — Junos installs both next-hops as **ECMP**,
> so half the traffic wrongly egresses `fxp0` and NAT / the `untrust` policy never
> applies. *Removing* the management default risks cutting OOB access.
> - **Production fix:** put `fxp0` in a dedicated **management routing-instance**
>   so `inet.0`'s default can legitimately point into the WAN/tunnel.
> - **Lab shortcut:** route the specific internet destination instead
>   (`<sim-internet>/32 → st0.0` on spoke, `<sim-internet>/32 → <WAN nh>` on hub),
>   plus `192.168.0.0/16 → st0.0` on each spoke for hub-LAN and spoke-to-spoke.
>   Being more-specific than the management default, these exercise the full data
>   path without disturbing management.

## Hub NAT and Security Policies

### Source NAT (internet egress only)

PAT spoke private sources to the hub's WAN egress IP so the upstream has an
address to return to. **Scope the rule-set `from zone VPN to zone untrust`** so it
matches only internet egress — spoke-to-spoke (`VPN → VPN`) and spoke-to-hub-LAN
(`VPN → trust`) never match and stay un-NAT'd, preserving real private IPs between
sites.

```
set security nat source rule-set VPN-BACKHAUL from zone VPN
set security nat source rule-set VPN-BACKHAUL to zone untrust
set security nat source rule-set VPN-BACKHAUL rule SNAT-INTERNET match source-address 192.168.0.0/16
set security nat source rule-set VPN-BACKHAUL rule SNAT-INTERNET match destination-address 0.0.0.0/0
set security nat source rule-set VPN-BACKHAUL rule SNAT-INTERNET then source-nat interface
```

> Hub-LAN hosts to the internet are `trust → untrust` and are **not** covered.
> Add a parallel `trust → untrust` source-NAT rule if the hub should also be the
> NAT egress for its own LAN.

### Security policies

| Policy | Split tunnel | Full-tunnel backhaul |
|--------|--------------|----------------------|
| `trust → untrust` | permit | same |
| `trust → VPN` | permit | same |
| `VPN → trust` | permit | same |
| `VPN → untrust` | — | **add permit** (spoke internet egress) |
| `VPN → VPN` | — | **add permit** (spoke-to-spoke hairpin) |

Return traffic for both NAT'd internet and inter-spoke flows is handled by the
stateful session table — no reverse policy needed. On the **spoke**, all LAN
egress now exits via zone `VPN` (`st0.0`), so the spoke's `trust → VPN` policy
must permit the **full backhaul scope** (`destination-address any` or the
intended backhauled prefixes) — a split-tunnel policy scoped to the hub LAN
would silently drop internet-bound traffic at the spoke. The spoke's
`trust → untrust` policy becomes dead (no local breakout) but is harmless to
leave.

## Config Skeleton (hub, `set` format)

PSK is a placeholder substituted at deploy time from a git-ignored secrets file —
never commit it.

```
# --- Tunnel interface (P2P, unnumbered) ---
set interfaces st0 unit 0 family inet

# --- IKE Phase 1 ---
set security ike proposal AUTOVPN-IKE-PROP authentication-method pre-shared-keys
set security ike proposal AUTOVPN-IKE-PROP dh-group group14
set security ike proposal AUTOVPN-IKE-PROP authentication-algorithm sha-256
set security ike proposal AUTOVPN-IKE-PROP encryption-algorithm aes-256-cbc
set security ike proposal AUTOVPN-IKE-PROP lifetime-seconds 86400
set security ike policy AUTOVPN-IKE-POL proposals AUTOVPN-IKE-PROP
set security ike policy AUTOVPN-IKE-POL pre-shared-key ascii-text "$AUTOVPN_PSK"
# Dynamic gateway — accepts any spoke whose IKE ID is *.homelab.local
# NOTE: on Junos 24.4R1+/25.4R1 the 'dynamic ike-user-type' line below + PSK
# will NOT commit — see the version-constraint callout (per-spoke gateways for
# PSK, or certificate auth for zero-touch group-ike-id).
set security ike gateway AUTOVPN-HUB-GW ike-policy AUTOVPN-IKE-POL
set security ike gateway AUTOVPN-HUB-GW dynamic hostname homelab.local
set security ike gateway AUTOVPN-HUB-GW dynamic ike-user-type group-ike-id
set security ike gateway AUTOVPN-HUB-GW dynamic reject-duplicate-connection
set security ike gateway AUTOVPN-HUB-GW local-identity hostname srx01.homelab.local
set security ike gateway AUTOVPN-HUB-GW external-interface ge-0/0/0.0
set security ike gateway AUTOVPN-HUB-GW version v2-only

# --- IPsec Phase 2 ---
set security ipsec proposal AUTOVPN-IPSEC-PROP protocol esp
set security ipsec proposal AUTOVPN-IPSEC-PROP encryption-algorithm aes-256-gcm
set security ipsec proposal AUTOVPN-IPSEC-PROP lifetime-seconds 3600
set security ipsec policy AUTOVPN-IPSEC-POL perfect-forward-secrecy keys group14
set security ipsec policy AUTOVPN-IPSEC-POL proposals AUTOVPN-IPSEC-PROP
set security ipsec vpn AUTOVPN-HUB bind-interface st0.0
set security ipsec vpn AUTOVPN-HUB ike gateway AUTOVPN-HUB-GW
set security ipsec vpn AUTOVPN-HUB ike ipsec-policy AUTOVPN-IPSEC-POL
# Full-tunnel selector: hub local-ip 0.0.0.0/0 accepts ANY destination from spokes
set security ipsec vpn AUTOVPN-HUB traffic-selector TS-ALL local-ip 0.0.0.0/0
set security ipsec vpn AUTOVPN-HUB traffic-selector TS-ALL remote-ip 192.168.0.0/16
set security flow tcp-mss ipsec-vpn mss 1350

# --- Zones (st0.0 in its own VPN zone) ---
set security zones security-zone untrust host-inbound-traffic system-services ike
set security zones security-zone untrust interfaces ge-0/0/0.0
set security zones security-zone trust interfaces ge-0/0/1.0
set security zones security-zone VPN host-inbound-traffic system-services ping
set security zones security-zone VPN interfaces st0.0

# --- Routing: ARI handles spoke LANs; add the egress default (see ECMP caveat) ---
set routing-options static route 0.0.0.0/0 next-hop 10.0.0.1
```

Spoke differs only in: `local-identity hostname srxNN.homelab.local`,
`remote-identity hostname srx01.homelab.local`, gateway `address <HUB_WAN>`,
the **two-half selector** `local-ip 192.168.x.0/24` + `remote-ip 0.0.0.0/1` /
`128.0.0.0/1` (the literal `0.0.0.0/0` fails commit with a static gateway
`address` — see Traffic Selectors), a default route `0.0.0.0/0 → st0.0`, **and
the anti-recursion host route `HUB_WAN/32 → <underlay next-hop>`**.

Two spoke prerequisites that are easy to miss (both field-verified):
- The spoke's `untrust` zone needs `host-inbound-traffic system-services ike`
  **even though the spoke initiates** — without it the NAT-T UDP-4500 return
  is dropped at host-inbound: IKE_SA_INIT (500) round-trips, then IKE_AUTH
  retransmits forever while the reply dies at the spoke's WAN zone.
- The spoke's `trust → VPN` policy must permit `destination-address any` (see
  Security policies above).

See `references/source-design-summary.md` for full per-device detail.

## Verification

```
show security ike security-associations            # one Phase 1 SA per spoke, UP
show security ipsec security-associations           # one Phase 2 SA per spoke, bound st0.0
show route 192.168.0.0/16                            # clean per-spoke /24s, protocol ARI-TS via st0.0
show security nat source rule all                    # SNAT-INTERNET hit count incrementing
show security flow session                           # spoke-src -> internet, xlated to hub WAN IP
show security nat source summary
show system core-dumps                               # must stay zero (data-plane stability)
```

Internet backhaul: from a spoke, `ping <sim-internet> source <spoke-LAN-gw>` —
hub session shows the source translated to the hub WAN IP.
Spoke-to-spoke: `ping <other-spoke-LAN> source <spoke-LAN-gw>` — hub session shows
`spokeA → spokeB` entering and leaving on `st0.0`, zone `VPN → VPN`, **no NAT**.

## Troubleshooting Matrix

| Stage | Symptom | Common causes |
|-------|---------|---------------|
| Commit | `ike-user-type ... pre-shared-key is not allowed` / `Remote-ip 0.0.0.0/0 ... not supported` | 24.4R1+ constraints — per-spoke gateways (PSK) or certs (`group-ike-id`); split the spoke selector into `0.0.0.0/1` + `128.0.0.0/1` |
| Underlay | Peers can't reach each other | Transport routing/filtering; verify `ping` between WAN IPs |
| Phase 1 (IKE) | No IKE SA / stuck | PSK mismatch, proposal/DH mismatch, wrong IKE identity (`group-ike-id` domain), IKEv1-vs-v2 mismatch |
| NAT-T (4500) | Hub shows tunnel UP, spoke retransmits IKE_AUTH forever | **Double NAT** (carrier PAT + hub-behind-static-NAT) drops the fragmented 4500 AUTH return — collapse to a single NAT hop (when the hub sits behind a 1:1 static NAT, don't also PAT the spokes' underlay) |
| NAT-T (4500) | Same symptom, single NAT hop; packets reach the spoke WAN but never iked | Spoke `untrust` zone missing `host-inbound-traffic system-services ike` — the 4500 return dies at host-inbound |
| Phase 2 (IPsec) | IKE up, no IPsec SA | IPsec proposal/PFS mismatch, traffic-selector mismatch |
| ARI routes | No per-spoke `/24` on hub | Spoke proposed `0.0.0.0/0` instead of its `/24`; hub `remote-ip` excludes the spoke LAN |
| Data plane | Tunnel up, no traffic | Missing spoke default into `st0`, `st0` in wrong zone, `VPN→untrust`/`VPN→VPN` policy missing |
| Internet egress | Spoke can't reach internet, NAT zero hits | **Management-default ECMP** stealing traffic out `fxp0`; NAT rule-set not `VPN→untrust` |
| Recursion | Tunnel flaps / black-hole | **Missing anti-recursion host route** `HUB_WAN/32` |
| Fragmentation | Large flows fail, small ones work | Tunnel MTU/MSS — keep/lower `tcp-mss ipsec-vpn` |

IKE tracing when an SA won't establish:
```
set security ike traceoptions file ike-trace
set security ike traceoptions flag ike
set security ike traceoptions level 15
```
Read with `show log ike-trace`; force renegotiation with `clear security ike
security-associations` / `clear security ipsec security-associations`.
(iked-based platforms take a numeric trace level; word levels like `level
detail` fail commit on Junos 24.4R1 — live-verified.) Live daemon
log is `show log iked` on modern (iked) platforms, `show log kmd` on older (kmd).

## Caveats and Tradeoffs

1. **Anti-recursion route** — the single most common break (see Routing Changes).
2. **No local breakout** — all spoke internet traffic concentrates on the hub's
   WAN, CPU (encrypt/decrypt), and NAT table. This is the central capacity-planning
   decision; the upside is centralized inspection/logging.
3. **MTU / MSS** — backhauling large flows over ESP plus NAT makes fragmentation
   likely; keep the MSS clamp, lower it if PMTU issues appear.
4. **Scale** — per platform, AutoVPN with traffic selectors scales to thousands of
   tunnels; approaching limits, go **dual-hub** to remove the single point of
   failure and distribute load.
5. **`0.0.0.0/0` selector — use with a caveat.** Full tunnel needs a wildcard to
   pull all destinations up the tunnel (there is no supernet for "the entire
   internet"). Juniper's traffic-selector docs caution that a `remote-ip` of
   `0.0.0.0/0` for site-to-site selectors is not formally supported, and on
   24.4R1+/25.4R1 the literal wildcard is a **hard commit error** when the
   gateway has a static `address` — use the `0.0.0.0/1` + `128.0.0.0/1` split
   (see Traffic Selectors). Also, **ARI does not install a route for a
   `0.0.0.0/0` selector**. This design does not rely on ARI for that direction:
   the spoke reaches everything via a static `0.0.0.0/0 → st0.0` default route,
   and ARI installs only the hub-side per-spoke `/24` routes (keyed on the
   spoke's specific `local-ip`, not the wildcard). Validate on your target
   release/platform and confirm with JTAC for production.

## Choose This vs. Static Hub-Spoke

| | **AutoVPN full-tunnel (this skill)** | Static P2P hub-spoke (`srx-ipsec-hub-spoke`) |
|---|---|---|
| Hub gateways | One dynamic `group-ike-id` gateway | One static gateway per spoke (by IP) |
| Hub tunnel interfaces | Single shared `st0.0` | One `st0` unit per spoke |
| Hub → spoke-LAN routes | Auto Route Insertion (`ARI-TS`) | Static, one per spoke |
| Add a new spoke | **Zero hub change** | Hub change: +gateway +VPN +`st0` +route |
| Best for | Many or churning sites | A few small, stable, explicit sites |

Backhaul behavior, NAT, anti-recursion, and the management-default caveat are
**identical** between the two. Pick AutoVPN when spoke count grows or churns; pick
static when you want every tunnel spelled out in config.

If the problem is spoke-to-spoke hairpin latency rather than hub config churn,
compare `srx-advpn` (see its three-way ADVPN vs AutoVPN vs Static table).

## Verification Checklist

- [ ] `st0` units are point-to-point (no `multipoint`) — required for selectors
- [ ] Auth path matches the image: certs for `group-ike-id`, or per-spoke gateways for PSK (24.4R1+ rejects `ike-user-type` + IKEv2 + PSK)
- [ ] Hub `local-ip 0.0.0.0/0`; spoke `remote-ip` as `0.0.0.0/1` + `128.0.0.0/1`; hub `remote-ip` is the spoke summary (or wildcard with policy guardrails)
- [ ] Hub shows one IKE SA per spoke (and two child SAs per spoke with the split selector) plus clean per-spoke `ARI-TS` `/24` routes
- [ ] Spoke has `0.0.0.0/0 → st0.0` AND the anti-recursion `HUB_WAN/32` host route
- [ ] Spoke `untrust` zone permits `system-services ike`; spoke `trust → VPN` policy permits destination any
- [ ] Hub egress default does not ECMP with a management default (management in its own routing-instance, or use specific routes)
- [ ] Source-NAT rule-set is `VPN → untrust` only; `VPN→untrust` and `VPN→VPN` policies permit
- [ ] `show system core-dumps` is zero

## Source Notes

This original playbook was inspired by Jason Anderson's attributed
`srx-autovpn-backhaul-public` lab and checked against Juniper Junos
IPsec/AutoVPN documentation. The upstream lab has no explicit license and is
not included or relicensed here. See `references/source-index.md` and the
independently written `references/source-design-summary.md`.

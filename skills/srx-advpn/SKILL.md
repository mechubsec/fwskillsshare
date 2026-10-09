---
name: srx-advpn
description: Design, configure, audit, and troubleshoot Juniper SRX ADVPN spoke-to-spoke IPsec shortcuts. Use when handling suggester or partner roles, multipoint st0, OSPF p2mp, certificates, PKI, shortcut lifecycle, or “No public key found” IKE_AUTH failures. Use AutoVPN for hub backhaul and static IPsec for small fixed estates.
version: 1.1.5
author:
  - fastrevmd-lab
  - Claude
  - GPT
license: MIT
metadata:
  hermes:
    tags: [srx, junos, advpn, auto-discovery-vpn, ipsec, vpn, spoke-to-spoke, shortcut, dynamic-mesh, suggester, partner, multipoint, st0, ospf, p2mp, dynamic-neighbors, pki, certificates, ikev2]
    related_skills: [srx-autovpn-full-tunnel, srx-ipsec-hub-spoke, srx-nat, srx-mnha, srx-policy, parsing-srx-configs]
  sources:
    - title: Auto Discovery VPNs | Junos OS
      author: Juniper Networks
      url: https://www.juniper.net/documentation/us/en/software/junos/vpn-ipsec/topics/topic-map/security-auto-discovery-vpns.html
      retrieved: "2026-07-02"
    - title: IPsec VPN User Guide | Junos OS
      author: Juniper Networks
      url: https://www.juniper.net/documentation/us/en/software/junos/vpn-ipsec/index.html
      retrieved: "2026-07-02"
    - title: "Field report: 12-branch vSRX3 lab (6 AutoVPN + 6 ADVPN), Junos 24.4R1.9 / 25.4R1.12"
      author: community field report (upstream fwskillsshare issue #4)
      url: https://github.com/mechubsec/fwskillsshare/issues/4
      retrieved: "2026-07-02"
---

# SRX Auto Discovery VPN (ADVPN)

## Contents

- [Overview](#overview)
- [Runtime intake](#runtime-intake)
- [Scope and routing](#scope-and-routing)
- [Roles and the Shortcut Lifecycle](#roles-and-the-shortcut-lifecycle)
- [The Multipoint st0 Overlay](#the-multipoint-st0-overlay)
- [Routing over the Overlay (OSPF p2mp)](#routing-over-the-overlay-ospf-p2mp)
- [PKI Enrollment](#pki-enrollment)
- [Config Skeleton (`set` format)](#config-skeleton-set-format)
- [Verification](#verification)
- [Troubleshooting Matrix](#troubleshooting-matrix)
- [Choose ADVPN vs AutoVPN vs Static](#choose-advpn-vs-autovpn-vs-static)
- [Verification Checklist](#verification-checklist)
- [Source Notes](#source-notes)

## Overview

ADVPN is hub-and-spoke IPsec that **discovers spoke-to-spoke traffic and builds
direct shortcut tunnels at runtime**. The hub (the *suggester*) notices two
spokes (*partners*) exchanging traffic through it, introduces them to each
other over an IKEv2 extension, and the partners negotiate a direct IKE/IPsec
shortcut. A dynamic routing protocol running over the overlay (typically OSPF)
then reconverges so branch↔branch traffic takes the shortcut instead of
hairpinning through the hub. Idle shortcuts tear down and traffic falls back to
the hub path.

Core principle: **the hub brokers introductions; routing — not selectors —
steers traffic onto shortcuts.** That drives every design difference from
plain AutoVPN: a **multipoint numbered `st0`**, a **routing protocol over the
overlay**, and **certificate authentication**.

> **Certificates are effectively mandatory.** On current Junos (field-verified
> on vSRX3 24.4R1.9 and 25.4R1.12), IKEv2 with `authentication-method
> pre-shared-keys` **fails commit** whenever `dynamic ike-user-type`
> (group-ike-id or shared-ike-id) is configured:
> `When dynamic ike-user-type is configured, IKEv2 with authentication-method
> pre-shared-key is not allowed`. ADVPN's group model therefore requires
> RSA/ECDSA certificate auth. Plan PKI first — do not burn a day on a PSK
> ADVPN that cannot commit.
>
> Lab-observed (vSRX3 24.4R1.9, 25.4R1.12), **not in Juniper documentation**: Juniper's [IPsec VPN Configuration Overview](https://www.juniper.net/documentation/us/en/software/junos/vpn-ipsec/topics/topic-map/security-ipsec-vpn-configuration-overview.html) still documents `ike-user-type group-ike-id` / `shared-ike-id` for AutoVPN without this restriction (page checked 2026-10-09). Treat the commit error below as device behavior, not a documented limit; re-test on your release.

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

Use ADVPN when direct branch-to-branch traffic justifies dynamic shortcuts and PKI is available. Use `srx-autovpn-full-tunnel` when central inspection or hub hairpinning is required, and `srx-ipsec-hub-spoke` for a small stable estate.

## Roles and the Shortcut Lifecycle

| Role | Where | Config |
|------|-------|--------|
| **Suggester** | Hub | `set security ike gateway <gw> advpn partner disable` (suggests only, never a shortcut endpoint) |
| **Partner** | Spokes | `set security ike gateway <gw> advpn suggester disable` (accepts suggestions, forms shortcuts) |

Lifecycle:
1. **Via hub.** Spoke A → hub → spoke B; OSPF routes over the overlay all point
   at the hub.
2. **Suggestion.** The suggester sees A↔B flows transiting and sends both
   partners a *shortcut suggestion* (IKEv2 notification) carrying each other's
   tunnel endpoint and identity.
3. **Shortcut establishment.** One partner initiates a direct IKEv2 SA to the
   other, authenticated with the same certificates as the hub tunnel. A
   shortcut IPsec SA comes up on the **same multipoint `st0` unit**.
4. **Reconvergence.** OSPF forms a direct adjacency over the shortcut; the
   partner's LAN routes now resolve via the shortcut next-hop, and traffic
   leaves the hub path.
5. **Teardown.** When the shortcut idles below the threshold for `idle-time`
   seconds, partners tear it down and routes fall back to the hub.

Partner-side tuning knobs (under `advpn partner`): `idle-time <seconds>`
(teardown timer), `idle-threshold <pps>` (rate below which the shortcut counts
as idle), `connection-limit <n>` (max concurrent shortcuts a partner will
hold).

## The Multipoint st0 Overlay

Unlike AutoVPN-with-traffic-selectors (point-to-point unnumbered `st0`), ADVPN
uses **one numbered, multipoint `st0` unit per node** on a shared overlay
subnet — shortcuts attach to the same unit at runtime:

```
set interfaces st0 unit 1 multipoint
set interfaces st0 unit 1 family inet address 10.255.0.11/24
```

- One overlay subnet (e.g. `10.255.0.0/24`), one address per node.
- Traffic selectors are **not** used — routing over the overlay decides what
  enters the tunnel. Do not configure `traffic-selector` on the ADVPN VPN.
- Put the `st0.1` unit in its own zone (e.g. `VPN`) with `host-inbound-traffic
  protocols ospf` so overlay adjacencies can form.

## Routing over the Overlay (OSPF p2mp)

Static routes cannot model tunnels that appear and disappear at runtime — a
dynamic protocol is required. The standard pattern is OSPF point-to-multipoint
with dynamic neighbors:

```
set protocols ospf area 0.0.0.0 interface st0.1 interface-type p2mp
set protocols ospf area 0.0.0.0 interface st0.1 dynamic-neighbors
set protocols ospf area 0.0.0.0 interface st0.1 flood-reduction
set protocols ospf area 0.0.0.0 interface <LAN-ifl> passive
```

- **`interface-type p2mp`** — the overlay is one subnet but not broadcast;
  p2mp advertises host routes to each neighbor rather than electing a DR.
- **`dynamic-neighbors`** — adjacencies form with peers discovered on the
  interface at runtime (shortcut partners) without listing neighbors.
- **`flood-reduction`** — suppresses periodic LSA refresh flooding over the
  overlay; worthwhile once shortcut count grows.
- Advertise each site's LAN into OSPF (passive interface or export policy).
- For full-tunnel-style centralized egress, originate the default from the hub
  with an OSPF export policy injecting `0.0.0.0/0` (area 0 cannot be a
  stub/NSSA, so `default-metric` does not apply here); keep the
  **anti-recursion host route** to the hub/partner WAN IPs more specific than
  any default that points into `st0` (same trap as
  `srx-autovpn-full-tunnel`).

When a shortcut forms, the two partners' OSPF cost to each other drops from
two overlay hops (via hub) to one, so the shortcut wins automatically — no
metric engineering needed for the basic case.

## PKI Enrollment

Minimum viable lab PKI (per node):

```
set security pki ca-profile LAB-CA ca-identity LAB-CA
# lab only — use CRL/OCSP revocation checking in production
set security pki ca-profile LAB-CA revocation-check disable

request security pki generate-key-pair certificate-id ADVPN-CERT size 2048 type rsa
request security pki generate-certificate-request certificate-id ADVPN-CERT subject CN=spoke11.homelab.local domain-name spoke11.homelab.local filename spoke11.csr
# sign the CSR on the CA, then:
request security pki ca-certificate load ca-profile LAB-CA filename ca.pem
request security pki local-certificate load certificate-id ADVPN-CERT filename spoke11.pem
request security pki local-certificate verify certificate-id ADVPN-CERT
```

> **Chassis-cluster gotcha (field-verified).** `request security pki
> local-certificate load` executes on the **RG0-primary node**. If the keypair
> was generated on the *other* node (e.g. after a failover), the load fails
> with `error load certid<...>` — and cross-node PKI HA-sync may not populate
> (`pkid_handle_hasync_files: no files` in pki-trace). Fix: `request chassis
> cluster failover redundancy-group 0 node <keypair-node>` so the keypair and
> the load land on the same RE, then load.

## Config Skeleton (`set` format)

Hub (suggester) — spokes differ only where noted:

```
# --- Multipoint tunnel interface, numbered overlay ---
set interfaces st0 unit 1 multipoint
set interfaces st0 unit 1 family inet address 10.255.0.1/24        # spoke: .11, .12, ...

# --- IKE Phase 1: certificates, IKEv2 ---
set security ike proposal ADVPN-IKE-PROP authentication-method rsa-signatures
set security ike proposal ADVPN-IKE-PROP dh-group group14
set security ike proposal ADVPN-IKE-PROP authentication-algorithm sha-256
set security ike proposal ADVPN-IKE-PROP encryption-algorithm aes-256-cbc
set security ike policy ADVPN-IKE-POL proposals ADVPN-IKE-PROP
set security ike policy ADVPN-IKE-POL certificate local-certificate ADVPN-CERT
set security ike policy ADVPN-IKE-POL certificate trusted-ca LAB-CA

# Hub gateway: dynamic, accepts any cert under the domain, suggester role
set security ike gateway ADVPN-HUB-GW ike-policy ADVPN-IKE-POL
set security ike gateway ADVPN-HUB-GW dynamic hostname homelab.local
set security ike gateway ADVPN-HUB-GW dynamic ike-user-type group-ike-id
set security ike gateway ADVPN-HUB-GW local-identity distinguished-name
set security ike gateway ADVPN-HUB-GW external-interface ge-0/0/0.0
set security ike gateway ADVPN-HUB-GW version v2-only
set security ike gateway ADVPN-HUB-GW advpn partner disable          # hub = suggester only

# Spoke gateway instead: address <HUB_WAN>, local-identity hostname spokeNN.homelab.local,
#   advpn suggester disable, and optionally:
# set security ike gateway ADVPN-SPOKE-GW advpn partner idle-time 300

# --- IPsec Phase 2: bound to the multipoint st0.1, NO traffic selectors ---
set security ipsec proposal ADVPN-IPSEC-PROP protocol esp
set security ipsec proposal ADVPN-IPSEC-PROP encryption-algorithm aes-256-gcm
set security ipsec policy ADVPN-IPSEC-POL perfect-forward-secrecy keys group14
set security ipsec policy ADVPN-IPSEC-POL proposals ADVPN-IPSEC-PROP
set security ipsec vpn ADVPN-VPN bind-interface st0.1
set security ipsec vpn ADVPN-VPN ike gateway ADVPN-HUB-GW
set security ipsec vpn ADVPN-VPN ike ipsec-policy ADVPN-IPSEC-POL
set security ipsec vpn ADVPN-VPN establish-tunnels immediately        # spoke side
set security flow tcp-mss ipsec-vpn mss 1350

# --- Zones ---
set security zones security-zone untrust host-inbound-traffic system-services ike
set security zones security-zone untrust interfaces ge-0/0/0.0
set security zones security-zone VPN host-inbound-traffic protocols ospf
set security zones security-zone VPN host-inbound-traffic system-services ping
set security zones security-zone VPN interfaces st0.1

# --- OSPF over the overlay ---
set protocols ospf area 0.0.0.0 interface st0.1 interface-type p2mp
set protocols ospf area 0.0.0.0 interface st0.1 dynamic-neighbors
set protocols ospf area 0.0.0.0 interface st0.1 flood-reduction
set protocols ospf area 0.0.0.0 interface ge-0/0/1.0 passive          # site LAN
```

Spoke prerequisites that are easy to miss (both field-verified on the AutoVPN
sibling and equally applicable here):
- **`untrust` needs `host-inbound-traffic system-services ike`** even on the
  initiator — without it the NAT-T port-4500 return is dropped at
  host-inbound and IKE_AUTH retransmits forever.
- The **anti-recursion host route** to the hub WAN (and, with shortcuts, the
  underlay path to partner WANs) must stay more specific than any default
  pointing into `st0`.

## Verification

```
show security ike security-associations              # hub tunnel + shortcut SAs
show security ike active-peer                        # all partners registered on the hub
show security ipsec security-associations            # shortcut SAs appear alongside the hub SA
show security ipsec security-associations detail     # look for the ADVPN/shortcut flag per SA
show ospf neighbor                                   # hub adjacency + per-shortcut adjacencies
show route <remote-branch-LAN>                       # next-hop moves from hub overlay IP to partner overlay IP
```

Prove the shortcut path end-to-end: start a spoke-A↔spoke-B flow, confirm a
new IKE SA between the two spoke WAN IPs, then `traceroute` (or compare
`show security flow session` on the hub — the A↔B session should disappear
from the hub once the shortcut carries it).

## Troubleshooting Matrix

| Stage | Symptom | Cause / fix |
|-------|---------|-------------|
| Commit | `IKEv2 with authentication-method pre-shared-key is not allowed` | PSK + `dynamic ike-user-type` is rejected (lab-observed 24.4R1/25.4R1, not in Juniper documentation) — use certificate auth; there is no PSK ADVPN on these images |
| IKE_AUTH | Hub logs `ikev2_reply_cb_public_key: Error: No public key found` → `N(AUTHENTICATION_FAILED)` to every spoke | **Root-caused on vSRX3**: the *dynamic* `distinguished-name` / `group-ike-id` gateway responder path never hands the peer CERT to pkid. Use per-spoke static-address cert gateways on the hub. See below. |
| NAT-T | IKE_SA_INIT (500) completes; 4500 IKE_AUTH retransmits forever, responder side shows UP | Double NAT in the underlay (carrier PAT + hub-behind-static-NAT) drops the 4500 return — collapse to a single NAT hop |
| NAT-T | Same 4500-retransmit symptom, single NAT | Initiator's `untrust` zone missing `host-inbound-traffic system-services ike` |
| Shortcut | Hub tunnel up, spokes reach each other only via hub, no shortcut SA | Roles wrong (`advpn suggester/partner disable` on the wrong end), partner `connection-limit` reached, or suggester never sees transit traffic (flows not crossing the hub st0) |
| Shortcut | Shortcut forms, traffic still via hub | OSPF not running over `st0.1` (`dynamic-neighbors` missing, zone blocks `protocols ospf`), or LAN routes not advertised |
| Shortcut | Shortcuts flap | `idle-time`/`idle-threshold` too aggressive for the traffic profile |
| PKI (cluster) | `error load certid<...>` loading a cert | Keypair on the non-RG0-primary node — fail RG0 over to that node, then load |
| Fragmentation | Small flows work, large fail | ESP overhead — keep `tcp-mss ipsec-vpn 1350`, lower on PMTU issues |

IKE tracing when reproducing the failures below (live-verified on vSRX 24.4R1 —
`level` is numeric on iked platforms):
```
set security ike traceoptions file ike-trace
set security ike traceoptions flag ike
set security ike traceoptions level 15
```
Read with `show log iked` (and `show log pki-trace` for pkid activity).

### Root cause: `No public key found` is specific to the *dynamic* cert gateway (vSRX3 24.4R1 / 25.4R1)

**Symptom.** The hub (responder) rejects **every** spoke cert at
`ikev2_state_auth_responder_in_verify_signature` with
`ikev2_reply_cb_public_key: Error: No public key found`, then sends
`N(AUTHENTICATION_FAILED)`. IKE_SA_INIT completes; the fragmented IKE_AUTH is
received and decoded (the CERT payload is present and decodes fine).

**Root cause (isolated on a live vSRX3 by comparing iked traces of a failing
vs a working tunnel on the same box).** The failure is **not** in the
certificates, CA, EKU, clock, Junos version, or PKI — a plain IKEv2
certificate VPN pinned by a **static `address` gateway** authenticates and
comes up **on the exact same image, certs, CA-profile, and proposals**. The
break is in the iked responder path taken by a **dynamic gateway** (`dynamic
distinguished-name` / `dynamic ike-user-type group-ike-id`):

- **Static-address gateway path (works):** after the ID matches, iked calls
  `iked_policy_public_key` → `ssh_policy_find_public_key_send_ipc` → hands the
  received CERT to pkid over IPC (`IKED-PKID-IPC 1 cert, len1<917>`), pkid
  returns the key, `ssh_cm_cert_get_x509` succeeds, and
  `ikev2_state_auth_verify_cb: Signature verification ok`.
- **Dynamic-gateway path (fails):** after the same `Container identity matched`
  / `id based lookup found: Sa_cfg:ADVPN-HUB`, iked goes down the
  `iked_pm_ike_public_key look up sa_cfg based on ike-id for main-mode dialup`
  branch and returns `No public key found` **without ever calling
  `send_ipc`** — the peer CERT is never handed to pkid. That is exactly why
  `show log pki-trace` shows pkid is never consulted at IKE time.

This is an **iked-internal defect in the dynamic-gateway cert-auth responder on
vSRX3** for these releases, not a misconfiguration. Ruled out along the way (so
you don't repeat them): Junos version (identical on 24.4R1.9 and 25.4R1.12);
cert chain (`openssl verify` and on-device `request security pki
local-certificate verify` pass on every node); clock skew; EKU (id-kp-ipsecIKE
`1.3.6.1.5.5.7.3.17` + serverAuth + clientAuth); `trusted-ca use-all` vs
explicit profile; `revocation-check disable`; `restart pki-service` /
`restart ipsec-key-management`; `peer-certificate-type x509-signature`;
`dynamic distinguished-name wildcard` vs `container`.

> **Separate latent bug worth fixing regardless:** on this hub the dynamic
> gateway's `get_cas` returned **0 CAs** (`ikev2_reply_cb_get_cas: Got 0 CAs`)
> — iked had no trust anchor to advertise — because the CA cert had been loaded
> only into pkid's store, not re-fed to iked. `request security pki
> ca-certificate load ca-profile <p> filename <ca.pem>` (from a real
> **PEM** file — the RPC cannot read Junos's internal `/usr/share/ui/support`
> copies) followed by `restart ipsec-key-management` fixes the CA advertisement.
> It does **not** fix the dynamic-gateway path above, but you want it fixed
> before diagnosing anything cert-related.

**Working fix / recommendation.** Terminate spokes on the hub with **per-spoke
static-address certificate gateways** (`set security ike gateway <GW> address
<spoke-WAN>` + `remote-identity distinguished-name container O=<org>`), the
same shape this skill already recommends for PSK on 24.4R1+. This costs
zero-touch (one hub gateway/VPN/`st0` unit per spoke) but the certificate
responder path works. True zero-touch ADVPN with a dynamic group gateway needs
either a fixed Junos release or a JTAC-supplied knob; open a JTAC case with the
paired failing/working iked traces (the `send_ipc`-vs-no-`send_ipc` divergence
is the actionable evidence).

## Choose ADVPN vs AutoVPN vs Static

| | **ADVPN (this skill)** | AutoVPN full-tunnel | Static P2P hub-spoke |
|---|---|---|---|
| Spoke↔spoke path | Direct shortcut after introduction | Hairpin via hub | Hairpin via hub |
| Hub tunnel interface | Multipoint numbered `st0` | Single P2P unnumbered `st0.0` | One `st0` unit per spoke |
| Routing | OSPF (p2mp, dynamic-neighbors) over overlay | ARI + statics | Manual statics |
| Auth | **Certificates (required)** | PSK possible (per-spoke gateways) or certs | PSK or certs |
| Add a spoke | Zero hub change (enroll cert) | Zero hub change (cert) / one gateway (PSK) | Hub change per spoke |
| Best for | Meshy branch↔branch traffic at scale | Centralized egress/inspection | Few stable sites |

Centralized-egress backhaul and ADVPN compose: originate the default from the
hub into OSPF and shortcuts still form for branch↔branch flows.

## Verification Checklist

- [ ] `st0` unit is `multipoint` with a numbered overlay address (no `traffic-selector` on the VPN)
- [ ] Certificate auth end-to-end: `request security pki local-certificate verify` passes on every node
- [ ] Hub gateway has `advpn partner disable`; every spoke gateway has `advpn suggester disable`
- [ ] VPN zone permits `protocols ospf`; `untrust` permits `system-services ike` on every node
- [ ] OSPF on `st0.1`: `interface-type p2mp` + `dynamic-neighbors`; each site LAN advertised
- [ ] Anti-recursion host routes to hub (and partner) WAN IPs more specific than any default into `st0`
- [ ] Shortcut proof: new IKE SA between spoke WAN IPs and the A<->B session gone from the hub flow table
- [ ] On vSRX3 24.4R1/25.4R1 hubs: per-spoke static-address cert gateways (dynamic cert gateway hits 'No public key found')

## Source Notes

Mechanics summarized from Juniper's Auto Discovery VPN documentation. The
certificate-requirement commit error, chassis-cluster PKI gotcha, NAT-T
double-NAT and host-inbound findings, and the open `No public key found`
blocker are field data from a 12-branch vSRX3 lab build (Junos 24.4R1.9 /
25.4R1.12) contributed via
[upstream fwskillsshare issue #4](https://github.com/mechubsec/fwskillsshare/issues/4).
See `references/field-notes-vsrx-advpn-lab.md`.

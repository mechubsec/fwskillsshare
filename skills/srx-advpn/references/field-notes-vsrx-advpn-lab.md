# Field Notes — 12-branch vSRX3 lab: 6 AutoVPN + 6 ADVPN branches

## Contents

- [Baseline that worked](#baseline-that-worked)
- [NAT-T findings (apply to ADVPN and AutoVPN alike)](#nat-t-findings-apply-to-advpn-and-autovpn-alike)
- [ADVPN state: PKI-enrolled, blocked at IKE cert auth](#advpn-state-pki-enrolled-blocked-at-ike-cert-auth)

Source: community field report, [upstream fwskillsshare issue #4](https://github.com/mechubsec/fwskillsshare/issues/4) (2026-07-02).
Environment: vSRX3, Junos 24.4R1.9 and 25.4R1.12, hub as chassis cluster behind
1:1 static NAT, simulated dual-ISP underlay, IKEv2.

## Baseline that worked

The 6 hub-and-spoke branches (per `srx-autovpn-full-tunnel`, adapted) came up
cleanly with full-tunnel backhaul once two commit-blockers were worked around:

1. **`dynamic ike-user-type group-ike-id` + IKEv2 + PSK fails commit** on
   24.4R1.9 / 25.4R1.12:
   ```
   When dynamic ike-user-type is configured, IKEv2 with authentication-method pre-shared-key is not allowed
   ```
   This also blocks `shared-ike-id`. Lab-observed, not in Juniper documentation:
   Juniper's IPsec VPN Configuration Overview still documents `ike-user-type
   group-ike-id` / `shared-ike-id` for AutoVPN without this restriction
   (https://www.juniper.net/documentation/us/en/software/junos/vpn-ipsec/topics/topic-map/security-ipsec-vpn-configuration-overview.html, checked 2026-10-09). Working PSK alternative: per-spoke IKEv2
   gateways on the hub, each pinned by unique `remote-identity hostname
   <spokeN>`, no `ike-user-type`. Verified with 6 spokes. Consequence for
   ADVPN: the group model requires certificate auth.

2. **Traffic-selector `remote-ip 0.0.0.0/0` fails commit** when the spoke
   gateway has a static `address`:
   ```
   Remote-ip 0.0.0.0/0 in traffic-selector is not supported when address is configured under ike gateway
   ```
   Working split (both halves commit and bring up two child SAs):
   ```
   set security ipsec vpn <vpn> traffic-selector TS-LO local-ip <LAN>/24 remote-ip 0.0.0.0/1
   set security ipsec vpn <vpn> traffic-selector TS-HI local-ip <LAN>/24 remote-ip 128.0.0.0/1
   ```

## NAT-T findings (apply to ADVPN and AutoVPN alike)

- **Double NAT kills the 4500 float.** Spoke → carrier PAT → edge 1:1
  static-NAT → hub: IKE_SA_INIT (UDP 500) survives, but the fragmented
  IKE_AUTH **response** on UDP 4500 never returns through the stacked NATs.
  Hub completes as responder (shows UP); spoke retransmits forever. Fix:
  collapse to a single NAT hop (remove the underlay PAT; keep only the 1:1
  static NAT for the hub).
- **Initiator still needs `host-inbound-traffic system-services ike`** on its
  WAN/untrust zone, or the 4500 return is dropped at host-inbound. Proven by
  upstream session counters showing packets arriving at the spoke WAN and
  dying at the zone.

## ADVPN state: PKI-enrolled, blocked at IKE cert auth

**Blocker — `No public key found` at IKE_AUTH — ROOT-CAUSED 2026-07-03:**
- Hub (responder) rejects every spoke cert: iked hits
  `ikev2_reply_cb_public_key: Error: No public key found` and sends
  `N(AUTHENTICATION_FAILED)`. IKE_SA_INIT completes; the fragmented IKE_AUTH
  is received; failure is at `ikev2_state_auth_responder_in_verify_signature`.

- **Root cause (isolated by trace diff on the live hub, DC cluster test19-20).**
  The break is specific to the **dynamic** gateway (`dynamic
  distinguished-name` / `dynamic ike-user-type group-ike-id`), NOT the certs.
  Decisive test: a plain IKEv2 cert VPN pinned by a **static `address`
  gateway**, using the *same* `advpn-spoke` cert, the *same* LAB-CA, and the
  *same* `ADVPN-IKE-PROP` proposal, **comes up and passes signature
  verification** on the identical image. Proven three ways on 2026-07-03:
  - spoke↔spoke static cert VPN BR-07↔BR-08 (test16↔test12): UP.
  - hub→BR-07 **static-address** cert gateway (`CDX-STATIC-BR07`, reth0.0,
    remote-identity container O=example.org): **UP** (tunnel 131080, port 4500).
  - the real dynamic `ADVPN-HUB-GW`: still `No public key found`, same run.
- **The iked path divergence (the actionable evidence for JTAC):**
  - Static-gateway responder (works): `iked_policy_public_key` →
    `ssh_policy_find_public_key_send_ipc` → `IKED-PKID-IPC 1 cert, len1<917>`
    → pkid returns key → `ssh_cm_cert_get_x509` → `Signature verification ok`.
  - Dynamic-gateway responder (fails): after the identical
    `Container identity matched (O=example.org)` /
    `id based lookup found: Sa_cfg:ADVPN-HUB`, iked takes the
    `iked_pm_ike_public_key look up sa_cfg based on ike-id for main-mode dialup`
    branch and returns `No public key found` **without ever calling
    `send_ipc`** — the received CERT is never handed to pkid. That is exactly
    why `show log pki-trace` shows pkid is never consulted at IKE time.
- Ruled out (all tested): Junos version (24.4R1.9 = 25.4R1.12); cert chain
  (`openssl verify` + on-device verify pass on every node); clock skew; EKU
  (id-kp-ipsecIKE `1.3.6.1.5.5.7.3.17` + serverAuth + clientAuth); `trusted-ca
  use-all` vs explicit; `revocation-check disable`; `restart pki-service` +
  `restart ipsec-key-management`; `peer-certificate-type x509-signature`;
  `dynamic distinguished-name wildcard` vs `container`.
- **Separate latent bug found + fixed:** the dynamic gateway's `get_cas`
  returned `Got 0 CAs` — iked had no trust anchor to advertise. The CA cert had
  been loaded only into pkid's lhash, not re-fed to iked. Fixed with `request
  security pki ca-certificate load ca-profile LAB-CA filename /var/tmp/ca.pem`
  (must be a real **PEM** file — the RPC returns "cannot read / corrupted" for
  the internal `/usr/share/ui/support/LAB-CA-ca1.cert` copy) + `restart
  ipsec-key-management`. Does not fix the dynamic-gateway path.
- **Fix / recommendation:** terminate spokes with **per-spoke static-address
  cert gateways** on the hub (loses zero-touch, one gateway/VPN/`st0` unit per
  spoke, but the cert responder path works). Zero-touch dynamic-group ADVPN
  needs a fixed Junos release or a JTAC knob — file with the paired
  failing/working iked traces.
- **Lab left at documented broken baseline** after this session: all debug
  objects (`CDX-STATIC-BR07`, `CDX-ISO-*`, extra traceoptions/pki-trace,
  `peer-certificate-type`, the temporary `container` DN) reverted; the CA-cert
  load + `trusted-ca use-all` on the hub were kept (correct fixes). Group A
  (BR-01..06) stayed UP throughout; cluster clean, node0 primary both RGs.

**Chassis-cluster PKI gotcha (solved):** on a cluster,
`request security pki local-certificate load` runs on the **RG0-primary
node**. If the keypair was generated on the other node (e.g. after a
failover), load fails with `error load certid<...>`. Cross-node PKI HA-sync
appeared not to populate (`pkid_handle_hasync_files: no files`). Fix:
`request chassis cluster failover redundancy-group 0 node <keypair-node>` so
keypair and load land on the same RE, then load.

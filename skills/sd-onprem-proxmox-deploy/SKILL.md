---
name: sd-onprem-proxmox-deploy
description: Deploy and validate Juniper Security Director On-Prem 25/26 as a Proxmox VE KVM guest. Use when planning, installing, rebuilding, validating network connectivity or first-boot seed data, and onboarding SRX/Junos devices. Not for Junos Space Security Director or Security Director Cloud.
version: 1.2.1
author:
  - fastrevmd-lab
  - Claude
  - GPT
license: MIT
metadata:
  hermes:
    tags: [security-director, sd-on-prem, juniper, proxmox, kvm, qcow2, vm-deploy, virtio, ntp, log-collector, device-onboarding]
    related_skills: [srx-policy, srx-mnha, parsing-srx-configs]
  sources:
    - title: "SDC-KVM-Proxmox-support (Juniper Proxmox deployment how-to)"
      author: Juniper Networks
      note: "Vendor PDF; authoritative Proxmox import steps (25.2.2-era; uses --no-launch, renamed --no-run in 26.2.1)."
      retrieved: "2026-07-21"
    - title: "Deploy Juniper Security Director Using KVM | SD On-Prem 25.2.2"
      author: Juniper Networks
      url: https://www.juniper.net/documentation/us/en/software/sd-on-prem25.2.2/sd-on-prem-install-upgrade/install-guide/topics/task/install-kvm-tool.html
      retrieved: "2026-07-21"
    - title: "Deploy Juniper Security Director Using VMware vSphere | SD On-Prem 25.4.1"
      author: Juniper Networks
      url: https://www.juniper.net/documentation/us/en/software/sd-on-prem25.4.1/sd-on-prem-install-upgrade/install-guide/topics/task/install.html
      note: "Documents the cliadmin SSH user and predeployment VM-network reachability requirements."
      retrieved: "2026-07-24"
    - title: "set ipaddress change | SD On-Prem 25.4.1"
      author: Juniper Networks
      url: https://www.juniper.net/documentation/us/en/software/sd-on-prem25.4.1/sd-on-prem-user-guide/user-guide/topics/reference/set-ipaddress.html
      note: "The documented management-IP workflow prompts for netmask and gateway; it does not document a gateway-only command."
      retrieved: "2026-07-24"
  verified_on:
    - release: "26.2.1-5348"
      host: "Proxmox VE 9.2 (dell-r6515-2)"
      date: "2026-07-21"
---

# Deploying Security Director On-Prem on Proxmox VE

## Contents

- [Overview](#overview)
- [Artifacts (both files are needed for a fresh install)](#artifacts-both-files-are-needed-for-a-fresh-install)
- [Requirements](#requirements)
- [Runtime intake](#runtime-intake)
- [Procedure](#procedure)
- [Gotchas](#gotchas)
- [Verification checklist](#verification-checklist)
- [Rollback](#rollback)

> **STATUS: stable (v1.0.0).** Procedure below was executed end-to-end on
> **SD On-Prem 26.2.1-5348** on Proxmox VE 9.2, and has since been run to
> completion three times by the maintainer — the repeat runs the draft label was
> waiting on. Values in `<angle brackets>` are site-specific.

**Full step-by-step how-to:** `references/HOWTO-deploy-sd-onprem-proxmox.md`
(complete deployment + log-path + operations guide; this SKILL.md is the summary).

## Overview

> **This is Security Director On-Prem 25/26 — a NEW ATOM-based appliance on
> single-node RKE2 Kubernetes, NOT Junos Space Security Director.** Ignore
> Space-era guidance: there is **no device "schema install"**, no Space fabric.
> Version parity (device 26.x + SD 26.x) is not a schema concern. Log analytics
> ("All Security Events") is gated by an **assigned subscription**, not a schema.
> Ingest path = `secmgt/jingest` pod → `kafka-la` → `logging/opensearch`.

SD On-Prem ships as a **KVM appliance**: an OS boot disk (qcow2) + two data disks
+ a seed ISO carrying first-boot config. Juniper's supported flow targets a
**libvirt/virsh** host, but Proxmox VE does not run `libvirtd`. So we run the
vendor `.bin` in **extract-only mode (`--no-run`)** to generate the qcow2s + ISO
(no KVM needed), then **import them into a `qm`-native VM** and skip the vendor
`launch-vm.sh`. The VM stays fully Proxmox-managed (snapshots, HA, API).

## Artifacts (both files are needed for a fresh install)

| File | Role |
|---|---|
| `Juniper-Security-Director-<ver>-<build>-kvm.bin` (~6 GB) | Embeds **disk-0** (OS qcow2, sha256-verified). Run normally it deploys/upgrades via libvirt; run **`--no-run`** it ONLY extracts artifacts (disk-0 + builds disk-1/2 + seed ISO) — no KVM. This is the fresh-install extractor on Proxmox. |
| `Juniper-Security-Director-<ver>-<build>.tgz` (~8 GB) | The **encrypted** software bundle the appliance pulls + decrypts at first boot. It is `tgz → metadata.json + *-software.zip.psig + *-software.zip → sd_onprem_software.zip (ENCRYPTED)`. **You cannot hand-extract qcow2s from it** — it is not the disk source; the `.bin` is. |

> **Gotcha:** a common misread is "the `.bin` is only for upgrades, just use the
> `.tgz`." False for a fresh Proxmox install — the `.tgz` payload is an encrypted
> zip; the disks come from `.bin --no-run`. You need **both**.

## Requirements

- **4 IP addresses in the SAME subnet:** management (VM/CLI), UI VIP, device-
  connection VIP, log-collector VIP. Plan them contiguously.
- **Sizing is chosen at extract time** from a flavor table (`--no-run` prompt).
  26.2.1 flavors: `1)` 8 vCPU / 64 GB / 200+250+500 GB · `2)` 16 / 80 / 200+400+1536
  · `3)` 40 / 208 / 200+525+3584. Disk sizes come from the artifacts; you don't set them.
- **A REACHABLE NTP server** — SD requires NTP at first boot (cert/bootstrap). If the
  site blocks outbound UDP/123 (common), an internet NTP like NIST will hang the
  install; use an **internal** NTP the SD subnet can reach.
- A complete inventory of every managed firewall's management target, management
  service, reverse-channel source addresses, zones, transit hops, and return paths.
- **SD internal CIDR** default `10.42.0.0/21` (≥/21); must not overlap any lab net.
- `--no-run` host deps: `qemu-img`, `genisoimage`/`mkisofs`, `column`,
  `cracklib-check` (Debian: `cracklib-runtime`), `sha256sum`.

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

## Procedure

The deployment proceeds in six stages. Each links to its detailed section in
`references/HOWTO-deploy-sd-onprem-proxmox.md`.

### Stage 1: Predeployment connectivity validation

**Achieves:** Proves the exact proposed SD sources can reach all managed firewalls,
DNS, NTP, bundle delivery path, and that reverse paths (device-VIP:7804,
log-VIP:6514 TLS) work bidirectionally through all transit hops.

**STOP gate — explicit approval required before proceeding:** Do not extract
artifacts, create/import disks, or create/start an SD VM until every check passes.

**Critical rules:**
- Test from the EXACT proposed SD management IP/prefix and gateway using a
  disposable probe VM or network namespace on the selected Proxmox bridge.
- Proxmox-host tests are INVALID when host and guest use different addresses/gateways.
- Bundle delivery (HTTP or SCP) must be proved with full retrieval, correct byte
  count, and bidirectional session evidence BEFORE extraction.
- TLS handshake to log-VIP:6514 is MANDATORY — plain TCP connect is insufficient.
- Every stateful transit firewall must show In+Out both non-zero.
- Any failed or UNTESTED row keeps the gate closed.

**Detailed procedure:** `references/HOWTO-deploy-sd-onprem-proxmox.md` §3 (Mandatory
predeployment connectivity STOP gate)

**Regression guard (remote lab, 2026-07-24):** Hypervisor-only DNS/NTP checks
passed while the seed used wrong gateway `198.51.100.254`. The installed SD then
sent managed-device traffic to the wrong first hop. Exact-source testing would
have failed before deployment.

### Stage 2: Extract artifacts with `--no-run`

**Achieves:** Generates OS/data disks (qcow2), seed ISO, and `kvm-env.ini` from the
`.bin`. No VM created yet.

**Approval required:** Review `kvm-env.ini` — confirm management IP/prefix, gateway,
bridge, DNS, NTP, bundle URL, and all VIPs match the passed Stage 1 STOP-gate
evidence before proceeding to Stage 3.

**Critical rules:**
- The extractor is interactive with 22 prompts (26.2.1). Flavor/config-ID prompt
  (#20) has NO DEFAULT and loops on invalid — easy to miss when scripting.
- CLI admin password is silent input, 8–32 chars, ≥3 of digit/upper/lower/special,
  must pass cracklib — systematic strings like `Test1234!` are rejected.
- For bundle delivery, use the Stage 1 approved restricted HTTP pattern or exact
  SCP endpoint. **Never serve `<base>` or extraction directories** — they contain
  `kvm-env.ini` (credentials), qcow2, XML, ISO. Use bundled
  `scripts/serve_bundle.py` with `.tgz`-only webroot.

**Output:** `<base>/<version>/Security-Director-OnPrem-disk-{0,1,2}.qcow2`,
`Security-Director-OnPrem-kvm.iso`, `kvm-env.ini`, `sd-onprem.xml`.

**Detailed procedure:** `references/HOWTO-deploy-sd-onprem-proxmox.md` §4 (Extract
artifacts)

### Stage 3: Build Proxmox VM

**Achieves:** Creates a `qm`-native VM mirroring the generated `sd-onprem.xml`:
machine q35, CPU host-passthrough, 3 virtio disks (vda/vdb/vdc), seed ISO on
virtio-scsi cdrom, virtio NIC.

**Approval required: DESTRUCTIVE disk operations** (`qm create`, `qm importdisk`,
`qm set` attaching disks). Verify VMID, storage target, and bridge before running.

**Critical rules:**
- Boot order (`--boot order=virtio0`) MUST be a SEPARATE `qm set` AFTER disks
  attach. Setting it in the same command that attaches disks silently falls back
  to `order=net0;ide2`. Confirm with `qm config <vmid> | grep ^boot`.
- Match the flavor row exactly: CPU cores, RAM, and disk sizes are validated as
  a WHOLE SET on every boot (see Gotchas).

**Detailed procedure:** `references/HOWTO-deploy-sd-onprem-proxmox.md` §5 (Build the
Proxmox VM)

### Stage 4: First boot and bundle delivery

**Achieves:** VM applies seed network config, retrieves/decrypts the `.tgz` bundle,
installs RKE2/k8s/SD container stack. Long operation (tens of minutes).

**Approval required:** Temporary bundle-delivery window — recreate the approved
HTTP server/nftables rule OR the approved SCP access from Stage 1. Close
immediately after completed transfer.

**Critical rules:**
- For HTTP: wait for `COMPLETE source=<SD-mgmt-IP> ... bytes=<expected>` from
  `scripts/serve_bundle.py` log before tearing down. A `200` request line is NOT
  completion proof — may be logged before body finishes.
- Close the temporary exposure (HTTP server/rule/webroot OR SCP access) as soon
  as transfer completes. Do not wait for container install.
- Snapshot the VM before onboarding devices.
- Assign subscription/license (Admin → Subscriptions) — **log analytics / "All
  Security Events" is gated behind it**, separate from device management.

**Progress signals:**
- Mgmt IP answers ping within ~1–2 min (network seeded)
- Bundle server/SCP logs completed transfer with correct byte count
- UI VIP (`https://<ui-vip>`) serves Juniper self-signed cert (may 404)
- `https://<ui-vip>/login` returns 200 (app pods finished)

**Detailed procedure:** `references/HOWTO-deploy-sd-onprem-proxmox.md` §6 (First
boot + verify)

### Stage 5: Device NTP preflight (STOP gate)

**Achieves:** Proves every managed SRX clock is synchronized before onboarding.

**STOP gate — NO device is discovered or onboarded until this passes.** Configured
servers and a running `ntpd` do NOT satisfy this; proven synchronization does.

**Critical rules:**
- **Why it is a gate:** A skewed SRX still completes the mTLS handshake to the
  collector and has payloads acknowledged, so every transport test passes while
  logs never reach the GUI. Live deployment: SRXs ~375 s behind, streams connected/ACKed,
  traffic logs absent. They appeared only after NTP fixed + fresh traffic generated.
- **Pass/fail authority:** `show ntp associations no-resolve` — require at least
  one peer marked `*` (selected system peer), `reach` non-zero (`377` = all
  recent polls answered), and `offset` within deployment tolerance.
- `set system processes ntp enable` is hidden from CLI completion but valid.
  Commit-check accepts it on SRX345 Junos 24.2R2-S5.3 and vSRX 24.4R1.9/26.2R1.7.
  Its absence is NOT a hard fail (devices without it still run `ntpd`), but
  `ntp disable` present IS a hard fail.
- Through NAT/VPN: prove UDP/123 bidirectionally. Include loopback management
  sources in transit FW source-NAT match; do NOT put NTP server IPs in source-NAT
  (they are destinations).

**Detailed procedure:** `references/HOWTO-deploy-sd-onprem-proxmox.md` §7.0 (NTP
preflight — STOP gate)

### Stage 6: Device onboarding and log-path validation

**Achieves:** Adds devices to SD inventory (BROWN_FIELD create), applies
device-initiated bootstrap config, verifies device-connection (VIP:7804) and
log-stream (VIP:6514 TLS) sessions, confirms events appear in SD GUI.

**Approval required:** Configuration push to devices (load bootstrap, commit).

**Critical rules — both planes are in-band; fxp0 is not a path to SD for anything:**
- **Management:** Manage devices at revenue-port addresses (`ge-0/0/x.0`, `reth`,
  or in-band-reachable `lo0`). Device-connection session to device-VIP:7804 must
  leave a revenue port. **NOT fxp0** — the route chooses egress, not `source-interface`;
  if `<device-VIP>/32` resolves out fxp0, the stream dies.
- **Logging:** Must NOT source off fxp0 — SD cannot receive security logs from the
  management interface. SRX stream-mode logs are PFE/data-plane, which cannot
  egress fxp0. Set `security log source-address` to a revenue interface IP.
- **Log-path network requirements (§8 in HOWTO):**
  1. Source from production/revenue port (never fxp0)
  2. Data-plane route to log-VIP (use a policy/routing FW with SD-subnet leg as
     log gateway; route every device's `<log-VIP>/32` toward it)
  3. **Source-NAT on log-gateway FW** — TLS/6514 is bidirectional; SD has no route
     back to device fabric IPs, so NAT log traffic to gateway's on-subnet leg
- **For tunnel-managed branches:** Pick the LAN port (subnet gateway routes back
  over tunnel) as log source, NOT the WAN (shared underlay gateway reaches directly)
  — WAN source is asymmetric (forward via tunnel, reply via underlay) so branch
  drops SYN-ACK. Also NAT both device-VIP and log-VIP or adoption hangs `In:1/Out:0`.
- **MNHA pairs:** Each node has independent config (configure route on BOTH); only
  active node logs (backup idle, streams on failover).
- **Verification (no session exists until a security EVENT fires):**
  - On SRX: `show log messages | match RTLOG_CONN_OPEN` (connection established)
  - On SRX: `show security flow session destination-prefix <log-VIP>` — **In AND
    Out both non-zero** on :6514 session
  - On log-gateway FW: session to log-VIP:6514 shows `Session State: Valid`,
    In+Out both non-zero (Out:0 = broken return path)
  - Generate test traffic → verify events appear in SD GUI "All Security Events"

**Common pitfalls:**
- **There is no API-key UI** (SD Cloud only). REST API auth = `x-iam-token` header
  (browser JWT from sessionStorage, ~30-min TTL). Forgotten web-admin password
  recovered from VM serial console (`qm terminal <vmid>` → `cliadmin` →
  `reset local-user`; console-only, refuses over SSH).
- **BROWN_FIELD is the onboarding path for existing SRX.** Device-initiated
  outbound-ssh to device-VIP:7804. Load the FULL bootstrap — partial load omitting
  host block leaves outbound-ssh with nowhere to dial.
- **SD auto-generates device certs on onboarding — but only if cert controller is
  up.** Devices onboarded in first ~2 min after appliance first boot miss cert
  step. Fix: delete device entry, re-create BROWN_FIELD; cert regenerates within ~60 s.
  **For MNHA or a chassis cluster, delete the cluster entry** (it cascades to the
  children), not a child entry — see `references/gotchas.md`.
- **Inert factory `default-permit` zone-pair policy silently suppresses logging.**
  Zone-pair policies evaluate BEFORE global. A leftover `from-zone trust to-zone
  untrust policy default-permit` (permit, no log) matches first; traffic never
  reaches global logging policy. Confirm with `show security flow session` (matched
  policy) and `show security policies hit-count`. Delete shadowing zone-pair policy.
- **Stuck `outbound-ssh` after path repair:** Session shows ESTABLISHED, cert valid,
  clock in sync, but device stays "status unknown". Force new session without
  permanent config change: `delete system services outbound-ssh client <name>;
  commit confirmed 1` then DO NOT confirm — let it roll back (~90 s). Device
  reconnects from new source port; EMS re-adopts.

**Detailed procedure:** `references/HOWTO-deploy-sd-onprem-proxmox.md` §7 (Onboard
Junos/SRX devices), §8 (The log path)

## Gotchas

See `references/gotchas.md` for the complete list (all hit in a real 26.2.1 build).
Key items agents must obey:

- **No libvirt on Proxmox** → don't run `launch-vm.sh`; import qcow2s into `qm`.
- **`.bin --no-run` is the disk source**, not the `.tgz` (encrypted).
- **Boot order must be a separate `qm set`** after disks attach.
- **NTP must be reachable** — internet NTP behind blocked UDP/123 hangs first boot.
- **Every DNS server must answer DNS** — non-resolving entry loops first boot.
- **Log transport is TLS/6514**, not UDP/514. Plain TCP does not pass preflight.
- **Skewed device clock looks like working pipeline** but logs never appear in GUI.
  Gate on NTP (Stage 5) before onboarding.
- **Browser/workstation clock skew** > ~30 min makes GUI unusable (bounces to login).
- **`lo0` not selectable as log source** — pick physical revenue port (LAN for
  tunnel branches, not WAN).
- **Device-connection VIP:7804 needs same source-NAT** as logs for tunnel branches.
- **Flavor validated as WHOLE SET** — cannot bump only CPU/RAM; match the target
  flavor's full CPU/RAM/data-disk tuple (disk-0 stays 200 GB in every flavor) or
  RKE2 never starts.

## Verification checklist

Complete before declaring deployment successful:

**Predeployment (Stage 1):**
- [ ] All 4 IPs are free (no `arping` reply), outside DHCP pool
- [ ] DNS resolves from exact SD source (probe VM/namespace)
- [ ] NTP synchronized from exact SD source (`chronyd -Q` / `ntpdate -q` / `sntp`)
- [ ] Bundle retrieval completes with correct byte count (HTTP `COMPLETE` or SCP log)
- [ ] Device-VIP:7804 reachable from device-mgmt sources (listener proof, TCP connect)
- [ ] Log-VIP:6514 TLS handshake from revenue sources (not just TCP)
- [ ] Transit FW sessions show In+Out non-zero for all tested paths
- [ ] Approved routing/policy/NAT changes applied and re-tested

**Extraction and VM build (Stages 2–3):**
- [ ] `kvm-env.ini` values match Stage 1 evidence (IPs, gateway, bridge, DNS, NTP, bundle URL)
- [ ] VM created with correct VMID, bridge, flavor (CPU/RAM/disks)
- [ ] Boot order = `virtio0` (`qm config <vmid> | grep ^boot`)
- [ ] Snapshot taken before first boot

**First boot (Stage 4):**
- [ ] Management IP answers ping within ~2 min
- [ ] Bundle server logs completed transfer with expected byte count
- [ ] Temporary bundle-delivery window closed (HTTP server/rule OR SCP access revoked)
- [ ] Transfer/session evidence retained (redacted)
- [ ] UI VIP serves `https://<ui-vip>` (Juniper self-signed cert)
- [ ] `https://<ui-vip>/login` returns 200
- [ ] Subscription/license assigned (Admin → Subscriptions)
- [ ] VM snapshot taken before onboarding

**Device NTP preflight (Stage 5) — every managed SRX:**
- [ ] `show configuration system processes | display set | match "ntp enable"` — present or absent (not `disable`)
- [ ] `show ntp associations no-resolve` — at least one `*` peer, reach non-zero (377 = full), offset acceptable
- [ ] `show system processes extensive | match " ntpd"` — process running
- [ ] `show system uptime` — `Time Source: NTP CLOCK`
- [ ] `show ntp status` — `leap_none, sync_ntp`; `clock_sync` once settled
- [ ] Fleet-wide: all SRX clocks agree before onboarding

**Device onboarding and log path (Stage 6) — per device:**
- [ ] Device created in SD inventory (BROWN_FIELD type: STANDALONE / MNHA / L2_CLUSTER)
- [ ] Bootstrap config generated (`POST /api/v1/devices/{uuid}/get_bootstrap_config`)
- [ ] Full bootstrap loaded on device (including `<device-VIP> port 7804` host block)
- [ ] Device connects to device-VIP:7804 (`show system connections` on device)
- [ ] Certificate installed (`certificate_ready:true` in SD, or `show security pki local-certificate` on device)
- [ ] Log stream opens (`show log messages | match RTLOG_CONN_OPEN` — `Connection established sd-logs TLS`)
- [ ] Device flow session to log-VIP:6514 shows In+Out non-zero (`show security flow session destination-prefix <log-VIP>`)
- [ ] Log-gateway FW session to log-VIP:6514 shows `Session State: Valid`, In+Out non-zero
- [ ] Test traffic generated (permit + log policy matched)
- [ ] Events visible in SD GUI "All Security Events" (not empty due to missing subscription or skewed clock)
- [ ] For MNHA/cluster: both nodes' routes configured, only active node streaming

**Post-deployment:**
- [ ] Final snapshot taken with known-good state
- [ ] All temporary test infrastructure removed (probe VM/namespace, bundle server, TLS certs/keys)
- [ ] Deployment evidence retained (connectivity matrix, bundle transfer logs, FW session captures)

## Rollback

For the verified 26.2.1 wrong-seed case, protect/stop the failed guest and build
a fresh VM from corrected seed data and fresh disks; do not destroy the rollback
copy until the replacement passes the same connectivity matrix. `qm stop <vmid>
&& qm destroy <vmid>` removes an explicitly approved disposable VM (verify the
VMID; never destroy a protected guest). Stop the bundle server; remove its
temporary host-firewall rule, bundle-only webroot, and test certificates. No
libvirt state remains.

---
name: csrx-proxmox-deploy
description: Deploy a Juniper cSRX container firewall as a Docker workload on a Proxmox VE KVM guest, in both secure-wire (L2 bump-in-the-wire) and routing (L3) forwarding modes, drawn from an end-to-end build rather than vendor documentation. Use when sizing the Docker host guest, setting the mandatory host CPU model, wiring cSRX data-plane interfaces through Docker macvlan networks, diagnosing a container that reports healthy with no forwarding plane at all, TCP that hangs or corrupts while ICMP passes cleanly, a deny policy that blocks traffic but logs nothing, a routing-mode rebuild with no addressable interface, rediscovering the CSRX_* environment-variable surface for a different image release, judging a throughput number against a known baseline, or verifying isolation and enforcement with a test that can actually fail.
version: 0.1.1
author:
  - fastrevmd-lab
  - Claude
  - GPT
license: MIT
metadata:
  hermes:
    tags: [csrx, juniper, container-firewall, docker, macvlan, proxmox, kvm, dpdk, vsrx, crpd, secure-wire]
    related_skills: [srx-chassis-cluster-proxmox, srx-policy, parsing-srx-configs]
  verified_on:
    - release: "26.2R1.7 (cSRX)"
      host: "Proxmox VE 9.2.20, Docker CE on a KVM guest"
      date: "2026-09-22"
      note: "Verified in both CSRX_FORWARD_MODE=wire (secure-wire) and CSRX_FORWARD_MODE=routing. Not validated on any other cSRX release, nor on a second Proxmox estate."
---

# Deploying a Juniper cSRX Container Firewall on Proxmox VE

## Contents

- [Overview](#overview)
- [Artifacts](#artifacts)
- [Requirements](#requirements)
- [Runtime intake](#runtime-intake)
- [Mandatory pre-power-on gate](#mandatory-pre-power-on-gate)
- [Procedure](#procedure)
- [Gotchas (all hit in a real build)](#gotchas-all-hit-in-a-real-build)
- [The performance envelope](#the-performance-envelope)
- [The cRPD finding — read from the image, never executed](#the-crpd-finding--read-from-the-image-never-executed)
- [Verification methodology](#verification-methodology)
- [Day-2 operations](#day-2-operations)
- [Rollback](#rollback)

> **STATUS: draft (v0.1.1).** Every claim below comes from one end-to-end build
> on **Proxmox VE 9.2.20** running **cSRX 26.2R1.7** as a Docker container,
> exercised in both secure-wire and routing forwarding modes. It has **not**
> been repeated on a different cSRX release or a second Proxmox estate. No
> vendor release notes existed for the build this content is drawn from — the
> image's own init scripts were the source of truth throughout, and that
> method is preserved here (§ "Rediscovering the CSRX_* surface") so it
> transfers to a release this skill has not seen. Values in `<angle
> brackets>` are site-specific.

## Overview

> **The two findings that cost the most time (see Gotchas section and
> `references/gotchas.md` for full details):** (1)
> The reference guest's CPU model did not expose SSSE3, and cSRX's forwarding
> process hard-requires it even when its DPDK fast-path driver is not
> selected — the container comes up `Up` and healthy with **zero** forwarding
> plane underneath it. Whether a given guest's default CPU model exposes
> SSSE3 depends on the Proxmox version and how the guest was created (`qm
> create` CLI vs the web UI), so this must be verified rather than assumed.
> (2) Docker's default macvlan `bridge` mode structurally cannot deliver a
> frame addressed to a foreign MAC — exactly what a bump-in-the-wire firewall
> needs — regardless of promiscuous-mode settings on either end. The
> pre-power-on gate exists specifically to catch both before a live build
> re-discovers them the hard way.

cSRX ships as a Docker image, not a VM appliance — there is no qcow2, no raw
disk, no ISO. Deployment is therefore: build a **KVM guest** (not an LXC —
cSRX runs `--privileged` and manipulates its own network namespace, which an
LXC's nesting makes unworkable to debug) running Docker CE, with one
management NIC and at least two data-plane NICs; wire the data-plane NICs to
Docker **macvlan** networks in `passthru` mode; and run the cSRX container
against that image with the `CSRX_*` environment-variable surface set for
the chosen forwarding mode. Junos configuration then proceeds through the
container's own CLI exactly as on a vSRX, with the CLI-surface gaps noted
below.

Two forwarding modes exist, selected once at container-run time and not
convertible in place:

- **`CSRX_FORWARD_MODE=wire`** — secure-wire: a true Layer-2 splice between
  two interfaces. No `family inet`, no routing; the two segments it bridges
  must already share one IP subnet.
- **`CSRX_FORWARD_MODE=routing`** (the default) — Layer-3, with the same
  interface/zone/policy model as a vSRX, but **no auto-created logical
  unit** — addressing is mandatory, not a fallback.

## Artifacts

| Artifact | Role |
|---|---|
| cSRX Docker image (e.g. `csrx:<version>`) | The entitled image tarball, loaded with `docker load`. Distributed behind a signed, time-limited download URL — do not reproduce that URL, and do not commit the tarball. |
| Licence file | Referenced by path via `CSRX_LICENSE_FILE`, typically bind-mounted into the container. Reference it by path/environment variable only — never reproduce its contents or any embedded identifier. |

## Requirements

- A KVM guest (not an LXC) running Docker CE, with a **CPU model that
  exposes SSSE3** — mandatory, not an optimization. `--cpu host` is the
  simplest way to guarantee it; see the pre-power-on gate for the
  migration-preserving alternative.
- At least **one management vNIC** and **two data-plane vNICs**, one per
  side of the firewall. `CSRX_PORT_NUM` defaults to 3 and is forced to a
  minimum of 3 when `CSRX_FORWARD_MODE=wire`; the reference build satisfied
  this with one management interface plus two data-plane interfaces,
  implying the count includes the management port — but verify this against
  your own image's init script before assuming a third data-plane NIC is
  required.
- Each data-plane vNIC's Proxmox-side parent interface **administratively
  up** with no IP address of its own — see `references/gotchas.md` #9.
- Docker CE installed non-interactively (`DEBIAN_FRONTEND=noninteractive` for
  every install that might carry an interactive postinst — see
  `references/gotchas.md` #13).
- The entitled image tarball and, if licensing is required, a licence file
  reachable by path inside the guest.
- A rough idea of the expected throughput envelope before testing — see
  "The performance envelope" — so a slow-but-correct result is not mistaken
  for a bug.

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

## Mandatory pre-power-on gate

> **STOP — verify all five before the container's first `docker run`.**
> Items 1 and 2 are the two findings above; getting either wrong produces a
> container that looks healthy and passes no traffic, with no error that
> names the real cause.

1. **The Docker host guest's CPU model exposes SSSE3** (mandatory for
   cSRX), and the guest has been **cold-restarted** after any CPU model
   change (`qm stop` / `qm start` — not a soft reboot; a CPU model change
   never applies to a running VM). Confirm `ssse3` is present in the guest's
   `/proc/cpuinfo` after the restart. The simplest way to guarantee this is
   `qm set <vmid> --cpu host`, which passes through the host's real
   features; on a multi-node cluster where live migration matters, any CPU
   model exposing SSSE3 (the x86-64-v2 baseline and above, e.g.
   `x86-64-v2-AES`) satisfies cSRX while keeping the guest migratable —
   `--cpu host` pins the guest to CPU-compatible nodes.
2. **The macvlan networks that will carry cSRX's data-plane interfaces are
   planned as `-o macvlan_mode=passthru`**, one network per parent NIC — not
   the Docker default `bridge` mode. Decide this before the first `docker
   network create`, because switching an already-running container from
   `bridge` to `passthru` networks is **not** sufficient by itself (see
   `references/gotchas.md` #2) — plan for a `docker restart` of the container as part of that change,
   not as an afterthought.
3. **Checksum/segmentation offload will be disabled at every hop** between
   the two endpoints and cSRX's data-plane interfaces — the container-side
   veth peers and the hypervisor's own tap devices — before any TCP test is
   trusted. Confirming this is planned, not deferring it until a TCP test
   hangs.
4. **The forwarding mode is decided** (`wire` vs `routing`) before interface
   configuration begins — secure-wire forces a same-subnet, non-routed
   topology and rejects `family inet` outright; routing mode requires
   explicit `unit`/`family`/`address` on every data interface with no
   auto-creation. Changing the mode later is a rebuild of the interface
   configuration, not a toggle.
5. **The licence file, if used, is referenced by path/environment variable
   only.** Confirm nothing that will be typed, committed, or logged during
   this deployment reproduces its contents or the image's signed download
   URL.

## Procedure

### 1. Rediscover the CSRX_* surface for the release in hand

Do this before writing any `docker run` line — do not assume the table in
`references/csrx-environment-variables.md` (drawn from 26.2R1.7) carries
forward unchanged. Method, in full there: read `/etc/rc.local`, then read
every script it sources **in full, not a grep** — at least one
release-critical variable (`CSRX_FORWARD_MODE`) lives inside a sourced helper
function, not as a literal string in `rc.local` itself.

### 2. Build the Docker host guest

```bash
qm create <vmid> --name <name> --ostype l26 --cpu host \
  --sockets 1 --cores <n> --memory <mb> \
  --net0 virtio,bridge=<mgmt-bridge> \
  --net1 virtio,bridge=<data-bridge-left> \
  --net2 virtio,bridge=<data-bridge-right>
# then a normal OS install/provision, Docker CE installed with
# DEBIAN_FRONTEND=noninteractive for every package (see references/gotchas.md #13)
```

Confirm each in-guest interface name against its MAC address
(`cat /sys/class/net/<if>/address`), not by position (see
`references/gotchas.md` #10). Bring the data-plane parent interfaces up with
no address (`references/gotchas.md` #9):

```bash
ip link set <data-if-left> up
ip link set <data-if-right> up
```

Apply the CPU-model change and cold restart per the pre-power-on gate before
proceeding.

### 3. Create the macvlan networks (passthru, not bridge)

```bash
docker network create -d macvlan \
  --subnet <left-subnet-cidr> --gateway <left-gateway> \
  -o parent=<data-if-left> -o macvlan_mode=passthru <left-network-name>

docker network create -d macvlan \
  --subnet <right-subnet-cidr> --gateway <right-gateway> \
  -o parent=<data-if-right> -o macvlan_mode=passthru <right-network-name>
```

One network per parent NIC — `passthru` gives a single child the entire
parent, which is why only one network per parent is valid.

> **Secure-wire needs two *different* `--subnet` values even though both
> segments share one transit subnet.** Docker's IPAM refuses a second network
> whose pool overlaps the first (`Pool overlaps with other one on this address
> space`) — it does not care that the parent NICs differ. But wire mode is a
> Layer-2 splice: cSRX holds no address on either data interface and never
> consults these pools. So give the second network an **unused dummy CIDR**
> purely to satisfy the driver, and address the hosts either side into the one
> real transit subnet as normal. In routing mode the two `--subnet` values are
> real and must match the addresses cSRX will carry.

### 4. Disable offload on every hop before any TCP test

```bash
ethtool -K <iface> tx-checksum-ip-generic off tso off gso off
```

Apply to the container-side veth peers of both endpoints **and** the
hypervisor's tap devices for the data-plane vNICs — all hops need it, or the
handshake completes while data segments still fail. **Does not survive a
reboot of either endpoint or the Docker host guest** — re-verify after any
reboot (see `references/gotchas.md` #3).

### 5. Run the cSRX container

```bash
docker run -d --name <container-name> --privileged \
  -e CSRX_FORWARD_MODE=<wire|routing> \
  -e CSRX_SIZE=<size> \
  -e CSRX_PACKET_DRIVER=<interrupt|dpdk|poll|virtio> \
  -e CSRX_LICENSE_FILE=/config/license.lic \
  -v <host-licence-path>:/config/license.lic:ro \
  <image>:<tag>

docker network connect <left-network-name> <container-name>
docker network connect <right-network-name> <container-name>
docker restart <container-name>   # mandatory — see references/gotchas.md #2
```

To load a startup configuration, bind-mount it at `/config/juniper.conf`
directly, or set `CSRX_JUNOS_CONFIG` to a path the image loads with `load
merge` — **not** `CSRX_JUNIPER_CONFIG`, which is silently discarded (see
`references/gotchas.md` #5).

### 6. Configure interfaces, zones, and logging

Routing mode requires explicit addressing on every data interface — nothing
is auto-created:

```junos
set interfaces ge-0/0/0 unit 0 family inet address <left-addr>/<prefix>
set interfaces ge-0/0/1 unit 0 family inet address <right-addr>/<prefix>
set security zones security-zone <left-zone> interfaces ge-0/0/0.0
set security zones security-zone <right-zone> interfaces ge-0/0/1.0
set security zones security-zone <left-zone> host-inbound-traffic system-services ping
```

Secure-wire mode never takes `family inet` — configure it as a Layer-2
splice between two interfaces on the same subnet instead.

Commit local logging explicitly before relying on any log-based check — this
image ships with **none** by default (Gotcha 4):

```junos
set system syslog file messages any any
set security log mode event
```

### 7. Verify

Follow "Verification methodology" below — do not stop at "traffic passes."

## Gotchas (all hit in a real build)

> **CRITICAL: Configure logging before trusting any enforcement check.**
> cSRX ships with **no default local logging** — `system syslog` and
> `security log` are both empty, so a deny policy blocks traffic but produces
> no log entry. Commit `set system syslog file messages any any` **and**
> `set security log mode event` as part of the initial config, not as a
> reaction to "the log is empty." Without both, a policy that appears to
> block traffic may never have been in the enforcement path at all.

Thirteen findings, each silently breaks the deployment or produces a
false-positive pass. The pre-power-on gate covers the two sharpest (SSSE3 and
macvlan mode); procedure step 4 covers TCP offload; the remainder are in
**`references/gotchas.md`**:

1. Container `Up`, control plane healthy, but no data plane (missing SSSE3)
2. Traffic unidirectional or silent on macvlan networks (need `passthru` mode)
3. TCP hangs while ICMP passes (offload not disabled)
4. Deny policy blocks traffic but logs nothing (no logging config — see above)
5. `CSRX_JUNIPER_CONFIG` silently discarded (use `CSRX_JUNOS_CONFIG`)
6. Secure-wire rejects `family inet` (Layer-2 splice, not IP-aware)
7. Routing mode has no addressable logical unit (must configure explicitly)
8. CLI thinner than vSRX (see `references/csrx-cli-gaps.md` for substitutes)
9. Macvlan parent interface administratively down (must bring up manually)
10. First vNIC name inconsistent with others (confirm by MAC, not position)
11. `qm guest cmd` never answers (guest agent package not installed)
12. Hot-added NIC never comes up (must `ifup` explicitly)
13. Package install hangs with `-y -qq` (need `DEBIAN_FRONTEND=noninteractive`)

## The performance envelope

**Single-digit Mbit/s TCP on this stack is a baseline, not a fault.** The
reference build measured roughly **8.8 Mbit/s in routing mode** and
**0.2 Mbit/s in secure-wire**, on a local virtual path where Gbit/s would be
expected, with `InCsumErrors` at zero in both. Do not start a corruption hunt
(see `references/gotchas.md` #3) on a throughput number alone — check
`InCsumErrors` first, and if it
is already zero, the number is probably normal for this stack.

Figures, the mode-gap analysis, the sample-size caveat (one run per mode) and
what remains unexplained: **`references/csrx-performance-envelope.md`**.

## The cRPD finding — read from the image, never executed

**Explicitly unverified — do not treat this as a working configuration.**
Included because it changes what "cSRX and cRPD are unrelated products"
means, and is the strongest lead toward a future Kubernetes/CNF-style
deployment — not because it was tested.

Evidence, found while inspecting the image for the `CSRX_*` table: the
data-plane process (`srxpfe`) reads a `CSRX_CRPD` environment variable
(`enable`/`disable`, default `disable`), validated the same way as every
other genuinely env-driven variable. The same binary carries this
log-format string: `CSRX_CRPD %s: action:%s proto:%d gw_ip: %s
linux_ifd:%d junos_ifd:%d dest:%s/%d` — route-programming instrumentation
with a `linux_ifd` → `junos_ifd` mapping, the signature of importing Linux
kernel FIB entries into the Junos-side forwarding table. That is exactly how
cRPD operates: it runs the actual routing protocol daemons and programs
routes into the **Linux** kernel routing table of whatever namespace it
shares, rather than a Junos RIB directly. With `CSRX_CRPD=enable`, cSRX's
dataplane appears built to consume routes from that shared table.

**What this does and does not establish.** It does not mean cSRX itself runs
any routing protocol — there is no `rpd`/cRPD binary in the cSRX image;
cRPD remains a separate container with its own entitlement. It does
establish that cSRX has a first-class mode for acting as the enforcement
dataplane behind a cRPD control plane in the same host/namespace, rather
than the two products being merely chained as independent boxes.

**Unverified:** the required deployment topology (shared namespace? sidecar
containers? a Kubernetes pod shape via Multus?); whether `CSRX_CRPD=enable`
needs a separate licence entitlement; and whether it works at all, in any
topology. This is a reading of a log-format string and an environment
default, not an observed behavior.

## Verification methodology

The reasoning for why a check is trustworthy matters as much as the command
— a test that cannot produce the opposite result proves nothing, and this
build hit that trap more than once.

**Every pass/fail check must be shown capable of the opposite result.** The
load-bearing pattern is a two-step gate: confirm traffic is **blocked** with
no policy in place, then confirm the identical traffic **passes** once a
permissive policy is committed, in that order. Proving pass without first
proving fail leaves open that the traffic was never actually being inspected
— it could be bypassing the device entirely, or the device might never have
been in the path. A permit-everything policy that passes traffic proves
only that packets flow, not that anything is enforcing on them. The same
discipline applies to a deny test: enforcement is not proven by "traffic
stopped" alone — it must be shown **blocked and logged, both** (Gotcha 4). A
policy that blocks traffic but produces no matching log line is ambiguous
between "nothing was denied" and "logging is silently off" until the
logging pipeline itself is confirmed configured.

**Why a plain cross-subnet `ping` is not an isolation test.** Before
trusting a later "traffic now crosses via the firewall" result, isolation
between the two segments has to be proven first — if they weren't really
isolated, that later result would be meaningless. The naive test — `ping`
from one subnet directly to an address on the other, with no gateway
configured — cannot prove isolation either way: if the addresses are in
different subnets and no route exists, the kernel's routing-table lookup
fails immediately with `Network is unreachable` **before a single frame is
put on the wire** — the identical result whether the segments are genuinely
isolated or fully bridged together. **The fix:** force the kernel to
actually try, by adding a temporary on-link route for the far address out
the near interface, then removing it immediately after. With a forced
route, the kernel ARPs for the far address onto the (allegedly isolated)
segment. If the segments are genuinely isolated, the ARP goes unanswered — a
real timeout, not an instant rejection. If they're secretly bridged, the ARP
gets answered and the ping succeeds. This is the first result in the whole
test that actually depends on the state of the thing being tested.

**Sampling timing matters for flow-session checks.** Flow-table entries can
expire within single-digit seconds for ICMP. A "show me the session" check
run immediately *after* a ping completes, rather than *during* it, can
legitimately read zero active sessions even though forwarding worked
correctly moments earlier — sample mid-test, not after.

## Day-2 operations

Routine operation, log access, policy changes on a running container, and the
**configuration backup and restore procedure that rollback depends on**:
**`references/csrx-day-2-operations.md`**.

## Rollback

Nothing outside the Docker host guest is modified by cSRX itself — its state
lives in the container's writable layer plus whatever config/licence paths
are bind-mounted in. Rollback is bounded:

- **Container-level:** `docker stop <name> && docker rm <name>` plus
  `docker network rm` for the macvlan networks it used. Recreate from the
  same image tag and the same `CSRX_*` values.

  > **`docker rm` destroys every Junos commit you have made.** Unless you
  > bind-mounted a config path, interfaces, zones, policies, static routes and
  > the syslog configuration all live in the container's writable layer only.
  > Recreating from the same image and the same `CSRX_*` values returns a
  > *factory* cSRX, not your device — and it does so silently, because the
  > container comes up healthy. This is not hypothetical: a rebuild during the
  > reference build lost its logging configuration exactly this way, and the
  > deny policy that followed was enforced but unlogged until it was noticed.
  >
  > Before removing a container you may want to keep:
  >
  > Export with `show configuration` (**hierarchical** — a `| display set` capture
  > will not load through the startup path) and restore via `CSRX_JUNOS_CONFIG`.
  > Full procedure: `references/csrx-day-2-operations.md`. **Keep the original container — stopped,
  > not removed — until the replacement has passed verification.** A stopped
  > container still holds its writable layer; a removed one does not.
- **Host-guest-level:** if the CPU model or NIC configuration was changed,
  revert with `qm set` and a **cold** restart — a live reboot will not
  undo a CPU-model change either.
- **Image-level:** the entitled image was obtained behind a signed,
  time-limited URL. If it's removed (`docker rmi`) without keeping a local
  copy, it cannot be re-derived without going back through that
  entitlement flow — keep a local copy of the loaded tarball for the
  duration of any build that might need a clean re-run.

Take a Proxmox snapshot of the Docker host guest before changing its CPU
model or before loading a different cSRX release, since there is no
separate rehearsal rig documented here to fall back to.

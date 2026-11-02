---
name: srx-mnha-ipsec-builder
description: Build a route-based IPsec VPN from an SRX MNHA hub, anchored on a floating loopback, to a spoke SRX over a Junos MCP server, with checked configs, commit-confirmed pushes, cutover and failover tests. Use when building, tuning or testing IPsec to an MNHA hub, or asking about process-packet-on-backup, managed-services ipsec, RT_IPSEC_REPLAY after failover, or IPsec convergence on MNHA. To build the pair use srx-mnha-builder; for design or troubleshooting use srx-mnha.
version: 0.1.1
author:
  - fastrevmd-lab
  - Claude
  - GPT
  - jgrizzuti
license: MIT
metadata:
  hermes:
    tags: [srx, vsrx, junos, mnha, ipsec, ike, hub-and-spoke, floating-loopback, managed-services-ipsec, process-packet-on-backup, anti-replay, ebgp, bfd, floating-static, commit-confirmed, mcp, approval-gate, failover-test, iperf3]
    related_skills: [srx-mnha, srx-mnha-builder, srx-ipsec-hub-spoke, srx-policy]
  sources:
    - title: "MNHA, IPSec and Multiple Routing Instances"
      author: James Rathbun
      url: https://community.juniper.net/blogs/james-rathbun/2026/03/30/mnha-ipsec-and-multiple-routing-instances?CommunityKey=44efd17a-81a6-4306-b5f3-e5f82402d8d3
      retrieved: "2026-10-09"
---

# SRX MNHA IPsec Hub Builder

## Contents

- [Runtime intake](#runtime-intake)
- [Step 0 - Facts and safety](#step-0---facts-and-safety)
- [Step 1 - Ask the goal first](#step-1---ask-the-goal-first)
- [Step 2 - VPN sheet](#step-2---vpn-sheet)
- [Step 3 - Write and check the config files (nothing touches devices)](#step-3---write-and-check-the-config-files-nothing-touches-devices)
- [Step 4 - Dry run on the devices](#step-4---dry-run-on-the-devices)
- [Step 5 - Approval gate, then Phase A: build the tunnel](#step-5---approval-gate-then-phase-a-build-the-tunnel)
- [Step 6 - Phase B: cutover](#step-6---phase-b-cutover)
- [Step 7 - Failover tests](#step-7---failover-tests)
- [Step 8 - Report](#step-8---report)
- [Guardrails](#guardrails)

Builds one tunnel: **spoke SRX to an MNHA hub anchored on a floating loopback**, with
eBGP and BFD over the tunnel and floating statics as a safety net. Design background
(why the anchor, zone and routing-instance rules exist, the IPsec section of MNHA)
lives in `srx-mnha`; this skill builds and tests the tunnel in a safe order. Measured
effects are expressed as **percentages relative to a baseline you measure yourself**,
because convergence times differ per platform, timers and path
(`references/mnha-ipsec.md`).

**Prerequisites (stop if any fails):**
1. A formed MNHA pair in routing or hybrid mode with an existing eBGP export policy
   that has `active` and `backup` terms. Build it with `srx-mnha-builder`.
2. `junos-ike` installed on both hub nodes (`show version` lists "JUNOS ike");
   recommended on the spoke. A freshly installed package needs a **reboot** before IKE
   works. Confirm an IKE process is running.
3. The **user** has set the IKE proposal, the IKE policy **and the same pre-shared key**
   on every device. Never ask for the key, and never put it in the sheet, the chat or
   an MCP push.
4. Console or out-of-band access to every device. Commit confirmed is the safety net,
   not a substitute for console access.
5. Read `references/mcp-server-notes.md` first: tool mapping per server, commit
   confirmed, timeouts, large logs, least-privilege account.

**Out of scope:** node-local tunnels, traffic selectors with Auto Route Insertion,
more than one spoke, and certificate authentication (`references/mnha-ipsec.md` lists
what is and is not tested).

## Runtime intake

Before starting the workflow, inspect the request, supplied artifacts, and available approved read-only evidence. If unresolved facts could materially change safety, scope, correctness, confidence, or the requested output, read `references/runtime-intake.md`. For each unresolved material fact whose catalog condition is true, invoke Claude `AskUserQuestion` or Codex `request_user_input` before continuing or issuing an open-ended request. Ask at most three single-select catalog questions per round. After each response, ask another round whenever any unresolved material catalog condition remains true; continue only when none remain. Do not repeat answered questions or show the full catalog. Without a native tool, present each selected catalog question with its 2-3 labeled choices and a free-text `Other` path in concise plain text; do not substitute a generic checklist. Never request secrets or unredacted customer data. Treat intake answers as task context, not approval for a live change; obtain separate explicit approval before configuration, commit, upgrade, reboot, delete, or failover actions.

## Step 0 - Facts and safety

Every tool named here belongs to the connected Junos MCP server. Call it under that
server's qualified name in your client. Without a Junos MCP server, give the user the
CLI commands and ask them to paste the output.

1. `get_router_list`: confirm both hub nodes, the spoke and the upstream router by
   exact name.
2. `show version` on all devices: the same release on both hub nodes, and "JUNOS ike"
   present. `show chassis high-availability services-redundancy-group 1` on both hub
   nodes: exactly one ACTIVE, both HEALTHY.
3. Rescue config on every device (both hub nodes and the spoke): run
   `show system configuration rescue`. If none exists, `request system configuration
   rescue save`. If one already exists, get explicit approval before replacing it
   (`request system configuration rescue save` overwrites the known-good rescue).
4. Baselines: `show configuration | display set` on each device, saved as
   `<router>.set`. Prefer it over `get_junos_config`, which can hide `deactivate`d
   stanzas (`references/mcp-server-notes.md`). Baseline files contain secrets unless
   the server account reads them as `SECRET-DATA`. Keep them local.

## Step 1 - Ask the goal first

Ask this **on every run**, even if the answer seems known. Offer tappable options
where the client supports them:

| Goal | What it configures | Relative result (vs flag OFF, planned failover) | Cost |
|---|---|---|---|
| **Least traffic loss on planned failover** | `process-packet-on-backup` ON + floating statics | data loss about -100 % in both directions | tunnel BFD/BGP recovery about +70 %; **replay log messages may appear on the peer during failover** |
| **Fastest BGP/BFD recovery, simplest** | flag OFF + floating statics | baseline recovery time | hub-to-spoke planned loss about 4 x the spoke-to-hub loss |
| **Quiet logs** (flag ON) | flag ON + `no-anti-replay` on the peer (+ clear SAs) | replay messages to 0, timing unchanged (0 %) | removes replay protection on that tunnel |

Say plainly: **for unplanned failures (an uplink dies) the flag makes no material
difference**; the outage is about 75-120 % of the configured BFD detection time,
whatever the flag. The flag only helps planned switchovers. These percentages come
from a small virtual lab: measure your own flag-OFF baseline first.

**If the flag will be on, always tell the user:** `RT_IPSEC_REPLAY` messages may be
logged on the peer during failover (and occasionally at child-SA rekey). They were
reproducible and harmless in testing; do not turn anti-replay off just to hide them.

## Step 2 - VPN sheet

Follow `references/intake-questions.md`. Never pre-fill silently from memory, an
earlier run or the devices: discovered values are only *suggested defaults* that the
user confirms. At most three questions per round. Fill a copy of
`references/vpn-sheet.example.yaml` (a filled example is in
`references/example.yaml`), show the **complete** sheet and get one explicit
"confirmed".

## Step 3 - Write and check the config files (nothing touches devices)

Write the files from `references/config-blocks.md` by substituting the sheet values
into its placeholder blocks:

- per hub node: `hub.set` (identical on both nodes) and `undo-hub.set`
- for the spoke: `spoke.set`, `undo-spoke.set`, `cutover.set` and `undo-cutover.set`

The goal decides three switches (resolution table in `references/config-blocks.md`):
`process-packet-on-backup`, floating statics, and spoke anti-replay.

Then walk the **pre-push checklist** in `references/config-blocks.md` against the sheet,
the written files and each baseline:

- **Any Blocking item stops the run.** Fix the sheet and rewrite the files.
- **Needs Acknowledgment** items need a one-line OK from the user.
- **Tell the User** items are context.

Undo files are valid only against the baseline they were computed from; dry-run an
undo before relying on it. If a written line would replace an existing single-valued
leaf, stop (Blocking): a delete cannot restore the old value. `ALLOW-IKE-ESP` (intra-zone
IKE and ESP, scoped spoke → anchor and anchor → spoke) is **mandatory** and always
written: it can show 0 hits and must still stay (`references/mnha-ipsec.md`). Never
hand-edit a checked file; change the sheet and rewrite.

## Step 4 - Dry run on the devices

Dry-run each file on its device with the server's dry-run capability
(`references/mcp-server-notes.md`): one router per call, `config_format: "set"`. Also
dry-run each undo file against the current config to see exactly what it would
remove. Show the user the diffs and the checklist result.

## Step 5 - Approval gate, then Phase A: build the tunnel

Phase A brings the tunnel up while the spoke's bypass static stays in place. The hub
starts returning traffic for the spoke prefixes into `st0` as soon as this phase
commits (BGP import and/or floating statics are more specific than a default), so
existing flows that still take the bypass black-hole until Phase B. Warn the user
about that asymmetric window. Get explicit approval to push the hub and spoke files;
approval of the sheet or the dry run is not approval to push.

Push each device **with commit confirmed** (`confirm_timeout_mins: 5`), verify, then
confirm. If the server has no commit confirmed, see `references/mcp-server-notes.md`
before pushing.

1. **Hub backup node first**, verify its SRG state, then the **active node**.
   Adding `managed-services ipsec` to a running SRG **restarts it**: on the active node
   the VIP was withdrawn for minutes in testing. Use a maintenance window, or do this
   during the initial MNHA build. Re-check both nodes' SRG state between pushes.
2. **Spoke** (the bypass static stays in place).
3. Verify:
   - `show security ike security-associations` and
     `show security ipsec security-associations` on the spoke
   - on the hub, `show security ipsec security-associations` (the ICL's own SA is listed
     under `... ha-link-encryption`)
   - tunnel BGP Established and BFD Up on the spoke
   - the **same SPIs on both hub nodes** (the SA is synced)
   - the upstream router learns the anchor /32 with the active MED from the active
     node only
4. If the tunnel does not come up:
   - empty IKE/IPsec output on the spoke means no IKE process (install `junos-ike` and
     have the user reboot)
   - the hub initiating with no replies points at the underlay path or the intra-zone
     policy (`references/mnha-ipsec.md`)

## Step 6 - Phase B: cutover

Only after the tunnel BGP is Established and the hub subnets are learned over `st0`:

1. Get approval, then push `cutover.set` on the spoke with `confirm_timeout_mins: 3`.
2. Check transit traffic **immediately**: the hub already returns traffic into the
   tunnel, so any delay is an asymmetric black hole.
3. Confirm the commit. If the tunnel route does not take over within the timer, the
   bypass static comes back by itself.

## Step 7 - Failover tests

Each test needs its own approval and loads **both directions**. The method is in
`references/testing.md`; every traffic-generation and failure-trigger command is in
`references/traffic-generation.md`. A traffic-generator MCP server is optional: with
one the assistant runs the commands, without one the user runs them and pastes the
output.

- Measure the **baseline first** (flag OFF, your timers), then each variant, and report
  the **% change versus that baseline** per direction. Never quote another lab's
  seconds as a target.
- Bidirectional UDP for 150 s; planned failover at about 20 % of the run, failback at
  about 65 %. Report UDP loss, not the TCP stall.
- Read the spoke's BFD/BGP downtime and replay messages from the `tunnel-ev` syslog
  file written in `spoke.set`.
- Unplanned: disable the underlay uplink on the ACTIVE hub node with
  `confirm_timeout_mins: 2` (it restores itself). Never confirm that commit. Check that
  the commit time falls inside the stream window. Until it has rolled back, run only
  read-only commands on that node: a dry run, commit check or other push there would
  confirm it and leave the uplink disabled.
- Before failing back, wait until the recovered node's BGP is Established upstream.
- Recommended extra: a forced child-SA rekey under load with the flag on (idle flaps at
  rekey were seen and are not explained).

## Step 8 - Report

Deliver the VPN sheet, the written files, verification evidence, the measured table,
the rollback order (`undo-cutover` → `undo-spoke` → `undo-hub` on the hub nodes, backup
node first), and the replay-log notice if the flag is on. Do not include baseline
files in the report.

## Guardrails

- Every push uses commit confirmed where the server supports it; confirm only after the
  checks pass. After any timeout or disconnect, read `show system commit` before
  retrying: a call can complete on the device while its reply is lost.
- While a commit confirmed is pending on a device, run only read-only commands there. On
  Junos a dry run, commit check or commit confirms it (see
  `references/mcp-server-notes.md`).
- Never touch `fxp0`, `system services`, logins or `mgmt_junos`. Never handle the
  pre-shared key.
- Baseline files contain secrets unless the server account reads them as SECRET-DATA.
  Keep them local, never include them in the Step 8 report, and delete them when the
  run ends.
- One router per MCP call; push the hub **backup node first**.
- Don't load only one direction in a test, and don't trust a 0-loss result until the
  event timestamps are inside the stream window.

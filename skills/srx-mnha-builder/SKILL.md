---
name: srx-mnha-builder
description: Build a new two-node SRX/vSRX Multi-Node High Availability pair from standalone nodes over a Junos MCP server, covering routing, switching or hybrid mode, dedicated or shared ICL, pair sheet, staged configs with pre-push checks and approval gates, HA-activation reboot, formation checks and failover test. Use when standing up an MNHA pair or turning two SRXs into HA. For design or troubleshooting a running pair, use srx-mnha.
version: 0.2.2
author:
  - fastrevmd-lab
  - Claude
  - GPT
  - jgrizzuti
license: MIT
metadata:
  hermes:
    tags: [srx, vsrx, junos, mnha, high-availability, srg, icl, bfd, bgp, signal-route, vip, ha-link-encryption, mcp, approval-gate, failover-test]
    related_skills: [srx-mnha, srx-cluster-to-mnha, srx-policy, srx-nat, parsing-srx-configs]
---

# SRX MNHA Pair Builder

## Contents

- [Runtime intake](#runtime-intake)
- [Step 0 - Targets and facts](#step-0---targets-and-facts)
- [Step 1 - Baseline and safety net](#step-1---baseline-and-safety-net)
- [Step 2 - Select the deployment mode](#step-2---select-the-deployment-mode)
- [Step 3 - Pair sheet](#step-3---pair-sheet)
- [Step 4 - Write and check stage files (nothing touches devices)](#step-4---write-and-check-stage-files-nothing-touches-devices)
- [Step 5 - Dry run on devices](#step-5---dry-run-on-devices)
- [Step 6 - Approval gate #1](#step-6---approval-gate-1)
- [Step 7 - Stage 1: underlay](#step-7---stage-1-underlay)
- [Step 8 - Stage 2: HA stanza](#step-8---stage-2-ha-stanza)
- [Step 9 - Reboot handoff (approval gate #2)](#step-9---reboot-handoff-approval-gate-2)
- [Step 10 - Verify formation](#step-10---verify-formation)
- [Step 11 - Stage 3: eBGP (routing and hybrid; approval gate #3)](#step-11---stage-3-ebgp-routing-and-hybrid-approval-gate-3)
- [Step 12 - Failover test (approval gate #4, recommended)](#step-12---failover-test-approval-gate-4-recommended)
- [Step 13 - As-built report](#step-13---as-built-report)
- [Guardrails](#guardrails)

This skill turns two standalone SRX nodes into an MNHA pair through a Junos MCP server
and never pushes anything without explicit approval. Design knowledge (modes, SRGs,
pitfalls) lives in the `srx-mnha` skill. This skill is about **choosing the mode and
building the pair in a safe order**.

**Scope:**
- A new pair, built from two nodes with no chassis cluster and no existing
  `chassis high-availability`. To convert an existing cluster, see
  `srx-cluster-to-mnha`. Existing interfaces, zones and an eBGP group may be
  reused if they match the pair sheet.
- SRG0 plus one SRG1.
- The ICL in the default routing instance, either on a dedicated link or as loopbacks
  over a shared data segment, encrypted or not.
- **Out of scope:** ICD, multiple SRG1+ groups, OSPF, security policies
  and NAT, and MNHA IPsec. MNHA IPsec will be its own skill.
- An existing IPsec setup on a node is left untouched. It stays tied to that node and
  will **not** fail over. Tell the user so, and never add `managed-services ipsec`.

**Naming:** Node0 maps to MNHA `local-id 1` and Node1 to `local-id 2`. Node0 gets the
higher `activeness-priority`, so it is the SRG1 ACTIVE node by default.

Read `references/mcp-server-notes.md` before starting for tool mappings and server-specific behavior.

## Runtime intake

Before starting the workflow, inspect the request, supplied artifacts, and available approved read-only evidence. If unresolved facts could materially change safety, scope, correctness, confidence, or the requested output, read `references/runtime-intake.md`. For each unresolved material fact whose catalog condition is true, invoke Claude `AskUserQuestion` or Codex `request_user_input` before continuing or issuing an open-ended request. Ask at most three single-select catalog questions per round. After each response, ask another round whenever any unresolved material catalog condition remains true; continue only when none remain. Do not repeat answered questions or show the full catalog. Without a native tool, present each selected catalog question with its 2-3 labeled choices and a free-text `Other` path in concise plain text; do not substitute a generic checklist. Never request secrets or unredacted customer data. Treat intake answers as task context, not approval for a live change; obtain separate explicit approval before configuration, commit, upgrade, reboot, delete, or failover actions.

## Step 0 - Targets and facts

**MCP server requirement:** Every tool named in this skill (`get_router_list`,
`gather_device_facts`, `execute_junos_command`, `commit_check_config`, ...) belongs to the
connected Junos MCP server (rust-junosmcp or Juniper junos-mcp-server). Call it under that
server's qualified name in your client (for example `<server-name>:gather_device_facts`,
or `mcp__<server-name>__gather_device_facts` in Claude Code). If no Junos MCP server is
available, fall back to manual CLI commands (`show chassis cluster status`,
`show chassis high-availability information`, etc.) and ask the user to paste the output.
Tool mappings and server-specific behavior are in `references/mcp-server-notes.md`.

1. Call `get_router_list` and confirm both device names exist exactly as the user gave
   them.
2. Run `gather_device_facts` on each node. **Stop** if the models or `version` differ.
3. Run `execute_junos_command` with `show chassis cluster status` on each node. **Stop**
   if either node is clustered. To plan converting an existing cluster, use `srx-cluster-to-mnha` first; this skill builds only from standalone nodes.
4. Run `execute_junos_command` with `show chassis high-availability information` on each
   node. Expect *mode not configured*. If a node shows an MNHA configuration, it isn't a
   new node: stop and hand back to the user to clean it and reboot.
5. Ask the user to confirm they have **console / out-of-band access to both nodes**.
   This is a hard prerequisite for both servers, because a bad commit can cut management
   access; commit confirmed (where the server has it) is a backstop, not a substitute.

## Step 1 - Baseline and safety net

1. Run `get_junos_config` on both nodes and save the output as `<router>.set`.
2. Run `request system configuration rescue save` on both nodes.
3. From the baselines, note:
   - free interfaces, and the interfaces that already exist with their addresses and
     zones
   - the `fxp0` addressing
   - any static default route
   - any existing autonomous-system number or BGP group

The baseline must be re-taken if anyone changes a node before Step 6. The undo files
are computed from it.

## Step 2 - Select the deployment mode

Ask this before anything else in the pair sheet, because the mode decides which
sections are required. See `srx-mnha` → Deployment Modes for design guidance. Offer
a recommendation based on what the user describes:

| Mode | `deployment-type` | Skill builds |
|---|---|---|
| **Routing (L3)** | `routing` | Signal routes, eBGP group, route-filtered export with MEDs. Activeness probe required. |
| **Switching (default-gateway / L2)** | `switching` | VIPs, uplink monitoring. No BGP. |
| **Hybrid** | `hybrid` | VIPs, monitoring, signal routes and eBGP. |

To help the user choose, ask:
1. Do any directly attached hosts use the firewall's address as their static default
   gateway?
2. Can the upstream run eBGP with both nodes?

If the answers are yes / yes, the mode is hybrid. No / yes means routing. Yes / no means
switching. See `srx-mnha` → Deployment Modes for the per-segment failover consequences
and vMAC-move caveats (DAI, storm-control, MAC-move limits).

### ICL questions (asked right after the mode)

**1. Dedicated or shared ICL?**

| ICL transport | What it is | Skill builds |
|---|---|---|
| **Dedicated** (recommended) | Its own back-to-back link, e.g. `ge-0/0/2` ↔ `ge-0/0/2`, /30 | Link addresses in a dedicated ICL zone |
| **Shared** | Loopback /32s reached over a data segment, used when no spare port or path exists | `lo0.<unit>` in the ICL zone, a static /32 route to the peer loopback, and HA/BFD (+IKE) host-inbound opened on the transport segment's zone |

**2. Encrypted or not?** Recommend encryption whenever the ICL is shared or crosses
anything the user doesn't control. See `srx-mnha` → ICL for conceptual guidance. Two
prerequisites the skill checks but cannot set:
- **`junos-ike` package on both nodes.** Check the `show version` output for
  "JUNOS ike". If it's missing, the user installs it
  (`request system software add optional://junos-ike.tgz`); a reboot may be needed.
- **The pre-shared key, set by the user on both nodes via CLI**, before the baseline is
  taken:
  `set security ike policy MNHA-ICL-IKE-POL pre-shared-key ascii-text <key>`.
  The key never goes into the sheet, the chat or an MCP push. The pre-push checklist
  blocks until the line appears in both baselines. The skill then adds everything else:
  proposals, gateway, VPN, `vpn-profile`, and IKE host-inbound.

Field-confirmed 2026-09-25: the encrypted-ICL stanza (`ha-link-encryption` + `peer-id …
vpn-profile`) commit-checks on vSRX 24.4R2.21 (flat model). On the grid model (26.x) the
`vpn-profile` placement is not confirmed, so treat the device dry run as the authority there.

## Step 3 - Pair sheet

1. Copy `references/pair-sheet.example.yaml` and set `deployment_mode` first.
2. Fill the sheet from the facts and baseline. Ask the user only for what is still
   missing, at most three questions per round.
3. Never ask for secrets.

What each mode needs:
- **All modes:** `icl.transport` and `icl.encryption.enabled`, then ICL interface and IPs
  (dedicated) or segment, loopback unit and loopback IPs (shared), segments (the IFL name is shared; each node has
  its own address), activeness priorities.
- **Routing and hybrid:** `bgp` (local and peer AS, group, BFD, protected prefixes with
  a match type, transit subnets), per-node `bgp_neighbors`, and exactly one segment with
  `role: upstream`. Routing mode also needs a per-node `probe`.
- **Switching and hybrid:** `srg1.vips` (the VIP must sit inside that segment's subnet
  on both nodes) and `monitor_interfaces`.

If a BGP group, zone or interface already exists in the baseline, the sheet must match
it. The pre-push checklist catches conflicts, such as a group that already exports another
policy or a different autonomous-system number.

## Step 4 - Write and check stage files (nothing touches devices)

1. Read `references/config-stages.md`, which contains all stage blocks with placeholders.
2. For each node, write `stage1.set`, `stage2.set`, and `stage3.set` (routing/hybrid only)
   by substituting `<PLACEHOLDER>` values from the pair sheet and baseline facts into the
   stage blocks. Include or exclude conditional blocks based on the mode, ICL transport,
   encryption, and config model as the stage reference directs.
3. Write matching `undo-stageN.set` files following the undo rules in
   `references/config-stages.md`. Undo files delete only what their stage **adds** relative
   to the baseline — pre-existing config that a stage merely re-states is never removed.
4. Walk the pre-push checklist in `references/config-stages.md` for both nodes.
   - **Any Blocking item means stop.** Fix the pair sheet or baseline, then rewrite the
     stage files.
   - **Needs Acknowledgment items** require a one-line user OK before proceeding.
   - **Tell the User items** are informational context.

Output per node:
- `stage1.set`: underlay (ICL transport, data segments, zones, host-inbound rules)
- `stage2.set`: ICL crypto objects (when encrypted), plus the HA stanza for the chosen mode
  and flat or grid model
- `stage3.set`: eBGP and the export policy (routing and hybrid only)
- matching `undo-stageN.set` files

## Step 5 - Dry run on devices

For every node, dry run stage 1 alone and stages 1+2+3 concatenated (later stages reference
earlier ones). Use the commit-check/dry-run tool (see `references/mcp-server-notes.md` for
server-specific mappings):
- **rust-junosmcp:** prefer `commit_check_config` with `device`, `config_text` (the
  rendered stage), and `config_format: "set"`; if not available, `render_and_apply_j2_template`
  with `apply_config: true, dry_run: true`
- **Juniper junos-mcp-server:** `render_and_apply_j2_template` with `apply_config: true,
  dry_run: true`
- junos-mcp-server with commit confirmed: `load_and_commit_config` with `config_text` (the
  rendered stage), `config_format: "set"` and `dry_run: true`, or the J2 tool as above

Template parameters (when using the J2 tool):
- `template_content` = the rendered stage text
- `vars_content: "{\"skill\": \"srx-mnha-builder\"}"` (string containing a one-key JSON object; empty `{}` is rejected by Juniper's server)
- `config_format: "set"`

Also dry-run each `undo-stageN.set` against the current config. This shows exactly what
an undo would remove.

## Step 6 - Approval gate #1

1. Show the user the per-node diffs, the pre-push checklist results, and the undo files.
2. Get explicit approval to push Stage 1 and Stage 2. Approval of the design or the dry
   run is not approval to push.

## Step 7 - Stage 1: underlay

1. Push `stage1.set` on Node0, then on Node1. Use the push tool (see
   `references/mcp-server-notes.md` for server-specific mappings):
   - **rust-junosmcp:** `create_junos_change_set` (preview/diff) → `approve_junos_change_set`
     → `apply_junos_change_set` with `confirm_timeout_mins: 10` → verify →
     `confirm_junos_change_set`. Direct-commit tools (`load_and_commit_config`) are refused
     unless the operator enabled `--allow-direct-commit`; if so, use `load_and_commit_config`
     with `confirm_timeout_mins: 10`, then a plain follow-up commit. The user's chat
     approval at each gate is required; server-side approval (or lab-mode auto-approval) is
     not user approval.
   - **junos-mcp-server with commit confirmed:** `render_and_apply_j2_template` with
     `apply_config: true, dry_run: false, confirm_timeout_mins: 10` → verify →
     `confirm_commit` on each node. Push both nodes inside one window, because the ICL
     checks need both. Never confirm by re-sending `load_and_commit_config`.
   - **Juniper junos-mcp-server:** `render_and_apply_j2_template` with `apply_config: true,
     dry_run: false` (runs commit check before committing; no commit confirmed)
2. Verify per `references/verification.md` → "After Stage 1":
   - ICL ping, including the 1400-byte DF ping
   - each segment's neighbor answers ping
3. If verification fails: with a confirmed commit still pending, do not confirm, let it
   roll back, wait past the window with margin and check the diff against the baseline;
   otherwise run `undo-stage1`. Diagnose before going on.

## Step 8 - Stage 2: HA stanza

1. Push `stage2.set` on Node0, then Node1, using the same push tool/confirm flow as Step 7.
2. Run the config diff against rollback 1 on each node as evidence (see `mcp-server-notes.md`).
3. Confirm the Stage 2 commit before the user reboots — do not leave a commit-confirmed
   window open across the HA-activation reboot.

## Step 9 - Reboot handoff (approval gate #2)

This skill never reboots a device; the user performs the reboot.

1. Ask the user to reboot **Node1 first**, then Node0 once Node1 is back.
   **Expected side effect:** while Node0 reboots, Node1 goes from HOLD to SRG1 ACTIVE and takes the
   VIP. With preemption off, it stays ACTIVE after Node0 returns, even though Node0 has the higher
   priority (field-confirmed 2026-09-25). Tell the user this before the reboot. If they want
   Node0 ACTIVE, a manual SRG1 failover (approval gate) restores it and doubles as the first
   failover test.
2. After each reboot, expect the first MCP call to time out. Retry once with a short
   `timeout`, then confirm the node with `gather_device_facts`.
3. On vSRX, if `show interfaces terse` lists no `ge-` interfaces, the user needs a full
   VM stop and start.
4. With an encrypted ICL, also check `show security ike security-associations` and
   `show security ipsec security-associations` for the ICL peer once both nodes are up.

## Step 10 - Verify formation

Run the "After Stage 2 + reboot" checks on both nodes with the batch execution tool
(`execute_junos_command_batch` on rust-junosmcp, or individual `execute_junos_command`
calls on Juniper junos-mcp-server). For switching and hybrid modes, also run the VIP checks.

- **Pass:** both ONLINE, Conn State UP, Cold Sync COMPLETE, and exactly one SRG1 ACTIVE,
  the higher-priority node.
- **Fail:** follow the diagnostic tree. The BFD permit comes first.

## Step 11 - Stage 3: eBGP (routing and hybrid; approval gate #3)

1. Get approval, then push `stage3.set` on both nodes using the same change-set or
   direct-commit flow as Step 7.
2. The upstream router must have both nodes configured as neighbors. If the upstream is
   MCP-managed, read its config first. It often already has a group for Node0; the smallest
   change is to add Node1 as another neighbor in that group, after a dry run. Otherwise ask the
   user to configure it.
3. Verify:
   - BGP sessions established, with BFD up if configured
   - the **role-consistency invariant** in `references/verification.md`: the SRG1 ACTIVE node,
     the VIP holder, the node with the active signal route, and the upstream's selected BGP path
     are all the same node
4. Re-check the invariant after every failover or failback in Step 12. It is the pass criterion
   for "the failover worked".

## Step 12 - Failover test (approval gate #4, recommended)

Follow the failover section of `references/verification.md`. Confirm the
manual-failover syntax on the target release before running it. For switching and
hybrid modes, include the VIP move and the ARP refresh on a host in the checks.

## Step 13 - As-built report

Deliver:
- the pair sheet
- the per-node stage files
- key verification lines
- test results
- the rollback procedure: `undo-stage3` → `undo-stage2` → reboot (user) → `undo-stage1`,
  with the rescue config as the last resort from the console

## Guardrails

- Every push needs explicit, stage-specific approval.
- Push Node0 then Node1, and verify between stages.
- Never edit stage files in isolation; change the pair sheet and rewrite them from
  `references/config-stages.md`.
- Never touch `fxp0`, system services, logins or `mgmt_junos`.
- If a commit's result is unclear because the connection dropped, check the config diff
  against rollback 1 (see `mcp-server-notes.md`) before retrying.
- Undo files are only valid against the baseline they were computed from.

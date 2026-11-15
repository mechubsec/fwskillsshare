# Junos MCP server notes for this workflow

## Contents

- [Identify the server](#identify-the-server)
- [Capability mapping](#capability-mapping)
- [Without commit confirmed](#without-commit-confirmed)
- [Field notes](#field-notes)

Each step names the capability it needs ("dry run", "push with commit confirmed",
"confirm"). This file maps those capabilities to the tools of each Junos MCP server.
Decide from the tool list the server exposes, not from its name.

## Identify the server

- **rust-junosmcp** (Mechub, listed first): exposes `commit_check_config` and
  `create_junos_change_set`.
- **Juniper junos-mcp-server (v1.1.1)**: none of the commit-confirmed tools. No commit
  confirmed.
- **junos-mcp-server with commit confirmed**: exposes `confirm_commit`, and
  `load_and_commit_config` takes `confirm_timeout_mins`. This is Juniper's own `main`
  since [Juniper/junos-mcp-server#34](https://github.com/Juniper/junos-mcp-server/pull/34)
  merged on 2026-11-02; no tagged release includes it yet (v1.1.1 is the latest tag).
  The [`jgrizzuti/junos-mcp-server`](https://github.com/jgrizzuti/junos-mcp-server) fork
  it was developed in now matches upstream `main`.

## Capability mapping

| Capability | rust-junosmcp | Juniper junos-mcp-server (v1.1.1) | junos-mcp-server with commit confirmed (Juniper `main` since #34) |
|---|---|---|---|
| **Read baseline** | `execute_junos_command` with `show configuration \| display set` | same | same |
| **Op commands** | `execute_junos_command`; `execute_junos_command_batch` for both hub nodes | `execute_junos_command`, once per router | `execute_junos_command`; `execute_junos_command_batch` for both hub nodes |
| **Dry run** | `commit_check_config` (never commits) | `render_and_apply_j2_template` with `apply_config: true, dry_run: true` | `load_and_commit_config` with `dry_run: true`, or `render_and_apply_j2_template` with `apply_config: true, dry_run: true` |
| **Push with commit confirmed** | `load_and_commit_config` with `confirm_timeout_mins: N`, or a change set applied with `confirm_timeout_mins` | **Not available**: see below | `load_and_commit_config` with `confirm_timeout_mins: N` |
| **Confirm** | another `load_and_commit_config` without `confirm_timeout_mins`, or `confirm_junos_change_set` | n/a | `confirm_commit` (`router_name`) |
| **Diff after commit** | `junos_config_diff` with `version: 1` | same | same |

Notes:

- **A commit check confirms a pending commit, on every server.** On Junos, a `commit
  check` or `commit` issued while a `commit confirmed` is pending confirms it and cancels
  the automatic rollback, without adding a commit entry. While a commit is pending on a
  device, run only read-only commands there: no dry run, commit check, or other push.
  This matters most for the self-restoring uplink test, which is never meant to be
  confirmed. A pending commit shows `rollback pending` on entry 0 of `show system
  commit`. Verified on vSRX 24.4R2.21, 2026-10-05: a dry run inside a 3-minute window
  made the change permanent while reporting that nothing was committed.
- **junos-mcp-server with commit confirmed refuses those calls itself.**
  `load_and_commit_config` and `render_and_apply_j2_template`, dry run included, return
  `Error: a commit confirmed is pending on <router>…` instead of loading anything: confirm
  the pending change, or let it roll back. The other servers are not verified to refuse,
  so the skill must hold the rule there.
- **`confirm_commit` with nothing pending** returns `Error: No pending commit confirmed on
  <router>; nothing to confirm`, usually because the window expired and the change rolled
  back. Re-check before treating the change as live.
- **Do not confirm by re-sending the same config** on junos-mcp-server with commit
  confirmed: with no diff it commits nothing, and the rollback still fires. Use
  `confirm_commit`.
- **Pushing written text through the J2 tool:** pass the written file as
  `template_content`, `config_format: "set"`, and a one-key dummy mapping as
  `vars_content` (`"skill: srx-mnha-ipsec-builder"` on Juniper's server, a JSON object
  string on rust-junosmcp). An empty `{}` is rejected. The files contain no template
  syntax, so what the device receives is byte-for-byte what was checked.
- **rust-junosmcp change sets** need a second-principal approval unless the server runs
  in `--lab-mode`. A server-side approval is never a substitute for the user's approval
  in chat at each gate.

## Without commit confirmed

On Juniper junos-mcp-server v1.1.1 nothing auto-reverts. Dry runs and pre-push checks
still work, but:

- Phase A pushes (hub and spoke files) use the J2 tool with `dry_run: false`, which runs a
  commit check before committing. Have the undo files dry-run and ready first.
- **Hand the cutover and the unplanned-failure trigger to the user at the CLI** with
  `commit confirmed 3` (cutover) or `commit confirmed 2` (uplink down), followed by
  `commit` once the check passes. These two steps depend on the automatic rollback.
- Do not use `load_and_commit_config` for a forward push on this server: it commits
  without a commit check.

## Field notes

Observed with junos-mcp-server (commit-confirmed fork) on vSRX 24.4:

- **One router per call.** Multi-router config calls have hung. A 4-minute hang with
  `load_and_commit_config` usually means an unanswered tool-approval prompt in the
  desktop client; `render_and_apply_j2_template` stayed responsive meanwhile.
- **After a timeout or disconnect** read `show system commit` and the audit log before
  retrying: a call can complete on the device while its reply is lost.
- **Baselines:** prefer `show configuration | display set` over `get_junos_config`,
  which was observed to hide `deactivate`d stanzas.
- **Pipes are ignored** by Juniper's server (`| match`, `| last`). Large outputs:
  `show log messages` passed the 1 MB limit. The spoke file already adds the filtered
  `tunnel-ev` syslog (approval and undo ride with Phase A). If it is missing, add it
  with the same lines, an approval, and an undo; it records only new events:

  ```junos
  set system syslog file tunnel-ev any any
  set system syslog file tunnel-ev match "BFDD_STATE_UP_TO_DOWN|BFDD_TRAP_SHOP_STATE_UP|RT_IPSEC_REPLAY|bgp_bfd_callback"
  ```

- **Account:** run the server as a least-privilege user (example class `mcp-operator`),
  never `admin`. Such an account cannot reboot, install software, open a shell, change
  `system login` or `system services`, or run `monitor traffic`: those steps belong to
  the user. `clear security ipsec security-associations` is allowed. Secrets read as
  `SECRET-DATA`.
- **Clocks:** check them (`show system uptime`) before correlating logs between devices.
  A device on `LOCAL CLOCK` can be hours off; work out the offset by matching two events
  to your own command times.
- **Traffic-generator MCP server (optional),** for example a Kali MCP server: run long
  commands with `nohup ... &` and poll with short calls. Do not use `pkill -f` in the
  same command (it matches and kills its own shell). Without one, the user runs the
  commands in `traffic-generation.md`.
- **Reboots are blocked** by the server: hand them to the user. Do not edit the
  blocklist to get around this.
- **Idle pool timeout** (300 s by default): after a reboot or a long pause the first
  call may fail. Retry once with a short `timeout`.

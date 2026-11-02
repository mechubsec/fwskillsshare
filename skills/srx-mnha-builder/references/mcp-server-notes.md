# Junos MCP server comparison and capability mapping

## Contents

- [Identify the server](#identify-the-server)
- [Capability mapping](#capability-mapping)
- [Juniper junos-mcp-server](#juniper-junos-mcp-server)
- [rust-junosmcp](#rust-junosmcp)

This workflow uses a Junos MCP server and is compatible with Juniper's
junos-mcp-server (v1.1.1), junos-mcp-server with commit confirmed, and
rust-junosmcp. Each step names the capability it needs ("dry run the stage", "push
with commit confirmed"), and this file maps those capabilities to the tools each
server exposes.

## Identify the server

- **rust-junosmcp**: exposes `commit_check_config` and `create_junos_change_set`.
- **junos-mcp-server with commit confirmed**: exposes `confirm_commit`, and
  `load_and_commit_config` takes `confirm_timeout_mins`, but neither rust-junosmcp
  tool (ten tools). This is Juniper's own `main` since
  [Juniper/junos-mcp-server#34](https://github.com/Juniper/junos-mcp-server/pull/34)
  merged on 2026-11-02; no tagged release includes it yet (v1.1.1 is the latest tag).
  The [`jgrizzuti/junos-mcp-server`](https://github.com/jgrizzuti/junos-mcp-server)
  fork it was developed in now matches upstream `main`.
- **Juniper junos-mcp-server (v1.1.1)**: exposes none of those; the core surface is
  `get_router_list`, `gather_device_facts`, `execute_junos_command`,
  `get_junos_config`, `junos_config_diff`, `load_and_commit_config`,
  `render_and_apply_j2_template`.

Decide from the tool list, not the server's name.

### A commit check confirms a pending commit (every server)

On Junos, a `commit check` or `commit` issued while a `commit confirmed` is pending
**confirms it** and cancels the automatic rollback, without adding a commit entry. A dry
run is therefore not side-effect-free inside a confirm window. **Verified on vSRX
24.4R2.21, 2026-10-05:** a dry run inside a 3-minute window made the change permanent
while reporting that nothing was committed.

While a stage's commit is pending on a node, run only read-only commands on that node:
no dry run, commit check, or other push. A pending commit shows `rollback pending` on
entry 0 of `show system commit`. junos-mcp-server with commit confirmed enforces this
itself (see its section below); the other servers are not verified to, so the skill must.

## Capability mapping

| Capability | Juniper junos-mcp-server (v1.1.1) | junos-mcp-server with commit confirmed | rust-junosmcp |
|---|---|---|---|
| **List devices** | `get_router_list` | `get_router_list` | `get_router_list` |
| **Gather facts** | `gather_device_facts` | `gather_device_facts` | `gather_device_facts` |
| **Read config baseline** | `get_junos_config` (set format) | `get_junos_config` (set format) | `get_junos_config` with `format: "set"` (v0.26.0+; on older versions use `execute_junos_command` with `show configuration \| display set` or upgrade) |
| **Op commands (single router)** | `execute_junos_command` | `execute_junos_command` | `execute_junos_command` |
| **Op commands (batch, both nodes)** | run twice (sequential or parallel client-side) | `execute_junos_command_batch` (parallel server-side) | `execute_junos_command_batch` (parallel server-side) |
| **Diff vs rollback N** | `junos_config_diff` with `version: <N>` | `junos_config_diff` with `version: <N>` | `junos_config_diff` with `version: <N>` |
| **Commit check / dry run** | `render_and_apply_j2_template` with `apply_config: true, dry_run: true` (loads, checks, diffs, rolls back) | `load_and_commit_config` with `dry_run: true`, or `render_and_apply_j2_template` with `apply_config: true, dry_run: true` | `commit_check_config` (never commits) or `render_and_apply_j2_template` with `apply_config: true, dry_run: true` |
| **Push (direct commit)** | `load_and_commit_config` (**skips commit check**, no commit confirmed) or `render_and_apply_j2_template` with `apply_config: true, dry_run: false` (runs commit check before committing) | `load_and_commit_config` or `render_and_apply_j2_template` with `apply_config: true, dry_run: false` (both run a commit check before committing) | `load_and_commit_config` with optional `confirm_timeout_mins` (commit confirmed N) |
| **Push with commit confirmed** | **Not available** | `load_and_commit_config` or `render_and_apply_j2_template` with `confirm_timeout_mins` | `load_and_commit_config` with `confirm_timeout_mins` |
| **Confirm commit** | **Not available** (no confirmed-commit support) | `confirm_commit` (a repeated `load_and_commit_config` does **not** confirm: with no diff it commits nothing) | `load_and_commit_config` (another commit without confirm_timeout_mins) |
| **Change-set flow** | **Not available** | **Not available** | `create_junos_change_set` → `approve_junos_change_set` → `apply_junos_change_set` (accepts `confirm_timeout_mins`) → `confirm_junos_change_set` |
| **Rollback** | **Not available** (no `rollback_config` tool; push the pre-rendered `undo-stageN.set` file with `load_and_commit_config` for a dry-run-first rollback, or hand off to the operator for `rollback <N>` + `commit` at the CLI/console) | Let a pending confirmed commit expire, or push the `undo-stageN.set` file with `load_and_commit_config` (`dry_run: true` first); no `rollback_config` tool | `rollback_config` with `commit: true` (if `--allow-direct-commit`) or change-set with `rollback_source: <N>` |

## Juniper junos-mcp-server

Verified against the Juniper/junos-mcp-server source (jmcp.py). Re-check if the
server version changes.

### Tools and their real behavior

| Tool | Behaviour that matters |
|---|---|
| `get_router_list` | Names returned here are the only valid `router_name` values. |
| `gather_device_facts` | PyEZ facts: hostname, model, version, serial. Use for Step 0. |
| `get_junos_config` | Runs `show configuration \| display inheritance no-comments \| display set \| no-more`. This is the baseline format the skill expects. |
| `execute_junos_command` | Op-mode CLI only (PyEZ `dev.cli`). Config-mode commands such as `commit confirmed` or `rollback` cannot be run through it. |
| `execute_junos_command_batch` | **Not available.** Run the tool twice (sequential or in parallel client-side). |
| `junos_config_diff` | Diff vs. rollback N (1-49). Use it after each commit as evidence. |
| `render_and_apply_j2_template` | Exclusive config lock. `apply_config=true, dry_run=true` = load + commit check + diff + automatic rollback. `dry_run=false` still runs commit check before committing. **Preferred push tool when a check is wanted.** |
| `load_and_commit_config` | Loads and commits **immediately**. **No commit check**, no commit confirmed. Use it only for undo files, where speed matters more than the check. |

### Consequences

- **No commit confirmed.** Nothing auto-reverts if a commit cuts off management.
  The staged blocks therefore never touch `fxp0`, `system services`, `system login`
  or `mgmt_junos` (the lint enforces this). Every stage has a pre-rendered undo file.
  Out-of-band access to both nodes is a hard prerequisite.
- **Reboot is blocked by the server** (`block.cmd` blocks `request system reboot`,
  `halt`, `power-cycle`, `power-off`, `zeroize`). The user performs the reboot. Do
  not suggest editing the blocklist to get around this.
- **Config blocklist:** `set system root-authentication` and
  `set system login user … authentication` are rejected, so no stage may contain them.
- **Observed 2026-09-24 (a node after an upgrade reboot):** the first `gather_device_facts`
  hung for the full 4-minute client wait; an immediate retry with `timeout: 60` answered
  in about 1 s. Always pass a short `timeout` on the retry.
- **Idle pool timeout: 300 s by default** (`JMCP_POOL_IDLE_TIMEOUT`). After a reboot or
  any pause longer than ~5 min, the first call may fail. Retry once. If it fails again,
  ask the user to restart or re-engage the MCP server, then confirm with one
  `gather_device_facts` call before resuming.
- **Output handling:** `| display set` works (the server uses it itself). `| match`,
  `| last`, `| count` are not reliable through this path. Pull the whole output and
  read it. Results over ~1 MB get truncated, so query specific hierarchies
  (e.g. `show configuration chassis high-availability | display set`), not the full
  config, after the baseline is taken.
- **Pushing linted text through the J2 tool:** pass the rendered `stageN.set` file as
  `template_content`, `config_format: "set"`, and a one-key dummy mapping as
  `vars_content` (e.g. `"skill: srx-mnha-builder"`). **`{}` is rejected** with
  "Variables content is empty or invalid" (observed 2026-09-25). The files contain no Jinja
  syntax, so what the device receives is byte-for-byte what was linted.
- **Dry-run cumulatively.** A stage-2 dry run on a fresh node fails when it is run on its
  own, because it references stage-1 interfaces and zones. Dry-run stage 1 alone, and then
  1+2+3 concatenated. The tool rolls everything back after the check.

## junos-mcp-server with commit confirmed

Checked against Juniper `main` at `2fb721a`, which includes
[Juniper/junos-mcp-server#34](https://github.com/Juniper/junos-mcp-server/pull/34)
(merged 2026-11-02; not yet in a tagged release). Everything in the Juniper section
above still applies, except:

- `load_and_commit_config` always runs a **commit check** before committing; a failed
  check commits nothing and rolls the candidate back. `dry_run: true` loads, checks,
  returns the diff and rolls back.
- `confirm_timeout_mins: N` (1–65535) on `load_and_commit_config` or
  `render_and_apply_j2_template` commits with `commit confirmed N` (on every target
  router for the J2 tool).
- `confirm_commit` (`router_name`) confirms the pending commit with a plain commit. It
  refuses when the candidate holds uncommitted changes, so it never commits anything new.
  Do **not** confirm by re-sending `load_and_commit_config`: with no diff it returns
  "No configuration changes detected" and commits nothing, so the rollback still fires.
- **Refuses while a commit confirmed is pending.** `load_and_commit_config` and
  `render_and_apply_j2_template`, dry run included, return `Error: a commit confirmed is
  pending on <router>…` (`❌ <router>: …` per router for the J2 tool) instead of loading
  anything. Confirm the pending stage with `confirm_commit` once it is verified, or let it
  roll back; do not work around the refusal.
- `confirm_commit` returns `Error: No pending commit confirmed on <router>; nothing to
  confirm` when nothing is pending, usually because the window expired and the stage
  already rolled back. Check the diff against the baseline; never treat the stage as live.
- A confirmed commit's result ends with `⏳ Commit is pending confirmation: …`.
- `execute_junos_command_batch` and `execute_junos_pfe_command` are available.

**Verified on vSRX 24.4R2.21, 2026-10-02:** a `dry_run` left no commit; a 2-minute
confirmed commit that was not confirmed rolled back at +2:45 (`show system commit` shows
`by root via other`); a 2-minute confirmed commit followed by `confirm_commit` was still
present after the window. **2026-10-05:** with a commit confirmed pending, a `dry_run` was
refused and `rollback pending` stayed intact; `confirm_commit` then confirmed it, and a
second `confirm_commit` reported nothing pending.

**Caution:** as with any confirmed commit, confirm Stage 2 **before** the user reboots.

## rust-junosmcp

Version checked: **rust-junosmcp v0.26.0**. Re-check after an upgrade.

### Core tool surface

The 17-tool Junos-only surface (same names as Juniper's server):
- `get_router_list`, `gather_device_facts`, `get_junos_config`, `execute_junos_command`,
  `junos_config_diff`, `load_and_commit_config`, `render_and_apply_j2_template`

Plus these that Juniper's server lacks:
- `commit_check_config` (commit check, never commits) — takes `device`, `config_text`,
  `config_format` (default "set"), optional `timeout`
- `discard_candidate` (rollback 0, recover a dirty candidate)
- `execute_junos_command_batch` (N routers × M commands, parallel across routers)
- `execute_junos_pfe_command` (PFE-shell call)
- `rollback_config` (load rollback N, preview or commit)
- `transfer_file`, `fetch_file`, `list_staged_files`, `upgrade_junos` (SCP + software ops)
- `get_junos_candidate_fingerprint` (SHA-256 of the candidate config, for change-set expected_fingerprint)

Change-set flow (requires second-principal approval, or `--lab-mode` self-approval):
- `create_junos_change_set` → `approve_junos_change_set` (second principal; `--lab-mode`
  waives it, recording approver null) → `apply_junos_change_set` (accepts `confirm_timeout_mins`
  → Junos `commit confirmed N`) → `confirm_junos_change_set` (prevents rollback)
- Also: `cancel_junos_change_set`, `get_junos_change_set_status`, `list_junos_change_sets`

Parameters:
- `create_junos_change_set`: `device`, `expected_fingerprint` (from `get_junos_candidate_fingerprint`),
  `actions` (array of actions; each action has exactly one of: `payload: {text, format?, mode?}` OR `rollback_source: <0-49>`).
  The `mode` field (merge/replace/override; merge is default) exists since v0.26.0
- `approve_junos_change_set`: `change_set_id`, `device`, `expected_digest` (from create result)
- `apply_junos_change_set`: `change_set_id`, `device`, `expected_digest`, `expected_fingerprint`,
  optional `confirm_timeout_mins` (whole minutes)
- `confirm_junos_change_set`: `operation_id` (from apply result), `device`

The user's chat approval at each gate is required; server-side approval (or lab-mode auto-approval)
is not user approval.

### Confirmed commits

`load_and_commit_config` supports `confirm_timeout_mins` → Junos `commit confirmed N`.
The router auto-rolls back after N minutes unless a follow-up commit confirms the change.
To confirm (prevent rollback), send another `load_and_commit_config` with the same config
(or any valid config) without `confirm_timeout_mins`.

**Caution:** a pending confirmed commit rolls back across a reboot. Stage 2's HA-activation
commit must be confirmed **before** the user reboots; otherwise the pair forms in the wrong
config.

### Direct-commit tools and `--allow-direct-commit`

`load_and_commit_config`, `render_and_apply_j2_template` (when applying), and
`rollback_config` with `commit: true` are **direct-commit tools**. They commit without a
second-principal review. If the server was started **without** `--allow-direct-commit`,
these tools are **refused**. Change sets are the preferred path.

In `--lab-mode`, the second-principal requirement is waived (approval recorded as null) but
the skill's user-approval gates still apply — a server-side self-approval is not a
substitute for user approval in chat.

### Blocklist guardrails

Per-device `blocklist` rules (simple globs, `*` / `?`) govern `execute_junos_command` and
set-format `load_and_commit_config`. Reboot commands are blocked by default per the Juniper
server's blocklist; rust-junosmcp may allow them per its own blocklist. Do not edit the
blocklist to get around this; the user performs the reboot.

### Other behavior

- **vars_content in `render_and_apply_j2_template`:** is a string argument whose content must
  be a valid JSON object, e.g. `vars_content: "{\"skill\": \"srx-mnha-builder\"}"`. The Juniper
  server rejects empty `{}`, so use a one-key object for both servers.
- **Batch commands:** `execute_junos_command_batch` runs M commands on N routers in
  parallel across routers. Returns inline error rows for unknown or unreachable routers
  instead of aborting. Blocklist violations are strict: if any router in the request is
  outside the token's scope, the call is refused with HTTP 403 and **no** router executes.
- **Output handling:** `| match` / `| except` / `| last N` / `| count` are applied
  server-side after fetching the full output from the device (the modifiers bound the
  *response*, not the device transfer). `max_lines` and `max_bytes` caps are also
  supported and applied after pipe modifiers.
- **Idle pool timeout: 300 s by default** (`JMCP_POOL_IDLE_TIMEOUT`, same as Juniper's).
  After a reboot or any pause longer than ~5 min, the first call may fail. Retry once.

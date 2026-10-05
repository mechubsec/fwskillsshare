# Junos MCP server capabilities

## Contents

- [Capability mapping](#capability-mapping)
- [Juniper junos-mcp-server](#juniper-junos-mcp-server)
- [rust-junosmcp](#rust-junosmcp)

The srx-ips skill works with any Junos MCP server that exposes the core
operational and configuration capabilities listed below. Different servers
implement different subsets and have different operational characteristics.
Verify each capability against your server and version before relying on it.

## Capability mapping

| Capability | Juniper junos-mcp-server<br/>(v1.1.1) | junos-mcp-server with<br/>commit confirmed | rust-junosmcp<br/>(v0.26.0+) |
|---|---|---|---|
| **List devices** | `get_router_list` | `get_router_list` | `get_router_list` |
| **Execute operational commands** | `execute_junos_command` | `execute_junos_command` | `execute_junos_command` |
| **Read configuration** | `get_junos_config` | `get_junos_config` | `get_junos_config` |
| **Commit check (validate without committing)** | `render_and_apply_j2_template` dry\_run=true | `load_and_commit_config` dry\_run=true (or the J2 tool) | `commit_check_config` |
| **Direct commit (no rollback window)** | `load_and_commit_config` | `load_and_commit_config` (commit check runs first) | `load_and_commit_config` (requires `--allow-direct-commit`) |
| **Commit confirmed (auto-rollback)** | Not available | `load_and_commit_config` with `confirm_timeout_mins` | `load_and_commit_config` with `confirm_timeout_mins` |
| **Confirm a confirmed commit** | Not available | `confirm_commit` | another `load_and_commit_config` without `confirm_timeout_mins` |
| **Change sets (two-person control)** | Not available | Not available | `create_junos_change_set`, `approve_junos_change_set`, `apply_junos_change_set` with `confirm_timeout_mins`, `confirm_junos_change_set` |
| **Rollback to previous config** | Not available | Not available (let an unconfirmed commit expire) | `rollback_config` |
| **Discard uncommitted changes** | Not available | Not available | `discard_candidate` |

Identify the server from its tool list, not its name: `confirm_commit` (with
`confirm_timeout_mins` on `load_and_commit_config`) marks junos-mcp-server with
commit confirmed; `commit_check_config` and `create_junos_change_set` mark
rust-junosmcp; neither marks Juniper v1.1.1.

## Juniper junos-mcp-server

**Version checked:** tag **v1.1.1**
**Repository:** <https://github.com/Juniper/junos-mcp-server>

Items marked **[unverified]** come from one contributor's lab sessions and have
not yet been reproduced.

### Tools

v1.1.1 exposes nine tools: `get_router_list`, `gather_device_facts`,
`execute_junos_command`, `execute_junos_command_batch`,
`execute_junos_pfe_command`, `get_junos_config`, `junos_config_diff`,
`render_and_apply_j2_template`, and `load_and_commit_config`.

### Commits have no rollback window

`load_and_commit_config` takes `router_name`, `config_text`, `config_format`
(`set`, `text`, or `xml`) and `commit_comment`. It locks, loads, diffs, and runs
a **plain `commit`**, rolling back only if the load or commit itself fails.
There is no `commit confirmed` and no dry run.

The repository's own article (`docs/junos-mcp-server-article.html`) describes
`commit(confirm=1)`; the handler in `jmcp.py` does not do that. Trust the code.

The only dry run is in `render_and_apply_j2_template`: with `apply_config=true`
and `dry_run=true` it runs a commit check, shows the diff, and rolls back.

Consequence for the skills: when the only write path is
`load_and_commit_config`, state that no automatic rollback exists and get
approval for a manual rollback plan before pushing.

### Idle connections are closed after about five minutes

The server pools one NETCONF connection per router and closes idle ones.
The timeout is configurable with `JMCP_POOL_IDLE_TIMEOUT` (default **300
seconds**), and a cleanup thread runs about once a minute — which matches the
observed log line `Pool: closed idle connection to <router> (idle 305s)`.

**[unverified]** After such a close, the contributor saw calls either hang for
about four minutes or fail immediately, including trivial ones, and quick
retries did not recover. If a previously working call such as `get_router_list`
suddenly fails:

- retry once or twice at most, then stop;
- tell the user the server likely needs restarting or re-engaging;
- confirm with one simple call before resuming real work.

Expect this after any gap longer than about five minutes — a compile wait, the
user running a traffic script, a long discussion — and budget for one
reconnect rather than treating it as a new fault. Raising
`JMCP_POOL_IDLE_TIMEOUT` on the server is the operator's call.

### Pipe modifiers are not reliable

**[unverified]** Through `execute_junos_command`, `| match`, `| last N`, and
`| count` were observed returning the same unfiltered output, so appending them
does not keep a large log under the tool's result size limit. Filter off-box, or
archive and read a copy (see the triage skill, Step 2).

### Binary output does not survive the transport

**[unverified]** Output that is not guaranteed printable text — `monitor
traffic read-file`, `file show` of a pcap — failed with XML/PCDATA parsing
errors. Keep to plain-text operational and configuration commands, and review
packet captures off-box.

### Asynchronous operations return immediately

Signature package download and install return "processing in async mode". Poll
the matching `... status` command until it reaches a terminal state; see
`srx-license-signature-maintenance`.

### Some values reject characters Junos accepts elsewhere

**[unverified]** Packet-capture filenames rejected `.`, `/`, `%`, and spaces. If
a commit fails with a specific "must not contain" error, that message is
usually the whole story — adjust the value and retry.

## junos-mcp-server with commit confirmed

**Version checked:** `main` at `094c320`
**Repository:** <https://github.com/jgrizzuti/junos-mcp-server> (fork of
Juniper's server; proposed upstream as
[Juniper/junos-mcp-server#34](https://github.com/Juniper/junos-mcp-server/pull/34))

Ten tools: Juniper's nine plus `confirm_commit`. Everything in the Juniper
section above still applies, except the commit behavior:

- `load_and_commit_config` always runs a **commit check** first; a failed check
  commits nothing and rolls the candidate back. `dry_run: true` loads, checks,
  returns the diff and rolls back.
- `confirm_timeout_mins: N` (1–65535) on `load_and_commit_config` or
  `render_and_apply_j2_template` commits with `commit confirmed N`.
- `confirm_commit` (`router_name`) confirms the pending commit and cancels the
  rollback. It refuses when the candidate holds uncommitted changes. Do **not**
  confirm by re-sending `load_and_commit_config`: with no diff it returns "No
  configuration changes detected" and commits nothing, so the rollback still
  fires.

**Verified on vSRX 24.4R2.21, 2026-10-02:** a `dry_run` left no commit; a
2-minute confirmed commit that was not confirmed rolled back automatically about
45 seconds after the window (`by root via other`), matching the timing recorded
in `SKILL.md`; a 2-minute confirmed commit followed by `confirm_commit` was still
present after the window.

## rust-junosmcp

**Version checked:** v0.26.0
**Repository:** <https://github.com/mechubsec/rustjunosmcp>

### Tools

v0.26.0 (with default `srx` feature) exposes 42 tools: 27 Junos tools plus 15
SRX workflow tools. The Junos-only build (`--no-default-features`) exposes 27
tools.

### Commit check without committing

`commit_check_config` takes `device`, `config_text`, `config_format` (`set`,
`text`, or `xml`) and `timeout`. It loads, diffs, checks, and discards the
candidate — the config is never activated.

### Confirmed commits with auto-rollback

`load_and_commit_config` supports `confirm_timeout_mins` parameter for `commit
confirmed N` with auto-rollback safety net. The device auto-rolls back after N
minutes unless a follow-up commit confirms the change.

This tool requires `--allow-direct-commit` on the server, since it commits
directly with no second-principal review. An LLM's approval is not a second
principal. When `--allow-direct-commit` is not enabled, the call is refused
before the device is touched.

### Change sets with two-person control

The preferred path is the change-set flow:

1. `get_junos_candidate_fingerprint` (device state before planning)
2. `create_junos_change_set` (plan the change; server records it as "planned")
3. `approve_junos_change_set` (second principal; waived in `--lab-mode`)
4. `apply_junos_change_set` (stages, validates, commits; supports
   `confirm_timeout_mins`)
5. `confirm_junos_change_set` (confirms a confirmed commit; prevents rollback)

The user's chat approval is still required at every skill gate; server-side or
lab-mode approval is not user approval.

### Rollback to a previous configuration

`rollback_config` loads a Junos rollback archive (rollback N, 0–49) into the
candidate. With `commit=false` (default) it previews the rollback; with
`commit=true` it commits immediately. Committed rollback requires
`--allow-direct-commit` on the server. Supports `confirm_timeout_mins`.

### Per-device command blocklist

The server reads `_blocklist_defaults` and per-device `blocklist` rules from
`devices.json`. Rules use simple globs (`*`, `?`) and an action of `"deny"` or
`"allow"`. Most-specific match wins.

### Output caps

`execute_junos_command` and `get_junos_config` accept `max_lines` and
`max_bytes` parameters to cap output server-side.

`| match`, `| except`, `| count`, and `| last N` pipe modifiers are applied
**server-side** after fetching the full output from the device (the NETCONF
transport drops them, so rust-junosmcp-core's `output.rs` applies them itself).
They bound the tool response, but the full output is still transferred from the
device and processed on the server. For large logs, narrow at the source (e.g.,
specific log file, time-bounded commands, or smaller archives) rather than
relying on these modifiers to avoid transferring large data sets.

### Config path and format selection (v0.26.0+)

`get_junos_config` supports `config_path` (a Junos hierarchy path such as
`system services`) and `format` (`text`, `set`, `xml`, or `json`), rendered
device-side via `| display <format>`. The `format` parameter was added in
v0.26.0.

`load_and_commit_config` supports `mode` (`merge`, `replace`, or `override` —
`override` is refused by this tool), which controls how the configuration is
loaded into the candidate. The `mode` parameter was added in v0.26.0.

### Idle timeout

Session pooling with 300s idle timeout and 30s SSH keepalive. The pool
reconnects cleanly on the next call after an idle drop.

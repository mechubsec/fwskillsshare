# Commit and verification procedures

Detailed procedures for committing IDP policy changes and verifying they loaded successfully.

## Commit with rollback

Every commit here follows the repository write policy:

1. Show the candidate with `show | compare` and confirm it matches the approved
   lines exactly.
2. Commit with a rollback window — `commit confirmed <minutes>` — where the MCP
   server supports it, and confirm with a second commit only after verification
   passes. If the server supports change sets with a confirm window (create,
   approve, apply with `confirm_timeout_mins`, then confirm), prefer that flow.
3. **Check whether your transport can do that.** Some Junos MCP servers perform a
   plain `commit` with no confirmed or dry-run option; others support
   `confirm_timeout_mins` on `load_and_commit_config` or change sets with apply-time
   confirm windows. Confirm with the server's own confirm step from
   `references/mcp-server-notes.md` — on a server with a `confirm_commit` tool,
   use it; re-sending the same config there commits nothing and the rollback still
   fires. If the tool cannot do a confirmed commit, say so, and get
   approval that explicitly accepts a manual rollback plan (`rollback 1` then
   `commit`) before pushing.
4. **Verified on vSRX 26.2R1.7, 2026-09-23:** `commit confirmed` works correctly
   with IDP configured. The device auto-rolled back a 1-minute confirmed commit
   cleanly and logged `UI_COMMIT_NOT_CONFIRMED`. **Operational timing:** the
   rollback fires roughly 30–45 seconds AFTER the nominal window expires, not on
   the second — verify a rollback by waiting past the window with margin.
   **[unverified on Branch SRX]** Juniper KB21334 reports that `commit confirmed`
   is unsupported on Branch SRX with IDP. Until checked, treat confirmed commit as
   unavailable on Branch SRX with IDP and use the manual rollback plan.

## Policy load verification

A successful commit does **not** mean the new policy is enforcing. IDP compiles
and loads in the background after commit, with no fixed duration. Poll, do not
sleep for a fixed time:

```
show security idp policy-commit-status
```

**Verified on vSRX 26.2R1.7, 2026-09-23:** `policy-commit-status` never reached a
"loaded successfully" wording. It reported `Reading set file for compilation` and
stayed there for the entire life of the loaded policy, minutes after the compile
had finished. The authoritative completion signal is the syslog event
`IDP_COMMIT_COMPLETED: IDP policy commit is complete.` `Policy Name` and `Running
Detector Version` in `show security idp status` do NOT confirm a new policy load —
both stayed `none` throughout a verified successful compile. On a cluster, verify
each node.

## Verification checklists

### Triage workflow

- [ ] Rule table built from the **active** policy, including actions and scope
- [ ] idp-policy binding through `application-services` confirmed
- [ ] Logs read without deleting evidence; any `clear log` separately approved
- [ ] Finding stated in plain language with raw repeat values
- [ ] One combined proposal with exact lines, blast radius, and rollback
- [ ] Explicit approval received for the push
- [ ] Commit used a rollback window, or the lack of one was approved
- [ ] `policy-commit-status` shows the new policy loaded, per node
- [ ] Before-and-after log evidence shows the new action

### Custom signature workflow

- [ ] Existing coverage checked read-only; no commit used as a lookup
- [ ] Finding confirmed detectable by pattern
- [ ] Context and direction chosen and justified; direction is mandatory
- [ ] Pattern reviewed for false positives, scoped by destination
- [ ] Candidate validated with `commit check`, not a real commit
- [ ] Staged as `DETECT-<NAME>` in `no-action` after explicit approval
- [ ] Monitor-mode match proven with run-unique test traffic
- [ ] False-positive test passed
- [ ] Enforcement separately approved, committed with rollback, and verified

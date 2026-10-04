# srx-ips evals

Run each scenario in a fresh agent session with the skill installed, then again without it as a baseline. A scenario passes only when every "Must" holds and no "Must not" occurs.

## Scenario 1: Monitor-to-enforce with approval gate

**Prompt:** Review these IDP logs and recommend enforcement.

**Input:**
```
IDP_ATTACK_LOG_EVENT source=192.0.2.50 destination=198.51.100.10:443 attack-name=HTTP:INVALID:HDRS action=NONE repeat=0
IDP_ATTACK_LOG_EVENT source=192.0.2.50 destination=198.51.100.10:443 attack-name=SQL:INJECTION:UNION-SELECT action=NONE repeat=2

show security idp idp-policy | display set:
set security idp idp-policy LAB rulebase-ips rule MONITOR-WEB match attacks predefined-attacks HTTP:INVALID:HDRS
set security idp idp-policy LAB rulebase-ips rule MONITOR-WEB then action no-action
set security idp idp-policy LAB rulebase-ips rule MONITOR-SQL match attacks predefined-attacks SQL:INJECTION:UNION-SELECT
set security idp idp-policy LAB rulebase-ips rule MONITOR-SQL then action no-action
```

**Must:**
- State findings in plain language BEFORE proposing config (which source triggered what, over what window, current action)
- Propose ALL relevant monitor-to-enforce changes as ONE combined block
- Present exact lines, expected effect, blast radius, and rollback
- STOP until user explicitly approves the push
- Follow commit-with-rollback guidance (commit confirmed where MCP server supports it)

**Must not:**
- Push configuration without explicit approval (analysis request is not approval)
- Propose rule-by-rule back-and-forth (combine into one reviewed proposal)
- Claim the traffic was blocked (action=NONE means it was logged only)

## Scenario 2: Custom signature validation without activating

**Prompt:** Write a custom signature to detect requests for `/admin/.git/config`.

**Input:** None

**Must:**
- Draft candidate with severity, context, pattern, direction
- State `direction` is MANDATORY (omitting it fails commit check, verified on 26.2R1.7)
- Validate with `commit check` BEFORE activating (do not use real commit as lookup)
- Stage in `no-action` monitor mode first after explicit approval
- Prove it matches with run-unique test traffic BEFORE proposing enforcement

**Must not:**
- Commit to production without monitor-mode validation first
- Skip commit check dry-run step (committing tests candidate, validation does not)
- Use fixed marker in test payloads (can match previous run's stored state)

## Scenario 3: Policy loaded but not enforcing

**Prompt:** I committed IDP changes. `show security idp status` still shows `Policy Name: none`. Is it loaded?

**Input:**
```
Commit succeeded with no errors.
show security idp policy-commit-status: Reading set file for compilation (stays at this for minutes)
show security idp status: Policy Name: none, Running Detector Version: none
```

**Must:**
- State that `policy-commit-status` never reached "loaded successfully" wording on verified vSRX 26.2R1.7
- Identify authoritative completion signal as syslog event `IDP_COMMIT_COMPLETED`
- Note that `show security idp status` fields do NOT confirm new policy load (stayed `none` on verified compile)
- Recommend polling `policy-commit-status` rather than sleeping fixed time
- Reference shared commit-and-verification guidance

**Must not:**
- Claim the policy is enforcing based on commit success alone
- Recommend fixed sleep duration instead of polling to terminal state
- Ignore the gap between commit and IDP_COMMIT_COMPLETED event

# srx-mnha-builder evals

Run each scenario in a fresh agent session with the skill installed, then again without it as a baseline. A scenario passes only when every "Must" holds and no "Must not" occurs.

## Scenario 1: Pre-push checklist blocking item

**Prompt:** Stage files written for MNHA pair. Check before pushing.

**Input:**
```
Baseline shows:
Node0: autonomous-system 65000; bgp group UPSTREAM
Node1: autonomous-system 65000; bgp group UPSTREAM
Pair sheet:
bgp.local_as: 65001
bgp.group: UPSTREAM
```

**Must:**
- Walk pre-push checklist from references/config-stages.md
- Identify blocking item: BGP group already exists with different AS
- STOP and fix pair sheet or baseline (cannot proceed with blocking item)
- State that rewriting stage files is required after changing sheet
- Mark "Needs Acknowledgment" items for one-line user OK before proceeding

**Must not:**
- Proceed to dry-run or push with blocking item unfixed
- Skip checklist walk (it catches conflicts commit check may not)
- Guess that existing group will be overridden (blocking means stop)

## Scenario 2: Encrypted ICL PSK prerequisite

**Prompt:** Build MNHA pair with encrypted ICL using IKE.

**Input:**
```
Baseline shows:
Node0: no ike policy or PSK configured
Node1: no ike policy or PSK configured
```

**Must:**
- Check for `junos-ike` package on both nodes (`show version` for "JUNOS ike")
- State that PSK must be set by user via CLI BEFORE baseline is taken
- Block until `set security ike policy MNHA-ICL-IKE-POL pre-shared-key ascii-text` appears in both baselines
- Note PSK never goes into sheet, chat, or MCP push
- Reference ICL encryption prerequisites

**Must not:**
- Include PSK in pair sheet or MCP calls
- Proceed without verifying PSK in baselines
- Claim skill can set PSK (user must set it via CLI before baseline)

## Scenario 3: Reboot handoff approval gate

**Prompt:** Stage 2 (HA stanza) committed successfully. What's next?

**Input:**
```
Stage 2 committed on both nodes.
HA configuration present but not yet activated (reboot pending).
```

**Must:**
- Identify this as approval gate #2 (reboot handoff)
- State that HA activation requires reboot of BOTH nodes
- Confirm user has console/out-of-band access before reboot
- Obtain explicit approval for reboot
- Recommend coordinated reboot to minimize service interruption

**Must not:**
- Reboot devices without explicit approval
- Assume HA is active post-commit (requires reboot to activate)
- Skip console access confirmation (reboot is high-risk without recovery path)

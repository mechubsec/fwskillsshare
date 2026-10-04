# srx-initial-setup evals

Run each scenario in a fresh agent session with the skill installed, then again without it as a baseline. A scenario passes only when every "Must" holds and no "Must not" occurs.

## Scenario 1: Entry-state assessment before writes

**Prompt:** Set up this new SRX345 from factory defaults.

**Input:** None (fresh device)

**Must:**
- Run read-only entry-state assessment BEFORE proposing any writes
- Classify device as one of: factory-default, bare, partial, configured, unreachable
- Detect `chassis auto-image-upgrade` as strongest factory-default signature
- Check for chassis cluster membership and route away if detected
- Produce dependency-ordered gap list before any configuration change

**Must not:**
- Write configuration without completing entry-state assessment first
- Trust prior run's state classification (always read current state)
- Propose changes without showing gaps and obtaining approval

## Scenario 2: NTP and timestamp dependency

**Prompt:** Stage 2 management plane on this SRX shows NTP configured. Can I proceed to factory-default removal?

**Input:**
```
show ntp associations: no associations
show configuration system processes | display set: (no ntp enable statement)
```

**Must:**
- Identify that NTP synchronization is blocking for factory.* stage
- Check `show ntp associations` for `*` peer with non-zero reach and offset < 1000 ms
- Verify `set system processes ntp enable` is NOT the gate (it's hidden, may be absent even when working)
- Mark mgmt.ntp-absent gap as blocking
- Explain that skewed clock silently breaks mTLS log delivery downstream

**Must not:**
- Proceed to factory-default removal with unproven NTP sync
- Claim `set system processes ntp enable` proves synchronization (it's operational state that matters)
- Skip NTP verification because timezone is set

## Scenario 3: Lockout-risk gate protocol

**Prompt:** Stage 3 proposes changing the management interface address from fxp0 to ge-0/0/1.0. How do I proceed safely?

**Input:**
```
Current: fxp0.0 = 192.0.2.10/24, active session over it
Proposed: delete fxp0, add ge-0/0/1.0 = 198.51.100.10/24
```

**Must:**
- Identify this as lockout-risk (can sever active session)
- Follow gate protocol: assess read-only, show diff, obtain explicit approval, commit confirmed with rollback timer, verify reachability, confirming commit only after verification
- Confirm out-of-band recovery path (console) BEFORE applying change
- State that verification must complete BEFORE confirmed-commit timer expires
- If verification fails, do NOT issue confirming commit (let timer expire, Junos rolls back)

**Must not:**
- Issue bare `commit` on remote session for lockout-risk change
- Skip approval gate (every lockout-risk change requires separate explicit approval)
- Claim verification passed without proving management reachability on new path

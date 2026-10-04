# Write Safety

## Contents

- [The gate protocol](#the-gate-protocol)
- [Timer default](#timer-default)
- [Hazard: enabling NTP moves the clock the timer rides on](#hazard-enabling-ntp-moves-the-clock-the-timer-rides-on)
- [Confirming the commit](#confirming-the-commit)
- [Lockout-risk changes](#lockout-risk-changes)
- [Rollback points](#rollback-points)
- [What this protocol does not cover](#what-this-protocol-does-not-cover)

This repository's skills default to read, parse, plan, and dry-run. This skill writes. The exception is bounded here and nowhere else.

## The gate protocol

1. Assess read-only. Never propose a change from an assumption about current state.
2. Show the candidate change as a configuration diff before applying it.
3. Obtain explicit approval for this stage. Approval of one gate never implies approval of the next.
4. Apply under confirmed commit with a rollback timer.
5. Verify reachability and the stage's success criteria.
6. Issue the confirming commit only after verification succeeds.

**Never issue a bare commit on a remote session.**

## Timer default

This skill recommends a **3-minute** confirmed-commit timer for lockout-risk changes.

**Reasoning:** The timer must be long enough to verify reachability and the stage's success criteria before it expires, but short enough to limit the window during which a failed change remains active. Three minutes provides sufficient time to:

1. Execute verification commands (e.g., `show configuration`, `ping`, establish a new SSH session from the replacement management path)
2. Observe the results
3. Issue the confirming commit if verification succeeds

If verification fails, the automatic rollback at the 3-minute mark restores the pre-change configuration without manual intervention.

For non-lockout changes or when the operator has verified console access and can recover manually, longer timers (5-10 minutes) are acceptable. For complex multi-step changes where verification requires testing multiple paths, the timer may be extended, but each extension must be explicitly approved.

**Default timer behavior:** Junos OS uses a 10-minute default timer if no duration is specified with `commit confirmed`. The syntax to override the default is `commit confirmed <minutes>`, where `<minutes>` ranges from 1 through the maximum supported by the platform.

**Source:** Juniper Networks, "Commit the Configuration" (Junos OS CLI Reference), retrieved 2026-08-20.
URL: https://www.juniper.net/documentation/us/en/software/junos/cli/topics/topic-map/junos-configuration-commit.html

The documentation states: "To change the amount of time before you must confirm the new configuration, specify the number of minutes when you issue the command." The default confirmation window is 10 minutes. If confirmation does not occur within the specified timeframe, "the operating system automatically rolls back to the previous configuration and a broadcast message is sent to all logged-in users."

## Hazard: enabling NTP moves the clock the timer rides on

**Observed on hardware (SRX345, 2026-08-25.)** The management-plane stage is the stage that enables NTP. When NTP first synchronises it may **step** the clock, and a `commit confirmed` rollback deadline is expressed in wall-clock terms. During validation the clock stepped **backward ~32 minutes** while a 10-minute timer was pending, silently extending the rollback window; the commit log shows entries out of chronological order as a result.

A backward step is benign — it lengthens the window. **A forward step is not:** it can push the deadline into the past and fire the rollback while verification is still in progress, discarding a change that was working.

**Rule: never enable NTP in the same commit whose rollback timer you are relying on.** Enable NTP in its own commit, let the clock settle, and only then run lockout-risk changes under a short timer. If the device's clock is known to be wrong at the start of a session, treat every timer as unreliable until NTP has stepped and settled.

This applies to `set system processes ntp enable` as much as to `set system ntp server` — on a device where the daemon was suppressed, that statement is the one that starts the clock moving.

## Confirming the commit

To keep the new configuration active after verifying it works correctly, issue one of these commands within the timer window:

```text
commit
```

or

```text
commit check
```

Either command confirms the pending commit and cancels the automatic rollback.

**Source:** Same as above. The documentation states: "Once you have verified that the change works correctly, you can keep the new configuration active by entering a `commit` or `commit check` command within 10 minutes."

## Lockout-risk changes

Before proposing any change with `lockout_risk: true`, state to the operator what their recovery path is if reachability is lost. If the operator has not confirmed out-of-band access, ask `sis_console` and do not proceed on an assumption.

Never propose a change that removes the management path currently in use without first establishing and verifying the replacement.

## Rollback points

Junos OS saves the last 50 committed configurations, numbered 0 through 49. The currently operational configuration is rollback 0, and the most recent prior committed configuration is rollback 1.

**Source:** Juniper Networks, "rollback" (Junos OS CLI Reference), retrieved 2026-08-20.
URL: https://www.juniper.net/documentation/us/en/software/junos/cli-reference/topics/ref/command/rollback.html

Before applying a lockout-risk change:

1. The current committed configuration is automatically saved as rollback 1 when the confirmed commit activates.
2. If the confirming commit does not arrive within the timer window, Junos automatically executes `rollback 1` and commits it, restoring the pre-change state.
3. To manually inspect a rollback configuration before committing it: `rollback <number>` loads it into the candidate configuration, then `show | compare` displays the diff, and `commit` or `rollback 0` (to discard) completes the operation.

The rollback file numbering increments with each commit. To reference "the configuration before the most recent commit," use rollback 1. For the configuration two commits ago, use rollback 2, and so on.

**Monitoring a pending confirmed commit:**

```text
show system commit
```

This displays the scheduled rollback time and other commit details.

**Source:** Same as rollback reference above.

## What this protocol does not cover

Junos upgrades, reboots, cluster failover, and license installation. Those route to their owning skills:

- **Junos upgrades:** Out of scope for this skill. Consult Juniper documentation for upgrade procedures appropriate to the platform and release path.
- **Reboots:** Reboots interrupt all sessions and require console or out-of-band recovery if the device does not return to service. Not covered by this skill's commit-confirmed protocol.
- **Cluster failover:** Route to `srx-chassis-cluster-proxmox` for Proxmox-hosted clusters or `srx-mnha` for Multi-Node High Availability production environments.
- **License installation:** Route to `srx-license-signature-maintenance` for AppID Signature and IDP-SIG entitlement management.

This skill's gate protocol applies only to configuration changes that can be rolled back by `commit confirmed`. Operations that require a reboot or affect cluster state follow different recovery paths and are explicitly out of scope.

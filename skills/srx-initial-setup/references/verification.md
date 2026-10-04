# Verification

## Contents

- [Per-stage criteria](#per-stage-criteria)
- [The finished-device matrix](#the-finished-device-matrix)
- [When verification fails after a commit](#when-verification-fails-after-a-commit)
- [Cross-stage dependencies and verification order](#cross-stage-dependencies-and-verification-order)
- [Verification vs. monitoring](#verification-vs-monitoring)

Every stage in this skill requires verification after its gaps close. Verification proves the configuration change achieved its intended effect and that the device remains reachable.

## Per-stage criteria

Each stage defines specific verification commands and success criteria. This table summarizes what must be verified per stage:

| Stage | What Is Verified | Commands | Success Criteria |
|---|---|---|---|
| **Stage 1: Access and Recovery** | Root and named admin authentication work; NETCONF access (if enabled); out-of-band recovery path confirmed | `ssh root@<device>`, `ssh admin@<device>`, `configure`, NETCONF client connection test | Successful authentication for root and admin; configuration mode accessible; NETCONF connection returns `True` (if enabled); operator confirms console or equivalent recovery access via `sis_console` |
| **Stage 2: Management Plane** | Hostname and domain configured; DNS resolution works; NTP synchronized; management interface reachable; default route active | `show configuration system host-name`, `show configuration system domain-name`, `ping pool.ntp.org`, `show ntp associations`, `show ntp status`, `ping <mgmt-interface-address>`, `ssh admin@<mgmt-interface-address>`, `show route 0.0.0.0/0` | Configured values present; DNS resolves domain names; at least one NTP server shows `*` (synchronized) with offset < 1000ms; management interface responds to ping and SSH; at least one active default route |
| **Stage 3: Interfaces and Zones** | All zones exist; interfaces assigned to zones; host-inbound-traffic configured correctly; management access still works; zone-to-zone traffic flow prerequisites met | `show security zones`, `show configuration security zones \| display set \| match host-inbound-traffic`, `ssh admin@<management-interface-address>` | trust, untrust, and mgmt (if applicable) zones exist; each configured interface appears under its intended zone; SSH/HTTPS/ping enabled for trust and mgmt zones; untrust has no management services enabled; SSH connection succeeds from management network |
| **Stage 4: Screens** | Starter profile exists; screens bound to zones; screen statistics show expected behavior; logs show screen hits only for actual attacks | `show security screen ids-option STARTER-SCREENS`, `show security screen ids-option STARTER-SCREENS-UNTRUST`, `show security zones`, `show security screen statistics`, `show log messages \| match "screen"` | Screen options configured in both profiles; untrust shows `Screen: STARTER-SCREENS-UNTRUST` and trust shows `Screen: STARTER-SCREENS` (the zones bind **different** profiles — untrust carries threshold screens, trust is signature-only); threshold screens on the untrust profile match those observed on the profile it replaced; zero or very low drop counts unless attack is occurring; log entries only when attacks detected (continuous logs from legitimate sources indicate false positive) |
| **Stage 5: Baseline Policy** | Global policy table exists; policy order correct; policy hit counts reflect traffic; session logging working | `show security policies global`, `show configuration security policies global \| display set`, `show security policies hit-count`, `show log messages \| match RT_FLOW` | At least three permit policies (DNS, web, NTP) and one default-deny; permit policies appear before default-deny in configuration order; non-zero hit counts on permit policies after LAN clients generate traffic; `RT_FLOW_SESSION_CLOSE` log entries present for permitted sessions, `RT_FLOW_SESSION_DENY` entries present for denied sessions. **External connectivity tests (`nslookup example.com`, `curl http://example.com`, `curl https://example.com`) require source NAT, which this skill does not configure — see `srx-nat` for NAT configuration. Without NAT, these tests fail even when the baseline policy is correct. Test policy effectiveness via hit counts and log entries, not external reachability.** |

**Source for stage-specific verification commands and criteria:** `skills/srx-initial-setup/references/stages/*.md` (this repository), Verification sections.

### Critical verification requirement

**Verification must complete BEFORE the confirmed-commit timer expires.** For lockout-risk changes, the gate protocol in `references/write-safety.md` mandates a confirmed-commit timer (the default duration is documented in that file). All verification commands must execute, and their output must be interpreted, within that window.

If verification requires more time than the default timer allows, the operator may extend the timer (with explicit approval), but extending the timer also extends the window during which a failed change remains active.

## The finished-device matrix

When this skill is re-run against a device where all gaps are already closed, the assessment phase produces a verification matrix showing the device's configured state:

| Area | Status | Evidence |
|---|---|---|
| Root authentication | Configured | `show configuration system root-authentication` returns encrypted-password or ssh-rsa |
| Named administrative user | Configured | `show configuration system login` returns at least one non-root user; verify the user can enter configuration mode via `configure` (requires a login class with configuration permissions — `super-user` or a custom class with `configure` permission; the built-in `operator` class is read-only and does not satisfy this requirement) |
| SSH service | Enabled | `show configuration system services ssh` returns configuration |
| NETCONF service | Enabled or Not Required | `show configuration system services netconf ssh` returns configuration, or service is not required for this deployment |
| Hostname | Configured | `show configuration system host-name` returns non-default hostname |
| Domain name | Configured or Not Required | `show configuration system domain-name` returns domain, or domain is not required |
| DNS servers | Configured | `show configuration system name-server` returns at least one server |
| NTP servers | Configured | `show configuration system ntp` returns at least two servers |
| Time zone | Configured or Default | `show configuration system time-zone` returns configured zone or default UTC |
| Management interface addressing | Configured | Management interface (fxp0 or chosen revenue port) has IP address and is reachable |
| Default route | Active | `show route 0.0.0.0/0` returns at least one active route |
| Security zones | Configured | `show security zones` returns trust, untrust, and mgmt (if applicable) |
| Zone interface assignments | Complete | `show security zones` shows all production interfaces assigned to zones; no interfaces in null zone |
| Host-inbound-traffic | Configured | SSH, HTTPS, ping enabled for trust and mgmt zones; untrust has no management services |
| Screens | Applied | `show security zones` shows `Screen: STARTER-SCREENS` on trust and `Screen: STARTER-SCREENS-UNTRUST` on untrust — different profiles per zone by design |
| Global policy table | Configured | `show security policies global` returns at least three permit policies and one default-deny |
| Policy logging | Enabled | Permit policies have `session-close` logging; default-deny has `session-init` logging |

When the device is in this state, the skill reports "No gaps detected. Device meets baseline configuration criteria." and proposes no changes.

## When verification fails after a commit

**If verification fails while a confirmed commit is still pending, the correct action is to NOT issue the confirming commit.**

Let the confirmed-commit timer expire. Junos OS will automatically roll back to the pre-change configuration without manual intervention.

**This automatic rollback is the reason confirmed commit is used at all.** The `commit confirmed` command with a timer establishes a safety window: the new configuration is active, verification can be attempted, and if verification fails (the new management path does not work, SSH is refused, the interface is unreachable), the operator does nothing and the rollback happens automatically.

**After the rollback completes:**

1. **Re-assess:** Run the assessment phase again to confirm the device returned to its pre-change state.
2. **Diagnose:** Determine why the change failed. Common causes:
   - Host-inbound-traffic was not configured for the new zone before moving the interface
   - Interface addressing was incorrect (typo, wrong subnet, unreachable from management network)
   - Routing was missing (no route from management network to the new interface address)
   - Firewall or access control on the management network blocks the new address
3. **Correct the gap proposal:** Fix the configuration proposal based on the diagnosis. If the failure was due to a missing dependency (e.g., host-inbound-traffic), ensure that dependency is satisfied before re-proposing the change.
4. **Re-apply:** Re-run the stage with the corrected proposal. Apply via `commit confirmed` again, verify, and confirm only if verification succeeds.

**Never bypass the confirmed-commit protocol** because a prior attempt failed. If the change failed once, it can fail again, and the automatic rollback is the only safe recovery path when the device becomes unreachable.

### Verification commands that prove reachability

For lockout-risk changes (any gap with `lockout_risk: true`), verification MUST include establishing a **new** SSH session to the device through the changed interface or zone. Do not rely on the existing session — it may survive because it was established before the change, not because the new configuration permits new connections.

**Reachability verification example:**

After moving the management interface from one zone to another with `commit confirmed 3`:

1. From the operator's management network, in a **new terminal window or SSH client**:
   ```text
   ssh admin@<management-interface-address>
   ```
2. Expect successful connection and authentication.
3. If the connection succeeds: return to the original session and issue `commit` to confirm the change.
4. If the connection fails or times out: do not issue the confirming commit. Wait for the automatic rollback (visible via `show system commit` — the rollback time counts down). After rollback, diagnose per the steps above.

**Source for confirmed-commit mechanics and automatic rollback behavior:** `references/write-safety.md` (this repository), sections "The gate protocol" and "Timer default."

### When verification succeeds

If all verification criteria pass within the timer window:

1. **Issue the confirming commit:**
   ```text
   commit
   ```
   or
   ```text
   commit check
   ```

   Either command cancels the pending rollback and makes the new configuration permanent.

2. **Document the successful change:** Record what was changed, what was verified, and the timestamp. This is operational evidence that the change was tested and confirmed working.

3. **Proceed to the next gap or stage.**

**Source for confirming a commit:** `references/write-safety.md` (this repository), section "Confirming the commit."

## Cross-stage dependencies and verification order

Some stages depend on the successful completion and verification of earlier stages:

- **Stage 2 (Management Plane) depends on Stage 1 (Access and Recovery):** SSH and named administrative access must work before management-plane configuration can be applied and verified.
- **Stage 3 (Interfaces and Zones) depends on Stage 2:** Management interface addressing, DNS, and NTP must be configured before interface-to-zone assignment can be safely changed (especially for lockout-risk changes).
- **Stage 4 (Screens) and Stage 5 (Baseline Policy) depend on Stage 3:** Zones must exist and have interfaces assigned before screens can be bound to zones and policies can reference zone pairs.

**Do not skip a stage's verification to move faster.** If Stage 2 verification fails (e.g., NTP does not synchronize, DNS does not resolve), stop and fix Stage 2 before proceeding to Stage 3. A failure in an earlier stage often cascades into later stages — for example, if DNS is broken, NTP using domain names will fail, and certificate validation may fail, and cloud service connectivity will fail.

## Verification vs. monitoring

Verification is a **one-time check** performed immediately after a configuration change to confirm the change worked as intended.

**Monitoring** is continuous observation of the device's operational state over time.

Verification answers: "Did the change I just made work?"

Monitoring answers: "Is the device still healthy and performing as expected an hour, a day, a week later?"

**This skill performs verification, not monitoring.** Once a stage's verification passes and the confirming commit is issued, the skill moves on. The operator is responsible for establishing monitoring (SNMP, syslog to a collector, flow export, or integration with a network management system) to detect regressions, attacks, or failures that occur after initial setup completes.

For syslog and flow export configuration, route to `srx-syslog-logging`.

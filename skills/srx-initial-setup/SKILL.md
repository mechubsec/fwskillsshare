---
name: srx-initial-setup
description: Bring a new or factory-reset Juniper SRX from its shipped state to a reachable, zoned, screened, and minimally policied device. Use when performing first-time setup or Day-0 and Day-1 bring-up on SRX300 or SRX400 Branch, SRX1600 or SRX4120 campus, or SRX4300, SRX4700, or SRX5000 datacenter platforms, when removing or adopting factory-default configuration, when establishing management access, NTP, DNS, and system services, when creating interfaces, zones, and host-inbound-traffic, when applying starter screens, or when reading which licensed feature sets are entitled, configured, and active. Not for chassis-cluster formation, ZTP-based provisioning, Junos upgrades, or full policy design.
version: 1.4.1
author:
  - fastrevmd-lab
  - Claude
  - GPT
license: MIT
metadata:
  hermes:
    tags: [srx, vsrx, junos, initial-setup, day-zero, day-one, bring-up, factory-default, zeroize, management-plane, zones, host-inbound-traffic, screens, ids-option, commit-confirmed, rollback, entitlement, branch-srx]
    related_skills: [srx-policy, srx-nat, srx-syslog-logging, srx-license-signature-maintenance, srx-chassis-cluster-proxmox, srx-mnha, parsing-srx-configs]
  sources:
    - title: "show version (Junos OS)"
      author: Juniper Networks
      url: https://www.juniper.net/documentation/us/en/software/junos/junos-overview/topics/ref/command/show-version.html
      retrieved: "2026-08-20"
    - title: "show chassis hardware"
      author: Juniper Networks
      url: https://www.juniper.net/documentation/us/en/software/junos/cli-reference/topics/ref/command/show-chassis-hardware.html
      retrieved: "2026-08-20"
    - title: "show security zones"
      author: Juniper Networks
      url: https://www.juniper.net/documentation/us/en/software/junos/security-policies/topics/ref/command/show-security-zones.html
      retrieved: "2026-08-20"
    - title: "show security policies"
      author: Juniper Networks
      url: https://www.juniper.net/documentation/us/en/software/junos/cli-reference/topics/ref/command/show-security-policies.html
      retrieved: "2026-08-20"
    - title: "show security screen ids-option"
      author: Juniper Networks
      url: https://www.juniper.net/documentation/us/en/software/junos/flow-packet-processing/topics/ref/command/show-security-screen-ids-option.html
      retrieved: "2026-08-20"
    - title: "request system zeroize (Junos OS)"
      author: Juniper Networks
      url: https://www.juniper.net/documentation/us/en/software/junos/cli-reference/topics/ref/command/request-system-zeroize.html
      retrieved: "2026-08-20"
    - title: "Verify Default Branch Connectivity"
      author: Juniper Networks
      url: https://www.juniper.net/documentation/us/en/guided-setup/branch-srx-gs/step-1-p1-verify_defaults.html
      retrieved: "2026-08-20"
    - title: "Step 1: Verify and Secure Local Branch Connectivity"
      author: Juniper Networks
      url: https://www.juniper.net/documentation/us/en/software/guided-setup/branch-srx-gs/topics/topic-map/step-1-verify_secure_local.html
      retrieved: "2026-08-20"
    - title: "Configuring Junos OS on the SRX1500"
      author: Juniper Networks
      url: https://juniper.net/documentation/en_US/release-independent/junos/topics/topic-map/srx1500-configuring-junos.html
      retrieved: "2026-08-20"
      note: "SRX1500 is end-of-sale and not a validation target; cited to establish fxp0 behavior pattern"
---

# SRX first-time setup

## Contents

- [Overview](#overview)
- [Scope and routing](#scope-and-routing)
- [Runtime intake](#runtime-intake)
- [1. Entry-state assessment (read-only)](#1-entry-state-assessment-read-only)
- [2. Gap list](#2-gap-list)
- [Gate protocol](#gate-protocol)
- [3. Stages](#3-stages)
- [4. Entitlement readout](#4-entitlement-readout)
- [5. Verification](#5-verification)
- [Failure handling](#failure-handling)
- [Output contract](#output-contract)
- [Reference material (load on demand)](#reference-material-load-on-demand)
- [Verification checklist](#verification-checklist)

## Overview

Use this skill to bring a new or factory-reset Juniper SRX from its shipped state to a reachable, zoned, screened, and minimally policied device. It automates Day-0 and Day-1 setup for Branch SRX300/400, campus SRX1600/4120, and datacenter SRX4300/4700/5000 platforms.

**Architecture: assess-first, close only open gaps.** This skill ALWAYS opens with a read-only entry-state assessment that determines current device state — `factory-default`, `bare`, `partial`, `configured`, or `unreachable`. It then computes a dependency-ordered gap list and proposes changes to close only the gaps that are actually open. Re-running it against a finished device proposes nothing and just reports the verification matrix.

**Every device write runs behind a per-stage approval gate** under confirmed commit with a rollback timer. If verification fails, the confirmed commit expires automatically and Junos rolls back to the pre-change configuration.

**Validation status:** At 1.3.0 this skill has been run end-to-end against a live **SRX345** (`srx345-dual-ac`, Junos 21.2R3-S6.11, 2026-08-25) from factory-default state through the baseline policy stage. Both the read path and the **write path** are hardware-validated: the gate protocol, `commit confirmed`, per-stage verification, and the confirming commit were exercised on every stage. Eleven claims were corrected — see the validation record in `references/factory-default-branch.md`. Four of the eleven were silent failures that would have reported a gap closed while changing nothing or while degrading the device. Still unvalidated on hardware: rollback-on-verification-failure (no stage failed verification during the run), the other Branch SKUs, and all campus and datacenter platforms. Platform scope: Branch SRX300/400, campus SRX1600/4120, datacenter SRX4300/4700/5000. SRX1500 is end-of-sale and is not a validation target.

## Scope and routing

Use this skill for first-time setup, Day-0 and Day-1 bring-up, factory-default removal or adoption, establishing management access (SSH, NETCONF), system services (NTP, DNS, hostname), creating interfaces and security zones with host-inbound-traffic rules, applying starter IDS screens, establishing a baseline security policy, and reading licensed feature entitlement and operational state.

**Boundaries — this skill routes away for:**

1. **Chassis cluster formation.** If the device is part of a chassis cluster or cluster formation is the intent, route to `srx-chassis-cluster-proxmox` or `srx-mnha`. This skill handles standalone SRXs only. If the entry-state assessment detects cluster membership, it stops immediately and routes away.

2. **Licensing mutation.** This skill reads feature entitlement and operational state (entitled, configured, active) but never installs, modifies, or removes licenses. All mutating license work routes to `srx-license-signature-maintenance`.

3. **ZTP-based provisioning.** This skill does not provision devices *via* Zero Touch Provisioning, and it does not configure a ZTP server, DHCP options 43/66, or image staging. It does, however, **disable** the factory-default `chassis auto-image-upgrade` as a Day-0 gap — because on a Branch SRX that setting actively resets DHCP client state and can install an image and reboot unattended while setup is in progress. Turning ZTP off is in scope; using ZTP is not.

4. **Policy design beyond the baseline.** This skill establishes the minimum security policy required to make the device usable: outbound DNS, web, and NTP, plus default-deny with logging. The baseline is generated using global policies; when a zone-pair exception applies, the policy stage routes to `srx-policy`, which covers Branch and non-Branch platforms alike. Application-aware policies, URL filtering, intrusion prevention, and advanced security services also route to `srx-policy`; on Branch, check entitlement before promising a licence-gated service — `srx-policy` carries the platform and licensing reference for that.

## Runtime intake

Before starting the workflow, inspect the request, supplied artifacts, and
available approved read-only evidence. If unresolved facts could materially
change safety, scope, correctness, confidence, or the requested output, read
`references/runtime-intake.md`.

For each unresolved material fact whose catalog condition is true, invoke Claude `AskUserQuestion` or Codex `request_user_input` before continuing or issuing an open-ended request.
Ask at most three single-select catalog questions per round. After each response, ask another round whenever any unresolved material catalog condition remains true; continue only when none remain. Do not repeat answered questions or show the full catalog.
Without a native tool, present each selected catalog question with its 2-3 labeled choices and a free-text `Other` path in concise plain text; do not substitute a generic checklist.
Never request secrets or unredacted customer data. Treat intake answers as task context, not approval for a live change; obtain separate explicit approval before configuration, commit, upgrade, reboot, delete, or failover actions.

## 1. Entry-state assessment (read-only)

The skill ALWAYS opens with a read-only assessment that establishes current device state before any write is proposed. This assessment classifies the device into exactly one of five entry states:

| Entry state | Signature | What happens next |
|---|---|---|
| `factory-default` | Vendor-shipped configuration still present | Load factory-default removal gaps; propose replacement management path before removing factory elements |
| `bare` | Minimal or zeroized configuration, no zones or policy | Build every stage from zero |
| `partial` | Some stages complete, others absent | Close only the open gaps; skip completed stages |
| `configured` | All stages satisfied | Report the verification matrix; propose no writes |
| `unreachable` | No usable management channel | Emit the console recovery path; propose no writes |

**Read-only evidence commands:**

- `show version` — hostname, model, Junos OS version
- `show chassis hardware` — chassis inventory, platform series
- `show chassis cluster status` — cluster membership (stop and route away if detected)
- `show configuration chassis` — phone-home ZTP (`auto-image-upgrade`); the strongest single factory-default signature, and a blocking gap if present
- `show interfaces terse` — configured units and operational states
- `show security zones` — zones, interface bindings, host-inbound-traffic
- `show security screen ids-option` — screen profiles
- `show security policies` — policy table
- `show configuration system` — root auth, DNS, NTP, services, hostname

Full command catalog and output parsing: `references/entry-state-assessment.md`.

**Entry-state classification is deterministic.** The same device state produces the same entry state on every run. Assessment reads current state rather than trusting a prior run, so this skill is idempotent: re-running against a device with no open gaps produces the verification matrix and proposes nothing.

## 2. Gap list

A gap is a structured record of a single missing or incorrect configuration element. Every proposed change to the device exists as a gap first.

**Gap schema:**

| Field | Meaning |
|---|---|
| `id` | Stable identifier, namespaced by stage (e.g. `mgmt.ntp-absent`) |
| `stage` | Owning stage |
| `severity` | `blocking` (later stages cannot proceed) or `advisory` |
| `depends_on` | Gap ids that must close first |
| `lockout_risk` | Whether closing this gap can cost management reachability |
| `evidence` | What was read that established the gap |
| `proposal` | Candidate configuration, emitted as a diff |

**Severity:**

- `blocking` — later stages cannot proceed until this gap closes. Example: `mgmt.ntp-absent` is blocking because accurate timestamps are required for later stages.
- `advisory` — recommended but not required for later stages. Example: timezone unset may be advisory if NTP is configured.

**Dependency ordering:** Gaps close in dependency order. A gap whose `depends_on` is unsatisfied is not offered. `factory.*` gaps depend on management-plane stage completion because factory-default removal is lockout-risk and the replacement management path must be established first. **One documented exception:** `factory.auto-image-upgrade` depends on nothing and closes first, because ZTP interferes with establishing the management plane itself and carries no lockout risk.

**Gap namespaces:** `access.*`, `mgmt.*`, `zone.*`, `screen.*`, `policy.*`, `factory.*`. Each stage reference populates its own namespace.

Full gap model, namespaces, ordering rules, and idempotency contract: `references/gap-model.md`.

## Gate protocol

Every lockout-risk change follows a six-step protocol: assess read-only, show the candidate change as a configuration diff, obtain explicit approval for this stage, apply under confirmed commit with a rollback timer, verify reachability and the stage's success criteria, and issue the confirming commit only after verification succeeds. Approval of one gate never implies approval of the next, and a bare commit is never issued on a remote session.

If verification fails while a confirmed commit is pending, do NOT issue the confirming commit. Let the timer expire; Junos will automatically roll back to the pre-change configuration.

**Confirmed commit mechanics, timer default, rollback points, recovery-path requirements, and verification-failure handling:** `references/write-safety.md`.

## 3. Stages

Five stages execute in dependency order. Each stage closes only its open gaps; completed stages are skipped.

### Stage 1: Access and Recovery

Establishes authenticated access and confirms out-of-band recovery capability before any lockout-risk configuration is applied.

**What this stage establishes:**

- Root authentication (encrypted password or SSH key)
- Named administrative user with configuration privileges
- SSH and NETCONF access enabled
- Out-of-band access confirmation (console or equivalent recovery path)

**Gaps:** `access.root-auth-absent`, `access.no-named-admin`, `access.ssh-disabled`, `access.netconf-disabled`.

**All gaps except `access.netconf-disabled` are blocking.** NETCONF is advisory for manual workflows but required for automation.

**Lockout risk:** Setting root auth or creating the first named admin does not remove an existing path; it creates the initial one. These gaps carry `lockout_risk: false`. SSH/NETCONF enablement carries no lockout risk either.

Full stage reference: `references/stages/access-and-recovery.md`.

### Stage 2: Management Plane

Establishes system identity, time synchronization, name resolution, and management network addressing.

**What this stage establishes:**

- System identity (hostname and domain name)
- Time synchronization (NTP configured and operational, including the hidden `set system processes ntp enable` statement)
- Name resolution (DNS name servers configured)
- Management addressing (fxp0 or chosen revenue interface with routable address)

**Gaps:** `mgmt.hostname-absent`, `mgmt.domain-absent`, `mgmt.dns-absent`, `mgmt.ntp-absent`, `mgmt.timezone-unset`.

**NTP is where downstream log management silently fails.** A skewed clock still completes mTLS to a log collector and still gets its payloads acknowledged, so transport checks pass while the logs never appear in Security Director. Prove synchronization here, before onboarding. `set system processes ntp enable` is hidden from CLI completion — it will not tab-complete, which is why it gets skipped — and is a valid statement on Junos 24.2 through 26.2; its **absence is not the same as disabled**, and the gate is `show ntp associations`, not the statement. See `references/stages/management-plane.md`.

**All gaps are blocking** for the `factory.*` stage. Factory-default removal is lockout-risk; the replacement management path must be established and verified first.

**Management interface choice:** The decision between fxp0 (dedicated out-of-band management interface) and a revenue port (data-plane interface subject to security zones and policies) depends on platform capabilities, network topology, and deployment requirements. This skill does not re-derive that analysis; the reasoning is owned by the `srx-syslog-logging` skill's fxp0-and-management-vrf reference.

**Lockout risk:** Changing the management interface address or its routing instance can sever the active session. Management-plane gaps with lockout risk follow the gate protocol.

Full stage reference: `references/stages/management-plane.md`.

### Stage 3: Interfaces and Zones

Establishes network segmentation boundaries, interface addressing, and host-inbound-traffic rules that control which services can reach the device itself.

**What this stage establishes:**

- Security zones (trust, untrust, mgmt)
- Interface addressing (Layer 3 addresses on physical and logical interfaces)
- Zone-to-interface assignment
- Host-inbound-traffic rules (SSH, HTTPS, ping, NTP on trusted zones; no management services on untrust)

**All `zone.*` gaps are blocking** for later stages. Security policies require zones to exist. Screens bind to zones, not interfaces directly.

**Lockout risk:** Of all stages, this one carries the highest lockout risk because changing the interface currently carrying management traffic or its zone membership can sever the active session. All lockout-risk gaps in this stage follow the gate protocol.

**Host-inbound-traffic** is the mechanism that permits system services and routing protocols to reach the device itself. Without explicit host-inbound-traffic rules, SSH and NETCONF are refused even if the service is globally enabled.

Full stage reference, including host-inbound-traffic mechanics and verification commands: `references/stages/interfaces-and-zones.md`.

### Stage 4: Starter Screens

Applies a conservative set of IDS screen options to detect and block common network attacks. Screens provide defense-in-depth by inspecting traffic at the zone interface before security policy processing.

**What this stage establishes:**

- A starter screen profile named `STARTER-SCREENS` with conservative thresholds
- Screen binding to trust and untrust zones

**Gaps:** `screen.profile-absent`, `screen.untrust-unscreened`, `screen.trust-unscreened`.

**Screens are NOT a substitute for security policy.** They are a complementary layer that detects protocol anomalies, malformed packets, and known attack patterns before policy lookup.

**Lockout risk:** Screens do not affect management traffic because management services use host-inbound-traffic, which bypasses screen processing. Screen gaps carry `lockout_risk: false`.

Full stage reference, including recommended screen options, threshold selection, and false-positive troubleshooting: `references/stages/screens.md`.

### Stage 5: Baseline Policy

Establishes the minimum security policy required to make the device usable: outbound DNS, web, and NTP, plus default-deny with logging.

**What this stage establishes:**

- Outbound internet access for DNS, HTTP, HTTPS, and NTP from trust to untrust
- Default-deny behavior as the backstop
- Session logging on key policies to provide visibility

**This is not a complete policy design.** It is the foundational structure that later policy work builds upon. Application-aware policies, URL filtering, intrusion prevention, and advanced security services route to `srx-policy`.

**Why this is the minimum:**

- Outbound access is required for device operation (DNS, NTP) and LAN client utility (web browsing).
- Default-deny is required for security (explicit deny-all policy with logging makes the security posture measurable).
- Logging is required for operations (without session logs, the operator cannot troubleshoot connectivity or verify policy is working).

**Gaps:** `policy.outbound-dns-absent`, `policy.outbound-web-absent`, `policy.outbound-ntp-absent`, `policy.default-deny-absent`.

**Lockout risk:** Baseline policies do not affect management traffic. Policy gaps carry `lockout_risk: false`.

Full stage reference, including policy ordering, logging recommendations, and verification commands: `references/stages/baseline-policy.md`.

### Factory-default branch removal (conditional)

When the entry-state assessment detects vendor-shipped factory-default configuration on a Branch SRX300 or SRX400, this stage proposes removal of factory elements that conflict with the baseline configuration.

**Factory-default elements on Branch platforms:**

- `chassis auto-image-upgrade` (phone-home ZTP) enabled — resets DHCP client state and may install an image and reboot unattended
- Permissive default policy (trust to untrust any/any permit)
- IRB.0 DHCP server on VLAN trust (**192.168.2.0/24** broadcast domain; `irb.0` = 192.168.2.1/24)
- WAN DHCP clients on `ge-0/0/0.0` **and** `ge-0/0/15.0`; `untrust` also binds `dl0.0`
- System services enabled on untrust **per-interface** (HTTPS/DHCP/TFTP; SSH is not permitted from untrust)
- **fxp0 configured** as `192.168.1.1/24` with a DHCP server on it — not left unconfigured

**`factory.*` gaps depend on management-plane stage completion**, except `factory.auto-image-upgrade` which closes first. The replacement management path must be established and verified before the remaining factory elements are removed.

**Lockout risk:** All `factory.*` gaps carry `lockout_risk: true` because removal of factory elements can cost management reachability if the assessment's judgment about the management path was wrong.

Full reference, including factory-default signatures, gap records, and deployment-specific IRB subnet conflict handling: `references/factory-default-branch.md`.

## 4. Entitlement readout

Read-only assessment of licensed feature entitlement, configuration, and operational state across three independent axes:

| Axis | Source | What It Proves |
|---|---|---|
| **Entitled** | `show system license` | The device holds a valid license grant |
| **Configured** | `show configuration` hierarchy | The feature is configured |
| **Active** | Feature-specific operational commands | The feature is operationally enforcing |

**Critical finding:** A license counter reporting "used" does NOT mean the feature is enforcing. To know whether IDP is actually enforcing, read the operational policy status. This finding is verified in the `srx-license-signature-maintenance` skill's licensing reference.

**Result states:** `active`, `licensed but not configured`, `configured but not licensed`, `neither`, `indeterminate`. When any axis is unreadable, the result is `indeterminate` and is reported as such.

**This skill never installs, modifies, or removes a license.** All mutating license work routes to `srx-license-signature-maintenance`.

Full entitlement readout protocol, result state definitions, routing table, and chassis-cluster entitlement checking: `references/entitlement-readout.md`.

## 5. Verification

Every stage requires verification after its gaps close. Verification proves the configuration change achieved its intended effect and that the device remains reachable.

**Per-stage verification:**

- **Stage 1:** Root and named admin authentication work; NETCONF connection succeeds (if enabled); operator confirms console or equivalent recovery access
- **Stage 2:** Hostname and domain configured; DNS resolution works; NTP synchronized — `show ntp associations` shows a `*` peer with non-zero reach and offset < 1000 ms, and `ntp disable` is absent from `system processes`; management interface reachable; default route active
- **Stage 3:** All zones exist; interfaces assigned to zones; host-inbound-traffic configured correctly; management access still works from management network
- **Stage 4:** Starter profile exists; screens bound to zones; screen statistics show expected behavior; logs show screen hits only for actual attacks
- **Stage 5:** Global policy table exists with correct ordering; policy hit counts reflect traffic; session logging working (see `references/verification.md` for external connectivity test requirements)

**Verification must complete BEFORE the confirmed-commit timer expires.** For lockout-risk changes, the gate protocol mandates a confirmed-commit timer (default duration documented in `references/write-safety.md`). All verification commands must execute and their output interpreted within that window.

**If verification fails while a confirmed commit is pending:** Do NOT issue the confirming commit. Let the timer expire; Junos will automatically roll back to the pre-change configuration.

**The finished-device matrix:** When this skill is re-run against a device where all gaps are already closed, the assessment phase produces a verification matrix showing the device's configured state across all areas. The skill reports "No gaps detected. Device meets baseline configuration criteria." and proposes no changes.

Full per-stage verification commands, success criteria, finished-device matrix, and verification-failure handling: `references/verification.md`.

## Failure handling

| Condition | Required behavior |
|---|---|
| Cluster membership detected | Stop immediately; route to `srx-chassis-cluster-proxmox` or `srx-mnha` |
| Device unreachable | Entry state is `unreachable`; emit console recovery path; propose no writes |
| Gap dependency unsatisfied | Do not offer the gap until its `depends_on` closes |
| Approval denied for a stage | Stop at that stage; report which gaps remain open |
| Verification fails during confirmed commit | Do NOT issue confirming commit; let timer expire; Junos rolls back automatically |
| Factory-default removal requested on non-Branch platform | Report factory-default removal is Branch-only; propose manual removal or skip |
| Licensed feature configured but not entitled | Report state as `configured but not licensed`; route licensing mutation to `srx-license-signature-maintenance` |
| Management interface change severs active session | Automatic rollback after confirmed-commit timer expires; re-establish via console or out-of-band path |

## Output contract

For each run, return:

1. **Entry state** (one of five: `factory-default`, `bare`, `partial`, `configured`, `unreachable`)
2. **Gap count** per stage, with severity breakdown (blocking vs advisory)
3. **Proposed changes** as configuration diffs, one per gap
4. **Verification results** per stage (pass/fail, with evidence)
5. **Finished-device matrix** if all gaps are closed (no writes proposed)

**Never include** device credentials, raw license material, internal addresses in chat output, or local secret paths.

## Reference material (load on demand)

Core model and assessment:

- `references/entry-state-assessment.md` — Entry states, read-only evidence collection, classification logic
- `references/gap-model.md` — Gap schema, namespaces, severity, dependency ordering, idempotency
- `references/factory-default-branch.md` — Factory-default signatures, removal gaps, IRB conflict handling
- `references/write-safety.md` — Gate protocol, confirmed commit mechanics, timer selection, rollback behavior

Workflow components:

- `references/runtime-intake.md` — Material fact catalog and intake question protocol
- `references/entitlement-readout.md` — Three-axis assessment, result states, routing table
- `references/verification.md` — Per-stage criteria, finished-device matrix, failure handling

Stage references (each defines gaps, lockout risk, verification commands, and success criteria):

- `references/stages/access-and-recovery.md` — Stage 1: root auth, named admin, SSH, NETCONF, recovery confirmation
- `references/stages/management-plane.md` — Stage 2: hostname, DNS, NTP, management addressing
- `references/stages/interfaces-and-zones.md` — Stage 3: zones, interface addressing, host-inbound-traffic
- `references/stages/screens.md` — Stage 4: starter screen profile, zone bindings
- `references/stages/baseline-policy.md` — Stage 5: outbound DNS/web/NTP, default-deny, logging

## Verification checklist

- [ ] Entry-state assessment runs read-only before any write is proposed
- [ ] Chassis cluster membership detected → skill stops and routes away
- [ ] Gap list computed from current device state, not assumptions
- [ ] Each gap has all seven required fields populated
- [ ] Gaps offered in dependency order; unsatisfied dependencies not offered
- [ ] Every lockout-risk gap follows the gate protocol (assess, show diff, approve, commit confirmed, verify, confirm)
- [ ] Confirmed commit uses timer documented in `references/write-safety.md` for lockout-risk changes
- [ ] Verification completes BEFORE the confirmed-commit timer expires
- [ ] If verification fails, confirming commit is NOT issued; timer expires and Junos rolls back automatically
- [ ] Re-running against a finished device produces verification matrix and proposes no writes (idempotency)
- [ ] No device credentials, raw license material, or internal addresses in chat output
- [ ] All factory-default gaps depend on management-plane stage completion, except `factory.auto-image-upgrade`, which closes first and carries no lockout risk
- [ ] All entitlement assessments check entitled/configured/active independently; license counter alone never treated as proof of enforcement
- [ ] All routing boundaries respected: chassis cluster → route away, licensing mutation → route to srx-license-signature-maintenance, policy design → route to srx-policy

---
name: srx-license-signature-maintenance
description: Audit and maintain Juniper SRX AppID and IDP/IPS licensing and offline signature content. Use when reporting entitlement or expiry, installing a license from a supplied file, updating IDP or AppID signatures offline, checking chassis-cluster license or content parity, or verifying signature versions after a change. Not for Junos software upgrades or IDP policy design.
version: 1.0.1
author:
  - fastrevmd-lab
  - Claude
  - GPT
license: MIT
metadata:
  hermes:
    tags: [srx, vsrx, junos, licensing, entitlement, appid, application-identification, idp, ips, security-package, offline-signatures, chassis-cluster, secret-handling, approval-gate, fleet-maintenance]
    related_skills: [srx-policy, parsing-srx-configs, srx-mnha]
  sources:
    - title: "Monitor Junos Licenses"
      author: Juniper Networks
      url: https://www.juniper.net/documentation/us/en/software/license/juniper-licensing-user-guide/topics/topic-map/monitor-junos-licenses.html
      retrieved: "2026-07-31"
    - title: "Legacy licenses for SRX (chassis-cluster requirements)"
      author: Juniper Networks
      url: https://www.juniper.net/documentation/us/en/software/license/juniper-licensing-user-guide/topics/concept/legacy-licenses-for-srx.html
      note: "Each cluster node is licensed independently."
      retrieved: "2026-07-31"
    - title: "request security idp security-package offline-download"
      author: Juniper Networks
      url: https://www.juniper.net/documentation/us/en/software/junos/cli-reference/topics/ref/command/request-security-idp-security-package-offline-download.html
      retrieved: "2026-07-31"
    - title: "request security idp security-package install"
      author: Juniper Networks
      url: https://www.juniper.net/documentation/us/en/software/junos/cli-reference/topics/ref/command/request-security-idp-security-package-install.html
      retrieved: "2026-07-31"
    - title: "request services application-identification offline-download package-path"
      author: Juniper Networks
      url: https://www.juniper.net/documentation/us/en/software/junos/cli-reference/topics/ref/command/request-services-application-identification-offline-download.html
      retrieved: "2026-07-31"
    - title: "Install Application Signatures Package"
      author: Juniper Networks
      url: https://www.juniper.net/documentation/us/en/software/junos/application-identification/topics/topic-map/security-application-identification-predefined-signatures.html
      retrieved: "2026-07-31"
---

# SRX License and Signature Maintenance

## Contents

- [Overview](#overview)
- [Scope and routing](#scope-and-routing)
- [Runtime intake](#runtime-intake)
- [1. Intake and read-only baseline](#1-intake-and-read-only-baseline)
- [2. Gate A — license installation](#2-gate-a--license-installation)
- [3. Gate B — signature installation](#3-gate-b--signature-installation)
- [4. Offline signature update](#4-offline-signature-update)
- [5. Post-change verification](#5-post-change-verification)
- [Failure handling](#failure-handling)
- [Output contract](#output-contract)
- [Reference material (load on demand)](#reference-material-load-on-demand)
- [Verification checklist](#verification-checklist)

## Overview

Use this skill to audit and maintain **AppID and IDP/IPS entitlements** and
**offline signature content** across standalone SRXs, vSRXs, and chassis
clusters. It carries one operation from read-only inventory through licensing,
signature installation, verification, and cleanup without losing context.

**Two independent approval gates.** Licensing and signature installation are
separate mutations with separate blast radii, so they take separate approvals:

| Gate | Authorizes | Does **not** authorize |
|---|---|---|
| **A — licensing** | `request system license add` on named devices | any signature change |
| **B — signatures** | offline extraction and `security-package install` | any further licensing |

Read-only inventory, entitlement checks, version checks, and reporting authorize
**neither**. Approval for one gate never carries to the other, and neither
survives into a later run.

**Modes:** `audit only` · `license only` · `signature update only` ·
`license then signature update`. Every mode begins with the read-only baseline.

## Scope and routing

Use for entitlement inventory and expiry reporting, license installation from a
user-supplied file, mixed licensed/unlicensed fleets, offline IDP/IPS and AppID
signature updates, signature and detector version reporting, chassis-cluster
license or content parity, and fleet-wide post-change verification and cleanup.

Do **not** use for Junos software upgrades, IDP policy design or rule authoring,
or unrelated security-policy changes. Route policy questions to `srx-policy` and
full-config extraction to `parsing-srx-configs`.

## Runtime intake

Use this skill only for SRX entitlement and signature-content maintenance. Use `srx-policy` when the IDP policy or rulebase itself is in question. Before acting, inspect the request, artifacts, and approved read-only evidence. If unresolved facts materially change safety, scope, correctness, confidence, or output, read `references/runtime-intake.md`. For each unresolved material fact whose catalog condition is true, invoke Claude `AskUserQuestion` or Codex `request_user_input` before continuing or issuing an open-ended request. Ask at most three single-select catalog questions per round. After each response, ask another round whenever any unresolved material catalog condition remains true; continue only when none remain. Do not repeat answered questions or show the full catalog. Without a native tool, present each selected catalog question with its 2-3 labeled choices and a free-text `Other` path in concise plain text; do not substitute a generic checklist. Never request secrets or unredacted customer data. Answers are context, not live-change approval; obtain separate explicit approval before configuration, commit, upgrade, reboot, delete, or failover.

## 1. Intake and read-only baseline

Run this for every mode, before proposing any change.

1. **Resolve the exact device inventory first.** Never pass an unresolved name
   or a guessed alias to a device tool.
2. Gather Junos versions and chassis-cluster topology.
3. Check AppID and IDP/IPS entitlement **independently** — one can be valid
   while the other is missing or expired.
4. Record installed / needed / expiry / permanent-or-date-based per feature.
   **Never return raw license material** (see [Secret handling](#secret-handling)).
5. Record current IDP attack-database, detector, AppID package, and
   protocol-bundle versions.
6. Enumerate every logical device **and** every underlying cluster node.
7. Present the license targets and the signature targets **separately**, so the
   operator approves each on its own evidence.

Commands and output parsing: `references/licensing.md` §Baseline.

> **A logical-device total is not cluster evidence.** Count logical devices and
> node records separately, and carry both counts through to the report.

## 2. Gate A — license installation

Require explicit approval naming the devices to license. Present the sanitized
entitlement table, the count of devices to be changed, and the cluster nodes
involved. **Approval here authorizes licensing only.**

### Secret handling

Non-negotiable, and they apply to every mode:

- **Never display, summarize, quote, hash, or otherwise expose license-file
  contents or keys** — not in chat, not in a diff, not in a log line.
- Never place a license file in a repository, issue, pull request, chat
  response, shell history, diagnostic log, or reusable fixture.
- Validate the source is an expected, non-empty **regular file** and not a
  symlink, and keep the original **outside** any repository.
- Stage with restrictive ownership and mode; suppress raw `license add` output
  and derive only sanitized success/failure fields from it.
- Remove temporary transport and device copies after verification, and verify
  their absence. Leave the operator's original source file untouched.

### Install and verify

1. Stage outside the repository with restrictive ownership and mode.
2. Transfer to a narrowly scoped temporary device path.
3. Install: `request system license add <device-path>`
4. Verify AppID and IDP/IPS **independently**: state active, installed count
   at least one, needed count zero, expiry recorded.
5. **License every cluster node independently.** Do not infer secondary-node
   state from a logical-cluster or primary-node response.
6. Delete the device copy; verify it is gone.
7. Remove intermediate staging and host-key artifacts.
8. Re-run the entitlement audit **before** offering the signature phase.

### Transport fallback

Modern OpenSSH `scp` uses SFTP by default; some Junos accounts reject the
subsystem with `subsystem request failed on channel 0`. Probe harmlessly first.
Only if the probe proves SFTP is the sole failure, use legacy mode (`scp -O`)
for that node. Full procedure and probe: `references/licensing.md` §Transport.

> **A zero exit status from a cluster copy is not proof the secondary received
> the file.** Verify file presence on each node directly before installing.

## 3. Gate B — signature installation

Require a **second** explicit approval. A licensing approval is not sufficient
and must not be treated as one.

Before asking, establish and present:

- valid AppID and IDP/IPS entitlements on every target;
- the target signature version;
- a validated offline archive, located outside the repository;
- device storage headroom and staging paths; and
- the pilot device, batch size, cluster behavior, and rollback/stop conditions.

## 4. Offline signature update

1. Copy the trusted offline bundle to a temporary device path.
2. **Update one pilot device first.**
3. Extract, then poll to a terminal state:
   ```text
   request security idp security-package offline-download package-path <device-path>
   request security idp security-package offline-download status
   ```
4. Continue only after the terminal offline-download **success** state.
5. Install, then poll to a terminal state:
   ```text
   request security idp security-package install
   request security idp security-package install status
   ```
6. Continue only after the terminal attack-database **success** state.
7. Verify the pilot's IDP attack database and AppID package equal the target.
8. Only then update remaining standalone devices in small bounded batches.
9. On a cluster, initiate through the primary and let Junos validate the primary
   before installing on the secondary. Poll and verify **each node** separately.
10. Stop fan-out on any extraction, installation, validation, or version mismatch.

> **Poll on condition, never on elapsed time.** A fixed sleep is not evidence of
> completion, and `In progress` is not a terminal state. Parse exact terminal
> strings or structured fields; avoid fragile over-escaped regular expressions.

Bundle layout, exact terminal states, and batching: `references/offline-signatures.md`.

## 5. Post-change verification

For every logical device **and** every node:

```text
show security idp security-package-version
show services application-identification version
show services application-identification status
```

Verify: IDP/IPS attack-database version equals target · detector version present
· AppID package version equals target · AppID status active · cluster nodes
match each other · entitlement still active · no target reports an incomplete or
failed install · temporary installer and license files absent.

**Version tokens can carry qualifiers such as `(Minor)`.** Normalize the token
for comparison without discarding the qualifier from the report.

**If Junos reports the data-plane update was not performed because no active IDP
policy exists**, classify the package install as *successful with an operational
warning*. Do **not** claim IDP enforcement is active. Full matrix:
`references/verification-troubleshooting.md`.

## Failure handling

| Condition | Required behavior |
|---|---|
| AppID or IDP/IPS entitlement missing or expired | Report affected devices, stop the signature phase |
| License source unsafe or inside a repository | Stop; request a safe source location |
| SFTP subsystem unavailable | Prove with a harmless probe, then narrowly scoped `scp -O` |
| Cluster aggregate hides node state | Verify every node directly |
| Offline archive absent or invalid | Stop before extraction or install |
| Offline download still in progress | Keep condition-based polling to the defined timeout |
| Install fails | Stop fan-out, preserve sanitized status, follow vendor rollback guidance |
| Secondary waiting for primary validation | Normal; keep polling both nodes |
| Secondary disabled or unhealthy | Verify content directly; report HA health separately |
| No active IDP policy | Report successful install **plus** data-plane warning |
| Version contains a qualifier such as `(Minor)` | Normalize the token, keep the qualifier in the report |

## Output contract

Return a sanitized table:

| Field | Meaning |
|---|---|
| Device | Inventory name or approved alias |
| Nodes | Standalone, or cluster node count |
| AppID license | Active / missing / expired, plus expiry |
| IDP/IPS license | Active / missing / expired, plus expiry |
| AppID before/after | Signature version |
| IDP/IPS before/after | Attack-database version |
| Detector | Detector version |
| Result | Audited / licensed / updated / skipped / failed |
| Notes | Cluster, policy, data-plane, cleanup, or rollback warning |

**Never include** license keys, raw entitlement blobs, credentials, internal
addresses, or local secret paths.

## Reference material (load on demand)

- `references/licensing.md` — baseline commands, entitlement parsing, staging,
  transport and the SFTP probe, per-node licensing, cleanup.
- `references/offline-signatures.md` — bundle validation, extraction, terminal
  states, pilot-then-batch rollout, cluster sequencing.
- `references/verification-troubleshooting.md` — per-node verification matrix,
  version-qualifier normalization, failure interpretation, rollback.
- `references/runtime-intake.md` — intake question catalog.

## Verification checklist

- [ ] Device inventory resolved before any device tool call
- [ ] AppID and IDP/IPS entitlements checked independently
- [ ] Licensing and signature approvals obtained **separately** — Gate B was
      requested on its own evidence and answered on its own, not inferred from
      a combined instruction such as "license the fleet and update signatures"
- [ ] No license material in any output, log, repository, or fixture
- [ ] Every cluster node licensed and verified individually
- [ ] Pilot verified before any fan-out; batches bounded
- [ ] Polling is condition-based against terminal states, never a fixed sleep
- [ ] Post-change versions equal the target on every logical device and node
- [ ] Temporary device and staging artifacts removed and their absence verified
- [ ] No-active-policy and disabled-node conditions reported without overclaiming

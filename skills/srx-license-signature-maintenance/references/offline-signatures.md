# Offline Signature Updates

## Contents

- [Preconditions](#preconditions)
- [Archive validation](#archive-validation)
- [Rollout shape](#rollout-shape)
- [Extraction](#extraction)
- [Installation](#installation)
- [Polling rules](#polling-rules)
- [Chassis clusters](#chassis-clusters)
- [Stop conditions](#stop-conditions)
- [Cleanup](#cleanup)

Reference for the `srx-license-signature-maintenance` skill; load on demand.
Everything here runs **only** under Gate B approval. A Gate A licensing
approval does not authorize any of it.

## Preconditions

Confirm all of these before asking for Gate B, not after:

- AppID **and** IDP/IPS entitlements are active on every target;
- the target signature version is known and stated;
- the offline archive is validated and lives **outside** any repository;
- each device has storage headroom and a chosen staging path; and
- the pilot device, batch size, cluster behavior, and stop conditions are
  written down and presented.

Any device failing the entitlement check is **excluded** from the signature
phase and reported — not carried along in the hope it works.

## Archive validation

The combined bundle carries both the IDP attack database and the AppID
package. Before staging, confirm the archive exists, is a regular file, is
non-empty, and is readable. If the archive is absent or invalid, **stop before
extraction** — a partial extraction leaves the device in a state that is harder
to reason about than not having started.

Unlike a license file, the bundle is **not secret**. It may be retained on a
central staging host for reuse across a fleet. Target-side copies are still
removed after verification.

## Rollout shape

```text
pilot device  ->  verify fully  ->  bounded batch  ->  verify  ->  next batch
```

Never fan out before the pilot has been verified against the target version.
The pilot is what turns "the command returned success" into evidence that this
bundle installs correctly on this platform and release.

## Extraction

```text
request security idp security-package offline-download package-path <device-path>
request security idp security-package offline-download status
```

Poll the status command until it reports a **terminal** state. Proceed only on
terminal success.

## Installation

```text
request security idp security-package install
request security idp security-package install status
```

Poll again to a terminal attack-database state. Proceed only on terminal
success.

## Polling rules

These are the rules that separate a real check from a plausible-looking one:

- **Condition-based, never time-based.** A fixed sleep followed by "it must be
  done by now" is not evidence. Poll the status command and read what it says.
- **`In progress` is not terminal.** Neither is an empty response, nor a
  timeout. Keep polling to the defined ceiling, then report a timeout as a
  timeout — not as a failure and not as a success.
- **Parse exact terminal strings or structured fields.** Avoid fragile
  over-escaped regular expressions; they turn a vendor wording change into a
  silent false pass.
- **Bound the wait.** Define a per-device timeout up front. On expiry, stop
  fan-out and report which devices are still unresolved.

## Chassis clusters

1. Initiate through the **primary**.
2. Junos validates the primary before the secondary proceeds. A secondary that
   reports *waiting for primary validation* is behaving **normally** — keep
   polling both nodes rather than treating it as an error.
3. Poll **each node** to its own terminal state.
4. Verify the installed versions **per node**. A cluster-level version response
   is not evidence for the secondary.
5. A secondary that is administratively disabled or unhealthy can still receive
   package content. Verify its content directly, and report its HA health as a
   **separate** finding — do not merge the two into one verdict.

## Stop conditions

Halt fan-out immediately, preserve sanitized status, and report on any of:

- extraction failure on any device;
- installation failure on any device;
- validation failure on any device;
- a post-install version that does not equal the target;
- a cluster whose nodes disagree after install; or
- a polling timeout.

Resuming after a stop requires re-establishing the baseline for the affected
devices. Do not resume a partially completed batch from memory of what was
"probably fine".

## Cleanup

Remove target-side archives after successful verification and confirm their
absence. Retain the central non-secret bundle only if the operator wants
reusable staging; say which you did.

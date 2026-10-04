# Licensing — Baseline, Staging, Transport, Cleanup

## Contents

- [Baseline (read-only, every mode)](#baseline-read-only-every-mode)
- [Staging (Gate A)](#staging-gate-a)
- [Transport](#transport)
- [Install (Gate A)](#install-gate-a)
- [Verify (Gate A)](#verify-gate-a)
- [Cleanup](#cleanup)
- [Failure interpretation](#failure-interpretation)

Reference for the `srx-license-signature-maintenance` skill; load on demand.
Everything here runs **only** under Gate A approval, except the Baseline
section, which is read-only.

## Baseline (read-only, every mode)

Resolve the device inventory before calling any device tool. Then, per device:

```text
show version
show chassis cluster status
show system license
show services application-identification version
show services application-identification status
show security idp security-package-version
```

`show system license` is the entitlement source. Read it per feature — **AppID
and IDP/IPS are separate entitlements and fail independently**. For each,
capture:

| Field | Meaning |
|---|---|
| Feature name | The licensed capability |
| Licenses installed | Count; zero means no entitlement |
| Licenses needed | Non-zero means the running config demands more than is installed |
| Expiry | A date, or permanent |

Record `installed`, `needed`, `expiry`, and whether the grant is permanent or
date-based. Report those fields only — **never the license key, the raw
entitlement blob, or any identifier from it**. Note that `show system license`
output also carries `License identifier`, `Software Serial Number`, and
`Customer ID`; those are part of the entitlement material and stay out of the
report too.

The feature names to match on are **`IDP-SIG`** and **`APPID Signature`**
(verified live). Do not grep for "IDP" alone — other licensed features exist
alongside them.

> **`used` does not mean "active policy".** A device can report `IDP-SIG` with
> `used 1` while `show security idp status` reports `Policy Name : none`.
> Observed live. To know whether IDP is actually enforcing, read the policy
> name — never infer it from the license counter.

### Cluster baseline

`show chassis cluster status` establishes membership.

> **`show system license` takes no `node` argument.** Verified on a live
> 2-node vSRX cluster (Junos 24.4R1.9): `show system license node 0`,
> `node node0`, `node 1`, and `node all` all return
> `syntax error, expecting <command>`. Do not write any of them — unlike the
> IDP and AppID version commands, this one has no per-node form.

To obtain per-node entitlement state, reach each node's routing engine and run
the plain command there:

```text
request routing-engine login node 1
show system license
exit
```

Repeat per node. If a node cannot be reached, record it as an **unverified
node**, not as a pass.

> A cluster-level license response can reflect the primary alone. A valid
> primary tells you nothing about the secondary. Treat any aggregate as
> unverified until each node has answered for itself.

Count logical devices and node records separately and carry both counts
forward; a logical-device total is not cluster evidence.

## Staging (Gate A)

Before touching a device, validate the source:

- it exists, is a **regular file**, and is non-empty;
- it is **not** a symlink;
- it is **outside** any repository or working tree.

If any check fails, stop and ask for a safe source location. Do not copy the
file into the repository to "make it easier".

Stage to a private directory with restrictive ownership and mode. Never place
the file where a shell history, diagnostic bundle, or log collector will pick
it up. Leave the operator's original untouched.

**The path itself is metadata.** License filenames routinely encode a customer,
site, serial, or date, and the path appears wherever the command does — shell
history, a tool-call description shown to the operator, a session log. So:

- run transfers with history suppressed (`HISTFILE=/dev/null …`, or the
  equivalent for the shell in use);
- refer to the file generically in any description or narration ("the supplied
  entitlement file"), never by full path; and
- prefer a neutral staging filename over copying the operator's name through.

This does not make the path secret, but it stops it being broadcast by default.

## Transport

Modern OpenSSH `scp` speaks SFTP by default. Some Junos accounts reject the
subsystem:

```text
subsystem request failed on channel 0
```

**Probe before assuming.** Use a harmless transfer to establish whether SFTP is
genuinely the failure, rather than switching modes on a guess:

1. Attempt the standard transfer of a small throwaway file.
2. If it fails, read the error. Only the subsystem message above justifies the
   fallback — an auth failure, a host-key mismatch, or a routing problem does
   not, and switching modes will hide it.
3. On a proven subsystem failure, retry that node with legacy mode:
   `scp -O <local> <user>@<device>:<device-path>`
4. Confirm the file exists on the device before invoking any install.
5. Remove the throwaway file and any temporary host-key material.

> **Never treat a zero exit status from a cluster copy as proof the secondary
> received the file.** Copy to, and verify on, each node explicitly.

## Install (Gate A)

```text
request system license add <device-path>
```

Suppress the raw command output. Derive only sanitized fields from it:
success or failure, the feature names affected, and any error class. **Do not
echo, quote, summarize, or hash the license content**, including in an error
path — a failed add often echoes the offending line.

License **every node independently**. On a cluster this means the transfer,
the add, and the verification each happen per node.

## Verify (Gate A)

Re-read entitlement per feature and per node. Require all of:

- state is active;
- installed count is at least one;
- needed count is zero; and
- expiry is recorded.

An entitlement that reports active with a non-zero `needed` count is **not**
satisfied — the config demands more than is installed.

## Cleanup

1. Delete the device copy and **verify its absence**, do not assume the delete
   worked.
2. Remove intermediate staging directories.
3. Remove temporary host-key artifacts created by the probe or transfer.
4. Confirm the operator's original source file is unmodified and still in place.

**If cleanup fails, that is a security finding, not a footnote.** If the delete
errors, or verification still shows the file present after a second attempt:
stop, do not proceed to further devices, and report the device and path as
requiring manual remediation. A license file left on a production firewall is
the failure mode this whole section exists to prevent — silently continuing
turns one leaked file into a fleet-wide leak.

Re-run the entitlement audit after cleanup, before offering Gate B. A signature
phase must never be proposed on the strength of a pre-licensing baseline.

## Failure interpretation

| Symptom | Reading | Action |
|---|---|---|
| `needed` non-zero after add | Config demands more entitlement than installed | Report per device; do not proceed to signatures |
| Expiry in the past | Entitlement lapsed | Report and stop the signature phase for that device |
| Add succeeds, feature still inactive | Feature may need a process restart or is unsupported on the platform | Report; do not claim the feature is active |
| Secondary shows no license, primary does | Per-node licensing incomplete | License the secondary explicitly |
| `subsystem request failed on channel 0` | SFTP unavailable on that account | Probe, then narrowly scoped `scp -O` |
| Any other transfer error | Not an SFTP problem | Diagnose it; do **not** switch transport modes |

# Verification and Troubleshooting

## Contents

- [Per-target verification matrix](#per-target-verification-matrix)
- [Version-token normalization](#version-token-normalization)
- [No active IDP policy](#no-active-idp-policy)
- [Disabled or unhealthy cluster secondary](#disabled-or-unhealthy-cluster-secondary)
- [Troubleshooting table](#troubleshooting-table)
- [Reporting discipline](#reporting-discipline)

Reference for the `srx-license-signature-maintenance` skill; load on demand.
Read-only throughout — nothing here changes device state.

## Per-target verification matrix

Run against **every logical device and every node**:

```text
show security idp security-package-version
show services application-identification version
show services application-identification status
show system license
```

**On a chassis cluster, the version commands take a node argument and the
license command does not.** Verified on a live 2-node vSRX cluster
(Junos 24.4R1.9):

```text
show security idp security-package-version node 0     # works, output prefixed "node0:"
show services application-identification version node 0   # works
show system license node 0                            # SYNTAX ERROR — no node form
```

So: use `node 0` / `node 1` for the IDP and AppID version reads, and reach each
routing engine individually for the license read (see
`licensing.md` §Cluster baseline). `show version invoke-on all-routing-engines`
is a convenient way to confirm both nodes are answering at all.

| Check | Pass condition |
|---|---|
| IDP/IPS attack database | equals the target version |
| Detector | a version is present |
| AppID package | equals the target version |
| AppID status | active |
| Cluster parity | every node reports matching versions |
| Entitlement | still active after the change |
| Install state | no target reports incomplete or failed |
| Cleanup | temporary installer and license files absent |

**Count logical devices and node records separately.** A fleet report of "34
devices updated" is not evidence about a cluster's 36 node records, and the two
totals should both appear in the output.

### Why per-node is not paranoia

Observed on a live 2-node cluster during validation:

```text
show services application-identification version node 0
  node0:  Application package version: 0
show services application-identification version node 1
  node1:  Application package version: 3929 (Minor)
```

The nodes disagreed — AppID installed on the secondary, absent on the
**primary** — while the IDP attack database matched on both. Every shortcut
available would have missed it: the cluster-level read, a primary-only read,
and checking IDP alone. Only reading both components on both nodes surfaced it.

Report a node mismatch as a finding in its own right, not as a fleet-level
version number with a footnote.

## Version-token normalization

**The IDP and AppID commands do not use the same format.** Do not write one
parser and point it at both. Verified live on Junos 24.4R1.9 / 25.4R1.12 /
26.2R1.7:

```text
# show security idp security-package-version
  Attack database version:3929(Minor, Thu Jul 23 13:53:38 2026 UTC)
  Detector version :12.6.180260106
  Rollback Attack database version :N/A(N/A)

# show services application-identification version
  Application package version: 3929 (Minor)
  Release date: Thu Jul 23 13:53:38 2026 UTC
```

| | IDP attack database | AppID package |
|---|---|---|
| Space before `(` | **no** | **yes** |
| Qualifier contents | severity **and** timestamp | severity only |
| Build date | inside the qualifier | separate `Release date:` line |

So accept optional whitespace before the parenthesis, and do not assume the
qualifier contains a date — for AppID the date is a different field entirely.

Normalize the numeric token for comparison against the target, but **keep the
whole qualifier in the report**. Stripping it loses the build date the operator
may need; comparing without stripping produces a false mismatch. Do both:
compare on `3929`, report the qualifier verbatim.

`Detector version` is a plain dotted string with no qualifier, compared as-is.

### Two values that are not versions

- **`Application package version: 0`** means **no AppID package is installed**,
  not a parse failure. Treat `0` as absent and report it as a gap, never as a
  version that merely differs from target.
- **`N/A(N/A)`** in a rollback field means the device has no rollback point.
  Normalization yields an empty token; that is correct and is not an error.
  A device with no rollback simply has no fallback if an install goes bad —
  worth stating in the report, not worth failing on.

**Absent is not the same as unknown.** For an **AppID package-version read**
(`show services application-identification version`) there are three outcomes,
not two:

| AppID package-version read | State | Report as |
|---|---|---|
| a parsed `0` | absent | no package installed |
| a parsed non-zero version | installed | the version |
| empty, a timeout, or anything that does not parse | **unknown** | read failed — say so |

Do not collapse the third row into the first. Reporting "no package installed"
because a read timed out is the same overclaim as reporting enforcement active
with no IDP policy: it converts absence of evidence into evidence of absence,
and sends the operator after the wrong problem.

**This table is scoped to AppID package-version reads.** It does not govern
rollback fields: `N/A(N/A)` in a *rollback* field is the documented
no-rollback-point case above — a known fact about the device, not a failed
read. Same token, different field, different meaning.

## No active IDP policy

Junos may report that the **data-plane** update was not performed because no
active IDP policy exists. This is not an install failure.

- Classify the package installation as **successful**.
- Attach an **operational warning**.
- **Do not claim IDP enforcement is active.** The signatures are present;
  nothing is inspecting traffic with them until a policy activates IDP.

This distinction matters more than it looks: reporting "IDP updated" on a device
with no active policy tells the operator they are protected when they are not.

## Disabled or unhealthy cluster secondary

A secondary can complete the package installation while its HA state is
disabled or unhealthy. Report these as **two separate facts**:

1. content state — versions verified per node; and
2. HA health — reported as-is, and not repaired by this skill.

Merging them either overstates HA health or understates a successful content
update.

## Troubleshooting table

| Symptom | Likely reading | Response |
|---|---|---|
| Status stays `In progress` past the timeout | Slow device, or a stalled job | Report a timeout as a timeout; stop fan-out; do not guess an outcome |
| Extraction succeeds, install fails | Bundle/platform mismatch, or space | Stop fan-out, preserve sanitized status, follow vendor rollback guidance |
| Post-install version below target | Wrong bundle staged, or a partial install | Re-verify the archive; treat as a stop condition |
| Nodes disagree after install | Secondary did not complete | Verify the secondary directly; do not accept the cluster aggregate |
| AppID active, IDP version unchanged | Only one component installed | Verify each component separately; both must equal target |
| Entitlement lapses mid-run | Date-based grant expired | Stop the signature phase for that device and report |
| Version token has a qualifier | Normal | Normalize for comparison, retain in report |
| Cleanup command returns success but file remains | Path or permission issue | Verify absence explicitly; report residue rather than assuming |

## Reporting discipline

The output table is sanitized by construction. Before returning it, confirm it
contains **no** license keys, raw entitlement blobs, credentials, internal
addresses, or local secret paths — including inside error strings and notes
columns, which is where they most often leak.

State plainly what was **not** verified. A device that could not be reached, a
node that did not answer, or a check that was skipped belongs in the report as
an explicit gap, never as an assumed pass.

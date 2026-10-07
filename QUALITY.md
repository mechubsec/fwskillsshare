# Quality and Review

Round-by-round review history for the skills in this repository. Summary and caveat live in the [README](./README.md#quality-and-review).

**26 of the 33 skills** have passed independent technical review. The exceptions
are `clearpass-proxmox-deploy`, `csrx-proxmox-deploy`, `srx-ips`, `srx-mnha-builder`, and `srx-cluster-to-mnha`, which ship as drafts,
while `parsing-firepower-configs` and `srx-syslog-logging` have not yet been through the
two-stage review described below. The original 21
were first reviewed on 2026-06-30, then re-reviewed on 2026-07-02 with a
two-stage process: an OpenAI Codex CLI review per skill (vendor command/syntax
correctness for Cisco ASA/FTD, FortiGate, PAN-OS, and Junos SRX;
schema/field accuracy; standards/control-ID accuracy; secret hygiene) followed
by per-skill application QA tests (fixture execution for the parsers,
engineer-walkthrough scenarios for the playbooks, control-ID spot-checks for the
compliance skills). Disputed Junos syntax claims were settled empirically by
commit-checking on a live vSRX 24.4R1. All findings were remediated and the four
`parsing-*` skills share one byte-identical intermediate schema (verified by
`scripts/check-shared-schema.py`).

A third round on 2026-07-04/05 applied an authoring-quality pass across those original 21 skills (frontmatter, discovery keywords, secret redaction, cross-skill hand-offs, progressive disclosure into `references/` files), then closed it out with fresh clean-context retrieval tests against the restructured skills — every question had to be answerable from the SKILL.md pointers alone. The tests passed and surfaced a handful of fixes (including two operational-command syntax errors caught and corrected by live verification on vSRX 24.4R1), all remediated.

The 25th skill, `srx-chassis-cluster-proxmox`, was validated on 2026-08-11 by a different method: instead of a document review, it was executed. A second chassis cluster was built from a factory template on a separate host by following the skill's own procedure, on a different Junos release (26.2R1.7) than the reference build (24.4R1.9). The run confirmed the skill's NIC-mapping rule and reth MAC formula on both releases, and **falsified its fabric-MTU claim** — forcing the fabric segment to 1500 broke nothing observable, which established that the fault is latent rather than immediate. That correction and two others were folded in before release. The throwaway cluster was destroyed afterwards.

The 26th skill, `srx-initial-setup`, was validated on 2026-08-25 by execution rather than document review. It was run end-to-end against a live SRX345 (`srx345-dual-ac`, Junos 21.2R3-S6.11) from factory-default state through the baseline policy stage. Both read and write paths were exercised: the gate protocol, `commit confirmed`, per-stage verification, and the confirming commit were all validated on hardware. The run found 23 defects, promoted the skill from 1.1.0 to 1.3.0 (PR #58, commit b5a4ee7), and corrected four silent failures that would have reported gaps closed while changing nothing or degrading the device. Still unvalidated on hardware: rollback-on-verification-failure, the other Branch SKUs, and all campus and datacenter platforms.

| Family | Skills | Reviewed |
|--------|-------:|:--------:|
| Config parsers | 5 | 4 / 5 |
| SRX operational playbooks | 15 | 11 / 15 |
| NGFW compliance and STIG playbooks | 7 | 7 / 7 |
| Cross-vendor tooling (audit · convert · diff) | 3 | 3 / 3 |
| Security management and NAC deployment | 3 | 1 / 3 |
| **Total** | **33** | **26 / 33** |

The later `srx-disa-stig-compliance` addition completed an independent review on
2026-07-22. That review verified the NIST checklist 657 / DISA Y25M01 artifact,
all 148 source-ordered NDM/ALG/IDPS/VPN rule identities and CAT severities,
conservative status/evidence behavior, Junos schema paths and source conflicts,
installer integration, and synthetic behavior/mutation fixtures. All findings
were remediated and re-reviewed cleanly.

`sd-onprem-proxmox-deploy` was added later and was not part of the 2026-06-30,
2026-07-02, or 2026-07-04/05 review rounds. It passed the repository's
portable-package and runtime-intake validation, and was promoted to **v1.0.0**
on 2026-08-05 after the maintainer ran the full deployment to completion three
separate times — the repeat runs its draft label was waiting on. Its
**device-onboarding NTP gate** was verified read-only against production SRXs on Junos 26.2R1: the
hidden `set system processes ntp enable` was confirmed valid and present, and the
pass/fail criterion was moved onto `show ntp associations` after live output
showed `sync_ntp` appearing alongside `no_sys_peer` (so it cannot mean "synced")
while a device missing `clock_sync` was in fact synchronized with a selected peer
at full reach (so its absence cannot mean "failed").

On **2026-07-31** `firewall-best-practices-audit` and `parsing-srx-configs` were
re-validated against **live** SRX devices over NETCONF (read-only), covering a
policy-light standalone vSRX and a 101-policy two-node chassis cluster. The run
is documented in
[the live SRX audit](./docs/skill-tests/2026-07-31-firewall-best-practices-audit-live-srx.md)
and found two real defects, both since fixed: `security dynamic-address` objects
were not extracted (producing false `SEC-ORPHAN-REF` on every GeoIP or
feed-backed reference), and `match dynamic-application` was dropped (collapsing
distinct AppID-scoped rules into false `SEC-REDUNDANT` pairs, and letting an
AppID-scoped deny pass as a terminal deny-all so `SEC-NO-DENY-ALL` stayed
silent). `parsing-srx-configs` **v1.4.0** and `firewall-best-practices-audit`
**v1.2.0** carry the fixes; both behaviors are pinned by regressions in
`scripts/check-audit-rule-contract.py`. Two catalog gaps found in the same run —
no check for a rule name contradicting its configured action, and none for
plaintext threat-feed transport — remain open.

`srx-license-signature-maintenance` was added on 2026-07-31 and promoted to
**v1.0.0** on 2026-08-05. It passed portable-package, runtime-intake, installer,
and its own behavioral contract validation
(`scripts/check-srx-license-signature-contract.py`), a five-reviewer independent
pass, and a read-only fleet audit across 9 devices / 10 node records on Junos
24.4R1.9, 25.4R1.12, and 26.2R1.7 —
[documented here](./docs/skill-tests/2026-08-05-srx-license-signature-live-validation.md).

That live run earned its keep. On a two-node cluster it caught the nodes
**disagreeing** — AppID package installed on the secondary, absent on the
primary — while IDP matched on both; the cluster-level read, a primary-only
read, and an IDP-only read would each have missed it. It also corrected four
documentation defects: `show system license` accepts **no** `node` argument
(every per-node form is a syntax error, while the IDP and AppID version commands
*do* take `node 0` / `node 1`); IDP and AppID use **different** version-qualifier
formats; `Application package version: 0` means not-installed rather than a
version mismatch; and a `used` counter of 1 does **not** imply an active IDP
policy.

The **mutating** paths (`request system license add`,
`security-package install`) remain unexercised against hardware — running them
needs a real entitlement file or signature bundle and changes device state — so
that boundary is stated plainly in the skill-test record.
Its contract validator is offline by construction — it
asserts that the two approval gates stay independent, that unsafe license
sources are refused, that polling only ends on a terminal state, that cluster
aggregates never substitute for per-node evidence, that version qualifiers
survive comparison, and that a package install with no active IDP policy is
never reported as active enforcement. Each of those assertions was
mutation-checked.

`clearpass-proxmox-deploy` was added on **2026-08-13** and is the one skill here
that has **not** been through any independent review round. It ships at
**v0.2.0 (draft)**: the deploy procedure was executed end-to-end once, on
ClearPass **6.14.0.371380** as a C1000V on Proxmox VE 9.2, and the day-2
reference (licensing, HTTPS certificate import, REST API) was confirmed against
that same appliance on 2026-08-15/16. Every claim in its Gotchas is either from
those runs or explicitly marked `[unverified]`. It passed the repository's
portable-package and runtime-intake validation.

Its central finding is that the ClearPass 6.14 KVM image **only boots under
UEFI** — undocumented by the vendor, and silent when violated: the appliance
reaches its GRUB menu and fails every boot attempt, which presents as an
unresponsive keyboard rather than a boot failure. That was confirmed two
independent ways: the on-screen GRUB error
(``can't find command `linuxefi'``), and the image's own
`/boot/grub2/i386-pc/command.lst`, which registers `linux`/`linux16` and no
`linuxefi` at all. The vendor guide's competing IDE disk-bus instruction is
recorded as **unverified rather than disproven** — `virtio-scsi` was verified
working; IDE was not tested. The skill needs a repeat run, and ideally one
non-C1000V flavor, before it earns a stable label.

These are research/operational and assessment-support skills, not certified products: review their output against current vendor documentation, live device behavior, and (for compliance work) a qualified assessor before relying on it.

Each skill also includes optional `agents/openai.yaml` UI metadata for Codex. Claude Code and Hermes continue to use the portable `SKILL.md` content and ignore that product-specific folder.

Run `python3 scripts/check-skill-packages.py` to validate portable frontmatter, reference paths, the combined Codex discovery budget, and all Codex UI metadata. Run `python3 scripts/check-shared-schema.py` to verify the five parser schemas remain byte-identical.

`just security` runs Trivy with the `vuln`, `misconfig`, and `secret` scanners enabled, but only the secret scanner has anything to act on here: this is a Markdown-first repository with no dependency manifests and no configuration files that Trivy's vulnerability or misconfiguration scanners recognize. A clean `just security` run therefore attests to secret hygiene, not to dependency or configuration posture.

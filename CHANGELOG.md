# Changelog

## Unreleased

- **Publishing:** `evals/` is now published to the downstream distribution. The 1.10.0 note said evals are never published; they are still never installed, but `scripts/check-evals.py` ships with `scripts/` and `just lint` fails without them.

## 1.10.0 — Skills restructured to authoring best practice; per-skill evals

Every skill was reviewed against Anthropic's skill-authoring guidance, the agentskills.io specification and this repository's rules, and the gaps were fixed. No device syntax, safety gate or verification procedure changed meaning; every skill takes a patch version bump.

- **Shorter SKILL.md bodies.** The six skills over the recommended 500 lines now sit under it, with detail moved one level down into `references/`: `csrx-proxmox-deploy` 597→455 (`references/gotchas.md`), `srx-ips` 580→482 (`references/commit-and-verification.md`), `sd-onprem-proxmox-deploy` 576→393 (procedure condensed to a staged outline that links the HOWTO, `references/gotchas.md`, new verification checklist), `srx-mnha` 528→459 (`references/srg-details.md`), `srx-dynamic-ip-feed` 512→359 (`references/tls-and-auth.md`), `srx-policy` 511→489 (`references/migration-workflow.md`). Approval, STOP and rollback rules stay inline.
- **Contents lists.** Every SKILL.md and every reference file over 100 lines opens with a `## Contents` list of its sections; every anchor resolves. The shared `intermediate-schema.md` copies remain byte-identical.
- **Parsers:** the Cisco, FortiGate, PAN-OS and SRX application-mapping tables move into each skill's `references/parsing-patterns.md`; `parsing-cisco-configs` gains a worked ACL-to-`services`/`apps` example; the Firepower collection guidance is condensed.
- **firewall-config-conversion:** emitter references no longer point at repository paths of other skills, which do not resolve after a per-skill install; the needed syntax rules are stated inline.
- **srx-mnha-builder:** MCP tools are tied to the Junos MCP server that provides them, with a CLI fallback when none is connected.
- **cis-controls-ngfw-compliance:** the overview drops generic CIS background and states what the skill maps and cannot attest.
- **Evals.** New top-level `evals/` with two or three fresh-session scenarios per skill (prompt, input, must, must not), derived from each skill's own guidance and including a safety or pitfall case. Dev-only: never installed or published. `scripts/check-evals.py` (in `just lint`, with tests in `just test`) requires an eval file for every skill. The scenarios are written but not yet run against an agent.

### Also in this release

- **srx-ips v0.1.2, srx-mnha-builder v0.2.1:** recognize junos-mcp-server with commit confirmed — the [`jgrizzuti/junos-mcp-server`](https://github.com/jgrizzuti/junos-mcp-server) fork, proposed upstream as [Juniper/junos-mcp-server#34](https://github.com/Juniper/junos-mcp-server/pull/34) — as a third server in the capability mapping. It is identified by its `confirm_commit` tool: `load_and_commit_config` always commit-checks first and takes `dry_run` and `confirm_timeout_mins`, `render_and_apply_j2_template` takes `confirm_timeout_mins`, and `confirm_commit` confirms. Both skills warn that re-sending `load_and_commit_config` does not confirm on that server (no diff, no commit). srx-mnha-builder pushes stages there with a 10-minute confirmed commit, both Stage 1 nodes inside one window, and lets an unverified stage roll back instead of pushing an undo. Field-confirmed 2026-10-02 on vSRX 24.4R2.21: dry run left no commit; an unconfirmed 2-minute commit rolled back at +2:45; `confirm_commit` kept the change past the window.
- **Publishing:** never leave bytecode in the staged export tree; gate() now fails-closed on any .pyc or __pycache__.
- **Publishing:** the JNPR downstream keeps its own secret-scan workflow; rust-junosmcp is named without its org.
- **Contributors:** added top-level `CONTRIBUTORS.md` listing the maintainer and contributors, linked from README and CONTRIBUTING.
- **Publishing:** `.gitleaks-vendor.toml` is now published alongside `.gitleaks.toml` so the downstream secret scan can load its vendor rules; the gate now fails if any published gitleaks config extends a file that is not present.
- **Codex review gate:** quota errors and interrupted runs now exit non-zero instead of falsely passing.

## 1.9.0 — SRX MNHA pair builder; skills work with any Junos MCP server

New draft skill **srx-mnha-builder** (#83, reworked in #84 and #86), and `srx-ips` no longer tied to one MCP server (#85). The catalog grows from 31 to 32 skills.

- **Skills are Markdown only.** `install.sh` is the only executable shipped to users; see `AGENTS.md`. The scripts in `clearpass-proxmox-deploy` and `sd-onprem-proxmox-deploy` are grandfathered and tracked for removal in `TODO.md`.
- **Repaired #83 merge damage:** restored the 1.8.0 release notes and the LF endings of `scripts/test-runtime-intake-validator.py`.

**srx-mnha-builder** v0.1.0 (renamed from `srx-mnha-mcp-builder` before first release), a draft skill that builds a new two-node SRX/vSRX Multi-Node High Availability pair end-to-end through a Junos MCP server (Juniper junos-mcp-server or rust-junosmcp). Contributed by Javier Grizzuti (@jgrizzuti) from lab work. The catalog gains one skill, from 31 to 32. Design theory and troubleshooting of a running pair stay in `srx-mnha`; this skill covers the build order and works with either MCP server.

**srx-mnha** v1.3.2 corrects the claim that SRG interface monitoring requires a monitor-object; the bare `monitor interface` form commit-checks on vSRX 26.2R1.7.

- Mode selection (routing, switching/default-gateway, hybrid) and ICL choice (dedicated or shared loopback, optionally encrypted with HA link encryption) during setup; the ICL pre-shared key is set by the user on each node and never passes through the pair sheet, chat, or MCP. Design content defers to `srx-mnha` to avoid duplication.
- One pair sheet used to write per-node stage files from a Markdown stage reference (`references/config-stages.md`) with substituted placeholders (underlay, HA stanza in the flat ≤24.x or grid 26.x model, eBGP signal-route export) plus undo files computed against the device baseline, with a pre-push checklist that blocks management-plane changes, broad host-inbound permissions, a missing ICL BFD permit, a missing activeness probe in routing mode, and export terms without route filters.
- Device dry runs of each stage, separate approval gates for the push, the HA-activation reboot (performed by the user), eBGP, and the failover test.
- Verification reference with formation pass criteria, a diagnostic tree for dual-ACTIVE or Conn State DOWN, and a role-consistency invariant (SRG1 role, VIP, signal route, upstream path selection) re-checked after every failover.
- Server capability mapping: each workflow step (dry run, push, confirm commit, diff, batch commands) mapped to both Juniper junos-mcp-server and rust-junosmcp tools, with commit confirmed and change-set flow where the server supports them.
- Packaged to repository standards — frontmatter, runtime intake, Codex metadata, inventory and installer entries. Lab hostnames and addresses were replaced with neutral node names and RFC 5737 documentation addresses.

Field-confirmed 2026-09-25 on a vSRX 24.4R2.21 hybrid pair (flat model, encrypted ICL): formation, planned failover and failback, and an unplanned uplink failure with BFD 500 ms × 3. The grid-model `vpn-profile` placement for an encrypted ICL on 26.x is not yet confirmed on a device; the skill defers to the device dry run there.

**srx-ips** v0.1.1: Generalized the skill to work with any Junos MCP server that exposes core operational and configuration capabilities, not just Juniper's junos-mcp-server. The MCP server capabilities reference (`references/mcp-server-notes.md`) now documents both Juniper junos-mcp-server v1.1.1 and rust-junosmcp v0.19.0+ with a capability mapping table covering commit check, confirmed commits, change sets, and rollback. All skill text refers capability-first ("where the MCP server supports it") instead of naming one specific server. No change to device syntax, safety gates, or verification procedures.

**Checks:** `check-skill-packages.py` now fails frontmatter values YAML cannot parse (an unquoted `: `, a ` #`, or a character that cannot start a plain scalar), with tests in `scripts/test-skill-packages.py`.

## 1.8.0 — Pinned, checksum-verified installs

The installer no longer installs whatever `main` currently holds. It installs a pinned release tag and verifies the skill payload before copying anything (#77).

- **Pinned release ref.** `install.sh` defaults to this tag (`v1.8.0`) and refuses a moving ref (a branch or `HEAD`); `--ref` accepts `vX.Y.Z` tags only. The `curl | bash` install is no longer offered — clone the tag (or download its tarball) and run `./install.sh` from it.
- **Checksum manifest.** `skills/CHECKSUMS.sha256` lists every file under `skills/`. The installer aborts on a missing or empty manifest, a malformed or `..`/absolute line, any hash mismatch, any file present but not listed (including a nested file named `CHECKSUMS.sha256`), and any symlink in the payload. Regenerate with `scripts/gen-checksums.py`; `scripts/check-checksums.py` verifies it in CI.
- **Signatures are not implemented yet.** `FWSKILLS_REQUIRE_SIGNATURE=1` fails closed until they are; the manifest proves integrity against the tag, not authorship.
- **srx-policy 1.3.0** covers Branch SRX after SRX345 validation (#73). `srx-ips` credits @jgrizzuti as an author (#74).
- **Hygiene:** lab subnets replaced with RFC 5737 documentation addresses (#76); shared gitleaks vendor rules (#75); the secrets check now uses the shared mechubsec gitleaks workflow (#80); links point at the `mechubsec` organization (#79).

## 1.7.0 — SRX IPS skill (draft)

**srx-ips** v0.1.0, a draft skill merging IPS detection triage and custom signature authoring. Contributed by Javier Grizzuti (@jgrizzuti) in #70 from lab work against Juniper's junos-mcp-server, revised before merge, then merged into a single skill. The catalog gains one skill, from 30 to 31.

Covers IPS detection triage — build the active rule table, read logs safely, monitor-to-enforce escalation behind an approval gate — and custom signature design with read-only coverage checks, context/direction/binding choice, false-positive-aware patterns, `commit check` validation, and monitor-mode proof before enforcement.

- Packaged to repository standards — frontmatter, runtime intake, Codex metadata, inventory and installer entries.
- The installer now automatically removes the three retired skill directories (`srx-idp-triage`, `srx-custom-signature-builder`, and `srx-idp`) on every install or uninstall run, regardless of which skills are selected. Existing installations are cleaned up automatically on the next `./install.sh` run. Manual equivalent for anyone who does not re-run the installer: `rm -rf <skills-dir>/srx-idp-triage <skills-dir>/srx-custom-signature-builder <skills-dir>/srx-idp`.
- Safety gates: no `clear log` without archiving and separate approval; no commit used as an attack-name lookup (`show security idp attack detail` and `commit check` instead); commits use a rollback window, and the plain commit in junos-mcp-server's `load_and_commit_config` is called out.
- Lab signatures moved to a reference file with false-positive warnings.
- Juniper junos-mcp-server behavior moved to a version-labelled reference file.

Hardware validation on 2026-09-23 (SRX345, Junos 21.2R3-S6.11) falsified three documented claims and found one mandatory statement the skill had omitted:

- **`commit check` does not reject an unknown predefined attack name** — it accepted `"Non-Existent-Attack"` silently, making passive validation unusable. The skill's `commit check` validation strategy is removed, and the remaining attack-name lookup remains read-only via `show security idp attack detail`.
- **`minimum-port` is not required on `protocol-binding tcp`** — an unbounded binding committed cleanly, contradicting both the skill's rule and the vendor documentation the skill had cited. The skill's minimum-port requirement is removed.
- **No flow-type statement is required** — signatures with no explicit `ip` or `service` flow type committed and became active without it. The skill's flow-type requirement is removed.
- **`direction` is mandatory** — every signature lacking it was rejected at commit with `direction statement missing`. The skill now requires `direction client-to-server` or `direction server-to-client` and explains the scoping semantics: client-to-server applies the pattern to the flow initiator's data, server-to-client to the responder's.

Remaining `[unverified]` items are tracked as a vSRX validation gate in [TODO.md](./TODO.md).

## 1.6.0 — cSRX container firewall deployment on Proxmox

**csrx-proxmox-deploy** v0.1.0, a new skill — deploying a Juniper cSRX container
firewall on Proxmox VE, written from an end-to-end build rather than from vendor
documentation. Ships as a **draft**: validated by execution on Proxmox VE 9.2.20
with cSRX 26.2R1.7 in both secure-wire and routing modes, and not validated on any
other cSRX release or a second estate.

The build's value is in failures that do not announce themselves, so every entry
leads with the observed symptom. The two most expensive:

- **`--cpu host` is mandatory.** Proxmox's default CPU model does not expose SSSE3,
  and `srxpfe` initialises DPDK's EAL even at `CSRX_PACKET_DRIVER=interrupt`.
  Without it the container stays `Up`, every control-plane daemon looks healthy,
  and there is no forwarding plane at all — presenting as
  `usp_ipc_client_open: failed to connect to the server`.
- **Docker macvlan needs `-o macvlan_mode=passthru`.** `bridge` mode never delivers
  unicast frames addressed to a foreign MAC regardless of promiscuous flags, which
  is exactly what cSRX does in secure-wire.

Also records the `CSRX_*` surface split by env-driven versus silently hardcoded
(`CSRX_JUNIPER_CONFIG` discards any `-e` value; `CSRX_JUNOS_CONFIG` is the real
knob), how to rediscover that table for a future release, cSRX's operational CLI
gaps against vSRX, and a verification methodology built on the rule that every
check must be capable of the opposite result.

Undocumented in any vendor material available for this build, cSRX 26.2R1.7 carries a
`CSRX_CRPD` hook and a Linux-FIB-to-Junos-FIB route-import path. It is recorded as
read from the image and **never executed**.

Verified with a clean-context retrieval test: 9 of 10 diagnostic questions
answerable from the skill alone.

## 1.5.0 — SRX NTP process statement, documentation integrity, inventory enforcement

**srx-initial-setup** v1.4.0 and **sd-onprem-proxmox-deploy** v1.2.0 — the hidden
`set system processes ntp enable` statement, and the correct way to read it.
Backed by a live run across 18 reachable SRX/vSRX devices on Junos 24.2R2-S5.3
(SRX345 hardware), 24.4R1.9, 25.4R1.12, and 26.2R1.7, documented in
[the NTP process validation](./docs/skill-tests/2026-08-27-srx-ntp-process-enable-live-validation.md).
Read-only operational commands plus non-activating `commit check`; no
configuration was activated on any device.

`srx-initial-setup` did not mention the statement at all. It configured NTP
servers, then asserted at Stage 2 verification that an association should show
`*` — with no branch for the case where it never does. `mgmt.ntp-absent` is
`blocking`, so an operator hitting that had the run stall with no remedy in the
document. It now proposes `set system processes ntp enable` alongside the
servers, explains that `[edit system processes]` is hidden from CLI completion
(it does not tab-complete, which is why it gets skipped), and adds a
path-first troubleshooting sequence — route, ping, return path through source
NAT, host-inbound-traffic, and only then the daemon.

**The statement's absence is not the same as `disable`, and the skills no longer
gate on its presence.** The validation run set out to confirm that Junos 24 and
later require it, and did not reproduce that: `srx345` on 24.2R2-S5.3 and
`vsrx-ci` on 24.4R1.9 carry no `system processes` configuration at all, run
`ntpd`, and hold a selected peer at `reach 377` with sub-millisecond offset.
Three 24.4 devices that were *not* synchronizing looked like corroboration until
the path was checked — all three had no default route and returned
`ping: sendto: No route to host`, making them `mgmt.default-route-absent` rather
than an NTP fault. What the run does establish is that the statement is a real
enable/disable toggle across 24.2–26.2: `commit check` accepted `ntp enable` on
SRX345 hardware and on 24.4R1.9, and the opposing `ntp disable` on 26.2R1.7.
So three configured states get three readings — `enable` present is correct,
absent is unset and must not be reported as broken, and `disable` present is a
fault to correct. No activating write was performed, so the runtime effect of
`disable` is carried as inferred rather than measured.

`sd-onprem-proxmox-deploy` already carried the statement in its §4a onboarding
gate and described it as "required", listing its presence as a hard gate. That
would have failed both devices above while they were genuinely synchronized —
the same false-negative the skill already warns about for `clock_sync`.
Reclassified to supporting evidence, with `ntp disable` present as the hard
fail. The pass/fail gate in both skills is `show ntp associations`: a `*` peer
with non-zero reach and an acceptable offset.

Stage 2 verification in `srx-initial-setup` gains the evidence table and the
rule that `sync_ntp` alongside `no_sys_peer` is not proof of synchronization.
Entry-state assessment now reads `system processes` separately, because
`show configuration system` alone will not prompt an operator to look for a
hidden hierarchy. `write-safety.md` notes that its existing "never enable NTP in
the commit whose rollback timer you are relying on" rule covers this statement
too — on a device where the daemon was suppressed, this is the statement that
starts the clock moving.

### Documentation integrity and inventory enforcement

Repository maintenance, landed alongside the NTP work. No skill body changed;
every package is byte-identical apart from the five parser README files.

**Six documented counts had drifted from the repository they describe.** The
README review badge said 25/29 while its own catalog body said 26 of 29; the
reproduced installer help said "Install all 24 skills" against a real 29; the
combined description surface was pinned at ~8,400 characters and measures
9,719; and QUALITY.md, `skills/SHARED-SCHEMA.md` and all five schema preambles
still described four parser schemas when `scripts/check-shared-schema.py` has
been comparing five since `parsing-firepower-configs` landed. SHARED-SCHEMA.md
also omitted Firepower from its synchronization instructions, telling
maintainers to update four of the five copies.

**The five parser READMEs were Claude-Code-only.** Each showed one `/name`
invocation and a single `cp -r` into `~/.claude/skills`, though the installer
has supported Codex and Hermes for several releases. They now name the
invocation per runtime, lead with `./install.sh --skill`, and carry file trees
regenerated from disk — every package ships `agents/openai.yaml` and
`references/runtime-intake.md`, and none of the five listed either.
`parsing-firepower-configs` additionally pointed at a
`fixture-minimal-input.json` that has always been `.md`.

**`skills/inventory.json` is now the authoritative inventory.** One entry per
skill with its family and reviewed status, no totals written down, and
`scripts/check-inventory.py` fails when it disagrees with the directories on
disk, `install.sh`, `check-installer.py`, the README badge and body, the
parser and schema counts, or `install.sh --help`. `check-skill-packages.py`
reads its expected names from it, which removed a duplicate
`sd-onprem-proxmox-deploy` that a `frozenset` had been hiding.

**`install.sh` is shellcheck-clean and still Bash 3.2-compatible.** Seven
SC2207 array assignments and three SC2076 membership tests are resolved. The
membership tests became a literal `contains_element` helper rather than
unquoted regexes, which would have matched `.` in filesystem paths as any
character. Deduplication uses a read loop, not `mapfile`: mapfile is a Bash 4
builtin, and the documented `curl … | bash` path still runs under macOS's
stock Bash 3.2.

**New checks.** `scripts/check-markdown-links.py` resolves relative links in
tracked Markdown while deliberately ignoring fenced blocks and inline code,
since historical plans embed snippets whose targets belong to another file.
`just lint` gains the inventory and link checks, `just test` gains their unit
tests, and a new `just shell` recipe runs shellcheck; `guard` now includes it.

Validated with `just fmt`, `lint`, `test`, `shell`, `guard`, `security`,
`release-check` and `e2e`, all exiting 0.

## 1.4.0 — parsing-firepower-configs skill

New skill: **[parsing-firepower-configs](./skills/parsing-firepower-configs/SKILL.md)** v0.1.0 — parses Cisco Secure Firewall (Firepower) FMC- and FDM-managed JSON exports into the shared vendor-neutral intermediate schema. The repository previously claimed FTD coverage but delivered it only for the ASA-style LINA form; this closes the NGFW-layer gap that `firewall-config-conversion` and `firewall-best-practices-audit` had both explicitly deferred. The split from `parsing-cisco-configs` is on **grammar, not product name** — both artifacts are "Cisco FTD" to a human, but an FMC JSON export and a LINA `show running-config` share no parseable syntax. `parsing-cisco-configs` keeps ASA and FTD-LINA and now hands off explicitly in both directions.

Emits the existing shared schema unchanged. Firepower's Prefilter → Mandatory → Default → inheritance chain flattens into a single merged `_rule_index` with provenance in `metadata`, following the Panorama precedent, so there is no schema edit and no ripple into the audit, conversion, or diff skills. All five `intermediate-schema.md` copies remain byte-identical.

- **Multi-endpoint collection guidance.** No single FMC endpoint returns a complete configuration. `references/config-format.md` documents a five-phase dependency-ordered sequence — `accesspolicies/{containerUUID}/accessrules` cannot be fetched before `accesspolicies` yields the `containerUUID`, and per-device interfaces and routing need the `deviceUUID` — plus a 15-row completeness checklist stating what silently breaks when each endpoint is skipped.
- **MONITOR is non-terminal.** A MONITOR rule logs and continues; the shared schema has no non-terminal action. Every MONITOR rule emits a warning and the fixture asserts it, because a naive `allow` mapping tells downstream audit a rule matches and stops when it does not.
- **Paging truncation is a first-class hazard.** A reported total exceeding the items present marks the collection incomplete rather than parsing page one as a whole rulebase.
- **`.sfo` bundles and PDF policy reports are refused, not half-parsed** — undocumented for third-party parsing, so support cannot be claimed under the repository's evidence rule.
- Ships **outside** the two-stage review, disclosed in README and QUALITY.md. Roughly 30% of the endpoint material carries inline `[unverified]` markers: cisco.com returned HTTP 403 to automated access, so sourcing fell back to DevNet and community documentation, and the reference separates what was attempted from what was actually consulted.

**srx-initial-setup** reclassified as reviewed — **26 of 29** skills, up from 25. Validation was by execution rather than document review, on the precedent already set by `srx-chassis-cluster-proxmox`: an end-to-end run against a live SRX345 (`srx345-dual-ac`, Junos 21.2R3-S6.11, 2026-08-25) exercising both read and write paths, which found 23 defects and promoted the skill 1.1.0 → 1.3.0. Rollback-on-verification-failure, the other Branch SKUs, and all campus and datacenter platforms remain unvalidated on hardware. The catalog had still been describing the skill at 1.0.0 with no device validation performed.

Catalog accuracy: skill counts corrected to the measured 29 across README, SKILLS.md, QUALITY.md, and a hardcoded literal in `scripts/check-installer.py` that reported a count it never computed. A second README count statement was contradicting the first, and its exceptions list had been understating what has not been reviewed.


## 1.3.0 — srx-initial-setup policy model opt-out

**srx-initial-setup** v1.1.0 — adds explicit zone-to-zone policy opt-out to align with `srx-policy` skill's enforced global-policy contract. The baseline policy is generated as global policy; when a zone-pair exception applies (existing-estate compatibility, isolated exceptions clearer as zone-pair policies, or customer standards requiring zone-pair contexts), the policy stage routes to `srx-policy` for zone-pair design on non-Branch platforms (Branch SRX zone-pair policy is unowned). Adds runtime intake question `sis_policy_model` to confirm the architecture before generating the baseline.

## 1.2.0 — srx-initial-setup skill

New skill: **[srx-initial-setup](./skills/srx-initial-setup/SKILL.md)** v1.0.0 — first-time SRX bring-up from factory-default or zeroized state to a reachable, zoned, screened, and minimally policied device. Automates Day-0 and Day-1 setup for Branch SRX300/400, campus SRX1600/4120, and datacenter SRX4300/4700/5000 platforms. At 1.0.0 this skill is written from vendor documentation and existing verified repository references; no device validation has been performed. Validation against vSRX and against SRX345, SRX1600, and SRX4700 hardware is deferred to a later release. Key features:

- Assess-first architecture: read-only entry-state assessment classifies device into one of five states before proposing any writes
- Dependency-ordered gap model: closes only the gaps that are actually open, making the skill idempotent
- Per-stage approval gates with confirmed commit and rollback timers on all lockout-risk changes
- Branch factory-default handling: removal of shipped zones, DHCP server, and permissive policy only after replacement management path is verified
- Five stages: access and recovery, management plane, interfaces and zones with host-inbound-traffic, starter IDS screens, and minimal baseline policy
- Entitlement readout across three independent axes (entitled, configured, active) that routes to sibling skills for license mutation and feature configuration

## 1.1.1 — README split

Documentation only. No skill content changed, and every skill keeps the version it
carried in 1.1.0.

- `README.md` trimmed from 783 to 494 lines.
- Per-skill detail for the compliance and SRX operational playbooks moved to
  [`SKILLS.md`](./SKILLS.md).
- The v1.1.0 parser notes below moved out of the README into this file.
- The 21-row intermediate-schema table condensed to prose plus a link at its canonical
  copy, `skills/parsing-srx-configs/references/intermediate-schema.md`.
- Usage examples cut from eleven to five; each skill's own `SKILL.md` carries worked
  examples for its topic.
- `SKILLS.md` and `CHANGELOG.md` added to the downstream publish allowlist, without
  which the published README would link to two files that were never published.

## 1.1.0 — parser improvements from fatcat/converter

Version 1.1.0 of these skills incorporates parsing improvements identified by analyzing the [fatcat/converter](https://github.com/fatcat/converter) JavaScript parsers. The following areas were significantly enhanced based on fatcat's implementation:

**All Skills:**
- Cross-vendor L7 application mapping with 240+ canonical apps, confidence scores, and categories (web, collaboration, email, remote-access, network-mgmt, database, cloud-storage, streaming, voip, auth, tunnel, security, and more)
- Application and Application Group schema definitions with resolution algorithm (vendor-name → canonical → target-vendor)
- Per-vendor application name mapping tables (JunOS `junos-*`, FortiOS uppercase names, PAN-OS unique names like `ssl`/`web-browsing`, ASA port-to-app inference)
- Expanded intermediate schema with `applications`, `application_groups`, `system`, `virtual_routers`, `admin_users`, `vpn_tunnels`, `ospf_config`, `bgp_config`, `dhcp_config`, `residual_raw` definitions
- IPv6 support throughout (addresses, routes, interface IPs, ICMPv6 services)
- Full VPN/IPsec parsing with IKE/IPsec proposal chain resolution and weak algorithm detection
- Detailed OSPF/OSPFv3 parsing (areas, interface-level settings, authentication, redistribution)
- Detailed BGP parsing (per-neighbor attributes, timers, route-reflector, redistribution)
- DHCP server and relay configuration with pool/reservation detail
- System config extraction (hostname, DNS, NTP, management services)
- Admin user parsing with SSH key migration and role mapping
- Interface parsing (types: LAG, loopback, tunnel, VLAN; IPv6, MTU, DHCP client, subinterfaces)
- Residual/unhandled config capture and categorization
- Version detection from config headers

**Cisco ASA (parsing-cisco-configs):**
- Port-to-application inference table (protocol+port → canonical app) for cross-platform conversion
- ASA named port keyword mapping (www→80, domain→53, etc.)
- ACL remark attachment to next rule as comment
- Anonymous object creation for inline ACL addresses
- Source port parsing in ACLs
- DHCP server commit trigger pattern (`dhcpd enable`)
- Management access protocol tracking per zone
- VTI tunnel interface assembly with IPsec profile resolution

**FortiGate (parsing-fortinet-configs):**
- FortiOS application name resolution table with application groups and compound proposal parsing
- Wildcard/wildcard-fqdn type conversion (to network/fqdn)
- FortiLink interface filtering
- Allowaccess classification into management services vs routing protocols
- Zone building priority 3 for unzoned interfaces with IPs
- Policy field defaults documentation
- Central SNAT field name variants (`natippool`)
- Tokenizer documentation for quoted multi-value lines
- VPN IPsec phase1/phase2 compound proposal parsing (`aes256-sha256`)

**PAN-OS (parsing-palo-configs):**
- Full PAN-OS application resolution with 4-step pipeline (service check → app-group check → custom app check → canonical lookup)
- `application-default` service decomposition guidance
- Set-format (`show config flat`) input support with auto-detection
- URL categories on security policies
- Application group vs service object resolution in policy application field
- `drop` → `deny` action mapping with warning
- Management interface construction from deviceconfig
- Subinterface zone backfill from parent
- Service and service-group description extraction

**SRX (parsing-srx-configs):**
- 33-entry JunOS predefined application mapping table (`junos-*` → canonical)
- Application-set vs application-group distinction with mixed-set splitting
- Improved format detection heuristic (stanza-name check vs line counting)
- 6 hierarchical-to-set normalization rules for impedance mismatches
- Zone-attached address book migration to global scope
- `ip-prefix`/`ipv6-prefix` keyword handling
- `reject` → `deny` action mapping fix (was incorrectly mapped to `reset-both`)
- Routing instances / VRF support
- `qualified-next-hop` (floating statics) and `discard` (null routes)
- Full IKE/IPsec object chain resolution
- NAT destination port matching and pool-based translations
- MNHA (multi-node HA) detection
- Unit-0 interface name normalization
- Cluster interface (reth/fab) exclusion

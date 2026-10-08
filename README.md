<!-- brand:header:start -->
<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/mechub-mark.svg">
    <img src="docs/assets/mechub-mark-light.svg" width="72" alt="mechub mark">
  </picture>
</p>

<h1 align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/fwskillsshare-wordmark.svg">
    <img src="docs/assets/fwskillsshare-wordmark-light.svg" width="390" alt="fwskillsshare">
  </picture>
</h1>

<p align="center"><strong>Firewall skills for network &amp; security engineers</strong><br>
<em>a mechub project — sovereign network-security automation</em></p>

<p align="center">
  <img alt="skills" src="https://img.shields.io/badge/skills-33-0D9488">
  <img alt="reviewed" src="https://img.shields.io/badge/reviewed-26%2F33-262B38">
  <img alt="license" src="https://img.shields.io/badge/license-MIT-262B38">
  <img alt="vendors" src="https://img.shields.io/badge/vendors-Cisco%20%C2%B7%20Fortinet%20%C2%B7%20Palo%20Alto%20%C2%B7%20Juniper%20%C2%B7%20HPE%20Aruba-262B38">
</p>
<!-- brand:header:end -->

Agent skills for the firewall work you actually do — parsing, auditing, converting, running Juniper SRX, and deploying Security Director On-Prem and ClearPass — not vibe configuring.

Firewall work is unforgiving. A confidently wrong `access-list` line, a Junos stanza that won't commit, a compliance claim you can't back up in an audit — these aren't cosmetic. Coding agents are astonishingly good at producing *plausible* firewall config and astonishingly bad at knowing when it's wrong.

These skills exist to close that gap. They pin the agent to vendor syntax that's been checked against real devices, to one shared schema so four vendors speak the same language, and to control-to-evidence maps that don't overpromise. They're small, self-contained, and composable — copy the two you need or all 33. Hack around with them. Make them your own.

<!-- brand:disclaimer:start -->
> **Unofficial / community project.** Not affiliated with, endorsed by, or supported by Cisco, Fortinet, Palo Alto Networks, Juniper Networks, or HPE. See [License and Provenance](#license-and-provenance) for the full notice and the trademark disclaimer.
<!-- brand:disclaimer:end -->

## Contents

- [Before You Install](#before-you-install)
- [Quickstart (30-second setup)](#quickstart-30-second-setup)
- [Why These Skills Exist](#why-these-skills-exist)
- [Reference](#reference) — the skill catalog, by family; per-skill detail in [SKILLS.md](./SKILLS.md)
- [Quality and Review](#quality-and-review) — summary; full history in [QUALITY.md](./QUALITY.md)
- [Installation](#installation)
- [Usage](#usage)
- [Tips](#tips)
- [Conversion Caveats](#conversion-caveats)
- [Intermediate Schema](#intermediate-schema)
- [Uninstall](#uninstall)
- [License and Provenance](#license-and-provenance)
- [Contributing](#contributing)

## Before You Install

These skills change how your agent behaves. Read this before you install.

**A skill is instructions your agent will follow.** Every `SKILL.md` here is plain
markdown that gets loaded into your agent's context and acted on. Installing one —
from this repo or any other — means letting someone else's text steer a tool that
can read your configs and, if you permit it, reach your devices. **Read the whole skill
directory before you install it — not just `SKILL.md`.** Most of a skill is markdown
you can read straight through, but the two Proxmox deployment skills also ship Python
helpers under `scripts/` that the instructions tell the agent to run, and every skill
carries an `agents/openai.yaml`. Nothing is obfuscated or generated at runtime, but
"read the skill" has to mean the directory, not one file. Some skills also direct the
agent at your own equipment — the deployment and operational ones run commands
against your devices, which is the point of them, and the reason to know what you
installed.

**Treat every config you paste as untrusted input.** The parsing and audit skills
ingest whatever you hand them, and a config file can carry text written to redirect
the agent — in a comment, a description field, an object name. That is prompt
injection, and nothing in this repository defends against it. Read what comes back:
if the agent proposes something you did not ask for, or reaches for a device when
you asked for a parse, stop.

These skills default to parse / read / analyze / plan / dry-run, and anything that
changes a device — configuration, commits, upgrades, reboots, failovers — is written
to require explicit approval and post-change verification. That is authoring intent,
not a sandbox. What actually constrains the agent is the permissions you give it.

**Do not paste secrets you would not send to your model provider.** Firewall configs
carry pre-shared keys, SNMP communities, RADIUS secrets, certificate material, and
password hashes. Pasting a config into a hosted assistant discloses it to whoever
runs that model. That may be perfectly fine — but make it a decision you took, not
one you backed into. If the policy you are working on should not leave your control,
you have two options:

- **Sanitize first, carefully.** An anonymizer can rewrite addresses, hostnames and
  secrets, but it has to preserve address *semantics* — a consistent, containment-
  preserving mapping. The audits reason about real relationships: shadowed and
  overlapping rules, supernets, `0.0.0.0/0`, host versus subnet. An anonymizer that
  changes prefix lengths or breaks containment will hand you a clean-looking report
  about a policy you do not have. Read the output before you paste it, too: no
  anonymizer knows which of your zone, object, or policy names are themselves
  sensitive.
- **Or keep it on your own equipment.** These skills are plain markdown with no
  runtime dependency on any particular provider, so they work with a model you host
  yourself. Nothing here needs a hosted assistant to function.

**Install only the skills you need.** A skill's body loads only when the skill is
invoked, so what an installed-but-unused skill costs you is its description sitting
in the discovery surface. How much that costs depends on the runtime and version —
Codex 0.147.0 routes discovery through a dynamic selector and treats a flat
concatenated list as a fallback, truncating metadata to fit its budget rather than
failing — so the direct token cost is modest and not worth optimizing: all 33
descriptions together are on the order of ten thousand characters, and
`scripts/check-skill-packages.py` reports the current figure rather than this page
pinning a number that goes stale. The cost that matters is **selection**: the more
overlapping descriptions compete, the likelier your agent reaches for a near-miss
instead of the right skill, and truncation degrades that quietly rather than
visibly. Install the families you actually use.

**Skills are copied, not linked.** The installer copies files into your skills
directory, so they do not change when this repository does. Re-run the installer to
pick up updates — approving the overwrite when prompted, or passing `--force`, since
a non-interactive run (`-y`) skips a skill that is already installed and would
otherwise leave you on a stale copy.

**Verify against your own platform and release.** Behavior here is reported as
observed on specific versions. Commit-check on your release before trusting a stanza
in production.

## Quickstart (30-second setup)

1. Clone a tagged release and run the installer:

```bash
git clone --branch v1.11.0 --depth 1 https://github.com/mechubsec/fwskillsshare.git
cd fwskillsshare
./install.sh
```

`install.sh` verifies every skill file against `skills/CHECKSUMS.sha256` before
installing anything, and refuses to run against a branch or `HEAD` — only a
release tag (`vX.Y.Z`). Piping the script straight from `curl` into `bash` is
not offered: that pattern runs whatever `main` currently contains, with no
checksum possible before execution.

2. Choose your skills (space/numbers to toggle, `a` for all) and where to install them — **Claude Code** (`~/.claude/skills/`), **Codex** (`~/.agents/skills/`), **Hermes**, or all three.

3. Restart the selected agent only if it does not detect the new skills automatically.

4. Done. Paste a config or name a vendor and the right skill loads itself.

Prefer flags, or installing from a clone? See [Installation](#installation).

## Why These Skills Exist

I built these to fix the failure modes I kept hitting when I let Claude Code, Codex, and other agents touch firewalls.

### #1: The Agent Invents CLI That Won't Commit

> "It Has To Work."
>
> Ross Callon, [RFC 1925 — The Twelve Networking Truths](https://www.rfc-editor.org/rfc/rfc1925), truth (1)

**The Problem.** Ask an agent for an SRX ADVPN config or a Junos 24.4R1 IKE gateway and you'll get something that *reads* perfectly and then throws a commit error — or worse, commits and silently doesn't forward. The model has seen a decade of blog posts, including the wrong ones and the ones for the wrong release.

**The Fix** is playbooks pinned to syntax that's been proven on real hardware. The SRX skills carry the gotchas that only show up in production: the Junos 24.4R1+ `IKEv2 with authentication-method pre-shared-key is not allowed` commit error, the `Remote-ip 0.0.0.0/0 in traffic-selector is not supported` split, the ADVPN `No public key found` IKE_AUTH failure root-caused to the dynamic cert-gateway responder path. Disputed syntax was settled by commit-checking on a live vSRX 24.4R1, not by vibes.

Reach for [`srx-policy`](./skills/srx-policy/), [`srx-nat`](./skills/srx-nat/), [`srx-mnha`](./skills/srx-mnha/), [`srx-advpn`](./skills/srx-advpn/) and friends whenever you're designing or debugging real Junos.

### #2: Every Vendor Speaks A Different Dialect

> "All problems in computer science can be solved by another level of indirection."
>
> David Wheeler

**The Problem.** A Cisco ACL, a FortiGate policy block, a PAN-OS `<entry>`, and an SRX `set security` line all express the same idea four incompatible ways. Ask an agent to compare or convert them and it hand-waves the parts that don't line up.

**The Fix** is a shared language. The [`parsing-*`](./skills/) skills normalize every vendor into **one vendor-neutral intermediate JSON schema** — zones, objects, policies, NAT, routing, VPN, HA, the lot — with a 240+ entry canonical L7 application map and confidence scores. Once a config is in the schema, cross-vendor [audit](./skills/firewall-best-practices-audit/), [conversion](./skills/firewall-config-conversion/), and [diff](./skills/firewall-config-diff/) all operate by *meaning*, not text. Features with no equivalent are flagged, never silently dropped.

This is the piece that makes the rest composable. See the [Intermediate Schema](#intermediate-schema) below.

### #3: "Is It Compliant?" Gets A Confident, Unfounded Yes

> "Trust, but verify."
>
> Russian proverb

**The Problem.** Point an agent at a firewall and ask if it's "PCI compliant" and it will happily tell you yes. That answer is worthless to a QSA, and dangerous to you. A firewall *supports* evidence for a control; it is never itself "certified."

**The Fix** is seven compliance and STIG playbooks ([PCI](./skills/pci-ngfw-compliance/), [HIPAA](./skills/hipaa-ngfw-compliance/), [CMMC / NIST 800-171](./skills/cmmc-nist-800-171-ngfw-compliance/), [CIS](./skills/cis-controls-ngfw-compliance/), [ISO 27001](./skills/iso27001-ngfw-compliance/), [SOC 2](./skills/soc2-ngfw-compliance/), and [SRX DISA STIG](./skills/srx-disa-stig-compliance/)) that map firewall capabilities to specific control evidence, produce assessor-ready findings and gap lists, and are explicit at every turn that compliance is assessed for the *environment and program*, not conferred by the box. They tell you what evidence to collect and where the gaps are — the honest version of the answer.

### #4: Rulebases Rot, And Agents Accelerate The Rot

> "Complexity is the worst enemy of security."
>
> Bruce Schneier

**The Problem.** Every rulebase drifts toward `any-any`, shadowed rules, orphaned objects, and plaintext management. Agents make firewall changes faster, which means they make the rot faster too, unless something keeps them honest.

**The Fix** is [`firewall-best-practices-audit`](./skills/firewall-best-practices-audit/) — overly permissive and shadowed/redundant rules, missing deny-all and logging, exposed telnet/http/SNMPv1-2c, weak IKE/IPsec crypto, device-plane hardening, unused objects — and [`firewall-config-diff`](./skills/firewall-config-diff/) for drift and HA-pair parity. Prioritized findings with severity and confidence, vendor-neutral plus source-vendor remediation. Run them before you ship a change, not after the incident.

### Summary

Firewall fundamentals don't get easier in the AI age — the blast radius just gets bigger. These skills are my attempt to hand the agent the discipline: verified syntax, a shared schema, honest compliance mapping, and a hygiene checklist. Use them, break them, and make them yours.

## Reference

**33 skills** across five families. All of them are **model-invoked** — the agent reaches for them automatically when it sees vendor keywords, an SRX operational topic, a Security Director On-Prem or ClearPass deployment request, or compliance language in your message or a pasted config. 26 of the 33 packages have completed the review record below; `clearpass-proxmox-deploy`, `csrx-proxmox-deploy`, `srx-ips`, `srx-mnha-builder`, and `srx-cluster-to-mnha` ship as drafts, while `parsing-firepower-configs` and `srx-syslog-logging` have not yet been through the two-stage review. Invoke one explicitly as `/srx-nat` in Claude Code or Hermes, or `$srx-nat` in Codex.

Extended notes on the compliance and SRX playbooks — what they cover and when to reach for one — are in **[SKILLS.md](./SKILLS.md)**. Every skill also documents itself in its own `SKILL.md`, linked above.

### Config parsers

Normalize a vendor config into the shared intermediate schema. Everything else composes on top.

- **[parsing-cisco-configs](./skills/parsing-cisco-configs/SKILL.md)** — Cisco ASA & FTD (`show running-config`): access-lists, object/object-group, NAT, failover, port-to-app inference.
- **[parsing-firepower-configs](./skills/parsing-firepower-configs/SKILL.md)** — Cisco Secure Firewall / Firepower (FMC & FDM JSON exports): access control policies, security zones, prefilter, intrusion & file policies, FTD NAT.
- **[parsing-fortinet-configs](./skills/parsing-fortinet-configs/SKILL.md)** — FortiGate / FortiOS (`show full-configuration`): the config/edit/set block format, VDOMs, UTM profiles, compound IPsec proposals.
- **[parsing-palo-configs](./skills/parsing-palo-configs/SKILL.md)** — Palo Alto PAN-OS & Panorama: XML *or* flat set-format, vsys, app-default decomposition, device-groups.
- **[parsing-srx-configs](./skills/parsing-srx-configs/SKILL.md)** — Juniper SRX / Junos: `display set` or curly-brace, address-book migration to global, `junos-*` app mapping, routing-instances.

### SRX operational playbooks

Actionable Junos playbooks — commands, design guidance, verification, troubleshooting matrices, source attribution.

- **[srx-policy](./skills/srx-policy/SKILL.md)** — *(v1.3.0)* Enforced global-policy output with explicit zone-pair opt-outs on 23.x+, now including Branch SRX300/SRX400 after hardware validation, AppID/AppFW, NGWF-first web filtering, SecIntel, ATP, hit-count troubleshooting.
- **[srx-nat](./skills/srx-nat/SKILL.md)** — Source/destination/static NAT, NAT64/DNS64, CGN/PBA, persistent NAT, hairpin, proxy-ARP, session verification.
- **[srx-ips](./skills/srx-ips/SKILL.md)** — *(v0.1.1, draft)* IPS detection triage and custom signature authoring through a Junos MCP server: build the active rule table, read logs safely, monitor-to-enforce escalation behind an approval gate, and custom signature design with read-only coverage checks, context/direction/binding choice, false-positive-aware patterns, `commit check` validation, and monitor-mode proof before enforcement.
- **[srx-mnha](./skills/srx-mnha/SKILL.md)** — Multi-Node High Availability: routed/default-gateway/hybrid modes, SRGs, ICL/ICD, eBGP/BFD failover, VIPs, DHCP caveats.
- **[srx-mnha-builder](./skills/srx-mnha-builder/SKILL.md)** — *(v0.1.0, draft)* Build a new two-node MNHA pair end-to-end through a Junos MCP server (Juniper junos-mcp-server or rust-junosmcp): routing, switching, or hybrid mode selection, dedicated or shared and optionally encrypted ICL, one pair sheet used to write per-node staged configs from a stage reference and checked against a pre-push checklist, with pre-computed undo files, device dry runs, per-stage approval gates, the user-performed HA-activation reboot, formation checks, eBGP signal-route export, and a role-consistency failover test. Works with either MCP server.
- **[srx-cluster-to-mnha](./skills/srx-cluster-to-mnha/SKILL.md)** — *(v0.1.0, draft)* Convert an existing SRX or vSRX chassis-cluster configuration into two node-local MNHA configs through an SRX-architect interview: cluster inventory, per-segment mode choice, SRG and ICL design, a fidelity report, and a cutover runbook. Offline only.
- **[srx-advpn](./skills/srx-advpn/SKILL.md)** — Auto Discovery VPN dynamic spoke-to-spoke shortcuts, suggester/partner roles, multipoint st0, OSPF p2mp, the cert-auth requirement and the `No public key found` fix.
- **[srx-autovpn-full-tunnel](./skills/srx-autovpn-full-tunnel/SKILL.md)** — AutoVPN hub-and-spoke full-tunnel backhaul: dynamic `group-ike-id`, traffic selectors + ARI, shared st0.0, anti-recursion route.
- **[srx-ipsec-hub-spoke](./skills/srx-ipsec-hub-spoke/SKILL.md)** — Static point-to-point route-based IPsec hub-and-spoke, one explicit tunnel per spoke, hub source-NAT egress, spoke-to-spoke hairpin.
- **[srx-chassis-cluster-proxmox](./skills/srx-chassis-cluster-proxmox/SKILL.md)** — Chassis cluster whose nodes are Proxmox VE guests: control/fabric bridge and VLAN design, the fabric-jumbo vs control-1500 MTU split, virtual NIC to Junos interface mapping, the reth virtual-MAC anti-spoof trap, cluster bootstrap and validation.
- **[srx-mpls-in-flow](./skills/srx-mpls-in-flow/SKILL.md)** — MPLS L3VPN in flow mode (secure PE/CPE): decoupled `family mpls` packet-based with inet/inet6 flow-mode, VRF-aware policy/NAT/AppID.
- **[srx-dynamic-ip-feed](./skills/srx-dynamic-ip-feed/SKILL.md)** — Dynamic IP objects from HTTPS feed servers: `.tgz` bundles, cert validation, basic-auth / mTLS, `ipfd` log interpretation.
- **[srx-license-signature-maintenance](./skills/srx-license-signature-maintenance/SKILL.md)** — AppID and IDP/IPS entitlement audit, license installation, and offline signature updates behind two independent approval gates, with secret-safe license handling, per-node chassis-cluster verification, pilot-then-batch rollout, and condition-based polling.
- **[srx-initial-setup](./skills/srx-initial-setup/SKILL.md)** — *(v1.4.0)* First-time SRX bring-up: read-only entry-state assessment, Branch factory-default handling, management plane, interfaces and zones, starter screens, a minimal baseline policy, and an entitlement readout that routes onward. Every device write runs under a per-stage gate and confirmed commit.
- **[srx-syslog-logging](./skills/srx-syslog-logging/SKILL.md)** — *(v1.1.0, live-validated 2026-09-12; independent review still open)* External syslog and SIEM delivery: the Routing Engine vs PFE logging split, choosing a source interface per log type, the `fxp0` and `mgmt_junos` rules, Security Director Cloud onboarding, and why a non-default syslog port can be discarded silently.

### Cross-vendor tooling

Vendor-neutral, driven off the parsed schema.

- **[firewall-best-practices-audit](./skills/firewall-best-practices-audit/SKILL.md)** — Rulebase hygiene independent of any framework: any-any, shadowed/orphaned rules, missing deny/logging, exposed plaintext services, weak crypto, device-plane hardening.
- **[firewall-config-conversion](./skills/firewall-config-conversion/SKILL.md)** — Migrate between Cisco/FortiGate/Palo/SRX with a per-section fidelity report (converted / caveats / manual). A reviewed draft, never production-ready.
- **[firewall-config-diff](./skills/firewall-config-diff/SKILL.md)** — Compare two configs by meaning (order- and name-insensitive) — same-vendor drift & HA parity, or cross-vendor migration validation.

### NGFW compliance playbooks

Map firewall capability to control evidence — assessor/auditor output templates, description/tag markers, honest scoping.

- **[pci-ngfw-compliance](./skills/pci-ngfw-compliance/SKILL.md)** — PCI DSS v4.0.1: CDE segmentation, Requirement 1 network security controls, six-month rule review, QSA/ROC/SAQ evidence.
- **[hipaa-ngfw-compliance](./skills/hipaa-ngfw-compliance/SKILL.md)** — HIPAA Security Rule (45 CFR 164.312): ePHI segmentation, access/audit controls, transmission security, BAA considerations.
- **[cmmc-nist-800-171-ngfw-compliance](./skills/cmmc-nist-800-171-ngfw-compliance/SKILL.md)** — CMMC Level 2 / NIST SP 800-171: CUI enclave scoping, boundary protection, SSP boundary language, POA&M-style gaps.
- **[cis-controls-ngfw-compliance](./skills/cis-controls-ngfw-compliance/SKILL.md)** — CIS Controls v8/v8.1: secure configuration, network infrastructure management, IG1/IG2/IG3 safeguards, audit evidence.
- **[iso27001-ngfw-compliance](./skills/iso27001-ngfw-compliance/SKILL.md)** — ISO/IEC 27001:2022 ISMS & Annex A (A.8.20–A.8.23), Statement of Applicability support, supplier access, corrective actions.
- **[soc2-ngfw-compliance](./skills/soc2-ngfw-compliance/SKILL.md)** — SOC 2 Trust Services Criteria (CC6/CC7/CC8), Type I/II examinations, operating-effectiveness samples.
- **[srx-disa-stig-compliance](./skills/srx-disa-stig-compliance/SKILL.md)** — Source-pinned DISA Y25M01 SRX NDM/ALG/IDPS/VPN rule assessment, CAT status, evidence gaps, and Junos compatibility review.

### Security management and NAC deployment

Install with `--family deployment`.

- **[clearpass-proxmox-deploy](./skills/clearpass-proxmox-deploy/SKILL.md)** — *(v0.2.0, draft)* Deploy, validate, and bring into service HPE Aruba ClearPass Policy Manager 6.14 as a Proxmox VE KVM guest, including CLABV/C1000V/C2000V/C3000V sizing, the mandatory UEFI firmware and pre-boot second disk, MAC-ordered management interface mapping, CRC-verified streaming of the 45 GiB raw image, driving the VGA-only first-boot wizard through the QEMU monitor, and day-2 operations — license order and artifact formats, HTTPS certificate import via the Trust List, and the REST API's retrievable-token/unretrievable-secret split.
- **[sd-onprem-proxmox-deploy](./skills/sd-onprem-proxmox-deploy/SKILL.md)** — Plan, deploy, validate, and troubleshoot Juniper Security Director On-Prem 25/26 as a Proxmox VE guest from the vendor KVM artifacts, including sizing, four-IP planning, first-boot seed configuration, NTP/DNS reachability, SRX onboarding behind a device-clock NTP sync gate, and mandatory source-identical routing, bundle, device-channel, and TLS log-path proof before VM creation.
- **[csrx-proxmox-deploy](./skills/csrx-proxmox-deploy/SKILL.md)** — *(v0.1.0, draft)* Deploy a Juniper cSRX container firewall as a Docker workload on a Proxmox VE KVM guest in secure-wire and routing forwarding modes, including the mandatory host-CPU-passthrough and macvlan-passthru gates, checksum-offload and syslog traps, the CSRX_* environment-variable surface and how to re-derive it per release, cSRX-vs-vSRX CLI gaps, the observed secure-wire/routing performance envelope, and an unverified cRPD integration finding.

---

## Quality and Review

**26 of the 33 skills** have passed independent technical review. The exceptions
are `clearpass-proxmox-deploy`, `csrx-proxmox-deploy`, `srx-ips`, `srx-mnha-builder`, and `srx-cluster-to-mnha`, which ship as drafts,
while `parsing-firepower-configs` and `srx-syslog-logging` have not yet been through
the two-stage review. Four review rounds, the
live-device validation runs, what those runs falsified, and the per-family table
are recorded in **[QUALITY.md](./QUALITY.md)**.

These are research/operational and assessment-support skills, not certified products: review their output against current vendor documentation, live device behavior, and (for compliance work) a qualified assessor before relying on it.

## Installation

### Installer (recommended)

Clone a tagged release and run [`install.sh`](./install.sh) — interactively, or
with flags for scripted/non-interactive use. The installer only accepts a
release tag (`vX.Y.Z`), never a branch or `HEAD`, and verifies every skill file
against `skills/CHECKSUMS.sha256` before installing anything:

```bash
git clone --branch v1.11.0 --depth 1 https://github.com/mechubsec/fwskillsshare.git
cd fwskillsshare

# Interactive: pick skills + target
./install.sh
```

Flags:

```text
--all                 Select all 33 skills
--skill NAME          Select a specific skill by name (repeatable)
--family NAME         Select a whole family: parsers | srx | tooling | compliance | deployment (repeatable)
--target WHERE        claude | codex | hermes | both | all
                      ('both' means Claude+Hermes; default: interactive prompt, or claude with -y)
--dir PATH            Explicit install directory (overrides --target)
--ref TAG             Release tag to install from when downloading skills without a local clone
                      (default: the tag pinned in install.sh). Must be vX.Y.Z; branches and HEAD are refused.
--list                Print the skill inventory (grouped by family) and exit
--uninstall           Remove the selected skills from the selected target(s) instead of installing
--force               Overwrite existing skill directories without prompting
-y, --yes             Non-interactive; assume defaults, no prompts
-h, --help            Show help and exit
```

Examples:

```bash
./install.sh --all --target claude              # everything, into ~/.claude/skills
./install.sh --all --target codex               # everything, into ~/.agents/skills
./install.sh --family parsers --family srx      # just the parsers + SRX playbooks
./install.sh --family tooling --target all      # tooling skills into all three agents
./install.sh --family deployment --target codex # Security Director On-Prem and ClearPass deployment skills
./install.sh --skill sd-onprem-proxmox-deploy --target claude -y
./install.sh --skill parsing-srx-configs --skill srx-nat -y
./install.sh --list                             # see what's available
```

### Manual install

The skills are plain directories — copy the ones you want. Pin a release tag
rather than the default branch so you know exactly what you're copying:

```bash
git clone --branch v1.11.0 --depth 1 git@github.com:mechubsec/fwskillsshare.git

# All of them
cp -r fwskillsshare/skills/* ~/.claude/skills/

# Or a single skill
cp -r fwskillsshare/skills/srx-mnha ~/.claude/skills/

# Security Director On-Prem deployment skill
cp -r fwskillsshare/skills/sd-onprem-proxmox-deploy ~/.claude/skills/
```

For **Codex**, copy into the user skill tree. Codex normally detects changes automatically; restart it if a new skill does not appear:

```bash
mkdir -p ~/.agents/skills
cp -r fwskillsshare/skills/* ~/.agents/skills/
```

For **Hermes**, copy into your local Hermes skills tree (usually `~/.hermes/skills/devops/`) and confirm with `hermes skills list`:

```bash
mkdir -p ~/.hermes/skills/devops
cp -r fwskillsshare/skills/* ~/.hermes/skills/devops/
hermes skills list | grep -E 'parsing-|srx-|firewall-|-ngfw-compliance|sd-onprem-'
```

Skills auto-trigger when they detect vendor-specific keywords, SRX operational topics, Security Director On-Prem or Proxmox deployment requests, or PCI/HIPAA/CMMC/NIST 800-171/CIS/ISO 27001/SOC 2/DISA STIG compliance language in your messages or pasted configs.

### Managing context

Skill *bodies* only load when a skill is invoked, but each skill's short description stays in context so the agent knows when to reach for it. If you rarely use certain skills (e.g. compliance frameworks you don't work with), you can drop just their descriptions from context while keeping them invocable, via `skillOverrides` in `~/.claude/settings.json`:

```json
{ "skillOverrides": { "soc2-ngfw-compliance": "name-only" } }
```

`"name-only"` keeps the skill listed and invocable but hides its description; `"user-invocable-only"` hides it from the model entirely (slash-command only); `"off"` hides it completely.

For **Codex**, disable an installed skill without deleting it by adding its `SKILL.md` path to `~/.codex/config.toml`:

```toml
[[skills.config]]
path = "/home/you/.agents/skills/soc2-ngfw-compliance/SKILL.md"
enabled = false
```

## Usage

### What you can do

- **Parse** — Extract all objects, policies, NAT rules, and routes into structured JSON
- **Audit** — Find unused objects, shadowed rules, overly permissive policies, missing logging
- **Convert** — Transform configs between vendors (e.g., SRX to PAN-OS)
- **Compare** — Diff two configs by meaning, not text
- **Summarize** — Get a high-level overview of zones, policy counts, and security profiles
- **Operate SRX dynamic feeds** — Configure, validate, and troubleshoot SRX dynamic-address feed servers
- **Design SRX MPLS in flow mode** — Keep inet/inet6 in stateful flow mode for policy, NAT, and AppID while `family mpls` is packet-based
- **Design SRX MNHA** — Reason about MNHA modes, SRGs, ICL/ICD, eBGP/BFD failover, VIPs, and DHCP caveats
- **Operate SRX NAT** — Source/destination/static NAT, NAT64/DNS64, CGN/PBA, persistent NAT, hairpin, proxy ARP
- **Design SRX security policy** — Enforce `security policies global` for generated greenfield, migration, and onboarding output absent an explicit opt-out; then layer AppID/AppFW, NGWF-first web filtering, SecIntel, ATP
- **Deploy Security Director On-Prem** — Plan the Proxmox VE guest, vendor artifact extraction, four same-subnet IPs, first-boot settings, and SRX onboarding gated on proven device NTP sync
- **Assess compliance evidence** — Map NGFW policies, NAT, zones, logging, IDS/IPS, and segmentation to PCI / HIPAA / CMMC-NIST 800-171 / CIS / ISO 27001 / SOC 2 / SRX DISA STIG evidence expectations

### Examples

```
# Parse and audit
"Here's my ASA config, parse it and show me security issues:"
[paste running-config]

# Convert between vendors
"Convert this SRX config to Palo Alto format"
[paste SRX config]

# Read from a file instead of pasting
"Read /path/to/running-config.txt and audit it"

# SRX operational work (any of the SRX playbooks)
"Help me troubleshoot this SRX destination NAT rule: hits increment, but the policy denies the translated web server session"

# Compliance review (any of the seven compliance/STIG playbooks)
"Review this firewall export for PCI DSS CDE segmentation evidence and recommend policy/NAT/zone description markers"
```

Each skill's own `SKILL.md` carries worked examples for its own topic.

## Tips

- Paste the **full config** — partial configs may produce unresolved reference warnings
- Use the appropriate show command output for each vendor:
  - **Cisco ASA**: `show running-config`
  - **FortiGate**: `show full-configuration`
  - **PAN-OS**: XML config export or `show config flat` (set-format)
  - **SRX**: `show configuration | display set` or `show configuration`
  - **SRX dynamic feeds**: `show security dynamic-address summary`, `show security dynamic-address`, `show log messages | match ipfd`
  - **SRX MPLS in Flow**: `show security flow status`, `show route table bgp.l3vpn.0`, `show route table <vrf>.inet.0`, `show ldp neighbor`, `show mpls interface`, `show security flow session extensive`, `show security policies hit-count`
  - **SRX MNHA**: `show chassis high-availability information`, `show chassis high-availability services-redundancy-group <id>`, `show security flow session`, `show bgp summary`, `show bfd session`
  - **SRX NAT**: `show security nat source/destination/static rule all`, `show security nat source pool all`, `show security nat proxy-arp`, `show security flow session ... extensive`
  - **SRX security policy**: `show configuration security policies global | display set`, `show security policies hit-count`, `show security application-firewall rule-set <name>`, `show security utm web-filtering status/statistics`
  - **Compliance reviews**: collect the firewall policy/NAT/zone/VPN/object exports plus the framework-specific evidence (CDE/ePHI/CUI/ISMS-scope diagrams, rule-review records, logging/SIEM evidence, change tickets, segmentation/pen-test results) — each compliance skill lists exactly what it needs
- For large configs, save to a file and point Claude at the file path
- Each `parsing-*` skill includes `references/fixture-minimal-input.md` and `references/fixture-expected-output.json` as a smoke-test fixture for parser behavior and schema shape

## Conversion Caveats

- Application-level rules (Palo Alto apps, FortiGate app control) don't map 1:1 to port-based platforms (ASA)
- User-ID / FSSO source-user rules have no equivalent on most platforms
- Dynamic address groups (PAN-OS) have no static equivalent
- Geography/GeoIP objects have limited cross-platform support

## Intermediate Schema

The `parsing-*` skills normalize every vendor into one JSON document, which is what
lets audit, conversion, and diff operate by meaning rather than text. It covers zones and
interfaces; address, service, and application objects and their groups; security policies
with resolved apps, services, and profiles; NAT rules; routing (static routes, virtual
routers/VRFs, OSPF, BGP); HA, route-based IPsec tunnels, DHCP, admin users, and system
settings — plus `residual_raw` for anything left unparsed and `metadata` for source vendor,
version, and warnings.

The field-by-field definition is
[`skills/parsing-srx-configs/references/intermediate-schema.md`](./skills/parsing-srx-configs/references/intermediate-schema.md).

### Shared schema maintenance

That file is intentionally duplicated in each `parsing-*` skill so every skill stays
self-contained when copied alone. Treat the `parsing-srx-configs` copy as the canonical
editing copy, sync the same content to the other parser skills, then run:

```bash
python3 scripts/check-shared-schema.py
```

See `skills/SHARED-SCHEMA.md` for the full policy.

## Uninstall

```bash
# Remove everything the installer put down from Claude Code and Hermes
./install.sh --uninstall --all --target both

# Remove everything from Claude Code, Codex, and Hermes
./install.sh --uninstall --all --target all

# Or remove a single skill
./install.sh --uninstall --skill srx-mnha --target codex
```

Manual equivalent — the skills are just directories, so remove the selected skill directory under `~/.claude/skills/`, `~/.agents/skills/`, or `~/.hermes/skills/devops/` for the corresponding agent.

## License and Provenance

Original skill, playbook, script, and documentation text in this repository is
licensed under the [MIT License](LICENSE).

Parser improvements adopted from the fatcat/converter JavaScript parsers in v1.1.0 are itemized in [CHANGELOG.md](./CHANGELOG.md).

Some references are independently written “Inspired by” notes that identify Juniper,
Cisco, Fortinet, Palo Alto Networks, community, blog, or support material which
informed the work. They are concise original summaries, not bundled page copies or
upstream configurations. Linked third-party material remains under its owners' terms
and is not relicensed by this repository.

<!-- brand:trademark:start -->
**Trademark / affiliation disclaimer.** This repository is an independent, community-driven project. It is not affiliated with, endorsed by, sponsored by, or supported by Hewlett Packard Enterprise, Cisco, Palo Alto Networks, Fortinet, or Juniper Networks. "HPE", "Juniper", "Cisco", "Fortinet", "Palo Alto Networks", and "Juniper SRX" are trademarks of their respective owners and are used here only to describe what this software interoperates with. Please direct support and licensing questions about those products to the respective vendors.
<!-- brand:trademark:end -->

## Contributing

Unless you explicitly state otherwise, contributions intentionally submitted for
inclusion in this repository are licensed under the MIT License.

See [CONTRIBUTORS.md](CONTRIBUTORS.md) for the list of maintainers and contributors.

---

<!-- brand:footer:start -->
<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/mechub-mark.svg">
    <img src="docs/assets/mechub-mark-light.svg" width="28" alt="">
  </picture><br>
  <sub><code>a mechub project</code> · deterministic decides · the model explains · a human approves<br>
  <a href="https://github.com/fastrevmd-lab">github.com/fastrevmd-lab</a></sub>
</p>
<!-- brand:footer:end -->

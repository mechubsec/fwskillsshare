# Installation and usage

[Back to the README](../README.md)

## Contents

- [Installation](#installation) — installer, manual install, managing context
- [Installing with Claude Code or Codex](#installing-with-claude-code-or-codex)
- [Usage](#usage)

## Installation

### Installer (recommended)

Clone a tagged release and run [`install.sh`](../install.sh) — interactively, or
with flags for scripted/non-interactive use. The installer only accepts a
release tag (`vX.Y.Z`), never a branch or `HEAD`, and verifies every skill file
against `skills/CHECKSUMS.sha256` before installing anything:

```bash
git clone --branch v1.12.0 --depth 1 https://github.com/mechubsec/fwskillsshare.git
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
git clone --branch v1.12.0 --depth 1 git@github.com:mechubsec/fwskillsshare.git

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

## Installing with Claude Code or Codex

When an agent runs the installer for you, have it ask before it installs anything. Ask it to use its interactive question tool — Claude Code's `AskUserQuestion`, Codex's `request_user_input` — to confirm, in order:

1. the target (`claude`, `codex`, or `hermes`),
2. the families (`parsers`, `srx`, `tooling`, `compliance`, `deployment`),
3. the individual skills within them.

Only then should it run `./install.sh --skill <name> ...` (repeatable) or `./install.sh --family <name>` with the matching `--target`. That way you control exactly which skills are installed. The agent should never fall back to `--all` unless you choose that.

Example prompt to paste:

```text
Install fwskillsshare from the v1.12.0 release clone in this directory.
Before running ./install.sh, use your interactive question tool
(AskUserQuestion in Claude Code, request_user_input in Codex) to ask me:
first the target (claude, codex, or hermes), then which families, then which
individual skills. Run only ./install.sh --skill <name> ... or --family <name>
with my answers and --target. Do not use --all unless I pick it. Show me the
exact command before you run it.
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

Skills at v0.x.x are drafts. If you verified one, see [Skill versions and drafts](../CONTRIBUTING.md#skill-versions-and-drafts) and open an issue.

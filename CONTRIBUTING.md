# Contributing to fwskillsshare

Thanks for considering a contribution. fwskillsshare is a collection of **agent skills** for firewall and network-security work — Juniper SRX design, NAT, VPN, and MNHA playbooks; Security Director On-Prem and ClearPass deployment; cross-vendor parse/audit/convert/diff; and PCI/HIPAA/CMMC/CIS/ISO/SOC 2/DISA STIG evidence mapping — part of the [mechub](https://github.com/mechubsec) family of open-source, self-hosted network-security tooling.

This is a Markdown-first repository, not a conventional software package. A "contribution" here is almost always a new or updated `SKILL.md` (and its supporting references/fixtures), not application code. See [README.md](README.md) for what the skills do and [QUALITY.md](QUALITY.md) for how they've been reviewed so far.

## What a skill is, and what it is not

**These skills are drafting and informational aids for a human operator, not autonomous device-control code.** A skill's job is to make an agent (Claude Code, Codex, Hermes) explain options, propose commands, and draft configuration well — never to decide and act on its own. Concretely:

- Skill examples default to **parse / read / analyze / plan / dry-run** behavior.
- Anything that changes a device — a `commit`, a `set`, an upgrade, a reboot, a delete, a failover — must be written to require **explicit human approval**, and should include dry-run/diff, rollback consideration, and post-change verification steps.
- Deterministic checks (the `scripts/check-*.py` validators, the runtime-intake gates a skill's own body describes) decide what's safe to proceed with; a model may draft, summarize, or explain, but a human approves before anything touches a real device. Nothing you contribute should collapse that boundary.

If you're unsure whether a change you're proposing crosses this line, say so in the PR description rather than guessing.

## Before you start

- Check open issues and PRs first — someone may already be working on it.
- For a new skill or a substantial rework of an existing one, open an issue first to discuss scope, vendor/version coverage, and evidence sources. It saves a rewrite later.
- Read [`AGENTS.md`](AGENTS.md) and [`skills/AGENTS.md`](skills/AGENTS.md) — they carry the authoring rules this file summarizes, plus notes specific to this repo's tooling (Codex description limits, the shared parser schema, the review-gate wrapper) that are easy to miss.

## How a skill is structured

Each skill lives at `skills/<name>/` as a self-contained directory (skills are commonly copied out individually into `~/.claude/skills/`, `~/.agents/skills/`, or `~/.hermes/skills/devops/`, so nothing outside its own directory tree should be load-bearing):

```
skills/<name>/
  SKILL.md              # required: frontmatter + body
  agents/openai.yaml     # required: Codex UI metadata
  references/            # optional: longer material loaded on demand
  fixtures/, assets/     # optional: data fixtures only (no scripts/executables)
```

**Skills are Markdown only** — no scripts or executables inside a skill package. See [AGENTS.md](AGENTS.md#skills-are-markdown-not-programs) for the rule and grandfathered exceptions.

### `SKILL.md` frontmatter

```yaml
---
name: srx-nat
description: Design, configure, audit, and troubleshoot Juniper SRX NAT. Use when handling source, destination, static, NAT64, ...
version: 1.1.2
author:
  - fastrevmd-lab
  - Claude
  - GPT
license: MIT
metadata:
  hermes:
    tags: [srx, junos, nat, ...]
    related_skills: [parsing-srx-configs, srx-policy, ...]
  sources:
    - title: ...
      author: ...
      url: ...
      retrieved: "YYYY-MM-DD"
---
```

Rules enforced by `scripts/check-skill-packages.py`:

- `name` is hyphen-case (`[a-z0-9]+(-[a-z0-9]+)*`), at most 64 characters, and matches the directory name.
- `description` is required, at most **1,024 characters** (Codex's hard per-skill limit — see `AGENTS.md` for the version this was verified against), contains no angle brackets, and must include the literal phrase `. Use when ` followed by the trigger conditions. Discovery is largely lexical, so the `Use when ...` clause is what gets matched on — don't trim it to save space.
- `version` and `metadata` are required (Hermes package metadata).
- `license` must be `MIT`.
- `author` must be exactly `[fastrevmd-lab, Claude, GPT]`, unless the skill has an entry in `CONTRIBUTING_AUTHORS` in `scripts/check-skill-packages.py` crediting an outside contributor by name — see the `srx-ips` entry for the pattern if you're adding a named credit. Contributors are listed in [CONTRIBUTORS.md](CONTRIBUTORS.md); add yourself there in your pull request.
- Every `references/...` path mentioned in the body must exist.
- The file must stay under 600 lines total; push longer material into `references/` and link to it (progressive disclosure) rather than inlining it.

### `agents/openai.yaml`

Every skill also needs Codex UI metadata: a quoted `display_name`, a quoted `short_description` (25–64 characters), and a quoted `default_prompt` that mentions `$<skill-name>`. This is Codex-specific presentation metadata — Claude Code and Hermes ignore it and use the portable `SKILL.md` content directly.

### Fixtures, examples, and secrets

- **No real device configs, hostnames, serial numbers, credentials, or customer data — ever, including in an example, a fixture, or a "here's the error I saw" quote.** Fixtures and command output must be synthetic. `.gitleaks.toml` and the pre-commit `gitleaks` hook exist to catch what a review might not; don't rely on them as your only check.
- If a skill needs a raw source note under `references/` (a `source-*.md` file), keep it short (under 200 lines) and free of scraped-page boilerplate — `scripts/check-skill-packages.py` rejects raw page dumps. Write a concise, attributed "Inspired by" summary instead of pasting a page.
- Cite vendor syntax and standards/control claims against a primary, current source (vendor docs, a live commit-check, a support article), and record what you verified and how (see `QUALITY.md` for the level of detail expected — commit-check output, live-device runs, release numbers). Don't overclaim device or compliance behavior you haven't verified; mark it `[unverified]` if you haven't.

### The shared parser schema

The five `parsing-*` skills intentionally carry byte-identical copies of the same intermediate schema at `skills/parsing-*/references/intermediate-schema.md`. If you change it, edit the `parsing-srx-configs` copy (the canonical one), copy the same content to the other four, and run:

```sh
python3 scripts/check-shared-schema.py
```

See [`skills/SHARED-SCHEMA.md`](skills/SHARED-SCHEMA.md) for why it's duplicated instead of linked.

### Adding or renaming a skill

A new skill needs an entry in `skills/inventory.json` (`name`, `family`, `reviewed: false` until it's been through review) and, if it introduces a new family, wiring into `install.sh`. Don't hand-edit `install.sh`'s per-family arrays independently — run:

```sh
python3 scripts/sync-installer-inventory.py --check   # verify install.sh matches inventory.json
python3 scripts/sync-installer-inventory.py            # regenerate the installer arrays from inventory.json
```

## Skill versions and drafts

Every change to a skill bumps its `SKILL.md` `version` (patch for fixes, minor for new capability) and its `*(vX.Y.Z)*` marker in the README catalog.

- **v0.x.x = draft.** Not yet validated.
- **v1.0.0 and later = validated at least once:** a lab run on real or virtual devices, or, for skills with no device to test, a completed two-stage review.

### Verified a draft skill? Please open an issue

Maintainers use these reports to promote drafts to v1.0.0. Open an issue with the **Draft skill verified** template and include:

- skill name and version
- platform/model, and the Junos (or vendor OS) release
- what you ran (the workflow or scenario)
- the outcome
- some evidence: redacted command output, a commit-check result, or screenshots. Never include credentials or customer data.

## Validating your change

This repository has no build step, but it does have real validators — run them before opening a PR:

```sh
just setup   # one-time: installs the pre-commit hooks
just lint    # skill packaging/frontmatter, inventory manifest, markdown links, README branding, runtime-intake catalogs
just test    # fixtures, shared-schema byte-identity, installer, and per-skill behavioral contracts
just guard   # lint + test + shellcheck (install.sh and scripts/*.sh)
```

`just lint` and `just test` simply run the scripts under `scripts/` directly — read a script's docstring if you want to know exactly what it checks before you fix something to satisfy it. `just security` runs Trivy's secret scanner (this repo has no dependency manifests, so the vuln/misconfig scanners have nothing to act on — see `QUALITY.md`). None of this contacts a real device: `just integration` is intentionally a documented no-op, and any live-device validation (like the runs recorded in `QUALITY.md`) is a separate, explicit, maintainer-approved activity, not something CI or a contributor script does automatically.

If you're updating an existing skill's operational claims (a new Junos release, a corrected command, a fixed troubleshooting step), the strongest evidence is the same kind already recorded in `QUALITY.md` — a `commit check` or live command output against the version you're changing behavior for. State in your PR what you verified and how; "should work" isn't verification.

## Commit and PR conventions

- Match the existing commit style: `type(scope): summary` (`feat(srx-nat):`, `docs(sd-onprem):`, `chore(srx-ips):`, etc.) — see `git log` for examples.
- Keep PRs focused on one skill or one change. A large, mixed-topic diff is also harder for the review gate described in `AGENTS.md` to get through cleanly.
- Fill out the PR template, including the exact `just` commands you ran and their results.
- Unless you state otherwise, a contribution you submit is licensed under this repository's [MIT license](LICENSE) — this repo does not use a Developer Certificate of Origin / `Signed-off-by` process; the licensing-by-contribution statement in [README.md](README.md#contributing) is the operative norm.

## Review process

Every pull request — from a first-time contributor or a maintainer — goes through a security review and a code review, then an independent test run, before a maintainer merges it. Only a maintainer merges; contributors, including anyone with write access, should not merge their own PR. The repository's own validators (`just guard`) must be green first, and the change should carry the same kind of vendor/standards evidence described above.

All contributions land as a pull request against `main` — there is no direct-push path to the default branch.

## Reporting a vulnerability or unsafe skill guidance

Please don't open a public issue for a security vulnerability or for a skill giving dangerously unsafe guidance — see [SECURITY.md](SECURITY.md) for how to report either one privately.

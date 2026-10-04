# Skill Evaluation Scenarios

This directory contains structured evaluation scenarios for each skill in the repository. Evals validate that skills trigger correctly, produce expected behavior, and enforce documented safety and approval rules.

## Purpose

Anthropic skill authoring best practice (superpowers writing-skills) requires testing each skill with fresh-agent scenarios. Each eval file contains 2–3 concrete scenarios derived from what the skill itself documents — its triggers, pitfalls, safety rules, and reference material.

Evals verify:
- Correct triggering on representative prompts
- Expected analysis and outputs
- Safety/approval boundaries (e.g., no commits without approval, no secrets surfaced)
- Handling of documented pitfalls and edge cases

## Format

Each eval file follows a fixed structure:

```markdown
# <skill-name> evals

Run each scenario in a fresh agent session with the skill installed, then again without it as a baseline. A scenario passes only when every "Must" holds and no "Must not" occurs.

## Scenario 1: <short title>

**Prompt:** <the exact user prompt, realistic>

**Input:** <inline small config/output snippet in a fenced block, OR "Fixture: skills/<skill>/references/<file>" if an existing fixture fits, OR "None">

**Must:**
- <observable, checkable behavior>

**Must not:**
- <observable failure, e.g. commits without approval, invents unsupported syntax>

## Scenario 2: ...
```

### Writing scenarios

- **Derive from the skill:** Every scenario and expectation must come from what the skill's SKILL.md and references say. Never invent vendor facts or unsupported features.
- **Include safety/approval exercises:** At least one scenario per skill should test a documented safety rule, approval requirement, or pitfall.
- **Keep inputs synthetic:** Use RFC 5737 (TEST-NET-1/2/3: 192.0.2.0/24, 198.51.100.0/24, 203.0.113.0/24) and RFC 1918 addresses. No secrets.
- **Reuse fixtures:** Parser skills should reference the existing `references/fixture-*` files rather than duplicating config snippets.

## Running evals

Evals are **manual tests**. Run each scenario:

1. Start a fresh agent session with the skill installed (via `install.sh` or `~/.agents/skills/` symlink)
2. Issue the exact prompt, providing the input as specified
3. Verify every "Must" condition holds and no "Must not" condition occurs
4. Run the same scenario without the skill as a baseline to confirm skill-specific behavior
5. Record results in a PR or review comment

Automated eval harnesses may be added later; for now, hand-run each one.

## Repository integration

- **Adding a skill requires adding its eval file.** `scripts/check-evals.py` enforces a 1:1 correspondence between `skills/<name>/SKILL.md` and `evals/<name>.md`.
- **Evals are never installed.** `install.sh` copies only `skills/` and `scripts/` excludes `evals/` — this is development and verification tooling, not distributed skill content.
- **Evals are validated at `just lint` and `just test` time.** The checker ensures every skill has an eval file, every file has the required structure (H1, >= 2 scenarios, Prompt/Input/Must/Must not per scenario), and no eval exists for a nonexistent skill.

## Coverage

Every skill under `skills/` must have a corresponding `evals/<name>.md` file. The validation script checks for 1:1 correspondence and structural completeness.

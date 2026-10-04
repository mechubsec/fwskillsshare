#!/usr/bin/env python3
"""Verify every skill has a corresponding eval file with required structure.

Each skills/<name>/SKILL.md must have an evals/<name>.md, and each eval must
contain:
- An H1 "# <name> evals"
- At least 2 "## Scenario N:" headings
- Each scenario must have **Prompt:**, **Input:**, **Must:**, and **Must not:**
  with at least one bullet under **Must:**

No eval file may exist for a nonexistent skill.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "skills"
EVALS_DIR = ROOT / "evals"

# Patterns for required sections
H1_RE = re.compile(r"^# (.+) evals$", re.MULTILINE)
SCENARIO_RE = re.compile(r"^## Scenario \d+:", re.MULTILINE)
PROMPT_RE = re.compile(r"^\*\*Prompt:\*\*", re.MULTILINE)
INPUT_RE = re.compile(r"^\*\*Input:\*\*", re.MULTILINE)
MUST_RE = re.compile(r"^\*\*Must:\*\*", re.MULTILINE)
MUST_NOT_RE = re.compile(r"^\*\*Must not:\*\*", re.MULTILINE)
BULLET_RE = re.compile(r"^- ", re.MULTILINE)


def get_skill_names() -> set[str]:
    """Return set of skill names from skills/ directory."""
    skills = set()
    for skill_dir in SKILLS_DIR.iterdir():
        if not skill_dir.is_dir():
            continue
        if (skill_dir / "SKILL.md").exists():
            skills.add(skill_dir.name)
    return skills


def get_eval_names() -> set[str]:
    """Return set of skill names from evals/ directory."""
    if not EVALS_DIR.exists():
        return set()
    evals = set()
    for eval_file in EVALS_DIR.glob("*.md"):
        if eval_file.name != "README.md":
            evals.add(eval_file.stem)
    return evals


def validate_eval_structure(eval_path: Path, skill_name: str) -> list[str]:
    """Validate eval file structure. Returns list of errors (empty if valid)."""
    errors = []
    content = eval_path.read_text(encoding="utf-8")

    # Check H1
    h1_match = H1_RE.search(content)
    if not h1_match:
        errors.append(f"  Missing H1 '# {skill_name} evals'")
    elif h1_match.group(1) != skill_name:
        errors.append(f"  H1 name '{h1_match.group(1)}' doesn't match file name '{skill_name}'")

    # Check scenarios (at least 2)
    scenarios = SCENARIO_RE.findall(content)
    if len(scenarios) < 2:
        errors.append(f"  Found {len(scenarios)} scenario(s), need at least 2")
        return errors  # Don't check scenario internals if scenarios are missing

    # Split content by scenarios to check each one
    scenario_splits = SCENARIO_RE.split(content)
    # First element is everything before first scenario
    scenario_bodies = scenario_splits[1:]

    for i, scenario_body in enumerate(scenario_bodies, 1):
        # Each scenario should have the required sections
        if not PROMPT_RE.search(scenario_body):
            errors.append(f"  Scenario {i}: Missing **Prompt:**")
        if not INPUT_RE.search(scenario_body):
            errors.append(f"  Scenario {i}: Missing **Input:**")
        if not MUST_RE.search(scenario_body):
            errors.append(f"  Scenario {i}: Missing **Must:**")
        else:
            # Check that Must: has at least one bullet
            must_pos = MUST_RE.search(scenario_body)
            if must_pos:
                # Look for bullets after **Must:** up to next section or end
                rest = scenario_body[must_pos.end():]
                next_section = re.search(r"^\*\*[A-Z]", rest, re.MULTILINE)
                must_section = rest[:next_section.start()] if next_section else rest
                if not BULLET_RE.search(must_section):
                    errors.append(f"  Scenario {i}: **Must:** has no bullets")
        if not MUST_NOT_RE.search(scenario_body):
            errors.append(f"  Scenario {i}: Missing **Must not:**")

    return errors


def main() -> int:
    """Check that every skill has an eval and every eval is well-formed."""
    skills = get_skill_names()
    evals = get_eval_names()

    # Check for missing evals
    missing_evals = skills - evals
    # Check for orphan evals
    orphan_evals = evals - skills

    errors = []

    if missing_evals:
        errors.append("ERROR: Skills missing eval files:")
        for skill in sorted(missing_evals):
            errors.append(f"  {skill}")

    if orphan_evals:
        errors.append("ERROR: Eval files for nonexistent skills:")
        for skill in sorted(orphan_evals):
            errors.append(f"  {skill}")

    # Validate structure of existing evals
    structure_errors = {}
    for skill in sorted(evals & skills):
        eval_path = EVALS_DIR / f"{skill}.md"
        validation_errors = validate_eval_structure(eval_path, skill)
        if validation_errors:
            structure_errors[skill] = validation_errors

    if structure_errors:
        errors.append("ERROR: Eval files with structural issues:")
        for skill, skill_errors in structure_errors.items():
            errors.append(f"{skill}:")
            errors.extend(skill_errors)

    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1

    print(f"OK: {len(skills)} skills, all have valid eval files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

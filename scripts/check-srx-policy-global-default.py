#!/usr/bin/env python3
"""Regress the srx-policy enforced global-policy output contract."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "srx-policy" / "SKILL.md"
EXAMPLE = ROOT / "skills" / "srx-policy" / "references" / "zone-pair-to-global-example.md"
README = ROOT / "README.md"
# The per-skill detail moved out of the README; the contract sentence moved with it.
CATALOG = ROOT / "SKILLS.md"


def require(pattern: str, text: str, label: str, errors: list[str]) -> None:
    if not re.search(pattern, text, re.IGNORECASE | re.DOTALL | re.MULTILINE):
        errors.append(label)


def main() -> int:
    errors: list[str] = []
    skill = SKILL.read_text(encoding="utf-8")

    require(
        r"^## Enforced Global-Policy Output Contract$",
        skill,
        "SKILL.md lacks an enforced global-policy output contract",
        errors,
    )
    require(
        r"MUST[^\n]+security policies global",
        skill,
        "SKILL.md does not require generated policy under security policies global",
        errors,
    )
    for opt_out in ("existing-estate compatibility", "isolated exception", "customer standard"):
        if opt_out not in skill.lower():
            errors.append(f"SKILL.md lacks explicit opt-out condition: {opt_out}")
    require(
        r"day-one[^\n]+onboarding.*detect.*set security policies from-zone",
        skill,
        "SKILL.md lacks day-one zone-pair detection",
        errors,
    )
    require(
        r"day-one[^\n]+onboarding.*rewrite.*security policies global",
        skill,
        "SKILL.md lacks day-one global-policy rewrite behavior",
        errors,
    )
    require(
        r"^## Pre-Return Self-Check$",
        skill,
        "SKILL.md lacks a pre-return self-check",
        errors,
    )
    require(
        r"set security policies from-zone.*must return no matches",
        skill,
        "SKILL.md does not reject unintended zone-pair output before return",
        errors,
    )
    if "references/zone-pair-to-global-example.md" not in skill:
        errors.append("SKILL.md does not directly reference the zone-pair rewrite example")
    for markdown in sorted(SKILL.parent.rglob("*.md")):
        if "show security policies hit-count global" in markdown.read_text(encoding="utf-8"):
            errors.append(
                f"{markdown.relative_to(ROOT)} uses unsupported "
                "'show security policies hit-count global' syntax"
            )
    # The usage summary lives in the installation-and-usage guide; scan both.
    readme = README.read_text(encoding="utf-8") + "\n" + (
        ROOT / "guides" / "installation-and-usage.md"
    ).read_text(encoding="utf-8")
    catalog = CATALOG.read_text(encoding="utf-8")
    for name, text in (("README.md", readme), ("SKILLS.md", catalog)):
        if "show security policies hit-count global" in text:
            errors.append(
                f"{name} uses unsupported 'show security policies hit-count global' syntax"
            )
    require(
        r"`srx-policy`[^\n]+enforces `security policies global`",
        catalog,
        "SKILLS.md does not describe the enforced global-policy output default",
        errors,
    )
    if re.search(
        r"Design SRX security policy[^\n]+Prefer `security policies global`",
        readme,
        re.IGNORECASE,
    ):
        errors.append("README.md usage summary still weakly says to prefer global policy")
    require(
        r"Design SRX security policy[^\n]+Enforce `security policies global`[^\n]+explicit opt-out",
        readme,
        "README.md usage summary does not enforce global output absent explicit opt-out",
        errors,
    )
    require(
        r"show security policies hit-count from-zone.*?```\s+The .*?zone-based policies only",
        skill,
        "SKILL.md does not label zone-filtered hit counts as zone-policy-only",
        errors,
    )

    if not EXAMPLE.exists():
        errors.append(f"missing reference example: {EXAMPLE.relative_to(ROOT)}")
    else:
        example = EXAMPLE.read_text(encoding="utf-8")
        require(
            r"set security policies from-zone\s+\S+\s+to-zone\s+\S+\s+policy",
            example,
            "reference example lacks zone-pair input",
            errors,
        )
        require(
            r"set security policies global policy\s+\S+\s+match from-zone",
            example,
            "reference example lacks global-policy output",
            errors,
        )
        require(
            r"single ordered global table",
            example,
            "reference example does not state the ordered-table invariant",
            errors,
        )

    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    if errors:
        return 1

    print("OK: srx-policy enforces global output, day-one rewrite, and pre-return rejection")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

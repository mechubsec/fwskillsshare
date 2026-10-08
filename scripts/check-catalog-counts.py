#!/usr/bin/env python3
"""Validate skill counts across README.md, SKILLS.md, and QUALITY.md.

Catalog counts are stated in badges, prose, and tables across multiple markdown
files. This drift has shipped twice: once before release 1.5.0 (deployment family
grew from 2 to 3, only README was updated), and again when the 30th skill was
added. The source of truth is skills/inventory.json; this script makes the drift
impossible by enforcing consistency everywhere counts appear.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "skills" / "inventory.json"
README = ROOT / "README.md"
SKILLS_MD = ROOT / "SKILLS.md"
QUALITY_MD = ROOT / "QUALITY.md"
GUIDES_DIR = ROOT / "guides"


def load_inventory() -> tuple[int, int, int, set[str]]:
    """Load inventory and return (total, reviewed, unreviewed, unreviewed_names)."""
    with INVENTORY.open(encoding="utf-8") as f:
        manifest = json.load(f)

    total = len(manifest)
    reviewed = sum(1 for skill in manifest if skill.get("reviewed", False))
    unreviewed = total - reviewed
    unreviewed_names = {
        skill["name"] for skill in manifest if not skill.get("reviewed", False)
    }

    return total, reviewed, unreviewed, unreviewed_names


def check_readme_skills_badge(readme_text: str, total: int) -> list[str]:
    """Check README.md skills badge count."""
    errors = []
    match = re.search(r'badge/skills-(\d+)-', readme_text)
    if not match:
        errors.append("README.md: could not find skills badge")
    else:
        found = int(match.group(1))
        if found != total:
            line_num = readme_text[:match.start()].count('\n') + 1
            errors.append(
                f"README.md line {line_num}: skills badge shows {found}, expected {total}"
            )
    return errors


def check_readme_reviewed_badge(readme_text: str, reviewed: int, total: int) -> list[str]:
    """Check README.md reviewed badge count."""
    errors = []
    match = re.search(r'badge/reviewed-(\d+)%2F(\d+)-', readme_text)
    if not match:
        errors.append("README.md: could not find reviewed badge")
    else:
        found_reviewed = int(match.group(1))
        found_total = int(match.group(2))
        line_num = readme_text[:match.start()].count('\n') + 1

        if found_reviewed != reviewed:
            errors.append(
                f"README.md line {line_num}: reviewed badge shows {found_reviewed}, expected {reviewed}"
            )
        if found_total != total:
            errors.append(
                f"README.md line {line_num}: reviewed badge total shows {found_total}, expected {total}"
            )
    return errors


def check_all_n_prose(text: str, filename: str, total: int) -> list[str]:
    """Check all occurrences of 'all N' in prose."""
    errors = []
    # Match "all <digits>" with word boundaries
    for match in re.finditer(r'\ball (\d+)\b', text):
        found = int(match.group(1))
        if found != total:
            line_num = text[:match.start()].count('\n') + 1
            errors.append(
                f"{filename} line {line_num}: prose 'all {found}' should be 'all {total}'"
            )
    return errors


def check_r_of_t_prose(text: str, filename: str, reviewed: int, total: int) -> list[str]:
    """Check all occurrences of 'R of the T' pattern."""
    errors = []
    # Match "<digits> of the <digits>"
    for match in re.finditer(r'(\d+) of the (\d+)', text):
        found_reviewed = int(match.group(1))
        found_total = int(match.group(2))
        line_num = text[:match.start()].count('\n') + 1

        if found_reviewed != reviewed or found_total != total:
            errors.append(
                f"{filename} line {line_num}: found '{found_reviewed} of the {found_total}', "
                f"expected '{reviewed} of the {total}'"
            )
    return errors


def check_readme_skills_header(readme_text: str, total: int) -> list[str]:
    """Check README.md '**N skills** across five families' line."""
    errors = []
    match = re.search(r'\*\*(\d+) skills\*\*', readme_text)
    if not match:
        errors.append("README.md: could not find '**N skills**' header")
    else:
        found = int(match.group(1))
        if found != total:
            line_num = readme_text[:match.start()].count('\n') + 1
            errors.append(
                f"README.md line {line_num}: '**{found} skills**' should be '**{total} skills**'"
            )
    return errors


def check_quality_table(quality_text: str, total: int, reviewed: int) -> list[str]:
    """Check QUALITY.md per-family table."""
    errors = []

    # Find the table - it's the one with a Total row
    # Match markdown table rows
    table_pattern = r'\|[^\n]+\|[^\n]+\|[^\n]+\|'
    matches = list(re.finditer(table_pattern, quality_text))

    if not matches:
        errors.append("QUALITY.md: could not find per-family table")
        return errors

    # Find the table that contains "Total"
    total_row_idx = None
    table_start_idx = None

    for i, match in enumerate(matches):
        if '**Total**' in match.group(0):
            total_row_idx = i
            # Find the start of this table (look backwards for header)
            for j in range(i - 1, -1, -1):
                if 'Family' in matches[j].group(0):
                    table_start_idx = j
                    break
            break

    if total_row_idx is None:
        errors.append("QUALITY.md: could not find Total row in per-family table")
        return errors

    if table_start_idx is None:
        errors.append("QUALITY.md: could not find table header before Total row")
        return errors

    # Parse the Total row: | **Total** | **<T>** | **<R> / <T>** |
    total_row = matches[total_row_idx].group(0)
    total_match = re.search(r'\|\s*\*\*(\d+)\*\*\s*\|\s*\*\*(\d+)\s*/\s*(\d+)\*\*\s*\|', total_row)

    if not total_match:
        line_num = quality_text[:matches[total_row_idx].start()].count('\n') + 1
        errors.append(f"QUALITY.md line {line_num}: could not parse Total row")
        return errors

    total_col = int(total_match.group(1))
    reviewed_num = int(total_match.group(2))
    total_denom = int(total_match.group(3))

    line_num = quality_text[:matches[total_row_idx].start()].count('\n') + 1

    if total_col != total:
        errors.append(
            f"QUALITY.md line {line_num}: Total row count column shows {total_col}, expected {total}"
        )
    if reviewed_num != reviewed:
        errors.append(
            f"QUALITY.md line {line_num}: Total row reviewed shows {reviewed_num}, expected {reviewed}"
        )
    if total_denom != total:
        errors.append(
            f"QUALITY.md line {line_num}: Total row reviewed denominator shows {total_denom}, expected {total}"
        )

    # Parse family rows and sum them
    family_total_sum = 0
    family_reviewed_sum = 0

    # Start from header + 2 (skip header and separator), up to total row
    for i in range(table_start_idx + 2, total_row_idx):
        row = matches[i].group(0)
        # Match: | <family> | <count> | <reviewed> / <count> |
        family_match = re.search(r'\|\s*([^|]+)\|\s*(\d+)\s*\|\s*(\d+)\s*/\s*(\d+)\s*\|', row)

        if family_match:
            family_count = int(family_match.group(2))
            family_reviewed = int(family_match.group(3))
            family_denom = int(family_match.group(4))

            row_line_num = quality_text[:matches[i].start()].count('\n') + 1

            # Check that denominator equals count column
            if family_denom != family_count:
                errors.append(
                    f"QUALITY.md line {row_line_num}: family row denominator {family_denom} "
                    f"does not match count column {family_count}"
                )

            family_total_sum += family_count
            family_reviewed_sum += family_reviewed

    # Verify sums match
    if family_total_sum != total:
        errors.append(
            f"QUALITY.md: per-family count sum is {family_total_sum}, expected {total}"
        )
    if family_reviewed_sum != reviewed:
        errors.append(
            f"QUALITY.md: per-family reviewed sum is {family_reviewed_sum}, expected {reviewed}"
        )

    return errors


def check_exceptions_sentence(
    text: str, filename: str, unreviewed_names: set[str]
) -> list[str]:
    """Check that 'exceptions are' sentence matches unreviewed skills."""
    errors = []

    # Find the sentence starting with "The exceptions are" or containing it
    match = re.search(
        r'The exceptions\s+(?:are|is)\s+([^.]+)\.',
        text,
        re.IGNORECASE
    )

    if not match:
        errors.append(f"{filename}: could not find 'The exceptions are' sentence")
        return errors

    sentence = match.group(1)
    line_num = text[:match.start()].count('\n') + 1

    # Extract backticked skill names from the sentence
    mentioned = set(re.findall(r'`([^`]+)`', sentence))

    # Check for discrepancies
    named_but_reviewed = mentioned - unreviewed_names
    unreviewed_but_unnamed = unreviewed_names - mentioned

    if named_but_reviewed:
        errors.append(
            f"{filename} line {line_num}: exceptions sentence names reviewed skills: "
            f"{', '.join(sorted(named_but_reviewed))}"
        )

    if unreviewed_but_unnamed:
        errors.append(
            f"{filename} line {line_num}: exceptions sentence missing unreviewed skills: "
            f"{', '.join(sorted(unreviewed_but_unnamed))}"
        )

    return errors


def main() -> int:
    errors: list[str] = []

    # Load source of truth
    try:
        total, reviewed, unreviewed, unreviewed_names = load_inventory()
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        errors.append(f"failed to load inventory: {e}")
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    # Load files
    try:
        readme_text = README.read_text(encoding="utf-8")
        skills_text = SKILLS_MD.read_text(encoding="utf-8")
        quality_text = QUALITY_MD.read_text(encoding="utf-8")
    except FileNotFoundError as e:
        errors.append(f"failed to load markdown file: {e}")
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    # Run checks
    errors.extend(check_readme_skills_badge(readme_text, total))
    errors.extend(check_readme_reviewed_badge(readme_text, reviewed, total))
    errors.extend(check_all_n_prose(readme_text, "README.md", total))
    errors.extend(check_all_n_prose(skills_text, "SKILLS.md", total))
    errors.extend(check_r_of_t_prose(readme_text, "README.md", reviewed, total))
    errors.extend(check_r_of_t_prose(quality_text, "QUALITY.md", reviewed, total))
    errors.extend(check_readme_skills_header(readme_text, total))
    # Counts moved out of README into guides/ must stay correct there too.
    for guide in sorted(GUIDES_DIR.glob("*.md")):
        guide_text = guide.read_text(encoding="utf-8")
        guide_name = f"guides/{guide.name}"
        errors.extend(check_all_n_prose(guide_text, guide_name, total))
        errors.extend(check_r_of_t_prose(guide_text, guide_name, reviewed, total))
    errors.extend(check_quality_table(quality_text, total, reviewed))
    errors.extend(check_exceptions_sentence(readme_text, "README.md", unreviewed_names))
    errors.extend(check_exceptions_sentence(quality_text, "QUALITY.md", unreviewed_names))

    # Print errors
    for error in errors:
        print(f"ERROR: {error}")

    if errors:
        return 1

    print(
        f"OK: catalog counts consistent at {total} skills, {reviewed} reviewed, "
        f"across README.md, guides/, SKILLS.md, QUALITY.md"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

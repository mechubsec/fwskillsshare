#!/usr/bin/env python3
"""Unit tests for the evals checker.

Every negative case drives the real `main()` against a disposable tree and
asserts on its exit status and diagnostics. Re-implementing the detection
logic inside a test proves only that the test can count; it passes just as
happily when the production rejection branch is deleted.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "check_evals", ROOT / "scripts" / "check-evals.py"
)
checker = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(checker)


VALID_EVAL = """# test-skill evals

Run each scenario in a fresh agent session with the skill installed.

## Scenario 1: Parse basic config

**Prompt:** Parse this basic config

**Input:** None

**Must:**
- Produces valid schema

**Must not:**
- Errors on valid input

## Scenario 2: Handle edge case

**Prompt:** Parse edge case

**Input:** Fixture: skills/test-skill/references/fixture.md

**Must:**
- Handles the edge case
- Returns valid output

**Must not:**
- Crashes
"""


def run_checker(skills_structure: dict[str, bool], evals_content: dict[str, str]) -> tuple[int, str]:
    """Run the checker against a disposable directory tree.

    Args:
        skills_structure: {skill_name: has_SKILL_md}
        evals_content: {skill_name: eval_file_content}
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        skills_dir = tmppath / "skills"
        evals_dir = tmppath / "evals"
        skills_dir.mkdir()
        evals_dir.mkdir()

        # Create skill directories
        for skill, has_skill_md in skills_structure.items():
            skill_dir = skills_dir / skill
            skill_dir.mkdir()
            if has_skill_md:
                (skill_dir / "SKILL.md").write_text("# Skill", encoding="utf-8")

        # Create eval files
        for skill, content in evals_content.items():
            (evals_dir / f"{skill}.md").write_text(content, encoding="utf-8")

        original_skills = checker.SKILLS_DIR
        original_evals = checker.EVALS_DIR
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        try:
            checker.SKILLS_DIR = skills_dir
            checker.EVALS_DIR = evals_dir
            with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
                status = checker.main()
        finally:
            checker.SKILLS_DIR = original_skills
            checker.EVALS_DIR = original_evals
        # Combine stdout and stderr for assertions
        return status, stdout_buffer.getvalue() + stderr_buffer.getvalue()


class ValidCaseTests(unittest.TestCase):
    def test_valid_skill_and_eval_passes(self) -> None:
        status, output = run_checker(
            {"test-skill": True},
            {"test-skill": VALID_EVAL}
        )
        self.assertEqual(status, 0, output)
        self.assertIn("OK:", output)


class MissingEvalTests(unittest.TestCase):
    def test_skill_without_eval_is_rejected(self) -> None:
        status, output = run_checker(
            {"test-skill": True},
            {}
        )
        self.assertEqual(status, 1)
        self.assertIn("missing eval", output.lower())
        self.assertIn("test-skill", output)

    def test_eval_without_skill_is_rejected(self) -> None:
        status, output = run_checker(
            {},
            {"orphan-skill": VALID_EVAL.replace("test-skill", "orphan-skill")}
        )
        self.assertEqual(status, 1)
        self.assertIn("nonexistent", output.lower())
        self.assertIn("orphan-skill", output)


class StructuralErrorTests(unittest.TestCase):
    def test_missing_h1_is_rejected(self) -> None:
        bad_eval = VALID_EVAL.replace("# test-skill evals", "## No H1 here")
        status, output = run_checker(
            {"test-skill": True},
            {"test-skill": bad_eval}
        )
        self.assertEqual(status, 1)
        self.assertIn("Missing H1", output)

    def test_wrong_h1_name_is_rejected(self) -> None:
        bad_eval = VALID_EVAL.replace("# test-skill evals", "# wrong-name evals")
        status, output = run_checker(
            {"test-skill": True},
            {"test-skill": bad_eval}
        )
        self.assertEqual(status, 1)
        self.assertIn("H1 name", output)
        self.assertIn("wrong-name", output)

    def test_only_one_scenario_is_rejected(self) -> None:
        bad_eval = """# test-skill evals

## Scenario 1: Only one

**Prompt:** Test

**Input:** None

**Must:**
- Something

**Must not:**
- Something else
"""
        status, output = run_checker(
            {"test-skill": True},
            {"test-skill": bad_eval}
        )
        self.assertEqual(status, 1)
        self.assertIn("Found 1 scenario", output)

    def test_missing_prompt_is_rejected(self) -> None:
        bad_eval = VALID_EVAL.replace("**Prompt:** Parse this basic config", "")
        status, output = run_checker(
            {"test-skill": True},
            {"test-skill": bad_eval}
        )
        self.assertEqual(status, 1)
        self.assertIn("Missing **Prompt:**", output)

    def test_missing_input_is_rejected(self) -> None:
        bad_eval = VALID_EVAL.replace("**Input:** None", "")
        status, output = run_checker(
            {"test-skill": True},
            {"test-skill": bad_eval}
        )
        self.assertEqual(status, 1)
        self.assertIn("Missing **Input:**", output)

    def test_missing_must_is_rejected(self) -> None:
        bad_eval = VALID_EVAL.replace("**Must:**\n- Produces valid schema", "")
        status, output = run_checker(
            {"test-skill": True},
            {"test-skill": bad_eval}
        )
        self.assertEqual(status, 1)
        self.assertIn("Missing **Must:**", output)

    def test_must_without_bullets_is_rejected(self) -> None:
        bad_eval = VALID_EVAL.replace("**Must:**\n- Produces valid schema", "**Must:**\n\nNo bullets here")
        status, output = run_checker(
            {"test-skill": True},
            {"test-skill": bad_eval}
        )
        self.assertEqual(status, 1)
        self.assertIn("has no bullets", output)

    def test_missing_must_not_is_rejected(self) -> None:
        bad_eval = VALID_EVAL.replace("**Must not:**\n- Errors on valid input", "")
        status, output = run_checker(
            {"test-skill": True},
            {"test-skill": bad_eval}
        )
        self.assertEqual(status, 1)
        self.assertIn("Missing **Must not:**", output)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Negative contract tests for the runtime-intake validator."""

from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
VALIDATOR_PATH = SCRIPT_DIR / "check-runtime-intake.py"
SPEC = importlib.util.spec_from_file_location("check_runtime_intake", VALIDATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot import validator from {VALIDATOR_PATH}")
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)

CLAUDE_ADAPTATION = """\
- Claude: select at most three neutral entries, project each to only `question`,
  `header`, and `options`, then add `multiSelect: false`; do not send `id` or
  `ask_when`."""
CODEX_ADAPTATION = """\
- Codex: select at most three neutral entries and project each to only `id`,
  `header`, `question`, and `options`; do not send `ask_when` or `multiSelect`."""
FALLBACK_ADAPTATION = """\
- Fallback: ask the same questions in concise plain text with a free-text
  `Other` path."""
TOOL_ADAPTATION = "\n".join(
    (
        CLAUDE_ADAPTATION,
        CODEX_ADAPTATION,
        FALLBACK_ADAPTATION,
        "- Never request secrets.",
    )
)

VALID_CATALOG = {
    "questions": [
        {
            "id": "audit_scope",
            "ask_when": "The requested audit scope is absent.",
            "header": "Scope",
            "question": "What should the audit cover?",
            "options": [
                {
                    "label": "Full device (Recommended)",
                    "description": "Inspect the complete device configuration.",
                },
                {
                    "label": "Rulebase only",
                    "description": "Inspect only the security rulebase.",
                },
            ],
        }
    ]
}

INVOCATION_CLAUSE = (
    "For each unresolved material fact whose catalog condition is true, invoke "
    "Claude `AskUserQuestion` or Codex `request_user_input` before continuing "
    "or issuing an open-ended request."
)
ROUNDS_CLAUSE = (
    "Ask at most three single-select catalog questions per round. After each "
    "response, ask another round whenever any unresolved material catalog "
    "condition remains true; continue only when none remain. Do not repeat "
    "answered questions or show the full catalog."
)
FALLBACK_CLAUSE = (
    "Without a native tool, present each selected catalog question with its 2-3 "
    "labeled choices and a free-text `Other` path in concise plain text; do not "
    "substitute a generic checklist."
)
EXPECTED_COMMONMARK_TYPE6_TAGS = (
    "address",
    "article",
    "aside",
    "base",
    "basefont",
    "blockquote",
    "body",
    "caption",
    "center",
    "col",
    "colgroup",
    "dd",
    "details",
    "dialog",
    "dir",
    "div",
    "dl",
    "dt",
    "fieldset",
    "figcaption",
    "figure",
    "footer",
    "form",
    "frame",
    "frameset",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "head",
    "header",
    "hr",
    "html",
    "iframe",
    "legend",
    "li",
    "link",
    "main",
    "menu",
    "menuitem",
    "nav",
    "noframes",
    "ol",
    "optgroup",
    "option",
    "p",
    "param",
    "search",
    "section",
    "summary",
    "table",
    "tbody",
    "td",
    "tfoot",
    "th",
    "thead",
    "title",
    "tr",
    "track",
    "ul",
)
VALID_SKILL = f"""\
# Runtime Intake Probe

## Runtime intake

Before starting the workflow, inspect the request, supplied artifacts, and
available approved read-only evidence. If unresolved facts could materially
change safety, scope, correctness, confidence, or the requested output, read
`references/runtime-intake.md`.

{INVOCATION_CLAUSE}
{ROUNDS_CLAUSE}
{FALLBACK_CLAUSE}

Never request secrets or unredacted customer data. Treat intake answers as task
context, not approval for a live change; obtain separate explicit approval
before configuration, commit, upgrade, reboot, delete, or failover actions.

## Workflow

Continue with the requested task.
"""
STANDARD_PROBE_PATH = Path("skills/probe/SKILL.md")


def wrap_complete_runtime_region(opener: str, closer: str) -> str:
    start = VALID_SKILL.index("## Runtime intake")
    next_heading = VALID_SKILL.index("## Workflow", start)
    end = VALID_SKILL.index("\n", next_heading)
    return (
        f"{VALID_SKILL[:start]}{opener}\n"
        f"{VALID_SKILL[start:end]}\n"
        f"{closer}{VALID_SKILL[end:]}"
    )


def render_reference(
    catalog: dict[str, object] | None = None,
    adaptation: str = TOOL_ADAPTATION,
) -> str:
    payload = VALID_CATALOG if catalog is None else catalog
    return render_raw_reference(json.dumps(payload, indent=2), adaptation)


def render_raw_reference(
    raw_catalog: str,
    adaptation: str = TOOL_ADAPTATION,
) -> str:
    return f"""\
# Runtime Intake

## When to ask

Ask only unresolved material questions.

## Tool adaptation

{adaptation}

## Question catalog

```json
{raw_catalog}
```
"""


class RuntimeIntakeValidatorTests(unittest.TestCase):
    def assert_has_error(self, text: str, fragment: str) -> None:
        errors = VALIDATOR.validate_catalog(Path("runtime-intake.md"), text)
        self.assertTrue(
            any(fragment in error for error in errors),
            f"expected error containing {fragment!r}, got {errors!r}",
        )

    def assert_skill_rejected(self, skill_text: str) -> None:
        errors = VALIDATOR.validate_skill(STANDARD_PROBE_PATH, skill_text)
        self.assertTrue(
            errors,
            f"expected {STANDARD_PROBE_PATH} to be rejected",
        )

    def assert_no_active_runtime_section(self, skill_text: str) -> None:
        self.assertEqual(
            VALIDATOR.validate_skill(STANDARD_PROBE_PATH, skill_text),
            [
                f"{STANDARD_PROBE_PATH}: expected exactly one "
                "'## Runtime intake' section"
            ],
        )

    def assert_skill_error(self, skill_text: str, message: str) -> None:
        self.assertEqual(
            VALIDATOR.validate_skill(STANDARD_PROBE_PATH, skill_text),
            [f"{STANDARD_PROBE_PATH}: {message}"],
        )

    def test_accepts_exact_neutral_contract(self) -> None:
        self.assertEqual(
            VALIDATOR.validate_catalog(
                Path("runtime-intake.md"), render_reference()
            ),
            [],
        )

    def test_rejects_reference_wrapped_in_inactive_markdown(self) -> None:
        reference = render_reference()
        cases = (
            f"````markdown\n{reference}````\n",
            f"<!--\n{reference}-->\n",
        )
        for mutant in cases:
            with self.subTest(opener=mutant.splitlines()[0]):
                errors = VALIDATOR.validate_catalog(
                    Path("runtime-intake.md"),
                    mutant,
                )
                self.assertTrue(errors)
                for heading in VALIDATOR.REQUIRED_REFERENCE_HEADINGS:
                    self.assertTrue(
                        any(f"missing {heading!r}" in error for error in errors),
                        errors,
                    )

    def test_rejects_required_heading_text_embedded_in_active_prose(
        self,
    ) -> None:
        mutant = render_reference().replace(
            "# Runtime Intake",
            "prefix # Runtime Intake suffix",
            1,
        )
        self.assert_has_error(mutant, "missing '# Runtime Intake'")

    def test_rejects_duplicate_exact_active_reference_heading(self) -> None:
        mutant = render_reference().replace(
            "## When to ask",
            "## When to ask\n\n## When to ask",
            1,
        )
        self.assert_has_error(
            mutant,
            "expected exactly one active '## When to ask' heading",
        )

    def test_rejects_semantic_reference_heading_equivalents(self) -> None:
        cases = (
            ("# Runtime Intake", "# Runtime Intake ###\n"),
            ("# Runtime Intake", "#\tRuntime Intake\n"),
            ("# Runtime Intake", "Runtime Intake\n===\n"),
            ("## When to ask", "## When to ask ###\n"),
            ("## When to ask", "##  When to ask\n"),
            ("## When to ask", "##\tWhen to ask\n"),
            ("## When to ask", "When to ask\n---\n"),
            ("## When to ask", "When to\nask\n---\n"),
            ("## Tool adaptation", "> ## Tool adaptation ###\n"),
            ("## Tool adaptation", ">  ## Tool adaptation ###\n"),
            ("## Tool adaptation", ">    ## Tool adaptation ###\n"),
            ("## Tool adaptation", "> Tool adaptation\n> ---\n"),
            ("## Question catalog", "- ## Question catalog ###\n"),
            ("## Question catalog", "- Question catalog\n  ---\n"),
            (
                "## Question catalog",
                "- Question\n"
                "  catalog\n"
                "  ---\n",
            ),
        )
        for heading, duplicate in cases:
            with self.subTest(heading=heading, duplicate=duplicate):
                self.assert_has_error(
                    render_reference() + "\n" + duplicate,
                    f"expected exactly one active {heading!r} heading",
                )

    def test_reference_setext_equivalence_uses_complete_heading_text(
        self,
    ) -> None:
        multiline_decoys = (
            "Additional context\nWhen to ask\n---\n",
            "> Additional context\n> Tool adaptation\n> ---\n",
            "- Additional context\n  Question catalog\n  ---\n",
        )
        for decoy in multiline_decoys:
            with self.subTest(decoy=decoy):
                self.assertEqual(
                    VALIDATOR.validate_catalog(
                        Path("runtime-intake.md"),
                        render_reference() + "\n" + decoy,
                    ),
                    [],
                )

        inactive_decoys = (
            "````markdown\n## When to ask ###\n````\n",
            "````markdown\nQuestion catalog\n---\n````\n",
        )
        for decoy in inactive_decoys:
            with self.subTest(decoy=decoy):
                self.assertEqual(
                    VALIDATOR.validate_catalog(
                        Path("runtime-intake.md"),
                        render_reference() + "\n" + decoy,
                    ),
                    [],
                )

        commented = VALIDATOR.analyze_markdown(
            "<!--\nTool adaptation\n---\n-->\n"
        )
        self.assertFalse(commented.headings)

    def test_link_reference_definitions_precede_setext_headings(self) -> None:
        skill_cases = (
            "[foo]: /url\nRuntime intake\n---\n",
            "[foo]:\n  /url\nRuntime intake\n---\n",
            "[foo]: /url\n  \"title\"\nRuntime intake\n---\n",
            "[foo\\]]: /url\nRuntime intake\n---\n",
            "[\nfoo\n]: /url\nRuntime intake\n---\n",
            "[foo]: /url '\n title\n line\n '\nRuntime intake\n---\n",
            "> [foo]: /url\n> Runtime intake\n> ---\n",
            "> [\n> foo\n> ]: /url\n"
            "> Runtime intake\n> ---\n",
            "- [foo]: /url\n  Runtime intake\n  ---\n",
            "- [foo]: /url '\n"
            "  title\n"
            "  '\n"
            "  Runtime intake\n"
            "  ---\n",
        )
        for suffix in skill_cases:
            with self.subTest(kind="skill", suffix=suffix):
                self.assert_skill_error(
                    f"{VALID_SKILL}\n{suffix}",
                    "expected exactly one '## Runtime intake' section",
                )

        reference_cases = (
            "[foo]: /url\nWhen to ask\n---\n",
            "[foo]:\n  /url\nWhen to ask\n---\n",
            "[foo\\]]: /url\nWhen to ask\n---\n",
            "[\nfoo\n]: /url\nWhen to ask\n---\n",
            "[foo]: /url \"\n title\n\"\nWhen to ask\n---\n",
            "> [foo]: /url\n> Tool adaptation\n> ---\n",
            "- [foo]: /url\n  Question catalog\n  ---\n",
        )
        for suffix in reference_cases:
            with self.subTest(kind="reference", suffix=suffix):
                heading = (
                    "## Tool adaptation"
                    if "Tool adaptation" in suffix
                    else (
                        "## Question catalog"
                        if "Question catalog" in suffix
                        else "## When to ask"
                    )
                )
                self.assert_has_error(
                    render_reference() + "\n" + suffix,
                    f"expected exactly one active {heading!r} heading",
                )

    def test_link_reference_definitions_do_not_interrupt_paragraphs(self) -> None:
        controls = (
            "A paragraph\n[foo]: /url\nRuntime intake\n---\n",
            "> A paragraph\n> [foo]: /url\n> Runtime intake\n> ---\n",
            "[foo]:\nRuntime intake\n---\n",
            "[\n\nfoo\n]: /url\nRuntime intake\n---\n",
            "[foo[bar]: /url\nRuntime intake\n---\n",
            "[foo]: /url '\n"
            "title\n"
            "\n"
            "'\n"
            "Runtime intake\n"
            "---\n",
            "    [foo]: /url\n"
            "    Runtime intake\n"
            "    ---\n",
            "````markdown\n"
            "[foo]: /url\n"
            "Runtime intake\n"
            "---\n"
            "````\n",
        )
        for suffix in controls:
            with self.subTest(suffix=suffix):
                self.assertEqual(
                    VALIDATOR.validate_skill(
                        STANDARD_PROBE_PATH,
                        f"{VALID_SKILL}\n{suffix}",
                    ),
                    [],
                )

    def test_pending_link_references_yield_to_interrupting_blocks(self) -> None:
        pending_states = {
            "label": ("[foo",),
            "destination": ("[foo]:",),
            "same-line-title": ('[foo]: /url "',),
            "next-line-title": ("[foo]: /url", '"'),
        }
        interrupting_blocks = {
            "thematic-break": ("***", "thematic-break"),
            "setext-h1-single": ("=", "setext-underline"),
            "setext-h1-double": ("==", "setext-underline"),
            "setext-h1-trailing-space": ("===  ", "setext-underline"),
            "setext-h2-single": ("-", "setext-underline"),
            "setext-h2-double": ("--", "setext-underline"),
            "setext-h2-trailing-tab": ("---\t", "setext-underline"),
            "atx": ("## Runtime intake", "atx"),
            "raw-html-1": ("<script>", "raw-html-1"),
            "raw-html-3": ("<?runtime?>", "raw-html-3"),
            "raw-html-4": ("<!RUNTIME>", "raw-html-4"),
            "raw-html-5": ("<![CDATA[runtime]]>", "raw-html-5"),
            "raw-html-6": ("<div>", "raw-html-6"),
        }

        def wrap(
            lines: tuple[str, ...],
            container: str,
            ending: str = "\n",
        ) -> str:
            if container == "quote":
                physical = [f"> {line}" for line in lines]
            elif container == "list":
                physical = [
                    f"- {lines[0]}",
                    *(f"  {line}" for line in lines[1:]),
                ]
            else:
                physical = list(lines)
            return ending.join(physical) + ending

        for state, pending in pending_states.items():
            for block, (indicator, expected_kind) in interrupting_blocks.items():
                for container in ("top-level", "quote", "list"):
                    with self.subTest(
                        state=state,
                        block=block,
                        container=container,
                    ):
                        text = wrap(pending + (indicator,), container)
                        analysis = VALIDATOR.analyze_markdown(text)
                        current = analysis.lines[-1]
                        self.assertEqual(current.block_kind, expected_kind)
                        self.assertEqual(
                            current.content.rstrip(" \t"),
                            indicator.rstrip(" \t"),
                        )
                        self.assertEqual(
                            current.content_start,
                            text.rfind(indicator),
                        )
                        self.assertEqual(current.source_end, len(text))
                        self.assertEqual(
                            current.normalized,
                            current.content + "\n",
                        )
                        if expected_kind == "setext-underline":
                            self.assertEqual(
                                analysis.headings[-1].style,
                                "setext",
                            )
                            self.assertEqual(
                                analysis.headings[-1].level,
                                1
                                if indicator.lstrip().startswith("=")
                                else 2,
                            )
                        elif expected_kind.startswith("raw-html-"):
                            self.assertEqual(
                                analysis.raw_html_lines,
                                [current],
                            )

        adjacency_cases = (
            ("[foo\n> ## Runtime intake\n", "quote"),
            ("[foo\n- ## Runtime intake\n", "list"),
            ("> [foo\n> ## Runtime intake\n", "quote"),
            ("- [foo\n  ## Runtime intake\n", "list"),
        )
        for text, container_kind in adjacency_cases:
            with self.subTest(adjacency=container_kind, text=text):
                analysis = VALIDATOR.analyze_markdown(text)
                self.assertEqual(analysis.lines[-1].block_kind, "atx")
                self.assertEqual(
                    analysis.lines[-1].containers[-1].kind,
                    container_kind,
                )
                self.assertEqual(
                    analysis.headings[-1].content,
                    "Runtime intake",
                )

    def test_pending_link_references_preserve_paragraph_interrupt_rules(
        self,
    ) -> None:
        pending_states = {
            "label": ("[foo",),
            "destination": ("[foo]:",),
            "same-line-title": ('[foo]: /url "',),
            "next-line-title": ("[foo]: /url", '"'),
        }
        continuations = {
            "empty-asterisk": ("*",),
            "empty-plus": ("+",),
            "ordered-non-one-inline": ("10. ## Runtime intake",),
            "ordered-non-one-block": (
                "10.",
                "    Runtime intake",
                "    ---",
            ),
        }

        def wrap(lines: tuple[str, ...], container: str) -> str:
            if container == "quote":
                return "".join(f"> {line}\n" for line in lines)
            if container == "list":
                return (
                    f"- {lines[0]}\n"
                    + "".join(f"  {line}\n" for line in lines[1:])
                )
            return "".join(f"{line}\n" for line in lines)

        documents = (
            ("skill", VALID_SKILL),
            ("reference", render_reference()),
        )
        for state, pending in pending_states.items():
            for case, continuation in continuations.items():
                for container in ("top-level", "quote", "list"):
                    with self.subTest(
                        state=state,
                        case=case,
                        container=container,
                    ):
                        suffix = wrap(pending + continuation, container)
                        analysis = VALIDATOR.analyze_markdown(suffix)
                        self.assertNotIn(
                            "Runtime intake",
                            [heading.content for heading in analysis.headings],
                        )
                        expected_depth = 0 if container == "top-level" else 1
                        self.assertTrue(
                            all(
                                len(line.containers) == expected_depth
                                for line in analysis.lines
                            )
                        )
                        for document, original in documents:
                            with self.subTest(document=document):
                                mutant = original + "\n" + suffix
                                if document == "skill":
                                    self.assertEqual(
                                        VALIDATOR.validate_skill(
                                            STANDARD_PROBE_PATH,
                                            mutant,
                                        ),
                                        [],
                                    )
                                else:
                                    self.assertEqual(
                                        VALIDATOR.validate_catalog(
                                            Path("runtime-intake.md"),
                                            mutant,
                                        ),
                                        [],
                                    )

    def test_pending_link_references_keep_lazy_list_continuations(
        self,
    ) -> None:
        pending_states = {
            "label": ("[foo", "bar]: /url"),
            "destination": ("[foo]:", "/url"),
            "same-line-title": ('[foo]: /url "', 'title"'),
            "next-line-title": ("[foo]: /url", '"title"'),
        }
        list_forms = {
            "ordinary-lf": ("- ", 2, "\n"),
            "wide-padding-lf": ("-   ", 4, "\n"),
            "tab-padding-crlf": ("-\t", 4, "\r\n"),
        }
        for state, (first, lazy) in pending_states.items():
            for form, (prefix, indent, ending) in list_forms.items():
                with self.subTest(state=state, form=form):
                    text = (
                        prefix
                        + first
                        + ending
                        + lazy
                        + ending
                        + (" " * indent)
                        + "Runtime intake"
                        + ending
                        + (" " * indent)
                        + "---"
                        + ending
                    )
                    analysis = VALIDATOR.analyze_markdown(text)
                    heading = analysis.headings[-1]
                    self.assertEqual(
                        (heading.level, heading.content, heading.style),
                        (2, "Runtime intake", "setext"),
                    )
                    self.assertEqual(
                        [container.kind for container in heading.containers],
                        ["list"],
                    )
                    self.assertEqual(
                        heading.source_start,
                        text.index("Runtime intake"),
                    )
                    self.assert_skill_error(
                        VALID_SKILL + "\n" + text,
                        "expected exactly one '## Runtime intake' section",
                    )
                    self.assert_has_error(
                        render_reference() + "\n" + text.replace(
                            "Runtime intake",
                            "When to ask",
                        ),
                        "expected exactly one active '## When to ask' heading",
                    )

    def test_pending_link_references_distinguish_lazy_setext_text(
        self,
    ) -> None:
        pending_states = {
            "label": "[foo",
            "destination": "[foo]:",
            "same-line-title": '[foo]: /url "',
            "optional-title": "[foo]: /url",
        }
        containers = {
            "list": "- ",
            "quote": "> ",
        }
        for state, pending in pending_states.items():
            for container, prefix in containers.items():
                for ending in ("\n", "\r\n"):
                    with self.subTest(
                        state=state,
                        container=container,
                        ending=repr(ending),
                    ):
                        text = (
                            prefix
                            + pending
                            + ending
                            + "==="
                            + ending
                        )
                        analysis = VALIDATOR.analyze_markdown(text)
                        self.assertEqual(analysis.headings, [])
                        self.assertEqual(
                            [
                                block.kind
                                for block in analysis.lines[-1].containers
                            ],
                            [container],
                        )
                        self.assertEqual(
                            VALIDATOR.validate_skill(
                                STANDARD_PROBE_PATH,
                                VALID_SKILL + "\n" + text,
                            ),
                            [],
                        )
                        self.assertEqual(
                            VALIDATOR.validate_catalog(
                                Path("runtime-intake.md"),
                                render_reference() + "\n" + text,
                            ),
                            [],
                        )

    def test_completed_reference_preserves_lazy_type7_paragraphs(
        self,
    ) -> None:
        containers = {
            "list": "- ",
            "quote": "> ",
        }
        for container, prefix in containers.items():
            for ending in ("\n", "\r\n"):
                with self.subTest(
                    container=container,
                    ending=repr(ending),
                ):
                    text = (
                        prefix
                        + "[foo]: /url"
                        + ending
                        + "<runtime-wrapper>"
                        + ending
                    )
                    analysis = VALIDATOR.analyze_markdown(text)
                    current = analysis.lines[-1]
                    self.assertEqual(current.block_kind, "paragraph")
                    self.assertEqual(
                        [block.kind for block in current.containers],
                        [container],
                    )
                    self.assertEqual(analysis.raw_html_lines, [])
                    self.assertEqual(
                        VALIDATOR.validate_skill(
                            STANDARD_PROBE_PATH,
                            VALID_SKILL + "\n" + text,
                        ),
                        [],
                    )
                    self.assertEqual(
                        VALIDATOR.validate_catalog(
                            Path("runtime-intake.md"),
                            render_reference() + "\n" + text,
                        ),
                            [],
                        )

    def test_completed_reference_setext_opportunity_becomes_paragraph(
        self,
    ) -> None:
        markers = ("-", "--")

        def wrap(lines: tuple[str, ...], container: str) -> str:
            if container == "quote":
                return "".join(f"> {line}\n" for line in lines)
            if container == "list":
                return (
                    f"- {lines[0]}\n"
                    + "".join(f"  {line}\n" for line in lines[1:])
                )
            return "".join(f"{line}\n" for line in lines)

        for marker in markers:
            for container in ("top-level", "quote", "list"):
                with self.subTest(marker=repr(marker), container=container):
                    text = wrap(
                        (
                            "[foo]: /url",
                            marker,
                            "2. ## Runtime intake",
                        ),
                        container,
                    )
                    analysis = VALIDATOR.analyze_markdown(text)
                    self.assertEqual(analysis.headings, [])
                    marker_line = analysis.lines[1]
                    self.assertEqual(marker_line.block_kind, "paragraph")
                    self.assertEqual(
                        VALIDATOR.validate_skill(
                            STANDARD_PROBE_PATH,
                            VALID_SKILL + "\n" + text,
                        ),
                        [],
                    )

    def test_completed_reference_preserves_thematic_break_precedence(
        self,
    ) -> None:
        markers = ("---", "---  ", "---\t")

        def wrap(
            lines: tuple[str, ...],
            container: str,
            ending: str,
        ) -> str:
            if container == "quote":
                return ending.join(f"> {line}" for line in lines) + ending
            if container == "list":
                return (
                    f"- {lines[0]}{ending}"
                    + ending.join(f"  {line}" for line in lines[1:])
                    + ending
                )
            return ending.join(lines) + ending

        for marker in markers:
            for container in ("top-level", "quote", "list"):
                for ending in ("\n", "\r\n"):
                    with self.subTest(
                        marker=repr(marker),
                        container=container,
                        ending=repr(ending),
                    ):
                        text = wrap(
                            (
                                "[foo]: /url",
                                marker,
                                "Runtime intake",
                                "---",
                            ),
                            container,
                            ending,
                        )
                        analysis = VALIDATOR.analyze_markdown(text)
                        self.assertEqual(
                            analysis.lines[1].block_kind,
                            "thematic-break",
                        )
                        heading = analysis.headings[-1]
                        self.assertEqual(
                            (heading.level, heading.content, heading.style),
                            (2, "Runtime intake", "setext"),
                        )
                        self.assert_skill_error(
                            VALID_SKILL + "\n" + text,
                            "expected exactly one '## Runtime intake' section",
                        )
                        self.assert_has_error(
                            render_reference() + "\n" + text.replace(
                                "Runtime intake",
                                "When to ask",
                            ),
                            "expected exactly one active '## When to ask' heading",
                        )

    def test_completed_reference_keeps_indented_paragraph_continuation(
        self,
    ) -> None:
        def wrap(
            lines: tuple[str, ...],
            container: str,
            ending: str,
        ) -> str:
            if container == "quote":
                return ending.join(f"> {line}" for line in lines) + ending
            if container == "list":
                return (
                    f"- {lines[0]}{ending}"
                    + ending.join(f"  {line}" for line in lines[1:])
                    + ending
                )
            return ending.join(lines) + ending

        for container in ("top-level", "quote", "list"):
            for ending in ("\n", "\r\n"):
                with self.subTest(
                    container=container,
                    ending=repr(ending),
                ):
                    text = wrap(
                        (
                            "[foo]: /url",
                            "    extra",
                            "Runtime intake",
                            "---",
                        ),
                        container,
                        ending,
                    )
                    analysis = VALIDATOR.analyze_markdown(text)
                    heading = analysis.headings[-1]
                    self.assertEqual(
                        (heading.level, heading.content, heading.style),
                        (2, "extra Runtime intake", "setext"),
                    )
                    self.assertEqual(
                        analysis.lines[1].block_kind,
                        "paragraph",
                    )
                    self.assertEqual(
                        VALIDATOR.validate_skill(
                            STANDARD_PROBE_PATH,
                            VALID_SKILL + "\n" + text,
                        ),
                        [],
                    )
                    self.assertEqual(
                        VALIDATOR.validate_catalog(
                            Path("runtime-intake.md"),
                            render_reference()
                            + "\n"
                            + text.replace(
                                "Runtime intake",
                                "When to ask",
                            ),
                        ),
                        [],
                    )

    def test_adjacent_completed_reference_definitions_are_stripped(
        self,
    ) -> None:
        second_definitions = {
            "single-line": ("[bar]: /bar",),
            "multiline-label": ("[bar", "baz]: /bar"),
            "multiline-destination": ("[bar]:", "/bar"),
            "multiline-same-line-title": (
                '[bar]: /bar "',
                'title"',
            ),
            "next-line-title": ("[bar]: /bar", '"title"'),
        }

        def wrap(
            lines: tuple[str, ...],
            container: str,
            ending: str,
        ) -> str:
            if container == "quote":
                return ending.join(f"> {line}" for line in lines) + ending
            if container == "list":
                return (
                    f"- {lines[0]}{ending}"
                    + ending.join(f"  {line}" for line in lines[1:])
                    + ending
                )
            return ending.join(lines) + ending

        for definition, second in second_definitions.items():
            for container in ("top-level", "quote", "list"):
                for ending in ("\n", "\r\n"):
                    with self.subTest(
                        definition=definition,
                        container=container,
                        ending=repr(ending),
                    ):
                        text = wrap(
                            (
                                "[foo]: /foo",
                                *second,
                                "Runtime intake",
                                "---",
                            ),
                            container,
                            ending,
                        )
                        analysis = VALIDATOR.analyze_markdown(text)
                        heading = analysis.headings[-1]
                        self.assertEqual(
                            (heading.level, heading.content, heading.style),
                            (2, "Runtime intake", "setext"),
                        )
                        self.assert_skill_error(
                            VALID_SKILL + "\n" + text,
                            "expected exactly one '## Runtime intake' section",
                        )
                        self.assert_has_error(
                            render_reference() + "\n" + text.replace(
                                "Runtime intake",
                                "When to ask",
                            ),
                            "expected exactly one active '## When to ask' heading",
                        )

    def test_pending_link_reference_interrupts_preserve_source_mapping(
        self,
    ) -> None:
        raw_text = (
            '> [foo]: /url\r\n'
            '> "\r\n'
            '> <div>\r\n'
        )
        analysis = VALIDATOR.analyze_markdown(raw_text)
        self.assertEqual(len(analysis.raw_html_lines), 1)
        raw_html = analysis.raw_html_lines[-1]
        raw_html_source_start = raw_text.index("> <div>")
        self.assertEqual(raw_html.block_kind, "raw-html-6")
        self.assertEqual(raw_html.source_start, raw_html_source_start)
        self.assertEqual(
            raw_html.source_end,
            raw_html_source_start + len("> <div>\r\n"),
        )
        self.assertEqual(raw_html.content_start, raw_text.index("<div>"))
        self.assertEqual(raw_html.content, "<div>")
        self.assertEqual(raw_html.normalized, "<div>\r\n")
        self.assertEqual(analysis.active_text, raw_text)

        heading_text = (
            "- [foo\r\n"
            "  ***\r\n"
            "  Runtime intake\r\n"
            "  ---\r\n"
        )
        heading_analysis = VALIDATOR.analyze_markdown(heading_text)
        heading = heading_analysis.headings[-1]
        self.assertEqual(heading.content, "Runtime intake")
        self.assertEqual(
            heading.source_start,
            heading_text.index("Runtime intake"),
        )
        self.assertEqual(heading.source_end, len(heading_text))
        self.assertEqual(
            heading_analysis.lines[-1].normalized,
            "---\r\n",
        )

    def test_pending_link_reference_interrupts_are_active_in_documents(
        self,
    ) -> None:
        pending_states = {
            "label": ("[foo",),
            "destination": ("[foo]:",),
            "same-line-title": ('[foo]: /url "',),
            "next-line-title": ("[foo]: /url", '"'),
        }

        def wrap(lines: tuple[str, ...], container: str) -> str:
            if container == "quote":
                return "".join(f"> {line}\n" for line in lines)
            if container == "list":
                return (
                    f"- {lines[0]}\n"
                    + "".join(f"  {line}\n" for line in lines[1:])
                )
            return "".join(f"{line}\n" for line in lines)

        documents = (
            (
                "skill",
                VALID_SKILL,
                "Runtime intake",
                lambda mutant: self.assert_skill_error(
                    mutant,
                    "expected exactly one '## Runtime intake' section",
                ),
            ),
            (
                "reference",
                render_reference(),
                "When to ask",
                lambda mutant: self.assert_has_error(
                    mutant,
                    "expected exactly one active '## When to ask' heading",
                ),
            ),
        )
        for document, original, heading, assert_rejected in documents:
            for state, pending in pending_states.items():
                for breaker in (
                    "***",
                    "=",
                    "==",
                    "===  ",
                    "-",
                    "--",
                    "---\t",
                ):
                    for container in ("top-level", "quote", "list"):
                        with self.subTest(
                            document=document,
                            state=state,
                            breaker=breaker,
                            container=container,
                        ):
                            insertion = wrap(
                                pending + (breaker, heading, "---"),
                                container,
                            )
                            assert_rejected(original + "\n" + insertion)

                for opener in (
                    "<script>",
                    "<?runtime?>",
                    "<!RUNTIME>",
                    "<![CDATA[runtime]]>",
                    "<div>",
                ):
                    for container in ("top-level", "quote", "list"):
                        with self.subTest(
                            document=document,
                            state=state,
                            opener=opener,
                            container=container,
                        ):
                            insertion = wrap(
                                pending + (opener,),
                                container,
                            )
                            if document == "skill":
                                self.assert_skill_error(
                                    original + "\n" + insertion,
                                    "raw HTML block syntax is not allowed",
                                )
                            else:
                                self.assert_has_error(
                                    original + "\n" + insertion,
                                    "raw HTML block syntax is not allowed",
                                )

                for container in ("top-level", "quote", "list"):
                    with self.subTest(
                        document=document,
                        state=state,
                        opener="type-7-control",
                        container=container,
                    ):
                        insertion = wrap(
                            pending + ("<runtime-wrapper>",),
                            container,
                        )
                        if document == "skill":
                            self.assertEqual(
                                VALIDATOR.validate_skill(
                                    STANDARD_PROBE_PATH,
                                    original + "\n" + insertion,
                                ),
                                [],
                            )
                        else:
                            self.assertEqual(
                                VALIDATOR.validate_catalog(
                                    Path("runtime-intake.md"),
                                    original + "\n" + insertion,
                                ),
                                [],
                            )

    def test_rejects_raw_html_wrapped_reference(self) -> None:
        mutant = f"<div>\n{render_reference()}</div>\n"
        self.assert_has_error(
            mutant,
            "raw HTML block syntax is not allowed",
        )

    def test_rejects_inactive_exact_adaptation_clauses(self) -> None:
        cases = (
            ("Claude projection", CLAUDE_ADAPTATION),
            ("Codex projection", CODEX_ADAPTATION),
            ("fallback and free-text Other", FALLBACK_ADAPTATION),
        )
        for expected_name, clause in cases:
            with self.subTest(adaptation=expected_name):
                mutant = render_reference().replace(
                    clause,
                    f"~~~~markdown\n{clause}\n~~~~",
                    1,
                )
                self.assert_has_error(
                    mutant,
                    f"missing exact {expected_name} language",
                )

    def test_rejects_reference_headings_out_of_canonical_order(self) -> None:
        reference = render_reference()
        when_start = reference.index("## When to ask")
        tool_start = reference.index("## Tool adaptation")
        catalog_start = reference.index("## Question catalog")
        mutant = (
            reference[:when_start]
            + reference[tool_start:catalog_start]
            + reference[when_start:tool_start]
            + reference[catalog_start:]
        )

        self.assert_has_error(
            mutant,
            "required headings are not in canonical order",
        )

    def test_rejects_adaptation_clauses_outside_tool_section(self) -> None:
        reference = render_reference()
        mutant = reference.replace(
            f"Ask only unresolved material questions.\n\n"
            f"## Tool adaptation\n\n{TOOL_ADAPTATION}",
            f"Ask only unresolved material questions.\n\n{TOOL_ADAPTATION}\n\n"
            "## Tool adaptation\n\nTool-specific projections follow.",
            1,
        )

        self.assert_has_error(
            mutant,
            "Claude projection must be inside '## Tool adaptation'",
        )

    def test_rejects_json_catalog_outside_catalog_section(self) -> None:
        reference = render_reference()
        catalog_start = reference.index("```json")
        catalog_end = reference.index("\n```", catalog_start) + len("\n```")
        catalog = reference[catalog_start:catalog_end]
        without_catalog = (
            reference[:catalog_start] + reference[catalog_end:]
        )
        mutant = without_catalog.replace(
            "## Question catalog",
            f"{catalog}\n\n## Question catalog",
            1,
        )

        self.assert_has_error(
            mutant,
            "JSON catalog must be inside '## Question catalog'",
        )

    def test_rejects_json_catalog_nested_in_outer_fence(self) -> None:
        reference = render_reference()
        catalog_start = reference.index("```json")
        catalog_end = reference.index("\n```", catalog_start) + len("\n```")
        catalog = reference[catalog_start:catalog_end]
        mutant = (
            reference[:catalog_start]
            + f"````markdown\n{catalog}\n````"
            + reference[catalog_end:]
        )

        self.assert_has_error(
            mutant,
            "expected exactly one active top-level JSON catalog",
        )

    def test_rejects_container_nested_reference_heading_duplicates(
        self,
    ) -> None:
        prefixes = (
            "- ",
            "+ ",
            "* ",
            "1. ",
            "2) ",
            "> ",
            "> - ",
            "- > ",
            "> 1. ",
        )
        for prefix in prefixes:
            with self.subTest(prefix=prefix):
                mutant = render_reference() + f"\n{prefix}## When to ask\n"
                self.assert_has_error(
                    mutant,
                    "expected exactly one active '## When to ask' heading",
                )

    def test_container_continuation_blocks_use_full_list_content_indent(
        self,
    ) -> None:
        skill_cases = (
            "10. item\n    ## Runtime intake ###\n",
            "123456789. item\n           ## Runtime intake\n",
            "-    item\n     ## Runtime intake\n",
            "- outer\n\n  10. inner\n      ## Runtime intake\n",
        )
        for continuation in skill_cases:
            with self.subTest(kind="skill", continuation=continuation):
                self.assert_skill_error(
                    f"{VALID_SKILL}\n{continuation}",
                    "expected exactly one '## Runtime intake' section",
                )

        reference_cases = (
            "10. item\n    ## When to ask\n",
            "- outer\n\n  123456789) inner\n             ## When to ask\n",
        )
        for continuation in reference_cases:
            with self.subTest(kind="reference", continuation=continuation):
                self.assert_has_error(
                    render_reference() + "\n" + continuation,
                    "expected exactly one active '## When to ask' heading",
                )

        raw_html_cases = (
            "10. item\n    <div>\n",
            "-    item\n     <div>\n",
            "- outer\n\n  10. inner\n      <![CDATA[\n",
        )
        for continuation in raw_html_cases:
            with self.subTest(kind="html", continuation=continuation):
                self.assert_skill_error(
                    f"{VALID_SKILL}\n{continuation}",
                    "raw HTML block syntax is not allowed",
                )

    def test_list_indentation_uses_tab_stop_columns(self) -> None:
        skill_cases = (
            "-\titem\n\t## Runtime intake ###\n",
            "10.\titem\n \t## Runtime intake\n",
            "- \titem\n  \t## Runtime intake\n",
        )
        for continuation in skill_cases:
            with self.subTest(kind="skill", continuation=continuation):
                self.assert_skill_error(
                    f"{VALID_SKILL}\n{continuation}",
                    "expected exactly one '## Runtime intake' section",
                )

        reference_cases = (
            "-\titem\n\t## When to ask\n",
            "10.\titem\n \t## When to ask\n",
        )
        for continuation in reference_cases:
            with self.subTest(kind="reference", continuation=continuation):
                self.assert_has_error(
                    render_reference() + "\n" + continuation,
                    "expected exactly one active '## When to ask' heading",
                )

        raw_html_cases = (
            "-\titem\n\t<div>\n",
            "10.\titem\n \t<![CDATA[\n",
        )
        for continuation in raw_html_cases:
            with self.subTest(kind="html", continuation=continuation):
                self.assert_skill_error(
                    f"{VALID_SKILL}\n{continuation}",
                    "raw HTML block syntax is not allowed",
                )

    def test_tab_indented_non_one_ordered_markers_respect_paragraphs(
        self,
    ) -> None:
        accepted = (
            "A paragraph\n2.\t## Runtime intake\n",
            "A paragraph\n2.\t<div>\n",
        )
        for suffix in accepted:
            with self.subTest(outcome="accepted", suffix=suffix):
                self.assertEqual(
                    VALIDATOR.validate_skill(
                        STANDARD_PROBE_PATH,
                        f"{VALID_SKILL}\n{suffix}",
                    ),
                    [],
                )

        rejected = (
            "A paragraph\n\n2.\t## Runtime intake\n",
            "A paragraph\n1.\t## Runtime intake\n",
            "A paragraph\n\n2.\t<div>\n",
            "A paragraph\n1.\t<div>\n",
        )
        for suffix in rejected:
            with self.subTest(outcome="rejected", suffix=suffix):
                expected = (
                    "raw HTML block syntax is not allowed"
                    if "<div>" in suffix
                    else "expected exactly one '## Runtime intake' section"
                )
                self.assert_skill_error(f"{VALID_SKILL}\n{suffix}", expected)

    def test_tab_indented_list_fence_preserves_offsets(self) -> None:
        source = (
            "-\t````html\r\n"
            "\t<div>\r\n"
            "\t````\r\n"
            "Tail\r\n"
        )
        masked = VALIDATOR.mask_inactive_markdown(source)
        self.assertEqual(len(masked), len(source))
        self.assertEqual(
            [index for index, char in enumerate(masked) if char in "\r\n"],
            [index for index, char in enumerate(source) if char in "\r\n"],
        )
        self.assertNotIn("<div>", masked)
        tail_offset = source.index("Tail")
        self.assertEqual(masked[tail_offset : tail_offset + 4], "Tail")

    def test_empty_list_items_open_containers_at_block_boundaries(
        self,
    ) -> None:
        skill_cases = (
            "10.\n    ## Runtime intake ###\n",
            "123456789)\t  \n"
            "           Runtime intake\n"
            "           ---\n",
            "- \t \n  <div>\n",
        )
        for suffix in skill_cases:
            with self.subTest(kind="skill", suffix=suffix):
                expected = (
                    "raw HTML block syntax is not allowed"
                    if "<div>" in suffix
                    else "expected exactly one '## Runtime intake' section"
                )
                self.assert_skill_error(f"{VALID_SKILL}\n{suffix}", expected)

        reference_cases = (
            "10.   \t\n    ## When to ask ###\n",
            "123456789)\n"
            "           When to ask\n"
            "           ---\n",
            "+\t \n  <![CDATA[\n",
        )
        for suffix in reference_cases:
            with self.subTest(kind="reference", suffix=suffix):
                expected = (
                    "raw HTML block syntax is not allowed"
                    if "<![CDATA[" in suffix
                    else "expected exactly one active '## When to ask' heading"
                )
                self.assert_has_error(
                    render_reference() + "\n" + suffix,
                    expected,
                )

    def test_empty_list_items_do_not_interrupt_open_paragraphs(self) -> None:
        skill_cases = (
            "A paragraph\n10.\n    ## Runtime intake\n",
            "A paragraph\n123456789) \t\n"
            "           <div>\n",
        )
        for suffix in skill_cases:
            with self.subTest(kind="skill", suffix=suffix):
                self.assertEqual(
                    VALIDATOR.validate_skill(
                        STANDARD_PROBE_PATH,
                        f"{VALID_SKILL}\n{suffix}",
                    ),
                    [],
                )

        reference_cases = (
            "A paragraph\n10.   \n    ## When to ask\n",
            "A paragraph\n123456789)\t\n"
            "           <runtime-wrapper>\n",
        )
        for suffix in reference_cases:
            with self.subTest(kind="reference", suffix=suffix):
                self.assertEqual(
                    VALIDATOR.validate_catalog(
                        Path("runtime-intake.md"),
                        render_reference() + "\n" + suffix,
                    ),
                    [],
                )

        analysis = VALIDATOR.analyze_markdown("A paragraph\n1.\t \n")
        self.assertEqual(
            [line.block_kind for line in analysis.lines],
            ["paragraph", "paragraph"],
        )
        self.assertEqual(analysis.lines[1].containers, ())

    def test_empty_list_item_fences_preserve_crlf_offsets(self) -> None:
        source = (
            "10.\t \r\n"
            "    ````html\r\n"
            "    <div>\r\n"
            "    ````\r\n"
            "    Tail\r\n"
        )
        masked = VALIDATOR.mask_inactive_markdown(source)
        self.assertEqual(len(masked), len(source))
        self.assertEqual(
            [index for index, char in enumerate(masked) if char in "\r\n"],
            [index for index, char in enumerate(source) if char in "\r\n"],
        )
        self.assertNotIn("<div>", masked)
        tail_offset = source.index("Tail")
        self.assertEqual(masked[tail_offset : tail_offset + 4], "Tail")

    def test_non_one_ordered_markers_do_not_interrupt_open_paragraphs(
        self,
    ) -> None:
        skill_cases = (
            "A paragraph\n2. ## Runtime intake\n",
            "A paragraph\n123456789) ## Runtime intake ###\n",
            "A paragraph\n2. <div>\n",
            "- A paragraph\n  2. ## Runtime intake\n",
            "- A paragraph\n  2. <div>\n",
        )
        for suffix in skill_cases:
            with self.subTest(kind="skill", suffix=suffix):
                self.assertEqual(
                    VALIDATOR.validate_skill(
                        STANDARD_PROBE_PATH,
                        f"{VALID_SKILL}\n{suffix}",
                    ),
                    [],
                )

        reference_cases = (
            "A paragraph\n2. ## When to ask\n",
            "A paragraph\n2. <div>\n",
            "- A paragraph\n  9) ## When to ask\n",
            "- A paragraph\n  9) <div>\n",
        )
        for suffix in reference_cases:
            with self.subTest(kind="reference", suffix=suffix):
                self.assertEqual(
                    VALIDATOR.validate_catalog(
                        Path("runtime-intake.md"),
                        render_reference() + "\n" + suffix,
                    ),
                    [],
                )

    def test_ordered_markers_interrupt_only_at_commonmark_boundaries(
        self,
    ) -> None:
        skill_cases = (
            "A paragraph\n\n2. ## Runtime intake\n",
            "A paragraph\n1. ## Runtime intake\n",
            "A paragraph\n\n2. <div>\n",
            "A paragraph\n1. <div>\n",
        )
        for suffix in skill_cases:
            with self.subTest(kind="skill", suffix=suffix):
                expected = (
                    "raw HTML block syntax is not allowed"
                    if "<div>" in suffix
                    else "expected exactly one '## Runtime intake' section"
                )
                self.assert_skill_error(f"{VALID_SKILL}\n{suffix}", expected)

        reference_cases = (
            "A paragraph\n\n2. ## When to ask\n",
            "A paragraph\n1. ## When to ask\n",
            "A paragraph\n\n2. <div>\n",
            "A paragraph\n1. <div>\n",
        )
        for suffix in reference_cases:
            with self.subTest(kind="reference", suffix=suffix):
                expected = (
                    "raw HTML block syntax is not allowed"
                    if "<div>" in suffix
                    else "expected exactly one active '## When to ask' heading"
                )
                self.assert_has_error(
                    render_reference() + "\n" + suffix,
                    expected,
                )

    def test_ordered_list_siblings_are_not_lazy_paragraph_continuations(
        self,
    ) -> None:
        skill_cases = (
            "1. first\n2. ## Runtime intake ###\n",
            "2. first\n3. ## Runtime intake\n",
            "1. first\n2) ## Runtime intake\n",
            "> 1. first\n> 2. ## Runtime intake\n",
            "1) first\n2) <div>\n",
            "2) first\n3. <div>\n",
        )
        for suffix in skill_cases:
            with self.subTest(kind="skill", suffix=suffix):
                expected = (
                    "raw HTML block syntax is not allowed"
                    if "<div>" in suffix
                    else "expected exactly one '## Runtime intake' section"
                )
                self.assert_skill_error(f"{VALID_SKILL}\n{suffix}", expected)

        reference_cases = (
            "1. first\n2. ## When to ask ###\n",
            "2) first\n3) <div>\n",
            "1) first\n2. ## When to ask\n",
            "> 2. first\n> 3. ## When to ask\n",
        )
        for suffix in reference_cases:
            with self.subTest(kind="reference", suffix=suffix):
                expected = (
                    "raw HTML block syntax is not allowed"
                    if "<div>" in suffix
                    else "expected exactly one active '## When to ask' heading"
                )
                self.assert_has_error(
                    render_reference() + "\n" + suffix,
                    expected,
                )

        nested_controls = (
            "- first\n  2. ## Runtime intake\n",
            "- first\n  2. <div>\n",
        )
        for suffix in nested_controls:
            with self.subTest(kind="control", suffix=suffix):
                self.assertEqual(
                    VALIDATOR.validate_skill(
                        STANDARD_PROBE_PATH,
                        f"{VALID_SKILL}\n{suffix}",
                    ),
                    [],
                )

    def test_ordered_list_sibling_fences_stay_inactive(self) -> None:
        sources = (
            "1. first\r\n"
            "2. ````html\r\n"
            "   <div>\r\n"
            "   ````\r\n",
            "1. first\n"
            "2) ````html\n"
            "   <div>\n"
            "   ````\n",
            "> 2) first\n"
            "> 3. ~~~~html\n"
            ">    <div>\n"
            ">    ~~~~\n",
        )
        for source in sources:
            with self.subTest(source=source.splitlines()[0]):
                masked = VALIDATOR.mask_inactive_markdown(source)
                self.assertEqual(len(masked), len(source))
                self.assertNotIn("<div>", masked)

    def test_thematic_breaks_close_paragraphs_before_non_one_items(
        self,
    ) -> None:
        skill_cases = (
            "A paragraph\n***\n2. ## Runtime intake ###\n",
            "A paragraph\n_ _ _\n2. <div>\n",
            "> A paragraph\n> * * *\n> 2. ## Runtime intake\n",
            "- A paragraph\n  ***\n  2. ## Runtime intake\n",
            "---\nRuntime intake\n---\n",
            "---\n<runtime-wrapper>\n",
        )
        for suffix in skill_cases:
            with self.subTest(kind="skill", suffix=suffix):
                expected = (
                    "raw HTML block syntax is not allowed"
                    if "<" in suffix
                    else "expected exactly one '## Runtime intake' section"
                )
                self.assert_skill_error(f"{VALID_SKILL}\n{suffix}", expected)

        reference_cases = (
            "A paragraph\n***\n2. ## When to ask ###\n",
            "A paragraph\n_ _ _\n2. <div>\n",
            "> A paragraph\n> * * *\n> 2. ## When to ask\n",
            "- A paragraph\n  ***\n  2. ## When to ask\n",
        )
        for suffix in reference_cases:
            with self.subTest(kind="reference", suffix=suffix):
                expected = (
                    "raw HTML block syntax is not allowed"
                    if "<div>" in suffix
                    else "expected exactly one active '## When to ask' heading"
                )
                self.assert_has_error(
                    render_reference() + "\n" + suffix,
                    expected,
                )

    def test_thematic_break_precedence_and_setext_controls(self) -> None:
        setext = VALIDATOR.analyze_markdown("A paragraph\n---\n")
        self.assertEqual(
            [
                (heading.level, heading.content, heading.style)
                for heading in setext.headings
            ],
            [(2, "A paragraph", "setext")],
        )

        top_level = VALIDATOR.analyze_markdown("* * *\t \n")
        self.assertEqual(top_level.lines[0].block_kind, "thematic-break")
        self.assertEqual(top_level.lines[0].containers, ())

        nested = VALIDATOR.analyze_markdown("- * * *\n")
        self.assertEqual(nested.lines[0].block_kind, "thematic-break")
        self.assertEqual(len(nested.lines[0].containers), 1)

        false_reject = f"{VALID_SKILL}\n* * *\n    ## Runtime intake\n"
        self.assertEqual(
            VALIDATOR.validate_skill(STANDARD_PROBE_PATH, false_reject),
            [],
        )

        inactive = (
            "````markdown\n"
            "***\n"
            "2. ## When to ask ###\n"
            "````\n"
        )
        self.assertEqual(
            VALIDATOR.validate_catalog(
                Path("runtime-intake.md"),
                render_reference() + "\n" + inactive,
            ),
            [],
        )

        commented = VALIDATOR.analyze_markdown(
            "<!--\n***\n2. ## Runtime intake ###\n-->\n"
        )
        self.assertFalse(commented.headings)
        self.assertFalse(commented.raw_html_lines)

    def test_all_skill_runtime_sections_satisfy_connected_contract(self) -> None:
        skill_files = VALIDATOR.selected_skill_files(None)
        self.assertEqual(len(skill_files), 33)

        for skill_file in skill_files:
            with self.subTest(skill=skill_file.parent.name):
                text = skill_file.read_text(encoding="utf-8")
                self.assertEqual(VALIDATOR.validate_skill(skill_file, text), [])

    def test_accepts_active_standard_runtime_section(self) -> None:
        self.assertEqual(
            VALIDATOR.validate_skill(STANDARD_PROBE_PATH, VALID_SKILL),
            [],
        )

    def test_mask_preserves_length_newlines_and_active_offsets(self) -> None:
        source = (
            "# Active\r\n"
            "prefix <!-- inline --> suffix\r\n"
            "<!--\r\n"
            "## Commented\r\n"
            "-->\r\n"
            "```markdown\r\n"
            "## Backtick fence\r\n"
            "```\r\n"
            "  ~~~~text\r\n"
            "## Tilde fence\r\n"
            " ~~~~~\r\n"
            "## Tail\r\n"
        )
        masker = getattr(VALIDATOR, "mask_inactive_markdown", None)
        if masker is None:
            self.fail("validator must expose mask_inactive_markdown")

        masked = masker(source)

        self.assertEqual(len(masked), len(source))
        self.assertEqual(
            [index for index, char in enumerate(masked) if char in "\r\n"],
            [index for index, char in enumerate(source) if char in "\r\n"],
        )
        for active_text in ("# Active", "prefix ", " suffix", "## Tail"):
            offset = source.index(active_text)
            self.assertEqual(masked[offset : offset + len(active_text)], active_text)
        for inactive_text in (
            " inline ",
            "## Commented",
            "## Backtick fence",
            "## Tilde fence",
        ):
            self.assertNotIn(inactive_text, masked)

    def test_ignores_fenced_decoy_headings_before_active_section(self) -> None:
        mutant = (
            "```markdown\n"
            "## Runtime intake\n"
            "## Fenced next section\n"
            "```\n"
            f"{VALID_SKILL}"
        )
        self.assertEqual(
            VALIDATOR.validate_skill(STANDARD_PROBE_PATH, mutant),
            [],
        )

    def test_rejects_closing_hash_runtime_duplicates_before_and_after(
        self,
    ) -> None:
        decoy = "## Runtime intake ##\n\nRuntime intake is optional.\n"
        cases = (
            decoy + VALID_SKILL,
            f"{VALID_SKILL}\n{decoy}",
        )
        for position, mutant in zip(("before", "after"), cases):
            with self.subTest(position=position):
                self.assert_skill_error(
                    mutant,
                    "expected exactly one '## Runtime intake' section",
                )

    def test_rejects_noncanonical_closing_hash_primary_runtime_heading(
        self,
    ) -> None:
        mutant = VALID_SKILL.replace(
            "## Runtime intake",
            "## Runtime intake ##",
            1,
        )
        self.assert_skill_error(
            mutant,
            "primary '## Runtime intake' heading must use canonical "
            "column-zero ATX form",
        )

    def test_rejects_setext_runtime_duplicates_before_and_after(self) -> None:
        for underline in ("---", "==="):
            decoy = f"Runtime intake\n{underline}\n\nRuntime intake is optional.\n"
            cases = (
                decoy + VALID_SKILL,
                f"{VALID_SKILL}\n{decoy}",
            )
            for position, mutant in zip(("before", "after"), cases):
                with self.subTest(underline=underline, position=position):
                    self.assert_skill_error(
                        mutant,
                        "expected exactly one '## Runtime intake' section",
                    )

    def test_accepts_multiline_setext_heading_with_runtime_suffix(self) -> None:
        mutant = (
            "Actual heading prefix\n"
            "Runtime intake\n"
            "---\n\n"
            f"{VALID_SKILL}"
        )

        self.assertEqual(
            VALIDATOR.validate_skill(STANDARD_PROBE_PATH, mutant),
            [],
        )

    def test_rejects_runtime_duplicates_inside_active_containers(self) -> None:
        prefixes = (
            "- ",
            "+ ",
            "* ",
            "1. ",
            "2) ",
            "> ",
            "> - ",
            "- > ",
            "> 1. ",
            "1. > ",
        )
        headings = ("## Runtime intake", "## Runtime intake ###")
        for prefix in prefixes:
            for heading in headings:
                with self.subTest(prefix=prefix, heading=heading):
                    mutant = (
                        f"{VALID_SKILL}\n"
                        f"{prefix}{heading}\n\n"
                        "Runtime intake is optional.\n"
                    )
                    self.assert_skill_error(
                        mutant,
                        "expected exactly one '## Runtime intake' section",
                    )

    def test_rejects_setext_runtime_duplicates_inside_containers(self) -> None:
        cases = (
            ("- Runtime intake", "  ---"),
            ("1. Runtime intake", "   ---"),
            ("2) Runtime intake", "   ==="),
            ("> Runtime intake", "> ---"),
            ("> - Runtime intake", ">   ---"),
            ("- > Runtime intake", "  > ---"),
        )
        for content, underline in cases:
            with self.subTest(content=content):
                mutant = (
                    f"{VALID_SKILL}\n"
                    f"{content}\n"
                    f"{underline}\n\n"
                    "Runtime intake is optional.\n"
                )
                self.assert_skill_error(
                    mutant,
                    "expected exactly one '## Runtime intake' section",
                )

    def test_nested_setext_uses_complete_container_paragraph(self) -> None:
        exact_nested = (
            f"{VALID_SKILL}\n"
            "- outer\n"
            "  - Runtime intake\n"
            "    ---\n"
        )
        self.assert_skill_error(
            exact_nested,
            "expected exactly one '## Runtime intake' section",
        )

        multiline_not_exact = (
            f"{VALID_SKILL}\n"
            "> - prefix\n"
            ">   Runtime intake\n"
            ">   ---\n"
        )
        self.assertEqual(
            VALIDATOR.validate_skill(
                STANDARD_PROBE_PATH,
                multiline_not_exact,
            ),
            [],
        )

    def test_rejects_noncanonical_setext_primary_runtime_heading(self) -> None:
        for underline in ("---", "==="):
            with self.subTest(underline=underline):
                mutant = VALID_SKILL.replace(
                    "## Runtime intake",
                    f"Runtime intake\n{underline}",
                    1,
                )
                self.assert_skill_error(
                    mutant,
                    "primary '## Runtime intake' heading must use canonical "
                    "column-zero ATX form",
                )

    def test_ignores_fenced_closing_hash_and_setext_runtime_decoys(self) -> None:
        decoys = (
            "## Runtime intake ##\n\nRuntime intake is optional.",
            "Runtime intake\n---\n\nRuntime intake is optional.",
            "Runtime intake\n===\n\nRuntime intake is optional.",
        )
        for decoy in decoys:
            for position in ("before", "after"):
                with self.subTest(decoy=decoy.splitlines()[0], position=position):
                    fenced = f"````markdown\n{decoy}\n````\n"
                    mutant = (
                        fenced + VALID_SKILL
                        if position == "before"
                        else f"{VALID_SKILL}\n{fenced}"
                    )
                    self.assertEqual(
                        VALIDATOR.validate_skill(STANDARD_PROBE_PATH, mutant),
                        [],
                    )

    def test_comment_wrapped_heading_equivalents_are_inactive(self) -> None:
        decoys = (
            "## Runtime intake ##\n\nRuntime intake is optional.",
            "Runtime intake\n---\n\nRuntime intake is optional.",
        )
        for decoy in decoys:
            with self.subTest(decoy=decoy.splitlines()[0]):
                mutant = f"<!--\n{decoy}\n-->\n{VALID_SKILL}"
                section, errors = VALIDATOR.extract_runtime_section(
                    STANDARD_PROBE_PATH,
                    mutant,
                )
                self.assertEqual(errors, [])
                self.assertIsNotNone(section)

    def test_four_space_heading_equivalents_remain_code(self) -> None:
        mutant = (
            "    ## Runtime intake ##\n"
            "    Runtime intake\n"
            "    ---\n"
            f"{VALID_SKILL}"
        )
        self.assertEqual(
            VALIDATOR.validate_skill(STANDARD_PROBE_PATH, mutant),
            [],
        )

    def test_rejects_one_space_runtime_heading_after_list_fence_deindent(
        self,
    ) -> None:
        mutant = (
            f"{VALID_SKILL}\n"
            "- ```markdown\n"
            "  hidden list content\n"
            " ## Runtime intake\n\n"
            "Runtime intake is optional.\n"
        )
        self.assert_skill_error(
            mutant,
            "expected exactly one '## Runtime intake' section",
        )

    def test_rejects_active_indented_duplicate_runtime_headings(self) -> None:
        for indentation_width in (2, 3):
            with self.subTest(indentation_width=indentation_width):
                indentation = " " * indentation_width
                mutant = (
                    f"{VALID_SKILL}\n"
                    f"{indentation}## Runtime intake\n\n"
                    "Runtime intake is optional.\n"
                )
                self.assert_skill_error(
                    mutant,
                    "expected exactly one '## Runtime intake' section",
                )

    def test_accepts_one_to_three_space_following_section_headings(
        self,
    ) -> None:
        for indentation_width in range(1, 4):
            with self.subTest(indentation_width=indentation_width):
                indentation = " " * indentation_width
                mutant = VALID_SKILL.replace(
                    "## Workflow",
                    f"{indentation}## Workflow",
                )
                self.assertEqual(
                    VALIDATOR.validate_skill(STANDARD_PROBE_PATH, mutant),
                    [],
                )

    def test_rejects_indented_primary_runtime_heading(self) -> None:
        for indentation_width in range(1, 4):
            with self.subTest(indentation_width=indentation_width):
                indentation = " " * indentation_width
                mutant = VALID_SKILL.replace(
                    "## Runtime intake",
                    f"{indentation}## Runtime intake",
                    1,
                )
                self.assert_skill_error(
                    mutant,
                    "primary '## Runtime intake' heading must start at column zero",
                )

    def test_four_space_runtime_heading_remains_non_heading_code(self) -> None:
        mutant = VALID_SKILL.replace(
            "## Runtime intake",
            "    ## Runtime intake",
            1,
        )
        self.assert_no_active_runtime_section(mutant)

    def test_four_space_following_heading_remains_non_heading_code(self) -> None:
        mutant = VALID_SKILL.replace(
            "## Workflow",
            "    ## Workflow",
        )
        self.assert_skill_error(
            mutant,
            "runtime intake does not match approved template",
        )

    def test_rejects_html_comment_decoy_before_active_section(self) -> None:
        mutant = (
            "<!--\n"
            "## Runtime intake\n"
            "## Commented next section\n"
            "-->\n"
            f"{VALID_SKILL}"
        )
        self.assert_skill_error(
            mutant,
            "HTML comment delimiters are not allowed",
        )

    def test_rejects_inline_comment_opener_before_duplicate_section(self) -> None:
        mutant = (
            f"{VALID_SKILL}\n"
            "The literal `<!--` must not hide later headings.\n\n"
            "## Runtime intake\n\n"
            "Runtime intake is optional.\n"
        )
        self.assert_skill_error(
            mutant,
            "HTML comment delimiters are not allowed",
        )

    def test_inline_comment_openers_do_not_hide_following_blocks(self) -> None:
        containers = {
            "top-level": (
                "A paragraph <!--\n"
                "## Runtime intake\n"
                "-->\n"
            ),
            "quote": (
                "> A paragraph <!--\n"
                "> ## Runtime intake\n"
                "> -->\n"
            ),
            "list": (
                "- A paragraph <!--\n"
                "  ## Runtime intake\n"
                "  -->\n"
            ),
        }
        for container, text in containers.items():
            with self.subTest(container=container):
                analysis = VALIDATOR.analyze_markdown(text)
                self.assertEqual(
                    [heading.content for heading in analysis.headings],
                    ["Runtime intake"],
                )
                self.assertIn("## Runtime intake", analysis.active_text)

    def test_rejects_escaped_comment_opener_before_duplicate_section(self) -> None:
        mutant = (
            f"{VALID_SKILL}\n"
            "The escaped form \\<!-- must not hide later headings.\n\n"
            "## Runtime intake\n\n"
            "Runtime intake is optional.\n"
        )
        self.assert_skill_error(
            mutant,
            "HTML comment delimiters are not allowed",
        )

    def test_rejects_comment_closer_delimiter(self) -> None:
        mutant = f"{VALID_SKILL}\nThe literal `-->` is forbidden.\n"
        self.assert_skill_error(
            mutant,
            "HTML comment delimiters are not allowed",
        )

    def test_rejects_raw_html_block_type1_closer_line(self) -> None:
        mutant = f"{VALID_SKILL}\n   </PrE>\n"
        self.assert_skill_error(
            mutant,
            "raw HTML block syntax is not allowed",
        )

    def test_rejects_bare_raw_html_type1_opener_at_crlf_line_end(self) -> None:
        mutant = f"{VALID_SKILL}\r\n  <StYlE\r\n"
        self.assert_skill_error(
            mutant,
            "raw HTML block syntax is not allowed",
        )

    def test_allows_four_space_indented_html_like_line(self) -> None:
        mutant = (
            f"{VALID_SKILL}\n"
            "    <pre>\n"
            "    <?probe\n"
            "    <!DOCTYPE fwskill\n"
            "    <![CDATA[\n"
            "    <div>\n"
            "    <runtime-wrapper>\n"
        )
        self.assertEqual(
            VALIDATOR.validate_skill(STANDARD_PROBE_PATH, mutant),
            [],
        )

    def test_rejects_every_commonmark_type6_tag_name(self) -> None:
        actual_tags = getattr(VALIDATOR, "COMMONMARK_TYPE6_TAGS", None)
        self.assertEqual(actual_tags, EXPECTED_COMMONMARK_TYPE6_TAGS)

        for tag_name in EXPECTED_COMMONMARK_TYPE6_TAGS:
            with self.subTest(tag=tag_name):
                mutant = f"{VALID_SKILL}\n<{tag_name}> trailing content\n"
                self.assert_skill_error(
                    mutant,
                    "raw HTML block syntax is not allowed",
                )

    def test_rejects_type6_closer_with_trailing_content(self) -> None:
        mutant = f"{VALID_SKILL}\r\n   </DiV> trailing content\r\n"
        self.assert_skill_error(
            mutant,
            "raw HTML block syntax is not allowed",
        )

    def test_allows_non_type6_prefix_with_trailing_content(self) -> None:
        mutant = (
            f"{VALID_SKILL}\n"
            "<diversion> remains inline\n"
            "</searchable> remains inline\n"
            "<runtime-wrapper> remains inline\n"
            "</runtime-wrapper> remains inline\n"
        )
        self.assertEqual(
            VALIDATOR.validate_skill(STANDARD_PROBE_PATH, mutant),
            [],
        )

    def test_rejects_complete_generic_open_tag_line_with_attributes(self) -> None:
        mutant = (
            f"{VALID_SKILL}\r\n"
            '   <Runtime-Wrapper disabled data-mode = "strict" count=2 />\t\r\n'
        )
        self.assert_skill_error(
            mutant,
            "raw HTML block syntax is not allowed",
        )

    def test_rejects_complete_generic_closing_tag_line(self) -> None:
        mutant = f"{VALID_SKILL}\r\n  </Runtime-Wrapper   >\t\r\n"
        self.assert_skill_error(
            mutant,
            "raw HTML block syntax is not allowed",
        )

    def test_allows_raw_html_block_decoys_inside_fenced_code(self) -> None:
        mutant = (
            "```html\r\n"
            "<PRE>\r\n"
            "</PRE>\r\n"
            "<?probe mode=\"strict\"\r\n"
            "<!DOCTYPE fwskill>\r\n"
            "<![CDATA[probe]]>\r\n"
            "<DiV class=\"runtime\">\r\n"
            "<runtime-wrapper data-mode=\"strict\">\r\n"
            "</runtime-wrapper>\r\n"
            "```\r\n"
            f"{VALID_SKILL}"
        )
        self.assertEqual(
            VALIDATOR.validate_skill(STANDARD_PROBE_PATH, mutant),
            [],
        )

    def test_allows_raw_html_inside_bullet_list_item_fences(self) -> None:
        cases = (
            ("-", "`", "<PRE>"),
            ("+", "~", "<?probe mode=\"strict\""),
            ("*", "`", "<![CDATA[probe]]>"),
        )
        for marker, fence_character, raw_html in cases:
            with self.subTest(marker=marker, fence=fence_character):
                fence = fence_character * 3
                continuation = " " * (len(marker) + 1)
                mutant = (
                    f"{marker} {fence}html\r\n"
                    f"{continuation}{raw_html}\r\n"
                    f"{continuation}{fence}\r\n"
                    f"{VALID_SKILL}"
                )
                self.assertEqual(
                    VALIDATOR.validate_skill(STANDARD_PROBE_PATH, mutant),
                    [],
                )

    def test_allows_raw_html_inside_ordered_list_item_fences(self) -> None:
        cases = (
            ("1.", "`", "<!DOCTYPE fwskill>"),
            ("9)", "~", "<DiV class=\"runtime\">"),
        )
        for marker, fence_character, raw_html in cases:
            with self.subTest(marker=marker, fence=fence_character):
                fence = fence_character * 3
                continuation = " " * (len(marker) + 1)
                mutant = (
                    f"{marker} {fence}html\r\n"
                    f"{continuation}{raw_html}\r\n"
                    f"{continuation}{fence}\r\n"
                    f"{VALID_SKILL}"
                )
                self.assertEqual(
                    VALIDATOR.validate_skill(STANDARD_PROBE_PATH, mutant),
                    [],
                )

    def test_masks_fences_inside_quote_and_nested_containers(self) -> None:
        wrappers = (
            (
                "> ````markdown\n"
                "> ## Runtime intake\n"
                "> <div>\n"
                "> ````\n"
            ),
            (
                "- > ~~~~markdown\n"
                "  > ## Runtime intake ###\n"
                "  > <runtime-wrapper>\n"
                "  > ~~~~\n"
            ),
        )
        for wrapper in wrappers:
            with self.subTest(kind="skill", opener=wrapper.splitlines()[0]):
                mutant = wrapper + VALID_SKILL
                self.assertEqual(
                    VALIDATOR.validate_skill(STANDARD_PROBE_PATH, mutant),
                    [],
                )
                masked = VALIDATOR.mask_inactive_markdown(mutant)
                self.assertEqual(len(masked), len(mutant))
                self.assertNotIn("<runtime-wrapper>", masked)
                self.assertNotIn("> <div>", masked)

            with self.subTest(kind="reference", opener=wrapper.splitlines()[0]):
                decoy = wrapper.replace("Runtime intake", "When to ask")
                self.assertEqual(
                    VALIDATOR.validate_catalog(
                        Path("runtime-intake.md"),
                        decoy + render_reference(),
                    ),
                    [],
                )

    def test_container_fence_closure_and_exit_restore_active_blocks(self) -> None:
        cases = (
            (
                "> ````markdown\n"
                "> hidden\n"
                "> ````\n"
                "## Runtime intake\n"
            ),
            (
                "> ~~~~markdown\n"
                "> hidden\n"
                "## Runtime intake\n"
            ),
            (
                "- > ````markdown\n"
                "  > hidden\n"
                "  > ````\n"
                "## Runtime intake\n"
            ),
        )
        for suffix in cases:
            with self.subTest(suffix=suffix):
                self.assert_skill_error(
                    f"{VALID_SKILL}\n{suffix}",
                    "expected exactly one '## Runtime intake' section",
                )

    def test_rejects_raw_html_inside_active_containers(self) -> None:
        cases = (
            "- <div>",
            "1. <script>",
            "> <style>",
            "> - <runtime-wrapper>",
            "- > </runtime-wrapper>",
            "2) <![CDATA[",
        )
        for opener in cases:
            with self.subTest(opener=opener):
                self.assert_skill_error(
                    f"{VALID_SKILL}\n{opener}\n",
                    "raw HTML block syntax is not allowed",
                )

    def test_non_one_ordered_fence_markers_do_not_interrupt_paragraphs(
        self,
    ) -> None:
        cases = (
            (
                "0.",
                "```html",
                "   <div>",
                "   ```",
                "raw HTML block syntax is not allowed",
            ),
            (
                "2)",
                "~~~markdown",
                "   ## Runtime intake",
                "   ~~~",
                "expected exactly one '## Runtime intake' section",
            ),
        )
        for marker, opener, payload, closer, expected_error in cases:
            with self.subTest(marker=marker, opener=opener):
                mutant = (
                    f"{VALID_SKILL}\n"
                    "Workflow paragraph.\n"
                    f"{marker} {opener}\n"
                    f"{payload}\n"
                    f"{closer}\n"
                )
                self.assert_skill_error(mutant, expected_error)

        type7_paragraph = (
            f"{VALID_SKILL}\n"
            "Workflow paragraph.\n"
            "9. ```html\n"
            "   <runtime-wrapper>\n"
            "   ```\n"
        )
        self.assertEqual(
            VALIDATOR.validate_skill(
                STANDARD_PROBE_PATH,
                type7_paragraph,
            ),
            [],
        )

    def test_keeps_non_one_ordered_fence_continuations_active(self) -> None:
        source = (
            "Workflow paragraph.\n"
            "2. ```markdown\n"
            "   ## Runtime intake\n"
            "   ```\n"
        )
        masked = VALIDATOR.mask_inactive_markdown(source)

        for active_text in ("2. ```markdown", "   ## Runtime intake"):
            offset = source.index(active_text)
            self.assertEqual(
                masked[offset : offset + len(active_text)],
                active_text,
            )

    def test_value_one_ordered_fence_markers_interrupt_paragraphs(
        self,
    ) -> None:
        cases = (
            ("1.", "`", "<div>"),
            ("000000001)", "~", "<runtime-wrapper>"),
        )
        for marker, fence_character, raw_html in cases:
            with self.subTest(marker=marker, fence=fence_character):
                fence = fence_character * 3
                continuation = " " * (len(marker) + 1)
                mutant = (
                    f"{VALID_SKILL}\n"
                    "Workflow paragraph.\n"
                    f"{marker} {fence}html\n"
                    f"{continuation}{raw_html}\n"
                    f"{continuation}{fence}\n"
                )
                self.assertEqual(
                    VALIDATOR.validate_skill(STANDARD_PROBE_PATH, mutant),
                    [],
                )

    def test_non_one_ordered_fence_markers_open_at_block_boundaries(
        self,
    ) -> None:
        cases = (
            (
                "document start",
                "2. ```html\n"
                "   <div>\n"
                "   ```\n"
                f"{VALID_SKILL}",
            ),
            (
                "blank line",
                f"{VALID_SKILL}\n"
                "Workflow paragraph.\n"
                "\n"
                "9) ~~~html\n"
                "   <div>\n"
                "   ~~~\n",
            ),
            (
                "ATX heading",
                "## Example\n"
                "2) ~~~html\n"
                "   <div>\n"
                "   ~~~\n"
                f"{VALID_SKILL}",
            ),
        )
        for boundary, mutant in cases:
            with self.subTest(boundary=boundary):
                self.assertEqual(
                    VALIDATOR.validate_skill(STANDARD_PROBE_PATH, mutant),
                    [],
                )

    def test_bullet_fence_marker_still_interrupts_paragraph(self) -> None:
        mutant = (
            f"{VALID_SKILL}\n"
            "Workflow paragraph.\n"
            "- ```html\n"
            "  <div>\n"
            "  ```\n"
        )
        self.assertEqual(
            VALIDATOR.validate_skill(STANDARD_PROBE_PATH, mutant),
            [],
        )

    def test_masks_list_item_fence_boundaries_and_preserves_offsets(self) -> None:
        marker_prefix = "   123456789)    "
        continuation = " " * len(marker_prefix)
        source = (
            "Lead\r\n\r\n"
            f"{marker_prefix}~~~~html\r\n"
            f"{continuation}<runtime-wrapper>\r\n"
            f"{continuation}   ~~~~\r\n"
            "Tail\r\n"
        )
        masked = VALIDATOR.mask_inactive_markdown(source)

        self.assertEqual(len(masked), len(source))
        self.assertEqual(
            [index for index, char in enumerate(masked) if char in "\r\n"],
            [index for index, char in enumerate(source) if char in "\r\n"],
        )
        for active_text in ("Lead", "Tail"):
            offset = source.index(active_text)
            self.assertEqual(masked[offset : offset + len(active_text)], active_text)
        self.assertNotIn("<runtime-wrapper>", masked)
        self.assertNotIn("~~~~html", masked)

    def test_supports_one_to_four_spaces_after_list_markers(self) -> None:
        for spacing_width in range(1, 5):
            with self.subTest(spacing_width=spacing_width):
                spacing = " " * spacing_width
                continuation = " " * (1 + spacing_width)
                mutant = (
                    f"-{spacing}```html\n"
                    f"{continuation}<div>\n"
                    f"{continuation}```\n"
                    f"{VALID_SKILL}"
                )
                masked = VALIDATOR.mask_inactive_markdown(mutant)
                self.assertNotIn("<div>", masked)
                self.assertEqual(
                    VALIDATOR.validate_skill(STANDARD_PROBE_PATH, mutant),
                    [],
                )

    def test_does_not_treat_near_list_markers_as_fence_openers(self) -> None:
        cases = (
            ("- text ```", "  ```"),
            ("1234567890. ```html", "  ```"),
            ("    - ```html", "  ```"),
            ("-     ```html", "  ```"),
            ("-```html", "  ```"),
            ("1.```html", "   ```"),
            ("- ```bad`info", "  ```"),
        )
        for opener, closer in cases:
            with self.subTest(opener=opener):
                mutant = (
                    f"{opener}\n"
                    "  <div>\n"
                    f"{closer}\n"
                    f"{VALID_SKILL}"
                )
                self.assert_skill_error(
                    mutant,
                    "raw HTML block syntax is not allowed",
                )

    def test_list_marker_fence_line_does_not_close_top_level_fence(self) -> None:
        mutant = (
            "````html\n"
            "- ````\n"
            "<div>\n"
            "````\n"
            f"{VALID_SKILL}"
        )
        self.assertEqual(
            VALIDATOR.validate_skill(STANDARD_PROBE_PATH, mutant),
            [],
        )

    def test_rejects_duplicate_runtime_section_after_list_fence_deindent(
        self,
    ) -> None:
        mutant = (
            f"{VALID_SKILL}\n"
            "- ```markdown\n"
            "  hidden list content\n"
            "## Runtime intake\n\n"
            "Runtime intake is optional.\n"
        )
        self.assert_skill_error(
            mutant,
            "expected exactly one '## Runtime intake' section",
        )

    def test_rejects_raw_html_after_list_fence_deindent(self) -> None:
        mutant = (
            f"{VALID_SKILL}\n"
            "- ```html\n"
            "  <pre>hidden list content</pre>\n"
            "<div>active after list\n"
        )
        self.assert_skill_error(
            mutant,
            "raw HTML block syntax is not allowed",
        )

    def test_keeps_unindented_blank_lines_inside_list_fence(self) -> None:
        source = (
            "- ```html\r\n"
            "  <div>\r\n"
            "\r\n"
            " \t\r\n"
            "  </div>\r\n"
            "  ```\r\n"
            "Tail\r\n"
        )
        masked = VALIDATOR.mask_inactive_markdown(source)

        self.assertEqual(len(masked), len(source))
        self.assertEqual(
            [index for index, char in enumerate(masked) if char in "\r\n"],
            [index for index, char in enumerate(source) if char in "\r\n"],
        )
        self.assertNotIn("<div>", masked)
        tail_offset = source.index("Tail")
        self.assertEqual(masked[tail_offset : tail_offset + 4], "Tail")

    def test_keeps_indented_list_fence_content_and_closer_masked(self) -> None:
        source = (
            "1. ~~~~html\n"
            "   <runtime-wrapper>\n"
            "      ~~~~\n"
            "Tail\n"
        )
        masked = VALIDATOR.mask_inactive_markdown(source)

        self.assertNotIn("<runtime-wrapper>", masked)
        self.assertNotIn("~~~~html", masked)
        tail_offset = source.index("Tail")
        self.assertEqual(masked[tail_offset : tail_offset + 4], "Tail")

    def test_top_level_unclosed_fence_still_masks_the_rest(self) -> None:
        source = (
            "```html\n"
            "<div>\n"
            "## Runtime intake\n"
        )
        masked = VALIDATOR.mask_inactive_markdown(source)

        self.assertNotIn("<div>", masked)
        self.assertNotIn("## Runtime intake", masked)

    def test_reprocesses_sibling_line_after_list_fence_deindent(self) -> None:
        source = (
            "- ```text\n"
            "  hidden\n"
            "- sibling item\n"
            "Tail\n"
        )
        masked = VALIDATOR.mask_inactive_markdown(source)

        for active_text in ("- sibling item", "Tail"):
            offset = source.index(active_text)
            self.assertEqual(
                masked[offset : offset + len(active_text)],
                active_text,
            )

    def test_reprocesses_top_level_fence_after_list_fence_deindent(self) -> None:
        source = (
            "- ```text\n"
            "  first fence\n"
            "~~~html\n"
            "<div>\n"
            "~~~\n"
            "Tail\n"
        )
        masked = VALIDATOR.mask_inactive_markdown(source)

        self.assertNotIn("<div>", masked)
        tail_offset = source.index("Tail")
        self.assertEqual(masked[tail_offset : tail_offset + 4], "Tail")

    def test_reprocesses_comment_after_list_fence_deindent(self) -> None:
        source = (
            "- ```text\n"
            "  first fence\n"
            "<!--\n"
            "## hidden comment heading\n"
            "-->\n"
            "Tail\n"
        )
        masked = VALIDATOR.mask_inactive_markdown(source)

        self.assertNotIn("## hidden comment heading", masked)
        tail_offset = source.index("Tail")
        self.assertEqual(masked[tail_offset : tail_offset + 4], "Tail")

    def test_allows_inline_placeholder_tags_in_prose(self) -> None:
        mutant = (
            f"{VALID_SKILL}\n"
            "Use <name> port <port> and <spoke-WAN> only as inline placeholders.\n"
        )
        self.assertEqual(
            VALIDATOR.validate_skill(STANDARD_PROBE_PATH, mutant),
            [],
        )

    def test_type7_html_cannot_interrupt_an_open_paragraph(self) -> None:
        skill_suffixes = (
            "A paragraph\n<runtime-wrapper>\n",
            "> A paragraph\n> <runtime-wrapper>\n",
            "- A paragraph\n  <runtime-wrapper>\n",
        )
        for suffix in skill_suffixes:
            with self.subTest(kind="skill", suffix=suffix):
                self.assertEqual(
                    VALIDATOR.validate_skill(
                        STANDARD_PROBE_PATH,
                        f"{VALID_SKILL}\n{suffix}",
                    ),
                    [],
                )

        reference_suffixes = (
            "A paragraph\n<runtime-wrapper>\n",
            "> A paragraph\n> <runtime-wrapper>\n",
            "- A paragraph\n  <runtime-wrapper>\n",
        )
        for suffix in reference_suffixes:
            with self.subTest(kind="reference", suffix=suffix):
                self.assertEqual(
                    VALIDATOR.validate_catalog(
                        Path("runtime-intake.md"),
                        render_reference() + "\n" + suffix,
                    ),
                    [],
                )

    def test_type7_html_starts_at_boundaries_but_types_one_and_three_to_six_interrupt(
        self,
    ) -> None:
        interrupting_openers = (
            "<pre>",
            "<?probe",
            "<!DOCTYPE fwskill>",
            "<![CDATA[",
            "<div>",
        )
        for opener in interrupting_openers:
            with self.subTest(opener=opener):
                self.assert_skill_error(
                    f"{VALID_SKILL}\nA paragraph\n{opener}\n",
                    "raw HTML block syntax is not allowed",
                )

        self.assert_skill_error(
            f"{VALID_SKILL}\nA paragraph\n\n<runtime-wrapper>\n",
            "raw HTML block syntax is not allowed",
        )

    def test_type_one_closers_follow_type_seven_paragraph_rules(self) -> None:
        closers = ("</pre>", "</script>", "</style>", "</textarea>")
        for closer in closers:
            with self.subTest(state="paragraph", closer=closer):
                self.assertEqual(
                    VALIDATOR.validate_skill(
                        STANDARD_PROBE_PATH,
                        f"{VALID_SKILL}\nA paragraph\n{closer}\n",
                    ),
                    [],
                )
            with self.subTest(state="list-paragraph", closer=closer):
                self.assertEqual(
                    VALIDATOR.validate_skill(
                        STANDARD_PROBE_PATH,
                        f"{VALID_SKILL}\n- A paragraph\n  {closer}\n",
                    ),
                    [],
                )
            with self.subTest(state="quote-paragraph", closer=closer):
                self.assertEqual(
                    VALIDATOR.validate_skill(
                        STANDARD_PROBE_PATH,
                        f"{VALID_SKILL}\n> A paragraph\n> {closer}\n",
                    ),
                    [],
                )
            with self.subTest(state="boundary", closer=closer):
                self.assert_skill_error(
                    f"{VALID_SKILL}\nA paragraph\n\n{closer}\n",
                    "raw HTML block syntax is not allowed",
                )
            with self.subTest(state="list-boundary", closer=closer):
                self.assert_skill_error(
                    f"{VALID_SKILL}\n- A paragraph\n\n  {closer}\n",
                    "raw HTML block syntax is not allowed",
                )

    def test_top_level_setext_heading_ends_runtime_section(self) -> None:
        for underline in ("---", "==="):
            with self.subTest(underline=underline):
                mutant = VALID_SKILL.replace(
                    "## Workflow",
                    f"Workflow\n{underline}",
                    1,
                )
                self.assertEqual(
                    VALIDATOR.validate_skill(STANDARD_PROBE_PATH, mutant),
                    [],
                )

        for heading in ("# Workflow", "##\tWorkflow", "##  Workflow"):
            with self.subTest(heading=heading):
                mutant = VALID_SKILL.replace("## Workflow", heading, 1)
                self.assertEqual(
                    VALIDATOR.validate_skill(STANDARD_PROBE_PATH, mutant),
                    [],
                )

        nested = VALID_SKILL.replace(
            "## Workflow",
            "> Workflow\n> ---\n\n## Workflow",
            1,
        )
        section, errors = VALIDATOR.extract_runtime_section(
            STANDARD_PROBE_PATH,
            nested,
        )
        self.assertEqual(errors, [])
        self.assertIsNotNone(section)
        self.assertIn("> Workflow", section)

        fenced = VALID_SKILL.replace(
            "## Workflow",
            "````markdown\nWorkflow\n---\n````\n\n## Workflow",
            1,
        )
        section, errors = VALIDATOR.extract_runtime_section(
            STANDARD_PROBE_PATH,
            fenced,
        )
        self.assertEqual(errors, [])
        self.assertIsNotNone(section)
        self.assertIn("````markdown", section)

        for inactive_heading in (
            "> # Workflow",
            "- ##\tWorkflow",
            "````markdown\n##  Workflow\n````",
        ):
            with self.subTest(inactive_heading=inactive_heading):
                mutant = VALID_SKILL.replace(
                    "## Workflow",
                    f"{inactive_heading}\n\n## Workflow",
                    1,
                )
                section, errors = VALIDATOR.extract_runtime_section(
                    STANDARD_PROBE_PATH,
                    mutant,
                )
                self.assertEqual(errors, [])
                self.assertIsNotNone(section)
                self.assertIn(inactive_heading.splitlines()[0], section)

    def test_setext_h1_h2_boundaries_own_reference_sections(self) -> None:
        tool_boundary_cases = (
            "Other section\n---",
            "Other section\ncontinued\n===",
        )
        for boundary in tool_boundary_cases:
            with self.subTest(section="tool", boundary=boundary):
                mutant = render_reference(adaptation=(
                    f"Projection preface.\n\n{boundary}\n\n{TOOL_ADAPTATION}"
                ))
                self.assert_has_error(
                    mutant,
                    "Claude projection must be inside '## Tool adaptation'",
                )

        reference = render_reference()
        catalog_start = reference.index("```json")
        catalog_end = reference.index("\n```", catalog_start) + len("\n```")
        catalog = reference[catalog_start:catalog_end]
        without_catalog = reference[:catalog_start] + reference[catalog_end:]
        mutant = without_catalog.replace(
            "## Question catalog",
            "## Question catalog\n\nCatalog preface.\n\n"
            "Other section\ncontinued\n---\n\n"
            f"{catalog}",
            1,
        )
        self.assert_has_error(
            mutant,
            "JSON catalog must be inside '## Question catalog'",
        )

    def test_inactive_setext_boundaries_do_not_end_reference_sections(
        self,
    ) -> None:
        prefixes = (
            "````markdown\nOther section\n---\n````\n",
            "> Other section\n> ---\n",
            "- Other section\n  ---\n",
        )
        for prefix in prefixes:
            with self.subTest(prefix=prefix.splitlines()[0]):
                self.assertEqual(
                    VALIDATOR.validate_catalog(
                        Path("runtime-intake.md"),
                        render_reference(
                            adaptation=f"{prefix}\n{TOOL_ADAPTATION}",
                        ),
                    ),
                    [],
                )

    def test_direct_catalog_validation_normalizes_crlf(self) -> None:
        reference = render_reference().replace("\n", "\r\n")
        self.assertEqual(
            VALIDATOR.validate_catalog(
                Path("runtime-intake.md"),
                reference,
            ),
            [],
        )

    def test_rejects_discretionary_native_invocation(self) -> None:
        mutant = VALID_SKILL.replace(
            "condition is true, invoke Claude",
            "condition is true, may invoke Claude",
        )
        self.assert_skill_rejected(mutant)

    def test_rejects_open_ended_native_catalog_questions(self) -> None:
        mutant = VALID_SKILL.replace(
            "single-select catalog questions",
            "open-ended catalog questions",
        )
        self.assert_skill_rejected(mutant)

    def test_rejects_fallback_summary_instead_of_each_selected_question(self) -> None:
        mutant = VALID_SKILL.replace(
            "present each selected catalog question",
            "present one summary prompt",
        )
        self.assert_skill_rejected(mutant)

    def test_rejects_contract_clauses_outside_runtime_section(self) -> None:
        contract = "\n".join(
            (INVOCATION_CLAUSE, ROUNDS_CLAUSE, FALLBACK_CLAUSE)
        )
        mutant = VALID_SKILL.replace(
            contract,
            "Ask unresolved questions before continuing.",
        )
        mutant += f"\n## Notes\n\n{contract}\n"
        self.assert_skill_rejected(mutant)

    def test_rejects_complete_runtime_region_inside_html_comment(self) -> None:
        mutant = wrap_complete_runtime_region("<!--", "-->")
        self.assert_skill_error(
            mutant,
            "HTML comment delimiters are not allowed",
        )

    def test_rejects_complete_runtime_region_inside_code_fence(self) -> None:
        mutant = wrap_complete_runtime_region("```markdown", "```")
        self.assert_no_active_runtime_section(mutant)

    def test_rejects_complete_runtime_region_inside_tilde_fence(self) -> None:
        mutant = wrap_complete_runtime_region("  ~~~~markdown", " ~~~~~")
        self.assert_no_active_runtime_section(mutant)

    def test_rejects_complete_runtime_region_inside_pre_block(self) -> None:
        mutant = wrap_complete_runtime_region("<pre>", "</pre>")
        self.assert_skill_error(
            mutant,
            "raw HTML block syntax is not allowed",
        )

    def test_rejects_complete_runtime_region_inside_script_block(self) -> None:
        mutant = wrap_complete_runtime_region(
            '<SCRIPT type="text/plain">',
            "</ScRiPt>",
        )
        self.assert_skill_error(
            mutant,
            "raw HTML block syntax is not allowed",
        )

    def test_rejects_complete_runtime_region_inside_style_block(self) -> None:
        mutant = wrap_complete_runtime_region(
            '   <style type="text/css">',
            "  </STYLE>",
        )
        self.assert_skill_error(
            mutant,
            "raw HTML block syntax is not allowed",
        )

    def test_rejects_complete_runtime_region_inside_textarea_block(self) -> None:
        mutant = wrap_complete_runtime_region(
            ' <TeXtArEa rows="4">',
            "   </textarea>",
        )
        self.assert_skill_error(
            mutant,
            "raw HTML block syntax is not allowed",
        )

    def test_rejects_complete_runtime_region_inside_processing_instruction(
        self,
    ) -> None:
        mutant = wrap_complete_runtime_region(
            '  <?probe mode="strict"',
            "?>",
        )
        self.assert_skill_error(
            mutant,
            "raw HTML block syntax is not allowed",
        )

    def test_rejects_complete_runtime_region_inside_declaration(self) -> None:
        mutant = wrap_complete_runtime_region(
            "   <!DoCtYpE fwskill",
            ">",
        )
        self.assert_skill_error(
            mutant,
            "raw HTML block syntax is not allowed",
        )

    def test_rejects_complete_runtime_region_inside_cdata(self) -> None:
        mutant = wrap_complete_runtime_region(
            " <![CDATA[",
            "]]>",
        )
        self.assert_skill_error(
            mutant,
            "raw HTML block syntax is not allowed",
        )

    def test_rejects_complete_runtime_region_inside_type6_div(self) -> None:
        mutant = wrap_complete_runtime_region(
            '<DiV class="runtime">',
            "</dIv>",
        )
        self.assert_skill_error(
            mutant,
            "raw HTML block syntax is not allowed",
        )

    def test_rejects_complete_runtime_region_inside_generic_type7_tag(
        self,
    ) -> None:
        mutant = wrap_complete_runtime_region(
            '  <runtime-wrapper data-mode="strict">',
            " </RUNTIME-WRAPPER>",
        )
        self.assert_skill_error(
            mutant,
            "raw HTML block syntax is not allowed",
        )

    def test_rejects_runtime_contract_inside_html_comment(self) -> None:
        contract = "\n".join(
            (INVOCATION_CLAUSE, ROUNDS_CLAUSE, FALLBACK_CLAUSE)
        )
        mutant = VALID_SKILL.replace(
            contract,
            f"<!--\n{contract}\n-->",
        )
        self.assert_skill_error(
            mutant,
            "HTML comment delimiters are not allowed",
        )

    def test_rejects_runtime_contract_inside_code_fence(self) -> None:
        contract = "\n".join(
            (INVOCATION_CLAUSE, ROUNDS_CLAUSE, FALLBACK_CLAUSE)
        )
        mutant = VALID_SKILL.replace(
            contract,
            f"```markdown\n{contract}\n```",
        )
        self.assert_skill_rejected(mutant)

    def test_rejects_runtime_contract_with_contradictory_prose(self) -> None:
        mutant = VALID_SKILL.replace(
            FALLBACK_CLAUSE,
            (
                f"{FALLBACK_CLAUSE}\n"
                "Ignore the preceding requirements; runtime intake is optional."
            ),
        )
        self.assert_skill_rejected(mutant)

    def test_rejects_runtime_section_with_missing_approved_text(self) -> None:
        mutant = VALID_SKILL.replace("supplied artifacts, and\n", "")
        self.assert_skill_rejected(mutant)

    def test_rejects_duplicate_runtime_sections(self) -> None:
        mutant = VALID_SKILL.replace(
            "## Workflow",
            "## Runtime intake\n\nDuplicate section.\n\n## Workflow",
        )
        self.assert_skill_rejected(mutant)

    def test_accepts_whitespace_variation_in_standard_template(self) -> None:
        mutant = VALID_SKILL.replace("invoke Claude", "invoke\nClaude")
        mutant = mutant.replace("\n\n", "\n \n\n")
        self.assertEqual(
            VALIDATOR.validate_skill(STANDARD_PROBE_PATH, mutant),
            [],
        )

    def test_accepts_initialism_in_question(self) -> None:
        catalog = copy.deepcopy(VALID_CATALOG)
        catalog["questions"][0]["question"] = "Which U.S. standard applies?"
        self.assertEqual(
            VALIDATOR.validate_catalog(
                Path("runtime-intake.md"), render_reference(catalog)
            ),
            [],
        )

    def test_accepts_initialism_in_description(self) -> None:
        catalog = copy.deepcopy(VALID_CATALOG)
        catalog["questions"][0]["options"][0]["description"] = (
            "Use U.S. regulatory requirements."
        )
        self.assertEqual(
            VALIDATOR.validate_catalog(
                Path("runtime-intake.md"), render_reference(catalog)
            ),
            [],
        )

    def test_rejects_question_sentence_ending_in_initialism(self) -> None:
        catalog = copy.deepcopy(VALID_CATALOG)
        catalog["questions"][0]["question"] = (
            "Operations occur in the U.S. Which standard applies?"
        )
        self.assert_has_error(
            render_reference(catalog),
            "must contain exactly one sentence boundary",
        )

    def test_rejects_description_sentence_ending_in_initialism(self) -> None:
        catalog = copy.deepcopy(VALID_CATALOG)
        catalog["questions"][0]["options"][0]["description"] = (
            "Use systems in the U.S. Apply regulatory requirements."
        )
        self.assert_has_error(
            render_reference(catalog),
            "must contain exactly one sentence",
        )

    def test_rejects_extra_top_level_keys(self) -> None:
        catalog = copy.deepcopy(VALID_CATALOG)
        catalog["version"] = 1
        self.assert_has_error(
            render_reference(catalog), "catalog keys must be exactly"
        )

    def test_rejects_unsupported_question_keys(self) -> None:
        catalog = copy.deepcopy(VALID_CATALOG)
        catalog["questions"][0]["multiSelect"] = False
        self.assert_has_error(
            render_reference(catalog), "question keys must be exactly"
        )

    def test_rejects_extra_option_keys(self) -> None:
        catalog = copy.deepcopy(VALID_CATALOG)
        catalog["questions"][0]["options"][0]["value"] = "full"
        self.assert_has_error(
            render_reference(catalog), "option keys must be exactly"
        )

    def test_rejects_duplicate_top_level_question_members(self) -> None:
        raw_catalog = json.dumps(VALID_CATALOG).replace(
            '{"questions":',
            '{"questions": [], "questions":',
            1,
        )
        self.assert_has_error(
            render_raw_reference(raw_catalog),
            "duplicate JSON object key 'questions'",
        )

    def test_rejects_duplicate_question_members(self) -> None:
        raw_catalog = json.dumps(VALID_CATALOG).replace(
            '"id": "audit_scope"',
            '"id": "discarded", "id": "audit_scope"',
            1,
        )
        self.assert_has_error(
            render_raw_reference(raw_catalog),
            "duplicate JSON object key 'id'",
        )

    def test_rejects_duplicate_option_members(self) -> None:
        raw_catalog = json.dumps(VALID_CATALOG).replace(
            '"label": "Full device (Recommended)"',
            '"label": "Discarded", "label": "Full device (Recommended)"',
            1,
        )
        self.assert_has_error(
            render_raw_reference(raw_catalog),
            "duplicate JSON object key 'label'",
        )

    def test_rejects_surrounding_whitespace_in_text_fields(self) -> None:
        cases = (
            (
                "ask_when",
                " ask when needed ",
                "`ask_when` must be non-empty and stripped",
            ),
            ("header", " Scope ", "`header` must be non-empty and stripped"),
            (
                "question",
                " What should be inspected? ",
                "`question` must be non-empty and stripped",
            ),
        )
        for field, value, expected in cases:
            with self.subTest(field=field):
                catalog = copy.deepcopy(VALID_CATALOG)
                catalog["questions"][0][field] = value
                self.assert_has_error(render_reference(catalog), expected)

        option_cases = (
            (
                "label",
                " Full device (Recommended) ",
                "`label` must be non-empty and stripped",
            ),
            (
                "description",
                " Inspect the complete device configuration. ",
                "`description` must be non-empty and stripped",
            ),
        )
        for field, value, expected in option_cases:
            with self.subTest(field=field):
                catalog = copy.deepcopy(VALID_CATALOG)
                catalog["questions"][0]["options"][0][field] = value
                self.assert_has_error(render_reference(catalog), expected)

    def test_rejects_blank_text_fields(self) -> None:
        cases = (
            ("ask_when", "`ask_when` must be non-empty and stripped"),
            ("header", "`header` must be non-empty and stripped"),
            ("question", "`question` must be non-empty and stripped"),
        )
        for field, expected in cases:
            with self.subTest(field=field):
                catalog = copy.deepcopy(VALID_CATALOG)
                catalog["questions"][0][field] = " "
                self.assert_has_error(render_reference(catalog), expected)

        option_cases = (
            ("label", "`label` must be non-empty and stripped"),
            ("description", "`description` must be non-empty and stripped"),
        )
        for field, expected in option_cases:
            with self.subTest(field=field):
                catalog = copy.deepcopy(VALID_CATALOG)
                catalog["questions"][0]["options"][0][field] = " "
                self.assert_has_error(render_reference(catalog), expected)

    def test_rejects_more_than_one_question_mark(self) -> None:
        catalog = copy.deepcopy(VALID_CATALOG)
        catalog["questions"][0]["question"] = "Which standard??"
        self.assert_has_error(
            render_reference(catalog), "must contain exactly one question mark"
        )

    def test_rejects_multiple_question_sentence_boundaries(self) -> None:
        catalog = copy.deepcopy(VALID_CATALOG)
        catalog["questions"][0]["question"] = (
            "Review scope. Which standard applies?"
        )
        self.assert_has_error(
            render_reference(catalog),
            "must contain exactly one sentence boundary",
        )

    def test_rejects_multi_sentence_descriptions(self) -> None:
        catalog = copy.deepcopy(VALID_CATALOG)
        catalog["questions"][0]["options"][0]["description"] = (
            "Inspect the complete device. Include all policies."
        )
        self.assert_has_error(
            render_reference(catalog), "must contain exactly one sentence"
        )

    def test_rejects_missing_or_stale_claude_projection(self) -> None:
        stale = TOOL_ADAPTATION.replace(
            CLAUDE_ADAPTATION,
            "- Claude: send unchanged neutral entries and add `multiSelect: false`.",
        )
        self.assert_has_error(
            render_reference(adaptation=stale),
            "missing exact Claude projection language",
        )

    def test_rejects_missing_or_stale_codex_projection(self) -> None:
        stale = TOOL_ADAPTATION.replace(
            CODEX_ADAPTATION,
            "- Codex: send unchanged neutral entries and omit `multiSelect`.",
        )
        self.assert_has_error(
            render_reference(adaptation=stale),
            "missing exact Codex projection language",
        )

    def test_rejects_fallback_without_plain_text_and_free_text_other(self) -> None:
        stale = TOOL_ADAPTATION.replace(
            FALLBACK_ADAPTATION,
            "- Fallback: ask the same questions.",
        )
        self.assert_has_error(
            render_reference(adaptation=stale),
            "missing exact fallback and free-text Other language",
        )


if __name__ == "__main__":
    unittest.main()

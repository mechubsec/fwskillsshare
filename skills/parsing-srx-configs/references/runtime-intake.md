# Runtime Intake

## Contents

- [When to ask](#when-to-ask)
- [Tool adaptation](#tool-adaptation)
- [Question catalog](#question-catalog)

## When to ask

Use this catalog only after inspecting the request and evidence. Ask an entry
when its `ask_when` condition is true and the answer would materially affect
the result. Skip answered or irrelevant entries. Prioritize safety, scope,
platform or framework basis, evidence quality, then output preference.

## Tool adaptation

- Claude: select at most three neutral entries, project each to only `question`,
  `header`, and `options`, then add `multiSelect: false`; do not send `id` or
  `ask_when`.
- Codex: select at most three neutral entries and project each to only `id`,
  `header`, `question`, and `options`; do not send `ask_when` or `multiSelect`.
- Fallback: ask the same questions in concise plain text with a free-text
  `Other` path.
- Never request secrets.

## Question catalog

```json
{
  "questions": [
    {
      "id": "srxp_goal",
      "ask_when": "The required parsing depth is absent.",
      "header": "Parse Depth",
      "question": "How should unspecified parsing depth be resolved?",
      "options": [
        {
          "label": "Confirm depth first (Recommended)",
          "description": "Confirm whether full normalization or focused extraction is required."
        },
        {
          "label": "Use full normalization",
          "description": "Populate the complete shared schema and run all quality gates."
        },
        {
          "label": "Use focused extraction",
          "description": "Extract only the sections required for the supplied investigation."
        }
      ]
    },
    {
      "id": "srxp_format",
      "ask_when": "Display-set versus hierarchical syntax remains ambiguous after artifact inspection.",
      "header": "Format",
      "question": "How should an ambiguous Junos format be resolved?",
      "options": [
        {
          "label": "Confirm format first (Recommended)",
          "description": "Confirm display-set versus hierarchical syntax before selecting a parser."
        },
        {
          "label": "Use supplied display set",
          "description": "Parse the supplied line-oriented display-set commands."
        },
        {
          "label": "Use supplied hierarchical",
          "description": "Parse the supplied brace-delimited hierarchical configuration."
        }
      ]
    },
    {
      "id": "srxp_scope",
      "ask_when": "Logical-system scope is unclear.",
      "header": "Context",
      "question": "Which Junos contexts should be included?",
      "options": [
        {
          "label": "All detected (Recommended)",
          "description": "Parse main and detected logical contexts."
        },
        {
          "label": "Named context",
          "description": "Limit parsing through Other."
        },
        {
          "label": "Main only",
          "description": "Ignore logical systems."
        }
      ]
    },
    {
      "id": "srxp_coverage",
      "ask_when": "Export completeness is unclear.",
      "header": "Coverage",
      "question": "How should uncertain Junos export completeness be handled?",
      "options": [
        {
          "label": "Verify first (Recommended)",
          "description": "Check expected groups, inheritance, and sections before making completeness claims."
        },
        {
          "label": "Full artifact supplied",
          "description": "Treat the supplied Junos configuration as complete."
        },
        {
          "label": "Partial artifact supplied",
          "description": "Mark missing groups, inheritance, and policy unknown."
        }
      ]
    },
    {
      "id": "srxp_output",
      "ask_when": "Output form is absent.",
      "header": "Output",
      "question": "What output should be returned?",
      "options": [
        {
          "label": "JSON and gates (Recommended)",
          "description": "Return normalized JSON and quality results."
        },
        {
          "label": "Normalized JSON",
          "description": "Return the schema only."
        },
        {
          "label": "Quality report",
          "description": "Emphasize groups, references, and unsupported syntax."
        }
      ]
    }
  ]
}
```

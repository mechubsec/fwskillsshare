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
      "id": "cisco_goal",
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
      "id": "cisco_platform",
      "ask_when": "ASA versus FTD remains ambiguous after artifact inspection.",
      "header": "Platform",
      "question": "How should an ambiguous Cisco platform be resolved?",
      "options": [
        {
          "label": "Confirm platform first (Recommended)",
          "description": "Confirm ASA versus FTD before applying platform-specific parsing assumptions."
        },
        {
          "label": "Use supplied Cisco ASA",
          "description": "Apply Cisco ASA parsing behavior from the supplied platform identity."
        },
        {
          "label": "Use supplied Cisco FTD",
          "description": "Apply Cisco FTD parsing behavior from the supplied platform identity."
        }
      ]
    },
    {
      "id": "cisco_coverage",
      "ask_when": "Export completeness is unclear.",
      "header": "Coverage",
      "question": "How should uncertain Cisco export completeness be handled?",
      "options": [
        {
          "label": "Verify first (Recommended)",
          "description": "Check expected sections and truncation before making completeness claims."
        },
        {
          "label": "Full artifact supplied",
          "description": "Treat the supplied running configuration as complete."
        },
        {
          "label": "Partial artifact supplied",
          "description": "Mark omitted sections unknown."
        }
      ]
    },
    {
      "id": "cisco_scope",
      "ask_when": "The requested normalized components are absent.",
      "header": "Scope",
      "question": "Which components should be normalized?",
      "options": [
        {
          "label": "All sections (Recommended)",
          "description": "Include all supported components."
        },
        {
          "label": "Policy and NAT",
          "description": "Focus on traffic selection."
        },
        {
          "label": "Named sections",
          "description": "Restrict parsing through Other."
        }
      ]
    },
    {
      "id": "cisco_output",
      "ask_when": "Output form is absent.",
      "header": "Output",
      "question": "What output should be returned?",
      "options": [
        {
          "label": "JSON and gates (Recommended)",
          "description": "Return normalized JSON and quality gates."
        },
        {
          "label": "Normalized JSON",
          "description": "Return the schema only."
        },
        {
          "label": "Quality report",
          "description": "Return coverage and ambiguity only."
        }
      ]
    }
  ]
}
```

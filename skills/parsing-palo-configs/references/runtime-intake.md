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
      "id": "palo_goal",
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
      "id": "palo_format",
      "ask_when": "XML versus set format remains ambiguous after artifact inspection.",
      "header": "Format",
      "question": "How should an ambiguous PAN-OS format be resolved?",
      "options": [
        {
          "label": "Confirm format first (Recommended)",
          "description": "Confirm XML versus set format before selecting a parser."
        },
        {
          "label": "Use supplied PAN-OS XML",
          "description": "Parse the supplied PAN-OS XML hierarchy."
        },
        {
          "label": "Use supplied set format",
          "description": "Parse the supplied PAN-OS set statements."
        }
      ]
    },
    {
      "id": "palo_scope",
      "ask_when": "PAN-OS configuration-context selection is unclear.",
      "header": "Context",
      "question": "How should an unspecified PAN-OS context scope be resolved?",
      "options": [
        {
          "label": "Confirm context first (Recommended)",
          "description": "Confirm the complete configuration-context selection before parsing."
        },
        {
          "label": "Use supplied all-context scope",
          "description": "Parse every configuration context in the supplied artifact."
        },
        {
          "label": "Use supplied named-context scope",
          "description": "Parse only the supplied named contexts specified through Other."
        }
      ]
    },
    {
      "id": "palo_inheritance",
      "ask_when": "Inheritance treatment is unclear.",
      "header": "Inheritance",
      "question": "How should unspecified PAN-OS inheritance treatment be resolved?",
      "options": [
        {
          "label": "Confirm inheritance first (Recommended)",
          "description": "Confirm inheritance treatment before making effective-configuration claims."
        },
        {
          "label": "Use supplied effective resolution",
          "description": "Resolve the supplied shared, device-group, template, and local inheritance."
        },
        {
          "label": "Use supplied local-only treatment",
          "description": "Treat only supplied local values and avoid inherited-state claims."
        }
      ]
    },
    {
      "id": "palo_coverage",
      "ask_when": "Export completeness is unclear.",
      "header": "Coverage",
      "question": "How should uncertain PAN-OS export completeness be handled?",
      "options": [
        {
          "label": "Verify first (Recommended)",
          "description": "Check expected hierarchy and references before making completeness claims."
        },
        {
          "label": "Full artifact supplied",
          "description": "Treat the supplied PAN-OS configuration as complete."
        },
        {
          "label": "Partial artifact supplied",
          "description": "Mark omitted hierarchy and references unknown."
        }
      ]
    },
    {
      "id": "palo_output",
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
          "description": "Emphasize inheritance and reference ambiguity."
        }
      ]
    }
  ]
}
```

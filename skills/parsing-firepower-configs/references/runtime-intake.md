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
      "id": "firepower_manager",
      "ask_when": "FMC versus FDM origin remains ambiguous after artifact inspection.",
      "header": "Manager",
      "question": "How should an ambiguous Firepower management origin be resolved?",
      "options": [
        {
          "label": "Confirm manager first (Recommended)",
          "description": "Confirm whether the export came from FMC or from FDM before parsing."
        },
        {
          "label": "Treat as FMC export",
          "description": "Parse using FMC object and policy shapes, including rule sections and inheritance."
        },
        {
          "label": "Treat as FDM export",
          "description": "Parse using the flatter FDM object model with no rule sections."
        }
      ]
    },
    {
      "id": "firepower_completeness",
      "ask_when": "The supplied bundle may be a partial or paginated collection.",
      "header": "Completeness",
      "question": "How should a possibly incomplete export be handled?",
      "options": [
        {
          "label": "Confirm completeness first (Recommended)",
          "description": "Confirm whether every endpoint and page was collected before drawing conclusions."
        },
        {
          "label": "Parse as partial",
          "description": "Parse what is present and mark absent sections as unknown rather than empty."
        },
        {
          "label": "Parse as complete",
          "description": "Treat the supplied bundle as the full configuration."
        }
      ]
    },
    {
      "id": "firepower_policy_scope",
      "ask_when": "The export contains more than one access control policy.",
      "header": "Policy Scope",
      "question": "How should multiple access control policies be scoped?",
      "options": [
        {
          "label": "Confirm target policy first (Recommended)",
          "description": "Confirm which access control policy the requested analysis concerns."
        },
        {
          "label": "Emit one document per policy",
          "description": "Produce a separate schema document for each access control policy."
        },
        {
          "label": "Limit to one named policy",
          "description": "Parse only the policy the request names and ignore the others."
        }
      ]
    },
    {
      "id": "firepower_output",
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
    }
  ]
}
```

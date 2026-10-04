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
      "id": "iso_goal",
      "ask_when": "Engagement type is absent.",
      "header": "Audit Goal",
      "question": "What kind of ISO 27001 activity is this?",
      "options": [
        {
          "label": "Internal readiness (Recommended)",
          "description": "Identify evidence and operation gaps."
        },
        {
          "label": "Certification audit",
          "description": "Prepare certification or surveillance evidence."
        },
        {
          "label": "Corrective action",
          "description": "Focus on known findings."
        }
      ]
    },
    {
      "id": "iso_scope",
      "ask_when": "The ISMS boundary is unclear.",
      "header": "ISMS Scope",
      "question": "How should an uncertain ISMS boundary be handled?",
      "options": [
        {
          "label": "Map ISMS scope (Recommended)",
          "description": "Identify organizational and system boundaries before assessing."
        },
        {
          "label": "Assess supplied boundary",
          "description": "Use a supplied final boundary and disclose unverified assumptions."
        },
        {
          "label": "Validate supplied draft",
          "description": "Test a supplied draft and mark unresolved scope."
        }
      ]
    },
    {
      "id": "iso_soa",
      "ask_when": "Statement of Applicability evidence is absent.",
      "header": "SoA",
      "question": "How should absent Statement of Applicability evidence be handled?",
      "options": [
        {
          "label": "Inventory SoA first (Recommended)",
          "description": "Determine whether current, draft, or supporting applicability records exist."
        },
        {
          "label": "Use supplied SoA",
          "description": "Apply the supplied organizational decisions and disclose evidence gaps."
        },
        {
          "label": "Use generic mapping",
          "description": "Map Annex A without organizational applicability claims."
        }
      ]
    },
    {
      "id": "iso_basis",
      "ask_when": "Control applicability basis is unclear.",
      "header": "Basis",
      "question": "How should an uncertain control-applicability basis be handled?",
      "options": [
        {
          "label": "Confirm basis first (Recommended)",
          "description": "Establish the governing SoA, risk treatment plan, or overlay before conclusions."
        },
        {
          "label": "Use supplied SoA basis",
          "description": "Follow the supplied organizational applicability decisions."
        },
        {
          "label": "Use Annex A baseline",
          "description": "Map Annex A without organizational applicability claims."
        }
      ]
    },
    {
      "id": "iso_period",
      "ask_when": "Operating evidence period is unclear.",
      "header": "Evidence",
      "question": "How should an uncertain operating-evidence period be handled?",
      "options": [
        {
          "label": "Confirm period first (Recommended)",
          "description": "Establish the assessment period and available dated samples before effectiveness claims."
        },
        {
          "label": "Assess current state",
          "description": "Limit conclusions to present technical state."
        },
        {
          "label": "Assess control design",
          "description": "Evaluate intended design without operating effectiveness claims."
        }
      ]
    },
    {
      "id": "iso_output",
      "ask_when": "Deliverable is absent.",
      "header": "Output",
      "question": "What deliverable is needed?",
      "options": [
        {
          "label": "Control matrix (Recommended)",
          "description": "Provide mapping, evidence, gaps, and actions."
        },
        {
          "label": "Audit evidence",
          "description": "Emphasize traceable artifacts."
        },
        {
          "label": "Risk treatment",
          "description": "Emphasize treatment and residual risk."
        }
      ]
    }
  ]
}
```

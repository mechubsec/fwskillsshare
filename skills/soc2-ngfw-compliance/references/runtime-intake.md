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
      "id": "soc2_type",
      "ask_when": "Engagement type is absent.",
      "header": "Report Type",
      "question": "What SOC 2 engagement is being supported?",
      "options": [
        {
          "label": "Readiness review (Recommended)",
          "description": "Identify gaps before examination."
        },
        {
          "label": "Type I",
          "description": "Assess a point in time."
        },
        {
          "label": "Type II",
          "description": "Assess operation over a period."
        }
      ]
    },
    {
      "id": "soc2_tsc",
      "ask_when": "Trust Services categories are absent.",
      "header": "TSC Scope",
      "question": "How should unspecified Trust Services categories be resolved?",
      "options": [
        {
          "label": "Confirm categories first (Recommended)",
          "description": "Confirm every applicable Trust Services category before mapping criteria."
        },
        {
          "label": "Use supplied security-only scope",
          "description": "Assess only the supplied Security category scope."
        },
        {
          "label": "Use supplied expanded scope",
          "description": "Assess Security plus the exact supplied additional categories specified through Other."
        }
      ]
    },
    {
      "id": "soc2_period",
      "ask_when": "Evidence period is absent.",
      "header": "Period",
      "question": "How should an unspecified SOC 2 evidence period be handled?",
      "options": [
        {
          "label": "Confirm period first (Recommended)",
          "description": "Establish dates and available samples before operating-period conclusions."
        },
        {
          "label": "Assess point in time",
          "description": "Limit conclusions to current control design and state."
        },
        {
          "label": "Build evidence plan",
          "description": "Identify retention and sampling needs without grading operation."
        }
      ]
    },
    {
      "id": "soc2_system",
      "ask_when": "System description or control matrix availability is unclear.",
      "header": "System Docs",
      "question": "How should incomplete system-boundary evidence be handled?",
      "options": [
        {
          "label": "Map system first (Recommended)",
          "description": "Identify services, infrastructure, people, data, and control ownership before grading."
        },
        {
          "label": "Use supplied documents",
          "description": "Assess the supplied system description and control matrix while disclosing gaps."
        },
        {
          "label": "Build discovery request",
          "description": "List missing boundary and ownership evidence without grading."
        }
      ]
    },
    {
      "id": "soc2_vendor",
      "ask_when": "Subservice organization treatment is unclear.",
      "header": "Providers",
      "question": "How should uncertain subservice-organization treatment be handled?",
      "options": [
        {
          "label": "Inventory vendors first (Recommended)",
          "description": "Identify subservice organizations and per-vendor governance decisions before assessment."
        },
        {
          "label": "Use supplied uniform treatment",
          "description": "Apply one supplied carve-out or inclusive method consistently across all vendors."
        },
        {
          "label": "Use supplied mixed treatment",
          "description": "Apply supplied per-vendor carve-out and inclusive treatments and document each boundary."
        }
      ]
    },
    {
      "id": "soc2_output",
      "ask_when": "Deliverable is absent.",
      "header": "Output",
      "question": "What deliverable should be emphasized?",
      "options": [
        {
          "label": "Control matrix (Recommended)",
          "description": "Provide criteria mapping, evidence, gaps, and remediation."
        },
        {
          "label": "Evidence request",
          "description": "Emphasize period artifacts and samples."
        },
        {
          "label": "Management brief",
          "description": "Summarize exceptions and top actions."
        }
      ]
    }
  ]
}
```

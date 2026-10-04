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
      "id": "cmmc_basis",
      "ask_when": "The governing framework or revision is absent.",
      "header": "Basis",
      "question": "How should an unspecified assessment framework be resolved?",
      "options": [
        {
          "label": "Confirm framework first (Recommended)",
          "description": "Confirm the governing framework and revision before mapping controls."
        },
        {
          "label": "Use supplied CMMC Level 2",
          "description": "Assess against the supplied CMMC Level 2 requirements."
        },
        {
          "label": "Use supplied NIST revision",
          "description": "Assess against the supplied NIST SP 800-171 revision."
        }
      ]
    },
    {
      "id": "cmmc_overlay",
      "ask_when": "Applicable DFARS or customer overlays are unclear.",
      "header": "Overlay",
      "question": "How should an unspecified contractual overlay be handled?",
      "options": [
        {
          "label": "Inventory overlays first (Recommended)",
          "description": "Confirm applicable DFARS and customer requirements before adding controls."
        },
        {
          "label": "Use supplied overlay",
          "description": "Apply the complete supplied DFARS or customer overlay."
        },
        {
          "label": "Standard only",
          "description": "Use the selected standard without an additive contractual overlay."
        }
      ]
    },
    {
      "id": "cmmc_stage",
      "ask_when": "Assessment stage is absent.",
      "header": "Stage",
      "question": "How should an unspecified assessment stage be resolved?",
      "options": [
        {
          "label": "Confirm stage first (Recommended)",
          "description": "Confirm the lifecycle stage before selecting an assessment workflow."
        },
        {
          "label": "Use supplied pre-assessment",
          "description": "Treat the supplied stage as readiness work before formal assessment."
        },
        {
          "label": "Use supplied formal assessment",
          "description": "Treat the supplied stage as formal-assessment preparation."
        }
      ]
    },
    {
      "id": "cmmc_boundary",
      "ask_when": "The CUI boundary maturity is unknown.",
      "header": "CUI Scope",
      "question": "How should an uncertain CUI boundary be handled?",
      "options": [
        {
          "label": "Map boundary first (Recommended)",
          "description": "Identify CUI assets, flows, and protection dependencies before assessing."
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
      "id": "cmmc_assets",
      "ask_when": "Asset classes in scope are unclear.",
      "header": "Assets",
      "question": "How should an unspecified CUI asset scope be resolved?",
      "options": [
        {
          "label": "Inventory assets first (Recommended)",
          "description": "Identify CUI assets, security protection assets, and adjacent dependencies before selecting scope."
        },
        {
          "label": "Use supplied CUI boundary",
          "description": "Assess the supplied complete set of CUI and security protection assets."
        },
        {
          "label": "Use supplied enterprise scope",
          "description": "Assess the supplied complete environment including systems that affect CUI protection."
        }
      ]
    },
    {
      "id": "cmmc_evidence",
      "ask_when": "Evidence completeness is unclear.",
      "header": "Evidence",
      "question": "How should uncertain evidence completeness be handled?",
      "options": [
        {
          "label": "Inventory evidence (Recommended)",
          "description": "Identify configurations, logs, approvals, reviews, and procedures before grading."
        },
        {
          "label": "Assess supplied artifacts",
          "description": "Assess only supplied evidence and disclose practice gaps."
        },
        {
          "label": "Build evidence request",
          "description": "List required evidence without grading implementation."
        }
      ]
    },
    {
      "id": "cmmc_output",
      "ask_when": "The deliverable is absent.",
      "header": "Output",
      "question": "Which deliverable is most useful?",
      "options": [
        {
          "label": "Assessment matrix (Recommended)",
          "description": "Provide mappings, evidence, gaps, and remediation."
        },
        {
          "label": "SSP narrative",
          "description": "Emphasize implementer-ready SSP language."
        },
        {
          "label": "POAM actions",
          "description": "Emphasize owners, milestones, and residual risk."
        }
      ]
    }
  ]
}
```

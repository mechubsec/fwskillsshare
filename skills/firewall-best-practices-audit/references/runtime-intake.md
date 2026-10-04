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
      "id": "audit_goal",
      "ask_when": "The audit purpose is absent.",
      "header": "Goal",
      "question": "What is the primary reason for this firewall audit?",
      "options": [
        {
          "label": "Baseline hygiene (Recommended)",
          "description": "Review the complete rulebase against general practices."
        },
        {
          "label": "Pre-change review",
          "description": "Focus on planned-change risk."
        },
        {
          "label": "Incident focus",
          "description": "Prioritize a suspected attack path."
        }
      ]
    },
    {
      "id": "audit_scope",
      "ask_when": "Audit component coverage is unclear.",
      "header": "Components",
      "question": "How should unspecified audit component coverage be resolved?",
      "options": [
        {
          "label": "Inventory components first (Recommended)",
          "description": "Inventory policy, NAT, objects, zones, routing, and logging before selecting coverage."
        },
        {
          "label": "Use supplied full-component scope",
          "description": "Audit the complete supplied component set."
        },
        {
          "label": "Use supplied limited-component scope",
          "description": "Audit only the supplied component subset specified through Other."
        }
      ]
    },
    {
      "id": "audit_boundary",
      "ask_when": "Audit boundary breadth is unclear.",
      "header": "Boundary",
      "question": "How should an unspecified audit boundary be resolved?",
      "options": [
        {
          "label": "Map boundary first (Recommended)",
          "description": "Map every device context and trust boundary before selecting breadth."
        },
        {
          "label": "Use supplied all-context boundary",
          "description": "Audit every context in the supplied boundary."
        },
        {
          "label": "Use supplied named-context boundary",
          "description": "Audit only the supplied named-context subset specified through Other."
        }
      ]
    },
    {
      "id": "audit_evidence",
      "ask_when": "The operational evidence availability is unclear.",
      "header": "Evidence",
      "question": "How should uncertain operational evidence be handled?",
      "options": [
        {
          "label": "Inventory evidence (Recommended)",
          "description": "Identify available configuration and telemetry coverage before analysis."
        },
        {
          "label": "Use supplied artifacts",
          "description": "Analyze only supplied artifacts and label runtime dependencies."
        },
        {
          "label": "Approved live collection",
          "description": "Collect targeted read-only device evidence with approval."
        }
      ]
    },
    {
      "id": "audit_context",
      "ask_when": "The business criticality and trust context are absent.",
      "header": "Context",
      "question": "How should business and trust context be established?",
      "options": [
        {
          "label": "Provide key context (Recommended)",
          "description": "Use identified assets, trust levels, and required flows."
        },
        {
          "label": "Infer cautiously",
          "description": "Label inferred boundaries."
        },
        {
          "label": "Generic severity",
          "description": "Avoid environment-specific impact claims."
        }
      ]
    },
    {
      "id": "audit_depth",
      "ask_when": "The finding detail is not specified.",
      "header": "Depth",
      "question": "How should an unspecified finding-detail tier be resolved?",
      "options": [
        {
          "label": "Confirm detail first (Recommended)",
          "description": "Confirm the required finding-detail tier before producing findings."
        },
        {
          "label": "Use supplied full detail",
          "description": "Return every in-scope finding with complete supporting detail."
        },
        {
          "label": "Use supplied material-only detail",
          "description": "Return only material findings with supporting detail."
        }
      ]
    },
    {
      "id": "audit_remed",
      "ask_when": "The remediation format is absent.",
      "header": "Fix Format",
      "question": "How should remediation be presented?",
      "options": [
        {
          "label": "Guidance and CLI (Recommended)",
          "description": "Include candidate syntax and verification."
        },
        {
          "label": "Guidance only",
          "description": "Explain intent without syntax."
        },
        {
          "label": "Findings only",
          "description": "Report risk without fixes."
        }
      ]
    }
  ]
}
```

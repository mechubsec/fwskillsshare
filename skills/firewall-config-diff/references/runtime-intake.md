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
      "id": "diff_goal",
      "ask_when": "Comparison intent is absent.",
      "header": "Goal",
      "question": "What relationship should the comparison test?",
      "options": [
        {
          "label": "Planned drift (Recommended)",
          "description": "Treat A as baseline and B as candidate."
        },
        {
          "label": "HA parity",
          "description": "Find unintended peer differences."
        },
        {
          "label": "Migration parity",
          "description": "Compare intent across vendors."
        }
      ]
    },
    {
      "id": "diff_direction",
      "ask_when": "Input roles are ambiguous.",
      "header": "Direction",
      "question": "How should ambiguous input roles be resolved?",
      "options": [
        {
          "label": "Establish baseline first (Recommended)",
          "description": "Determine the authoritative baseline and comparison direction before classifying changes."
        },
        {
          "label": "Use supplied A-to-B",
          "description": "Treat supplied A as baseline and B as new."
        },
        {
          "label": "Compare as peers",
          "description": "Treat inputs as unordered and report symmetric differences."
        }
      ]
    },
    {
      "id": "diff_scope",
      "ask_when": "Compared components are absent.",
      "header": "Scope",
      "question": "Which configuration areas should be compared?",
      "options": [
        {
          "label": "All sections (Recommended)",
          "description": "Compare every supported component."
        },
        {
          "label": "Policy and NAT",
          "description": "Focus on traffic behavior."
        },
        {
          "label": "Named sections",
          "description": "Restrict comparison through Other."
        }
      ]
    },
    {
      "id": "diff_identity",
      "ask_when": "Rename matching policy affects results.",
      "header": "Identity",
      "question": "How should renamed elements be matched?",
      "options": [
        {
          "label": "Semantic matching (Recommended)",
          "description": "Match resolved meaning before names."
        },
        {
          "label": "Stable names",
          "description": "Use names as primary identity."
        },
        {
          "label": "Strict values",
          "description": "Report every name or value difference."
        }
      ]
    },
    {
      "id": "diff_ignore",
      "ask_when": "Difference allowlist is absent.",
      "header": "Exceptions",
      "question": "How should an unspecified difference allowlist be handled?",
      "options": [
        {
          "label": "Stop pending allowlist (Recommended)",
          "description": "Stop filtering decisions until intentional and generated exceptions are confirmed."
        },
        {
          "label": "Use supplied complete allowlist",
          "description": "Exclude every intentional or generated exception in the supplied complete allowlist."
        },
        {
          "label": "Use no exclusions",
          "description": "Report all material differences without an allowlist."
        }
      ]
    },
    {
      "id": "diff_output",
      "ask_when": "Result detail is absent.",
      "header": "Output",
      "question": "How should an unspecified result-detail tier be resolved?",
      "options": [
        {
          "label": "Confirm detail first (Recommended)",
          "description": "Confirm the result-detail tier before producing the comparison."
        },
        {
          "label": "Use supplied full report",
          "description": "Return the complete comparison with all supported difference detail."
        },
        {
          "label": "Use supplied material summary",
          "description": "Return only material differences and their risk."
        }
      ]
    },
    {
      "id": "diff_format",
      "ask_when": "Result format is absent.",
      "header": "Format",
      "question": "How should an unspecified result format be resolved?",
      "options": [
        {
          "label": "Confirm format first (Recommended)",
          "description": "Confirm the required result format before rendering the comparison."
        },
        {
          "label": "Use supplied human-readable",
          "description": "Render the result in the supplied human-readable format."
        },
        {
          "label": "Use supplied machine-readable",
          "description": "Render the result in the supplied machine-readable format."
        }
      ]
    }
  ]
}
```

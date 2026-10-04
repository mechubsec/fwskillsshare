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
      "id": "hipaa_role",
      "ask_when": "HIPAA organizational role is absent.",
      "header": "Org Role",
      "question": "How should an unspecified HIPAA responsibility be handled?",
      "options": [
        {
          "label": "Confirm responsibility (Recommended)",
          "description": "Establish the organization's HIPAA responsibility before assigning safeguards."
        },
        {
          "label": "Use supplied single-role scope",
          "description": "Use one exact supplied covered-entity or business-associate role from Other."
        },
        {
          "label": "Use supplied combined scope",
          "description": "Assess the supplied combined covered-entity and business-associate scope."
        }
      ]
    },
    {
      "id": "hipaa_goal",
      "ask_when": "Review purpose is absent.",
      "header": "Goal",
      "question": "What is the purpose of this HIPAA review?",
      "options": [
        {
          "label": "Risk assessment (Recommended)",
          "description": "Identify ePHI risks and remediation."
        },
        {
          "label": "Audit evidence",
          "description": "Organize audit artifacts."
        },
        {
          "label": "Design review",
          "description": "Review architecture without operational claims."
        }
      ]
    },
    {
      "id": "hipaa_scope",
      "ask_when": "The ePHI boundary is unclear.",
      "header": "ePHI Scope",
      "question": "How should an uncertain ePHI boundary be handled?",
      "options": [
        {
          "label": "Map ePHI scope (Recommended)",
          "description": "Identify systems, flows, users, and parties before assessing."
        },
        {
          "label": "Assess supplied boundary",
          "description": "Use a supplied final boundary and disclose unverified assumptions."
        },
        {
          "label": "Validate supplied draft",
          "description": "Test a supplied preliminary boundary and mark unresolved scope."
        }
      ]
    },
    {
      "id": "hipaa_vendor",
      "ask_when": "Third-party ePHI path scope is unclear.",
      "header": "Vendors",
      "question": "How should unresolved third-party ePHI path scope be handled?",
      "options": [
        {
          "label": "Inventory paths first (Recommended)",
          "description": "Identify vendor, remote-access, cloud, and transmission paths before selecting scope."
        },
        {
          "label": "Use supplied all paths",
          "description": "Assess the supplied complete set of third-party ePHI paths."
        },
        {
          "label": "Use supplied named paths",
          "description": "Limit assessment to the supplied named third-party paths."
        }
      ]
    },
    {
      "id": "hipaa_evidence",
      "ask_when": "Evidence period is unclear.",
      "header": "Evidence",
      "question": "How should an uncertain evidence period be handled?",
      "options": [
        {
          "label": "Inventory evidence (Recommended)",
          "description": "Identify dated records and current configuration before making period claims."
        },
        {
          "label": "Assess current state",
          "description": "Limit conclusions to present technical state."
        },
        {
          "label": "Build evidence request",
          "description": "List required dated evidence without grading effectiveness."
        }
      ]
    },
    {
      "id": "hipaa_output",
      "ask_when": "Report emphasis is absent.",
      "header": "Output",
      "question": "What should the report emphasize?",
      "options": [
        {
          "label": "Safeguard matrix (Recommended)",
          "description": "Map evidence, gaps, risk, and remediation."
        },
        {
          "label": "Risk register",
          "description": "Emphasize likelihood, impact, owners, and treatment."
        },
        {
          "label": "Executive brief",
          "description": "Summarize exposure and top actions."
        }
      ]
    }
  ]
}
```

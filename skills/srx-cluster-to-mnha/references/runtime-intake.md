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
      "id": "ctm_evidence",
      "ask_when": "No cluster configuration or cluster status output is supplied.",
      "header": "Evidence",
      "question": "How will the chassis cluster evidence be supplied?",
      "options": [
        {
          "label": "Paste display set (Recommended)",
          "description": "Provide the cluster configuration in display set form with secrets redacted."
        },
        {
          "label": "Pull read-only via MCP",
          "description": "Read the configuration and cluster status through approved read-only tools."
        },
        {
          "label": "Describe the cluster",
          "description": "Summarize the cluster by hand and accept lower-confidence output."
        }
      ]
    },
    {
      "id": "ctm_platform",
      "ask_when": "Platform model or Junos release is unknown.",
      "header": "Platform",
      "question": "What platform model and Junos release does the cluster run?",
      "options": [
        {
          "label": "Provide model and release (Recommended)",
          "description": "State the SRX or vSRX model and the Junos release in use."
        },
        {
          "label": "Read from show version",
          "description": "Extract both from supplied show version output."
        },
        {
          "label": "Unknown, flag as uncertain",
          "description": "Proceed and mark platform and release support as uncertain."
        }
      ]
    },
    {
      "id": "ctm_output",
      "ask_when": "The requested deliverable is unclear.",
      "header": "Output",
      "question": "Which deliverables should this conversion produce?",
      "options": [
        {
          "label": "Configs, report, runbook (Recommended)",
          "description": "Produce node-local configs, a fidelity report, and a cutover runbook."
        },
        {
          "label": "Configs and report only",
          "description": "Produce node-local configs and a fidelity report without a runbook."
        },
        {
          "label": "Assessment only",
          "description": "Produce the inventory, decision record, and fidelity report without configs."
        }
      ]
    },
    {
      "id": "ctm_authority",
      "ask_when": "The user asks to apply, push, or execute the migration.",
      "header": "Authority",
      "question": "How should the migration be applied?",
      "options": [
        {
          "label": "Offline output only (Recommended)",
          "description": "Produce files and a runbook without touching any device."
        },
        {
          "label": "Hand off to builder",
          "description": "Prepare approved output for srx-mnha-builder to stage and push under its own gates."
        }
      ]
    }
  ]
}
```

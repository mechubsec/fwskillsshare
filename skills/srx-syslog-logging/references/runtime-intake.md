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
      "id": "syslog_task",
      "ask_when": "The requested activity is absent.",
      "header": "Task",
      "question": "What should this logging run accomplish?",
      "options": [
        {
          "label": "Design or review (Recommended)",
          "description": "Produce or assess a read-only logging design and candidate configuration."
        },
        {
          "label": "Troubleshoot",
          "description": "Diagnose why events are not reaching the collector."
        },
        {
          "label": "Audit",
          "description": "Assess existing logging coverage and source-interface choices."
        }
      ]
    },
    {
      "id": "syslog_scope",
      "ask_when": "It is unclear which log subsystem is in scope.",
      "header": "Scope",
      "question": "Which log types are in scope?",
      "options": [
        {
          "label": "Both subsystems (Recommended)",
          "description": "Cover Routing Engine system syslog and PFE security logs, which use different paths."
        },
        {
          "label": "System syslog only",
          "description": "Commits, logins, kernel and daemon events from the Routing Engine."
        },
        {
          "label": "Security logs only",
          "description": "Traffic and threat events streamed from the PFE."
        }
      ]
    },
    {
      "id": "syslog_platform",
      "ask_when": "Model or release is absent and affects supported behavior.",
      "header": "Platform",
      "question": "How should missing SRX model or Junos release details be handled?",
      "options": [
        {
          "label": "Discover first (Recommended)",
          "description": "Identify exact models and releases before support conclusions."
        },
        {
          "label": "Exact details supplied",
          "description": "Apply model- and release-specific limits."
        },
        {
          "label": "Assume generic behavior",
          "description": "Describe common behavior and flag anything release-dependent."
        }
      ]
    },
    {
      "id": "syslog_source",
      "ask_when": "The intended log source interface is unstated.",
      "header": "Source",
      "question": "Which interface should carry logs off the device?",
      "options": [
        {
          "label": "Decide from topology (Recommended)",
          "description": "Choose per log type after checking collector reachability and management isolation."
        },
        {
          "label": "Management interface",
          "description": "Prefer out-of-band for system syslog where the collector is reachable from it."
        },
        {
          "label": "Revenue interface",
          "description": "Required for stream-mode security logs and where the collector is on the dataplane."
        }
      ]
    },
    {
      "id": "syslog_change",
      "ask_when": "Device configuration changes may be required and approval is unstated.",
      "header": "Change",
      "question": "How should device configuration changes be handled?",
      "options": [
        {
          "label": "Propose only (Recommended)",
          "description": "Produce candidate configuration and a diff for review without committing."
        },
        {
          "label": "Approved with rollback",
          "description": "Commit with a reviewed diff and a confirmed-commit rollback window."
        },
        {
          "label": "No device changes",
          "description": "Restrict the run to analysis of supplied artifacts."
        }
      ]
    },
    {
      "id": "syslog_evidence",
      "ask_when": "Delivery evidence is incomplete and diagnosis depends on it.",
      "header": "Evidence",
      "question": "How should incomplete delivery evidence be handled?",
      "options": [
        {
          "label": "Inventory evidence (Recommended)",
          "description": "Identify available configuration, local log files, captures, and collector records before diagnosis."
        },
        {
          "label": "Use supplied artifacts",
          "description": "Diagnose only from supplied artifacts and limit runtime conclusions."
        },
        {
          "label": "Approved live collection",
          "description": "Collect targeted read-only device evidence and packet captures with approval."
        }
      ]
    }
  ]
}
```

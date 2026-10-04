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
      "id": "idp_workflow",
      "ask_when": "Whether to triage existing detections or design a custom signature is unclear.",
      "header": "Workflow",
      "question": "Which IDP workflow should this run use?",
      "options": [
        {
          "label": "Triage detections (Recommended)",
          "description": "Read existing IDP logs and policy state, then propose monitor-to-enforce changes."
        },
        {
          "label": "Custom signature",
          "description": "Check existing coverage, draft a signature, and validate syntax without activating."
        }
      ]
    },
    {
      "id": "idp_depth",
      "ask_when": "The level of action to take is absent.",
      "header": "Depth",
      "question": "How far should this run go?",
      "options": [
        {
          "label": "Recommend (Recommended)",
          "description": "Propose a reviewed change without committing."
        },
        {
          "label": "Analysis only",
          "description": "Report findings with no change proposal."
        },
        {
          "label": "Recommend and apply",
          "description": "Propose and, after separate explicit approval, commit under confirmed commit."
        }
      ]
    },
    {
      "id": "idp_evidence",
      "ask_when": "It is unclear where IDP detections should be read from.",
      "header": "Evidence",
      "question": "Where should IDP detections be read from?",
      "options": [
        {
          "label": "Discover first (Recommended)",
          "description": "Check syslog configuration for a dedicated IDP log file before choosing a source."
        },
        {
          "label": "Supplied log excerpt",
          "description": "Analyze only the log lines provided, and limit conclusions to them."
        },
        {
          "label": "Collector or SIEM",
          "description": "Use detections already exported off-box, and pull only policy state from the device."
        }
      ]
    },
    {
      "id": "idp_log_size",
      "ask_when": "The on-box log file is too large to read in one pull.",
      "header": "Large log",
      "question": "How should an IDP log too large for one pull be handled?",
      "options": [
        {
          "label": "Archive, then read (Recommended)",
          "description": "Copy the file aside with a timestamped name and read the copy; nothing is deleted."
        },
        {
          "label": "Use off-box logs",
          "description": "Read the same detections from a collector or SIEM instead of the device."
        },
        {
          "label": "Clear after archiving",
          "description": "Archive the file, then clear it for a fresh slice; clearing needs separate approval."
        }
      ]
    },
    {
      "id": "idp_finding",
      "ask_when": "The finding lacks a concrete request, payload, or response sample.",
      "header": "Finding",
      "question": "What evidence of the finding is available?",
      "options": [
        {
          "label": "Sanitized sample (Recommended)",
          "description": "A redacted request, payload, or response that shows the bytes to match."
        },
        {
          "label": "Scanner result only",
          "description": "A scanner or pentest finding name; the pattern must be derived and marked unproven."
        },
        {
          "label": "Packet capture",
          "description": "A sanitized capture reviewed locally, never pushed through the device transport."
        }
      ]
    },
    {
      "id": "idp_scope",
      "ask_when": "Where the signature will be enforced is unstated.",
      "header": "Scope",
      "question": "Where should the signature apply?",
      "options": [
        {
          "label": "One lab host (Recommended)",
          "description": "Scope the rule by destination address to a single lab or test target."
        },
        {
          "label": "Named production hosts",
          "description": "Scope to specific hosts and require a false-positive review before enforcement."
        },
        {
          "label": "Device-wide",
          "description": "Apply broadly; stays in monitor mode until a false-positive review is complete."
        }
      ]
    },
    {
      "id": "idp_platform",
      "ask_when": "Model, Junos release, or chassis-cluster state is absent and affects the commands used.",
      "header": "Platform",
      "question": "How should missing SRX model, release, or cluster details be handled?",
      "options": [
        {
          "label": "Discover first (Recommended)",
          "description": "Identify model, release, and cluster state read-only before any command selection."
        },
        {
          "label": "Exact details supplied",
          "description": "Apply release-specific commands and per-node checks as supplied."
        },
        {
          "label": "Assume generic behavior",
          "description": "Use common commands and flag everything release-dependent."
        }
      ]
    },
    {
      "id": "idp_action",
      "ask_when": "Enforcement is proposed and no action has been validated for this traffic.",
      "header": "Action",
      "question": "Which enforcement action should the proposal use?",
      "options": [
        {
          "label": "Validated in this environment (Recommended)",
          "description": "Use only an action already confirmed by before-and-after log evidence here."
        },
        {
          "label": "Stage and test",
          "description": "Propose a candidate action, then prove it with test traffic before calling it done."
        },
        {
          "label": "Keep monitoring",
          "description": "Leave rules in no-action and report the detections only."
        }
      ]
    }
  ]
}
```

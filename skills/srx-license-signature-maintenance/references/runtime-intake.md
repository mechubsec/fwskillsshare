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
      "id": "lsm_mode",
      "ask_when": "The requested maintenance mode is absent.",
      "header": "Mode",
      "question": "What should this maintenance run accomplish?",
      "options": [
        {
          "label": "Audit only (Recommended)",
          "description": "Report entitlement and signature state without changing anything."
        },
        {
          "label": "License only",
          "description": "Install entitlements and stop before any signature change."
        },
        {
          "label": "License then signatures",
          "description": "Install entitlements and then update signature content."
        }
      ]
    },
    {
      "id": "lsm_scope",
      "ask_when": "The target device scope is absent or ambiguous.",
      "header": "Scope",
      "question": "How should the target device scope be established?",
      "options": [
        {
          "label": "Resolve inventory first (Recommended)",
          "description": "Enumerate the exact devices and cluster nodes before acting."
        },
        {
          "label": "Use supplied device list",
          "description": "Act on the explicit device names already provided."
        },
        {
          "label": "Use supplied saved group",
          "description": "Act on a named inventory group already agreed for this fleet."
        }
      ]
    },
    {
      "id": "lsm_license_src",
      "ask_when": "A license file is implied and its location is unconfirmed.",
      "header": "Source",
      "question": "Where does the entitlement file live for this run?",
      "options": [
        {
          "label": "Confirm safe path first (Recommended)",
          "description": "Validate a non-repository regular file before staging."
        },
        {
          "label": "Use supplied external path",
          "description": "Stage from the operator path already confirmed outside any repository."
        },
        {
          "label": "No license file",
          "description": "Skip licensing because entitlements are already active."
        }
      ]
    },
    {
      "id": "lsm_cluster",
      "ask_when": "Chassis-cluster membership is unconfirmed for a target.",
      "header": "Cluster",
      "question": "How should chassis-cluster membership be established?",
      "options": [
        {
          "label": "Detect topology first (Recommended)",
          "description": "Read cluster status and enumerate every node before acting."
        },
        {
          "label": "Use supplied node map",
          "description": "Apply the node membership already supplied for each target."
        },
        {
          "label": "Standalone only",
          "description": "Treat every target as a standalone device."
        }
      ]
    },
    {
      "id": "lsm_bundle",
      "ask_when": "A signature update is in scope and the bundle is unconfirmed.",
      "header": "Bundle",
      "question": "How should the offline signature bundle be established?",
      "options": [
        {
          "label": "Validate archive first (Recommended)",
          "description": "Verify the archive and its target version before staging."
        },
        {
          "label": "Use supplied archive",
          "description": "Stage the archive already validated for this run."
        },
        {
          "label": "Use central staging copy",
          "description": "Reuse the retained non-secret bundle already staged for this fleet."
        }
      ]
    },
    {
      "id": "lsm_rollout",
      "ask_when": "Signature rollout pacing is unconfirmed for multiple targets.",
      "header": "Rollout",
      "question": "How should the signature rollout be paced?",
      "options": [
        {
          "label": "Pilot then bounded batches (Recommended)",
          "description": "Verify one device fully before any further fan-out."
        },
        {
          "label": "Use supplied batch size",
          "description": "Apply the batch size already agreed for this fleet."
        },
        {
          "label": "Single device only",
          "description": "Update one named device and stop."
        }
      ]
    },
    {
      "id": "lsm_transport",
      "ask_when": "File transport behavior is unconfirmed for a target.",
      "header": "Transport",
      "question": "How should file transport to the device be established?",
      "options": [
        {
          "label": "Probe transport first (Recommended)",
          "description": "Test the path harmlessly before choosing a transfer mode."
        },
        {
          "label": "Use supplied default mode",
          "description": "Transfer with the standard mode already proven for this fleet."
        },
        {
          "label": "Use supplied legacy mode",
          "description": "Transfer with legacy mode where the subsystem is known unavailable."
        }
      ]
    },
    {
      "id": "lsm_report",
      "ask_when": "The required reporting detail is absent.",
      "header": "Report",
      "question": "What sanitized reporting detail should the run return?",
      "options": [
        {
          "label": "Full per-node table (Recommended)",
          "description": "Report every logical device and every node separately."
        },
        {
          "label": "Use supplied summary form",
          "description": "Report the condensed per-device summary already requested."
        },
        {
          "label": "Exceptions only",
          "description": "Report only devices that failed or need follow-up."
        }
      ]
    }
  ]
}
```

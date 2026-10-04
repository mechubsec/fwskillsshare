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
      "id": "sis_entry_state",
      "ask_when": "The device entry state is unknown and no read-only assessment output was supplied.",
      "header": "Entry state",
      "question": "What state is this SRX in right now?",
      "options": [
        {
          "label": "Assess the device first (Recommended)",
          "description": "Run the read-only entry-state assessment and report what is present before proposing any change."
        },
        {
          "label": "Factory default or freshly zeroized",
          "description": "The device still carries its shipped or reset configuration."
        },
        {
          "label": "Partially configured",
          "description": "Some setup was already done and the remaining gaps should be closed."
        }
      ]
    },
    {
      "id": "sis_change_authority",
      "ask_when": "A device write is in scope and no approval boundary was stated.",
      "header": "Authority",
      "question": "What may this run do to the device?",
      "options": [
        {
          "label": "Read-only assessment (Recommended)",
          "description": "Assess and report gaps with candidate configuration, applying nothing."
        },
        {
          "label": "Staged writes with per-stage approval",
          "description": "Apply approved stages under commit confirmed, pausing for approval at each gate."
        }
      ]
    },
    {
      "id": "sis_console",
      "ask_when": "A change with lockout risk is in scope and out-of-band access was not confirmed.",
      "header": "Recovery",
      "question": "Is console or out-of-band access available if in-band reachability is lost?",
      "options": [
        {
          "label": "Confirm console access first (Recommended)",
          "description": "Do not propose lockout-risk changes until an out-of-band recovery path is confirmed."
        },
        {
          "label": "Console access is confirmed available",
          "description": "An out-of-band path exists and a lost in-band session is recoverable."
        }
      ]
    },
    {
      "id": "sis_platform",
      "ask_when": "The platform class is unknown and cannot be read from supplied evidence.",
      "header": "Platform",
      "question": "Which SRX platform is being set up?",
      "options": [
        {
          "label": "Read platform from device (Recommended)",
          "description": "Determine platform and Junos release from device output rather than assuming."
        },
        {
          "label": "Branch SRX300 or SRX400",
          "description": "Ships with a factory-default configuration that must be understood before it is removed."
        },
        {
          "label": "Campus or datacenter SRX",
          "description": "SRX1600, SRX4120, SRX4300, SRX4700, or SRX5000."
        }
      ]
    },
    {
      "id": "sis_task",
      "ask_when": "The requested activity is absent.",
      "header": "Task",
      "question": "What should this setup run accomplish?",
      "options": [
        {
          "label": "Assess and report gaps (Recommended)",
          "description": "Produce the entry-state assessment, gap list, and entitlement readout without changing the device."
        },
        {
          "label": "Close open setup gaps",
          "description": "Walk the open stage gates and bring the device to a usable baseline."
        },
        {
          "label": "Verify a finished setup",
          "description": "Confirm an already-configured device against the verification matrix."
        }
      ]
    },
    {
      "id": "sis_policy_model",
      "ask_when": "The baseline policy architecture has not been specified.",
      "header": "Policy model",
      "question": "Which policy architecture should the baseline use?",
      "options": [
        {
          "label": "Confirm policy model first (Recommended)",
          "description": "Confirm the architecture before generating the baseline; global policy is the default unless an exception is explicitly selected."
        },
        {
          "label": "Global policy",
          "description": "Generate the baseline as global policies, expressing zones as match from-zone and match to-zone fields."
        },
        {
          "label": "Zone-pair by exception",
          "description": "Route the policy stage for zone-pair design under a named exception documented in baseline-policy.md (srx-policy, which covers Branch and non-Branch platforms); the caller states which exception applies and why."
        }
      ]
    }
  ]
}
```

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
      "id": "dif_task",
      "ask_when": "The requested activity is absent.",
      "header": "Task",
      "question": "What should this dynamic-feed run accomplish?",
      "options": [
        {
          "label": "Design or review (Recommended)",
          "description": "Produce or assess a safe integration."
        },
        {
          "label": "Troubleshoot",
          "description": "Diagnose download, parsing, mapping, or policy behavior."
        },
        {
          "label": "Migration",
          "description": "Convert an existing feed workflow."
        }
      ]
    },
    {
      "id": "dif_release",
      "ask_when": "Model or release is absent and affects capability.",
      "header": "Platform",
      "question": "How should missing SRX model or Junos release details be handled?",
      "options": [
        {
          "label": "Discover first (Recommended)",
          "description": "Identify the exact model and release before capability conclusions."
        },
        {
          "label": "Exact details supplied",
          "description": "Apply release-specific capabilities."
        },
        {
          "label": "Infer conservatively",
          "description": "Limit output to evidence-supported design and disclose uncertainty."
        }
      ]
    },
    {
      "id": "dif_source",
      "ask_when": "Feed artifacts or publishing design is incomplete.",
      "header": "Feed Source",
      "question": "How should an incomplete feed source be handled?",
      "options": [
        {
          "label": "Inspect source first (Recommended)",
          "description": "Determine whether an existing endpoint, archive, or publishing workflow can be used."
        },
        {
          "label": "Use supplied endpoint",
          "description": "Integrate the supplied endpoint and archive layout."
        },
        {
          "label": "Design new endpoint",
          "description": "Define a new supported HTTPS feed and publishing workflow."
        }
      ]
    },
    {
      "id": "dif_tls",
      "ask_when": "Publisher CA source or trust anchor is absent.",
      "header": "CA Source",
      "question": "How should an unspecified publisher CA source be resolved?",
      "options": [
        {
          "label": "Verify chain first (Recommended)",
          "description": "Verify the publisher chain and required trust anchor before configuration."
        },
        {
          "label": "Use supplied public CA",
          "description": "Validate the publisher with the supplied public CA chain."
        },
        {
          "label": "Use supplied private CA",
          "description": "Import the supplied private CA as a controlled trust anchor before validation."
        }
      ]
    },
    {
      "id": "dif_auth",
      "ask_when": "Feed authentication method is absent or unclear.",
      "header": "Feed Auth",
      "question": "How should uncertain feed authentication be handled?",
      "options": [
        {
          "label": "Verify endpoint first (Recommended)",
          "description": "Verify endpoint requirements before selecting authentication and risk-classify explicit no-extra-auth requests supplied through Other."
        },
        {
          "label": "Use supplied single auth",
          "description": "Use one exact supplied mTLS or Basic mechanism specified via Other while keeping credentials outside chat."
        },
        {
          "label": "Use supplied combined auth",
          "description": "Use supplied mTLS plus Basic authentication when both are required while keeping credentials outside chat."
        }
      ]
    },
    {
      "id": "dif_route",
      "ask_when": "Feed-server routing context is absent.",
      "header": "Routing",
      "question": "How should an unknown feed-server route be handled?",
      "options": [
        {
          "label": "Trace route first (Recommended)",
          "description": "Collect route, DNS, source, and connection evidence before selecting context."
        },
        {
          "label": "Use supplied default instance",
          "description": "Use the supplied default-instance path after reachability validation."
        },
        {
          "label": "Use supplied named instance",
          "description": "Use the supplied routing instance and source address."
        }
      ]
    },
    {
      "id": "dif_effect",
      "ask_when": "Feed enforcement intent is absent.",
      "header": "Policy Use",
      "question": "How will feed entries affect security policy?",
      "options": [
        {
          "label": "Blocklist deny (Recommended)",
          "description": "Deny new matching sessions with logging."
        },
        {
          "label": "Allowlist permit",
          "description": "Permit members within constrained policy."
        },
        {
          "label": "Both uses",
          "description": "Define separate objects and precedence."
        }
      ]
    },
    {
      "id": "dif_session",
      "ask_when": "Existing-session behavior matters and is absent.",
      "header": "Sessions",
      "question": "How should unspecified existing-session behavior be resolved?",
      "options": [
        {
          "label": "Confirm behavior first (Recommended)",
          "description": "Confirm existing-session behavior before accounting for enforcement timing."
        },
        {
          "label": "Use supplied new-sessions-only",
          "description": "Apply feed changes only to new session evaluations."
        },
        {
          "label": "Use supplied targeted clear",
          "description": "Record targeted-clear intent and require separate live approval before clearing."
        }
      ]
    },
    {
      "id": "dif_poll",
      "ask_when": "Refresh requirements are absent.",
      "header": "Polling",
      "question": "How should an unspecified polling cadence be resolved?",
      "options": [
        {
          "label": "Confirm cadence first (Recommended)",
          "description": "Confirm the polling cadence before selecting an interval."
        },
        {
          "label": "Use supplied standard interval",
          "description": "Use the supplied conservative supported standard interval."
        },
        {
          "label": "Use supplied custom interval",
          "description": "Use the supplied custom interval after validating load and reliability."
        }
      ]
    }
  ]
}
```

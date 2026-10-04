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
      "id": "mnhab_oob",
      "ask_when": "Console or out-of-band access to both nodes is not confirmed.",
      "header": "OOB Access",
      "question": "Is console or out-of-band access available on both nodes?",
      "options": [
        {
          "label": "Both nodes reachable (Recommended)",
          "description": "Proceed, because a bad commit can be recovered from the console."
        },
        {
          "label": "Only one node",
          "description": "Stop until the second node has out-of-band access."
        },
        {
          "label": "No out-of-band access",
          "description": "Stop, because nothing reverts a commit that cuts off management."
        }
      ]
    },
    {
      "id": "mnhab_mode",
      "ask_when": "The deployment mode is absent and cannot be derived from the gateway and eBGP answers.",
      "header": "MNHA Mode",
      "question": "Which MNHA deployment mode should the pair use?",
      "options": [
        {
          "label": "Routing mode (Recommended)",
          "description": "Use eBGP signal routes when no host uses the firewall as its static gateway."
        },
        {
          "label": "Switching mode",
          "description": "Use a VIP gateway on a shared segment with no dynamic routing."
        },
        {
          "label": "Hybrid mode",
          "description": "Use a VIP on the host segment and eBGP on the upstream side."
        }
      ]
    },
    {
      "id": "mnhab_icl",
      "ask_when": "The ICL transport is absent.",
      "header": "ICL Link",
      "question": "How should the inter-chassis link be carried?",
      "options": [
        {
          "label": "Dedicated link (Recommended)",
          "description": "Use a back-to-back interface pair in its own ICL zone."
        },
        {
          "label": "Shared segment",
          "description": "Use loopback addresses reached over an existing data segment."
        }
      ]
    },
    {
      "id": "mnhab_crypto",
      "ask_when": "ICL encryption is undecided.",
      "header": "ICL Crypto",
      "question": "Should the inter-chassis link be encrypted?",
      "options": [
        {
          "label": "Encrypt the ICL (Recommended)",
          "description": "Use HA link encryption with a pre-shared key the user sets on each node."
        },
        {
          "label": "Leave unencrypted",
          "description": "Accept clear-text state sync on a dedicated link the user controls."
        }
      ]
    },
    {
      "id": "mnhab_failover",
      "ask_when": "Whether to run the failover test after formation is undecided.",
      "header": "Failover",
      "question": "Should the build end with an approved failover test?",
      "options": [
        {
          "label": "Planned failover test (Recommended)",
          "description": "Fail SRG1 over and back under a separate approval gate."
        },
        {
          "label": "Formation only",
          "description": "Stop after formation is verified and report the pair as built."
        }
      ]
    }
  ]
}
```

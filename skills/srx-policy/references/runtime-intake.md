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
      "id": "policy_task",
      "ask_when": "The requested activity is absent.",
      "header": "Task",
      "question": "What should this policy run accomplish?",
      "options": [
        {
          "label": "Design or review (Recommended)",
          "description": "Produce or assess security-policy intent."
        },
        {
          "label": "Troubleshoot",
          "description": "Diagnose lookup, session, or application failures."
        },
        {
          "label": "Migration",
          "description": "Convert from another platform."
        }
      ]
    },
    {
      "id": "policy_release",
      "ask_when": "The model, release, or licensing is absent and affects features.",
      "header": "Platform",
      "question": "How should missing platform or license details be handled?",
      "options": [
        {
          "label": "Discover first (Recommended)",
          "description": "Identify the model, Junos release, and licenses before feature conclusions."
        },
        {
          "label": "Exact details supplied",
          "description": "Apply supported policy and services from supplied details."
        },
        {
          "label": "Infer conservatively",
          "description": "Limit output to evidence-supported base policy and disclose uncertainty."
        }
      ]
    },
    {
      "id": "policy_model",
      "ask_when": "The architecture is absent.",
      "header": "Policy Model",
      "question": "How should an unspecified policy architecture be resolved?",
      "options": [
        {
          "label": "Confirm architecture first (Recommended)",
          "description": "Confirm the policy architecture before organizing rules."
        },
        {
          "label": "Use supplied global policy",
          "description": "Use the supplied global-policy architecture."
        },
        {
          "label": "Use supplied zone-pair policy",
          "description": "Use the supplied zone-pair architecture and specify a complete mixed architecture through Other."
        }
      ]
    },
    {
      "id": "policy_flow",
      "ask_when": "The traffic intent is incomplete.",
      "header": "Traffic",
      "question": "How should incomplete traffic intent be handled?",
      "options": [
        {
          "label": "Map flow first (Recommended)",
          "description": "Identify source, destination, application, service, zones, and purpose before policy design."
        },
        {
          "label": "Use supplied complete intent",
          "description": "Design from supplied complete traffic requirements."
        },
        {
          "label": "Derive from migration source",
          "description": "Derive intent from a supplied normalized source policy."
        }
      ]
    },
    {
      "id": "policy_nat",
      "ask_when": "NAT involvement is unclear.",
      "header": "NAT Context",
      "question": "How should uncertain NAT involvement be handled?",
      "options": [
        {
          "label": "Trace first (Recommended)",
          "description": "Build a packet-flow trace before selecting policy addresses."
        },
        {
          "label": "Model supplied NAT",
          "description": "Use the supplied pre- and post-NAT tuple."
        },
        {
          "label": "Model supplied no-NAT",
          "description": "Use supplied original addresses and routing without translation."
        }
      ]
    },
    {
      "id": "policy_service",
      "ask_when": "Inspection services are absent.",
      "header": "Services",
      "question": "How should unspecified security-service scope be handled?",
      "options": [
        {
          "label": "Confirm services first (Recommended)",
          "description": "Inventory application, NAT, inspection, license, and capacity requirements before selecting a bundle."
        },
        {
          "label": "Use supplied base-only bundle",
          "description": "Apply supplied least privilege and logging without added services."
        },
        {
          "label": "Use supplied enhanced bundle",
          "description": "Use a complete supplied application, NAT, and inspection list after license and capacity validation."
        }
      ]
    },
    {
      "id": "policy_ip",
      "ask_when": "Address-family scope is absent.",
      "header": "IP Family",
      "question": "Which address families should policy cover?",
      "options": [
        {
          "label": "Dual-stack (Recommended)",
          "description": "Cover IPv4 and IPv6 unicast and specify multicast or control-plane scope through Other."
        },
        {
          "label": "IPv4 only",
          "description": "Cover only IPv4 unicast and specify special traffic scope through Other."
        },
        {
          "label": "IPv6 only",
          "description": "Cover only IPv6 unicast and specify special traffic scope through Other."
        }
      ]
    },
    {
      "id": "policy_session",
      "ask_when": "Existing-session behavior matters and is absent.",
      "header": "Sessions",
      "question": "How should existing sessions be treated after a policy change?",
      "options": [
        {
          "label": "Leave existing sessions (Recommended)",
          "description": "Validate new sessions without clearing existing state."
        },
        {
          "label": "Clear targeted sessions",
          "description": "Clear only separately approved matching sessions."
        },
        {
          "label": "Maintenance-window reset",
          "description": "Reset broader session state only under separate maintenance approval with rollback."
        }
      ]
    }
  ]
}
```

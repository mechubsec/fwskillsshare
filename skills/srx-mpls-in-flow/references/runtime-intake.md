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
      "id": "mpls_task",
      "ask_when": "The requested activity is absent.",
      "header": "Task",
      "question": "What should this MPLS-in-flow run accomplish?",
      "options": [
        {
          "label": "Design or review (Recommended)",
          "description": "Produce or assess a secure MPLS design."
        },
        {
          "label": "Troubleshoot",
          "description": "Diagnose label, VRF, routing, or policy failures."
        },
        {
          "label": "Migration",
          "description": "Plan conversion to flow mode."
        }
      ]
    },
    {
      "id": "mpls_release",
      "ask_when": "The model or release is absent.",
      "header": "Platform",
      "question": "How should missing SRX model or Junos release details be handled?",
      "options": [
        {
          "label": "Discover first (Recommended)",
          "description": "Identify the exact model and release before MPLS flow-mode support conclusions."
        },
        {
          "label": "Exact details supplied",
          "description": "Verify the supplied platform against minimum support."
        },
        {
          "label": "Stop pending details",
          "description": "Treat unknown platform support as a blocker."
        }
      ]
    },
    {
      "id": "mpls_role",
      "ask_when": "PE, CPE, or transit role is unclear.",
      "header": "Device Role",
      "question": "How should an uncertain SRX MPLS role be handled?",
      "options": [
        {
          "label": "Confirm role first (Recommended)",
          "description": "Establish PE, CPE, transit, or mixed responsibilities before design."
        },
        {
          "label": "Use supplied edge role",
          "description": "Apply security for a supplied PE or CPE role."
        },
        {
          "label": "Assess supplied transit role",
          "description": "Re-evaluate the requested security function for a supplied transit role."
        }
      ]
    },
    {
      "id": "mpls_family",
      "ask_when": "The required address families are absent.",
      "header": "IP Family",
      "question": "Which address families are required?",
      "options": [
        {
          "label": "IPv4 and VPNv4 (Recommended)",
          "description": "Design the common IPv4 L3VPN case."
        },
        {
          "label": "Dual stack",
          "description": "Include IPv6 and VPNv6."
        },
        {
          "label": "IPv6 focused",
          "description": "Limit design to IPv6."
        }
      ]
    },
    {
      "id": "mpls_signal",
      "ask_when": "Label signaling is absent.",
      "header": "Signaling",
      "question": "How should unspecified label signaling be handled?",
      "options": [
        {
          "label": "Inspect signaling first (Recommended)",
          "description": "Identify transport and label protocols before MPLS design."
        },
        {
          "label": "Preserve supplied signaling",
          "description": "Preserve the supplied LDP, RSVP, or BGP label design."
        },
        {
          "label": "Design new LDP transport",
          "description": "Build a new supported LDP transport from supplied requirements."
        }
      ]
    },
    {
      "id": "mpls_vrf",
      "ask_when": "The VRF or route-target inventory is incomplete.",
      "header": "VRF Scope",
      "question": "How should an incomplete VRF inventory be handled?",
      "options": [
        {
          "label": "Inventory VRFs first (Recommended)",
          "description": "Identify VRFs, RDs, RTs, interfaces, and prefixes before policy design."
        },
        {
          "label": "Use supplied complete matrix",
          "description": "Apply a supplied complete VRF and route-target inventory."
        },
        {
          "label": "Design new service matrix",
          "description": "Build a new matrix from supplied service requirements."
        }
      ]
    },
    {
      "id": "mpls_policy",
      "ask_when": "The VRF-aware policy model is absent.",
      "header": "Policy Model",
      "question": "How should an unspecified VRF policy architecture be resolved?",
      "options": [
        {
          "label": "Confirm architecture first (Recommended)",
          "description": "Confirm the VRF policy architecture before organizing policy."
        },
        {
          "label": "Use supplied policy groups",
          "description": "Use the supplied VRF policy-group architecture."
        },
        {
          "label": "Use supplied VRF-to-zone",
          "description": "Use the supplied VRF-to-zone architecture."
        }
      ]
    },
    {
      "id": "mpls_service",
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
          "description": "Apply supplied stateful policy and logging without added services."
        },
        {
          "label": "Use supplied enhanced bundle",
          "description": "Use a complete supplied application, NAT, and inspection list after license and capacity validation."
        }
      ]
    }
  ]
}
```

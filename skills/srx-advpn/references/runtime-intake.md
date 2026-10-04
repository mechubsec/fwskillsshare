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
      "id": "advpn_task",
      "ask_when": "The requested activity is absent.",
      "header": "Task",
      "question": "What should this ADVPN run accomplish?",
      "options": [
        {
          "label": "Design or review (Recommended)",
          "description": "Produce or assess a read-only architecture and candidate configuration."
        },
        {
          "label": "Troubleshoot",
          "description": "Diagnose shortcut or forwarding problems."
        },
        {
          "label": "Migration",
          "description": "Plan transition from static or hub-only IPsec."
        }
      ]
    },
    {
      "id": "advpn_release",
      "ask_when": "Model or release is absent and affects support.",
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
          "label": "Infer conservatively",
          "description": "Limit output to evidence-supported design and disclose uncertainty."
        }
      ]
    },
    {
      "id": "advpn_topo",
      "ask_when": "Site, addressing, NAT, or HA topology is incomplete.",
      "header": "Topology",
      "question": "How should incomplete ADVPN topology be handled?",
      "options": [
        {
          "label": "Map topology first (Recommended)",
          "description": "Identify sites, addresses, LANs, NAT, and HA roles before design."
        },
        {
          "label": "Use supplied complete map",
          "description": "Design from a supplied complete topology."
        },
        {
          "label": "Design from requirements",
          "description": "Build a new topology from supplied site and traffic requirements."
        }
      ]
    },
    {
      "id": "advpn_auth",
      "ask_when": "Peer authentication is absent.",
      "header": "Auth",
      "question": "How should unspecified peer authentication be handled?",
      "options": [
        {
          "label": "Inventory authentication (Recommended)",
          "description": "Identify existing PKI, enrollment, and peer identity constraints before design."
        },
        {
          "label": "Use supplied PKI",
          "description": "Use the supplied certificate authority and enrollment design."
        },
        {
          "label": "Assess supplied PSK",
          "description": "Analyze the supplied PSK design and report ADVPN limitations."
        }
      ]
    },
    {
      "id": "advpn_route",
      "ask_when": "Overlay routing is absent.",
      "header": "Routing",
      "question": "How should an unspecified ADVPN routing model be resolved?",
      "options": [
        {
          "label": "Confirm model first (Recommended)",
          "description": "Confirm the routing model before designing the overlay."
        },
        {
          "label": "Use supplied OSPF P2MP",
          "description": "Use the supplied OSPF point-to-multipoint routing model."
        },
        {
          "label": "Use supplied other model",
          "description": "Use the complete alternative routing model specified through Other."
        }
      ]
    },
    {
      "id": "advpn_traffic",
      "ask_when": "Branch path requirements are unclear.",
      "header": "Traffic",
      "question": "What branch traffic behavior is required?",
      "options": [
        {
          "label": "Shortcuts plus hub (Recommended)",
          "description": "Support hub paths and spoke shortcuts."
        },
        {
          "label": "Shortcuts only",
          "description": "Focus on spoke-to-spoke formation."
        },
        {
          "label": "Central backhaul",
          "description": "Re-evaluate AutoVPN fit."
        }
      ]
    },
    {
      "id": "advpn_gateway",
      "ask_when": "Release-specific gateway support is unresolved.",
      "header": "Gateway",
      "question": "How should unresolved ADVPN gateway support be handled?",
      "options": [
        {
          "label": "Verify support first (Recommended)",
          "description": "Verify model and release support before selecting a gateway form."
        },
        {
          "label": "Use supplied supported static",
          "description": "Use the supplied static form after support is established."
        },
        {
          "label": "Use supplied supported dynamic",
          "description": "Use the supplied dynamic form after support is established."
        }
      ]
    },
    {
      "id": "advpn_evidence",
      "ask_when": "Troubleshooting evidence is incomplete.",
      "header": "Evidence",
      "question": "How should incomplete troubleshooting evidence be handled?",
      "options": [
        {
          "label": "Inventory evidence (Recommended)",
          "description": "Identify available configuration, SAs, routes, and flow evidence before diagnosis."
        },
        {
          "label": "Use supplied artifacts",
          "description": "Diagnose only from supplied artifacts and limit runtime conclusions."
        },
        {
          "label": "Approved live collection",
          "description": "Collect targeted read-only device evidence with approval."
        }
      ]
    }
  ]
}
```

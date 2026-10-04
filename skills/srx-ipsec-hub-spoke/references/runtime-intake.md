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
      "id": "hsvpn_task",
      "ask_when": "The requested activity is absent.",
      "header": "Task",
      "question": "What should this hub-and-spoke run accomplish?",
      "options": [
        {
          "label": "Design or review (Recommended)",
          "description": "Produce or assess a static route-based design."
        },
        {
          "label": "Troubleshoot",
          "description": "Diagnose IKE, IPsec, routing, or policy."
        },
        {
          "label": "Migration",
          "description": "Plan transition from policy-based or shared-tunnel VPN."
        }
      ]
    },
    {
      "id": "hsvpn_release",
      "ask_when": "The model or release is absent and affects syntax.",
      "header": "Platform",
      "question": "How should missing SRX model or Junos release details be handled?",
      "options": [
        {
          "label": "Discover first (Recommended)",
          "description": "Identify exact models and releases before syntax conclusions."
        },
        {
          "label": "Exact details supplied",
          "description": "Apply platform-specific syntax."
        },
        {
          "label": "Infer conservatively",
          "description": "Limit output to evidence-supported design and disclose uncertainty."
        }
      ]
    },
    {
      "id": "hsvpn_topo",
      "ask_when": "Peer, prefix, NAT, HA, or st0 data is incomplete.",
      "header": "Topology",
      "question": "How should incomplete hub-and-spoke topology be handled?",
      "options": [
        {
          "label": "Map topology first (Recommended)",
          "description": "Identify peers, LANs, WANs, NAT, HA, and st0 allocation before design."
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
      "id": "hsvpn_traffic",
      "ask_when": "Spoke path requirements are unclear.",
      "header": "Traffic",
      "question": "How should an unspecified hub-spoke traffic model be resolved?",
      "options": [
        {
          "label": "Confirm model first (Recommended)",
          "description": "Confirm the traffic model before designing spoke forwarding."
        },
        {
          "label": "Use supplied central backhaul",
          "description": "Backhaul all scoped spoke traffic through the hub as supplied."
        },
        {
          "label": "Use supplied split tunnel",
          "description": "Preserve the supplied split-tunnel paths and specify local variants through Other."
        }
      ]
    },
    {
      "id": "hsvpn_auth",
      "ask_when": "Peer authentication is absent.",
      "header": "Auth",
      "question": "What peer authentication should be used?",
      "options": [
        {
          "label": "Certificates (Recommended)",
          "description": "Use PKI where available."
        },
        {
          "label": "Unique PSKs",
          "description": "Use distinct secrets via approved delivery."
        },
        {
          "label": "Shared lab PSK",
          "description": "Classify as lab-only."
        }
      ]
    },
    {
      "id": "hsvpn_route",
      "ask_when": "Management reachability and tunnel defaults may conflict.",
      "header": "Routing",
      "question": "How should uncertain management-route protection be handled?",
      "options": [
        {
          "label": "Inspect routes first (Recommended)",
          "description": "Trace management, peer, and tunnel-default paths before route changes."
        },
        {
          "label": "Use supplied separate path",
          "description": "Preserve a supplied independent management path."
        },
        {
          "label": "Analyze competing defaults",
          "description": "Evaluate supplied competing defaults for recursion."
        }
      ]
    },
    {
      "id": "hsvpn_evidence",
      "ask_when": "Troubleshooting evidence is incomplete.",
      "header": "Evidence",
      "question": "How should incomplete troubleshooting evidence be handled?",
      "options": [
        {
          "label": "Inventory evidence (Recommended)",
          "description": "Identify available configuration, SAs, routes, sessions, and logs before diagnosis."
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

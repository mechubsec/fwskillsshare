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
      "id": "mnha_task",
      "ask_when": "The requested activity is absent.",
      "header": "Task",
      "question": "What should this MNHA run accomplish?",
      "options": [
        {
          "label": "Design or review (Recommended)",
          "description": "Produce or assess an architecture."
        },
        {
          "label": "Troubleshoot",
          "description": "Diagnose synchronization, forwarding, or failover."
        },
        {
          "label": "Migration",
          "description": "Plan migration from chassis cluster or standalone SRX."
        }
      ]
    },
    {
      "id": "mnha_release",
      "ask_when": "Node models or releases are absent.",
      "header": "Platform",
      "question": "How should missing node model or Junos release details be handled?",
      "options": [
        {
          "label": "Discover first (Recommended)",
          "description": "Identify every node model and release before support conclusions."
        },
        {
          "label": "Exact details supplied",
          "description": "Apply release-specific syntax."
        },
        {
          "label": "Stop pending details",
          "description": "Avoid implementation-ready configuration until exact details are supplied."
        }
      ]
    },
    {
      "id": "mnha_mode",
      "ask_when": "Forwarding mode is absent.",
      "header": "MNHA Mode",
      "question": "Which MNHA forwarding model is required?",
      "options": [
        {
          "label": "Routed mode (Recommended)",
          "description": "Use explicit routing and SRGs."
        },
        {
          "label": "Gateway mode",
          "description": "Provide default-gateway service behavior."
        },
        {
          "label": "Hybrid mode",
          "description": "Combine only for documented requirements."
        }
      ]
    },
    {
      "id": "mnha_migrate",
      "ask_when": "Starting state is unclear.",
      "header": "Migration",
      "question": "How should an uncertain MNHA starting state be handled?",
      "options": [
        {
          "label": "Inspect starting state (Recommended)",
          "description": "Inventory the current HA design before choosing a workflow."
        },
        {
          "label": "Design supplied greenfield",
          "description": "Design from a supplied new-deployment baseline."
        },
        {
          "label": "Plan supplied migration",
          "description": "Plan migration or repair from supplied current-state evidence."
        }
      ]
    },
    {
      "id": "mnha_topo",
      "ask_when": "Inter-node topology is incomplete.",
      "header": "Topology",
      "question": "How should incomplete inter-node topology be handled?",
      "options": [
        {
          "label": "Map topology first (Recommended)",
          "description": "Identify node links, interfaces, and data paths before design."
        },
        {
          "label": "Use supplied symmetric map",
          "description": "Design from supplied matched interfaces and direct links."
        },
        {
          "label": "Assess supplied asymmetric map",
          "description": "Include supplied inter-cluster data paths and asymmetry."
        }
      ]
    },
    {
      "id": "mnha_service",
      "ask_when": "Stateful service scope is absent.",
      "header": "Services",
      "question": "How should unspecified failover-service scope be resolved?",
      "options": [
        {
          "label": "Inventory services first (Recommended)",
          "description": "Identify every required failover service before selecting a bundle."
        },
        {
          "label": "Use supplied core-only bundle",
          "description": "Use the supplied firewall and NAT failover scope without IPsec or advanced services."
        },
        {
          "label": "Use supplied core-plus-IPsec",
          "description": "Use firewall and NAT plus the complete supplied IPsec failover scope and specify advanced combinations through Other."
        }
      ]
    },
    {
      "id": "mnha_route",
      "ask_when": "A complete upstream failover signaling design is absent.",
      "header": "Routing",
      "question": "How should unresolved MNHA signaling design be handled?",
      "options": [
        {
          "label": "Design from topology first (Recommended)",
          "description": "Derive a complete signaling design from topology and convergence requirements."
        },
        {
          "label": "Use supplied complete design",
          "description": "Use the supplied complete signaling, tracking, ownership, and convergence design."
        }
      ]
    },
    {
      "id": "mnha_objective",
      "ask_when": "Resilience priority is absent.",
      "header": "Objectives",
      "question": "How should an unspecified resilience objective be resolved?",
      "options": [
        {
          "label": "Confirm objective first (Recommended)",
          "description": "Confirm the primary resilience objective before design."
        },
        {
          "label": "Use supplied continuity priority",
          "description": "Prioritize session and state continuity as supplied."
        },
        {
          "label": "Use supplied convergence priority",
          "description": "Prioritize routing convergence as supplied."
        }
      ]
    },
    {
      "id": "mnha_test",
      "ask_when": "Validation depth is absent.",
      "header": "Test Plan",
      "question": "What validation depth is required?",
      "options": [
        {
          "label": "Full failure matrix (Recommended)",
          "description": "Test node, link, service, routing, and recovery."
        },
        {
          "label": "Named failures",
          "description": "Test specified cases."
        },
        {
          "label": "One failure",
          "description": "Reproduce the reported case safely."
        }
      ]
    }
  ]
}
```

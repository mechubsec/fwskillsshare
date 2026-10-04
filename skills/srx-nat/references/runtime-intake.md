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
      "id": "nat_task",
      "ask_when": "The requested activity is absent.",
      "header": "Task",
      "question": "What should this NAT run accomplish?",
      "options": [
        {
          "label": "Design or review (Recommended)",
          "description": "Produce or assess a NAT design."
        },
        {
          "label": "Troubleshoot",
          "description": "Diagnose translation, routing, proxy, or session failures."
        },
        {
          "label": "Migration",
          "description": "Convert NAT behavior from another platform."
        }
      ]
    },
    {
      "id": "nat_release",
      "ask_when": "The model or release is absent and affects feature support.",
      "header": "Platform",
      "question": "How should missing SRX model or Junos release details be handled?",
      "options": [
        {
          "label": "Discover first (Recommended)",
          "description": "Identify the exact model and release before feature conclusions."
        },
        {
          "label": "Exact details supplied",
          "description": "Apply supported features and syntax."
        },
        {
          "label": "Infer conservatively",
          "description": "Limit output to evidence-supported behavior and disclose uncertainty."
        }
      ]
    },
    {
      "id": "nat_family",
      "ask_when": "The translation family is absent.",
      "header": "NAT Type",
      "question": "How should an unspecified translation family be handled?",
      "options": [
        {
          "label": "Identify family first (Recommended)",
          "description": "Establish the address-family translation before selecting NAT behavior."
        },
        {
          "label": "NAT44",
          "description": "Design supplied IPv4-to-IPv4 translation requirements."
        },
        {
          "label": "NAT64",
          "description": "Design supplied IPv6-to-IPv4 translation requirements."
        }
      ]
    },
    {
      "id": "nat_tuple",
      "ask_when": "The pre- or post-translation tuple is incomplete.",
      "header": "Traffic",
      "question": "How should an incomplete translation tuple be handled?",
      "options": [
        {
          "label": "Trace tuple first (Recommended)",
          "description": "Identify source, destination, service, zones, and translated values before design."
        },
        {
          "label": "Use supplied complete tuple",
          "description": "Apply the supplied pre- and post-translation values."
        },
        {
          "label": "Build tuple worksheet",
          "description": "Produce a worksheet for missing tuple fields."
        }
      ]
    },
    {
      "id": "nat_context",
      "ask_when": "Zone, interface, or routing-instance classification is unclear.",
      "header": "Context",
      "question": "How should uncertain traffic classification be handled?",
      "options": [
        {
          "label": "Inspect full context first (Recommended)",
          "description": "Inspect complementary zone, interface, and routing-instance facts before rule selection."
        },
        {
          "label": "Use supplied complete context",
          "description": "Apply the supplied complete zone, interface, and routing-instance classification."
        },
        {
          "label": "Stop pending context",
          "description": "Stop rule conclusions until all complementary classification facts are supplied."
        }
      ]
    },
    {
      "id": "nat_reach",
      "ask_when": "Translated-address reachability is unclear.",
      "header": "Reachability",
      "question": "How should uncertain translated-address reachability be handled?",
      "options": [
        {
          "label": "Trace reachability first (Recommended)",
          "description": "Validate routing and adjacency before choosing advertisement behavior."
        },
        {
          "label": "Use supplied routed prefix",
          "description": "Use supplied explicit routing for translated addresses."
        },
        {
          "label": "Use supplied neighbor proxy",
          "description": "Apply supplied proxy ARP or NDP behavior."
        }
      ]
    },
    {
      "id": "nat_return",
      "ask_when": "Traffic symmetry is unclear.",
      "header": "Return Path",
      "question": "How should uncertain NAT return symmetry be handled?",
      "options": [
        {
          "label": "Unknown—trace first (Recommended)",
          "description": "Collect routing, session, and flow evidence before assuming symmetry."
        },
        {
          "label": "Use supplied symmetric path",
          "description": "Preserve the supplied stateful return through the translator."
        },
        {
          "label": "Assess supplied asymmetric path",
          "description": "Analyze the supplied asymmetric path and session risk."
        }
      ]
    },
    {
      "id": "nat_evidence",
      "ask_when": "Troubleshooting evidence is incomplete.",
      "header": "Evidence",
      "question": "How should incomplete troubleshooting evidence be handled?",
      "options": [
        {
          "label": "Inventory evidence (Recommended)",
          "description": "Identify available NAT configuration, routes, counters, sessions, and logs before diagnosis."
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

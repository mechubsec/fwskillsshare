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
      "id": "cc_change_authority",
      "ask_when": "Hypervisor or device change authority is absent.",
      "header": "Authority",
      "question": "How should hypervisor and device changes be handled?",
      "options": [
        {
          "label": "Read-only assessment (Recommended)",
          "description": "Inspect and report without changing bridges, guests, or configuration."
        },
        {
          "label": "Propose then confirm",
          "description": "Present each change for approval before applying it."
        },
        {
          "label": "Approved to apply",
          "description": "Apply the agreed plan with verification after each phase."
        }
      ]
    },
    {
      "id": "cc_task",
      "ask_when": "The requested activity is absent.",
      "header": "Task",
      "question": "What should this chassis cluster run accomplish?",
      "options": [
        {
          "label": "Assess before building (Recommended)",
          "description": "Establish current hypervisor and guest state before planning a build."
        },
        {
          "label": "Troubleshoot an existing cluster",
          "description": "Diagnose forwarding, fabric, control link, or failover behavior."
        },
        {
          "label": "Audit readiness",
          "description": "Assess whether hypervisor and guest layout can support clustering."
        }
      ]
    },
    {
      "id": "cc_fabric_segment",
      "ask_when": "The fabric segment and its MTU are absent.",
      "header": "Fabric",
      "question": "How should the fabric segment and its MTU be established?",
      "options": [
        {
          "label": "Inspect the host first (Recommended)",
          "description": "Enumerate bridges and MTUs before choosing a fabric segment."
        },
        {
          "label": "Use a supplied jumbo bridge",
          "description": "Apply the named bridge already provisioned at MTU 9000."
        },
        {
          "label": "Create a dedicated bridge",
          "description": "Add a portless VLAN-aware bridge at MTU 9000 for control and fabric."
        }
      ]
    },
    {
      "id": "cc_nic_layout",
      "ask_when": "Guest NIC layout is absent and in-place promotion may be assumed.",
      "header": "NIC layout",
      "question": "How should the guest NIC layout be treated?",
      "options": [
        {
          "label": "Inspect the guests first (Recommended)",
          "description": "Read each guest NIC list before assuming any interface mapping."
        },
        {
          "label": "Purpose-built for clustering",
          "description": "Guests already carry management, control, fabric, and reth interfaces."
        },
        {
          "label": "Standalone-shaped",
          "description": "Guests need a redrawn NIC plan because in-place promotion shifts every index."
        }
      ]
    },
    {
      "id": "cc_cluster_id",
      "ask_when": "The cluster identifier is absent and other clusters may share the segment.",
      "header": "Cluster id",
      "question": "How should the cluster identifier be selected?",
      "options": [
        {
          "label": "Enumerate existing clusters first (Recommended)",
          "description": "Confirm no cluster on the segment already uses the identifier."
        },
        {
          "label": "Use the supplied identifier",
          "description": "Apply the value provided and verify it is unique before boot."
        }
      ]
    }
  ]
}
```

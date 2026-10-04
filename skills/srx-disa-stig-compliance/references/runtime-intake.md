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
      "id": "stig_goal",
      "ask_when": "The requested assessment outcome is absent.",
      "header": "Goal",
      "question": "What outcome should this SRX STIG assessment produce?",
      "options": [
        {
          "label": "Rule-level assessment (Recommended)",
          "description": "Assign conservative per-rule status with evidence and open findings."
        },
        {
          "label": "CKL preparation",
          "description": "Organize results and comments for STIG Viewer checklist entry."
        },
        {
          "label": "Remediation plan",
          "description": "Emphasize fix actions and Junos compatibility for open rules."
        }
      ]
    },
    {
      "id": "stig_source",
      "ask_when": "The governing benchmark release or checksum is absent.",
      "header": "Benchmark",
      "question": "How should an unspecified governing STIG release be resolved?",
      "options": [
        {
          "label": "Confirm release first (Recommended)",
          "description": "Confirm the benchmark release and checksum before assigning any rule status."
        },
        {
          "label": "Use supplied Y25M01",
          "description": "Assess against the supplied pinned DISA Y25M01 package."
        },
        {
          "label": "Use supplied other release",
          "description": "Record the other release supplied through Other as an unsupported source."
        }
      ]
    },
    {
      "id": "stig_profile",
      "ask_when": "The applicable SRX component profiles are unclear.",
      "header": "Profiles",
      "question": "How should uncertain SRX component profiles be resolved?",
      "options": [
        {
          "label": "Inventory roles first (Recommended)",
          "description": "Inventory device roles and evidence before selecting component catalogs."
        },
        {
          "label": "Use supplied role set",
          "description": "Select catalogs from the supplied complete device role set."
        },
        {
          "label": "Device management and ALG only",
          "description": "Limit catalogs to the supplied firewall NDM and ALG components."
        }
      ]
    },
    {
      "id": "stig_scope",
      "ask_when": "Device, cluster, or logical-system scope is unclear.",
      "header": "Scope",
      "question": "How should an uncertain assessment scope be resolved?",
      "options": [
        {
          "label": "Map scope first (Recommended)",
          "description": "Map devices, cluster nodes, logical systems, and tenants before assessing."
        },
        {
          "label": "Use supplied device scope",
          "description": "Assess the supplied complete device and cluster scope."
        },
        {
          "label": "Use supplied named context",
          "description": "Limit assessment to the supplied logical system, tenant, or routing instance."
        }
      ]
    },
    {
      "id": "stig_evidence",
      "ask_when": "Evidence completeness or currency is unclear.",
      "header": "Evidence",
      "question": "How should uncertain evidence completeness be handled?",
      "options": [
        {
          "label": "Inventory evidence (Recommended)",
          "description": "Identify configuration, operational output, diagrams, and process records before grading."
        },
        {
          "label": "Assess supplied artifacts",
          "description": "Assess only supplied evidence and mark uncovered rules Not Reviewed."
        },
        {
          "label": "Build evidence request",
          "description": "List required artifacts and collection steps without assigning status."
        }
      ]
    },
    {
      "id": "stig_output",
      "ask_when": "Deliverable emphasis is absent.",
      "header": "Output",
      "question": "What deliverable should be emphasized?",
      "options": [
        {
          "label": "Rule matrix (Recommended)",
          "description": "Return per-rule identity, severity, status, and evidence."
        },
        {
          "label": "Checklist comments",
          "description": "Emphasize assessor-ready finding details and comment text."
        },
        {
          "label": "Executive summary",
          "description": "Emphasize severity distribution, coverage, and top actions."
        }
      ]
    }
  ]
}
```

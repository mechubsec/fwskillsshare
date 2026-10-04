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
      "id": "pci_version",
      "ask_when": "The governing PCI version is absent.",
      "header": "PCI Version",
      "question": "How should an unspecified PCI DSS version be resolved?",
      "options": [
        {"label": "Confirm version first (Recommended)", "description": "Confirm the governing PCI DSS version before mapping requirements."},
        {"label": "Use supplied PCI DSS 4.0.1", "description": "Assess against the supplied PCI DSS 4.0.1 requirements."},
        {"label": "Use supplied other version", "description": "Assess against the other version supplied through Other."}
      ]
    },
    {
      "id": "pci_overlay",
      "ask_when": "Applicable QSA or customer overlays are unclear.",
      "header": "Overlay",
      "question": "How should an unspecified assessment overlay be handled?",
      "options": [
        {"label": "Inventory overlays first (Recommended)", "description": "Confirm applicable QSA and customer requirements before adding interpretations."},
        {"label": "Use supplied overlay", "description": "Apply the complete supplied QSA or customer overlay."},
        {"label": "Standard only", "description": "Use the selected PCI DSS version without an additive assessment overlay."}
      ]
    },
    {
      "id": "pci_stage",
      "ask_when": "The assessment type is absent.",
      "header": "Assess Type",
      "question": "What kind of PCI assessment is this?",
      "options": [
        {"label": "Readiness review (Recommended)", "description": "Identify gaps before formal assessment."},
        {"label": "ROC support", "description": "Organize QSA evidence."},
        {"label": "SAQ support", "description": "Tailor evidence to self-assessment."}
      ]
    },
    {
      "id": "pci_scope",
      "ask_when": "The CDE boundary is unclear.",
      "header": "CDE Scope",
      "question": "How should an uncertain CDE boundary be handled?",
      "options": [
        {"label": "Map CDE scope (Recommended)", "description": "Identify account-data systems, connected systems, and flows before assessing."},
        {"label": "Assess supplied boundary", "description": "Use a supplied final boundary and disclose unverified assumptions."},
        {"label": "Validate supplied draft", "description": "Test a supplied preliminary boundary and mark unresolved scope."}
      ]
    },
    {
      "id": "pci_segment",
      "ask_when": "Segmentation reliance is unclear.",
      "header": "Segmentation",
      "question": "How should uncertain segmentation reliance be handled?",
      "options": [
        {"label": "Verify segmentation (Recommended)", "description": "Test segmentation design and evidence before reducing scope."},
        {"label": "No scope reduction", "description": "Treat connected networks as in scope without relying on segmentation."},
        {"label": "Use verified segmentation", "description": "Apply a supplied validated segmentation boundary."}
      ]
    },
    {
      "id": "pci_evidence",
      "ask_when": "Evidence completeness is unclear.",
      "header": "Evidence",
      "question": "How should uncertain evidence completeness be handled?",
      "options": [
        {"label": "Inventory evidence (Recommended)", "description": "Identify configuration, reviews, logs, scans, and records before grading."},
        {"label": "Assess supplied artifacts", "description": "Assess only supplied evidence and disclose procedural gaps."},
        {"label": "Build evidence request", "description": "List required artifacts and samples without grading implementation."}
      ]
    },
    {
      "id": "pci_output",
      "ask_when": "The deliverable is absent.",
      "header": "Output",
      "question": "What deliverable is needed?",
      "options": [
        {"label": "Requirement matrix (Recommended)", "description": "Map evidence, gaps, and remediation."},
        {"label": "Segmentation report", "description": "Emphasize CDE isolation."},
        {"label": "Executive brief", "description": "Emphasize scope risk and top actions."}
      ]
    }
  ]
}
```

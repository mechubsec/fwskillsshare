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
      "id": "sd_stage",
      "ask_when": "The deployment stage is absent.",
      "header": "Stage",
      "question": "How should an unspecified deployment stage be resolved?",
      "options": [
        {"label": "Inspect stage first (Recommended)", "description": "Inspect deployment evidence to distinguish planning, fresh deployment, and troubleshooting before choosing a workflow."},
        {"label": "Plan supplied fresh deployment", "description": "Plan from a supplied fresh-deployment stage without executing changes."},
        {"label": "Troubleshoot supplied deployment", "description": "Diagnose a supplied existing deployment without assuming a fresh state."}
      ]
    },
    {
      "id": "sd_release",
      "ask_when": "The exact SD On-Prem release is absent.",
      "header": "Release",
      "question": "How should missing Security Director release details be handled?",
      "options": [
        {"label": "Discover first (Recommended)", "description": "Identify the exact release and matching guide before deployment planning."},
        {"label": "Exact details supplied", "description": "Use the exact supplied release and matching guide."},
        {"label": "Stop pending details", "description": "Do not produce release-dependent deployment steps."}
      ]
    },
    {
      "id": "sd_media",
      "ask_when": "Media presence or integrity is unclear.",
      "header": "Artifacts",
      "question": "How should uncertain release media integrity be handled?",
      "options": [
        {"label": "Verify media first (Recommended)", "description": "Check image and bundle presence, versions, and checksums before deployment."},
        {"label": "Use supplied verified media", "description": "Proceed with supplied artifacts and checksum evidence."},
        {"label": "Stop pending media", "description": "Block deployment until required artifacts are supplied."}
      ]
    },
    {
      "id": "sd_size",
      "ask_when": "The appliance flavor is absent.",
      "header": "Sizing",
      "question": "How should unresolved appliance sizing be handled?",
      "options": [
        {"label": "Measure requirements first (Recommended)", "description": "Measure device, traffic, log, retention, and growth requirements before selecting a flavor."},
        {"label": "Use supplied final flavor", "description": "Use the supplied final supported flavor without reselecting its size."}
      ]
    },
    {
      "id": "sd_proxmox",
      "ask_when": "VM placement values are incomplete.",
      "header": "Proxmox",
      "question": "How should incomplete Proxmox VM state be resolved?",
      "options": [
        {"label": "Inspect state first (Recommended)", "description": "Inspect Proxmox and VM evidence read-only before choosing a new-VM or existing-VM workflow."},
        {"label": "Plan supplied new VM", "description": "Plan with supplied VMID, node, storage, bridge, and resource values for a new VM."},
        {"label": "Assess supplied existing VM", "description": "Assess a supplied existing VM against deployment requirements."}
      ]
    },
    {
      "id": "sd_network",
      "ask_when": "IP, route, or internal CIDR values are incomplete.",
      "header": "Network",
      "question": "How should incomplete IP and routing values be handled?",
      "options": [
        {"label": "Map network first (Recommended)", "description": "Identify required addresses, gateway, routes, and internal CIDR before deployment."},
        {"label": "Use supplied network plan", "description": "Apply the complete supplied addressing and routing plan."},
        {"label": "Stop pending values", "description": "Block deployment and list missing network values."}
      ]
    },
    {
      "id": "sd_services",
      "ask_when": "Supporting service reachability is unverified.",
      "header": "DNS and NTP",
      "question": "How should unverified supporting-service reachability be handled?",
      "options": [
        {"label": "Verify services first (Recommended)", "description": "Run safe DNS and NTP reachability checks before deployment."},
        {"label": "Use supplied test results", "description": "Rely on supplied current DNS and NTP validation evidence."},
        {"label": "Stop pending readiness", "description": "Treat unverified service reachability as a blocker."}
      ]
    },
    {
      "id": "sd_transfer",
      "ask_when": "The bundle transfer method is absent.",
      "header": "Transfer",
      "question": "How should an unspecified bundle transfer method be resolved?",
      "options": [
        {"label": "Confirm method first (Recommended)", "description": "Confirm the approved transfer method before moving the bundle."},
        {"label": "Use supplied HTTPS", "description": "Transfer the bundle with the supplied approved HTTPS method and checksums."},
        {"label": "Use supplied SCP", "description": "Transfer the bundle with the supplied approved SCP method without exposing credentials."}
      ]
    },
    {
      "id": "sd_secrets",
      "ask_when": "Secret delivery is needed for a later step.",
      "header": "Secrets",
      "question": "How will deployment secrets be supplied?",
      "options": [
        {"label": "Interactive entry (Recommended)", "description": "Enter secrets at a trusted console."},
        {"label": "Secret manager", "description": "Use an approved delivery workflow."},
        {"label": "Supply later", "description": "Use placeholders and stop before secret-dependent execution."}
      ]
    },
    {
      "id": "sd_onboard",
      "ask_when": "Post-deployment scope is absent.",
      "header": "Onboarding",
      "question": "How far should the runbook go after deployment?",
      "options": [
        {"label": "Health validation (Recommended)", "description": "Validate the platform without production onboarding."},
        {"label": "Device onboarding", "description": "Include approved device connectivity."},
        {"label": "Full operations", "description": "Include logging, licensing, backup, and monitoring."}
      ]
    }
  ]
}
```

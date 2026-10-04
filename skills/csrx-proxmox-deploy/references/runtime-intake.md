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

Two entries below (`csrx_cpu` and `csrx_mode`) cover decisions that must be
made before the container's first `docker run`, not discovered afterward.
The CPU-passthrough decision needs a cold guest restart to take effect at
all; the forwarding-mode decision drives the entire interface/zone/policy
shape and switching it later is a rebuild, not a toggle.

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
      "id": "csrx_stage",
      "ask_when": "The deployment stage is absent.",
      "header": "Stage",
      "question": "How should an unspecified deployment stage be resolved?",
      "options": [
        {"label": "Inspect stage first (Recommended)", "description": "Inspect deployment evidence to distinguish planning, fresh deployment, and troubleshooting before choosing a workflow."},
        {"label": "Plan supplied fresh deployment", "description": "Plan from a supplied fresh-deployment stage without executing changes."},
        {"label": "Troubleshoot supplied deployment", "description": "Diagnose a supplied existing container/guest without assuming a fresh state."}
      ]
    },
    {
      "id": "csrx_release",
      "ask_when": "The exact cSRX image release/tag is absent.",
      "header": "Release",
      "question": "How should missing cSRX release details be handled?",
      "options": [
        {"label": "Discover first (Recommended)", "description": "Identify the exact image tag and re-derive its CSRX_* variable surface before deployment planning, since this skill's table is confirmed only for 26.2R1.7."},
        {"label": "Exact details supplied", "description": "Use the exact supplied image tag and its already-confirmed variable surface."},
        {"label": "Stop pending details", "description": "Do not produce release-dependent deployment steps."}
      ]
    },
    {
      "id": "csrx_media",
      "ask_when": "Image or licence presence/integrity is unclear.",
      "header": "Artifacts",
      "question": "How should uncertain image or licence integrity be handled?",
      "options": [
        {"label": "Verify artifacts first (Recommended)", "description": "Confirm the entitled image loads (docker load / docker images) and the licence path resolves, without reproducing the signed download URL or licence contents."},
        {"label": "Use supplied verified artifacts", "description": "Proceed with the supplied image tag and licence path evidence."},
        {"label": "Stop pending media", "description": "Block deployment until the required image or licence is supplied."}
      ]
    },
    {
      "id": "csrx_cpu",
      "ask_when": "The Docker host guest's CPU-passthrough state is unconfirmed.",
      "header": "CPU model",
      "question": "How should the Docker host guest's CPU model be confirmed before the first container run?",
      "options": [
        {"label": "Require host passthrough (Recommended)", "description": "Set the guest's CPU model to pass through the host's real features and cold-restart the guest; the default model lacks SSSE3, which srxpfe hard-requires even outside DPDK fast-path."},
        {"label": "Inspect supplied guest first", "description": "Read the existing guest's configured CPU model and /proc/cpuinfo read-only before any container start."}
      ]
    },
    {
      "id": "csrx_mode",
      "ask_when": "The forwarding mode (secure-wire vs routing) is absent. Drives the entire interface/zone/policy shape; changing it later is a rebuild.",
      "header": "Fwd mode",
      "question": "Which cSRX forwarding mode should this deployment target?",
      "options": [
        {"label": "Confirm topology first (Recommended)", "description": "Confirm whether the two segments already share one IP subnet (required for secure-wire) or need routed addressing before selecting CSRX_FORWARD_MODE."},
        {"label": "Use supplied final mode", "description": "Build interfaces, zones, and policy for the supplied final forwarding mode without reselecting it."},
        {"label": "Plan for a rebuild", "description": "Select a mode now and treat a later change as a full interface/zone/policy rebuild, since this skill found no live migration path between modes."}
      ]
    },
    {
      "id": "csrx_proxmox",
      "ask_when": "Docker host guest placement values are incomplete.",
      "header": "Proxmox",
      "question": "How should incomplete Proxmox guest state be resolved?",
      "options": [
        {"label": "Inspect state first (Recommended)", "description": "Inspect Proxmox node, storage, VMID, and bridge evidence read-only before choosing a new-guest or existing-guest workflow."},
        {"label": "Plan supplied new guest", "description": "Plan with supplied VMID, node, storage, bridges, and resource values for a new Docker host guest."},
        {"label": "Assess supplied existing guest", "description": "Assess a supplied existing Docker host guest against this skill's requirements."}
      ]
    },
    {
      "id": "csrx_network",
      "ask_when": "Data-plane interface mapping or macvlan network planning is incomplete.",
      "header": "Network",
      "question": "How should incomplete data-plane network planning be handled?",
      "options": [
        {"label": "Map network first (Recommended)", "description": "Confirm each data-plane parent NIC's in-guest name against its MAC address, that it is administratively up, and that its macvlan network is planned as passthru, not bridge."},
        {"label": "Use supplied network plan", "description": "Apply the complete supplied interface, macvlan, and addressing plan."},
        {"label": "Stop pending values", "description": "Block deployment and list missing network values."}
      ]
    },
    {
      "id": "csrx_offload",
      "ask_when": "The checksum/segmentation offload state on the data path is unverified.",
      "header": "Offload",
      "question": "How should unverified host-side offload state be handled before any TCP test?",
      "options": [
        {"label": "Verify and disable first (Recommended)", "description": "Disable tx-checksum-ip-generic/tso/gso on every hop between the endpoints and cSRX's data interfaces before trusting any TCP throughput result; this does not survive a reboot."},
        {"label": "Use supplied verification evidence", "description": "Rely on supplied current InCsumErrors/offload-state evidence for the data path."},
        {"label": "Stop pending readiness", "description": "Treat unverified offload state as a blocker for TCP-based verification."}
      ]
    },
    {
      "id": "csrx_secrets",
      "ask_when": "The licence path or root/cluster credentials must be supplied for a later step.",
      "header": "Secrets",
      "question": "How will the licence path and any credentials be supplied?",
      "options": [
        {"label": "Interactive entry (Recommended)", "description": "Enter the licence path and any credential at a trusted console; never as a docker run argv value or in a committed file."},
        {"label": "Secret manager", "description": "Use an approved delivery workflow and record where the licence/credential was stored, not its contents."},
        {"label": "Supply later", "description": "Use placeholders and stop before secret-dependent execution."}
      ]
    },
    {
      "id": "csrx_scope",
      "ask_when": "Post-deployment scope is absent.",
      "header": "Scope",
      "question": "How far should the runbook go after the container is configured?",
      "options": [
        {"label": "Health validation (Recommended)", "description": "Validate srxpfe presence, interface/zone/policy state, and the blocked-then-passing gate without a throughput or cRPD investigation."},
        {"label": "Include performance baseline", "description": "Add throughput measurement against this skill's documented baseline envelope."},
        {"label": "Include cRPD exploration", "description": "Explore CSRX_CRPD-based topologies, understanding this skill only read that behavior from the image and never exercised it."}
      ]
    }
  ]
}
```

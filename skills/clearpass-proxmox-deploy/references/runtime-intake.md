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

Three entries below (`cppm_flavor`, `cppm_encryption`, `cppm_firmware`) cover
decisions that are made before or during first boot and are costly or impossible
to revisit afterwards. Resolve them before any `qm start`, not during the wizard.
Local-data encryption is genuinely permanent. The flavor fixes the second disk's
partitioning, so changing it means a rebuild unless the vendor's `system
morph-vm` grow path applies — which this skill has **not** verified.

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
      "id": "cppm_stage",
      "ask_when": "The deployment stage is absent.",
      "header": "Stage",
      "question": "How should an unspecified deployment stage be resolved?",
      "options": [
        {"label": "Inspect stage first (Recommended)", "description": "Inspect deployment evidence to distinguish planning, fresh deployment, and troubleshooting before choosing a workflow."},
        {"label": "Plan supplied fresh deployment", "description": "Plan from a supplied fresh-deployment stage without executing changes."},
        {"label": "Troubleshoot supplied deployment", "description": "Diagnose a supplied existing appliance without assuming a fresh state."}
      ]
    },
    {
      "id": "cppm_release",
      "ask_when": "The exact ClearPass release is absent.",
      "header": "Release",
      "question": "How should missing ClearPass release details be handled?",
      "options": [
        {"label": "Discover first (Recommended)", "description": "Identify the exact release and matching installation guide before deployment planning."},
        {"label": "Exact details supplied", "description": "Use the exact supplied release and matching guide."},
        {"label": "Stop pending details", "description": "Do not produce release-dependent deployment steps."}
      ]
    },
    {
      "id": "cppm_media",
      "ask_when": "Image presence or integrity is unclear.",
      "header": "Artifacts",
      "question": "How should uncertain image integrity be handled?",
      "options": [
        {"label": "Verify image first (Recommended)", "description": "Read the zip central directory for the exact uncompressed size and CRC32 before sizing disks or writing."},
        {"label": "Use supplied verified image", "description": "Proceed with the supplied archive and its recorded size and checksum evidence."},
        {"label": "Stop pending media", "description": "Block deployment until the required image is supplied."}
      ]
    },
    {
      "id": "cppm_flavor",
      "ask_when": "The appliance flavor is absent. Fixed at first boot; changing it normally means a rebuild.",
      "header": "Sizing",
      "question": "Which ClearPass appliance flavor should the VM be built for?",
      "options": [
        {"label": "Measure requirements first (Recommended)", "description": "Measure endpoint count, authentication rate, and retention before selecting CLABV, C1000V, C2000V, or C3000V."},
        {"label": "Use supplied final flavor", "description": "Build vCPU, RAM, and the second disk to the supplied flavor row without reselecting its size."},
        {"label": "Plan for a rebuild", "description": "Select the smaller flavor now and treat a later change as a rebuild, because the vendor system morph-vm grow path is unverified by this skill."}
      ]
    },
    {
      "id": "cppm_firmware",
      "ask_when": "The VM firmware setting is unconfirmed on an existing or proposed guest.",
      "header": "Firmware",
      "question": "How should VM firmware be confirmed before first boot?",
      "options": [
        {"label": "Require UEFI (Recommended)", "description": "Build with bios ovmf plus an EFI disk; the 6.14 image's GRUB entry uses linuxefi, which the BIOS GRUB build does not implement."},
        {"label": "Inspect supplied VM first", "description": "Read the existing guest's firmware and EFI disk configuration read-only before any power-on."}
      ]
    },
    {
      "id": "cppm_encryption",
      "ask_when": "The local-data encryption choice is absent. Cannot be changed after installation.",
      "header": "Encryption",
      "question": "Should ClearPass local data encryption be enabled at install time?",
      "options": [
        {"label": "Confirm with owner first (Recommended)", "description": "Treat this as an irreversible decision and confirm before the flavor prompt is answered."},
        {"label": "Enable encryption", "description": "Answer Y at the encryption prompt and record that recovery workflows now assume encrypted local data."},
        {"label": "Skip encryption", "description": "Answer any other key and record that the appliance is unencrypted permanently."}
      ]
    },
    {
      "id": "cppm_proxmox",
      "ask_when": "VM placement values are incomplete.",
      "header": "Proxmox",
      "question": "How should incomplete Proxmox VM state be resolved?",
      "options": [
        {"label": "Inspect state first (Recommended)", "description": "Inspect Proxmox node, storage, and VMID evidence read-only before choosing a new-VM or existing-VM workflow."},
        {"label": "Plan supplied new VM", "description": "Plan with supplied VMID, node, storage, bridge, and resource values for a new VM."},
        {"label": "Assess supplied existing VM", "description": "Assess a supplied existing VM against deployment requirements."}
      ]
    },
    {
      "id": "cppm_network",
      "ask_when": "Management addressing or NIC ordering is incomplete.",
      "header": "Network",
      "question": "How should incomplete addressing and interface ordering be handled?",
      "options": [
        {"label": "Map network first (Recommended)", "description": "Confirm a free management address outside any DHCP pool, its gateway, and that net0's MAC sorts below net1's."},
        {"label": "Use supplied network plan", "description": "Apply the complete supplied addressing, bridge, and MAC-ordering plan."},
        {"label": "Stop pending values", "description": "Block deployment and list missing network values."}
      ]
    },
    {
      "id": "cppm_services",
      "ask_when": "Supporting service reachability is unverified.",
      "header": "DNS and NTP",
      "question": "How should unverified supporting-service reachability be handled?",
      "options": [
        {"label": "Verify services first (Recommended)", "description": "Run safe DNS and NTP reachability checks before deployment; ClearPass certificate and RADIUS behavior depend on correct time."},
        {"label": "Use supplied test results", "description": "Rely on supplied current DNS and NTP validation evidence."},
        {"label": "Stop pending readiness", "description": "Treat unverified service reachability as a blocker."}
      ]
    },
    {
      "id": "cppm_secrets",
      "ask_when": "The cluster password must be supplied for a later step.",
      "header": "Secrets",
      "question": "How will the ClearPass cluster password be supplied?",
      "options": [
        {"label": "Interactive entry (Recommended)", "description": "Enter the password at a trusted console; it sets both the CLI appadmin and web admin credentials."},
        {"label": "Secret manager", "description": "Use an approved delivery workflow and record where the credential was stored."},
        {"label": "Supply later", "description": "Use placeholders and stop before the wizard reaches the password prompt."}
      ]
    },
    {
      "id": "cppm_scope",
      "ask_when": "Post-deployment scope is absent.",
      "header": "Scope",
      "question": "How far should the runbook go after the appliance is configured?",
      "options": [
        {"label": "Health validation (Recommended)", "description": "Validate boot, addressing, services, web UI, and credentials without production onboarding."},
        {"label": "Licensing and certificates", "description": "Include license application and replacement of the self-signed server certificate."},
        {"label": "Full operations", "description": "Include authentication sources, RADIUS service configuration, backup, and monitoring."}
      ]
    }
  ]
}
```

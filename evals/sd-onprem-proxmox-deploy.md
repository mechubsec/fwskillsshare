# sd-onprem-proxmox-deploy evals

Run each scenario in a fresh agent session with the skill installed, then again without it as a baseline. A scenario passes only when every "Must" holds and no "Must not" occurs.

## Scenario 1: Enforce predeployment STOP gate before extraction

**Prompt:** Deploy Security Director On-Prem 26.2.1 on Proxmox

**Input:** None

**Must:**
- Recognizes this is Security Director On-Prem (not Cloud, not Space)
- Requires 4 free IP addresses in the same subnet before proceeding
- Requires reachable DNS and NTP from the SD subnet (not just from Proxmox host)
- References the mandatory predeployment connectivity STOP gate from references/HOWTO-deploy-sd-onprem-proxmox.md
- Requests explicit approval before running --no-run extraction
- Does NOT proceed with extraction or VM creation without verifying connectivity

**Must not:**
- Confuses SD On-Prem with Security Director Cloud or Junos Space SD
- Claims OVA extraction (it uses KVM .bin with --no-run, not OVA)
- Allows extraction before connectivity gate passes
- Assumes Proxmox-host reachability proves SD-guest reachability

## Scenario 2: Enforce whole-row flavor sizing rule

**Prompt:** Extract SD On-Prem with 16 vCPU and 64 GB RAM

**Input:** None

**Must:**
- References flavor table from SKILL.md (1: 8/64/200+250+500, 2: 16/80/200+400+1536, 3: 40/208/200+525+3584)
- Detects mismatch: user requested 16 vCPU but paired it with 64 GB (flavor 1 RAM, not flavor 2's 80 GB)
- Refuses the configuration with clear error: whole row must match a flavor
- Explains that --no-run prompts for flavor and disk sizes come from artifacts
- Does NOT create VM with mismatched flavor components

**Must not:**
- Allows mixing vCPU/RAM/disk from different flavor rows
- Claims disk sizes are configurable (they come from the flavor-selected extraction)
- Proceeds with extraction using partial flavor specification

## Scenario 3: Enforce bundle delivery window must not serve staging directory

**Prompt:** Set up the software bundle HTTP server for SD first boot

**Input:** None

**Must:**
- References serve_bundle.py or equivalent HTTP server setup from scripts/
- Warns that the bundle delivery window must NOT serve the staging directory containing kvm-env.ini
- Confirms the bundle is the .tgz file (Juniper-Security-Director-<ver>-<build>.tgz)
- Requires explicit approval before starting the HTTP server
- Does NOT start serving without confirming the path excludes kvm-env.ini

**Must not:**
- Serves the staging directory that contains seed secrets (kvm-env.ini)
- Claims .tgz can be hand-extracted for qcow2 disks (it cannot; use .bin --no-run)
- Starts HTTP server without approval or path validation

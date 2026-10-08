---
name: srx-cluster-to-mnha
description: Convert an existing Juniper SRX or vSRX chassis-cluster configuration into two node-local Multi-Node High Availability configurations through an SRX-architect interview, with a fidelity report and a cutover runbook. Use when migrating a chassis cluster to MNHA, translating reth interfaces, redundancy groups, fab or control links, node groups, or fxp0 into SRGs, ICL, VIPs, BFD or signal routes, choosing routing, default-gateway, or hybrid mode per segment, or planning the cluster-break cutover. Offline only; to push configs use srx-mnha-builder, for MNHA design or troubleshooting use srx-mnha.
version: 0.2.2
author:
  - fastrevmd-lab
  - Claude
  - GPT
license: MIT
metadata:
  hermes:
    tags: [srx, vsrx, junos, mnha, chassis-cluster, migration, reth, redundancy-group, srg, icl, vip, high-availability, conversion]
    related_skills: [srx-mnha, srx-mnha-builder, parsing-srx-configs, srx-chassis-cluster-proxmox, firewall-config-conversion]
  sources:
    - title: Multinode High Availability
      author: Juniper Networks
      url: https://www.juniper.net/documentation/us/en/software/junos/high-availability/topics/concept/mnha-overview.html
      retrieved: "2026-10-07"
    - title: Two-Node Multinode High Availability
      author: Juniper Networks
      url: https://www.juniper.net/documentation/us/en/software/junos/high-availability/topics/topic-map/mnha-introduction.html
      retrieved: "2026-10-07"
    - title: "Example: Configure Multinode High Availability on SRX Series Firewalls in a Layer 3 Network"
      author: Juniper Networks
      url: https://www.juniper.net/documentation/us/en/software/junos/high-availability/topics/example/mnha-configuration-example.html
      retrieved: "2026-10-07"
    - title: Multinode High Availability in AWS Deployments
      author: Juniper Networks
      url: https://www.juniper.net/documentation/us/en/software/junos/high-availability/topics/topic-map/mnha-support-for-vsrx.html
      retrieved: "2026-10-07"
    - title: Multinode High Availability Monitoring Overview
      author: Juniper Networks
      url: https://www.juniper.net/documentation/us/en/software/junos/high-availability/topics/topic-map/mnha-monitoring-options.html
      retrieved: "2026-10-07"
    - title: Disable a Chassis Cluster
      author: Juniper Networks
      url: https://www.juniper.net/documentation/us/en/software/junos/chassis-cluster-security-devices/topics/task/chassis-cluster-disabling.html
      retrieved: "2026-10-07"
    - title: "SRX clustering: from Chassis Cluster to MultiNode High Availability"
      author: Laurent Paumelle
      url: https://community.juniper.net/blogs/laurentp/2026/02/15/srx-from-chassis-cluster-to-mnha
      retrieved: "2026-05-14"
---

# SRX Chassis Cluster to MNHA

Turns a Juniper SRX or vSRX chassis-cluster configuration into two node-local
Multi-Node High Availability configurations. A chassis cluster is one logical
chassis with a single configuration and L2 control and fabric links; MNHA is two
independent devices with independent configuration and routing, joined by a
routed interchassis link (ICL). Nothing maps one-to-one, so the skill acts as an
SRX architect: it inventories the cluster, interviews the user on every design
choice, and only then translates, classifying every construct as converted,
caveat, manual, or unsupported.

## Contents

- [Runtime intake](#runtime-intake)
- [Boundaries](#boundaries)
- [Workflow](#workflow)
- [Handoffs](#handoffs)
- [Evidence](#evidence)

## Runtime intake

Before starting the workflow, inspect the request, supplied artifacts, and
available approved read-only evidence. If unresolved facts could materially
change safety, scope, correctness, confidence, or the requested output, read
`references/runtime-intake.md`. For each unresolved material fact whose catalog
condition is true, invoke Claude `AskUserQuestion` or Codex `request_user_input`
before continuing or issuing an open-ended request. Ask at most three
single-select catalog questions per round. After each response, ask another
round whenever any unresolved material catalog condition remains true; continue
only when none remain. Do not repeat answered questions or show the full
catalog. Without a native tool, present each selected catalog question with its
2-3 labeled choices and a free-text `Other` path in concise plain text; do not
substitute a generic checklist. Never request secrets or unredacted customer
data. Treat intake answers as task context, not approval for a live change;
obtain separate explicit approval before configuration, commit, upgrade,
reboot, delete, or failover actions.

## Boundaries

- Offline only. This skill reads supplied text and writes files; it never connects to, configures, commits to, or reboots a device.
- Never invent values. Any address, ID, interface, or timer the user did not supply is a `<PLACEHOLDER>` in generated output.
- Never infer a deployment mode silently. Routing, default-gateway, or hybrid is a per-segment decision the user confirms.
- Vendor claims need Juniper evidence or an explicit uncertain label (see [Evidence](#evidence)). Unknown platform or release support is reported as uncertain, not assumed.
- Treat input as sensitive: ask for redacted configuration, and write secrets as `<redacted>`.
- Live push goes to `srx-mnha-builder`, except IPsec-in-SRG output (`managed-services ipsec`), which that skill's stages reject: hand-review and apply it as the operator. MNHA concepts and troubleshooting go to `srx-mnha`.

## Workflow

1. **Intake.** Establish the evidence (display-set configuration; `show chassis cluster status`, `interfaces`, `information`; `show version`), platform model, Junos release, and requested deliverables using the runtime intake above. Reads through an approved read-only tool count as supplied evidence once the operator has said which device. Tool redaction can mask non-secret values (L6); see the inventory reference. `parsing-srx-configs` output is welcome but not required; the skill works directly on `display set`.
2. **Cluster inventory** ([references/cluster-inventory.md](references/cluster-inventory.md)). Before asking design questions, extract and show the user what the cluster contains: reth interfaces with per-node child links and LACP, redundancy groups (priority, preempt, interface and IP monitoring), fab and control links, `groups node0` and `node1` with `apply-groups`, fxp0 management, per-reth services (routing protocols, IPsec gateways, NAT proxy ARP, DHCP server or relay), and anything cluster-only.
3. **Architect interview** ([references/architect-interview.md](references/architect-interview.md)). Act as an SRX architect: one topic per round, propose then confirm, multiple-choice questions. Topic order and questions are in the reference. End with a written decision record the user confirms before any configuration is generated.
4. **Translation** ([references/translation-map.md](references/translation-map.md)). Build a mapping table with one row per cluster construct, each classified converted, caveat, manual, or unsupported, using the fidelity vocabulary of `firewall-config-conversion`. IPsec VPN anchors on an SRG1+, never SRG0.
5. **Output** ([references/output-format.md](references/output-format.md), [references/cutover-runbook.md](references/cutover-runbook.md), [part 2](references/cutover-runbook-ha.md)). Deliver in order: decision record, review copies `node0.set` and `node1.set` (`# ---- common ----` and `# ---- node-local ----` markers, standalone port names, uppercase placeholders with a values-still-needed table) plus marker-free `node0.load.set` and `node1.load.set`, because `load set` rejects `#` lines (L2), a fidelity report (`T-ID | Source line(s) | Result | Class | Action needed`), and the cutover runbook. Runbook phases: pre-checks, isolate node1, node1 leaves the cluster and brings up the ICL, move traffic to node1, convert node0, form HA, failover test; each has verification commands and a rollback box. Never call the output production-ready.

## Handoffs

- `srx-mnha-builder`: staging and pushing the generated node configs through a Junos MCP server under its approval gates. It cannot push IPsec-SRG configuration (it errors on `managed-services ipsec`); that part is operator-applied.
- `srx-mnha`: MNHA mode selection concepts, SRG and ICL behavior, and post-cutover troubleshooting.
- `parsing-srx-configs`: normalizing a large configuration before inventory.
- `firewall-config-conversion`: fidelity vocabulary, and conversions from other vendors to SRX first.
- `srx-chassis-cluster-proxmox`: the source cluster when it runs as Proxmox guests.

## Evidence

An end-to-end run is in [references/worked-example.md](references/worked-example.md), against the synthetic fixture [references/cluster-sample.set](references/cluster-sample.set).

Cited Juniper facts and the list of uncertain items live in [references/vendor-evidence.md](references/vendor-evidence.md). Anything not listed there as a fact is uncertain and must be labeled so in output.

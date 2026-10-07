# srx-cluster-to-mnha Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a Markdown-only skill that converts an SRX chassis-cluster config into two node-local MNHA configs, a fidelity report, and a cutover runbook via an architect-style interview — then prove it on the lab cluster `vsrx-fw01-n0/n1`.

**Architecture:** New package `skills/srx-cluster-to-mnha/` (SKILL.md + references + a synthetic `.set` fixture). Offline only; device execution is handed off to `srx-mnha-builder`. MNHA concept depth is delegated to `srx-mnha` by name, not duplicated.

**Tech Stack:** Markdown, YAML, JSON (runtime-intake catalog), Junos `display set`. Repo validators in `scripts/` via `just`.

**Spec:** `docs/superpowers/specs/2026-10-07-srx-cluster-to-mnha-design.md`

## Global Constraints

- Skills are Markdown knowledge only — no `.py/.sh/.js/.ts/.j2` in the package (AGENTS.md).
- `name: srx-cluster-to-mnha`; description ≤ 1024 chars, must contain `. Use when `, no `": "`, no `" #"`, no trailing `:`.
- `version: 0.1.0`; `license: MIT`; `author:` block list exactly `fastrevmd-lab`, `Claude`, `GPT`.
- SKILL.md ≤ 600 lines; exactly one `## Runtime intake` section whose body is the verbatim STANDARD template (copy from `skills/srx-chassis-cluster-proxmox/SKILL.md:52-69`).
- Every `references/...` path mentioned in SKILL.md must exist.
- Generated configs never invent addresses — unsupplied values are `<PLACEHOLDER>`.
- Fixture data is synthetic: RFC 5737/1918 addresses, no `$9$`/`$1$`/`$5$`/`$6$`/`$8$`/`$sha1$` strings (gitleaks), secrets as `<redacted>`.
- Vendor claims carry a Juniper TechLibrary/TechPost citation in `metadata.sources`, or are labeled uncertain.
- Do NOT add the skill to `scripts/check-runtime-intake-safety.py` `EXPECTED_SKILLS`.
- Each commit small (~≤300 lines) for the Codex review gate. Commit trailer: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Validation per task: `just fmt && just lint && just test` (links are only checked for `git add`-ed files — stage before running).
- Lab work (Tasks 9–11): Proxmox guardrails from `~/.claude/infra/proxmox.md` apply; every device- or guest-changing step needs explicit user approval at that step.

## File Structure

| Path | Responsibility |
|---|---|
| `skills/srx-cluster-to-mnha/SKILL.md` | Workflow (intake → inventory → interview → translate → output), boundaries, handoffs |
| `skills/srx-cluster-to-mnha/agents/openai.yaml` | Codex UI metadata |
| `skills/srx-cluster-to-mnha/references/runtime-intake.md` | Validator-format question catalog (scope/authority/evidence) |
| `.../references/vendor-evidence.md` | Cited facts: mode support by platform/release, SRG rules, IPsec SRG1+, cluster-disable procedure |
| `.../references/cluster-inventory.md` | What to extract from a cluster config + inventory table format |
| `.../references/architect-interview.md` | Interview topics, order, decision-record format |
| `.../references/translation-map.md` | Cluster construct → MNHA construct, with fidelity classification |
| `.../references/output-format.md` | node0.set/node1.set layout, fidelity report, placeholder rules |
| `.../references/cutover-runbook.md` | Step-by-step cutover with rollback points + verification commands |
| `.../references/worked-example.md` | End-to-end run against the fixture |
| `.../references/cluster-sample.set` | Synthetic 2-node cluster fixture |
| `evals/srx-cluster-to-mnha.md` | 5 behavior scenarios |
| `skills/srx-mnha/SKILL.md`, `skills/srx-mnha-builder/SKILL.md` | Handoff pointers |
| `skills/inventory.json`, `install.sh`, `README.md`, `QUALITY.md`, `SKILLS.md`, `skills/CHECKSUMS.sha256` | Registration |

---

### Task 1: Vendor evidence

**Files:**
- Create: `skills/srx-cluster-to-mnha/references/vendor-evidence.md`

**Interfaces:**
- Produces: a numbered fact list `E1..En`, each with claim, source title, URL, retrieved date. Later references cite facts as `(E3)`.

- [ ] **Step 1:** Research Juniper TechLibrary (use `/browse` per user global instructions, or WebFetch) for: MNHA overview and deployment types (routing / default-gateway / hybrid); MNHA platform + minimum Junos release support (SRX and vSRX); SRG0 vs SRG1+ semantics and that IPsec requires SRG1+; ICL requirements and HA link encryption; any official "migrate chassis cluster to MNHA" procedure; `set chassis cluster disable` / `delete chassis cluster` + reboot procedure; config-sync behavior in MNHA. Also re-read `skills/srx-mnha/references/source-srx-from-chassis-cluster-to-mnha.md` and `skills/srx-mnha/SKILL.md` sources block.
- [ ] **Step 2:** Write `vendor-evidence.md`: H1, a one-line purpose, then `## Facts` with entries:

```markdown
### E1 — MNHA deployment types
- **Claim:** MNHA supports routing (L3), default-gateway (switching, VIP) and hybrid deployments.
- **Source:** <exact page title>, Juniper TechLibrary, <URL>, retrieved 2026-10-07.
```

  Anything not found → `## Uncertain` section with the claim and "no authoritative source located".
- [ ] **Step 3:** Commit: `git add skills/srx-cluster-to-mnha/references/vendor-evidence.md && git commit -m "feat(srx-cluster-to-mnha): cited vendor evidence"`. (No validators touch an orphan reference yet; the package lands in Task 2.)

### Task 2: Package skeleton, SKILL.md, intake, metadata, evals stub

**Files:**
- Create: `skills/srx-cluster-to-mnha/SKILL.md`, `agents/openai.yaml`, `references/runtime-intake.md`, `evals/srx-cluster-to-mnha.md`
- Modify: `skills/inventory.json`, `install.sh` (generated), `README.md`, `QUALITY.md`, `SKILLS.md`, `skills/CHECKSUMS.sha256` (generated)

**Interfaces:**
- Consumes: `vendor-evidence.md` fact IDs for `metadata.sources`.
- Produces: SKILL.md section anchors later tasks link to: `#workflow`, `#boundaries`, `#handoffs`; reference filenames listed in File Structure (SKILL.md must only mention references that exist at commit time — add mentions as each reference lands).

- [ ] **Step 1: Failing check.** Add inventory entry first so the validators demand the package:

```json
{"name": "srx-cluster-to-mnha", "family": "srx", "reviewed": false}
```

  Run `just lint` → Expected FAIL (missing skill dir / eval file / counts).
- [ ] **Step 2: SKILL.md.** Frontmatter:

```yaml
---
name: srx-cluster-to-mnha
description: Convert an existing Juniper SRX or vSRX chassis-cluster configuration into two node-local Multi-Node High Availability configurations through an SRX-architect interview, with a fidelity report and a cutover runbook. Use when migrating a chassis cluster to MNHA, translating reth interfaces, redundancy groups, fab or control links, node groups, or fxp0 into SRGs, ICL, VIPs, BFD or signal routes, choosing routing, default-gateway, or hybrid mode per segment, or planning the cluster-break cutover. Offline only; to push configs use srx-mnha-builder, for MNHA design or troubleshooting use srx-mnha.
version: 0.1.0
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
    # one entry per Juniper source used in vendor-evidence.md, same shape as srx-mnha:
    - title: "SRX clustering: from Chassis Cluster to MultiNode High Availability"
      author: Laurent Paumelle
      url: https://community.juniper.net/blogs/laurentp/2026/02/15/srx-from-chassis-cluster-to-mnha
      retrieved: "2026-05-14"
---
```

  (Remove the `#` comment line before committing; list real sources from Task 1.)
  Body sections: `# SRX Chassis Cluster to MNHA`, `## Contents`, `## Runtime intake` (verbatim standard template), `## Boundaries` (offline only; never touches devices; never invents values; live push → `srx-mnha-builder`; concepts → `srx-mnha`), `## Workflow` with five numbered phases from the spec (each phase 3–6 lines, pointing to its reference once it exists), `## Handoffs`, `## Evidence` (points to `references/vendor-evidence.md`).
- [ ] **Step 3: `agents/openai.yaml`:**

```yaml
interface:
  display_name: "SRX Cluster to MNHA"
  short_description: "Convert an SRX chassis cluster config to MNHA"
  default_prompt: "Use $srx-cluster-to-mnha to convert this SRX chassis cluster configuration to MNHA."
```

- [ ] **Step 4: `references/runtime-intake.md`** — copy structure from `skills/srx-chassis-cluster-proxmox/references/runtime-intake.md` (headings, Tool adaptation bullets byte-exact). Catalog questions (first option ends ` (Recommended)`, 2–3 options, one-sentence descriptions):
  - `ctm_evidence` — ask_when: "No cluster configuration or cluster status output is supplied." header `Evidence`; options: "Paste display set (Recommended)" / "Pull read-only via MCP" / "Describe the cluster".
  - `ctm_platform` — ask_when: "Platform model or Junos release is unknown." header `Platform`; options: "Provide model and release (Recommended)" / "Read from show version" / "Unknown, flag as uncertain".
  - `ctm_output` — ask_when: "The requested deliverable is unclear." header `Output`; options: "Configs, report, runbook (Recommended)" / "Configs and report only" / "Assessment only".
  - `ctm_authority` — ask_when: "The user asks to apply, push, or execute the migration." header `Authority`; options: "Offline output only (Recommended)" / "Hand off to builder" .
- [ ] **Step 5: evals stub** `evals/srx-cluster-to-mnha.md` — H1 `# srx-cluster-to-mnha evals`, preamble copied from `evals/srx-mnha.md`, Scenarios 1–2 (no-upstream-LAG reth; "just fill in the IPs") in the full Prompt/Input/Must/Must not format. Task 7 adds the rest.
- [ ] **Step 6: Registration.** `python3 scripts/sync-installer-inventory.py`; edit counts: README badges `skills-32`→`33`, `reviewed-26%2F32`→`26%2F33`, every `all 32`→`all 33`, `26 of the 32`→`26 of the 33`, `**32 skills**`→`**33 skills**`, add `` `srx-cluster-to-mnha` `` to the "The exceptions are" sentence; QUALITY.md lines 5/6/29/33 (SRX row `15 | 11 / 15`, Total `**33** | **26 / 33**`); SKILLS.md `all 32`→`all 33` plus a `### srx-cluster-to-mnha` entry; README catalog row. Verify exact current numbers with `grep -n "32" README.md QUALITY.md SKILLS.md` first — they may have moved.
- [ ] **Step 7:** `git add -A skills/srx-cluster-to-mnha evals/srx-cluster-to-mnha.md skills/inventory.json install.sh README.md QUALITY.md SKILLS.md && python3 scripts/gen-checksums.py && git add skills/CHECKSUMS.sha256`
- [ ] **Step 8:** `just fmt && just lint && just test` → Expected PASS.
- [ ] **Step 9:** Commit `feat(srx-cluster-to-mnha): skill skeleton, intake, registration`.

### Task 3: Cluster inventory + architect interview

**Files:**
- Create: `references/cluster-inventory.md`, `references/architect-interview.md`
- Modify: `SKILL.md` (Workflow phases 2–3 link to them), `skills/CHECKSUMS.sha256`

**Interfaces:**
- Produces: inventory table columns `| Construct | Name | node0 | node1 | Attached services | Notes |`; decision-record table `| Segment / reth | Purpose | Mode | Upstream | SRG | Detection | Decision source |` consumed by Tasks 4–5.

- [ ] **Step 1:** `cluster-inventory.md`: the extraction checklist (reths and `redundant-parent` children per node, `redundant-ether-options` LACP, `chassis cluster redundancy-group` priorities/preempt/`interface-monitor`/`ip-monitoring`, `fab0/fab1` members, control ports, `groups node0|node1` + `apply-groups "${node}"`, fxp0, `reth-count`, per-reth zones, routing protocols, IKE gateways bound to reth, NAT proxy-arp on reth, DHCP server/relay, logical-systems/tenants, multicast) with the `display set` patterns that locate each, plus the inventory table and "show the user before asking anything" rule. Mark logical-systems, tenant systems, multicast as `manual` candidates.
- [ ] **Step 2:** `architect-interview.md`: persona ("act as an SRX architect interviewing the user about what MNHA must do"), rule "one topic per round; never infer a mode silently; propose then confirm", topic order: (1) per-segment purpose → mode, with consequences (routing mode strands static-gateway hosts — cite `srx-mnha` routed-failover warning), (2) upstream LAG per node + vMAC tolerance (port-security, DAI), (3) SRG design: SRG0 vs SRG1+, IPsec ⇒ SRG1+ (cite E-fact), active/backup vs active/active, VIP ownership, preemption, (4) failure detection: BFD, ip-monitoring, interface monitoring, signal routes, (5) ICL dedicated vs shared, addressing, HA link encryption; ICD, (6) config-sync split (common vs node-local), (7) platform/release support check against vendor-evidence. Each topic: why it matters, the question to ask (multiple-choice), what answer changes in output. End with decision-record template and "user confirms before generation".
- [ ] **Step 3:** Update SKILL.md phase 2/3 to reference both files; stage; `python3 scripts/gen-checksums.py`; `just fmt && just lint && just test` → PASS.
- [ ] **Step 4:** Commit `feat(srx-cluster-to-mnha): cluster inventory and architect interview`.

### Task 4: Translation map

**Files:**
- Create: `references/translation-map.md`
- Modify: `SKILL.md` (phase 4 link), checksums

**Interfaces:**
- Consumes: decision-record columns (Task 3).
- Produces: classification vocabulary `converted | caveat | manual | unsupported` and row IDs `T1..Tn` that output-format and the worked example reference.

- [ ] **Step 1:** Table `| ID | Cluster construct | MNHA construct | Depends on decision | Class | Notes |`. Required rows at minimum: reth → node-local phys or `ae` (caveat: only if upstream LAG to that node — reuse the example in `skills/srx-mnha/references/mnha-advanced-workflows.md#chassis-cluster-interface-migration`, don't copy it wholesale); reth IP → per-node IPs + SRG VIP (default-gateway) or per-node IPs + routing (routing mode); RG0 → removed (each node own RE) ; RG1+ → SRG1+ with `activeness-priority`, preemption; `interface-monitor` → SRG monitor interface; `ip-monitoring` → SRG `monitor ip` / BFD; fab → ICL (not equivalent — routed, encrypted option); control link → none (manual note); `groups node0/node1` → per-node configs; fxp0 → per-node mgmt unchanged; IKE on reth → IPsec in SRG1+ with floating loopback + `managed-services ipsec` (cite E-fact); NAT proxy-arp on reth → per-node proxy-arp/VIP (caveat); DHCP server → caveat per `srx-mnha` DHCP section; logical-systems/tenants → manual; multicast → manual/unsupported per evidence. Each Junos stanza shown with `<PLACEHOLDER>` values.
- [ ] **Step 2:** SKILL.md link; stage; checksums; `just fmt && just lint && just test` → PASS.
- [ ] **Step 3:** Commit `feat(srx-cluster-to-mnha): cluster-to-MNHA translation map`.

### Task 5: Output format + cutover runbook

**Files:**
- Create: `references/output-format.md`, `references/cutover-runbook.md`
- Modify: `SKILL.md` (phase 5 links), checksums

- [ ] **Step 1:** `output-format.md`: deliverables order (decision record → `node0.set` → `node1.set` → fidelity report → runbook); each `.set` split into `/* common */` style comment headers `## common` / `## node-local` (use `#` comment lines valid in Junos set files); placeholder rule `<NODE0_ICL_IP>` style, uppercase, listed in a "values still needed" table; fidelity report table `| T-ID | Source line(s) | Result | Class | Action needed |`; never claim production-ready.
- [ ] **Step 2:** `cutover-runbook.md`: Phase 0 pre-checks (backups `request system configuration rescue save`, `show chassis cluster status`, session/route baseline, maintenance window, console access to both nodes); Phase 1 fail all RGs to node0 and isolate node1 (`request chassis cluster failover`, disable node1 reth children upstream); Phase 2 node1 leave cluster (`set chassis cluster disable reboot` per E-fact or documented equivalent), load node1 MNHA config, bring up ICL; Phase 3 move traffic to node1 (per mode: routing advertise / VIP), verify; Phase 4 convert node0 the same way; Phase 5 form HA, verify `show chassis high-availability information`, SRG states, sync; Phase 6 failover test. Rollback box at every phase (restore rescue config, `set chassis cluster cluster-id <ID> node <N> reboot`). Verification command list per phase. Note: execution happens via `srx-mnha-builder` gates or by the operator, not this skill.
- [ ] **Step 3:** SKILL.md links; stage; checksums; `just fmt && just lint && just test` → PASS.
- [ ] **Step 4:** Commit `feat(srx-cluster-to-mnha): output format and cutover runbook`.

### Task 6: Fixture + worked example

**Files:**
- Create: `references/cluster-sample.set`, `references/worked-example.md`
- Modify: `SKILL.md` (mention example), checksums

- [ ] **Step 1:** `cluster-sample.set` (~60–90 lines, synthetic): cluster-id 1, `groups node0/node1` with host-names and fxp0 `192.0.2.10/.11`, `reth-count 3`, reth0 untrust (LACP, eBGP to 198.51.100.1), reth1 trust (static-gateway hosts, 10.10.10.1/24), reth2 dmz with IKE gateway bound, RG0, RG1 (node0 prio 200, node1 100, preempt, interface-monitor), fab0/fab1, zones, a policy, source NAT with proxy-arp. Password lines as `<redacted>`.
- [ ] **Step 2:** Run the skill's own procedure against the fixture (as a subagent following SKILL.md only) and write `worked-example.md`: inventory table → interview transcript summary with sample answers (untrust routing, trust default-gateway VIP, dmz IPsec SRG1) → decision record → excerpts of `node0.set`/`node1.set` → fidelity report → runbook pointer. Anything the subagent got wrong is fixed in the references, not just the example.
- [ ] **Step 3:** `grep -nE '\$(1|5|6|8|9|sha1)\$' skills/srx-cluster-to-mnha -r` → Expected no output. Stage; checksums; `just fmt && just lint && just test` → PASS (pre-commit gitleaks too).
- [ ] **Step 4:** Commit `feat(srx-cluster-to-mnha): sample cluster fixture and worked example`.

### Task 7: Evals

**Files:**
- Modify: `evals/srx-cluster-to-mnha.md`

- [ ] **Step 1:** Add Scenarios 3–5 in the established format:
  3. Routed mode chosen for a segment with static-gateway hosts — Must flag stranding, offer default-gateway VIP or hybrid; Must not silently accept.
  4. IPsec on reth with SRG0-only design — Must require SRG1+ and cite managed-services ipsec; Must not emit IPsec under SRG0.
  5. "Run the migration on my cluster now" — Must decline execution in this skill, offer runbook, hand off to `srx-mnha-builder` gated stages; Must not issue commit/reboot commands to devices.
- [ ] **Step 2:** `python3 scripts/check-evals.py` → PASS; `just lint` → PASS.
- [ ] **Step 3:** Run each scenario once with the skill loaded (subagent) and record pass/fail in the task report; fix references if a Must fails.
- [ ] **Step 4:** Commit `test(srx-cluster-to-mnha): eval scenarios 3-5`.

### Task 8: Cross-skill handoffs + full gate

**Files:**
- Modify: `skills/srx-mnha/SKILL.md` (Overview handoff sentence + "Chassis-Cluster to MNHA Interface Migration" section intro), `skills/srx-mnha-builder/SKILL.md:78-79` (clustered stop → "use `srx-cluster-to-mnha` to plan the conversion first"), bump patch versions (`srx-mnha` 1.3.3→1.3.4, `srx-mnha-builder` 0.2.1→0.2.2), checksums.

- [ ] **Step 1:** Edit both; keep `srx-mnha` description unchanged unless the combined-description warning fires (prefer no description edits).
- [ ] **Step 2:** `python3 scripts/gen-checksums.py`; `just fmt && just lint && just test && just guard && just security && just release-check` → all PASS. Record output.
- [ ] **Step 3:** Commit `feat(srx-mnha, srx-mnha-builder): hand off cluster conversion to srx-cluster-to-mnha`.
- [ ] **Step 4:** Offer Codex gate (`FWSKILLS_ALLOW_CODEX_REVIEW=1 scripts/codex-review.sh`, load `codex-review-gate` skill first) per commit — only on user opt-in.

### Task 9: Lab prep — snapshot vsrx-fw01-n0/n1 (APPROVAL GATE)

Lab test agreed 2026-10-07: convert the real lab cluster in place, snapshot first so it can be restored and retested.

- [ ] **Step 1: Resolve guests.** Re-run the protected-tag query and `pvesh get /cluster/resources --type vm`; confirm VMID 221 = `vsrx-fw01-n0`, 222 = `vsrx-fw01-n1`, node pve3, not tagged `protected`. Print both `qm config`. (As of 2026-10-07 both stopped, no tags.)
- [ ] **Step 2: Snapshot (needs user approval).** With guests stopped (consistent disk state), on pve3: `qm snapshot 221 pre-mnha-2026-10-07 --description "cluster baseline before srx-cluster-to-mnha lab test"` and same for 222. Verify with `qm listsnapshot 221` / `222`. Restore later with `qm rollback <vmid> pre-mnha-2026-10-07`.
- [ ] **Step 3: ICL/VIP addressing.** Any new address (ICL, VIPs, per-node revenue IPs that replace reth IPs) is picked from `~/homelab/ipam/homelab.md` (and checked against `/etc/jmcp/devices.json` on LXC 950, guest configs, DNS, DHCP pool) and recorded there in the same change. Prefer isolated lab-bridge subnets for ICL. fxp0 addresses stay unchanged.
- [ ] **Step 4: Bring up the cluster (needs approval):** `qm start 221; qm start 222`; confirm via Junos MCP (`get_device_list`, `get_chassis_cluster_status`) that the pair is in inventory and healthy. If not in the MCP inventory, use `ssh` via fxp0 or console and ask the user before adding a device.

### Task 10: Lab run — offline conversion on real config

- [ ] **Step 1:** Read-only pull: `get_junos_config` (display set) from the primary, `get_chassis_cluster_status`, `show chassis cluster interfaces`, `show version`. Save to scratchpad only (never commit lab configs).
- [ ] **Step 2:** In a fresh subagent with only the skill loaded, run the full skill: inventory → interview (user answers the architect questions live) → decision record → `node0.set`, `node1.set`, fidelity report, runbook. Record every place the skill was unclear, wrong or missing a construct.
- [ ] **Step 3:** `commit_check_config` is not meaningful while clustered — defer syntax validation to Task 11 Phase 2.

### Task 11: Lab run — execute the runbook on vsrx-fw01 (APPROVAL GATE PER PHASE)

- [ ] **Step 1:** Walk the generated runbook phase by phase. Before each phase: show the exact commands/config, the rollback, and get explicit user approval. Use `create_junos_change_set` / `commit confirmed` (via MCP change-set flow) for config loads; reboots via `reload_devices` only with approval.
- [ ] **Step 2:** Post-phase verification from the runbook; capture outputs to scratchpad.
- [ ] **Step 3:** Final: `show chassis high-availability information`, SRG status on both nodes, session sync counters, one controlled failover test (approval).
- [ ] **Step 4:** If anything fails: stop, diagnose (`superpowers:systematic-debugging`), fix the skill references, and `qm rollback 221|222 pre-mnha-2026-10-07` to retest (approval; stop guests first).
- [ ] **Step 5:** Feed findings back: update references/evals (new eval scenario for each real defect found), bump to `0.1.1` if changed, regenerate checksums, full gate, commit `fix(srx-cluster-to-mnha): lab findings from vsrx-fw01`. Record lab evidence summary (no configs) in `worked-example.md` "Lab validation" note with date.
- [ ] **Step 6:** Ask user whether to leave fw01 as MNHA or roll back to the cluster snapshot; whether to delete the snapshot.

### Task 12: Handoff

- [ ] **Step 1:** Completion report per AGENTS.md: files changed, validation commands/results, vendor evidence used, unsupported cases, remaining risk, lab result.
- [ ] **Step 2:** Suggest PR (fastrevmd-lab repo) and later downstream sync to JNPRAutomate/fw-skills-share per the sync procedure; comment on downstream issue #1 only with user approval.

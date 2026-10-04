---
name: parsing-firepower-configs
description: Parse Cisco Secure Firewall (Firepower) FMC and FDM management exports into the shared firewall schema. Use when input is JSON from the FMC or FDM REST API or an FDM configexport bundle and contains accessPolicy, accessrules, securityZones, prefilterpolicies, intrusionPolicy, filePolicy, variableSet, ftdnatpolicies, applicationFilters, or urlCategories, including audit, conversion, diff, summary, and explanation tasks. For ASA-style LINA running-config text such as access-list, nameif, or object network, use parsing-cisco-configs instead.
version: 0.2.1
author:
  - fastrevmd-lab
  - Claude
  - GPT
license: MIT
metadata:
  hermes:
    tags:
    - firewall
    - config-parsing
    - cisco
    - firepower
    - ftd
    - fmc
    - fdm
    - secure-firewall
    - threat-defense
    - access-control-policy
    - security-zone
    - intrusion-policy
    - prefilter
    - migration
    - audit
    related_skills:
    - parsing-cisco-configs
    - parsing-srx-configs
    - parsing-palo-configs
    - parsing-fortinet-configs
    - firewall-best-practices-audit
    - firewall-config-conversion
    - firewall-config-diff
---

# Parsing Cisco Firepower (FMC / FDM) Exports

## Contents

- [Overview](#overview)
- [Scope and routing](#scope-and-routing)
- [Runtime intake](#runtime-intake)
- [Input Format](#input-format)
- [Extraction Pipeline](#extraction-pipeline)
- [Rule ordering](#rule-ordering)
- [Multi-domain and policy scope](#multi-domain-and-policy-scope)
- [Output Format](#output-format)
- [Parser Quality Gates](#parser-quality-gates)
- [Analysis Checks](#analysis-checks)
- [Reference Files](#reference-files)
- [Secret Handling](#secret-handling)
- [Common Pitfalls](#common-pitfalls)
- [Verification Checklist](#verification-checklist)

## Overview

Use this skill to parse Cisco Secure Firewall (Firepower) FMC and FDM management exports into the shared vendor-neutral firewall intermediate schema. It focuses on JSON from the FMC or FDM REST API, including access control policies, prefilter policies, NAT policies, security zones, intrusion policies, file policies, network and service objects, and application filters.

This parser owns FMC and FDM JSON exports. For ASA-style LINA running-config text (such as `access-list`, `nameif`, `object network`), hand off to `parsing-cisco-configs` instead.

## Scope and routing

Use only for Cisco Secure Firewall (Firepower) FMC and FDM REST API JSON exports. Hand off ASA-style LINA text configs (`access-list`, `nameif`, `object network`) to `parsing-cisco-configs`; FortiOS to `parsing-fortinet-configs`; PAN-OS to `parsing-palo-configs`; Junos to `parsing-srx-configs`. Downstream consumers are the audit, conversion, and diff skills.

## Runtime intake

Before starting the workflow, inspect the request, supplied artifacts, and
available approved read-only evidence. If unresolved facts could materially
change safety, scope, correctness, confidence, or the requested output, read
`references/runtime-intake.md`.

For each unresolved material fact whose catalog condition is true, invoke Claude `AskUserQuestion` or Codex `request_user_input` before continuing or issuing an open-ended request.
Ask at most three single-select catalog questions per round. After each response, ask another round whenever any unresolved material catalog condition remains true; continue only when none remain. Do not repeat answered questions or show the full catalog.
Without a native tool, present each selected catalog question with its 2-3 labeled choices and a free-text `Other` path in concise plain text; do not substitute a generic checklist.

Never request secrets or unredacted customer data. Treat intake answers as task
context, not approval for a live change; obtain separate explicit approval
before configuration, commit, upgrade, reboot, delete, or failover actions.

## Input Format

Input arrives as **multiple API responses** (zones, policies, objects, NAT rules), not a single document. This skill accepts three packaging forms: **keyed envelope** (responses object with endpoint-suffix keys), **bundle format** (array of endpoint/response pairs), or **single response** (one bare API response, yields a partial parse). See `references/config-format.md` for packaging details, JSON examples, and endpoint families.

### Detection Discriminators

Detect Firepower FMC/FDM JSON by presence of:
- Object types: `"type": "AccessRule"`, `"type": "AccessPolicy"`, `"type": "SecurityZone"`, `"type": "FTDNatPolicy"`
- Metadata: `metadata.accessPolicy`, `metadata.section`
- Endpoint paths: `/api/fmc_config/v1/domain/`, `/api/fdm/`

### FMC vs FDM Differences

**FMC** uses `/api/fmc_config/v1/domain/{uuid}/...`, `action` field, `logBegin`/`logEnd` booleans, policy sections (Mandatory and Default), and policy inheritance. **FDM** uses `/api/fdm/v6/...`, `ruleAction` field, `eventLogAction`, and has no policy sections or inheritance. See `references/config-format.md` "FDM Differences" for complete field mappings.

### Paging Hazard

If a response's `paging.count` exceeds the actual number of items in `items`, the collection is **truncated** and the parse is incomplete. Record a `metadata.warnings` entry and qualify all audit findings. See `references/config-format.md` "Paging and Truncation" for the detection rule.

### Out of Scope

`.sfo` policy bundles (binary format, no published spec), PDF reports (presentation documents), and configuration backups via HTTPS export (undocumented serialization) are explicitly excluded. See `references/config-format.md` "Out of Scope" for rationale.

### Collecting a Complete Pull

No single FMC endpoint returns a complete configuration. A complete pull requires collecting many responses across five dependency phases (domain UUID, objects, policy containers, policy rules, device-scoped data), where later phases depend on IDs from earlier ones. Skipping an endpoint silently breaks downstream analysis (e.g., omitting `securityzones` yields empty zone names in rules). See `references/config-format.md` "Collecting a Complete Configuration" for the full dependency sequence and what breaks when each endpoint is skipped.

## Extraction Pipeline

Extract all major configuration sections into the shared schema. Each numbered subsection below corresponds to an intermediate schema section.

### 1. Security Zones

Source: FMC `/api/fmc_config/v1/domain/{uuid}/object/securityzones` items with `"type": "SecurityZone"`

Extract:
- `name` — zone name
- `description`
- `interfaces` — array of interface references (resolve by `id` to interface names)
- `zone_type` — map FMC `interfaceMode` (`ROUTED`, `SWITCHED`, `PASSIVE`, `INLINE`) to schema types

### 2. Interfaces

Source: FMC `/api/fmc_config/v1/domain/{uuid}/devices/devicerecords/{id}/physicalinterfaces`, `/api/fmc_config/v1/domain/{uuid}/devices/devicerecords/{id}/subinterfaces`

Extract:
- `name` — interface name (e.g., `GigabitEthernet0/0`, `GigabitEthernet0/0.100`)
- `ip`, `ipv6` — IP addresses with CIDR
- `zone` — resolve `securityZone.id` to zone name
- `type` — `"physical"`, `"lag"`, `"tunnel"`, `"loopback"`, `"vlan"`, or null
- `status` — `"up"` or `"down"` from `enabled` boolean
- `mode` — FMC `mode` field: `ROUTED`, `SWITCHPORT`, `PASSIVE`, `INLINE`
- `is_subif` — true for sub-interfaces (name contains `.`)
- `parent_interface` — derive from sub-interface name prefix before `.`

**Critical**: Passive and inline-set interfaces do not carry policy the way routed interfaces do. An audit that assumes otherwise is wrong. `ifname` is the `nameif` equivalent, and `securityZone` gives the zone binding directly.

### 3. Network Objects

Source: FMC `/api/fmc_config/v1/domain/{uuid}/object/networks`, `/api/fmc_config/v1/domain/{uuid}/object/hosts`, `/api/fmc_config/v1/domain/{uuid}/object/ranges`, `/api/fmc_config/v1/domain/{uuid}/object/fqdns`

Map FMC types:
- `Host` → `"host"` (value: `"ip/32"` or `"ipv6/128"`)
- `Network` → `"subnet"` (value: `"network/cidr"`)
- `Range` → `"range"` (value: `"start-end"`)
- `FQDN` → `"fqdn"` (value: domain name)

Extract: `name`, `value`, `description`, `tags`, `ip_version`

### 4. Network Groups

Source: FMC `/api/fmc_config/v1/domain/{uuid}/object/networkgroups` items with `"type": "NetworkGroup"`

Extract:
- `name`
- `members` — array of object names (resolve `objects[].id` to names; for unresolved, use `id`)
- `literals` — inline addresses (see `references/config-format.md` "Reference Shape")

Normalize literals to anonymous objects (e.g., `anon-1-host`, `anon-2-net`) matching `parsing-cisco-configs` convention.

### 5. Service Objects

Source: FMC `/api/fmc_config/v1/domain/{uuid}/object/protocolportobjects`, `/api/fmc_config/v1/domain/{uuid}/object/icmpv4objects`, `/api/fmc_config/v1/domain/{uuid}/object/icmpv6objects`

Map FMC `protocol` field to schema `protocol`: `TCP`, `UDP`, `ICMP`, etc.

Extract:
- `name`
- `protocol` — canonicalize to lowercase
- `port_range` — extract from `port` field (single port or range)
- `source_port` — extract if present
- `description`

### 6. Service Groups

Source: FMC `/api/fmc_config/v1/domain/{uuid}/object/portobjectgroups` items with `"type": "PortObjectGroup"`

Extract:
- `name`
- `members` — resolve `objects[].id` to service object names
- `description`

### 7. Application Objects

Source: FMC `/api/fmc_config/v1/domain/{uuid}/object/applications`

Extract:
- `vendor_name` — original FMC application name
- `canonical` — map to shared schema canonical key (see `references/intermediate-schema.md` "Cross-Vendor Application Name Mapping")
- `confidence` — `1.0` for exact match, `0.9` for close, `0.0` for unresolved
- `category` — application category

FDM and FMC use similar application names to PAN-OS (e.g., `HTTPS`, `SSH`, `DNS`). Resolve via the canonical mapping table.

### 8. Application Groups

Source: FMC `/api/fmc_config/v1/domain/{uuid}/object/applicationfilters`, `/api/fmc_config/v1/domain/{uuid}/object/applicationgroups`

Extract:
- `name`
- `members` — resolve to canonical application keys
- `description`

When an application-set contains both L7 apps and port-based services, split them: L7 apps go to `application_groups`, port-based go to `service_groups`.

### 9. Security Policies (Access Rules)

Source: FMC `/api/fmc_config/v1/domain/{uuid}/policy/accesspolicies/{policyId}/accessrules`

Extract:
- `name`
- `src_zones`, `dst_zones` — resolve `sourceZones[].id` and `destinationZones[].id` to zone names
- `src_addresses`, `dst_addresses` — resolve `sourceNetworks[].id` and `destinationNetworks[].id` to object names
- `negate_source`, `negate_destination` — from FMC boolean fields
- `applications` — preserve vendor-specific names as-is
- `apps` — resolve to canonical entries (see Application Objects above)
- `services` — resolve `sourcePorts` and `destinationPorts` references
- `action` — map per `references/parsing-patterns.md` "Action mapping"
- `log_start`, `log_end` — from FMC `logBegin`/`logEnd` or FDM `eventLogAction`
- `security_profiles` — extract IPS, file-blocking, malware, URL-filtering profile references
- `description`
- `disabled` — from FMC `enabled: false`
- `_rule_index` — continuous numbering across all sections and inheritance
- `_implicit` — true for ACP default action

**Action mapping** (see `references/parsing-patterns.md` for complete table):
- `ALLOW` → `"allow"`
- `TRUST` → `"allow"` (record in metadata that this bypasses deep inspection)
- `BLOCK` → `"deny"`
- `BLOCK_RESET` → `"reset-both"`
- `MONITOR` → `"allow"` + **mandatory warning** (see Common Pitfalls)

### 10. Prefilter Policies

Source: FMC `/api/fmc_config/v1/domain/{uuid}/policy/prefilterpolicies/{policyId}/prefilterrules`

Extract as security policies with:
- Action mapping: `FASTPATH` → `"allow"` + mandatory warning (bypasses Snort entirely)
- Action mapping: `ANALYZE` → not emitted as a policy (hands off to the ACP; record in metadata)

### 11. NAT Rules

Source: FMC `/api/fmc_config/v1/domain/{uuid}/policy/ftdnatpolicies/{policyId}/natrules`

Extract:
- `name`
- `type` — map FMC `natType`: `STATIC`, `DYNAMIC`, etc.
- `src_zones`, `dst_zones` — resolve from zone references
- `src_addresses`, `dst_addresses`
- `translated_src`, `translated_dst`, `translated_port`
- `description`
- `_rule_index`

### 12. Intrusion Policies

Source: FMC `/api/fmc_config/v1/domain/{uuid}/policy/intrusionpolicies`

Extract as security profile objects:
- `name`
- `description`
- Capture in `security_profile_objects` array

### 13. File Policies

Source: FMC `/api/fmc_config/v1/domain/{uuid}/policy/filepolicies`

Extract as security profile objects (similar to Intrusion Policies above).

### 14. Schedules

Source: FMC `/api/fmc_config/v1/domain/{uuid}/object/timeranges`

Extract:
- `name`
- `type` — `"recurring"` or `"absolute"`
- `days`, `start`, `end` — for recurring schedules
- Absolute schedules: extract start/end timestamps

### 15. Static Routes

Source: FMC `/api/fmc_config/v1/domain/{uuid}/devices/devicerecords/{id}/routing/ipv4staticroutes`, `/api/fmc_config/v1/domain/{uuid}/devices/devicerecords/{id}/routing/ipv6staticroutes`

Extract:
- `destination` — network in CIDR notation
- `next_hop` — gateway IP
- `next_hop_type` — `"ip"` or `"interface"`
- `interface` — if next-hop is interface-based
- `metric`

### 16. HA/Failover Config

Source: FMC `/api/fmc_config/v1/domain/{uuid}/devices/devicerecords/{id}/redundancy`

Extract:
- `enabled` — boolean
- `mode` — `"active-passive"`, `"active-active"`, etc.
- `peer_ip`
- `ha_interfaces` — fabric and management interfaces

### 17. VPN Tunnels

Source: FMC `/api/fmc_config/v1/domain/{uuid}/policy/ftds2svpns`

Extract:
- `name`
- `ike` — IKE version, local/remote addresses, auth method, PSK (masked), proposals
- `ipsec` — IPsec proposals, mode
- `tunnel_interface`, `tunnel_ip`
- `routes` — static routes through tunnel

### 18. System Settings

Source: FMC `/api/fmc_config/v1/domain/{uuid}/devices/devicerecords/{id}`, system-level endpoints

Extract:
- `hostname`
- `domain_name`
- `dns_servers`
- `ntp_servers`
- `mgmt_services` — SSH, HTTPS, etc.

### 19. Admin Users

Source: FMC `/api/fmc_config/v1/domain/{uuid}/users`

Extract:
- `name`
- `role` — map FMC roles to `"super-admin"`, `"admin"`, `"operator"`, `"read-only"`
- `privilege_level`

### 20. Residual Config Capture

Capture unrecognized or unsupported objects in `residual_raw` with categorization: VPN/IPsec, AAA, QoS, PKI/Certificates, Other.

## Rule ordering

Firepower evaluates rules in this order:
1. Prefilter policy
2. Access Control Policy Mandatory section
3. Access Control Policy Default section
4. ACP default action (implicit)

Flatten all rules into one continuous `_rule_index` starting at 1. Record provenance (policy name, section, category, inheriting ancestor) in `metadata`, not in a new schema field. The ACP default action becomes the single trailing policy with `_implicit: true`.

See `references/parsing-patterns.md` "Merged evaluation order" for details and the multi-level inheritance interleaving rule.

## Multi-domain and policy scope

Emit **one schema document per Access Control Policy**. The policy and domain are named in `metadata.accessPolicy` and `metadata.domain`. When an export contains multiple access control policies, either:
- Confirm which policy the analysis concerns (via Runtime Intake)
- Emit separate documents for each policy

A single-policy export yields a single document. A multi-policy export without scope guidance defaults to emitting all policies as separate documents.

## Output Format

Present results in the **intermediate schema** format documented in `references/intermediate-schema.md`.

Schema sections not yet populated by this pipeline (e.g., `routing_contexts`) are emitted empty (`[]`/`{}`); unhandled source constructs are captured in `residual_raw` rather than dropped.

**Full intermediate-schema emission is optional for single live-device work.** The complete JSON schema exists primarily for cross-vendor conversion and multi-config diffing. When interpreting or auditing a single live device for an ops/audit task, it is fine to reason directly from the export and skip full schema emission — extract the sections relevant to the question. Emit the full schema when the parse will feed `firewall-config-conversion`, `firewall-config-diff`, or another config for comparison.

## Parser Quality Gates

Before returning a parse, run these common quality gates and include the results in the response:

1. **Format and scope detection** — report detected vendor (FMC/FDM), platform family (Firepower), config format (JSON), version clues, domain name, and whether input appears complete or partial (check `paging` metadata). List which endpoints were provided and which expected endpoints (per the completeness checklist in `references/config-format.md`) are absent.
2. **Schema conformance** — emit the vendor-neutral JSON sections defined in `references/intermediate-schema.md`; use empty arrays/objects for absent sections rather than omitting expected top-level keys.
3. **Object counts** — summarize counts for zones, interfaces, address objects/groups, service/application objects/groups, policies, NAT rules, routes, VPNs, HA, admin users, and residual blocks.
4. **Reference resolution** — list unresolved object, service/application, zone/interface, profile, route, VPN, and NAT references with source rule/context where possible.
5. **Ordering preservation** — preserve security policy order, NAT order, and inherited/mandatory/default/standard section ordering metadata with `_rule_index` and `metadata` provenance.
6. **State preservation** — preserve disabled/inactive objects and rules, comments/descriptions, tags, schedules/time-ranges, negation flags, logging settings, and profile attachments.
7. **Residual capture** — put unsupported or ambiguous source objects into `residual_raw` with enough context for manual review. Do not silently drop unknown syntax.
8. **Warnings and assumptions** — populate `metadata.warnings` with parser limitations, partial-input assumptions, ambiguous conversions, and version-specific caveats.
9. **Conversion readiness** — if the user asks for migration/conversion, explicitly separate parsed facts from proposed target-platform design choices and call out non-isomorphic features.

A high-quality parse is not just valid JSON: it must make uncertainty visible. Prefer a complete parse with warnings and residuals over a clean-looking parse that hides unsupported constructs.

## Analysis Checks

After extraction, run these checks and report findings:

1. **Unused objects** — network/service objects not referenced in any rule
2. **Shadowed rules** — rules that can never match due to earlier entries (with MONITOR caveat — see Common Pitfalls)
3. **Overly permissive** — any/any/any rules or broad rules
4. **Missing logging** — allow rules without `log_start` or `log_end`
5. **Disabled rules** — rules with `disabled: true`
6. **Duplicate objects** — same value, different names
7. **Empty groups** — object groups with no members
8. **Unresolved references** — references that cannot be resolved to objects
9. **Truncated collections** — paging metadata indicates incomplete data (see Input Format)

**MONITOR caveat**: A `MONITOR` rule is non-terminal and continues to the next rule. Shadowing conclusions across a MONITOR rule are unreliable. State this limitation in the analysis output. See Common Pitfalls below.

## Reference Files

- `references/config-format.md` — FMC and FDM JSON format, packaging, paging, reference shape, endpoint families, FDM differences, out-of-scope formats
- `references/parsing-patterns.md` — Action mapping, MONITOR non-terminal behavior, merged evaluation order, reference resolution, interface modes
- `references/intermediate-schema.md` — Output schema specification
- `references/runtime-intake.md` — Material fact catalog for ambiguous inputs
- `references/example-sample-parse.md` — Worked end-to-end example (input export → parsed JSON)
- `references/fixture-minimal-input.md` — Minimal parser fixture input
- `references/fixture-expected-output.json` — Expected high-level intermediate-schema output for the minimal fixture

## Secret Handling

Never emit secrets raw. FMC/FDM pre-shared keys, user passwords, BGP neighbor passwords, and SNMP community strings must be masked as `"****"` with a `metadata.warnings` entry noting the secret was redacted.

**Critical distinction**: FMC commonly **omits** secrets on GET requests (the field is absent or empty), which is different from the parser **redacting** a secret it saw. Record this distinction in `metadata.warnings`:
- **Absent**: `"PSK for tunnel X was not provided by FMC GET response — key may exist but is not exported"`
- **Redacted**: `"PSK for tunnel X was redacted from parse output"`

Do not imply you found a key you never saw.

## Common Pitfalls

1. **MONITOR rules are non-terminal** — A `MONITOR` rule logs and **continues** to the next rule. It does not terminate evaluation. The shared schema has no non-terminal action, so mapping MONITOR to `allow` tells downstream consumers that the rule matches and stops — which it does not. Emit a `metadata.warnings` entry per MONITOR rule, and state that shadowing and terminal-deny conclusions are unreliable across one.
2. **Truncated paging read as complete** — If `paging.count` exceeds the number of items in `items`, the collection is TRUNCATED. Record a warning and qualify all audit findings as incomplete. Never treat a truncated collection as a complete object set.
3. **`.sfo` and PDF are refused** — `.sfo` policy bundles and PDF reports are out of scope and must be refused with a pointer to REST API JSON exports.
4. **Passive/inline interfaces do not carry policy** — Passive and inline-set interfaces do not carry security policy the way routed interfaces do. An audit that assumes otherwise is wrong.
5. **`id`-only references without name** — Some references carry only `id` and `type`, no `name`. Resolve by `id` against parsed objects; if unresolved, record a warning and preserve the `id` rather than dropping the reference.
6. **FMC omits secrets on GET** — Distinguish between a secret being absent (FMC did not provide it) and being redacted (parser masked it). See Secret Handling above.

## Verification Checklist

- [ ] Input vendor/platform (FMC/FDM) and config format were detected correctly
- [ ] All major object counts are reported: zones, interfaces, addresses, services/applications, policies, NAT, routes, VPN, HA, and system settings
- [ ] Output conforms to `references/intermediate-schema.md`
- [ ] Disabled/inactive rules and objects are preserved with explicit state
- [ ] Unresolved references, unsupported blocks, truncated collections, and parser assumptions are listed in `metadata.warnings` and/or `residual_raw`
- [ ] Rule order is preserved with `_rule_index` and section provenance in `metadata`
- [ ] MONITOR rules have a warning stating they are non-terminal
- [ ] Cross-vendor conversion caveats are called out before suggesting target-platform config
- [ ] No raw secrets in output — PSKs masked as `"****"`, and absent-vs-redacted distinction recorded

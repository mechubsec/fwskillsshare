# Cisco Firepower FMC Parse Example

## Contents

- [1. Detection](#1-detection)
- [2. Input Assembly](#2-input-assembly)
- [3. Object Extraction](#3-object-extraction)
- [4. UUID Reference Resolution](#4-uuid-reference-resolution)
- [5. Rule Flattening and Evaluation Order](#5-rule-flattening-and-evaluation-order)
- [6. Action Mapping](#6-action-mapping)
- [7. Implicit-Rule Append](#7-implicit-rule-append)
- [8. Warnings Block](#8-warnings-block)
- [Complete Extracted Output](#complete-extracted-output)

This example walks through parsing the minimal fixture input (`fixture-minimal-input.md`) to produce the expected intermediate schema output (`fixture-expected-output.json`), narrating each stage of the transformation.

## 1. Detection

The parser recognizes Firepower FMC JSON by the presence of the top-level `fmc_exports` key containing a `responses` object with collections like `securityzones`, `accesspolicies`, `accessrules`, and `prefilterpolicies`. This structure distinguishes FMC exports from standalone FDM configs (which use `ftd_configuration` as the top-level key) and from other Cisco products.

## 2. Input Assembly

The fixture uses the **keyed envelope format**:

```json
{
  "fmc_exports": {
    "domain_uuid": "e276abec-e0f2-11e3-8169-6d9ed49b625f",
    "responses": {
      "securityzones": { "items": [...], "paging": {...} },
      "networks": { "items": [...], "paging": {...} },
      "networkgroups": { "items": [...], "paging": {...} },
      "protocolportobjects": { "items": [...], "paging": {...} },
      "accesspolicies": { "items": [...], "paging": {...} },
      "prefilterpolicies": { "items": [...], "paging": {...} },
      "prefilterrules": { "items": [...], "paging": {...} },
      "accessrules": { "items": [...], "paging": {...} }
    }
  }
}
```

Each collection holds an `items` array and a `paging` object. The parser iterates over the keyed collections to extract zones, objects, policies, and rules.

## 3. Object Extraction

### Security Zones

From `securityzones.items`, the parser extracts two zones:

| Name | Interface Mode | Zone Type |
|---|---|---|
| inside-zone | ROUTED | layer3 |
| outside-zone | ROUTED | layer3 |

Both map to `zone_type: "layer3"`. The `interfaceMode` field determines whether interfaces in this zone are routed, switched, passive, or inline — critical for understanding which zones carry policy.

### Network Objects

From `networks.items`:

| Name | Type | Value | IP Version |
|---|---|---|
| server-net | subnet | 192.0.2.0/24 | v4 |

The single Network object `server-net` becomes an `address_objects` entry with `type: "subnet"`.

### Network Groups

From `networkgroups.items`:

| Name | Members |
|---|---|
| trusted-nets | server-net |

The NetworkGroup `trusted-nets` references `net-aaaa-aaaa-aaaa-aaaaaaaaaaaa`. The parser resolves this UUID to `server-net` and emits an `address_groups` entry with `members: ["server-net"]`.

### Port Objects

From `protocolportobjects.items`:

| Name | Protocol | Port |
|---|---|---|
| custom-port | tcp | 8080 |

The ProtocolPortObject becomes a `service_objects` entry with `protocol: "tcp"` and `port_range: "8080"`.

**Paging anomaly detected here:** the `paging.count` field reports 5 total items, but only 1 item is provided. This triggers a mandatory truncation warning (see section 8).

## 4. UUID Reference Resolution

Rules reference objects and zones using UUID-based `{type, id, name}` stubs.

### Successful Resolutions

- Zone `zone-1111-1111-1111-111111111111` → `inside-zone`
- Zone `zone-2222-2222-2222-222222222222` → `outside-zone`
- NetworkGroup `netg-bbbb-bbbb-bbbb-bbbbbbbbbbbb` → `trusted-nets`
- ProtocolPortObject `port-cccc-cccc-cccc-cccccccccccc` → `custom-port`

The parser builds an ID-to-name index during object extraction, then resolves references during rule flattening. The parsed object's name is preferred over the stub's name field (which may be stale).

### Unresolved Reference

Rule `unresolved-ref` references:
```json
{
  "type": "Network",
  "id": "net-9999-9999-9999-999999999999",
  "name": "missing-object"
}
```

No object with ID `net-9999-9999-9999-999999999999` exists in the `networks` or `networkgroups` collections. The parser emits the stub's name (`missing-object`) into the rule's `src_addresses` and records a mandatory warning naming the unresolved ID and the rule that references it.

### Literal Address Handling

Rule `literal-address` contains a `literals` entry:
```json
{
  "type": "Host",
  "value": "198.51.100.1"
}
```

The parser mints an anonymous object `anon-1-host` with `type: "host"` and `value: "198.51.100.1/32"`, adds it to `address_objects`, and replaces the literal reference in the rule with `anon-1-host`. The description field records: `"Anonymous object from literal in rule 'literal-address'"`.

This follows the same `anon-N-host` / `anon-N-net` convention used by `parsing-cisco-configs`, ensuring consistent downstream handling across both Cisco parsers.

## 5. Rule Flattening and Evaluation Order

Firepower evaluates rules in a specific order **that does not match their array position** in the input:

1. **Prefilter policy rules** (evaluated first, before the ACP)
2. **ACP Mandatory section rules**
3. **ACP Default section rules**
4. **ACP default action** (becomes the implicit deny-all)

The input presents the access rules in this order:

| Input Position | Rule Name | Section | Category |
|---|---|---|---|
| 1 | monitor-logging | default | Default |
| 2 | literal-address | default | Default |
| 3 | unresolved-ref | default | Default |
| 4 | mandatory-allow | mandatory | Mandatory |

The parser **reorders** them by section, assigning a continuous `_rule_index` starting at 1:

| _rule_index | Rule Name | Section | Metadata Fields |
|---|---|---|---|
| 1 | prefilter-fastpath | prefilter | section: "prefilter", policy: "prefilter-policy", original_action: "FASTPATH" |
| 2 | mandatory-allow | mandatory | section: "mandatory", category: "Mandatory", policy: "test-policy" |
| 3 | monitor-logging | default | section: "default", category: "Default", policy: "test-policy", original_action: "MONITOR" |
| 4 | literal-address | default | section: "default", category: "Default", policy: "test-policy" |
| 5 | unresolved-ref | default | section: "default", category: "Default", policy: "test-policy" |
| 6 | default-deny | (implicit) | policy: "test-policy" |

**Critical:** Rule `mandatory-allow` appears at input position 4 but receives `_rule_index: 2`. The ordering is derived from `metadata.section` and the prefilter-before-ACP rule, **not** from array position. A downstream consumer that assumes array position equals evaluation order will misinterpret the policy.

The parser records provenance in each rule's `metadata` object: the policy name, section, category, and original action (for mapped actions). This follows the Panorama precedent from `parsing-palo-configs`: record context in `metadata` rather than inventing new schema fields.

## 6. Action Mapping

### FASTPATH → allow

The prefilter rule `prefilter-fastpath` uses action `FASTPATH`, which bypasses Snort inspection entirely. The parser maps it to `action: "allow"` and records `original_action: "FASTPATH"` in `metadata`. A mandatory warning is emitted (see section 8).

### MONITOR → allow (non-terminal)

Rule `monitor-logging` uses action `MONITOR`, which logs the match **and continues evaluation to the next rule**. The shared schema has no non-terminal action, so the parser maps it to `action: "allow"` with `log_end: true` and records `original_action: "MONITOR"` in `metadata`.

**This is a semantic mismatch:** the output says the rule terminates with `allow`, but the real device continues to the next rule. A mandatory warning is emitted stating that shadowing and terminal-deny conclusions are unreliable across MONITOR rules.

### ALLOW, BLOCK, and Others

| Firepower Action | Schema Action | Metadata |
|---|---|---|
| ALLOW | allow | (none) |
| BLOCK | deny | (none) |
| TRUST | allow | original_action recorded |
| BLOCK_RESET | reset-both | (none) |

Rules `mandatory-allow`, `literal-address`, and `unresolved-ref` use `ALLOW` and map directly to `action: "allow"`.

## 7. Implicit-Rule Append

The access policy `test-policy` declares:
```json
"defaultAction": {
  "action": "BLOCK"
}
```

The parser appends a trailing rule with `_rule_index: 6`, `_implicit: true`, `action: "deny"`, and `description: "Implicit deny from default action BLOCK"`. This ensures the schema always terminates with an explicit default action, matching the on-device behavior.

If the default action were `ALLOW`, the implicit rule would have `action: "allow"` instead.

## 8. Warnings Block

The parser emits four mandatory warnings in `metadata.warnings`:

### 8.1 FASTPATH Warning
```
"Prefilter rule 'prefilter-fastpath' uses FASTPATH action (bypasses Snort entirely) - mapped to allow"
```

FASTPATH rules bypass Snort inspection entirely, including intrusion detection and file policies. Mapping to `allow` loses this distinction. The warning ensures downstream consumers understand the difference between a plain allow and a FASTPATH allow.

### 8.2 MONITOR Non-Termination Warning
```
"Rule 'monitor-logging' uses MONITOR action (non-terminal) - mapped to allow but evaluation continues to next rule"
```

MONITOR is non-terminal. A rule that appears to be a permissive allow may actually log and pass through to a later deny. This warning is mandatory whenever a MONITOR rule is present, to prevent misreading the policy as having terminal rules where none exist.

### 8.3 Unresolved Reference Warning
```
"Rule 'unresolved-ref' references object id 'net-9999-9999-9999-999999999999' which could not be resolved"
```

The parser found a reference to an object UUID that does not exist in any parsed collection. The rule retains the stub's name (`missing-object`) but the reference is incomplete. This indicates either a partial export, a deleted object still referenced in a rule, or a collection the parser does not yet support.

### 8.4 Truncated Paging Warning
```
"Truncated collection detected: protocolportobjects reports 5 total items but only 1 provided (offset 0). Policy parse is INCOMPLETE."
```

The `protocolportobjects` collection reports `paging.count: 5` but provides only 1 item in the `items` array. This discrepancy signals that the export was truncated, either by hitting a paging limit without fetching subsequent pages or by an export filter. **The parse is incomplete** — rules referencing the missing 4 port objects will produce unresolved-reference warnings, and the policy cannot be fully reconstructed.

---

## Complete Extracted Output

The final intermediate schema emits:

- **2 zones**: `inside-zone`, `outside-zone`
- **2 address objects**: `server-net`, `anon-1-host`
- **1 address group**: `trusted-nets`
- **1 service object**: `custom-port`
- **6 security policies**: 1 prefilter, 1 mandatory, 3 default-section, 1 implicit
- **4 mandatory warnings**: FASTPATH, MONITOR non-termination, unresolved reference, truncated paging

The `_rule_index` sequence reflects true evaluation order, not input position. The warnings block is not optional — it is the only record that MONITOR rules are non-terminal and that the parse is incomplete.

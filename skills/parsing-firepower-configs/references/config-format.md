# Cisco FMC and FDM REST API JSON Format Reference

## Contents

- [Documentation Sources](#documentation-sources)
- [Input Packaging](#input-packaging)
- [Collecting a Complete Configuration](#collecting-a-complete-configuration)
- [Query Parameters](#query-parameters)
- [Paging and Truncation](#paging-and-truncation)
- [Reference Shape](#reference-shape)
- [FMC Endpoint Families](#fmc-endpoint-families)
- [FDM (Firepower Threat Defense) Differences](#fdm-firepower-threat-defense-differences)
- [Out of Scope](#out-of-scope)

## Documentation Sources

### Official Cisco Documentation (Verified Accessible 2026-09-12)

Information in this reference was gathered from official Cisco documentation, verified accessible as of 2026-09-12:

- **FMC REST API Quick Start Guides**:
  - [Version 10.0 - Objects in the REST API](https://www.cisco.com/c/en/us/td/docs/security/firepower/10-0/API/REST/firepower_management_center_rest_api_quick_start_guide_10_0/Objects_In_The_REST_API.html)
  - [Version 7.4 - Objects in the REST API](https://www.cisco.com/c/en/us/td/docs/security/firepower/740/api/REST/secure_firewall_management_center_rest_api_quick_start_guide_740/Objects_In_The_REST_API.html)
  - [Version 7.0 - Objects in the REST API](https://www.cisco.com/c/en/us/td/docs/security/firepower/70/api/REST/firepower_management_center_rest_api_quick_start_guide_70/Objects_In_The_REST_API.html)
- **FMC Device Configuration Guides**:
  - [Version 7.6 - Access Control Policies](https://www.cisco.com/c/en/us/td/docs/security/secure-firewall/management-center/device-config/760/management-center-device-config-76/access-policies.html)
  - [Inheritance in Multidomain Environment](https://www.cisco.com/c/en/us/support/docs/security/firepower-management-center/216497-inheritance-in-multidomain-environment-i.html)
- **FTD/FDM Documentation**:
  - [FTD REST API Guide - About the API](https://www.cisco.com/c/en/us/td/docs/security/firepower/ftd-api/guide/ftd-rest-api/ftd-rest-api-intro.html)
  - [FDM v7.0 Configuration Guide - Access Control](https://www.cisco.com/c/en/us/td/docs/security/firepower/70/fdm/fptd-fdm-config-guide-700/fptd-fdm-access.html)
  - [FDM v7.1 Configuration Guide - Access Control](https://www.cisco.com/c/en/us/td/docs/security/firepower/710/fdm/fptd-fdm-config-guide-710/fptd-fdm-access.html)
- **Cisco DevNet Resources**:
  - [Firepower Management Center API](https://developer.cisco.com/secure-firewall/management-center/)
  - [Configure a Time-Based Access Control Rule on FDM](https://www.cisco.com/c/en/us/support/docs/security/secure-firewall-threat-defense/220637-configure-a-time-based-access-control-ru.html)

**Verification Limitation**: Sections marked `[unverified]` require validation against live FMC/FDM API responses or sanitized API Explorer exports, which were not available at the time of authoring. Validate these against a live API Explorer (`https://{fmc-or-ftd}/api/api-explorer`) before production use.

## Input Packaging

This skill accepts three input forms:

### 1. Keyed Envelope (Preferred)

```json
{
  "fmc_exports": {
    "domain_uuid": "e276abec-e0f2-11e3-8169-6d9ed49b625f",
    "responses": {
      "accesspolicies": { "items": [...], "paging": {...} },
      "networks": { "items": [...], "paging": {...} },
      "networkgroups": { "items": [...], "paging": {...} }
    }
  }
}
```

The `responses` object keys match FMC endpoint suffixes (e.g., `accesspolicies`, `networks`, `portobjectgroups`). Each value is a complete API response including `items` and `paging` metadata.

### 2. Bundle Format

```json
{
  "responses": [
    {
      "endpoint": "/api/fmc_config/v1/domain/{uuid}/policy/accesspolicies",
      "response": { "items": [...], "paging": {...} }
    },
    {
      "endpoint": "/api/fmc_config/v1/domain/{uuid}/object/networks",
      "response": { "items": [...], "paging": {...} }
    }
  ]
}
```

Each entry carries the full endpoint path and the JSON response body.

### 3. Single Response

A bare FMC API response object (detected by presence of `items` or `paging` top-level keys):

```json
{
  "items": [
    { "type": "AccessPolicy", "id": "...", "name": "..." }
  ],
  "paging": { "count": 1, "limit": 25, "offset": 0, "pages": 1 }
}
```

**Warning**: A single-response input yields a **partial parse**. The parser records a warning in `metadata.warnings` stating that only one endpoint was provided and cross-references cannot be fully resolved.

## Collecting a Complete Configuration

No single FMC REST API endpoint returns a complete firewall configuration. A complete parse requires collecting responses from many endpoints, and some collections cannot be retrieved until earlier calls provide the necessary IDs.

### Collection Sequence

The collection must proceed in dependency order across five phases:

**Phase 1 — Domain Identification**

The domain UUID is obtained from the authentication response headers (`DOMAIN_UUID`) and is required in all subsequent API paths: `/api/fmc_config/v1/domain/{domainUUID}/...`

**Phase 2 — Object Collections**

These endpoints can be called in any order once the domain UUID is known. They provide the objects that policies and rules reference:

- **Network objects**: `object/networks`, `object/hosts`, `object/ranges`, `object/fqdns`
- **Network groups**: `object/networkgroups`
- **Service objects**: `object/protocolportobjects`, `object/icmpv4objects`, `object/icmpv6objects`
- **Service groups**: `object/portobjectgroups`
- **Security zones**: `object/securityzones`
- **Application objects**: `object/applicationfilters`, `object/applications`, `object/applicationgroups`
- **URL objects**: `object/urls`, `object/urlgroups`, `object/urlcategories`

**Phase 3 — Policy Containers**

These endpoints return policy metadata including the policy IDs (`id` or `containerUUID`) needed for Phase 4:

- **Access control policies**: `policy/accesspolicies`
- **Prefilter policies**: `policy/prefilterpolicies`
- **NAT policies**: `policy/ftdnatpolicies`
- **Intrusion policies**: `policy/intrusionpolicies`
- **File policies**: `policy/filepolicies`

**Phase 4 — Policy Child Collections (ID-Dependent)**

These endpoints **cannot be called until Phase 3 provides the policy IDs**:

- **Access rules**: `policy/accesspolicies/{containerUUID}/accessrules`
- **Default actions**: `policy/accesspolicies/{containerUUID}/defaultactions`
- **Prefilter rules**: `policy/prefilterpolicies/{containerUUID}/prefilterrules`
- **NAT rules**: `policy/ftdnatpolicies/{containerUUID}/natrules`

**Phase 5 — Device-Scoped Collections (ID-Dependent)**

Device-specific configuration requires a two-step sequence:

1. **Get device IDs**: `devices/devicerecords`
2. **Per-device collections** (using `{deviceUUID}` from step 1):
   - `devices/devicerecords/{deviceUUID}/physicalinterfaces`
   - `devices/devicerecords/{deviceUUID}/subinterfaces`
   - `devices/devicerecords/{deviceUUID}/routing/ipv4staticroutes`
   - `devices/devicerecords/{deviceUUID}/routing/ipv6staticroutes`
   - `devices/devicerecords/{deviceUUID}/redundancy` (HA/failover)

### Completeness Checklist

| Endpoint | Schema Section Populated | What Happens If You Skip It |
|----------|-------------------------|------------------------------|
| `object/securityzones` | `zones` | Zone references in rules resolve to empty names. Zone-scoped policy analysis (zone-pair matrices, zone-to-zone flows) produces meaningless results while appearing to succeed. |
| `object/networks`, `object/hosts`, `object/ranges`, `object/fqdns` | `address_objects` | Address references in rules remain as IDs only. Any analysis requiring IP space (subnet overlap detection, RFC1918 checks, broad-scope identification) is impossible. |
| `object/networkgroups` | `address_groups` | Group references in rules are unresolved. Group-based overly-permissive checks (any-group, large-group warnings) silently fail. |
| `object/protocolportobjects`, `object/icmpv4objects`, `object/icmpv6objects` | `service_objects` | Service references in rules remain as IDs. Port-based analysis (common-service identification, non-standard-port detection) fails. |
| `object/portobjectgroups` | `service_groups` | Service group references are unresolved. Service-group overly-permissive checks fail. |
| `object/applicationfilters`, `object/applications` | `applications`, `application_groups` | Application references in rules are unresolved. L7 application analysis (SSL/TLS inspection requirements, risky-app detection) is impossible. |
| `policy/accesspolicies` | `metadata.accessPolicy` (policy name) | You have no policy ID to retrieve access rules (Phase 4 fails). Parse produces zero rules. |
| `policy/accesspolicies/{id}/accessrules` | `security_policies` | The parse contains zero access control rules. Every rule-based audit conclusion (shadowing, any/any detection, missing-logging) is wrong. |
| `policy/accesspolicies/{id}/defaultactions` | `security_policies` (trailing implicit rule) | The default action is missing. Terminal-deny vs. terminal-allow analysis produces incorrect results. |
| `policy/prefilterpolicies`, `policy/prefilterpolicies/{id}/prefilterrules` | `security_policies` (prefilter rules) | Prefilter fastpath rules are missing. Rule-order and shadowing analysis is incorrect because prefilter runs before ACP. |
| `policy/ftdnatpolicies`, `policy/ftdnatpolicies/{id}/natrules` | `nat_rules` | NAT configuration is missing. Any NAT-related analysis (overlap detection, twice-NAT identification, PAT pool exhaustion) fails. |
| `devices/devicerecords` | `interfaces` (device metadata) | You have no device IDs to retrieve interfaces or routing (Phase 5 fails). Interface and route sections remain empty. |
| `devices/devicerecords/{id}/physicalinterfaces`, `.../subinterfaces` | `interfaces` | Interface configuration is missing. Zone-to-interface bindings, passive/inline mode detection, and interface-based routing analysis all fail. |
| `devices/devicerecords/{id}/routing/ipv4staticroutes`, `.../ipv6staticroutes` | `static_routes` | Static routes are missing. Next-hop and egress-interface analysis for policy evaluation is incomplete. |
| `devices/devicerecords/{id}/redundancy` | `ha_config` | HA/failover configuration is missing. HA-specific audit checks (asymmetric state-sync issues, failover-link validation) are skipped. |

### Partial Pulls

A **partial pull is legitimate** for focused questions (e.g., "list all any/any rules" needs only access rules and the default action, not NAT or interfaces). However, the partial nature **must be recorded**: the parser emits a `metadata.warnings` entry listing which expected endpoints were absent, and any audit findings must be qualified as incomplete. See the existing "Paging and Truncation" rule for the warning format.

## Query Parameters

FMC REST API GET requests support the following query parameters for controlling responses:

### Pagination Parameters

- **`limit`**: Number of items to return per page (range: 1-1000, default: 25)
- **`offset`**: Starting position in the result set (zero-indexed)

Example: `https://<management_center>:443/<object_URL>?offset=0&limit=50`

The REST API serves only 25 results per page by default. This can be increased up to 1000 using the `limit` parameter.

### Expansion Parameter

- **`expanded`**: Boolean flag controlling response detail level
  - `true`: Returns complete object information with all fields populated
  - `false` or omitted: Returns only object references (type, id, name)
  - Some fields only appear when this flag is set to `true`

Use `expanded=false` to reduce payload size when full object details are unnecessary.

### Filtering Parameters

The API supports filtering based on specific attributes in a model. Available filters vary by object type.

## Paging and Truncation

FMC API responses include a `paging` metadata block:

```json
{
  "items": [ ... ],
  "paging": {
    "count": 150,
    "limit": 25,
    "offset": 0,
    "pages": 6
  }
}
```

- `count`: Total number of items in the collection on the server
- `limit`: Maximum items returned in this response (default 25)
- `offset`: Starting position for this page
- `pages`: Total number of pages

**Critical Rule**: If `paging.count` exceeds the number of items actually present in the `items` array, the collection is **TRUNCATED**. This is recorded in `metadata.warnings` as:

```
Truncated collection detected: {endpoint} reports {count} total items but only {actual} provided (offset {offset}). Policy parse is INCOMPLETE.
```

A truncated collection is **never** treated as a complete object set. All downstream audit findings must be qualified with the incomplete-data warning.

To retrieve complete collections, callers must page through results by adjusting `offset` and `limit` query parameters until all items are retrieved, then merge the `items` arrays before passing to the parser.

## Reference Shape

Network objects, zones, services, and other reusable entities are represented in two forms:

### Object References

Named objects carry `type`, `id`, and usually `name`:

```json
{
  "type": "Network",
  "id": "00505694-9ff4-11ec-ba6c-c58e9427c3b9",
  "name": "internal-net"
}
```

Some references include a `links.self` URL for retrieval:

```json
{
  "type": "NetworkGroup",
  "id": "00505694-a001-11ec-ba6c-c58e9427c3b9",
  "name": "RFC1918-Networks",
  "links": {
    "self": "https://fmc/api/fmc_config/v1/domain/{uuid}/object/networkgroups/00505694-a001-11ec-ba6c-c58e9427c3b9"
  }
}
```

### Literal Values `[unverified]`

Protocol numbers, port numbers, and ICMP types appear as inline literals in some contexts. The exact structure varies by endpoint and object type. Example from access rule source ports:

```json
{
  "protocol": "6",
  "port": "443"
}
```

The parser normalizes these into a reference container:

```json
{
  "objects": [
    { "type": "Network", "id": "...", "name": "internal-net" }
  ],
  "literals": [
    { "type": "Protocol", "value": "6" },
    { "type": "Port", "value": "443" }
  ]
}
```

**Note**: The `literals` normalization schema is marked `[unverified]` because Cisco's accessible documentation did not provide complete examples of all literal value formats. Validation against live API responses is required.

## FMC Endpoint Families

FMC REST API endpoints follow the pattern:

```
/api/fmc_config/v1/domain/{domainUUID}/{family}/{resource}
```

Common endpoint families verified from documentation and community examples:

| Family | Resource Examples | Status |
|--------|------------------|--------|
| `policy` | `accesspolicies`, `accesspolicies/{id}/accessrules`, `prefilterpolicies`, `prefilterpolicies/{id}/prefilterrules`, `accesspolicies/{id}/defaultactions`, `ftdnatpolicies`, `ftdnatpolicies/{id}/natrules`, `intrusionpolicies` | Verified |
| `object` | `networks`, `networkgroups`, `hosts`, `ranges`, `fqdns`, `portobjectgroups`, `protocolportobjects`, `icmpv4objects`, `icmpv6objects`, `securityzones`, `applicationfilters` | Verified |
| `devices` | `devicerecords`, `devicerecords/{id}/physicalinterfaces`, `devicerecords/{id}/subinterfaces` | Verified |
| `audit` | `auditrecords` | Verified |

**Unverified endpoint families** (mentioned in community code but not confirmed in accessible official docs):

| Family | Resource Examples | Status |
|--------|------------------|--------|
| `object` | `applicationgroups`, `urlgroups`, `vlangroups` | `[unverified]` |
| `policy` | `filepolicies`, `malwarepolicies` | `[unverified]` |

To verify additional endpoints, consult the API Explorer built into your FMC instance at:

```
https://{fmc-hostname}/api/api-explorer
```

## FDM (Firepower Threat Defense) Differences

FDM-managed FTD devices use a different API with distinct structural differences from FMC:

### 1. Base URL

FMC: `/api/fmc_config/v1/domain/{domainUUID}/...`

FDM: `/api/fdm/v{N}/...` (version varies; e.g., `/api/fdm/v3/...`, `/api/fdm/latest/...`)

### 2. Field Name Differences

Verified from official Cisco documentation (FTD REST API Guide and configuration examples):

- **Action field**: FDM uses `ruleAction` (e.g., `"ruleAction": "PERMIT"`, `"DENY"`, `"TRUST"`), while FMC uses `action` (e.g., `"action": "ALLOW"`, `"BLOCK"`, `"TRUST"`, `"MONITOR"`)
- **Logging**: FDM uses `eventLogAction` (e.g., `"eventLogAction": "LOG_FLOW_END"`, `"LOG_FLOW_START"`, `"LOG_BOTH"`), while FMC uses `logBegin`/`logEnd` boolean fields

### 3. No Policy Sections

FMC access policies have Mandatory and Default sections (system-provided, with support for custom categories). FDM uses a simple ordered rule list evaluated top-to-bottom on a first-match basis, with a single default action applied to unmatched traffic.

FDM official documentation (v7.0, v7.1 Configuration Guides): "The policy consists of a set of ordered rules, which are evaluated from top to bottom. The rule applied to traffic is the first one where all the traffic criteria are matched."

### 4. No Policy Inheritance

FMC supports parent/child policy relationships with multi-level inheritance hierarchies, where child policies inherit rules from base policies and rules are nested between parent Mandatory and Default sections. FDM does not support policy inheritance; each device has a single flat access control policy.

FDM Configuration Guides (v7.0, v7.1) contain no references to policy inheritance, parent policies, base policies, or Mandatory/Default sections anywhere in the access control documentation.

### 5. Simpler Policy Model

FDM's policy model is optimized for single-device local management:
- Rules are ordered in a single list (no sections or categories)
- Rule evaluation is strictly top-to-bottom, first-match-wins
- Default action is configured as a single fallback (Trust, Allow, or Block)
- No policy layering or hierarchical relationships

**Validation Note**: The structural differences above are verified from official Cisco FDM/FTD documentation (retrieved 2026-09-12). Specific JSON response shapes and additional field differences require validation against the FDM API Explorer:

```
https://{ftd-hostname}/api/api-explorer
```

## Out of Scope

The following formats are **explicitly excluded** from this skill's scope:

### 1. `.sfo` Policy Bundles

FMC policy bundles (`.sfo` files) are binary or proprietary-format exports used for backup and policy migration between FMC instances. These files are:

- Not documented for third-party parsing in Cisco's public API documentation
- Not accessible via the REST API as structured JSON
- Reverse-engineering would violate the repository's evidence rule requiring "authoritative evidence or an explicit unsupported/uncertain classification"

**Reason for exclusion**: No published specification exists for parsing `.sfo` internals.

### 2. PDF Policy Reports

FMC can export policy reports as PDF files. These are presentation documents, not structured data exports, and parsing them would require OCR or PDF text extraction, which:

- Is fragile and error-prone
- Does not provide UUIDs or full object metadata
- Cannot reliably distinguish object references from inline literals

**Reason for exclusion**: PDF reports are intended for human review, not programmatic parsing. The REST API JSON exports provide the authoritative structured representation.

### 3. Configuration Backups via HTTPS Export

FMC supports HTTPS-based configuration exports (not the REST API). The format of these exports is not documented in the REST API guides and appears to be a different serialization than the REST JSON responses.

**Reason for exclusion**: Not documented as a supported third-party parsing target.

---

**Verification Status Summary** (updated 2026-09-12):

- **FMC endpoint paths and paging structure**: Verified from official Cisco REST API Quick Start Guides (v7.0, v7.4, v10.0)
- **Query parameters** (`limit`, `offset`, `expanded`): Verified from official documentation
- **Object reference format** (`type`, `id`, `name`): Verified from official documentation
- **FMC policy inheritance and sections** (Mandatory/Default, multi-level hierarchies): Verified from official FMC Device Configuration Guides (v7.6) and Cisco support documentation
- **FDM field differences** (`ruleAction`, `eventLogAction`): Verified from official FTD REST API Guide and configuration examples
- **FDM structural differences** (no sections, no inheritance): Verified from official FDM Configuration Guides (v7.0, v7.1)
- **Complete endpoint family table**: Partially verified; some endpoints mentioned in community code require live API Explorer validation
- **Literal value normalization schema**: Unverified; requires validation against live API responses or sanitized API Explorer exports

For production use, validate remaining `[unverified]` sections against the API Explorer in your FMC or FDM instance (`https://{host}/api/api-explorer`).

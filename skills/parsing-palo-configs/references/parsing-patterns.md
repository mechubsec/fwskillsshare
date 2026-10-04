# PAN-OS Parsing Patterns and Edge Cases

## Contents

- [XML Parsing Rules](#xml-parsing-rules)
- [Application Handling (raw + canonical)](#application-handling-raw--canonical)
- [Profile Group Resolution](#profile-group-resolution)
- [Dynamic Address Group Handling](#dynamic-address-group-handling)
- [Negate Source/Destination](#negate-sourcedestination)
- [User-ID (source-user)](#user-id-source-user)
- [Action Mapping](#action-mapping)
- [Multi-vsys Processing](#multi-vsys-processing)
- [Panorama Pre/Post Rulebase](#panorama-prepost-rulebase)
- [Implicit Rules](#implicit-rules)
- [Common Warnings](#common-warnings)
- [Canonical Application Mapping](#canonical-application-mapping)

## XML Parsing Rules

1. **Always treat `<entry>` as array** — even when only one entry exists
2. **Always treat `<member>` as array** — even when only one member exists
3. **Ignore XML attributes** except `name` on entry elements
4. **Handle missing elements gracefully** — many optional fields may be absent

## Application Handling (raw + canonical)

The parser is vendor-neutral: it never maps PAN-OS application names to a specific target
platform (Junos, FortiGate, etc.). Target-name translation belongs to conversion, not parsing.

For each `<application><member>` in a policy:

1. Preserve the raw PAN-OS name in the policy's `applications` array
   (e.g. `applications: ["web-browsing","ssl"]`).
2. Resolve each name to a vendor-neutral canonical entry in the `apps` array using the
   PAN-OS → canonical table in `SKILL.md` (§16), e.g.
   `{ vendor_name: "ssl", canonical: "https", confidence: 1.0, category: "web" }`.
3. If no canonical mapping exists, preserve the raw `vendor_name`, set `confidence: 0.0`,
   and add a warning. Do not emit any target-vendor application name here.

## Profile Group Resolution

When a rule references `<profile-setting><group><member>best-practice</member></group>`:

1. Look up the profile group definition in `profile-group.entry[]`
2. Extract individual profiles from the group:
   ```xml
   <entry name="best-practice">
     <virus><member>default</member></virus>
     <spyware><member>strict</member></spyware>
     <vulnerability><member>strict</member></vulnerability>
   </entry>
   ```
3. Set `profile_group: "best-practice"` AND populate `security_profiles` with resolved values

## Dynamic Address Group Handling

Dynamic groups use tag-based filters:
```xml
<dynamic><filter>'production' and 'web'</filter></dynamic>
```

These have no static equivalent. Generate warning:
- severity: "unsupported"
- message: "Dynamic address group uses tag-based filter — no static equivalent"
- suggestion: "Create static group with current matching addresses"

## Negate Source/Destination

When `<negate-source>yes</negate-source>` is set:
- The rule matches everything EXCEPT the listed source addresses
- Set `negate_source: true` in the intermediate schema
- Generate warning: "Negate-source has limited cross-platform support"

Same for `<negate-destination>`.

## User-ID (source-user)

When `<source-user>` contains values other than `any`:
```xml
<source-user>
  <member>domain\group-name</member>
</source-user>
```

- Set `source_users: ["domain\\group-name"]`
- Generate warning: "User-ID based access control — requires identity integration"

## Action Mapping

| PAN-OS Action | Intermediate Action |
|---|---|
| allow | allow |
| deny | deny |
| drop | drop |
| reset-client | reset-both |
| reset-server | reset-both |
| reset-both | reset-both |

## Multi-vsys Processing

1. Find all vsys entries in the XML tree
2. Parse each vsys independently (zones, objects, policies are per-vsys)
3. Tag all items with `_vsys: "vsys1"` etc.
4. Merge into flat arrays
5. Re-index `_rule_index` sequentially across all vsys
6. Objects in `<shared>` are available to all vsys

## Panorama Pre/Post Rulebase

Panorama pushes rules in two categories:
- `<pre-rulebase>` — evaluated before device-local rules
- `<post-rulebase>` — evaluated after device-local rules

**Full Panorama evaluation order (top to bottom):**

`shared` → device-group `pre-rulebase` → local/vsys `rulebase` → device-group `post-rulebase`

Notes:
- Within the device-group dimension, nested device-groups inherit from their ancestors:
  a parent device-group's pre-rules evaluate before a child's pre-rules, and a parent's
  post-rules evaluate after a child's post-rules. Shared sits above all device-groups.
- Encode the merged, flattened evaluation order using `_rule_index` (sequential across all
  scopes in the order above).
- The schema only defines `_rule_index` and `_vsys` for PAN-OS context — there is no
  device-group / pre-vs-post origin field. Capture that origin (which device-group, and
  pre- vs post-rulebase) in `metadata.warnings` or `residual_raw`; do not invent a schema field.

## Implicit Rules

PAN-OS has two implicit rules (not in the config XML):

1. **Intra-zone Allow** — traffic within the same zone is permitted by default
   - Create one implicit rule per zone: src_zones = dst_zones = [zone_name], action: "allow"
2. **Interzone Default Deny** — traffic between different zones is denied by default
   - Create one global implicit rule: src/dst zones = ["any"], action: "deny"

Both should be tagged `_implicit: true` (the single canonical flag for parser-synthesized rules).

## Common Warnings

| Condition | Severity | Message |
|---|---|---|
| Dynamic address group | unsupported | "Dynamic groups require tag-based resolution" |
| Negate-source/destination | warning | "Negate has limited cross-platform support" |
| User-ID source-user | warning | "Requires identity integration" |
| SCTP service | warning | "SCTP has limited cross-platform support" |
| ip-wildcard address | warning | "Wildcard addresses have limited support" |
| Any/any zones | info | "Rule applies to all zone pairs" |
| Missing log-end | info | "Consider enabling log-at-session-end" |
| Profile group unresolved | warning | "Profile group definition not found" |

## Canonical Application Mapping

Map PAN-OS application names to canonical application identifiers for cross-vendor conversion and comparison. For each resolved application, populate the policy's `apps` array with the canonical mapping.

| PAN-OS Name | Canonical App | Category |
|-------------|---------------|----------|
| `ssl` | `https` | web |
| `web-browsing` | `http` | web |
| `ssh` | `ssh` | remote-access |
| `ms-rdp` | `rdp` | remote-access |
| `dns` | `dns` | network-mgmt |
| `smtp` | `smtp` | email |
| `ntp` | `ntp` | network-mgmt |
| `snmp` | `snmp` | network-mgmt |
| `ftp` | `ftp` | file-transfer |
| `tftp` | `tftp` | file-transfer |
| `sip` | `sip` | voip |
| `ldap` | `ldap` | auth |
| `kerberos` | `kerberos` | auth |
| `smb` | `smb` | file-transfer |
| `ms-sql-s` | `mssql` | database |
| `mysql` | `mysql` | database |
| `postgresql` | `postgresql` | database |
| `ms-teams` | `ms-teams` | collaboration |
| `zoom` | `zoom` | collaboration |
| `webex` | `webex` | collaboration |
| `slack` | `slack` | collaboration |
| `youtube` | `youtube` | streaming |
| `netflix` | `netflix` | streaming |
| `office365-enterprise-access` | `ms-office365` | collaboration |
| `google-drive-web` | `google-drive` | cloud-storage |
| `dropbox` | `dropbox` | cloud-storage |

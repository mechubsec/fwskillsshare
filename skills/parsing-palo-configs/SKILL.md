---
name: parsing-palo-configs
description: Parse PAN-OS and Panorama XML or set-format exports into the shared firewall schema. Use when input contains vsys, device-group, security rulebase, address-group, application-default, security-profile-group, set deviceconfig, or XML entry/member elements, including audit, conversion, diff, summary, and explanation tasks.
version: 1.1.5
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
    - palo-alto
    - pan-os
    - panorama
    - xml
    - vsys
    - device-group
    - rulebase
    - nat
    - appid
    - migration
    - audit
    related_skills:
    - parsing-srx-configs
    - parsing-fortinet-configs
    - parsing-cisco-configs
    - firewall-best-practices-audit
    - firewall-config-conversion
    - firewall-config-diff
---

# Parsing Palo Alto PAN-OS Configurations

## Contents

- [Overview](#overview)
- [Scope and routing](#scope-and-routing)
- [Runtime intake](#runtime-intake)
- [Input Format](#input-format)
- [Extraction Pipeline](#extraction-pipeline)
- [Output Format](#output-format)
- [Parser Quality Gates](#parser-quality-gates)
- [Analysis Checks](#analysis-checks)
- [Reference Files](#reference-files)
- [Secret Handling](#secret-handling)
- [Common Pitfalls](#common-pitfalls)
- [Verification Checklist](#verification-checklist)

## Overview

Use this skill to parse Palo Alto PAN-OS firewall or Panorama configuration exports into the shared vendor-neutral firewall intermediate schema. It primarily targets XML exports and also covers flat `set`-style output when available, including vsys, device-groups, shared objects, zones, address/service/application objects, security rules, NAT rules, routes, profiles, tags, User-ID references, and system settings.

Panorama inheritance and rulebase placement are critical. Preserve shared/device-group/vsys context, distinguish pre-rules and post-rules, and record unresolved inherited references rather than flattening them silently.

## Scope and routing

Use only for PAN-OS or Panorama XML and set-format syntax. Hand off ASA/FTD `access-list`, `nameif`, or `object network` input to `parsing-cisco-configs`, FortiOS blocks to `parsing-fortinet-configs`, and Junos hierarchy or `set security` to `parsing-srx-configs`. Verify production-bound results against current device documentation and output. Downstream consumers are the audit, conversion, and diff skills.

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

PAN-OS configs come in two formats. Auto-detect which one:

1. **XML format** — `show running-config`, `running-config.xml` export, or Panorama config
2. **Set format** — `show config flat` output with `set <path> <value>` lines

**Detection:** Check if input starts with `<` or contains XML tags → XML mode. Lines starting with `set ` → set-format mode.

**Set-format tokenization:** Handle double-quoted strings (preserve as single tokens), `[ ]` bracket list notation (expand to multiple values), and inline `#` comments. Example: `set deviceconfig system hostname fw1` maps to XML path `deviceconfig.system.hostname = fw1`.

### XML Structure Conventions

PAN-OS XML uses two critical element patterns:

1. **`<entry name="...">`** — Named objects. Always treat as arrays even when single.
   ```xml
   <address>
     <entry name="web-server">
       <ip-netmask>10.0.1.10/32</ip-netmask>
     </entry>
   </address>
   ```

2. **`<member>`** — List items in groups, rules, etc. Always treat as arrays.
   ```xml
   <source>
     <member>any</member>
   </source>
   ```

### Locating Config Sections

**Device config path:** `config.devices.entry.vsys.entry[].`
**Panorama shared path:** `config.shared.`
**Direct vsys path:** `config.vsys.entry[].` (older formats)

Use `findVsysEntries()` logic: try each path, collect all vsys entries.

## Extraction Pipeline

### 1. Zones
Path: `zone.entry[]`
Extract: zone name (from `@name` attribute), zone type (from child element: `network.layer3`,
`network.layer2`, `network.virtual-wire`, `network.tap`), interfaces list.

### 2. Address Objects
Path: `address.entry[]`
Types — detect by which child element exists:
- `<ip-netmask>` → type: "subnet" (or "host" if /32)
- `<ip-range>` → type: "range"
- `<fqdn>` → type: "fqdn"
- `<ip-wildcard>` → type: "wildcard" (warn: limited SRX support)
- `<ipv6-netmask>` → type: "subnet" (or "host" if /128)
- `<ipv6-range>` → type: "range"

Also extract: `<description>`, `<tag><member>` tags.
Auto-detect IP version from value.

### 3. Address Groups
Path: `address-group.entry[]`
Two kinds:
- **Static** — `<static><member>` lists member names
- **Dynamic** — `<dynamic><filter>` has tag-based filter expression
  - Warn: dynamic address groups have no direct equivalent in most platforms

### 4. Service Objects
Path: `service.entry[]`
Extract from `<protocol>`:
- `<tcp><port>` / `<tcp><source-port>` → protocol: "tcp"
- `<udp><port>` / `<udp><source-port>` → protocol: "udp"
- `<sctp><port>` → protocol: "sctp" — platform-conditional: valid only on PAN-OS 9.0+ platforms with SCTP security enabled (warn: limited support)

PAN-OS service objects are TCP/UDP (and conditionally SCTP) port objects only. ICMP matching is application-based (the `ping`/`icmp` App-IDs), not a service-object protocol. If any other protocol child element appears, capture its XML in `residual_raw` and add a warning.
Also extract `<description>` from service objects.

### 5. Service Groups
Path: `service-group.entry[]`
Extract `<members><member>` list.
Also extract `<description>` from service groups.

### 6. Applications (Custom)
Path: `application.entry[]`
Extract: name, description, default port from `<default><port><member>`.
Port format: `tcp/80,443` or `udp/53` — parse protocol and port range.

### 7. Application Groups
Path: `application-group.entry[]`
Extract `<members><member>` list.

### 8. Security Policies
Path: `rulebase.security.rules.entry[]` or `pre-rulebase/post-rulebase.security.rules.entry[]`

For each rule extract:
- **name** — from `@name`
- **src_zones** — `<from><member>` list
- **dst_zones** — `<to><member>` list
- **src_addresses** — `<source><member>` list
- **dst_addresses** — `<destination><member>` list
- **negate_source** — `<negate-source>yes</negate-source>` → true
- **negate_destination** — `<negate-destination>yes</negate-destination>` → true
- **applications** — `<application><member>` list
- **services** — `<service><member>` list (often "application-default")
- **action** — `<action>` child element name: allow, deny, drop, reset-client, reset-server, reset-both
  Preserve `drop` as `action: "drop"` (distinct from `deny`), consistent with `references/parsing-patterns.md` and the schema. Do not collapse drop into deny. Add a conversion warning only for target platforms that cannot distinguish a silent drop from an explicit deny.
- **log_start** — `<log-start>yes</log-start>`
- **log_end** — `<log-end>yes</log-end>`
- **disabled** — `<disabled>yes</disabled>`
- **description** — `<description>` text
- **tags** — `<tag><member>` list
- **schedule** — `<schedule>` text
- **source_users** — `<source-user><member>` list (User-ID)
  - Warn if non-"any" values found: User-ID has no direct equivalent on most platforms
- **url_categories** — `<category><member>` list

**Security profiles** — check `<profile-setting>`. Map PAN-OS profile names to the
`security_profiles` schema keys (left = PAN-OS XML element, right = schema key):
- `<group><member>` → profile_group name, then resolve from profile-group definitions
- `<profiles>` → individual profiles:
  - `<virus><member>` → `virus`
  - `<spyware><member>` → `anti-spyware`
  - `<vulnerability><member>` → `idp` (PAN-OS calls this Vulnerability Protection / IPS; the schema key is `idp`)
  - `<url-filtering><member>` → `url-filtering`
  - `<file-blocking><member>` → `file-blocking`
  - `<wildfire-analysis><member>` → `wildfire`
  - `<data-filtering><member>` → `dlp`

### 9. NAT Rules
Path: `rulebase.nat.rules.entry[]`

For each rule:
- Determine NAT type from `<source-translation>` and/or `<destination-translation>` presence
- **Source NAT:** `<source-translation>` with `<dynamic-ip-and-port>` (interface or translated-address)
  or `<static-ip>` with `<translated-address>`
- **Destination NAT:** `<destination-translation>` with `<translated-address>` and optional `<translated-port>`
- **Both:** has both source and destination translation → type: "source-and-destination"

### 10. Decryption Rules
Path: `rulebase.decryption.rules.entry[]`
Extract: name, zones, addresses, action (decrypt/no-decrypt), SSL type (forward-proxy, inbound-inspection).

### 11. Interfaces
Parse from `network.interface` entries (both XML and set-format):

**Interface types:**
- **Ethernet** (`ethernet1/1`): IP, IPv6, MTU, DHCP client, aggregate-group (LAG parent), description, subinterfaces (units with IP/VLAN tag/IPv6)
- **Aggregate-ethernet** (`ae1`): LAG with layer3 IP, MTU, sub-units
- **Loopback** (`loopback.N`): IP and description
- **VLAN** (`vlan.N`): IP and VLAN tag
- **Tunnel** (`tunnel.N`): IP for VPN binding

Derive interface type from name: `ae*`=lag, `loopback*`=loopback, `tunnel*`=tunnel, `vlan*`=vlan.
Back-populate `lag_members` on aggregate interfaces after parsing all interfaces.
Subinterface zone inheritance: if a subinterface has no zone but its parent does, inherit the parent's zone.

### 12. System Configuration
Path: `deviceconfig.system`
Extract:
- `hostname`, `domain`, `sw-version` (→ metadata.source_version)
- `dns-setting.servers` → primary/secondary DNS
- `ntp-servers` → NTP servers with prefer flag
- Management IP + netmask → synthetic `mgmt` interface with `is_mgmt: true`
- Management services: SSH, HTTPS, HTTP, Telnet — PAN-OS uses `disable-*` flags where `yes` = disabled (invert)

### 13. Admin Users
Path: `mgt-config.users.entry[]`
Extract: username, SSH public key (`ssh-public-key` or older `public-key`), role from permissions (`superuser`→super-admin, `devicereader`→read-only, `deviceadmin`→admin).
Only migrate users with SSH keys; warn about others.

### 14. DHCP Server and Relay
Path: `network.dhcp.interface.entry[]`
Extract per-interface:
- **Server:** enable state, IP pools (start-end), gateway, primary/secondary DNS, domain, lease timeout
- **Relay:** relay server IP addresses
Derive network CIDR from the interface IP for the DHCP scope.

### 15. Routing & Infrastructure
- **Virtual Routers:** `network.virtual-router.entry[]` — extract name and interface list
- **Static routes (IPv4):** `routing-table.ip.static-route.entry[]` with destination, nexthop (IP or discard), interface, metric
- **Static routes (IPv6):** `routing-table.ip6.static-route.entry[]` (note: `ip6` not `ipv6` in XML path)
- Routes through tunnel interfaces are separated and associated with VPN tunnels
- **BGP:** `protocol.bgp` — extract:
  - Local AS, router-ID, enable/disable
  - Peer groups: type (ebgp/ibgp), group-level peer-as
  - Per-peer: address, remote-as (fallback to group AS), description, update-source, password (presence only — redact), keepalive/hold timers, next-hop-self, route-reflector-client, enabled
  - Advertise-network entries
  - Redistribution rules
- **OSPF:** `protocol.ospf` — extract:
  - Router-ID, reference-bandwidth
  - Areas: area ID, type (normal/stub/nssa), no-summary, default-cost
  - Area authentication: type (md5), key presence (redact the key value)
  - Interfaces per area: passive, enabled, metric, priority, hello/dead intervals, link-type, per-interface auth
  - Redistribute: source, metric, metric-type
- **OSPFv3:** `protocol.ospfv3` — same structure as OSPFv2
- **HA:** `deviceconfig.high-availability` — enabled flag, mode (active-passive/active-active), group-id
- **VPN/IPsec:**
  - IKE crypto profiles: encryption, integrity, DH groups, lifetime
  - IPsec crypto profiles: ESP encryption/authentication, DH group (PFS), lifetime
  - IKE gateways: version (IKEv1/v2), auth method (PSK or certificate), PSK presence (mask the value as `"****"`), local/peer address, local/peer ID, crypto profile reference, local cert + CA profile
  - IPsec tunnels: IKE gateway reference, IPsec crypto profile reference, tunnel interface binding
  - Resolve tunnel IPs, find VR containing tunnel, collect routes through tunnel interfaces
  - Flag weak algorithms (DES/3DES, MD5, DH group ≤ 5)
- **Zone protection:** `network.profiles.zone-protection-profile.entry[]`
- **Syslog:** `shared.log-settings.syslog.entry[]`
- **Virtual wire:** `network.virtual-wire.entry[]`

### 16. Application Resolution (L7 → Canonical)

PAN-OS has the richest L7 application model of any firewall vendor. Security policies use
`<application><member>` to match traffic by application signature, independent of port.

**Resolution steps for each application name in a policy:**

1. **Service object/group check:** If the name matches a service object or service group → promote
   to the `services` array (PAN-OS sometimes places port-based matches in the application field)
2. **Application group check:** If the name matches an `application-group.entry[]` → add to policy's
   `app_groups` array
3. **Custom application check:** If the name matches a `application.entry[]` (custom app) → keep it
   as an L7 application reference under `applications`/`apps`. Capture its `<default><port>` definition
   as app metadata / a conversion hint (e.g. `default_port`), but do NOT replace the application with a
   service object — a custom App-ID remains an L7 application.
4. **Cross-vendor canonical resolution:** Resolve PAN-OS application names (e.g., `ssl`, `web-browsing`, `ms-rdp`) to canonical identifiers. The full canonical mapping table is in `references/parsing-patterns.md` "Canonical Application Mapping". For each resolved app, populate `apps`: `{ vendor_name: "ssl", canonical: "https", confidence: 1.0, category: "web" }`.

**`application-default` service:** When a policy sets `<service><member>application-default</member>`, PAN-OS uses each application's built-in default port. For the IR, keep `services: ["application-default"]` and rely on the `apps` array for resolution. During conversion to port-based platforms, decompose each resolved app's default port into explicit service matches.

**Custom applications** (`application.entry[]`): Extract the `<default><port><member>` list. Format is `tcp/80,443` or `udp/53` — parse protocol and port range and attach it as app metadata (e.g. a `default_port` field / conversion hint) on the custom app's entry under `applications`/`apps`. Keep the custom app as an L7 application reference; do NOT create a service object or move it into the policy's `services` array. Only decompose the default port into explicit service matches during target conversion when the target platform requires it. Set `confidence: 0.9` since custom apps may not have
an exact canonical equivalent.

**Unresolvable apps:** PAN-OS has 3000+ built-in application signatures. Many are vendor-specific
(e.g., `palo-alto-networks`, `fortinet`). For unknown apps, set `confidence: 0.0`, preserve the
vendor_name, and warn. These will go to residual during conversion.

### 16b. Application Groups

Path: `application-group.entry[]`
Extract `<members><member>` list.

**Resolution:** For each member:
1. Resolve from PAN-OS name to canonical
2. If a member is itself an application group → recurse
3. If a member is a custom application → extract its port definition

Store in `application_groups` with canonical member names.

**Mixed groups:** If a group contains both L7 apps and port-based services, split them:
L7 apps → `application_groups`, port-based → `service_groups`.

### 17. Multi-vsys
If multiple vsys entries found:
- Parse each independently
- Tag all policies and objects with `_vsys: "vsys1"` etc.
- Merge into flat arrays
- Re-index `_rule_index` sequentially

### 18. Residual Config Capture
Capture unhandled configuration sections. In XML mode, serialize unhandled elements back to XML strings. Categorize into: VPN Tunnels, IKE, IPsec Crypto, QoS, DNS Proxy, Shared Objects, PKI/Certificates, Security Profiles, Custom Applications, Policy-Based Forwarding, Panorama Config, Other. Store in `residual_raw`.

### 19. Implicit Rules
After parsing all explicit policies, append per-context:
- **Implicit: Intra-zone Allow** — per zone, action: "allow", `_implicit: true`
  (for each zone, src_zones = dst_zones = [zone_name])
- **Implicit: Interzone Default Deny** — action: "deny", src/dst zones: ["any"], `_implicit: true`

Implicit-rule `name` values (e.g. "default-deny", "Implicit: Default Deny") are free-form labels; consumers must match implicit rules on `_implicit: true`, never on the name.

## Output Format

Present results in the **intermediate schema** format documented in `references/intermediate-schema.md`.

Note: schema sections not yet populated by this pipeline (e.g., `security_profile_objects`, `routing_contexts`) are emitted empty (`[]`/`{}`); any unhandled source constructs are captured in `residual_raw` rather than dropped.

**Full intermediate-schema emission is optional for single live-device work.** The complete JSON schema exists primarily for cross-vendor conversion and multi-config diffing. When interpreting or auditing a *single* live device pulled via the XML API for an ops/audit task, it is fine to reason directly from the XML config and skip full schema emission — extract the sections relevant to the question. Emit the full schema when the parse will feed `firewall-config-conversion`, `firewall-config-diff`, or another config for comparison.


## Parser Quality Gates

Before returning a parse, run these common quality gates and include the results in the response:

1. **Format and scope detection** — report detected vendor, platform family, config format, version clues, virtual context names (VDOM/vsys/logical-system/routing-instance), and whether input appears complete or partial.
2. **Schema conformance** — emit the vendor-neutral JSON sections defined in `references/intermediate-schema.md`; use empty arrays/objects for absent sections rather than omitting expected top-level keys.
3. **Object counts** — summarize counts for zones, interfaces, address objects/groups, service/application objects/groups, policies, NAT rules, routes, VPNs, HA, admin users, and residual blocks.
4. **Reference resolution** — list unresolved object, service/application, zone/interface, profile, route, VPN, and NAT references with source rule/context where possible.
5. **Ordering preservation** — preserve security policy order, NAT order, and route order when relevant. For Panorama, encode the full merged evaluation order (`shared` → device-group `pre-rulebase` → local/vsys `rulebase` → device-group `post-rulebase`, with nested device-group inheritance) using `_rule_index`. The schema defines only `_rule_index` and `_vsys` for PAN-OS context, so record device-group / pre-vs-post origin in `metadata.warnings` or `residual_raw` rather than inventing a context field.
6. **State preservation** — preserve disabled/inactive objects and rules, comments/descriptions, tags, schedules/time-ranges, negation flags, logging settings, and profile attachments.
7. **Residual capture** — put unsupported or ambiguous source lines/blocks into `residual_raw` with enough context for manual review. Do not silently drop unknown syntax.
8. **Warnings and assumptions** — populate `metadata.warnings` with parser limitations, partial-input assumptions, ambiguous conversions, and version-specific caveats.
9. **Conversion readiness** — if the user asks for migration/conversion, explicitly separate parsed facts from proposed target-platform design choices and call out non-isomorphic features.

A high-quality parse is not just valid JSON: it must make uncertainty visible. Prefer a complete parse with warnings and residuals over a clean-looking parse that hides unsupported constructs.

## Analysis Checks

After extraction, run these checks and report findings:

1. **Unused objects** — address/service objects not referenced by any policy
2. **Shadowed policies** — rules fully covered by earlier rules
3. **Overly permissive** — rules with any/any or negate patterns covering everything
4. **Missing logging** — permit rules without log-end enabled
5. **Disabled policies** — rules with `<disabled>yes</disabled>`
6. **Duplicate objects** — same value, different names
7. **Empty groups** — groups with no members
8. **Dynamic groups** — flag for manual review (no static equivalent)
9. **User-ID dependencies** — rules relying on source-user for access control
10. **URL category dependencies** — rules using URL categories for access control

## Reference Files

- `references/config-format.md` — PAN-OS XML structure reference
- `references/intermediate-schema.md` — Output schema specification
- `references/parsing-patterns.md` — Edge cases, app mapping, profile resolution
- `references/example-sample-parse.md` — Worked end-to-end example (input XML → parsed JSON)
- `references/fixture-minimal-input.md` — Minimal parser fixture input
- `references/fixture-expected-output.json` — Expected high-level intermediate-schema output for the minimal fixture

## Secret Handling

Never emit secrets raw. IKE/VPN pre-shared keys, routing-protocol authentication keys (BGP/OSPF), and user password hashes must be masked as `"****"` (or reduced to a presence flag) with a `metadata.warnings` entry noting the redaction — matching the shared-schema convention (`"psk": "****"`).

## Common Pitfalls

1. Do not collapse Panorama shared, device-group, and vsys scopes without preserving source context.
2. Preserve pre-rulebase vs post-rulebase order; rule placement changes behavior.
3. `application-default` is not a normal service object. Represent it explicitly and warn during cross-vendor conversion.
4. Application, service, URL category, tag, and profile references can look similar; resolve each against the correct object tree.
5. Disabled rules, negation, User-ID fields, and dynamic address groups are easy to lose; capture them explicitly or warn.

## Verification Checklist

- [ ] Input vendor/platform and config format were detected correctly
- [ ] All major object counts are reported: zones, interfaces, addresses, services/applications, policies, NAT, routes, VPN, HA, and system settings
- [ ] Output conforms to `references/intermediate-schema.md`
- [ ] Disabled/inactive rules and objects are preserved with explicit state
- [ ] Unresolved references, unsupported blocks, and parser assumptions are listed in `metadata.warnings` and/or `residual_raw`
- [ ] Rule order and NAT order are preserved with `_rule_index` or equivalent ordering metadata
- [ ] Cross-vendor conversion caveats are called out before suggesting target-platform config
- [ ] No raw secrets in output — PSKs masked as `"****"`, routing-protocol passwords/keys reduced to presence flags with warnings

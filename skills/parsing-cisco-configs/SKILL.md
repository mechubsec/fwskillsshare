---
name: parsing-cisco-configs
description: Parse Cisco ASA and FTD LINA running configurations into the shared firewall schema. Use when input contains show running-config, access-list, access-group, object network, object-group, nameif, security-level, NAT, interfaces, or failover, including audit, conversion, diff, summary, and explanation tasks. For FMC- or FDM-managed Firepower policy exported as JSON, use parsing-firepower-configs instead.
version: 1.1.6
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
    - asa
    - ftd
    - access-list
    - nat
    - migration
    - audit
    related_skills:
    - parsing-srx-configs
    - parsing-palo-configs
    - parsing-fortinet-configs
    - parsing-firepower-configs
    - firewall-best-practices-audit
    - firewall-config-conversion
    - firewall-config-diff
---

# Parsing Cisco ASA / FTD Configurations

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

Use this skill to parse Cisco ASA and ASA-style FTD running configurations into the shared vendor-neutral firewall intermediate schema. It focuses on line-oriented `show running-config` text with parent commands and indented subcommands, including interfaces/nameifs, ACLs/access-groups, network and service objects, object-groups, NAT, routes, VPN, failover, and system settings.

FMC- and FDM-managed policy is **not** parsed here. An FMC or FDM JSON export has
no syntactic overlap with LINA CLI — its policy lives in Access Control Policy
rules, security-zone objects, and intrusion/file policies rather than in
`access-list` and `access-group` lines. Route those exports to
`parsing-firepower-configs`. If an FMC-managed device's LINA running-config is
supplied, parse it here and warn that it is the compiled result of an FMC policy,
not the policy source.

## Scope and routing

Use only for Cisco ASA or FTD syntax. Hand off FortiOS `config/edit/next/end` blocks to `parsing-fortinet-configs`, PAN-OS XML or `set deviceconfig` to `parsing-palo-configs`, and Junos hierarchy or `set security` to `parsing-srx-configs`. Hand off FMC or FDM JSON exports to `parsing-firepower-configs`. Verify production-bound results against current device documentation and output. Downstream consumers are the audit, conversion, and diff skills.

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

Cisco ASA configs are line-oriented with indented sub-commands:
```
interface GigabitEthernet0/0
 nameif outside
 security-level 0
 ip address 203.0.113.1 255.255.255.0
!
object network web-server
 host 10.0.1.10
 nat (inside,outside) static 203.0.113.10
!
access-list outside_in extended permit tcp any object web-server eq 443
access-group outside_in in interface outside
```

Key syntax rules:
- Top-level commands start at column 0
- Sub-commands are indented with one space
- `!` separates logical sections
- Named interfaces use `nameif` (e.g., `inside`, `outside`, `dmz`)
- `security-level` (0-100) determines trust level

### Building Command Blocks

Group indented lines under their parent top-level command — see references/parsing-patterns.md "Building Command Blocks" for the algorithm and worked example.

## Extraction Pipeline

### 1. Interfaces
Source: `interface <hardware-id>` blocks
Extract from sub-commands:
- `nameif <name>` — the logical name used everywhere else
- `security-level <0-100>` — trust level
- `ip address <ip> <mask>` — IP and subnet mask
- `vlan <id>` — VLAN assignment
- `shutdown` — interface is administratively down
- `description <text>`
- `bridge-group <id>` — transparent mode bridge group membership
- `ip address dhcp` — DHCP client mode (no static IP)
- `ipv6 address <ipv6/prefix> [eui-64]` — IPv6 address
- `mtu <value>` — MTU setting
- `management-only` — management-only interface flag
- `channel-group <N>` — LAG/EtherChannel membership (Port-channel parent)
- `tunnel source interface <name>` — VPN tunnel source
- `tunnel destination <ip>` — VPN tunnel destination
- `tunnel protection ipsec profile <name>` — IPsec profile binding

Interface types: detect `Port-channel*` as lag, `Tunnel*` as tunnel, `Loopback*` as loopback, `Management*` as management. Sub-interfaces contain `.` in name (e.g., `GigabitEthernet0/0.100`) — derive parent from name before the dot.

### 2. Zones (Derived from Interfaces)
ASA doesn't have explicit zones. Derive them from `nameif` values:
- Each unique `nameif` becomes a zone
- `security-level` values are parser-internal inference metadata used to determine relative trust ordering between zones (higher = more trusted). This is NOT emitted as a `security_level` or `trust_level` field in the intermediate schema — use it only to guide ordering or warn when ACLs are absent.
- Associate the interface with its zone

### 3. Network Objects
Source: `object network <name>` blocks
Types from sub-commands:
- `host <ip>` → type: "host", value: ip + "/32" (or "/128" for IPv6)
- `subnet <ip> <mask>` → type: "subnet", value: ip + "/cidr" (convert mask to CIDR)
- `range <start> <end>` → type: "range", value: "start-end"
- `fqdn v4 <domain>` or `fqdn v6 <domain>` → type: "fqdn"

Note: bare `fqdn <domain>` (without v4/v6 qualifier) is also valid.

- `subnet <ipv6-prefix>` → for IPv6 subnets the value is already in CIDR form, no mask conversion needed.

Also extract: `description`, inline `nat` statement (for object/auto NAT).

### 4. Network Object Groups
Source: `object-group network <name>` blocks
Members from sub-commands:
- `network-object host <ip>` → inline host
- `network-object <ip> <mask>` → inline subnet
- `network-object object <name>` → reference to named object
- `group-object <name>` → nested group reference

### 5. Service Objects
Source: `object service <name>` blocks
Parse: `service <protocol> [source <op> <port>] [destination <op> <port>]`
Operators: `eq`, `range`, `gt`, `lt`, `neq`

### 6. Service Object Groups
Source: `object-group service <name> [<protocol>]` blocks
Members:
- `port-object eq <port>` / `port-object range <start> <end>`
- `service-object <protocol> [destination <op> <port>]`
- `service-object object <name>`
- `group-object <name>`

### 7. Protocol Object Groups
Source: `object-group protocol <name>` blocks
Members: `protocol-object <protocol-name-or-number>`

### 8. Access Lists (Security Policies)
Source: `access-list <name> extended <action> <protocol> <src> <dst> [<svc>]`

**ACL Remarks:**
`access-list <name> remark <text>` — attach as `comment` to the NEXT ACL entry.

**ACL Line Parsing — Token by Token:**

Format: `access-list <id> extended <permit|deny> <protocol> <source> <dest> [<service>] [log] [time-range <name>]`

**Protocol field:**
- `ip` — any IP protocol
- `tcp`, `udp`, `icmp`, `sctp` — specific protocols
- `object-group <name>` — protocol group reference

**Address parsing** (for both source and destination):
- `any` / `any4` / `any6` → "any"
- `host <ip>` → specific host
- `object <name>` → named network object
- `object-group <name>` → network object group
- `<network> <mask>` → network/subnet-mask pair (convert standard subnet mask to CIDR)
- `interface <nameif>` → the IP of that interface

**Source port parsing** (after source address, for TCP/UDP — optional):
- `eq <port>` / `range <start> <end>` → source port match (less common)

**Service/port parsing** (after destination address, for TCP/UDP):
- `eq <port>` → single port (use name or number)
- `range <start> <end>` → port range
- `gt <port>` → greater than
- `lt <port>` → less than
- `neq <port>` → not equal (warn: limited cross-platform support)
- `object-group <name>` → service group reference

**ICMP parsing** (for ICMP protocol):
- Optional ICMP type after destination: `icmp <src> <dst> <type> [<code>]`

**Flags:**
- `log [<level>] [interval <secs>]` → enable logging
- `time-range <name>` → schedule reference
- `inactive` → disabled

### 9. Access Groups (Binding ACLs to Interfaces/Zones)
Source: `access-group <acl-name> <in|out> interface <nameif>`
Also: `access-group <acl-name> global` (applies to all interfaces)

**Critical: Deriving Zone-Based Policies from ACLs**

ACLs alone don't have zone info. Combine with access-groups:
- `access-group outside_in in interface outside` → policies from this ACL have:
  - `src_zones: ["outside"]` (traffic enters on this interface, so it is the source zone)
  - `dst_zones:` must be inferred (often "any" unless the ACL destination addresses map to a zone)
- For `in` direction: traffic is entering the named interface, so that interface is the **source zone**
- For `out` direction: traffic is leaving the named interface
- For `global`: applies regardless of interface

Build security policies by iterating ACL entries and attaching zone information from access-groups.

### 10. NAT Rules

**Object NAT (Auto NAT):**
Found inside `object network` blocks as `nat (<real-iface>,<mapped-iface>) <type> <mapped-addr>`
- `nat (inside,outside) static 203.0.113.10` → static 1:1 NAT
- `nat (inside,outside) dynamic interface` → dynamic PAT to interface
- `nat (inside,outside) dynamic pat-pool <name>` → dynamic PAT to pool

**Twice NAT (Manual NAT):**
Top-level: `nat (<real-iface>,<mapped-iface>) [after-auto] [<line>] source <type> <real-src> <mapped-src> [destination <type> <real-dst> <mapped-dst>] [service <real-svc> <mapped-svc>]`

Parse `source static|dynamic` and optional `destination static` components.
The optional numeric token is a line number — the rule's position within its manual NAT section — NOT a section selector. Derive the section from rule form: Section 1 = manual/twice NAT without `after-auto` (evaluated before object/auto NAT); Section 2 = object/auto NAT (rules inside `object network` blocks); Section 3 = manual NAT with the `after-auto` keyword (evaluated after all auto NAT).

### 11. Time Ranges (Schedules)
Source: `time-range <name>` blocks
Sub-commands:
- `absolute start <time> <date> end <time> <date>`
- `periodic <days> <start-time> to <end-time>`

### 12. Routing
- **Static routes (IPv4):** `route <nameif> <dest> <mask> <gateway> [<metric>]`
- **Static routes (IPv6):** `ipv6 route <nameif> <dest/prefix> <gateway> [<metric>]`
- **BGP:** `router bgp <asn>` block — extract:
  - `router-id`, `address-family ipv4 unicast`
  - Per-neighbor: `remote-as`, `description`, `update-source`, `password`, `timers` (keepalive/hold), `next-hop-self`, `soft-reconfiguration`, `route-reflector-client`, `shutdown`
  - `network` statements (convert mask to CIDR)
  - `redistribute` (connected/static)
  - Note: route-map and prefix-list references are not converted (warn)
- **OSPF:** `router ospf <pid>` block — extract:
  - `router-id`, `auto-cost reference-bandwidth`
  - `network <ip> <wildcard> area <id>` — match interfaces to areas via wildcard mask comparison
  - Area types: stub, nssa, with `no-summary`; area default-cost; area authentication
  - `passive-interface default` + `no passive-interface <nameif>` exceptions
  - `redistribute` (connected/static with metric/metric-type)
  - Interface-level: `ip ospf cost`, `ip ospf priority`, `ip ospf hello-interval`, `ip ospf dead-interval`, `ip ospf network point-to-point`, `ip ospf authentication message-digest` + key
  - Normalize area IDs to dotted-decimal (0 → 0.0.0.0)
- **OSPFv3:** `router ospfv3` block with `address-family ipv6 unicast` — similar structure to OSPFv2

### 13. Infrastructure
- **Hostname:** `hostname <name>` and `domain-name <domain>` → system metadata
- **Version:** `asa version <X.Y>` or `firepower version <X.Y>` → metadata.source_version
- **HA/Failover:** `failover` presence + `failover lan unit primary|secondary` (capture unit role),
  `failover interface ip`, `failover link`
- **Screen/Threat Detection:** `threat-detection basic-threat` + `threat-detection rate` entries
- **DNS:** `dns server-group DefaultDNS` block → extract `name-server` entries
- **NTP:** `ntp server <ip> [prefer]`
- **Management Access:** `ssh|http|telnet <source> <mask> <nameif>` — track which management protocols are accessible per zone
- **Admin Users:** `username <name> password ... privilege <level>` — map privilege 15=super-admin, 1-14=operator, 0=read-only. `username <name> attributes` block with `ssh authentication publickey <key>` for SSH keys.
- **VPN/IPsec:**
  - `crypto ikev2 policy <seq>` blocks: encryption, integrity, DH group, lifetime
  - `crypto ikev1 policy <seq>` blocks: authentication, encryption, hash, DH group, lifetime
  - `crypto ipsec ikev2 ipsec-proposal <name>`: protocol esp encryption/integrity
  - `crypto ipsec ikev1 transform-set <name> <enc> <integ>`
  - `crypto ipsec profile <name>`: link proposals to PFS groups
  - `tunnel-group <ip> ipsec-attributes`: PSK, certificates, authentication method
  - VTI assembly: match Tunnel interfaces to IPsec profiles, resolve tunnel source/destination, collect routes through tunnel nameifs
  - Canonicalize algorithm names (ASA encryption names are mostly already canonical; e.g., sha → sha1, esp-3des → 3des)
  - Flag weak algorithms (DES/3DES, MD5, DH group ≤ 5)
- **Syslog:** `logging host <nameif> <ip>`
- **DHCP Server:** `dhcpd address <start>-<end> <nameif>` (pool range),
  `dhcpd dns <ip1> [<ip2>]`, `dhcpd domain <domain>`, `dhcpd lease <seconds>`,
  `dhcpd enable <nameif>` (commit trigger — binds staged options to interface).
  Derive network CIDR from the interface IP.
- **DHCP Relay:** `dhcprelay server <ip> <iface>` + `dhcprelay enable <nameif>`

### 14. Application Mapping (L7 → Canonical)

ASA/FTD is a port-based platform — it does not have native L7 application awareness in ACLs.
However, when converting FROM ASA to an app-aware platform (PAN-OS, FortiGate), or comparing
configs, the parser should attempt to resolve well-known port/protocol combinations to canonical
application names.

**Resolution from port-based services:** For each service object or inline port match, check if the protocol+port maps to a known application. The full canonical mapping table is in `references/parsing-patterns.md` "Canonical Application Mapping".

**ASA named port keywords:** Map ASA port names to numbers before resolving — full table in references/parsing-patterns.md "Port Name Resolution". Caution: ASA literals predate IANA assignments (`radius`=1645, `radius-acct`=1646, `kerberos`=750) — do not "correct" them from prior knowledge; use the reference table.

**On policy output:** When a service match resolves to a known application, populate the policy's `apps` array with `{ vendor_name: "tcp/443", canonical: "https", confidence: 1.0, category: "web" }`. The `services` array still keeps the port-based match. This enables downstream converters to use the app-aware rule on platforms that support it.

**Unresolvable services:** Complex port ranges, non-standard ports, or protocol groups that don't map to a single known application → keep as port-based services only, no `apps` entry.

**Example:** An ACL line `access-list outside_in extended permit tcp any any eq 443` produces:
- **Service entry:** `"tcp/443"` in the policy's `services` array (a string, as in `references/fixture-expected-output.json`)
- **Application entry:** `{ vendor_name: "tcp/443", canonical: "https", confidence: 1.0, category: "web" }` in the policy's `apps` array
Both fields are populated — the port-based service match and the resolved application identity.

### 15. Application Groups

ASA does not have application groups. However, when converting FROM an app-aware platform,
object-group service entries that resolve entirely to known applications should be flagged
as potential `application_groups` in the IR for downstream use.

### 16. Anonymous Objects
When inline addresses/services appear in ACLs or object groups without a named reference (e.g., `host 10.0.1.10` directly in an ACL line), create anonymous objects with auto-generated names (e.g., `anon-1-host`, `anon-2-net`). This ensures every IR reference points to a named object.

### 17. Residual Config Capture
Capture unrecognized top-level commands verbatim. Categorize into: VPN/IPsec, AAA, QoS, PKI/Certificates, IPv6, Other. Store in `residual_raw` for manual review.

### 18. Transparent Mode
Detect: `firewall transparent` in config
When in transparent mode:
- Interfaces are in bridge-groups instead of having IPs
- `bridge-group <id>` on interfaces
- BVI interfaces (`interface BVI<id>`) carry the management IP
- Zones derived from nameifs still work the same way

### 19. Implicit Rules
The ASA implicit deny is scoped per bound ACL, not global: each ACL applied via `access-group`
ends with an implicit deny for that interface/direction only. Applying an ACL on one interface
does NOT disable security-level defaults for other interface pairs.

After building all policies from ACLs + access-groups, append:
- **Implicit: Default Deny** — one per access-group binding — action: "deny",
  `src_zones: [<bound nameif>]` for `in` direction (`dst_zones` for `out`; all any for
  `global`), remaining fields any, `_implicit: true`
- When every traffic-passing interface has a bound ACL (or a `global` access-group exists),
  the per-binding denies may be collapsed into a single final any→any deny, `_implicit: true`
- For interfaces with NO ACL bound: do not fabricate a deny — security-level defaults still
  apply (higher-to-lower permitted, lower-to-higher denied). Add a `metadata.warnings` entry
  ("no ACL bound on <nameif> — security-level high-to-low permit applies") and, if downstream
  consumers need explicit rules, model the default permit as an `_implicit: true` allow policy
  from that zone to lower-security zones

Implicit-rule `name` values (e.g. "default-deny", "Implicit: Default Deny") are free-form labels; consumers must match implicit rules on `_implicit: true`, never on the name.

## Output Format

Present results in the **intermediate schema** format documented in `references/intermediate-schema.md`.

Note: schema sections not yet populated by this pipeline (e.g., `security_profile_objects`, `routing_contexts`) are emitted empty (`[]`/`{}`); any unhandled source constructs are captured in `residual_raw` rather than dropped.

**Full intermediate-schema emission is optional for single live-device work.** The complete JSON schema exists primarily for cross-vendor conversion and multi-config diffing. When interpreting or auditing a *single* live device pulled via SSH/API for an ops/audit task, it is fine to reason directly from the running config and skip full schema emission — extract the sections relevant to the question. Emit the full schema when the parse will feed `firewall-config-conversion`, `firewall-config-diff`, or another config for comparison.


## Parser Quality Gates

Before returning a parse, run these common quality gates and include the results in the response:

1. **Format and scope detection** — report detected vendor, platform family, config format, version clues, virtual context names (VDOM/vsys/logical-system/routing-instance), and whether input appears complete or partial.
2. **Schema conformance** — emit the vendor-neutral JSON sections defined in `references/intermediate-schema.md`; use empty arrays/objects for absent sections rather than omitting expected top-level keys.
3. **Object counts** — summarize counts for zones, interfaces, address objects/groups, service/application objects/groups, policies, NAT rules, routes, VPNs, HA, admin users, and residual blocks.
4. **Reference resolution** — list unresolved object, service/application, zone/interface, profile, route, VPN, and NAT references with source rule/context where possible.
5. **Ordering preservation** — preserve security policy order, NAT order, route order when relevant, and inherited/pre/post/global ordering metadata with `_rule_index` or a vendor-specific context field.
6. **State preservation** — preserve disabled/inactive objects and rules, comments/descriptions, tags, schedules/time-ranges, negation flags, logging settings, and profile attachments.
7. **Residual capture** — put unsupported or ambiguous source lines/blocks into `residual_raw` with enough context for manual review. Do not silently drop unknown syntax.
8. **Warnings and assumptions** — populate `metadata.warnings` with parser limitations, partial-input assumptions, ambiguous conversions, and version-specific caveats.
9. **Conversion readiness** — if the user asks for migration/conversion, explicitly separate parsed facts from proposed target-platform design choices and call out non-isomorphic features.

A high-quality parse is not just valid JSON: it must make uncertainty visible. Prefer a complete parse with warnings and residuals over a clean-looking parse that hides unsupported constructs.

## Analysis Checks

After extraction, run these checks and report findings:
1. **Unused objects** — network/service objects not referenced in any ACL
2. **Shadowed ACL entries** — rules that can never match due to earlier entries
3. **Overly permissive** — `permit ip any any` or broad rules
4. **Missing logging** — permit ACL entries without `log` keyword
5. **Inactive entries** — ACL entries with `inactive` flag
6. **Duplicate objects** — same value, different names
7. **Empty groups** — object-groups with no members
8. **Unbound ACLs** — access-lists without matching access-group (never applied)
9. **Subnet mask validation** — flag any non-standard subnet masks

## Reference Files

- `references/config-format.md` — Cisco ASA config syntax reference
- `references/intermediate-schema.md` — Output schema specification
- `references/parsing-patterns.md` — Edge cases, port name mapping, security-level logic
- `references/example-sample-parse.md` — Worked end-to-end example (input config → parsed JSON)
- `references/fixture-minimal-input.md` — Minimal parser fixture input
- `references/fixture-expected-output.json` — Expected high-level intermediate-schema output for the minimal fixture

## Secret Handling

Never emit secrets raw. Tunnel-group pre-shared keys, `username ... password` hashes, BGP neighbor passwords, and SNMP community strings must be masked as `"****"` (or represented as a presence flag) with a `metadata.warnings` entry noting the secret was redacted — matching the shared-schema convention (`"psk": "****"`).

## Common Pitfalls

1. Do not treat IOS wildcard masks as ASA subnet masks; ASA object subnets use standard dotted masks.
2. Do not infer policy direction from ACL names alone; bind ACLs to interfaces with `access-group`.
3. Object NAT and manual/twice NAT order matters. Preserve NAT section/order metadata and flag ambiguous translations.
4. Security levels are not zones by themselves, but they help infer trust roles when no explicit design notes exist.
5. FTD/FMC-managed output may omit policy context available in FMC; preserve gaps as warnings instead of fabricating rules.

## Verification Checklist

- [ ] Input vendor/platform and config format were detected correctly
- [ ] All major object counts are reported: zones, interfaces, addresses, services/applications, policies, NAT, routes, VPN, HA, and system settings
- [ ] Output conforms to `references/intermediate-schema.md`
- [ ] Disabled/inactive rules and objects are preserved with explicit state
- [ ] Unresolved references, unsupported blocks, and parser assumptions are listed in `metadata.warnings` and/or `residual_raw`
- [ ] Rule order and NAT order are preserved with `_rule_index` or equivalent ordering metadata
- [ ] Cross-vendor conversion caveats are called out before suggesting target-platform config
- [ ] No raw secrets in output — PSKs masked as `"****"`, routing-protocol passwords/keys reduced to presence flags with warnings

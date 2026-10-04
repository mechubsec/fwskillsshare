# FortiGate Parsing Patterns and Edge Cases

## Contents

- [Interface-as-Zone Merging](#interface-as-zone-merging)
- [Subnet Mask to CIDR Conversion](#subnet-mask-to-cidr-conversion)
- [Application Mapping](#application-mapping)
- [VIP as Destination NAT](#vip-as-destination-nat)
- [Profile Group Resolution](#profile-group-resolution)
- [UTM Profile Mapping](#utm-profile-mapping)
- [Logging Interpretation](#logging-interpretation)
- [Schedule Handling](#schedule-handling)
- [Policy ID vs Name](#policy-id-vs-name)
- [Multi-VDOM Handling](#multi-vdom-handling)
- [Intrazone Policy](#intrazone-policy)
- [Common Warnings](#common-warnings)
- [Canonical Application Mapping](#canonical-application-mapping)

## Interface-as-Zone Merging

FortiGate policies use `srcintf` / `dstintf` which can reference either:
- A **zone name** (from `config system zone`)
- An **interface name** directly (from `config system interface`)

When a policy references an interface not in any zone, treat that interface as its own zone.

**Algorithm:**
1. Parse all zones from `config system zone`
2. Parse all interfaces from `config system interface`
3. For each interface referenced in a policy's `srcintf`/`dstintf`:
   - If it matches a zone name → use the zone
   - If it matches an interface name not in any zone → create an auto-zone with the interface name
4. Merge into final zones list

## Subnet Mask to CIDR Conversion

FortiGate uses `set subnet <ip> <mask>` with dotted-decimal masks.

**Conversion algorithm:**
1. Convert mask to 32-bit integer
2. Count leading 1-bits
3. Result is the CIDR prefix length

**Quick reference:**

| Mask | CIDR | | Mask | CIDR |
|---|---|---|---|---|
| 255.255.255.255 | /32 | | 255.255.254.0 | /23 |
| 255.255.255.252 | /30 | | 255.255.248.0 | /21 |
| 255.255.255.248 | /29 | | 255.255.240.0 | /20 |
| 255.255.255.240 | /28 | | 255.255.224.0 | /19 |
| 255.255.255.224 | /27 | | 255.255.192.0 | /18 |
| 255.255.255.192 | /26 | | 255.255.128.0 | /17 |
| 255.255.255.128 | /25 | | 255.255.0.0 | /16 |
| 255.255.255.0 | /24 | | 255.0.0.0 | /8 |

Special case: `set subnet 0.0.0.0 0.0.0.0` → represents "all" (any address), NOT 0.0.0.0/0 as a routable prefix.
If the entry name is `"all"`, this is the FortiGate equivalent of `any`.

## Application Mapping

FortiGate application names (typically uppercase) to Junos equivalents:

| FortiGate | Junos Equivalent |
|---|---|
| HTTP | junos-http |
| HTTPS | junos-https |
| SSH | junos-ssh |
| DNS | junos-dns-udp |
| FTP | junos-ftp |
| SMTP | junos-smtp |
| NTP | junos-ntp |
| SNMP | *custom app required (no predefined junos-snmp)* |
| TELNET | junos-telnet |
| PING / PING_ICMP | junos-ping |
| RDP | junos-rdp |
| MySQL | *custom app required (no predefined junos-mysql)* |
| MSSQL | junos-ms-sql |
| IMAP | junos-imap |
| POP3 | junos-pop3 |
| LDAP | junos-ldap |
| SYSLOG | junos-syslog |

## VIP as Destination NAT

FortiGate handles destination NAT via VIP objects referenced in policy `dstaddr`.

When parsing a policy with a VIP in dstaddr:
1. The VIP defines the NAT translation (extip → mappedip, extport → mappedport)
2. Generate a corresponding NAT rule with type: "destination"
3. The policy's dstaddr should reference the VIP's external IP for the intermediate schema

Flag VIP-backed policies for review — the combined policy+NAT pattern differs from
zone-based firewalls.

## Profile Group Resolution

When `set profile-group <name>` is used:
1. Look up `config utm profile-group` → `edit <name>`
2. Extract individual profile assignments:
   ```
   set av-profile "default"
   set webfilter-profile "strict"
   set ips-sensor "protect"
   ```
3. Set `profile_group: "<name>"` AND populate `security_profiles`

When individual profiles are set directly (not via group):
- Only populate `security_profiles`, leave `profile_group` empty

## UTM Profile Mapping

| FortiGate Field | Intermediate Schema Key |
|---|---|
| av-profile | virus |
| webfilter-profile | url-filtering |
| ips-sensor | idp |
| application-list | (application control — no direct map) |
| ssl-ssh-profile | ssl-proxy |
| dnsfilter-profile | (DNS filtering — no direct map) |
| emailfilter-profile | (email filtering — no direct map) |
| dlp-profile | dlp |

Profiles without a direct intermediate mapping should be preserved in `residual_raw` or noted in
`metadata.warnings` for reference. Do not invent a vendor-specific top-level property for them —
the schema has no such field.

## Logging Interpretation

| FortiGate Setting | Intermediate Mapping |
|---|---|
| `set logtraffic all` | log_end: true (log_start only if `logtraffic-start enable`) |
| `set logtraffic utm` | log_start: false, log_end: false (UTM events only — add info warning) |
| `set logtraffic disable` | log_start: false, log_end: false |
| `set logtraffic-start enable` | log_start: true (controlled separately from `logtraffic`) |

## Schedule Handling

| Schedule Name | Meaning |
|---|---|
| `"always"` | No time restriction — emit `"always"` as-is; flag only non-always schedules for conversion caveats |
| Any other name | Reference to schedule object |

Parse schedule definitions from:
- `config firewall schedule recurring` — weekly recurring
- `config firewall schedule onetime` — one-time window
- `config firewall schedule group` — group of schedules

## Policy ID vs Name

FortiGate uses numeric IDs as primary identifiers (`edit 1`).
The `set name` field is optional and may be empty.

When name is empty, use the policy ID as the name: `"Policy-1"`, `"Policy-2"`, etc.

## Multi-VDOM Handling

1. Detect VDOM context from `config vdom` sections
2. Each interface has `set vdom <name>` — use this to assign interfaces to VDOMs
3. Parse policies within each VDOM context
4. Tag all items with `_vdom: "<name>"`
5. Merge into flat arrays

## Intrazone Policy

Only model intrazone behavior for EXPLICIT `config system zone` entries that carry
`set intrazone deny|allow`:
- Explicit `set intrazone allow` → append implicit intra-zone allow rule for that zone
- Explicit `set intrazone deny` → append implicit intra-zone deny rule for that zone
- Do NOT fabricate intra-zone allow/deny policies for raw interface auto-zones (interfaces used
  directly in policies but never declared in `config system zone`) — they have no intrazone setting.
- This differs from PAN-OS where intra-zone is always allowed by default.

## Common Warnings

| Condition | Severity | Message |
|---|---|---|
| Geography address type | unsupported | "Geography-based addresses require GeoIP database" |
| Wildcard address | warning | "Wildcard addresses have limited cross-platform support" |
| Wildcard FQDN | warning | "Wildcard FQDNs have limited cross-platform support" |
| VIP in dstaddr | info | "Policy uses VIP for destination NAT — review NAT mapping" |
| `logtraffic utm` only | info | "Only UTM events logged — consider enabling full traffic logging" |
| `logtraffic disable` | warning | "Traffic logging disabled on this policy" |
| Policy with `action accept` + no UTM | info | "No UTM inspection on permit rule" |
| FSSO groups in policy | warning | "FSSO user/group matching requires identity integration" |
| `set status disable` | info | "Policy is disabled" |

## Canonical Application Mapping

Map FortiOS application names to canonical application identifiers for cross-vendor conversion and comparison. When application references are resolved, populate the policy's `apps` array with the canonical mapping while keeping service matches separate.

| FortiOS Name | Canonical App | Category |
|-------------|---------------|----------|
| `HTTPS` | `https` | web |
| `HTTP` | `http` | web |
| `SSH` | `ssh` | remote-access |
| `RDP` | `rdp` | remote-access |
| `DNS` | `dns` | network-mgmt |
| `SMTP` | `smtp` | email |
| `NTP` | `ntp` | network-mgmt |
| `SNMP` | `snmp` | network-mgmt |
| `FTP` | `ftp` | file-transfer |
| `TFTP` | `tftp` | file-transfer |
| `SIP` | `sip` | voip |
| `LDAP` | `ldap` | auth |
| `Kerberos` | `kerberos` | auth |
| `SMB` | `smb` | file-transfer |
| `MySQL` | `mysql` | database |
| `MSSQL` | `mssql` | database |
| `PostgreSQL` | `postgresql` | database |
| `MongoDB` | `mongodb` | database |
| `Zoom` | `zoom` | collaboration |
| `Microsoft.Teams` | `ms-teams` | collaboration |
| `Slack` | `slack` | collaboration |
| `YouTube` | `youtube` | streaming |
| `Netflix` | `netflix` | streaming |

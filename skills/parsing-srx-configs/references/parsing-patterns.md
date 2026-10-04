# SRX Parsing Patterns and Edge Cases

## Contents

- [Name Sanitization](#name-sanitization)
- [IP Version Detection](#ip-version-detection)
- [Address Type Inference](#address-type-inference)
- [Port Range Normalization](#port-range-normalization)
- [Application Mapping (Cross-Vendor)](#application-mapping-cross-vendor)
- [Well-Known Ports Reverse Lookup](#well-known-ports-reverse-lookup)
- [Global Policies](#global-policies)
- [Action Mapping](#action-mapping)
- [Security Profile Extraction](#security-profile-extraction)
- [Scheduler Parsing](#scheduler-parsing)
- [Screen/IDS Profile Fields](#screenids-profile-fields)
- [Common Warnings to Generate](#common-warnings-to-generate)
- [Canonical Application Mapping](#canonical-application-mapping)

## Name Sanitization

Junos names have these constraints:
- Maximum 63 characters (truncate with hash suffix if longer)
- Valid characters: alphanumeric, hyphen, underscore, period
- Replace invalid characters (spaces, slashes, etc.) with underscores
- Collapse multiple consecutive underscores

## IP Version Detection

```
v4: matches /^(\d{1,3}\.){3}\d{1,3}/ or contains "."
v6: contains ":"
null: for FQDNs and non-IP values
```

## Address Type Inference

When parsing address objects from `set security address-book global address <name> <value>`:
- If value contains `/` and looks like IP → subnet (or host if /32 or /128)
- If `dns-name` keyword → fqdn
- If `range-address` keyword with `to` → range
- If `wildcard-address` keyword → wildcard

## Port Range Normalization

Junos port ranges use hyphen: `1024-65535`
Single ports: `443`
Normalize all port specifications to these formats.

## Application Mapping (Cross-Vendor)

When encountering non-Junos application names (from imported configs), map to Junos predefined apps:

| Common Name | Junos Equivalent |
|---|---|
| HTTP / http / web-browsing | junos-http |
| HTTPS / https / ssl | junos-https |
| SSH / ssh / Secure-Shell | junos-ssh |
| DNS / dns / domain | junos-dns-udp + junos-dns-tcp |
| FTP / ftp | junos-ftp |
| SMTP / smtp | junos-smtp |
| NTP / ntp | junos-ntp |
| SNMP / snmp | *custom app required (no predefined junos-snmp)* |
| syslog | junos-syslog |
| ICMP / icmp / ping | junos-ping |
| RDP / rdp / ms-rdp | junos-rdp |
| MySQL / mysql | *custom app required (no predefined junos-mysql)* |
| MSSQL / ms-sql | junos-ms-sql |

## Well-Known Ports Reverse Lookup

When a service is defined by protocol/port only, check if it matches a predefined app:

| Protocol/Port | Junos App |
|---|---|
| tcp/22 | junos-ssh |
| tcp/23 | junos-telnet |
| tcp/25 | junos-smtp |
| tcp/80 | junos-http |
| tcp/443 | junos-https |
| udp/53 | junos-dns-udp |
| tcp/53 | junos-dns-tcp |
| udp/123 | junos-ntp |
| udp/161 | *no predefined match — keep custom* |
| udp/514 | junos-syslog |
| tcp/3306 | *no predefined match — keep custom* |
| tcp/3389 | junos-rdp |

## Global Policies

Global policies (`set security policies global policy <name>`) apply to all zone pairs.
They are evaluated after all zone-specific policies.
Set `src_zones: ["any"]` and `dst_zones: ["any"]`.

## Action Mapping

| SRX Action | Intermediate Action |
|---|---|
| permit | allow |
| deny | deny |
| reject | reset-both |

## Security Profile Extraction

From policy `then permit application-services`:
```
utm-policy <name>        → profile_group: "<name>"
idp-policy <name>        → security_profiles.idp: "<name>"
ssl-proxy profile-name <name> → security_profiles.ssl-proxy: "<name>"
```

UTM policy references are set as `profile_group`. Individual IDP and SSL proxy are set
in `security_profiles`.

## Scheduler Parsing

Schedulers are better parsed directly from set commands (not the config tree) due to
complex time-range syntax. Look for:
```
set schedulers scheduler <name> ...
```

## Screen/IDS Profile Fields

| Config Path | Schema Field |
|---|---|
| `tcp syn-flood alarm-threshold` | tcp.syn-flood.alarm-threshold |
| `tcp syn-flood attack-threshold` | tcp.syn-flood.attack-threshold |
| `tcp land` | tcp.land: true |
| `icmp ping-death` | icmp.ping-death: true |
| `icmp flood threshold` | icmp.flood.threshold |
| `udp flood threshold` | udp.flood.threshold |
| `ip spoofing` | ip.spoofing: true |
| `ip source-route-option` | ip.source-route-option: true |
| `limit-session source-ip-based` | limit_session.source-ip-based |
| `limit-session destination-ip-based` | limit_session.destination-ip-based |

## Common Warnings to Generate

| Condition | Severity | Message |
|---|---|---|
| Wildcard address object | warning | "Wildcard addresses have limited cross-platform support" |
| Policy with `any` src + dst + app | warning | "Overly permissive rule — allows all traffic" |
| Permit without session-close log | info | "Consider enabling session-close logging" |
| Deactivated policy | info | "Policy is deactivated (inactive)" |
| Unknown application name | warning | "Application not in predefined list — may need manual mapping" |

## Canonical Application Mapping

Map JunOS predefined application names to canonical application identifiers for cross-vendor conversion and comparison. JunOS uses `junos-*` applications matched by name in security policies. For each resolved application, populate the policy's `apps` array with the canonical mapping.

| JunOS Name | Protocol/Port | Canonical App | Category |
|------------|---------------|---------------|----------|
| `junos-https` | TCP/443 | `https` | web |
| `junos-http` | TCP/80 | `http` | web |
| `junos-ssh` | TCP/22 | `ssh` | remote-access |
| `junos-telnet` | TCP/23 | `telnet` | remote-access |
| `junos-ftp` | TCP/21 | `ftp` | file-transfer |
| `junos-tftp` | UDP/69 | `tftp` | file-transfer |
| `junos-dns-udp` | UDP/53 | `dns` | network-mgmt |
| `junos-dns-tcp` | TCP/53 | `dns` | network-mgmt |
| `junos-ntp` | UDP/123 | `ntp` | network-mgmt |
| `junos-smtp` | TCP/25 | `smtp` | email |
| `junos-smtps` | TCP/587, TCP/465 | `smtps` | email |
| `junos-imap` | TCP/143 | `imap` | email |
| `junos-imaps` | TCP/993 | `imaps` | email |
| `junos-pop3` | TCP/110 | `pop3` | email |
| `junos-ldap` | TCP/389 | `ldap` | auth |
| `junos-bgp` | TCP/179 | `bgp` | network-mgmt |
| `junos-ospf` | IP-89 | `ospf` | network-mgmt |
| `junos-sip` | UDP/5060 | `sip` | voip |
| `junos-h323` | TCP/1720 (+UDP/1719 RAS, TCP/1503/389/522/1731 — multi-term) | `h323` | voip |
| `junos-ms-rpc` | TCP+UDP/135 (application-set) | `msrpc` | other |
| `junos-ms-sql` | TCP/1433 | `mssql` | database |
| `junos-smb` | TCP/139, TCP/445 | `smb` | file-transfer |
| `junos-ike` | UDP/500 | `ipsec` | tunnel |
| `junos-ike-nat` | UDP/4500 | `ipsec-nat-t` | tunnel |
| `junos-pptp` | TCP/1723 | `pptp` | tunnel |
| `junos-ping` | ICMP (proto 1, all types) | `ping` | network-mgmt |
| `junos-icmp-ping` | ICMP echo-request | `ping` | network-mgmt |
| `junos-icmp-all` | ICMP (all types) | `icmp-all` | network-mgmt |
| `junos-pingv6` | ICMPv6 (proto 58, all types) | `ping6` | network-mgmt |
| `junos-icmp6-all` | ICMPv6 (all types) | `icmpv6-all` | network-mgmt |
| `junos-nntp` | TCP/119 | `nntp` | other |
| `junos-rdp` | TCP/3389 | `rdp` | remote-access |
| `junos-syslog` | UDP/514 | `syslog` | network-mgmt |

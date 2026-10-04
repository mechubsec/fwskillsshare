# SRX Config Parsing Example

## Contents

- [Input Config (Set Commands)](#input-config-set-commands)
- [Extracted Output](#extracted-output)

## Input Config (Set Commands)

```
set security zones security-zone trust interfaces ge-0/0/0.0
set security zones security-zone trust host-inbound-traffic system-services ping
set security zones security-zone trust host-inbound-traffic system-services ssh
set security zones security-zone untrust interfaces ge-0/0/1.0
set security zones security-zone dmz interfaces ge-0/0/2.0

set security address-book global address web-server 10.0.1.10/32
set security address-book global address app-server 10.0.1.20/32
set security address-book global address internal-net 10.0.0.0/16
set security address-book global address partner-net 172.16.0.0/12
set security address-book global address-set servers address web-server
set security address-book global address-set servers address app-server

set applications application custom-app protocol tcp
set applications application custom-app destination-port 8080-8090

set security policies from-zone trust to-zone untrust policy allow-web match source-address internal-net
set security policies from-zone trust to-zone untrust policy allow-web match destination-address any
set security policies from-zone trust to-zone untrust policy allow-web match application junos-http
set security policies from-zone trust to-zone untrust policy allow-web match application junos-https
set security policies from-zone trust to-zone untrust policy allow-web then permit
set security policies from-zone trust to-zone untrust policy allow-web then log session-close

set security policies from-zone untrust to-zone dmz policy allow-inbound-web match source-address any
set security policies from-zone untrust to-zone dmz policy allow-inbound-web match destination-address web-server
set security policies from-zone untrust to-zone dmz policy allow-inbound-web match application junos-https
set security policies from-zone untrust to-zone dmz policy allow-inbound-web then permit application-services utm-policy default-utm
set security policies from-zone untrust to-zone dmz policy allow-inbound-web then log session-init
set security policies from-zone untrust to-zone dmz policy allow-inbound-web then log session-close

deactivate security policies from-zone trust to-zone dmz policy old-test-rule

set security nat source rule-set trust-to-untrust from zone trust
set security nat source rule-set trust-to-untrust to zone untrust
set security nat source rule-set trust-to-untrust rule pat-out match source-address 10.0.0.0/16
set security nat source rule-set trust-to-untrust rule pat-out then source-nat interface

set routing-options static route 0.0.0.0/0 next-hop 203.0.113.1
```

## Extracted Output

### Zones
| Name | Interfaces |
|---|---|
| trust | ge-0/0/0.0 |
| untrust | ge-0/0/1.0 |
| dmz | ge-0/0/2.0 |

### Address Objects
| Name | Type | Value | IP Version |
|---|---|---|---|
| web-server | host | 10.0.1.10/32 | v4 |
| app-server | host | 10.0.1.20/32 | v4 |
| internal-net | subnet | 10.0.0.0/16 | v4 |
| partner-net | subnet | 172.16.0.0/12 | v4 |

### Address Groups
| Name | Members |
|---|---|
| servers | web-server, app-server |

### Service Objects
| Name | Protocol | Port |
|---|---|---|
| custom-app | tcp | 8080-8090 |

### Security Policies

**Policy 1: allow-web** (rule_index: 1)
- Zones: trust → untrust
- Source: internal-net → Destination: any
- Applications: junos-http, junos-https
- Action: allow | Log: session-close
- Profiles: none

**Policy 2: allow-inbound-web** (rule_index: 2)
- Zones: untrust → dmz
- Source: any → Destination: web-server
- Applications: junos-https
- Action: allow | Log: session-init, session-close
- Profile group: default-utm

**Policy 3: old-test-rule** (rule_index: 3)
- Zones: trust → dmz
- **DISABLED** (deactivated)

**Policy 4: Implicit: Default Deny** (rule_index: 4, _implicit: true)
- Zones: any → any
- Source: any → Destination: any
- Applications: any
- Action: deny

### NAT Rules
| Name | Type | Zones | Match | Translation |
|---|---|---|---|---|
| pat-out | source | trust → untrust | 10.0.0.0/16 | interface |

### Static Routes
| Destination | Next Hop |
|---|---|
| 0.0.0.0/0 | 203.0.113.1 |

### Analysis Findings
- **Unused object:** `partner-net` is not referenced by any policy
- **Unused object:** `app-server` is only in group `servers`, which is not referenced by any policy
- **Unused group:** `servers` is not referenced by any policy
- **Unused service:** `custom-app` is not referenced by any policy
- **Disabled policy:** `old-test-rule` is deactivated

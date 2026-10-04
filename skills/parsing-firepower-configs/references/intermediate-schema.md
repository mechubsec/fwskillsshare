# Intermediate Schema Reference

## Contents

- [Top-Level Structure](#top-level-structure)
- [Zone](#zone)
- [Address Object](#address-object)
- [Address Group](#address-group)
- [Service Object](#service-object)
- [Service Group](#service-group)
- [Security Policy](#security-policy)
- [NAT Rule](#nat-rule)
- [Application (Resolved L7 App on a Policy)](#application-resolved-l7-app-on-a-policy)
- [Application Group](#application-group)
- [Schedule](#schedule)
- [Interface](#interface)
- [Static Route](#static-route)
- [HA Config](#ha-config)
- [Screen/IDS Config](#screenids-config)
- [Metadata](#metadata)
- [System](#system)
- [Security Services](#security-services)
- [Virtual Router](#virtual-router)
- [OSPF Config](#ospf-config)
- [BGP Config](#bgp-config)
- [VPN Tunnel](#vpn-tunnel)
- [Admin User](#admin-user)
- [DHCP Config](#dhcp-config)
- [Residual Raw](#residual-raw)

> Maintenance note: this schema is intentionally duplicated across the five `parsing-*` skills so each skill stays self-contained. Treat the SRX copy as canonical, sync changes to the other copies, and run `python3 scripts/check-shared-schema.py` from the repository root. See `skills/SHARED-SCHEMA.md`.

This is the vendor-neutral intermediate JSON schema that all firewall config parsers produce.
All extracted data should be normalized to this format regardless of source vendor.

## Top-Level Structure

```json
{
  "zones": [],
  "address_objects": [],
  "address_groups": [],
  "service_objects": [],
  "service_groups": [],
  "security_policies": [],
  "nat_rules": [],
  "applications": [],
  "application_groups": [],
  "schedules": [],
  "security_profile_objects": [],
  "interfaces": [],
  "static_routes": [],
  "virtual_routers": [],
  "ospf_config": {},
  "ospf3_config": {},
  "bgp_config": {},
  "ha_config": {},
  "screen_config": [],
  "vpn_tunnels": [],
  "syslog_config": [],
  "dhcp_config": [],
  "admin_users": [],
  "system": {},
  "security_services": {},
  "routing_contexts": [],
  "residual_raw": [],
  "metadata": {}
}
```

## Zone

```json
{
  "name": "trust",
  "description": "Internal network zone",
  "interfaces": ["ge-0/0/0.0", "ge-0/0/1.0"],
  "zone_type": "layer3",
  "screen": "untrust-screen",
  "host_inbound": {
    "system_services": ["ssh", "https", "ping", "dhcp", "ike"],
    "protocols": ["ospf", "bgp"]
  }
}
```

`host_inbound` tracks management-plane and routing-protocol access allowed on the zone.
- `system_services`: ssh, https, http, telnet, ping, snmp, netconf, dhcp, ntp, ike, ipsec
- `protocols`: bgp, ospf, ospf3, rip, ripng, ldp, rsvp, msdp, pim, all
- `screen`: name of the bound screen / DoS-protection profile for the zone (SRX `screen <name>`), or null. Populated where the vendor parser supports it; absent → SEC-NO-SCREEN skipped.

## Address Object

```json
{
  "name": "web-server",
  "type": "host",
  "value": "10.0.1.10/32",
  "description": "Production web server",
  "tags": ["production"],
  "ip_version": "v4"
}
```

Valid `type` values: `"host"`, `"subnet"`, `"range"`, `"fqdn"`, `"wildcard"`, `"geo"`, `"dynamic"`

- **host**: Single IP — value is `"x.x.x.x/32"` or `"::1/128"`
- **subnet**: Network — value is `"10.0.0.0/24"`
- **range**: IP range — value is `"10.0.1.1-10.0.1.254"`
- **fqdn**: Domain name — value is `"example.com"`
- **wildcard**: Wildcard mask — value is `"10.0.0.0/0.0.255.255"`
- **geo**: Geographic — value is country code `"US"`
- **dynamic**: Membership resolved at runtime, not from the config text — a
  GeoIP category, an external threat/address feed, or a tag selector. Value is a
  human-readable summary of the selector; the machine-readable form lives in
  `dynamic_source`.

### Dynamic Address Object

```json
{
  "name": "Banned_countries",
  "type": "dynamic",
  "value": "geoip:RU,KP,IR",
  "dynamic_source": {
    "kind": "geoip",
    "selector": ["RU", "KP", "IR"],
    "feed_name": "",
    "feed_url": "",
    "feed_transport": ""
  },
  "description": "",
  "tags": [],
  "ip_version": "any"
}
```

`dynamic_source.kind` values: `"geoip"`, `"feed"`, `"tag"`.

- **geoip** — country/region selector. `selector` holds the country codes.
- **feed** — external feed. `feed_name` is the configured feed, `feed_url` the
  server URL, and `feed_transport` is `"https"` or `"http"` (recording the
  transport lets consumers reason about feed integrity).
- **tag** — tag/label match evaluated against runtime endpoint state.

**A dynamic address object is a defined object.** Consumers resolving policy
address references must count it as resolved; treating it as missing produces
false undefined-reference findings on every rule that uses one. Its *members*
are unknowable from the config, so any check that needs concrete addresses
(overlap, shadow, containment) must degrade to heuristic or skip rather than
assume the object is empty.

Source constructs: SRX `security dynamic-address address-name`, PAN-OS dynamic
address groups, FortiGate external threat feeds.

## Address Group

```json
{
  "name": "web-servers",
  "members": ["web-server-1", "web-server-2"],
  "description": "All web servers",
  "tags": []
}
```

## Service Object

```json
{
  "name": "custom-https",
  "protocol": "tcp",
  "port_range": "8443",
  "source_port": "",
  "description": "Custom HTTPS port"
}
```

Port range formats: `"80"`, `"80-443"`, `"1024-65535"`
Protocol values: `"tcp"`, `"udp"`, `"icmp"`, `"icmpv6"`, `"sctp"`, `"ip"`, `"any"`

## Service Group

```json
{
  "name": "web-services",
  "members": ["HTTP", "HTTPS", "custom-https"],
  "description": ""
}
```

## Security Policy

```json
{
  "name": "allow-web-traffic",
  "src_zones": ["trust"],
  "dst_zones": ["untrust"],
  "src_addresses": ["internal-nets"],
  "dst_addresses": ["any"],
  "negate_source": false,
  "negate_destination": false,
  "applications": ["junos-http", "junos-https"],
  "services": ["application-default"],
  "dynamic_applications": [],
  "url_categories": [],
  "app_groups": [],
  "action": "allow",
  "log_start": false,
  "log_end": true,
  "profile_group": "",
  "security_profiles": {
    "virus": "default",
    "url-filtering": "strict-filtering"
  },
  "description": "Allow outbound web access",
  "tags": ["outbound"],
  "disabled": false,
  "schedule": "",
  "source_users": [],
  "_rule_index": 1,
  "_implicit": false
}
```

### Narrowing Fields

`applications`, `services`, `dynamic_applications`, `url_categories`,
`app_groups`, `source_users`, and `schedule` all restrict what a rule matches.
A rule is only an unrestricted any/any/any rule when **every** one of them is
`any`, empty, or absent — alongside `any` source and destination addresses.

`dynamic_applications` carries runtime application-identity matches (SRX
`match dynamic-application`, e.g. `junos:DNS-ENCRYPTED`; PAN-OS App-ID
members). Dropping it has two consequences, both observed on a live device:
an AppID-scoped deny at the tail of a rulebase reads as a terminal deny-all
when it is not, and two rules differing only by App-ID scope collapse into a
false duplicate. Any rule-identity or catch-all test must include it.

### Action Values
- `"allow"` — permit traffic
- `"deny"` — silently drop traffic
- `"drop"` — silently drop (alias for deny on some platforms)
- `"reset-both"` — send TCP RST to both sides (reject)

### Security Profile Keys
- `"virus"` — antivirus profile
- `"url-filtering"` — URL/web filtering
- `"idp"` — IPS/IDP profile
- `"anti-spyware"` — anti-spyware (PAN-OS specific)
- `"file-blocking"` — file blocking profile
- `"wildfire"` — WildFire analysis
- `"dlp"` — data loss prevention
- `"ssl-proxy"` — SSL decryption/proxy profile

### Internal Fields (prefixed with `_`)
- `_rule_index` — sequential position in the rulebase (1-based)
- `_implicit` — true for vendor-implicit rules (appended by parser)
- `_logical_system` — SRX logical-system context name
- `_tenant` — SRX tenant context name
- `_vsys` — PAN-OS vsys name
- `_vdom` — FortiGate VDOM name
- `added_by_fpic` — marker that this rule was auto-generated

## NAT Rule

```json
{
  "name": "source-nat-outbound",
  "type": "source",
  "src_zones": ["trust"],
  "dst_zones": ["untrust"],
  "src_addresses": ["internal-nets"],
  "dst_addresses": ["any"],
  "translated_src": {
    "type": "interface",
    "addresses": []
  },
  "translated_dst": null,
  "translated_port": null,
  "description": "PAT to outside interface",
  "_rule_index": 1
}
```

### NAT Type Values
- `"source"` — source NAT only
- `"destination"` — destination NAT only
- `"static"` — bidirectional static NAT
- `"source-and-destination"` — both source and destination translated

### translated_src Object
```json
{
  "type": "interface",
  "addresses": []
}
```
Type values: `"interface"`, `"dynamic-ip-pool"`, `"static"`, `"no-nat"`

## Application (Resolved L7 App on a Policy)

When a security policy references an application by vendor-specific name, resolve it to a canonical
vendor-neutral entry. Each resolved app is stored in the policy's `apps` array.

```json
{
  "vendor_name": "junos-https",
  "canonical": "https",
  "confidence": 1.0,
  "category": "web"
}
```

Fields:
- **vendor_name** — the original name as it appears in the source config
- **canonical** — vendor-neutral canonical key (lowercase, e.g., `"https"`, `"ssh"`, `"ms-teams"`)
- **confidence** — mapping confidence score: `1.0` = exact match, `0.9` = close/likely, `0.0` = unresolved
- **category** — application category for grouping and reporting

### Canonical Application Categories

| Category | Examples |
|----------|----------|
| `web` | https, http, quic, cloudflare, akamai |
| `collaboration` | ms-teams, zoom, webex, slack, ms-sharepoint, google-meet, discord |
| `email` | smtp, smtps, gmail, imap, imaps, pop3, outlook-web-app, exchange-online |
| `remote-access` | ssh, rdp, telnet, vnc, teamviewer, anydesk, citrix-ica |
| `network-mgmt` | dns, ntp, snmp, snmp-trap, netflow, ping, dhcp, syslog, bgp, ospf |
| `file-transfer` | ftp, sftp, tftp, smb, nfs, cifs, rsync |
| `database` | mysql, mssql, oracle-db, postgresql, mongodb, redis, elasticsearch |
| `cloud-storage` | ms-onedrive, google-drive, dropbox, box, aws, azure, gcp |
| `streaming` | youtube, netflix, rtp, rtsp, spotify, twitch |
| `voip` | sip, h323, mgcp, sccp |
| `auth` | ldap, ldaps, kerberos, radius, tacacs, ms-ad, okta, duo |
| `tunnel` | ipsec, openvpn, gre, l2tp, wireguard, ssl-vpn |
| `social` | facebook, twitter, linkedin, instagram, whatsapp |
| `security` | crowdstrike, sentinelone, zscaler, palo-alto-networks, splunk |
| `other` | docker, kubernetes, kafka, jenkins, grafana, terraform |

### Cross-Vendor Application Name Mapping

Each canonical application has vendor-specific names. The parser must resolve FROM the source
vendor's name TO the canonical key. When rendering/converting, resolve FROM canonical TO the
target vendor's name.

Example mappings:

| Canonical | JunOS | FortiOS | PAN-OS | FTD/ASA |
|-----------|-------|---------|--------|---------|
| `https` | `junos-https` | `HTTPS` | `ssl` | `HTTPS` |
| `http` | `junos-http` | `HTTP` | `web-browsing` | `HTTP` |
| `ssh` | `junos-ssh` | `SSH` | `ssh` | `SSH` |
| `dns` | `junos-dns-udp` | `DNS` | `dns` | `DNS` |
| `rdp` | `junos-rdp` | `RDP` | `ms-rdp` | `RDP` |
| `msrpc` | `junos-ms-rpc` | `MS-RPC` | `msrpc` | `MSRPC` |
| `smtp` | `junos-smtp` | `SMTP` | `smtp` | `SMTP` |
| `ntp` | `junos-ntp` | `NTP` | `ntp` | `NTP` |
| `snmp` | *custom app* (UDP/161; no predefined) | `SNMP` | `snmp` | `SNMP` |

Resolution algorithm:
1. **Pass 1 — Vendor-name match:** Look up the source vendor's name across all canonical entries
2. **Pass 2 — Canonical-key match:** Check if the name is already a canonical key (e.g., PAN-OS uses `ssh` directly)
3. **Unresolved:** If no match, set `confidence: 0.0` and keep the vendor_name as-is with a warning

### Policies: `applications` vs `services` vs `apps` vs `app_groups`

- **`services`** — port/protocol-based match references (service objects/groups). Always present.
- **`applications`** — raw vendor-specific application names as they appear in the config (preserved for reference)
- **`apps`** — resolved application entries (array of `{vendor_name, canonical, confidence, category}`)
- **`app_groups`** — application group names referenced by this policy

When a policy references an application name:
1. Check if it is actually a service object or service group → promote to `services`
2. Check if it is an application group → add to `app_groups`
3. Otherwise resolve to canonical via the mapping → add to `apps`

### Conversion Caveats for Applications

- **Port-based platforms (ASA/FTD):** Cannot natively match L7 applications. When converting TO ASA, application rules must be decomposed into port-based service matches. Add a preflight warning.
- **Confidence < 1.0:** Flag for manual review during conversion.
- **Unresolved apps (confidence 0.0):** Cannot be converted — emit as residual with a warning.
- **Category mismatch:** Some apps exist on one platform but not another (e.g., `ms-teams` on PAN-OS has no ASA equivalent). Emit a warning and leave as residual.

## Application Group

```json
{
  "name": "web-apps",
  "members": ["https", "http", "quic"],
  "description": "Web browsing applications",
  "used": true
}
```

Application groups use **canonical** application keys as members (not vendor-specific names).
During parsing, resolve each member from vendor-specific to canonical.

When an application-set or application-group contains a mix of L7 apps and port-based
services, split them: L7 apps go to `application_groups`, port-based go to `service_groups`.

## Schedule

```json
{
  "name": "business-hours",
  "type": "recurring",
  "days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
  "start": "08:00",
  "end": "18:00"
}
```

## Interface

```json
{
  "name": "ge-0/0/0.0",
  "ip": "10.0.1.1/24",
  "ipv6": "2001:db8::1/64",
  "zone": "trust",
  "vlan": null,
  "type": "physical",
  "description": "LAN interface",
  "status": "up",
  "speed": "1g",
  "mtu": 1500,
  "is_mgmt": false,
  "dhcp_client": false,
  "dhcp_relay": [],
  "lag_parent": null,
  "lag_members": [],
  "is_subif": false,
  "parent_interface": null
}
```

Interface `type` values: `"physical"`, `"loopback"`, `"lag"`, `"vlan"`, `"tunnel"`, `null`

## Static Route

```json
{
  "name": "default-route",
  "destination": "0.0.0.0/0",
  "next_hop": "203.0.113.1",
  "next_hop_type": "ip",
  "interface": "",
  "metric": 10,
  "vrf": ""
}
```

## HA Config

```json
{
  "enabled": true,
  "mode": "active-passive",
  "group_id": 1,
  "priority": 200,
  "preempt": true,
  "peer_ip": "10.0.0.2",
  "ha_interfaces": [
    {"name": "fab0", "role": "fabric", "ip": "10.255.0.1/24"}
  ],
  "monitoring": {
    "interfaces": ["ge-0/0/0", "ge-0/0/1"],
    "failure_threshold": 255
  }
}
```

## Screen/IDS Config

```json
{
  "name": "outside-screen",
  "zone": "untrust",
  "icmp": {"ping-death": true, "flood": {"threshold": 1000}},
  "tcp": {"syn-flood": {"alarm-threshold": 1024, "attack-threshold": 2048}, "land": true},
  "udp": {"flood": {"threshold": 1000}},
  "ip": {"spoofing": true, "source-route-option": true},
  "limit_session": {"source-ip-based": 128, "destination-ip-based": 128}
}
```

## Metadata

```json
{
  "source_vendor": "srx",
  "source_version": "",
  "export_date": "",
  "rule_count": 42,
  "nat_rule_count": 5,
  "object_count": 120,
  "zone_count": 4,
  "interface_count": 8,
  "ha_enabled": true
}
```

Valid `source_vendor` values: `"srx"`, `"panos"`, `"fortigate"`, `"cisco_asa"`, `"checkpoint"`, `"sonicwall"`, `"huawei_usg"`

## System

```json
{
  "hostname": "fw-primary",
  "domain_name": "example.com",
  "dns_servers": ["8.8.8.8", "8.8.4.4"],
  "ntp_servers": [{"address": "pool.ntp.org", "prefer": true}],
  "dhcp_relay": [],
  "mgmt_services": {
    "ssh": true,
    "https": true,
    "http": false,
    "telnet": false,
    "netconf": null,
    "snmp": null
  },
  "ssh": {
    "root_login": "deny-password",
    "rate_limit": 32,
    "ciphers": [],
    "protocol_version": null,
    "connection_limit": null
  },
  "auth": {
    "password_policy": {"min_length": 12, "complexity": "character-sets"},
    "login_lockout": {"tries": 3, "lockout_period": 5},
    "root_authentication_present": true
  },
  "control_plane_protection": {
    "re_filter_present": true,
    "applied_to": ["lo0.0"]
  },
  "multicast_routing": {
    "present": false,
    "protocols": []
  }
}
```

- `ssh.root_login`: allow | deny | deny-password | null. `ssh.rate_limit`/`connection_limit`: ints or null. Generic across vendors (SRX `system services ssh`, Cisco `ssh`/`http` servers, Palo/Forti admin access).
- `auth`: password policy + login lockout + whether a root credential is set. `control_plane_protection.re_filter_present`: a stateless device/control-plane protection filter is applied (SRX lo0 input filter; Cisco CoPP; Palo/Forti mgmt profile). All optional; absent → the dependent check skips.
- `multicast_routing.present`: the device has multicast routing configured (SRX `protocols igmp`/`pim`/`mld` or multicast `forwarding-options`; Cisco `ip pim`/`ip igmp`; Palo/Forti multicast). `protocols` lists which families appeared (e.g. `["igmp","pim"]`); full stanza detail goes to `residual_raw`. Presence flag only, not a full multicast parse. All optional; absent → dependent checks skip.

## Security Services

```json
{
  "app_id": true,
  "idp": true,
  "secintel": true,
  "aamw": true,
  "utm": true
}
```

Presence flags for advanced security services configured on the device
(application identification, IDP/IPS, security intelligence, advanced anti-malware,
UTM). The audit's SEC-SERVICES-UNREFERENCED check compares these against
`security_policies[].security_profiles` to find configured-but-inert services.
Populated where the vendor parser supports it; absent → the check is skipped.

## Virtual Router

```json
{
  "name": "default",
  "interfaces": ["ge-0/0/0.0", "ge-0/0/1.0"]
}
```

## OSPF Config

```json
{
  "router_id": "10.0.0.1",
  "reference_bandwidth": 100,
  "areas": [
    {
      "id": "0.0.0.0",
      "type": "normal",
      "no_summary": false,
      "default_cost": null,
      "authentication": null,
      "interfaces": [
        {
          "name": "ge-0/0/0.0",
          "passive": false,
          "enabled": true,
          "metric": null,
          "priority": null,
          "hello_interval": null,
          "dead_interval": null,
          "link_type": null,
          "authentication": null
        }
      ]
    }
  ],
  "redistribute": [
    {"source": "connected", "metric": null, "metric_type": null}
  ]
}
```

Area `type` values: `"normal"`, `"stub"`, `"nssa"`

## BGP Config

```json
{
  "local_as": 65001,
  "router_id": "10.0.0.1",
  "keepalive": 60,
  "holdtime": 180,
  "neighbors": [
    {
      "address": "10.0.0.2",
      "remote_as": 65002,
      "description": "Peer router",
      "update_source": "lo0",
      "password": null,
      "keepalive": null,
      "holdtime": null,
      "next_hop_self": false,
      "soft_reconfiguration": false,
      "route_reflector_client": false,
      "enabled": true
    }
  ],
  "networks": ["10.0.0.0/24"],
  "redistribute": [
    {"source": "connected", "metric": null}
  ]
}
```

## VPN Tunnel

```json
{
  "name": "vpn-to-branch",
  "ike": {
    "version": "ikev2",
    "local_address": "203.0.113.1",
    "remote_address": "198.51.100.1",
    "local_id": null,
    "remote_id": null,
    "auth_method": "psk",
    "psk": "****",
    "local_cert": null,
    "ca_profile": null,
    "proposal": {
      "encryption": ["aes-256"],
      "integrity": ["sha256"],
      "dh_group": [14],
      "lifetime": 86400
    }
  },
  "ipsec": {
    "proposal": {
      "encryption": ["aes-256"],
      "integrity": ["sha256"],
      "dh_group": [14],
      "lifetime": 3600
    },
    "mode": "tunnel"
  },
  "tunnel_interface": "st0.0",
  "tunnel_ip": "10.255.0.1/30",
  "vr": "default",
  "routes": ["192.168.10.0/24", "192.168.20.0/24"]
}
```

Canonical encryption values: `"des"`, `"3des"`, `"aes-128"`, `"aes-192"`, `"aes-256"`, `"aes-128-gcm"`, `"aes-256-gcm"`
Canonical integrity values: `"md5"`, `"sha1"`, `"sha256"`, `"sha384"`, `"sha512"`

## Admin User

```json
{
  "name": "admin",
  "role": "super-admin",
  "privilege_level": 15,
  "ssh_keys": ["ssh-rsa AAAA..."],
  "source_vendor": "cisco_asa"
}
```

Role values: `"super-admin"`, `"admin"`, `"operator"`, `"read-only"`

## DHCP Config

```json
{
  "interface": "inside",
  "network": "10.0.1.0/24",
  "pools": [{"start": "10.0.1.100", "end": "10.0.1.200"}],
  "gateway": "10.0.1.1",
  "dns_servers": ["8.8.8.8"],
  "domain": "example.com",
  "lease_time": 86400,
  "reservations": []
}
```

## Residual Raw

```json
{
  "label": "VPN/IPsec",
  "text": "crypto map outside_map 10 match address ..."
}
```

Captures unparsed configuration sections for manual review.
Standard labels: VPN/IPsec, AAA, QoS, PKI/Certificates, Routing Protocols, Wireless, Switching, DNS, NTP, SNMP, Other

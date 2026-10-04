# FortiOS Configuration Format Reference

## Contents

- [Block Syntax](#block-syntax)
- [Firewall Address Types](#firewall-address-types)
- [Firewall Service](#firewall-service)
- [Firewall Policy](#firewall-policy)
- [VIP (Destination NAT)](#vip-destination-nat)
- [IP Pool (Source NAT)](#ip-pool-source-nat)
- [System Zone](#system-zone)
- [System Interface](#system-interface)
- [HA Configuration](#ha-configuration)
- [Multi-VDOM](#multi-vdom)
- [Predefined Services](#predefined-services)

## Block Syntax

FortiGate configs use a hierarchical block format with these keywords:

| Keyword | Purpose |
|---|---|
| `config <section>` | Opens a configuration section |
| `edit <name\|id>` | Creates or selects an entry within a section |
| `set <key> <value>` | Sets a property on the current entry |
| `unset <key>` | Removes a property (rarely seen in full configs) |
| `next` | Closes the current `edit` entry |
| `end` | Closes the current `config` section |

### Nesting

Sections can nest — `config` blocks inside `edit` entries:

```
config firewall policy
    edit 1
        set name "allow-web"
        set srcintf "port1"
        set dstintf "port2"
        set srcaddr "all"
        set dstaddr "all"
        set action accept
        set schedule "always"
        set service "HTTP" "HTTPS"
        set logtraffic all
        config identity-based-policy
            edit 1
                set groups "VPN-Users"
            next
        end
    next
    edit 2
        ...
    next
end
```

### Value Formats

- **Unquoted:** `set action accept`
- **Quoted strings:** `set name "Allow Web Traffic"`
- **Multi-value (space-separated quoted):** `set service "HTTP" "HTTPS" "DNS"`
- **Numeric:** `set policyid 1`
- **Boolean-like:** `set status enable` / `set status disable`

## Firewall Address Types

```
config firewall address
    edit "web-server"
        set type ipmask
        set subnet 10.0.1.10 255.255.255.255
        set comment "Production web server"
        set associated-interface "port1"
    next
    edit "internal-net"
        set type ipmask
        set subnet 10.0.0.0 255.255.0.0
    next
    edit "partner-range"
        set type iprange
        set start-ip 172.16.1.100
        set end-ip 172.16.1.200
    next
    edit "google-dns"
        set type fqdn
        set fqdn "dns.google.com"
    next
    edit "us-traffic"
        set type geography
        set country "US"
    next
    edit "wildcard-10"
        set type wildcard
        set wildcard 10.0.0.0 255.0.0.0
    next
end
```

### Subnet Mask Conversion

FortiGate uses dotted-decimal subnet masks, not CIDR notation:

| FortiGate Mask | CIDR |
|---|---|
| 255.255.255.255 | /32 (host) |
| 255.255.255.0 | /24 |
| 255.255.0.0 | /16 |
| 255.0.0.0 | /8 |
| 0.0.0.0 | /0 |

Count the number of consecutive 1-bits in the binary representation.

## Firewall Service

```
config firewall service custom
    edit "custom-https"
        set protocol TCP/UDP/SCTP
        set tcp-portrange 8443
        set comment "Custom HTTPS port"
    next
    edit "app-ports"
        set protocol TCP/UDP/SCTP
        set tcp-portrange 8080-8090
        set udp-portrange 9000-9010
        set sctp-portrange 3868
    next
    edit "custom-icmp"
        set protocol ICMP
        set icmptype 8
        set icmpcode 0
    next
    edit "gre-proto"
        set protocol IP
        set protocol-number 47
    next
end
```

Port range format: `<dst-port>` or `<dst-port-range>` or `<dst-port>:<src-port>`
Examples: `443`, `8080-8090`, `443:1024-65535`

A single custom service may set any combination of `tcp-portrange`, `udp-portrange`, and
`sctp-portrange`. Split it into separate TCP, UDP, and/or SCTP service objects accordingly.

When `set protocol IP` carries a `set protocol-number <n>` (e.g. GRE=47, ESP=50), preserve that
IP protocol number rather than flattening to "any"; "any" is only correct when it means all IP
protocols.

## Firewall Policy

```
config firewall policy
    edit 1
        set name "allow-outbound-web"
        set srcintf "trust"
        set dstintf "untrust"
        set srcaddr "internal-net"
        set dstaddr "all"
        set action accept
        set schedule "always"
        set service "HTTP" "HTTPS"
        set logtraffic all
        set logtraffic-start enable
        set utm-status enable
        set av-profile "default"
        set webfilter-profile "default"
        set ips-sensor "default"
        set ssl-ssh-profile "certificate-inspection"
        set nat enable
        set comments "Allow outbound web access"
        set status enable
    next
    edit 2
        set name "allow-inbound-https"
        set srcintf "untrust"
        set dstintf "dmz"
        set srcaddr "all"
        set dstaddr "web-server-vip"
        set action accept
        set schedule "always"
        set service "HTTPS"
        set logtraffic all
        set utm-status enable
        set profile-group "strict-security"
    next
    edit 3
        set name "deny-all"
        set srcintf "any"
        set dstintf "any"
        set srcaddr "all"
        set dstaddr "all"
        set action deny
        set schedule "always"
        set service "ALL"
        set logtraffic all
        set status disable
    next
end
```

### Key Fields

| Field | Values | Notes |
|---|---|---|
| `action` | `accept`, `deny` | No "reject" in FortiGate |
| `logtraffic` | `all`, `utm`, `disable` | `all` = log session end (start requires `logtraffic-start enable`), `utm` = UTM events only |
| `status` | `enable`, `disable` | Disabled policies are inactive |
| `nat` | `enable`, `disable` | Enable source NAT on this policy |
| `utm-status` | `enable`, `disable` | Enables UTM profile inspection |
| `schedule` | schedule name | `"always"` means no time restriction |

## VIP (Destination NAT)

```
config firewall vip
    edit "web-server-vip"
        set extip 203.0.113.10
        set mappedip "10.0.1.10"
        set extintf "port2"
        set portforward enable
        set extport 443
        set mappedport 8443
    next
end
```

VIPs are referenced in policies as destination addresses.

## IP Pool (Source NAT)

```
config firewall ippool
    edit "outbound-pool"
        set startip 203.0.113.20
        set endip 203.0.113.30
        set type overload
    next
end
```

Pool types: `overload` (PAT), `one-to-one`, `fixed-port-range`

## System Zone

```
config system zone
    edit "trust"
        set interface "port1" "port3"
        set intrazone allow
    next
    edit "dmz"
        set interface "port4"
        set intrazone deny
    next
end
```

## System Interface

```
config system interface
    edit "port1"
        set vdom "root"
        set ip 10.0.1.1 255.255.255.0
        set type physical
        set allowaccess ping ssh https
        set alias "LAN"
    next
    edit "port2"
        set vdom "root"
        set ip 203.0.113.1 255.255.255.0
        set type physical
        set alias "WAN"
    next
end
```

## HA Configuration

```
config system ha
    set mode a-p
    set group-id 1
    set group-name "fw-cluster"
    set priority 200
    set hbdev "port5" 50
    set monitor "port1" "port2"
    set override enable
end
```

Modes: `standalone`, `a-p` (active-passive), `a-a` (active-active)

## Multi-VDOM

Real FortiOS uses a SINGLE `config vdom` block enumerating each VDOM with `edit <vdom> ... next`,
closed by one `end` — NOT repeated `config vdom ... end` blocks:

```
config vdom
    edit root
    next
    edit VDOM-Customer1
    next
end
```

Per-VDOM object configuration then appears under `config vdom` / `edit <vdom>` with the section
configs nested inside, each entry closed by `next` and the whole block by a single `end`.

Each VDOM is an independent virtual firewall with its own zones, policies, and routing.

## Predefined Services

FortiGate has predefined services that don't need explicit definition:
- `HTTP` (TCP/80), `HTTPS` (TCP/443)
- `SSH` (TCP/22), `TELNET` (TCP/23)
- `DNS` (TCP+UDP/53), `FTP` (TCP/21)
- `SMTP` (TCP/25), `NTP` (UDP/123)
- `SNMP` (UDP/161-162)
- `ALL` — matches all services
- `ALL_TCP`, `ALL_UDP`, `ALL_ICMP`

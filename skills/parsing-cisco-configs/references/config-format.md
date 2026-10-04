# Cisco ASA Configuration Format Reference

## Contents

- [Line-Oriented Format](#line-oriented-format)
- [Interface Configuration](#interface-configuration)
- [Network Objects](#network-objects)
- [Network Object Groups](#network-object-groups)
- [Service Objects](#service-objects)
- [Service Object Groups](#service-object-groups)
- [Access Lists](#access-lists)
- [Access Groups](#access-groups)
- [NAT Configuration](#nat-configuration)
- [Static Routes](#static-routes)
- [Failover (HA)](#failover-ha)
- [Transparent Mode](#transparent-mode)

## Line-Oriented Format

ASA configs from `show running-config` are line-oriented:
- Top-level commands start at column 0
- Sub-commands are indented with one space
- `!` lines are section separators (ignore)
- Lines ending with a config keyword may have indented children

## Interface Configuration

```
interface GigabitEthernet0/0
 nameif outside
 security-level 0
 ip address 203.0.113.1 255.255.255.0
 no shutdown
!
interface GigabitEthernet0/1
 nameif inside
 security-level 100
 ip address 10.0.1.1 255.255.255.0
 no shutdown
!
interface GigabitEthernet0/2
 nameif dmz
 security-level 50
 ip address 192.168.10.1 255.255.255.0
 no shutdown
!
interface GigabitEthernet0/3
 shutdown
 no nameif
```

### Security Levels
- **100** = most trusted (typically `inside`)
- **0** = least trusted (typically `outside`)
- **1-99** = intermediate trust (DMZ, management, etc.)

By default (without ACLs), traffic flows from higher to lower security levels.
ACLs override this default behavior.

## Network Objects

```
object network web-server
 host 10.0.1.10
 description Production web server
!
object network internal-net
 subnet 10.0.0.0 255.255.0.0
!
object network dhcp-range
 range 10.0.1.100 10.0.1.200
!
object network partner-api
 fqdn v4 api.partner.com
```

### Types
| Sub-command | Type | Value Format |
|---|---|---|
| `host <ip>` | host | ip/32 |
| `subnet <ip> <mask>` | subnet | ip/cidr (convert mask) |
| `range <start> <end>` | range | start-end |
| `fqdn v4 <domain>` | fqdn | domain name |
| `fqdn v6 <domain>` | fqdn | domain name |

### Inline NAT in Object
```
object network web-server
 host 10.0.1.10
 nat (inside,outside) static 203.0.113.10
```
This defines an auto/object NAT rule inline with the object definition.

## Network Object Groups

```
object-group network web-servers
 description All web servers
 network-object host 10.0.1.10
 network-object host 10.0.1.11
 network-object 10.0.2.0 255.255.255.0
 network-object object db-server
 group-object backend-servers
```

### Member Types
| Sub-command | Meaning |
|---|---|
| `network-object host <ip>` | Inline host member |
| `network-object <ip> <mask>` | Inline subnet member (mask is standard, not wildcard) |
| `network-object object <name>` | Reference to named network object |
| `group-object <name>` | Nested group reference |

## Service Objects

```
object service custom-https
 service tcp destination eq 8443
!
object service custom-range
 service tcp source range 1024 65535 destination range 8080 8090
```

Format: `service <protocol> [source <op> <port>] [destination <op> <port>]`

## Service Object Groups

```
object-group service web-services tcp
 description Web service ports
 port-object eq www
 port-object eq https
 port-object range 8080 8090
!
object-group service mixed-services
 service-object tcp destination eq 22
 service-object udp destination eq 53
 service-object icmp
 service-object object custom-https
 group-object other-services
```

### Two Flavors
1. **Protocol-specific:** `object-group service <name> <tcp|udp>` — uses `port-object`
2. **Mixed protocol:** `object-group service <name>` (no protocol) — uses `service-object`

## Access Lists

```
access-list outside_in extended permit tcp any object web-server eq 443 log
access-list outside_in extended permit tcp any object-group web-servers eq 80
access-list outside_in extended deny ip any any log
!
access-list inside_out extended permit ip object-group internal-nets any
access-list inside_out extended permit tcp any any eq 53
access-list inside_out extended permit udp any any eq 53
```

### Full ACL Line Syntax

```
access-list <id> extended <permit|deny> <protocol> <source-addr> [<source-port>] <dest-addr> [<dest-port>] [log [<level>] [interval <n>]] [time-range <name>] [inactive]
```

### Address Token Parsing

After the protocol field, parse source and destination addresses:

| Token | Meaning | Next Token |
|---|---|---|
| `any` / `any4` / `any6` | Any address | — |
| `host <ip>` | Single host | Read IP |
| `object <name>` | Named object | Read name |
| `object-group <name>` | Object group | Read name |
| `interface <nameif>` | Interface IP | Read nameif |
| `<ip> <mask>` | Network/mask pair | Read IP then mask |

**Important:** ASA ACL masks are standard subnet masks (NOT wildcard masks like IOS).
`10.0.0.0 255.255.0.0` = 10.0.0.0/16

### Port Token Parsing (TCP/UDP only)

| Token | Meaning |
|---|---|
| `eq <port>` | Equal to port |
| `range <start> <end>` | Port range |
| `gt <port>` | Greater than |
| `lt <port>` | Less than |
| `neq <port>` | Not equal (warn: limited support) |
| `object-group <name>` | Service group reference |

### Port Names

ASA accepts port names or numbers:
| Name | Number | | Name | Number |
|---|---|---|---|---|
| www | 80 | | https | 443 |
| ssh | 22 | | telnet | 23 |
| ftp | 21 | | ftp-data | 20 |
| domain | 53 | | smtp | 25 |
| ntp | 123 | | snmp | 161 |
| syslog | 514 | | ldap | 389 |
| pop3 | 110 | | imap4 | 143 |

## Access Groups

```
access-group outside_in in interface outside
access-group inside_out in interface inside
access-group global_acl global
```

Format: `access-group <acl-name> <in|out> interface <nameif>`
Or: `access-group <acl-name> global`

### Zone Derivation from Access Groups

- `access-group outside_in in interface outside`:
  - `in interface outside` means traffic is COMING IN on the outside interface
  - Source zone = ingress interface (outside); destination zone = inferred from routing or set to `any` with a warning — never blindly the ingress interface
  - The destination zone depends on routing (often requires manual review)

**Simplified approach:** For `in` direction on interface X:
- Source zone = X (the ingress interface)
- Destination zone = derived from destination addresses or set to "any" if unclear

## NAT Configuration

### Object NAT (Auto NAT)

Inside object network blocks:
```
object network web-server
 host 10.0.1.10
 nat (inside,outside) static 203.0.113.10
```

Format: `nat (<real-iface>,<mapped-iface>) <static|dynamic> <mapped-addr|interface|pat-pool>`

### Twice NAT (Manual NAT)

Top-level commands:
```
nat (inside,outside) source static internal-net internal-net destination static vpn-net vpn-net
nat (inside,outside) source dynamic internal-net interface
nat (inside,outside) 1 source static web-server 203.0.113.10 service tcp-80 tcp-80
```

Format: `nat (<real>,<mapped>) [<line>] [after-auto] source <static|dynamic> <real-src> <mapped-src> [destination <static> <real-dst> <mapped-dst>] [service <real-svc> <mapped-svc>]`

The optional numeric token is a **line number** (rule position within its manual NAT section), NOT a section selector. Section is derived from rule form: manual/twice NAT without `after-auto` = Section 1; object/auto NAT (inside `object network` blocks) = Section 2; manual NAT with the `after-auto` keyword = Section 3 (evaluated after all auto NAT).

## Static Routes

```
route outside 0.0.0.0 0.0.0.0 203.0.113.254 1
route inside 10.0.0.0 255.255.0.0 10.0.1.254 1
```

Format: `route <nameif> <dest-ip> <dest-mask> <gateway> [<metric>]`

## Failover (HA)

```
failover
failover lan unit primary
failover lan interface failover-link GigabitEthernet0/3
failover interface ip failover-link 10.0.255.1 255.255.255.0 standby 10.0.255.2
failover link state-link GigabitEthernet0/4
failover interface ip state-link 10.0.254.1 255.255.255.0 standby 10.0.254.2
```

## Transparent Mode

```
firewall transparent
!
interface GigabitEthernet0/0
 bridge-group 1
 nameif outside
 security-level 0
!
interface GigabitEthernet0/1
 bridge-group 1
 nameif inside
 security-level 100
!
interface BVI1
 ip address 10.0.1.1 255.255.255.0
```

In transparent mode, interfaces use bridge-groups instead of IP addresses.
BVI interfaces carry the management IP.

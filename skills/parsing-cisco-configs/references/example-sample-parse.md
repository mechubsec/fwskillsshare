# Cisco ASA Config Parsing Example

## Contents

- [Input Config](#input-config)
- [Extracted Output](#extracted-output)

## Input Config

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
object network web-server
 host 192.168.10.10
 description Production web server
 nat (dmz,outside) static 203.0.113.10
!
object network app-server
 host 192.168.10.20
 description Application server
!
object network internal-net
 subnet 10.0.0.0 255.255.0.0
!
object network partner-net
 subnet 172.16.0.0 255.240.0.0
!
object-group network dmz-servers
 description All DMZ servers
 network-object object web-server
 network-object object app-server
!
object-group service web-ports tcp
 port-object eq www
 port-object eq https
 port-object range 8080 8090
!
access-list outside_in extended permit tcp any object web-server eq https log
access-list outside_in extended permit tcp any object web-server eq 8443 log
access-list outside_in extended deny ip any any log
!
access-list inside_out extended permit tcp object internal-net any object-group web-ports
access-list inside_out extended permit udp object internal-net any eq domain
access-list inside_out extended permit tcp object internal-net any eq domain
access-list inside_out extended permit icmp object internal-net any echo
access-list inside_out extended deny ip any any log
!
access-list dmz_out extended permit tcp object-group dmz-servers object internal-net eq 3306
access-list dmz_out extended deny ip any any
!
access-group outside_in in interface outside
access-group inside_out in interface inside
access-group dmz_out in interface dmz
!
nat (inside,outside) source dynamic internal-net interface
!
route outside 0.0.0.0 0.0.0.0 203.0.113.254 1
route inside 10.0.0.0 255.255.0.0 10.0.1.254 1
!
logging host inside 10.0.1.100
logging trap informational
!
time-range business-hours
 periodic weekdays 08:00 to 18:00
```

## Extracted Output

### Interfaces / Zones
| Zone (nameif) | Interface | Security Level | IP |
|---|---|---|---|
| outside | GigabitEthernet0/0 | 0 | 203.0.113.1/24 |
| inside | GigabitEthernet0/1 | 100 | 10.0.1.1/24 |
| dmz | GigabitEthernet0/2 | 50 | 192.168.10.1/24 |

### Address Objects
| Name | Type | Value | IP Version |
|---|---|---|---|
| web-server | host | 192.168.10.10/32 | v4 |
| app-server | host | 192.168.10.20/32 | v4 |
| internal-net | subnet | 10.0.0.0/16 | v4 |
| partner-net | subnet | 172.16.0.0/12 | v4 |

### Address Groups
| Name | Members |
|---|---|
| dmz-servers | web-server, app-server |

### Service Objects
| Name | Protocol | Port |
|---|---|---|
| web-ports | tcp | 80, 443, 8080-8090 |

### Security Policies (from ACLs + Access Groups)

**From ACL: outside_in (in interface outside)**

**Policy 1:** (rule_index: 1)
- Zones: outside → any
- Source: any → Destination: web-server
- Protocol: tcp, Port: 443
- Action: allow | Log: yes
- Note: Source zone = outside (ingress interface)

**Policy 2:** (rule_index: 2)
- Zones: outside → any
- Source: any → Destination: web-server
- Protocol: tcp, Port: 8443
- Action: allow | Log: yes

**Policy 3:** (rule_index: 3)
- Zones: outside → any
- Source: any → Destination: any
- Protocol: ip (all)
- Action: deny | Log: yes

**From ACL: inside_out (in interface inside)**

**Policy 4:** (rule_index: 4)
- Zones: inside → any
- Source: internal-net → Destination: any
- Services: web-ports (tcp/80, 443, 8080-8090)
- Action: allow

**Policy 5:** (rule_index: 5)
- Zones: inside → any
- Source: internal-net → Destination: any
- Protocol: udp, Port: 53 (DNS)
- Action: allow

**Policy 6:** (rule_index: 6)
- Zones: inside → any
- Source: internal-net → Destination: any
- Protocol: tcp, Port: 53 (DNS)
- Action: allow

**Policy 7:** (rule_index: 7)
- Zones: inside → any
- Source: internal-net → Destination: any
- Protocol: icmp, Type: echo
- Action: allow

**Policy 8:** (rule_index: 8)
- Zones: inside → any
- Source: any → Destination: any
- Action: deny | Log: yes

**From ACL: dmz_out (in interface dmz)**

**Policy 9:** (rule_index: 9)
- Zones: dmz → any
- Source: dmz-servers → Destination: internal-net
- Protocol: tcp, Port: 3306 (MySQL)
- Action: allow

**Policy 10:** (rule_index: 10)
- Zones: dmz → any
- Source: any → Destination: any
- Action: deny

**Policy 11: Implicit: Default Deny** (rule_index: 11, _implicit: true)
- Zones: any → any | Action: deny

### NAT Rules
| Name | Type | Real Zone | Mapped Zone | Match | Translation |
|---|---|---|---|---|---|
| web-server (auto) | static | dmz | outside | 192.168.10.10 | 203.0.113.10 |
| internal-net (manual) | source | inside | outside | 10.0.0.0/16 | interface (PAT) |

### Static Routes
| Destination | Gateway | Interface | Metric |
|---|---|---|---|
| 0.0.0.0/0 | 203.0.113.254 | outside | 1 |
| 10.0.0.0/16 | 10.0.1.254 | inside | 1 |

### Schedules
| Name | Type | Days | Start | End |
|---|---|---|---|---|
| business-hours | recurring | weekdays | 08:00 | 18:00 |

### Syslog Config
| Destination | Interface |
|---|---|
| 10.0.1.100 | inside |

### Analysis Findings
- **Unused object:** `partner-net` is not referenced in any ACL
- **Unused schedule:** `business-hours` is defined but not referenced by any ACL entry
- **Unbound ACL:** None — all ACLs have access-group bindings
- **Mixed NAT:** Both object NAT (web-server) and manual NAT (internal-net) — review ordering
- **Missing logging:** Policies 4-7, 9 have no `log` keyword

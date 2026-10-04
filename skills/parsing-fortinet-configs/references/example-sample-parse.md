# FortiGate Config Parsing Example

## Contents

- [Input Config](#input-config)
- [Extracted Output](#extracted-output)

## Input Config

```
config system interface
    edit "port1"
        set vdom "root"
        set ip 10.0.1.1 255.255.255.0
        set type physical
        set alias "LAN"
        set allowaccess ping ssh https
    next
    edit "port2"
        set vdom "root"
        set ip 203.0.113.1 255.255.255.0
        set type physical
        set alias "WAN"
    next
    edit "port3"
        set vdom "root"
        set ip 192.168.10.1 255.255.255.0
        set type physical
        set alias "DMZ"
    next
end

config system zone
    edit "trust"
        set interface "port1"
        set intrazone allow
    next
    edit "untrust"
        set interface "port2"
        set intrazone deny
    next
end

config firewall address
    edit "web-server"
        set type ipmask
        set subnet 192.168.10.10 255.255.255.255
        set comment "DMZ web server"
        set associated-interface "port3"
    next
    edit "internal-net"
        set type ipmask
        set subnet 10.0.0.0 255.255.0.0
    next
    edit "partner-dns"
        set type fqdn
        set fqdn "dns.partner.com"
    next
end

config firewall addrgrp
    edit "dmz-servers"
        set member "web-server"
    next
end

config firewall service custom
    edit "custom-app"
        set protocol TCP/UDP/SCTP
        set tcp-portrange 8080-8090
    next
end

config firewall vip
    edit "web-vip"
        set extip 203.0.113.10
        set mappedip "192.168.10.10"
        set extintf "port2"
        set portforward enable
        set extport 443
        set mappedport 443
    next
end

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
        set utm-status enable
        set av-profile "default"
        set webfilter-profile "default"
        set ips-sensor "protect_client"
        set ssl-ssh-profile "certificate-inspection"
        set nat enable
    next
    edit 2
        set name "allow-inbound-web"
        set srcintf "untrust"
        set dstintf "port3"
        set srcaddr "all"
        set dstaddr "web-vip"
        set action accept
        set schedule "always"
        set service "HTTPS"
        set logtraffic all
        set logtraffic-start enable
        set utm-status enable
        set profile-group "strict-security"
    next
    edit 3
        set srcintf "trust"
        set dstintf "port3"
        set srcaddr "internal-net"
        set dstaddr "dmz-servers"
        set action accept
        set schedule "always"
        set service "SSH" "HTTPS" "custom-app"
        set logtraffic all
        set status disable
    next
end

config router static
    edit 1
        set dst 0.0.0.0 0.0.0.0
        set gateway 203.0.113.254
        set device "port2"
    next
end
```

## Extracted Output

### Zones
| Name | Interfaces | Intrazone |
|---|---|---|
| trust | port1 | allow |
| untrust | port2 | deny |
| port3 (auto) | port3 | — (no intrazone setting) |

Note: `port3` is used directly in policies but not part of any zone — auto-created as its own zone.

### Address Objects
| Name | Type | Value | IP Version |
|---|---|---|---|
| web-server | host | 192.168.10.10/32 | v4 |
| internal-net | subnet | 10.0.0.0/16 | v4 |
| partner-dns | fqdn | dns.partner.com | — |

### Address Groups
| Name | Members |
|---|---|
| dmz-servers | web-server |

### Service Objects
| Name | Protocol | Port |
|---|---|---|
| custom-app | tcp | 8080-8090 |

### VIP Objects (Destination NAT)
| Name | External IP | Mapped IP | Port Forward |
|---|---|---|---|
| web-vip | 203.0.113.10 | 192.168.10.10 | 443 → 443 |

### Security Policies

**Policy 1: allow-outbound-web** (rule_index: 1)
- Zones: trust → untrust
- Source: internal-net → Destination: all
- Services: HTTP, HTTPS
- Action: allow | Log: end (logtraffic all; no logtraffic-start)
- Profiles: virus=default, url-filtering=default, idp=protect_client, ssl-proxy=certificate-inspection
- NAT: source NAT enabled (policy-based)

**Policy 2: allow-inbound-web** (rule_index: 2)
- Zones: untrust → port3
- Source: all → Destination: web-vip (VIP: 203.0.113.10 → 192.168.10.10)
- Services: HTTPS
- Action: allow | Log: start + end (logtraffic all + logtraffic-start)
- Profile group: strict-security
- Warning: "Policy uses VIP for destination NAT — review NAT mapping"

**Policy 3: Policy-3** (rule_index: 3, no name set)
- Zones: trust → port3
- Source: internal-net → Destination: dmz-servers
- Services: SSH, HTTPS, custom-app
- Action: allow | Log: end (logtraffic all)
- **DISABLED** (status: disable)

**Policy 4: Implicit: Intra-zone Allow (trust)** (rule_index: 4, _implicit: true)
- Zones: trust → trust | Action: allow

**Policy 5: Implicit: Intra-zone Deny (untrust)** (rule_index: 5, _implicit: true)
- Zones: untrust → untrust | Action: deny

**Policy 6: Implicit: Default Deny** (rule_index: 6, _implicit: true)
- Zones: any → any | Action: deny

Note: no intra-zone rule is modeled for `port3` — it is an auto-zone from a raw interface reference, never declared in `config system zone`, so it has no intrazone setting.

### NAT Rules (from VIPs)
| Name | Type | External | Translated | Port |
|---|---|---|---|---|
| web-vip | destination | 203.0.113.10 | 192.168.10.10 | 443 → 443 |

### Static Routes
| Destination | Gateway | Interface |
|---|---|---|
| 0.0.0.0/0 | 203.0.113.254 | port2 |

### Analysis Findings
- **Unused object:** `partner-dns` is not referenced by any policy
- **Disabled policy:** Policy 3 is disabled — review if still needed
- **Auto-zone created:** `port3` used as interface-zone in policies 2 and 3
- **VIP in policy:** Policy 2 uses VIP `web-vip` for DNAT
- **Missing name:** Policy 3 has no `set name` — generated as "Policy-3"

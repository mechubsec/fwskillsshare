# parsing-cisco-configs evals

Run each scenario in a fresh agent session with the skill installed, then again without it as a baseline. A scenario passes only when every "Must" holds and no "Must not" occurs.

## Scenario 1: Parse basic ASA config with ACLs and objects

**Prompt:** Parse this Cisco ASA running-config and show me the intermediate schema

**Input:** Fixture: skills/parsing-cisco-configs/references/fixture-minimal-input.md

**Must:**
- Produces valid intermediate schema JSON
- Extracts interface nameifs and security-levels
- Converts address objects (host, subnet, range) to intermediate format
- Maps access-lists to security_policies with correct src/dst zones
- Converts subnet masks to CIDR notation

**Must not:**
- Errors on valid vendor syntax
- Emits secrets or credentials in the output
- Routes FortiOS or PAN-OS syntax to this parser

## Scenario 2: Handle NAT and object-group complexity

**Prompt:** Parse this ASA config focusing on NAT rules and object-groups

**Input:**
```
interface GigabitEthernet0/0
 nameif outside
 security-level 0
 ip address 203.0.113.1 255.255.255.0
!
interface GigabitEthernet0/1
 nameif inside
 security-level 100
 ip address 192.0.2.1 255.255.255.0
!
object network web-servers
 subnet 192.0.2.10 255.255.255.248
 nat (inside,outside) static 203.0.113.10
!
object-group network internal-nets
 network-object 192.0.2.0 255.255.255.0
 network-object 198.51.100.0 255.255.255.0
!
access-list outside_in extended permit tcp any object web-servers eq 443
access-group outside_in in interface outside
```

**Must:**
- Parses object-group network members correctly
- Extracts NAT statement from object network block
- Associates access-group with correct interface/zone binding
- Represents static NAT translation in nat_rules section

**Must not:**
- Lose NAT direction (inside,outside)
- Confuse object-group with object network

## Scenario 3: Reject unsupported vendor syntax without inventing behavior

**Prompt:** Parse this firewall config

**Input:**
```
config firewall policy
    edit 1
        set srcintf "port1"
        set dstintf "port2"
    next
end
```

**Must:**
- Recognizes FortiOS syntax (config/edit/next/end)
- Routes to parsing-fortinet-configs skill or refuses parsing
- Does not attempt to parse as Cisco ASA

**Must not:**
- Silently misparses FortiOS as ASA
- Invents intermediate schema from unrecognized syntax
- Claims successful parse of wrong-vendor config

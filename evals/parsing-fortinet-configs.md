# parsing-fortinet-configs evals

Run each scenario in a fresh agent session with the skill installed, then again without it as a baseline. A scenario passes only when every "Must" holds and no "Must not" occurs.

## Scenario 1: Parse FortiGate config with VDOMs

**Prompt:** Parse this FortiGate configuration and extract the firewall policy

**Input:**
```
config vdom
edit "root"
config firewall address
    edit "server-10.0.1.10"
        set subnet 10.0.1.10 255.255.255.255
    next
    edit "client-subnet"
        set subnet 192.0.2.0 255.255.255.0
    next
end
config firewall policy
    edit 1
        set srcintf "port1"
        set dstintf "port2"
        set srcaddr "client-subnet"
        set dstaddr "server-10.0.1.10"
        set action accept
        set service "HTTPS"
        set logtraffic all
    next
    edit 2
        set srcintf "port2"
        set dstintf "port1"
        set srcaddr "server-10.0.1.10"
        set dstaddr "client-subnet"
        set action accept
        set service "ALL"
        set logtraffic disable
    next
end
next
```

**Must:**
- Parses config/edit/next/end block structure
- Extracts VDOM context (root)
- Converts FortiGate address objects to intermediate schema
- Maps firewall policy to security_policies with correct action
- Preserves policy order via _rule_index
- Records logging state per rule

**Must not:**
- Loses VDOM boundary information
- Routes Cisco or PAN-OS syntax to this parser
- Emits secrets in the parsed output

## Scenario 2: Handle address groups and service objects

**Prompt:** Parse this FortiGate snippet with object groups

**Input:**
```
config firewall addrgrp
    edit "internal-networks"
        set member "net-192.0.2.0" "net-198.51.100.0"
    next
end
config firewall service custom
    edit "tcp-8443"
        set tcp-portrange 8443
        set protocol TCP
    next
end
```

**Must:**
- Parses addrgrp as address_groups with member references
- Parses service custom as service_objects
- Extracts TCP port range correctly
- Normalizes protocol name to uppercase or schema convention

**Must not:**
- Confuses addrgrp with firewall address
- Loses member references
- Invents values for unspecified fields

## Scenario 3: Enforce runtime intake on ambiguous input

**Prompt:** Parse this config and tell me if it's secure

**Input:**
```
config firewall policy
    edit 1
        set srcintf "any"
        set dstintf "any"
        set srcaddr "all"
        set dstaddr "all"
        set action accept
        set service "ALL"
    next
end
```

**Must:**
- Parses the policy correctly as any-any-any allow
- Does NOT claim the config is secure or approved
- May note the any-any rule as a hygiene concern
- Routes security assessment to firewall-best-practices-audit if asked

**Must not:**
- Recommends approval or commits changes
- Invents best-practice verdicts beyond parsing
- Surfaces runtime intake questions for a simple parse request

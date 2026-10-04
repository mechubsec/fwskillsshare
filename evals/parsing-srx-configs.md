# parsing-srx-configs evals

Run each scenario in a fresh agent session with the skill installed, then again without it as a baseline. A scenario passes only when every "Must" holds and no "Must not" occurs.

## Scenario 1: Parse SRX hierarchical config with zones and policies

**Prompt:** Parse this Juniper SRX configuration

**Input:**
```
security {
    zones {
        security-zone trust {
            interfaces {
                ge-0/0/0.0;
            }
        }
        security-zone untrust {
            interfaces {
                ge-0/0/1.0;
            }
        }
    }
    address-book {
        global {
            address server-192.0.2.10 192.0.2.10/32;
            address-set internal-servers {
                address server-192.0.2.10;
            }
        }
    }
    policies {
        from-zone trust to-zone untrust {
            policy allow-web {
                match {
                    source-address any;
                    destination-address any;
                    application junos-http;
                }
                then {
                    permit;
                    log {
                        session-init;
                    }
                }
            }
        }
    }
}
```

**Must:**
- Parses Junos hierarchical config (braces and semicolons)
- Extracts security zones with interface bindings
- Parses global address-book addresses and address-sets
- Converts from-zone/to-zone policy to security_policies
- Records junos-http as application match
- Preserves log session-init setting

**Must not:**
- Routes set-based config to hierarchical parser without flattening
- Loses from-zone to-zone context
- Confuses address-set with address

## Scenario 2: Parse set-based config and NAT

**Prompt:** Parse this SRX config in set format

**Input:**
```
set security zones security-zone untrust interfaces ge-0/0/1.0
set security zones security-zone trust interfaces ge-0/0/0.0
set security nat source rule-set trust-to-untrust from zone trust
set security nat source rule-set trust-to-untrust to zone untrust
set security nat source rule-set trust-to-untrust rule nat-out match source-address 192.0.2.0/24
set security nat source rule-set trust-to-untrust rule nat-out then source-nat interface
set security policies from-zone trust to-zone untrust policy allow-outbound match source-address any
set security policies from-zone trust to-zone untrust policy allow-outbound match destination-address any
set security policies from-zone trust to-zone untrust policy allow-outbound match application any
set security policies from-zone trust to-zone untrust policy allow-outbound then permit
```

**Must:**
- Parses set-based Junos syntax
- Reconstructs hierarchical structure from set commands
- Extracts source NAT rule-set with zone binding
- Records interface-based source-nat (PAT)
- Maps security policy with zone-pair context

**Must not:**
- Requires braced syntax when set format is provided
- Loses NAT rule-set zone bindings
- Treats source-nat interface as static translation

## Scenario 3: Enforce intermediate schema as canonical reference

**Prompt:** Parse this SRX config and convert it to FortiGate

**Input:**
```
security {
    policies {
        from-zone trust to-zone untrust {
            policy test {
                match {
                    source-address any;
                    destination-address any;
                    application any;
                }
                then {
                    permit;
                }
            }
        }
    }
}
```

**Must:**
- Parses the SRX config into intermediate schema
- Recognizes request for conversion
- Routes conversion task to firewall-config-conversion skill
- Does NOT re-implement FortiGate emission within this parser

**Must not:**
- Emits FortiGate config directly from parsing-srx-configs
- Bypasses intermediate schema for cross-vendor conversion
- Invents FortiGate syntax not documented in emit-fortinet.md

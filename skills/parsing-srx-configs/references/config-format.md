# SRX Configuration Format Reference

## Contents

- [Set Command Format](#set-command-format)
- [Hierarchical Format](#hierarchical-format)
- [Multi-Context](#multi-context)
- [Key Predefined Applications](#key-predefined-applications)

## Set Command Format

The most common format from `show configuration | display set`:

```
set <path> <value>
deactivate <path>
```

### Path Structure

```
set security zones security-zone <zone-name> interfaces <interface>
set security zones security-zone <zone-name> host-inbound-traffic system-services <service>
set security address-book global address <name> <type> <value>
set security address-book global address-set <name> address <member>
set applications application <name> protocol <proto>
set applications application <name> destination-port <port>
set applications application-set <name> application <member>
set security policies from-zone <src> to-zone <dst> policy <name> match source-address <addr>
set security policies from-zone <src> to-zone <dst> policy <name> match destination-address <addr>
set security policies from-zone <src> to-zone <dst> policy <name> match application <app>
set security policies from-zone <src> to-zone <dst> policy <name> then <action>
set security policies from-zone <src> to-zone <dst> policy <name> then permit application-services utm-policy <name>
set security policies from-zone <src> to-zone <dst> policy <name> then log session-init
set security policies from-zone <src> to-zone <dst> policy <name> then log session-close
set security policies global policy <name> match source-address <addr>
set security nat source rule-set <name> from zone <zone>
set security nat source rule-set <name> to zone <zone>
set security nat source rule-set <name> rule <name> match source-address <addr>
set security nat source rule-set <name> rule <name> then source-nat interface
set security nat destination rule-set <name> rule <name> then destination-nat pool <pool-name>
set security nat destination pool <name> address <ip/prefix>
set security nat static rule-set <name> rule <name> match destination-address <addr>
set security nat static rule-set <name> rule <name> then static-nat prefix <addr>
set routing-options static route <prefix> next-hop <ip>
set protocols bgp group <name> neighbor <ip> peer-as <asn>
set protocols ospf area <id> interface <iface>
set chassis cluster reth-count <n>
set chassis cluster redundancy-group <id> node <n> priority <p>
set security screen ids-option <name> tcp syn-flood alarm-threshold <n>
```

### Deactivate

Lines with `deactivate` prefix mark a config element as inactive (present but not enforced):
```
deactivate security policies from-zone trust to-zone untrust policy old-rule
```

### Quoted Values

Values with spaces or special characters are quoted:
```
set security policies from-zone trust to-zone untrust policy "Allow Web" match source-address any
set security address-book global address "My Server" 10.0.1.10/32
```

## Hierarchical Format

From `show configuration` (without `| display set`):

```
security {
    zones {
        security-zone trust {
            host-inbound-traffic {
                system-services {
                    ping;
                    ssh;
                }
            }
            interfaces {
                ge-0/0/0.0;
                ge-0/0/1.0;
            }
        }
    }
    address-book {
        global {
            address web-server 10.0.1.10/32;
            address-set web-servers {
                address web-server;
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
                    permit {
                        application-services {
                            utm-policy default-utm;
                        }
                    }
                    log {
                        session-close;
                    }
                }
            }
        }
    }
}
```

### Inactive Prefix

In hierarchical format, `inactive:` before a keyword marks it as deactivated:
```
inactive: policy old-rule { ... }
```

### Bracket Lists

Multiple values on one line use brackets:
```
interfaces [ ge-0/0/0.0 ge-0/0/1.0 ge-0/0/2.0 ];
```
Expand to: one set command per value.

## Multi-Context

### Logical Systems
```
set logical-systems LSYS1 security zones security-zone trust ...
set logical-systems LSYS1 security policies from-zone trust to-zone untrust policy ...
```
Parse each logical-system as an independent security context.

### Tenants
```
set tenants TENANT1 security policies from-zone trust to-zone untrust policy ...
```
Same pattern as logical-systems but under `tenants`.

## Key Predefined Applications

Partial list — the authoritative, live-verified table is in SKILL.md "Application Mapping (L7 → Canonical)".

SRX has predefined applications that don't need explicit definition:
- `junos-http` (TCP/80), `junos-https` (TCP/443)
- `junos-ssh` (TCP/22), `junos-telnet` (TCP/23)
- `junos-ftp` (TCP/21), `junos-dns-udp` (UDP/53), `junos-dns-tcp` (TCP/53)
- `junos-ping` (ICMP), `junos-icmp-all` (ICMP all types)
- `junos-smtp` (TCP/25), `junos-ntp` (UDP/123)
- `junos-syslog` (UDP/514) — note: there is no predefined `junos-snmp`; SNMP needs a custom application
- `junos-dhcp-client` (UDP/68), `junos-dhcp-server` (UDP/67)
- `any` — matches all applications

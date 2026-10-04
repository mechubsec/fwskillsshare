# PAN-OS Config Parsing Example

## Contents

- [Input Config (XML)](#input-config-xml)
- [Extracted Output](#extracted-output)

## Input Config (XML)

```xml
<config version="10.2.0">
  <devices>
    <entry name="localhost.localdomain">
      <vsys>
        <entry name="vsys1">
          <zone>
            <entry name="trust">
              <network><layer3><member>ethernet1/1</member></layer3></network>
            </entry>
            <entry name="untrust">
              <network><layer3><member>ethernet1/2</member></layer3></network>
            </entry>
            <entry name="dmz">
              <network><layer3><member>ethernet1/3</member></layer3></network>
            </entry>
          </zone>
          <address>
            <entry name="web-srv">
              <ip-netmask>10.0.1.10/32</ip-netmask>
              <description>Production web server</description>
              <tag><member>production</member></tag>
            </entry>
            <entry name="internal-net">
              <ip-netmask>10.0.0.0/16</ip-netmask>
            </entry>
            <entry name="partner-api">
              <fqdn>api.partner.com</fqdn>
            </entry>
          </address>
          <address-group>
            <entry name="dmz-servers">
              <static>
                <member>web-srv</member>
              </static>
            </entry>
          </address-group>
          <service>
            <entry name="svc-8443">
              <protocol><tcp><port>8443</port></tcp></protocol>
              <description>Custom HTTPS</description>
            </entry>
          </service>
          <rulebase>
            <security>
              <rules>
                <entry name="allow-outbound-web">
                  <from><member>trust</member></from>
                  <to><member>untrust</member></to>
                  <source><member>internal-net</member></source>
                  <destination><member>any</member></destination>
                  <application>
                    <member>web-browsing</member>
                    <member>ssl</member>
                  </application>
                  <service><member>application-default</member></service>
                  <action>allow</action>
                  <log-end>yes</log-end>
                  <profile-setting>
                    <group><member>best-practice</member></group>
                  </profile-setting>
                </entry>
                <entry name="allow-inbound-https">
                  <from><member>untrust</member></from>
                  <to><member>dmz</member></to>
                  <source><member>any</member></source>
                  <destination><member>web-srv</member></destination>
                  <application><member>ssl</member></application>
                  <service><member>application-default</member></service>
                  <action>allow</action>
                  <log-start>yes</log-start>
                  <log-end>yes</log-end>
                  <profile-setting>
                    <profiles>
                      <virus><member>default</member></virus>
                      <vulnerability><member>strict</member></vulnerability>
                    </profiles>
                  </profile-setting>
                </entry>
                <entry name="block-crypto">
                  <from><member>any</member></from>
                  <to><member>any</member></to>
                  <source><member>any</member></source>
                  <destination><member>any</member></destination>
                  <application><member>bitcoin</member><member>mining</member></application>
                  <service><member>any</member></service>
                  <action>deny</action>
                  <log-end>yes</log-end>
                </entry>
              </rules>
            </security>
            <nat>
              <rules>
                <entry name="outbound-pat">
                  <from><member>trust</member></from>
                  <to><member>untrust</member></to>
                  <source><member>internal-net</member></source>
                  <destination><member>any</member></destination>
                  <source-translation>
                    <dynamic-ip-and-port>
                      <interface-address>
                        <interface>ethernet1/2</interface>
                      </interface-address>
                    </dynamic-ip-and-port>
                  </source-translation>
                </entry>
              </rules>
            </nat>
          </rulebase>
        </entry>
      </vsys>
    </entry>
  </devices>
</config>
```

## Extracted Output

### Zones
| Name | Type | Interfaces |
|---|---|---|
| trust | layer3 | ethernet1/1 |
| untrust | layer3 | ethernet1/2 |
| dmz | layer3 | ethernet1/3 |

### Address Objects
| Name | Type | Value | IP Version | Tags |
|---|---|---|---|---|
| web-srv | host | 10.0.1.10/32 | v4 | production |
| internal-net | subnet | 10.0.0.0/16 | v4 | — |
| partner-api | fqdn | api.partner.com | — | — |

### Address Groups
| Name | Members |
|---|---|
| dmz-servers | web-srv |

### Service Objects
| Name | Protocol | Port |
|---|---|---|
| svc-8443 | tcp | 8443 |

### Security Policies

**Policy 1: allow-outbound-web** (rule_index: 1)
- Zones: trust → untrust
- Source: internal-net → Destination: any
- Applications (raw): web-browsing, ssl
- Apps (canonical): `{vendor_name: "web-browsing", canonical: "http", confidence: 1.0, category: "web"}`, `{vendor_name: "ssl", canonical: "https", confidence: 1.0, category: "web"}`
- Services: application-default
- Action: allow | Log: session-end
- Profile group: best-practice

**Policy 2: allow-inbound-https** (rule_index: 2)
- Zones: untrust → dmz
- Source: any → Destination: web-srv
- Applications (raw): ssl
- Apps (canonical): `{vendor_name: "ssl", canonical: "https", confidence: 1.0, category: "web"}`
- Services: application-default
- Action: allow | Log: session-start, session-end
- Security profiles (PAN-OS → schema key): virus → `virus`=default, vulnerability → `idp`=strict

**Policy 3: block-crypto** (rule_index: 3)
- Zones: any → any
- Source: any → Destination: any
- Applications (raw): bitcoin, mining
- Apps (canonical): `{vendor_name: "bitcoin", canonical: null, confidence: 0.0}`, `{vendor_name: "mining", canonical: null, confidence: 0.0}`
- Services: any
- Action: deny | Log: session-end
- Warning: "Applications 'bitcoin', 'mining' have no canonical mapping — preserved as raw vendor_name with confidence 0.0"

**Policy 4: Implicit: Intra-zone Allow (trust)** (rule_index: 4, _implicit: true)
- Zones: trust → trust | Action: allow

**Policy 5: Implicit: Intra-zone Allow (untrust)** (rule_index: 5, _implicit: true)
- Zones: untrust → untrust | Action: allow

**Policy 6: Implicit: Intra-zone Allow (dmz)** (rule_index: 6, _implicit: true)
- Zones: dmz → dmz | Action: allow

**Policy 7: Implicit: Interzone Default Deny** (rule_index: 7, _implicit: true)
- Zones: any → any | Action: deny

### NAT Rules
| Name | Type | Zones | Match Src | Translation |
|---|---|---|---|---|
| outbound-pat | source | trust → untrust | internal-net | interface (ethernet1/2) |

### Analysis Findings
- **Unused object:** `partner-api` is not referenced by any policy
- **Unused service:** `svc-8443` is not referenced by any policy
- **Unused group:** `dmz-servers` is not referenced by any policy
- **Unmapped applications:** `bitcoin`, `mining` — no canonical equivalent; preserved as raw `vendor_name` with `confidence: 0.0` for review during conversion

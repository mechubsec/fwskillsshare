# parsing-palo-configs evals

Run each scenario in a fresh agent session with the skill installed, then again without it as a baseline. A scenario passes only when every "Must" holds and no "Must not" occurs.

## Scenario 1: Parse PAN-OS XML config with zones and App-ID

**Prompt:** Parse this PAN-OS configuration and show the security policy

**Input:**
```xml
<config>
  <devices>
    <entry name="localhost.localdomain">
      <vsys>
        <entry name="vsys1">
          <zone>
            <entry name="trust">
              <network>
                <layer3>
                  <member>ethernet1/1</member>
                </layer3>
              </network>
            </entry>
            <entry name="untrust">
              <network>
                <layer3>
                  <member>ethernet1/2</member>
                </layer3>
              </network>
            </entry>
          </zone>
          <rulebase>
            <security>
              <rules>
                <entry name="allow-web">
                  <from>
                    <member>trust</member>
                  </from>
                  <to>
                    <member>untrust</member>
                  </to>
                  <source>
                    <member>any</member>
                  </source>
                  <destination>
                    <member>any</member>
                  </destination>
                  <application>
                    <member>web-browsing</member>
                    <member>ssl</member>
                  </application>
                  <action>allow</action>
                  <log-end>yes</log-end>
                </entry>
              </rules>
            </security>
          </rulebase>
        </entry>
      </vsys>
    </entry>
  </devices>
</config>
```

**Must:**
- Parses PAN-OS XML structure
- Extracts vsys boundary
- Maps zones to intermediate schema
- Converts security rule with application-based matching
- Records App-ID applications (web-browsing, ssl) in applications or dynamic_applications field
- Preserves log-end setting

**Must not:**
- Loses vsys context
- Routes set-based or hierarchical Junos syntax to this parser
- Treats App-ID as port-based service

## Scenario 2: Handle NAT and address objects

**Prompt:** Parse the NAT rules from this PAN-OS config

**Input:**
```xml
<config>
  <devices>
    <entry name="localhost.localdomain">
      <vsys>
        <entry name="vsys1">
          <address>
            <entry name="web-server">
              <ip-netmask>192.0.2.10/32</ip-netmask>
            </entry>
            <entry name="public-ip">
              <ip-netmask>203.0.113.10/32</ip-netmask>
            </entry>
          </address>
          <rulebase>
            <nat>
              <rules>
                <entry name="inbound-web">
                  <source-translation>
                    <dynamic-ip-and-port>
                      <interface-address>
                        <interface>ethernet1/2</interface>
                      </interface-address>
                    </dynamic-ip-and-port>
                  </source-translation>
                  <to>
                    <member>untrust</member>
                  </to>
                  <from>
                    <member>trust</member>
                  </from>
                  <destination>
                    <member>public-ip</member>
                  </destination>
                  <service>service-http</service>
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

**Must:**
- Parses address objects with ip-netmask
- Extracts NAT rule with source-translation
- Records dynamic-ip-and-port PAT configuration
- Maps destination zone and referenced address object

**Must not:**
- Confuses source-translation with destination-translation
- Loses interface-address binding
- Invents unsupported NAT types

## Scenario 3: Refuse set-based config routed incorrectly

**Prompt:** Parse this PAN-OS config

**Input:**
```
set deviceconfig system hostname firewall01
set network interface ethernet ethernet1/1 layer3 ip 192.0.2.1/24
set zone trust network layer3 ethernet1/1
```

**Must:**
- Recognizes set-based CLI format
- Either parses it (PAN-OS does support set commands) OR routes to XML-based parsing
- Produces valid intermediate schema if parsed

**Must not:**
- Routes Junos set security syntax to PAN-OS parser
- Silently drops set commands expecting only XML
- Confuses set network with Junos set security

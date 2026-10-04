# PAN-OS XML Configuration Format Reference

## Contents

- [XML Structure Overview](#xml-structure-overview)
- [Critical XML Patterns](#critical-xml-patterns)
- [Zone Definition](#zone-definition)
- [Address Object Types](#address-object-types)
- [Address Group Types](#address-group-types)
- [Service Definition](#service-definition)
- [Security Rule](#security-rule)
- [NAT Rule](#nat-rule)
- [HA Configuration](#ha-configuration)

## XML Structure Overview

PAN-OS configs are XML documents. The root element is `<config>`.

### Device-Level Config

```xml
<config version="10.2.0">
  <mgt-config>...</mgt-config>
  <shared>...</shared>
  <devices>
    <entry name="localhost.localdomain">
      <vsys>
        <entry name="vsys1">
          <zone>...</zone>
          <address>...</address>
          <address-group>...</address-group>
          <service>...</service>
          <service-group>...</service-group>
          <application>...</application>
          <application-group>...</application-group>
          <rulebase>
            <security>
              <rules>...</rules>
            </security>
            <nat>
              <rules>...</rules>
            </nat>
          </rulebase>
        </entry>
      </vsys>
      <network>...</network>
      <deviceconfig>...</deviceconfig>
    </entry>
  </devices>
</config>
```

### Panorama Config

```xml
<config>
  <devices>
    <entry name="localhost.localdomain">
      <device-group>
        <entry name="DG-Branch">
          <pre-rulebase>
            <security><rules>...</rules></security>
          </pre-rulebase>
          <post-rulebase>
            <security><rules>...</rules></security>
          </post-rulebase>
        </entry>
      </device-group>
    </entry>
  </devices>
  <shared>
    <address>...</address>
  </shared>
</config>
```

## Critical XML Patterns

### entry Elements

All named objects use `<entry name="...">`. Always treat as arrays:

```xml
<address>
  <entry name="web-srv">
    <ip-netmask>10.0.1.10/32</ip-netmask>
    <description>Web server</description>
    <tag>
      <member>production</member>
    </tag>
  </entry>
  <entry name="db-srv">
    <ip-netmask>10.0.2.10/32</ip-netmask>
  </entry>
</address>
```

### member Elements

List items in groups and rules. Always treat as arrays even when single:

```xml
<source>
  <member>any</member>
</source>
<destination>
  <member>web-srv</member>
  <member>db-srv</member>
</destination>
```

## Zone Definition

```xml
<zone>
  <entry name="trust">
    <network>
      <layer3>
        <member>ethernet1/1</member>
        <member>ethernet1/2</member>
      </layer3>
    </network>
  </entry>
  <entry name="untrust">
    <network>
      <layer3>
        <member>ethernet1/3</member>
      </layer3>
    </network>
  </entry>
</zone>
```

Zone types determined by child of `<network>`: `layer3`, `layer2`, `virtual-wire`, `tap`.

## Address Object Types

```xml
<!-- Host/Subnet -->
<entry name="web-srv">
  <ip-netmask>10.0.1.10/32</ip-netmask>
</entry>

<!-- Range -->
<entry name="dhcp-range">
  <ip-range>10.0.1.100-10.0.1.200</ip-range>
</entry>

<!-- FQDN -->
<entry name="google-dns">
  <fqdn>dns.google.com</fqdn>
</entry>

<!-- Wildcard (rarely supported) -->
<entry name="wildcard-10">
  <ip-wildcard>10.0.0.0/0.0.255.255</ip-wildcard>
</entry>
```

## Address Group Types

```xml
<!-- Static group -->
<entry name="web-servers">
  <static>
    <member>web-srv-1</member>
    <member>web-srv-2</member>
  </static>
</entry>

<!-- Dynamic group (tag-based) -->
<entry name="auto-tagged">
  <dynamic>
    <filter>'production' and 'web'</filter>
  </dynamic>
</entry>
```

## Service Definition

```xml
<entry name="custom-https">
  <protocol>
    <tcp>
      <port>8443</port>
      <source-port>1024-65535</source-port>
    </tcp>
  </protocol>
  <description>Custom HTTPS</description>
</entry>

<entry name="custom-dns">
  <protocol>
    <udp>
      <port>5353</port>
    </udp>
  </protocol>
</entry>
```

## Security Rule

```xml
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
  <service>
    <member>application-default</member>
  </service>
  <action>allow</action>
  <log-start>no</log-start>
  <log-end>yes</log-end>
  <disabled>no</disabled>
  <description>Allow outbound web</description>
  <negate-source>no</negate-source>
  <negate-destination>no</negate-destination>
  <tag>
    <member>outbound</member>
  </tag>
  <source-user>
    <member>any</member>
  </source-user>
  <profile-setting>
    <group>
      <member>best-practice</member>
    </group>
  </profile-setting>
</entry>
```

### Profile Setting Variants

**Group reference:**
```xml
<profile-setting>
  <group>
    <member>strict-security</member>
  </group>
</profile-setting>
```

**Individual profiles:**
```xml
<profile-setting>
  <profiles>
    <virus><member>default</member></virus>
    <spyware><member>strict</member></spyware>
    <vulnerability><member>strict</member></vulnerability>
    <url-filtering><member>strict</member></url-filtering>
    <file-blocking><member>strict</member></file-blocking>
    <wildfire-analysis><member>default</member></wildfire-analysis>
  </profiles>
</profile-setting>
```

## NAT Rule

```xml
<entry name="outbound-nat">
  <from>
    <member>trust</member>
  </from>
  <to>
    <member>untrust</member>
  </to>
  <source>
    <member>internal-net</member>
  </source>
  <destination>
    <member>any</member>
  </destination>
  <source-translation>
    <dynamic-ip-and-port>
      <interface-address>
        <interface>ethernet1/3</interface>
      </interface-address>
    </dynamic-ip-and-port>
  </source-translation>
</entry>
```

### Source Translation Types

```xml
<!-- Dynamic IP and Port (PAT) to interface -->
<source-translation>
  <dynamic-ip-and-port>
    <interface-address>
      <interface>ethernet1/3</interface>
    </interface-address>
  </dynamic-ip-and-port>
</source-translation>

<!-- Dynamic IP and Port to address pool -->
<source-translation>
  <dynamic-ip-and-port>
    <translated-address>
      <member>nat-pool</member>
    </translated-address>
  </dynamic-ip-and-port>
</source-translation>

<!-- Static IP -->
<source-translation>
  <static-ip>
    <translated-address>203.0.113.10/32</translated-address>
  </static-ip>
</source-translation>
```

### Destination Translation

```xml
<destination-translation>
  <translated-address>10.0.1.10</translated-address>
  <translated-port>443</translated-port>
</destination-translation>
```

## HA Configuration

```xml
<deviceconfig>
  <high-availability>
    <group>
      <entry name="1">
        <configuration-synchronization>
          <enabled>yes</enabled>
        </configuration-synchronization>
        <peer-ip>10.0.0.2</peer-ip>
        <mode>
          <active-passive>
            <passive-link-state>auto</passive-link-state>
          </active-passive>
        </mode>
        <election-option>
          <device-priority>100</device-priority>
          <preemptive>yes</preemptive>
        </election-option>
      </entry>
    </group>
  </high-availability>
</deviceconfig>
```

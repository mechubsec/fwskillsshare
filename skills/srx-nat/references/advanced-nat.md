# Advanced SRX NAT Patterns

## Contents

- [NAT64 with DNS64](#nat64-with-dns64)
- [CGN, PBA, and Persistent NAT](#cgn-pba-and-persistent-nat)
- [Address-Persistent Symptoms](#address-persistent-symptoms)

Use this reference for NAT64/DNS64, carrier-grade NAT, port block allocation, persistent NAT, and address-persistent troubleshooting.

## NAT64 with DNS64

DNS64 synthesizes an IPv6 AAAA record from an IPv4 A record. With the well-known prefix `64:ff9b::/96`, the last 32 bits encode the IPv4 destination. SRX NAT64 extracts those last 32 bits and translates the IPv6 destination to IPv4.

Process:

1. IPv6-only client queries a DNS64 resolver.
2. DNS64 returns an address under `64:ff9b::/96` with the IPv4 address embedded in the last 32 bits.
3. SRX static NAT64 matches the NAT64 prefix and uses `static-nat inet` to extract the IPv4 destination.
4. SRX source NAT translates the IPv6 client source to an IPv4 source.
5. Return traffic maps back through the SRX session.

Static NAT64 destination extraction:

```junos
set security nat static rule-set NAT64 from zone trust
set security nat static rule-set NAT64 rule NAT64 match source-address ::/0
set security nat static rule-set NAT64 rule NAT64 match destination-address 64:ff9b::/96
set security nat static rule-set NAT64 rule NAT64 then static-nat inet
```

Source NAT for NAT64:

```junos
set security nat source rule-set NAT64_SNAT from zone trust
set security nat source rule-set NAT64_SNAT to zone untrust
set security nat source rule-set NAT64_SNAT rule NAT64_SNAT match source-address ::/0
set security nat source rule-set NAT64_SNAT rule NAT64_SNAT match destination-address 0.0.0.0/0
set security nat source rule-set NAT64_SNAT rule NAT64_SNAT then source-nat interface
```

The `destination-address 0.0.0.0/0` is intentional. Static NAT64 has already translated the destination to IPv4 before source NAT rule evaluation. Matching `64:ff9b::/96` in the source NAT rule will not match the translated flow.

Verification:

```text
host www.juniper.net
ping www.juniper.net
curl -6 https://www.juniper.net
show security nat static rule all
show security nat source rule all
show security flow session destination-port 443 extensive
```

Expected session pattern:

```text
In:  <IPv6-client> --> 64:ff9b::<embedded-v4>/443
Out: <real-IPv4-destination>/443 --> <translated-IPv4-source>/<port>
```

NAT64 caveats:

- DNS64 is required for hostname-based access unless the client explicitly uses embedded NAT64 notation.
- Native IPv6 destinations should not be caught by the NAT64 source NAT rule.
- Per the Juniper NAT overview, NAT64 traffic is not processed on the PowerMode IPsec fast path. Verify current release and platform behavior.

## CGN, PBA, and Persistent NAT

Treat carrier-grade NAT as a capacity-managed service, not just a large source NAT pool.

### Port Block Allocation

PBA allocates blocks of ports to subscribers:

```junos
set security nat source pool POOL_1 address 1.2.84.0/24
set security nat source pool POOL_1 address 1.2.85.0/24
set security nat source pool POOL_1 address 1.2.86.0/24
set security nat source pool POOL_1 address 1.2.87.0/24
set security nat source pool POOL_1 port block-allocation block-size 1280
set security nat source pool POOL_1 port block-allocation maximum-blocks-per-host 3
set security nat source pool POOL_1 port block-allocation last-block-recycle-timeout 300
set security nat source pool POOL_1 address-pooling paired
```

Guidance:

- `address-pooling paired` keeps a subscriber paired with the same NAT pool address and overrides global hash-based `address-persistent` behavior.
- `last-block-recycle-timeout` prevents the final allocated block from remaining allocated forever after the subscriber has no sessions.
- Start with realistic subscriber and session telemetry. Do not blindly copy lab block sizes.
- Active/active chassis cluster behavior can reserve port ranges and reduce usable ports per public IP; size from observed platform behavior.

### Selective Persistent NAT

Source-NAT pools translate ports by default. `set security nat source pool <name> port no-translation` preserves original source ports and needs enough pool addresses. `port-overloading-factor <n>` increases port capacity per pool IP at the cost of shared-port ambiguity.

Persistent NAT helps selected gaming, STUN, and peer-to-peer flows but consumes extra state. Put specific persistent rules before broad normal NAT rules:

```junos
set security nat source rule-set LAN_TO_WAN from zone LAN
set security nat source rule-set LAN_TO_WAN to zone WAN
set security nat source rule-set LAN_TO_WAN rule LAN_WAN_PNAT_1 match source-address 100.64.0.0/10
set security nat source rule-set LAN_TO_WAN rule LAN_WAN_PNAT_1 match destination-address 0.0.0.0/0
set security nat source rule-set LAN_TO_WAN rule LAN_WAN_PNAT_1 match application GAMING_CONSOLES_TUNED
set security nat source rule-set LAN_TO_WAN rule LAN_WAN_PNAT_1 then source-nat pool POOL_1
set security nat source rule-set LAN_TO_WAN rule LAN_WAN_PNAT_1 then source-nat pool persistent-nat permit any-remote-host
set security nat source rule-set LAN_TO_WAN rule LAN_WAN_NAT_1 match source-address 100.64.0.0/10
set security nat source rule-set LAN_TO_WAN rule LAN_WAN_NAT_1 match destination-address 0.0.0.0/0
set security nat source rule-set LAN_TO_WAN rule LAN_WAN_NAT_1 then source-nat pool POOL_1
```

Optional hardening:

```junos
set security nat source rule-set LAN_TO_WAN rule LAN_WAN_PNAT_1 then source-nat pool persistent-nat block-ext-session
```

`block-ext-session` is a valid `persistent-nat` sibling knob verified on vSRX 24.4R1. It requires `persistent-nat permit ...` on the same rule.

## Address-Persistent Symptoms

`address-persistent` keeps translated source mapping stable for a source IP. It can help protocols that require stable NAT mapping but can also cause speed-test failures, intermittent website element failures, or VPN failures through NAT.

If persistence is not required, remove the global setting:

```text
delete security nat source address-persistent
```

Global `address-persistent` lives at `[edit security nat source]`; pool-level persistence is `pool <name> address-persistent subscriber ...`.

If failures relate to tunnel or WAN MTU, validate path MTU before changing TCP MSS:

```junos
set security flow tcp-mss all-tcp mss 1350
```

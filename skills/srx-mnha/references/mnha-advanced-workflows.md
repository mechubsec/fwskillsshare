# SRX MNHA Advanced Workflows

## Contents

- [Chassis-Cluster Interface Migration](#chassis-cluster-interface-migration)
- [IPsec with Multiple Routing Instances](#ipsec-with-multiple-routing-instances)
- [NAT and Deterministic Routing](#nat-and-deterministic-routing)
- [Runtime and Configuration Synchronization](#runtime-and-configuration-synchronization)
- [Hybrid Routing with Signal Routes](#hybrid-routing-with-signal-routes)
- [DHCP on MNHA](#dhcp-on-mnha)

Use this reference for chassis-cluster migration, MNHA IPsec, deterministic NAT, state and configuration synchronization, hybrid routing, and DHCP. Load only the relevant section.

## Chassis-Cluster Interface Migration

A chassis-cluster `reth` has child links contributed by each node. MNHA has no cluster-wide `reth`; convert each node's members into node-local physical interfaces or a node-local `ae` bundle.

- Decide between a local LAG and a single physical link from the upstream design, not from the source config alone.
- A cluster `reth` with LACP does not prove that the upstream is a true LAG toward either standalone node.
- Confirm upstream LAG configuration before recreating `ae` and LACP. A single physical link loses aggregation and local link redundancy; a local `ae` requires an upstream LAG to that node.

Example:

```junos
# Source chassis-cluster children
# set interfaces ge-0/0/4 gigether-options redundant-parent reth1
# set interfaces ge-7/0/4 gigether-options redundant-parent reth1
# set interfaces reth1 redundant-ether-options lacp active

# MNHA node0, only when the upstream is a real LAG to node0
set interfaces ae1 aggregated-ether-options lacp active
set interfaces xe-0/0/4 ether-options 802.3ad ae1
set interfaces ae1 unit 0 family inet address <NODE0_IP>/<PLEN>

# Single-physical alternative
# set interfaces xe-0/0/4 unit 0 family inet address <NODE0_IP>/<PLEN>
```

Repeat independently on node1. Interface names, members, and addresses are node-specific and must not be blindly synchronized.

## IPsec with Multiple Routing Instances

Align the SRG, floating loopback, physical underlay, security zone, routing instance, and route advertisement so the active node and table receive IKE and ESP.

Requirements:

- Use SRG1 or higher for synchronized IPsec.
- Install and validate the newer IKE package when required by release and platform:

  ```text
  request system software add optional://junos-ike.tgz
  show system processes | match "iked|ikemd|kmd"
  ```

- Mark IPsec as a managed service:

  ```junos
  set chassis high-availability services-redundancy-group <SRG> managed-services ipsec
  ```

- Anchor the VPN endpoint on a floating loopback present on both nodes and tracked by the SRG prefix list.
- Set the IKE gateway `external-interface` to the loopback and set its `local-address`.
- Treat `process-packet-on-backup` as optional behavior to validate, not a cure for bad path design.

Floating-loopback pattern:

```junos
set interfaces lo0 unit <UNIT> family inet address <FLOATING_VPN_IP>/32
set policy-options prefix-list <IKE_GW_PREFIX_LIST> <FLOATING_VPN_IP>/32
set chassis high-availability services-redundancy-group <SRG> prefix-list <IKE_GW_PREFIX_LIST> routing-instance <RI>
set chassis high-availability services-redundancy-group <SRG> managed-services ipsec
set security ike gateway <GW> external-interface lo0.<UNIT>
set security ike gateway <GW> local-address <FLOATING_VPN_IP>
```

Routing-instance and zone rules:

- A loopback unit belongs to one security zone and one routing instance.
- Put the IKE loopback and physical IKE/ESP receiving interface in the same zone.
- Add intra-zone policy when traffic arrives on the physical interface and is rerouted to the loopback anchor.
- Align the ICL MNHA routing-instance context with the floating loopback routing instance. Imported transit routes may not satisfy control-plane IKE gateway lookup.
- Use route leaking for transit or `st0` reachability only after validating the control-plane anchor independently.

```junos
set security policies from-zone <EXT_ZONE> to-zone <EXT_ZONE> policy ALLOW-IKE-ESP match source-address <REMOTE_PEER>
set security policies from-zone <EXT_ZONE> to-zone <EXT_ZONE> policy ALLOW-IKE-ESP match destination-address <FLOATING_VPN_IP>
set security policies from-zone <EXT_ZONE> to-zone <EXT_ZONE> policy ALLOW-IKE-ESP match application junos-ike
set security policies from-zone <EXT_ZONE> to-zone <EXT_ZONE> policy ALLOW-IKE-ESP match application <ESP_APPLICATION>
set security policies from-zone <EXT_ZONE> to-zone <EXT_ZONE> policy ALLOW-IKE-ESP then permit
```

Define `<ESP_APPLICATION>` as a custom IP protocol 50 application or use a release-validated predefined application; bare `ESP` is not a Junos built-in.

Typical alignment failures:

```text
'external-interface'(lo0.<UNIT>) and 'routing-interface'(<PHY_IFL>) belong to different zones
Re-route failed, pkt dropped
unable to make the tunnel ready
Gateway lookup failed
```

Remote-access notes:

- IKEv1 aggressive-mode sessions are not synchronized; clients must reconnect after failover.
- Verify certificates on both nodes after ICL cold sync.
- Configure node-local source addresses, routes, secrets, and reachability for RADIUS and other control-plane dependencies.
- Use a common pool for one SRG or separate ranges per active/active SRG to prevent collisions.
- Treat `st0` counters as node-local.

```text
show security ike security-associations
show security ike security-associations srg-id <SRG>
show network-access address-assignment pool <POOL>
show interfaces st0.<UNIT> | match packets
```

Site-to-site notes:

- `st0` can live in another routing instance only with explicit, verified route import and export.
- Confirm where traffic-selector ARI routes install before writing policy.
- Steer floating-IP ingress toward the active node and the routing instance aligned with the ICL and loopback anchor.

```text
show security ike security-associations srg-id <SRG>
show security ipsec security-associations
show security flow session tunnel
show route table <PROTECTED_RI>.inet.0 <REMOTE_TS_PREFIX>
show route table <VPN_RI>.inet.0 <LOCAL_PROTECTED_PREFIX>
```

## NAT and Deterministic Routing

Keep NAT policy and pools equivalent where stateful failover is expected, but prevent both independent control planes from answering for one translated address at L2.

- Prefer routed next-hop reachability to SNAT pools over proxy ARP.
- Avoid shared pools across ISPs unless return routing and prefix advertisements are deterministic.
- Unique per-ISP pools avoid ambiguity but break active sessions when failover changes the translated range.
- Use `to interface <IFL>` only when pool, egress interface, and route advertisement align.
- Validate RPF and reverse-route lookup before NAT.
- Point upstream routes for shared SNAT prefixes at a deliberate routed VIP or node interface.

```text
show security nat source rule all
show security nat source pool all
show route table <RI>.inet.0 <SNAT_POOL_PREFIX>
show route table <RI>.inet.0 0.0.0.0/0 exact
show security packet-drop records | match "MNHA|IP spoofing|reroute|proxy|FLOW"
```

`Dropped by FLOW:error info in MNHA flow meta header` indicates a likely cross-node flow whose NAT or proxy-ARP return traffic landed on the wrong node.

## Runtime and Configuration Synchronization

MNHA synchronizes supported runtime state, not an entire logical chassis. Expect Active/Warm copies for firewall sessions, NAT translations, IPsec SAs, and other supported runtime objects.

```text
show security flow session destination-prefix <PREFIX>
show security flow session source-prefix <PREFIX>
show security flow session | match "Session ID|HA State|HA Wing State|In:|Out:"
```

Keep shared policy, NAT, zones, and forwarding paths equivalent for stateful failover. Prefer symmetric routing; use ICD only when asymmetric-flow support is planned and tested. Confirm state appears on both nodes before declaring readiness.

Keep these node-specific:

- hostnames and management addresses
- interface addresses
- routing neighbors, local addresses, and intentionally different policies
- node-local monitoring targets

Keep these equivalent where synchronized services depend on them:

- security policies, address books, applications, and profiles
- NAT policy structure
- IPsec definitions
- shared SRG logic adjusted for local and peer IDs

Use Junos groups and peer synchronization, automation, Security Director where supported, and config-diff checks. The full peer-sync stanza is in `references/mnha-config-patterns.md`. Never put real secrets in skill files, tickets, or chat.

## Hybrid Routing with Signal Routes

Use SRG1+ to control VIP ownership and active/backup signal routes, then condition routing export policy on the signal route present on each node.

```junos
set chassis high-availability services-redundancy-group <SRG> active-signal-route 169.254.200.1
set chassis high-availability services-redundancy-group <SRG> backup-signal-route 169.254.200.2
set policy-options condition ACTIVE_SRG1 if-route-exists address-family inet 169.254.200.1/32
set policy-options condition ACTIVE_SRG1 if-route-exists address-family inet table inet.0
set policy-options condition BACKUP_SRG1 if-route-exists address-family inet 169.254.200.2/32
set policy-options condition BACKUP_SRG1 if-route-exists address-family inet table inet.0
```

Use non-production signal prefixes. Match the condition table to the table where Junos installs the signal route. Route-filter every export term; never export all direct routes accidentally. Full BGP and OSPF export examples are in `references/mnha-config-patterns.md`.

For OSPF, advertise the protected passive-loopback prefix from both nodes with active and backup metrics gated by the corresponding signal route. Confirm the active route is preferred and the higher-cost backup remains installed.

Use BFD only with timers validated on the platform and path:

```junos
set protocols bgp group <GROUP> bfd-liveness-detection minimum-interval <MS>
set protocols bgp group <GROUP> bfd-liveness-detection minimum-receive-interval <MS>
set protocols bgp group <GROUP> bfd-liveness-detection multiplier <COUNT>
```

```text
show bfd session
show bgp summary
show route <PROTECTED_PREFIX>
show route <PROTECTED_PREFIX> advertising-protocol bgp <NEIGHBOR>
```

Test preemption and failback with routing convergence, not only SRG state. If a VIP becomes the advertised next hop, validate multihop or upstream static routing.

VIP pattern:

```junos
set chassis high-availability services-redundancy-group <SRG> virtual-ip 1 ip <VIP>/<PREFIXLEN>
set chassis high-availability services-redundancy-group <SRG> virtual-ip 1 interface <INTERFACE.UNIT>
```

Confirm the VIP is installed only on the active node and adjacent devices accept the ARP and MAC move after failover.

## DHCP on MNHA

Prefer relay to an external DHCP service when continuity matters. Local DHCP lease databases are not assumed to synchronize.

```junos
set routing-instances <RI> forwarding-options dhcp-relay server-group DHCP-SERVERS <DHCP_SERVER_IP>
set routing-instances <RI> forwarding-options dhcp-relay group RELAY-GROUP active-server-group DHCP-SERVERS
set routing-instances <RI> forwarding-options dhcp-relay group RELAY-GROUP interface <CLIENT_INTERFACE>
```

If local DHCP is required:

- Run a separate DHCP process on each node.
- Use non-overlapping split pools and mirrored reservations.
- Use each node's client-facing IP as server identifier.
- Use the VIP as the router option where clients need the floating gateway.
- Exclude infrastructure addresses and align lease times with failure behavior.
- Permit `host-inbound-traffic system-services dhcp`.

The local-server example is in `references/mnha-config-patterns.md`.

```text
show dhcp server binding routing-instance <RI>
show dhcp server statistics routing-instance <RI>
show chassis high-availability services-redundancy-group <SRG>
```

Run `clear dhcp server binding routing-instance <RI> all` only in an approved maintenance procedure.

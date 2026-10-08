# MNHA Configuration Stage Reference

## Contents

- [Introduction](#introduction)
- [Placeholder Mapping](#placeholder-mapping)
- [Stage 1: Underlay (ICL + Data Segments)](#stage-1-underlay-icl--data-segments)
- [Stage 2: HA Stanza](#stage-2-ha-stanza)
- [Stage 3: eBGP + Signal-Route Export](#stage-3-ebgp--signal-route-export)
- [Undo Files](#undo-files)
- [Pre-Push Checklist](#pre-push-checklist)
- [Config Model Resolution Logic](#config-model-resolution-logic)

## Introduction

After filling the pair sheet, the agent writes each node's stage files by substituting `<PLACEHOLDER>` values from the pair sheet and baseline facts into the blocks below. Each staged set file must contain no Jinja syntax or unfilled placeholders when pushed to devices.

Stages are applied in order: Stage 1 (underlay), Stage 2 (HA stanza), Stage 3 (eBGP). Each stage references configuration from earlier stages.

## Placeholder Mapping

| Placeholder | Pair Sheet Field | Notes |
|-------------|------------------|-------|
| `<ICL_TRANSPORT>` | `pair.icl.transport` | `dedicated` or `shared` |
| `<ICL_ZONE>` | `pair.icl.zone` | New zone for ICL, e.g. `ICL` |
| `<ICL_IFD>` | `pair.icl.ifd` (dedicated) or `lo0` (shared) | Physical interface or loopback |
| `<ICL_UNIT>` | `pair.icl.unit` (dedicated) or `pair.icl.loopback_unit` (shared) | Unit number |
| `<ICL_IFL>` | `<ICL_IFD>.<ICL_UNIT>` | Full interface name |
| `<ICL_CIDR>` | `nodes.nodeN.icl_ip/<prefix_len>` (dedicated) or `/32` (shared) | ICL address with mask |
| `<LOCAL_ICL_IP>` | `nodes.nodeN.icl_ip` | This node's ICL IP |
| `<PEER_ICL_IP>` | Other node's `icl_ip` | Peer node's ICL IP |
| `<ICL_PEER_NEXTHOP>` | Peer's segment address IP (shared ICL only) | Next-hop to reach peer loopback |
| `<ICL_TRANSPORT_ZONE>` | Zone of `pair.icl.segment` (shared ICL only) | Transport segment's zone |
| `<ICL_TRANSPORT_NET>` | Segment CIDR (shared ICL only) | Transport segment subnet |
| `<ICL_LO_UNIT>` | `pair.icl.loopback_unit` (shared ICL only) | Loopback unit, e.g. `1` |
| `<ICL_HA_IFL>` | `<ICL_IFL>` (dedicated) or transport segment IFL (shared) | Interface for HA |
| `<ICL_ENCRYPTED>` | `pair.icl.encryption.enabled` | `true` or `false` |
| `<ICL_IKE_POLICY>` | `pair.icl.encryption.ike_policy` | IKE policy name, e.g. `MNHA-ICL-IKE-POL` |
| `<SEGMENT_NAME>` | `pair.segments[].name` | Segment identifier |
| `<SEGMENT_IFD>` | Interface part of `pair.segments[].ifl` | Before the `.` |
| `<SEGMENT_UNIT>` | Unit part of `pair.segments[].ifl` | After the `.` |
| `<SEGMENT_IFL>` | `pair.segments[].ifl` | Full interface name |
| `<SEGMENT_CIDR>` | `nodes.nodeN.addresses.<SEGMENT_NAME>` | Address with mask for this segment |
| `<SEGMENT_ZONE>` | `pair.segments[].zone` | Zone name |
| `<SEGMENT_ROLE>` | `pair.segments[].role` | `upstream`, `downstream`, etc. |
| `<LOCAL_ID>` | `1` (node0) or `2` (node1) | MNHA local-id |
| `<PEER_ID>` | `2` (node0) or `1` (node1) | MNHA peer-id |
| `<LIVENESS_MIN>` | `pair.liveness.min_interval` | Milliseconds |
| `<LIVENESS_MULT>` | `pair.liveness.multiplier` | Multiplier value |
| `<DEPLOYMENT_TYPE>` | `pair.deployment_mode` | `routing`, `switching`, or `hybrid` |
| `<PROBE_DST>` | `nodes.nodeN.probe.dest_ip` | Probe destination (optional) |
| `<PROBE_SRC>` | `nodes.nodeN.probe.src_ip` | Probe source (optional) |
| `<ACTIVENESS_PRIORITY>` | `nodes.nodeN.activeness_priority` | Priority value, e.g. `200` or `100` |
| `<ACTIVE_SIGNAL_ROUTE>` | `pair.srg1.active_signal_route` | Signal route IP, e.g. `169.254.200.1` |
| `<BACKUP_SIGNAL_ROUTE>` | `pair.srg1.backup_signal_route` | Signal route IP, e.g. `169.254.200.2` |
| `<VIP_ID>` | `pair.srg1.vips[].id` | VIP identifier number |
| `<VIP_IP>` | `pair.srg1.vips[].ip` | VIP address with mask |
| `<VIP_IFL>` | `pair.srg1.vips[].ifl` | Interface for VIP |
| `<MONITOR_IFD>` | `pair.srg1.monitor_interfaces[]` | Physical interface to monitor |
| `<PREEMPTION>` | `pair.srg1.preemption` | `true` or `false` |
| `<CONFIG_MODEL>` | `pair.config_model`, default `flat` | `flat` (default) or `grid` (optional four-node-style syntax) |
| `<GRID_ID>` | `pair.grid_id` | Optional grid-id 1-15 for VMAC/VIP scale; omit when `0`/unset |
| `<LOCAL_AS>` | `pair.bgp.local_as` | Local AS number |
| `<PEER_AS>` | `pair.bgp.peer_as` | Peer AS number |
| `<BGP_GROUP>` | `pair.bgp.group` | BGP group name, e.g. `UPSTREAM` |
| `<EXPORT_POLICY>` | `pair.bgp.export_policy` | Export policy name, e.g. `MNHA-SRG1-EXPORT` |
| `<PROTECTED_PREFIX>` | `pair.bgp.protected_prefixes[]` | Prefix with match type, e.g. `198.51.100.0/24 exact` |
| `<TRANSIT_SUBNET>` | `pair.bgp.transit_subnets[]` | Transit subnet, e.g. `203.0.113.0/24` |
| `<ACTIVE_METRIC>` | `pair.bgp.active_metric` | MED for active node, e.g. `10` |
| `<BACKUP_METRIC>` | `pair.bgp.backup_metric` | MED for backup node, e.g. `20` |
| `<BGP_NEIGHBOR>` | `nodes.nodeN.bgp_neighbors[]` | Neighbor IP address |
| `<UPSTREAM_IP>` | IP part of this node's upstream segment CIDR | Local address on upstream segment |
| `<BGP_BFD_MIN>` | `pair.bgp.bfd.min_interval` | BFD interval (if BFD enabled) |
| `<BGP_BFD_MULT>` | `pair.bgp.bfd.multiplier` | BFD multiplier (if BFD enabled) |
| `<COND_ACTIVE>` | `MNHA-SRG1-ACTIVE` | Condition name for active state |
| `<COND_BACKUP>` | `MNHA-SRG1-BACKUP` | Condition name for backup state |

## Stage 1: Underlay (ICL + Data Segments)

Include only when ICL transport is **dedicated**:

```junos
set interfaces <ICL_IFD> unit <ICL_UNIT> family inet address <ICL_CIDR>
set security zones security-zone <ICL_ZONE> interfaces <ICL_IFL>
```

Include only when ICL transport is **shared**:

```junos
set interfaces lo0 unit <ICL_LO_UNIT> family inet address <LOCAL_ICL_IP>/32
set security zones security-zone <ICL_ZONE> interfaces lo0.<ICL_LO_UNIT>
set routing-options static route <PEER_ICL_IP>/32 next-hop <ICL_PEER_NEXTHOP>
set security zones security-zone <ICL_TRANSPORT_ZONE> host-inbound-traffic system-services high-availability
set security zones security-zone <ICL_TRANSPORT_ZONE> host-inbound-traffic protocols bfd
```

Include only when ICL transport is **shared** and **encrypted**:

```junos
set security zones security-zone <ICL_TRANSPORT_ZONE> host-inbound-traffic system-services ike
```

Always include (ICL zone host-inbound rules):

```junos
set security zones security-zone <ICL_ZONE> host-inbound-traffic system-services high-availability
set security zones security-zone <ICL_ZONE> host-inbound-traffic system-services ping
set security zones security-zone <ICL_ZONE> host-inbound-traffic protocols bfd
```

Include only when ICL is **encrypted**:

```junos
set security zones security-zone <ICL_ZONE> host-inbound-traffic system-services ike
```

For each segment in `pair.segments`:

```junos
set interfaces <SEGMENT_IFD> unit <SEGMENT_UNIT> family inet address <SEGMENT_CIDR>
set security zones security-zone <SEGMENT_ZONE> interfaces <SEGMENT_IFL>
set security zones security-zone <SEGMENT_ZONE> host-inbound-traffic system-services ping
```

Include only when segment role is **upstream** and mode is **routing or hybrid**:

```junos
set security zones security-zone <SEGMENT_ZONE> host-inbound-traffic protocols bgp
```

Include only when segment role is **upstream**, mode is **routing or hybrid**, and `pair.bgp.bfd` is set:

```junos
set security zones security-zone <SEGMENT_ZONE> host-inbound-traffic protocols bfd
```

## Stage 2: HA Stanza

### ICL Encryption Block (include only when `<ICL_ENCRYPTED>` is true)

**Optional.** An unencrypted ICL is acceptable when the ICL is local (direct link or same site); encryption is recommended when the ICL traverses other networks. Juniper's overview says "As the ICL link transmits private data, it is important to encrypt the link. You must encrypt the ICL using IPsec VPN." (MNHA overview, Interchassis link encryption); the operator treats it as a recommendation, and an unencrypted ICL formed and synced (`Encrypted: NO`) in the lab on vSRX 24.4R1.9 and 26.2R1.7. When `<ICL_ENCRYPTED>` is false, skip this block and every `vpn-profile` line.

**Prerequisite: not available on default vSRX.** lab-verified (commit check, 2026-10-08): on vSRX 26.2R1.7 and 24.4R1.9 in default non-FIPS mode, `ha-link-encryption` fails with `'ha-link-encryption' can be configure only in FIPS mode`; without it, `peer-id <P> vpn-profile` fails with `Referenced vpn object must have ha-link-encryption flag defined` and the IKE gateway with `IKEv2 requires bind-interface configuration as only route-based is supported`. FIPS mode and the junos-ike package were not tested (enabling FIPS mode zeroizes the config). Before offering encryption, confirm the platform and FIPS/IKE-package state; on a vSRX in default mode treat encryption as unavailable and build an unencrypted ICL (`<ICL_ENCRYPTED>` false).

**Gateway addressing.** Juniper's Layer 3 example ([mnha-configuration-example](https://www.juniper.net/documentation/us/en/software/junos/high-availability/topics/example/mnha-configuration-example.html)) defines `MNHA_IKE_GW` with only `ike-policy` and `version v2-only`, with no `address`, `local-address` or `external-interface`; this block mirrors it. The block is not meant to be committed alone: it is referenced by `vpn-profile` in the HA stanza below, and the ICL peer addresses come from `local-ip`/`peer-ip` there. If the device's dry run asks for gateway addressing, add `set security ike gateway MNHA-ICL-IKE-GW local-address <LOCAL_ICL_IP>`, `address <PEER_ICL_IP>` and `external-interface <ICL_IFL>` (standard IKE gateway statements; untestable on non-FIPS vSRX, so not confirmed); the PSK is still set by the user.

**Note:** The IKE policy's pre-shared key must be set by the user on each node via CLI before the baseline is taken. It never passes through the pair sheet, chat, or MCP.

```junos
set security ike proposal MNHA-ICL-IKE-PROP authentication-method pre-shared-keys
set security ike proposal MNHA-ICL-IKE-PROP dh-group group20
set security ike proposal MNHA-ICL-IKE-PROP encryption-algorithm aes-256-gcm
set security ike proposal MNHA-ICL-IKE-PROP lifetime-seconds 28800
set security ike policy <ICL_IKE_POLICY> proposals MNHA-ICL-IKE-PROP
set security ike gateway MNHA-ICL-IKE-GW ike-policy <ICL_IKE_POLICY>
set security ike gateway MNHA-ICL-IKE-GW version v2-only
set security ipsec proposal MNHA-ICL-IPSEC-PROP protocol esp
set security ipsec proposal MNHA-ICL-IPSEC-PROP encryption-algorithm aes-256-gcm
set security ipsec proposal MNHA-ICL-IPSEC-PROP lifetime-seconds 3600
set security ipsec policy MNHA-ICL-IPSEC-POL perfect-forward-secrecy keys group20
set security ipsec policy MNHA-ICL-IPSEC-POL proposals MNHA-ICL-IPSEC-PROP
set security ipsec vpn MNHA-ICL-VPN ha-link-encryption
set security ipsec vpn MNHA-ICL-VPN ike gateway MNHA-ICL-IKE-GW
set security ipsec vpn MNHA-ICL-VPN ike ipsec-policy MNHA-ICL-IPSEC-POL
```

### Flat Model (default; 24.x and 26.2R1.7)

Include when `<CONFIG_MODEL>` is `flat` (the default). Lab-verified on vSRX 26.2R1.7, 2026-10-08: the flat form commits and, after the HA-activation reboot, activates. Before that reboot, `show chassis high-availability information` says `mode not configured` on any release.

Optional VMAC/VIP-scale tuning (Juniper: `grid-id` 1-15, 25.4R1; coexists with `local-id`/`peer-id`), include only when `<GRID_ID>` is set:

```junos
set chassis high-availability grid-id <GRID_ID>
```

Core ICL lines:

```junos
set chassis high-availability local-id <LOCAL_ID> local-ip <LOCAL_ICL_IP>
set chassis high-availability peer-id <PEER_ID> peer-ip <PEER_ICL_IP>
set chassis high-availability peer-id <PEER_ID> interface <ICL_HA_IFL>
set chassis high-availability peer-id <PEER_ID> liveness-detection minimum-interval <LIVENESS_MIN>
set chassis high-availability peer-id <PEER_ID> liveness-detection multiplier <LIVENESS_MULT>
```

Include only when **flat model** and **encrypted ICL**:

```junos
set chassis high-availability peer-id <PEER_ID> vpn-profile MNHA-ICL-VPN
```

Flat model SRG0 and SRG1 peer-id:

```junos
set chassis high-availability services-redundancy-group 0 peer-id <PEER_ID>
set chassis high-availability services-redundancy-group 1 peer-id <PEER_ID>
```

### Four-Node-Style Syntax (`config_model: grid`, optional, not required)

Include only when the user explicitly sets `<CONFIG_MODEL>` to `grid`. `local-domain-id`, `domain-size` and `peer-domain-id` are documented by Juniper for four-node MNHA; this shape also committed on a two-node vSRX 26.2R1.7 pair (unencrypted) but is not needed for two nodes.

**Note:** `vpn-profile` placement under `peer-domain-id` is NOT field-confirmed — rely on the device dry run.

```junos
set chassis high-availability grid-id <GRID_ID>
set chassis high-availability local-id <LOCAL_ID> local-ip <LOCAL_ICL_IP>
set chassis high-availability local-domain-id <LOCAL_ID> domain-size 1
set chassis high-availability peer-domain-id <PEER_ID> domain-size 1
set chassis high-availability peer-domain-id <PEER_ID> peer-id <PEER_ID> local-ip <LOCAL_ICL_IP>
set chassis high-availability peer-domain-id <PEER_ID> peer-id <PEER_ID> peer-ip <PEER_ICL_IP>
set chassis high-availability peer-domain-id <PEER_ID> peer-id <PEER_ID> interface <ICL_HA_IFL>
set chassis high-availability peer-domain-id <PEER_ID> peer-id <PEER_ID> liveness-detection minimum-interval <LIVENESS_MIN> multiplier <LIVENESS_MULT>
```

Include only when **grid model** and **encrypted ICL**:

```junos
set chassis high-availability peer-domain-id <PEER_ID> peer-id <PEER_ID> vpn-profile MNHA-ICL-VPN
```

Grid model SRG0 and SRG1 peer-domain-id:

```junos
set chassis high-availability services-redundancy-group 0 peer-domain-id <PEER_ID> peer-id <PEER_ID>
set chassis high-availability services-redundancy-group 1 peer-domain-id <PEER_ID> peer-id <PEER_ID>
```

### SRG1 Common Block (both flat and grid models)

Always include:

```junos
set chassis high-availability services-redundancy-group 1 deployment-type <DEPLOYMENT_TYPE>
```

Include only when `<PROBE_DST>` is set:

```junos
set chassis high-availability services-redundancy-group 1 activeness-probe dest-ip <PROBE_DST> src-ip <PROBE_SRC>
```

Always include:

```junos
set chassis high-availability services-redundancy-group 1 activeness-priority <ACTIVENESS_PRIORITY>
```

Include only when mode is **routing or hybrid** (bgp_enabled):

```junos
set chassis high-availability services-redundancy-group 1 active-signal-route <ACTIVE_SIGNAL_ROUTE>
set chassis high-availability services-redundancy-group 1 backup-signal-route <BACKUP_SIGNAL_ROUTE>
```

For each VIP in `pair.srg1.vips`:

```junos
set chassis high-availability services-redundancy-group 1 virtual-ip <VIP_ID> ip <VIP_IP>
set chassis high-availability services-redundancy-group 1 virtual-ip <VIP_ID> interface <VIP_IFL>
```

Include whenever `pair.srg1.monitor_interfaces` is non-empty, **regardless of `config_model`**, unless the user explicitly asked for the monitor-object form below (the two blocks are mutually exclusive; the pair sheet has no field for the form, so the simple form is the default and the monitor-object form is only on an explicit request):

For each interface in `monitor_interfaces`:

```junos
set chassis high-availability services-redundancy-group 1 monitor interface <MONITOR_IFD>
```

Include instead of the simple form only when `pair.srg1.monitor_interfaces` is non-empty and the user **explicitly asked** for the monitor-object form (both forms commit-check on vSRX 26.2R1.7):

For each interface in `monitor_interfaces`:

```junos
set chassis high-availability services-redundancy-group 1 monitor monitor-object UPLINKS interface interface-name <MONITOR_IFD> weight 100
```

Then:

```junos
set chassis high-availability services-redundancy-group 1 monitor monitor-object UPLINKS interface threshold 100
set chassis high-availability services-redundancy-group 1 monitor monitor-object UPLINKS object-threshold 100
set chassis high-availability services-redundancy-group 1 monitor srg-threshold 100
```

Include only when `<PREEMPTION>` is true:

```junos
set chassis high-availability services-redundancy-group 1 preemption
```

## Stage 3: eBGP + Signal-Route Export

Include only in **routing and hybrid modes**.

```junos
set routing-options autonomous-system <LOCAL_AS>
set policy-options condition <COND_ACTIVE> if-route-exists address-family inet <ACTIVE_SIGNAL_ROUTE>/32
set policy-options condition <COND_ACTIVE> if-route-exists address-family inet table inet.0
set policy-options condition <COND_BACKUP> if-route-exists address-family inet <BACKUP_SIGNAL_ROUTE>/32
set policy-options condition <COND_BACKUP> if-route-exists address-family inet table inet.0
```

For each prefix in `pair.bgp.protected_prefixes`:

```junos
set policy-options policy-statement <EXPORT_POLICY> term active from route-filter <PROTECTED_PREFIX>
set policy-options policy-statement <EXPORT_POLICY> term backup from route-filter <PROTECTED_PREFIX>
```

Then:

```junos
set policy-options policy-statement <EXPORT_POLICY> term active from condition <COND_ACTIVE>
set policy-options policy-statement <EXPORT_POLICY> term active then metric <ACTIVE_METRIC>
set policy-options policy-statement <EXPORT_POLICY> term active then accept
set policy-options policy-statement <EXPORT_POLICY> term backup from condition <COND_BACKUP>
set policy-options policy-statement <EXPORT_POLICY> term backup then metric <BACKUP_METRIC>
set policy-options policy-statement <EXPORT_POLICY> term backup then accept
```

Include only when `pair.bgp.transit_subnets` is non-empty:

For each subnet in `pair.bgp.transit_subnets`:

```junos
set policy-options policy-statement <EXPORT_POLICY> term transit-active from route-filter <TRANSIT_SUBNET> exact
set policy-options policy-statement <EXPORT_POLICY> term transit-backup from route-filter <TRANSIT_SUBNET> exact
```

Then:

```junos
set policy-options policy-statement <EXPORT_POLICY> term transit-active from protocol direct
set policy-options policy-statement <EXPORT_POLICY> term transit-active from condition <COND_ACTIVE>
set policy-options policy-statement <EXPORT_POLICY> term transit-active then metric <ACTIVE_METRIC>
set policy-options policy-statement <EXPORT_POLICY> term transit-active then accept
set policy-options policy-statement <EXPORT_POLICY> term transit-backup from protocol direct
set policy-options policy-statement <EXPORT_POLICY> term transit-backup from condition <COND_BACKUP>
set policy-options policy-statement <EXPORT_POLICY> term transit-backup then metric <BACKUP_METRIC>
set policy-options policy-statement <EXPORT_POLICY> term transit-backup then accept
```

Always include (default term):

```junos
set policy-options policy-statement <EXPORT_POLICY> term default then reject
set protocols bgp group <BGP_GROUP> type external
set protocols bgp group <BGP_GROUP> local-address <UPSTREAM_IP>
set protocols bgp group <BGP_GROUP> peer-as <PEER_AS>
```

For each neighbor in `nodes.nodeN.bgp_neighbors`:

```junos
set protocols bgp group <BGP_GROUP> neighbor <BGP_NEIGHBOR>
```

Include only when `pair.bgp.bfd` is set:

```junos
set protocols bgp group <BGP_GROUP> bfd-liveness-detection minimum-interval <BGP_BFD_MIN>
set protocols bgp group <BGP_GROUP> bfd-liveness-detection multiplier <BGP_BFD_MULT>
```

Always include:

```junos
set protocols bgp group <BGP_GROUP> export <EXPORT_POLICY>
```

## Undo Files

Undo files delete only what their corresponding stage **adds** relative to the baseline. Pre-existing configuration that a stage merely re-states (reused interfaces, zones, BGP groups) is never removed by an undo.

Write undo files in **reverse stage order** (undo-stage3, undo-stage2, undo-stage1) when rolling back.

### Undo Algorithm

For each line in the stage file (in reverse order):
1. Extract the configuration hierarchy path (everything after `set`)
2. Find the shortest prefix that does not exist in the baseline
3. Write `delete <prefix>` to the undo file
4. Skip the line if it already existed in the baseline

### Example

Given baseline:

```junos
set interfaces ge-0/0/1 unit 0 family inet address 203.0.113.2/24
set security zones security-zone untrust interfaces ge-0/0/1.0
```

And stage1 adds:

```junos
set interfaces ge-0/0/1 unit 0 family inet address 203.0.113.2/24
set interfaces ge-0/0/2 unit 0 family inet address 192.168.100.1/30
set security zones security-zone ICL interfaces ge-0/0/2.0
```

The undo-stage1 would be:

```junos
delete security zones security-zone ICL
delete interfaces ge-0/0/2 unit 0
```

Note: `ge-0/0/1.0` is not deleted because it pre-existed in the baseline.

## Pre-Push Checklist

Walk this checklist after writing all stage files. Any **Blocking** item means stop — do not push. **Needs Acknowledgment** items require a one-line user OK before proceeding.

### Blocking (must fix before pushing)

#### Pair Sheet and Model Resolution
- [ ] Deployment mode is `routing`, `switching`, or `hybrid` (not something else)
- [ ] All required fields are filled (no `<FILL>` remains in the pair sheet)
- [ ] `config_model` is `flat` unless the user explicitly asked for the four-node-style syntax; the flat form is valid on 26.x (a 26.x `mode not configured` before reboot is the missing HA-activation reboot, not a wrong model)
- [ ] If `grid_id` is set, it is 1-15 and unique per MNHA pair sharing an L2 domain (Juniper)
- [ ] Junos release string parses correctly (format: `NN.NxRN.N`)

#### ICL Configuration
- [ ] ICL IPs are not identical on both nodes
- [ ] If ICL transport is **dedicated**: both ICL IPs are in the same subnet
- [ ] If ICL transport is **shared**: neither node's ICL loopback IP sits inside the transport segment's subnet
- [ ] Activeness priorities are not equal on both nodes
- [ ] If ICL transport is **dedicated** and the ICL interface exists in baseline: it has no other configuration (no other units, addresses, or zone assignments)
- [ ] If ICL transport is **dedicated** and the ICL interface is in a zone in baseline: the zone name matches `pair.icl.zone` (or is not present at all)
- [ ] If ICL transport is **shared** and `lo0.<loopback_unit>` exists in baseline: it has the correct `/32` address (not another address)
- [ ] If ICL transport is **shared** and `lo0.<loopback_unit>` is in a zone in baseline: the zone name matches `pair.icl.zone`
- [ ] ICL zone does not already exist in baseline (unless it's the reused zone from above)
- [ ] If ICL is encrypted: platform supports it (not a default-mode vSRX: `ha-link-encryption` is rejected outside FIPS mode, lab-verified 2026-10-08). If it does not: **STOP** and ask the user to either explicitly accept an unencrypted ICL (fine when the ICL is local) or choose a supported alternative (FIPS-mode platform or a different platform), then regenerate the stages. Never set `encryption.enabled: false` on your own
- [ ] If ICL is encrypted: the PSK is set in baseline on `security ike policy <ike_policy>` **on both nodes** (user sets this via CLI, then retakes baseline)
- [ ] If ICL is encrypted: existing crypto objects (`ike proposal MNHA-ICL-IKE-PROP`, `ike policy <ike_policy>`, `ike gateway MNHA-ICL-IKE-GW`, `ipsec proposal MNHA-ICL-IPSEC-PROP`, `ipsec policy MNHA-ICL-IPSEC-POL`, `ipsec vpn MNHA-ICL-VPN`) in baseline match the rendered ones exactly (except the PSK line)
- [ ] Rendered Stage 1 includes `host-inbound-traffic protocols bfd` on the ICL zone (see srx-mnha pitfall 22)
- [ ] If ICL is encrypted: rendered Stage 1 includes `host-inbound-traffic system-services ike` on the ICL zone

#### Probe Configuration
- [ ] If probe is set: both `dest_ip` and `src_ip` are filled (not just one)
- [ ] If probe is set: probe addresses are not on the ICL subnet (use a data segment)
- [ ] If deployment mode is **routing**: activeness-probe `dest_ip` and `src_ip` are set on **both nodes** (see srx-mnha pitfall 20)
- [ ] If deployment mode is **routing**: rendered Stage 2 includes `activeness-probe dest-ip` (see srx-mnha pitfall 20)

#### Mode-Specific Rules
- [ ] If deployment mode is **switching**: SRG1 has `virtual-ip` index 1 and 2 on unique interfaces. Lab-observed commit requirement on vSRX 26.2R1.7 (2026-10-08); not documented by Juniper in the pages reviewed. **Block** on 26.2R1.7; on other releases **warn only** ("may be required; commit check will tell") and let the dry run decide. Not applied to hybrid (untested)
- [ ] If deployment mode is **routing**: no VIPs are defined (use hybrid or switching for VIPs)
- [ ] If deployment mode is **switching or hybrid**: at least one VIP is defined
- [ ] For each VIP: its IFL is a declared segment
- [ ] For each VIP: the VIP address is in the same subnet as **both nodes'** addresses on that segment
- [ ] For each VIP: the VIP address does not equal either node's own address on that segment
- [ ] If deployment mode is **routing or hybrid**: exactly one segment has `role: upstream`
- [ ] If deployment mode is **routing or hybrid**: `pair.bgp.protected_prefixes` is not empty
- [ ] For each protected prefix: it includes a route-filter match type (e.g. `exact`, `orlonger`, `upto`)
- [ ] If deployment mode is **routing or hybrid**: `local_as` ≠ `peer_as` (this builder does eBGP only)
- [ ] If deployment mode is **routing or hybrid**: each node has at least one `bgp_neighbors` entry
- [ ] For each BGP export term in rendered Stage 3: the term accepts only if it also has a `route-filter` match (see srx-mnha pitfall 5)
- [ ] Signal routes (active and backup) are distinct (not identical)

#### Data Segment Configuration
- [ ] For each segment in baseline: if the segment interface exists with an address, that address matches the pair sheet
- [ ] For each segment in baseline: if the segment interface is in a zone, that zone name matches the pair sheet

#### BGP Configuration (routing and hybrid modes only)
- [ ] If baseline has `autonomous-system`: it matches `pair.bgp.local_as`
- [ ] If baseline has BGP group `<bgp_group>` with `peer-as`: it matches `pair.bgp.peer_as`
- [ ] If baseline has BGP group `<bgp_group>` with `export`: no other policies are exported (or remove those policies, or pick another group name)
- [ ] Export policy `<export_policy>` does not already exist in baseline

#### Baseline Prerequisites
- [ ] Baseline has no `chassis cluster` configuration
- [ ] Baseline has no existing `chassis high-availability` configuration (remove it and reboot before starting)
- [ ] `fxp0` is not on DHCP (see srx-mnha pitfall 23)
- [ ] If baseline has `managed-services ipsec`: **ERROR** out of scope

#### Rendered Stage Safety
- [ ] No stage line touches `interfaces fxp0`, `system services`, `system login`, `system root-authentication`, or `routing-instances mgmt_junos`
- [ ] No stage line includes `host-inbound-traffic system-services all`, `host-inbound-traffic protocols all`, or `default-policy permit-all`

### Needs User Acknowledgment (get one-line OK before pushing)

- [ ] If `config_model` is `grid` (four-node-style): confirm the user wants it; the flat form is the default and sufficient for two nodes
- [ ] If ICL transport is **shared** (or the ICL traverses other networks) and not encrypted: session state crosses a shared segment in clear text
- [ ] If deployment mode is **switching or hybrid** and no `monitor_interfaces`: VIP will not move on uplink loss
- [ ] If deployment mode is **switching or hybrid** and no activeness-probe: consider adding one to avoid dual-active on ICL loss (see srx-mnha pitfall 8)
- [ ] If `pair.bgp.transit_subnets` is empty (in routing/hybrid mode): return traffic to on-transit sources may black-hole (see srx-mnha pitfall 21)
- [ ] For each transit subnet also in `protected_prefixes`: the transit term is redundant
- [ ] For each BGP neighbor not on the upstream segment subnet: multihop is not built (may fail to establish)
- [ ] If signal routes are outside `169.254.0.0/16`: non-standard range
- [ ] If `preemption` is enabled: test failback convergence carefully (see srx-mnha pitfall 8)
- [ ] If baseline has a static default route: verify next-hop is on a zoned interface (see srx-mnha pitfall 18) and that it should win over BGP
- [ ] If baseline has node-local IPsec (not `MNHA-ICL-*` objects): it is untouched and will NOT fail over (out of scope)

### Tell the User (informational, no gate)

- [ ] If ICL transport is **shared**: HA/BFD (and IKE if encrypted) host-inbound is opened on the transport zone
- [ ] If ICL is **encrypted**: both nodes need the `junos-ike` package (`show version` for "JUNOS ike") and the same PSK set by the user on the IKE policy before the baseline is taken
- [ ] If ICL interface or data segment interface/zone already exists in baseline with matching config: it is reused (not replaced)
- [ ] If deployment mode is **switching or hybrid**: failover visibility is understood: without `use-virtual-mac` the ARP mapping changes to the new active node's physical MAC via gratuitous ARP (neighbors must accept GARP; check stale ARP caches, DAI); with `use-virtual-mac` a virtual MAC moves between switch ports (check MAC-move limits, port-security, DAI, storm-control)
- [ ] If baseline has `default-policy permit-all` or zone with `host-inbound 'all'`: noted (broad permissions present)
- [ ] If no baseline was provided: baseline checks are skipped; undo files will delete every staged line (no distinction between new and reused config)

## Config Model Resolution Logic

1. Use `pair.config_model`; if `auto` or unset, resolve to `flat` on every release (24.x and 26.2R1.7 are lab-verified).
2. Use `grid` only when the user explicitly asks for the four-node-style syntax.
3. `pair.grid_id` is independent of the model: when set (1-15), emit `set chassis high-availability grid-id <GRID_ID>` with the flat stanza.

Use the resolved model to select the Stage 2 HA stanza block.

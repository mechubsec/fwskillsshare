# srx-chassis-cluster-proxmox evals

Run each scenario in a fresh agent session with the skill installed, then again without it as a baseline. A scenario passes only when every "Must" holds and no "Must not" occurs.

## Scenario 1: Anti-spoof silent blackhole

**Prompt:** My chassis cluster shows both nodes primary/secondary, all reths UP, but no traffic passes. `bridge fdb show` on Proxmox returns empty for the reth virtual MAC.

**Input:**
```
show chassis cluster status:
Node                 ID    Status     Redundancy group
node0                0     Primary    0: primary, 1: primary
node1                1     Secondary  0: secondary, 1: secondary

show chassis cluster interfaces:
Control link name: fxp1
Control link status: Up
Fabric link name: fab0 / fab1
Fabric status: fab0: Up / Up, fab1: Up / Up
Redundant-ethernet: reth0 Up

qm config VMID shows:
net1: model=virtio,bridge=vmbr6,tag=101,firewall=1
```

**Must:**
- Identify per-NIC firewall (`firewall=1`) as the anti-spoof trap
- Explain that reth virtual MAC never matches assigned NIC MAC, so anti-spoof discards every frame
- State this is the single easiest way to break a cluster
- Recommend checking `qm config VMID | grep -c 'firewall=1'` and ensuring it returns 0
- Reference references/failure-modes.md anti-spoof signature

**Must not:**
- Suggest the cluster formation is broken (status shows healthy; this is a hypervisor filtering issue)
- Recommend changing reth configuration (the hypervisor is silently dropping frames)
- Claim logs will show the discard (anti-spoof is silent)

## Scenario 2: Fabric MTU undersized but healthy

**Prompt:** My cluster shows all Up, fabric probes both directions, reths Up, no alarms. Is the fabric MTU validated?

**Input:**
```
show chassis cluster status: all healthy
show chassis cluster statistics: heartbeats incrementing, zero errors
show interfaces fab0: MTU 9014 / 9000 (Junos provisioned values)
ip -d link show vmbr6 | head -2: mtu 1500
```

**Must:**
- State that device-side health checks do NOT detect an undersized fabric segment
- Explain that Junos provisions fab0 to MTU 9000; the segment itself must support it
- Identify the 1500-byte bridge as the gap
- Note this failure is latent (cluster passes every row in validation table but cannot carry jumbo frames)
- Reference "Before you start" question 1 and references/proxmox-network-invariants.md

**Must not:**
- State the cluster is broken (it genuinely is healthy at 1500-byte MTU for non-jumbo traffic)
- Claim fabric probes moving proves MTU support (probes are small)
- Recommend verifying MTU after the cluster is built (this must be checked BEFORE, per the skill)

## Scenario 3: DHCP fxp0 after cluster reboot

**Prompt:** I rebooted both nodes into cluster mode. Neither is reachable on fxp0 despite the control link being Up. Console shows no management address.

**Input:**
```
Pre-reboot standalone config had:
set interfaces fxp0 unit 0 family inet dhcp

Post-reboot cluster status:
show chassis cluster status: one primary, one secondary, control link Up
show interfaces fxp0: no address shown
```

**Must:**
- State that a chassis cluster cannot manage fxp0 with DHCP
- Explain that fxp0 addressing must be static per node under groups
- Provide the groups pattern from Phase 4 config
- Note that the cluster itself forms normally; this looks like boot failure but is only addressing
- Warn that recovering without console requires planning fxp0 groups config before the reboot

**Must not:**
- Suggest the cluster formation failed (control link Up proves it formed correctly)
- Recommend re-enabling DHCP (not supported in cluster mode per the skill)
- Claim this is a Junos bug (it's expected behavior; fxp0 needs static addressing under groups)

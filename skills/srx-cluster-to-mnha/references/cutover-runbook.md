# Cutover runbook

Companion to [output-format.md](output-format.md). Template for moving a live
two-node chassis cluster to two-node MNHA with the generated `node0.set` and
`node1.set`. Fill the `<PLACEHOLDER>` values from the values table; leave any
the user has not supplied.

**Execution boundary.** This skill never executes any step. The operator runs
the runbook, or hands the node configs to `srx-mnha-builder` and works through
its approval gates. `srx-mnha-builder` refuses `managed-services ipsec`, so the
IPsec-SRG block (T14) is applied by the operator in Phase 5. Every
reboot, commit, and failover below needs explicit approval at that step.

Conventions: node A is the node left running the cluster while node B is
converted. This template converts node1 first (as B), then node0. Swap names if
the user chose the other order.

## Phase 0 - Pre-checks

- Maintenance window agreed; outage risk accepted (a cutover with a single
  active path has no redundancy while one node is converted).
- **Console access to both nodes** that does not depend on the revenue network
  (serial or terminal server; for a vSRX, the hypervisor console). SSH over
  fxp0 or reth is lost across reboots.
- Junos release and platform match the confirmed verdict; IKE package
  installed if ICL encryption is chosen (E5, E6).
- Cluster healthy:
  `show chassis cluster status`, `show chassis cluster interfaces`,
  `show chassis cluster information`.
- Baselines saved to files off the box: `show security flow session summary`,
  `show route summary`, `show route protocol <PROTO>` for each routing
  protocol, `show arp no-resolve`, `show security ike security-associations`,
  `show security ipsec security-associations`, `show interfaces reth<N> terse`.
- **A verified rollback method is required before Phase 1.** Management
  tooling may ignore `| save`, and a rescue save may be unverifiable through it
  or return redacted copies (L12). On a hypervisor, the lab option is a
  snapshot of both guests (check the guest's tags first; snapshot, never
  destroy or restore without separate approval). Record which method is the
  real rollback and test that it can be read back.
- Backups, on **both** nodes (rescue save is per routing engine; reach node1
  with `request routing-engine login node 1`):
  `request system configuration rescue save`, then confirm with
  `show system configuration rescue`.
  Also save two copies of the configuration and copy them off the device:
  set format `show configuration | display set | save <CLUSTER_BACKUP_SET>`
  (restore with `delete` then `load set <CLUSTER_BACKUP_SET>`) and text format
  `show configuration | save <CLUSTER_BACKUP_FILE>` (restore with
  `load override <CLUSTER_BACKUP_FILE>`). Uncertain: `load override` with a
  set-format file is not documented in vendor-evidence.md, so never use it for
  rollback.
- VPN outage window: the IPsec-SRG block (T14) is operator-applied. It is
  applied on node1 in Phase 2, before traffic moves. If the reviewed block is
  not ready by then, state the VPN outage (Phase 3 until the block is applied)
  to the user and stakeholders now.
- Physical/virtual plan ready for the ICL path between nodes (routed, E4) and
  for removing control and fabric cabling (T10, T11).
- Upstream/downstream owners notified: routing neighbors must accept the new
  per-node peering (T3, T17); switches must tolerate the VIP moving between
  ports (T2).
- Address bindings: the cluster's reth MAC is virtual
  (`00:10:db:ff:<cluster-id><rg>`), while the lab VIP answered with the active
  node's physical MAC (L10). DHCP reservations, ARP pins, static neighbor entries
  and port-security entries tied to the old reth MAC go stale; list them and the
  addresses on shared LANs, and have the owner update them (and the IPAM record)
  in the window.
- **vSRX port names change** (L1): on vSRX the post-disable names are
  `ge-0/0/(N+1)` and the former control NIC is `ge-0/0/0`. Record each guest
  NIC's MAC and its current Junos name now (hypervisor config plus
  `show interfaces <if> | match "Hardware address"`) for the MAC-map check in
  Phase 2. For a physical SRX the renumbering is uncertain: the operator states
  the post-disable names.

Verify: both nodes `primary`/`secondary`, no RG in `ineligible` or
`disabled`, baselines captured, `show system configuration rescue` shows a
rescue configuration on each node.

> **Rollback box, phase 0:** nothing changed. Abort and discard files.

## Phase 1 - Fail all RGs to node0 and isolate node1

- If an RG's primary is on node1, move it to node0 first. If node0 already owns
  every RG, skip the moves and just confirm. Per RG:
  `request chassis cluster failover redundancy-group <RG> node 0`, then
  `request chassis cluster failover reset redundancy-group <RG>` to clear
  the manual-failover flag.
- Confirm node0 is primary for all RGs and traffic flows.
- Isolate node1 from the revenue network: shut or disable node1's reth child
  ports at the upstream and downstream switches (not on the SRX). Keep
  control, fabric, and console connected for now.

Verify: `show chassis cluster status` (all RGs primary on node0),
`show chassis cluster interfaces`, session count and routes unchanged from the
Phase 0 baseline, no traffic arriving on node1.

> **Rollback box, phase 1:** re-enable node1's child ports at the switches;
> `request chassis cluster failover reset redundancy-group <RG>` if needed. No
> device configuration changed.

## Phase 2 - Node1 leaves the cluster; load MNHA config; bring up ICL

- Cable or bring up the routed ICL path between the nodes' ICL interfaces
  (E4); node0 is not yet MNHA, so only node1 needs the path now. Normally the
  ICL uses ports separate from fab and control, which stay cabled until Phase 4.
  If the interview chose to reuse the fab NIC as the ICL, that NIC leaves the
  fabric role here: node0 loses its fabric peer, so do this only after Phase 1
  is stable. The former control NIC (vSRX: `ge-0/0/0` after disable, L1) is a
  candidate second ICL link.
- On node1 console: `set chassis cluster disable reboot` (operational
  command, E11). Console is needed here: node1 is the first node to leave while
  its peer is still in the cluster, and the host-name and fxp0 groups are shared
  configuration, so they cannot be pre-staged for node1 alone (L4).
- After the reboot the groups no longer apply (L4): the node has lost its
  host-name and fxp0 address. From the console, in configuration mode:
  `delete apply-groups`, `set system host-name <NODE1_HOSTNAME>`,
  `set interfaces fxp0 unit 0 family inet address <NODE1_FXP0_ADDR>/<PLEN>`,
  `commit`. This is recovery, not a surprise.
- **STOP - MAC map before load (L1).** For each revenue and ICL NIC, compare
  the MAC `show interfaces <if> | match "Hardware address"` reports with the
  hypervisor NIC MAC captured in Phase 0. If any generated interface name is not
  the name that carries the intended MAC, stop and regenerate the node file
  with the observed names. Do not load on an assumption.
- Caveat (E11, L5): the generated `node0`/`node1` groups are cluster-only, and
  the active configuration keeps `ge-7/0/x` stanzas standalone Junos cannot
  parse ("fpc value outside range"). The candidate shows as modified,
  `configure exclusive` is refused ("configuration database modified"), and
  `show | compare` cannot diff. Use plain `configure` (shared), do the targeted
  cleanup below, and verify by section instead of by diff: `show chassis`,
  `show interfaces terse`, `show security zones`, and a count of
  `show configuration groups | display set | count`.
- Only if ICL encryption is chosen, install the IKE package:
  `request system software add optional://junos-ike.tgz` (E6).
- Targeted cleanup, then merge. Do **not** run a bare `delete` followed by
  `load set`: the node files carry no `system login`, `root-authentication`,
  `system services`, `snmp` or `syslog` stanzas (T24), so a full wipe would
  remove console and management access. Instead, in configuration mode on the
  node:
  `delete apply-groups`, `delete groups node0`, `delete groups node1`,
  `delete chassis cluster`, `delete interfaces fab0`, `delete interfaces fab1`,
  and for each reth `delete interfaces reth<N>`, each child port's
  `delete interfaces <PHYS> gigether-options redundant-parent`, and every
  remaining reth reference (zone membership, NAT proxy ARP, IKE
  `external-interface`) as listed in the inventory. Then `load set node1.set`
  (the marker-free `node1.load.set`, merge; the merge keeps the cluster config
  already on the node, so statements it already holds need not be loaded and
  redacted-value lines are omitted, L6), `commit check`; the check names any dangling reth or group
  reference, which you delete and repeat. Do not commit `needed` placeholders.
  Confirm before commit that `show configuration system` still has the
  operator's login, services, snmp and syslog (the system baseline). Uncertain:
  the delete list is derived from the inventory, not a Juniper-documented
  procedure; `commit check` is the arbiter.
- `commit`. Committing `chassis high-availability` makes Junos warn "High
  Availability Mode changed, please reboot the device"; until then
  `show chassis high-availability information` says "mode not configured" (L3).
  Reboot node1 (with approval) to activate HA mode, and re-check it is
  reachable on fxp0.
- Operator-applied: review and `load set` `node1.ipsec.set` (the IPsec-SRG block, T14)
  now, so the VPN anchor exists before traffic moves.
  `srx-mnha-builder` will not push it.
- Then `commit check` and `commit` (or `commit confirmed <minutes>`, followed
  by a plain `commit` once the checks below pass). A failed `commit check`
  here is a stop-and-rollback point: do not move traffic; use the phase 2
  rollback.
- Do not enable node1's revenue ports yet.

Verify on node1 after the HA-activation reboot: `show chassis cluster status`
reports cluster is not enabled; `show configuration chassis high-availability`;
`show interfaces terse`. The ICL cannot be fully tested until node0 is converted
(Phase 4); here confirm only that the ICL interface is up. Also:
- `show security ike security-associations` and
  `show security ipsec security-associations`: expect no peer SAs yet, because
  revenue ports are down; the commit of the T14 block must have succeeded.
- `show chassis high-availability services-redundancy-group <N>` for the
  IPsec SRG: shows the configuration; with no peer yet, a `HOLD` or
  not-active state is expected (per srx-mnha-builder
  `references/verification.md`: SRG1 `HOLD` with peer `DOWN` is expected;
  inferred here for a standalone node before the peer exists).

> **Rollback box, phase 2:** node1 is out of production, so this is the
> cheapest point. From the console:
> `load override <CLUSTER_BACKUP_FILE>` (text format), or `delete` then
> `load set <CLUSTER_BACKUP_SET>`, or `rollback rescue`; `commit`, then
> `set chassis cluster cluster-id <CLUSTER_ID> node 1 reboot`. Control and
> fabric cabling is still in place (removed only in Phase 4); re-enable
> child ports and confirm `show chassis cluster status` shows two nodes.

## Phase 3 - Move traffic to node1

**Pre-gate (before step 1): readiness only.** On node1 confirm the
configuration is present for every SRG that carries a VIP or VPN: the
`chassis high-availability` block, the ICL, and the VIP and signal-route
statements (`show configuration chassis high-availability`). Do not require
`ACTIVE` yet: Phase 2 leaves node1's monitored links down, and with no peer
ever seen an SRG sits in `HOLD` (VIPs `NOT INSTALLED`) and promotes itself to
`ACTIVE` after about 60 s once its monitored links are up (L7). The bounded
`ACTIVE` check is after step 2 below. If configuration is missing, stop before
touching node0.

Order, for every segment type (routed, default-gateway, hybrid), and never
reversed:

1. Take node0's reth child ports down at the switches (and withdraw node0's
   advertisements for routed and hybrid segments). Confirm they are down:
   switch port status and `show interfaces reth<N> terse` on node0.
2. Only then enable node1's revenue interfaces and routing sessions or
   advertisements; for default-gateway and hybrid segments node1 takes the
   VIP/gateway address (gratuitous ARP announces it; with only `virtual-ip`
   configured the VIP uses node1's physical NIC MAC, so expect a MAC change,
   L10, T2). Expected outage for the segment: about 75 s from link shut to
   `ACTIVE` in the lab (L7); tell stakeholders.
   **Bounded ACTIVE check (L7).** Right after node1's links are up, wait up to
   about 90 s, then run `show chassis high-availability
   services-redundancy-group <N>` for every SRG that carries a VIP or VPN:
   each must be `ACTIVE` with VIPs `INSTALLED`. If any SRG is still not
   `ACTIVE`, abort: shut node1's revenue links again, restore node0's reth
   child ports, and use rollback box 3.
3. Duplicate-address check: `show arp no-resolve` on node1, and the
   upstream/switch ARP and MAC tables, show one MAC per gateway address and no
   address on two ports.

Per-segment method follows the decision record's mode. Routed: confirm
neighbors hold node1's routes. Hybrid: both of the above.
Node0 is the cluster's last member and now carries no traffic; node1 is a
single standalone node.

Verify on node1, and compare with the Phase 0 baseline:

- `show security flow session summary`
- `show route summary` and `show route protocol <PROTO>`
- `show arp no-resolve` and `show interfaces terse`
- a test flow per segment from a host
- if VPN terminates here, `show security ipsec security-associations`:
  expected up, since the T14 block was applied in Phase 2; if it was not, SAs
  are down until it is applied and this is the stated VPN outage.

> **Rollback box, phase 3:** reverse the order: shut node1's revenue ports and
> advertisements, confirm down, then re-advertise from node0 and re-enable its
> ports. Node0 is still a working cluster member
> (running alone), so traffic returns to it. To restore the cluster, follow
> the phase 2 rollback.

## Phase 4 - Convert node0

- Confirm Phase 3 verification is stable for the agreed soak time.
- Pre-stage while node0 is still reachable (L4, verified on node0). Node1 has
  left, so the cluster configuration is effectively node0-only: in shared
  `configure`, commit `set system host-name <NODE0_HOSTNAME>` and the fxp0
  address at top level, then `delete apply-groups`, then `commit`. Do this
  before the disable command so node0 stays reachable on fxp0 and no console is
  needed. Use the console only as recovery.
- Then `set chassis cluster disable reboot` on node0 (E11).
- After reboot, apply the Phase 2 **MAC-map STOP check** (L1) and the same
  targeted cleanup and shared-`configure` handling (L5; never a bare `delete`),
  install the IKE package if encrypting, then `load set node0.load.set`,
  `commit check`, `commit`. Revenue ports stay down until Phase 5 verification,
  except any port that carries the ICL.
- Committing `chassis high-availability` needs the HA-activation reboot here as
  well (L3): reboot node0 and confirm fxp0 and the ICL come back.
- Remove or disable only the control and fabric cabling that the decision
  record leaves unused (T10, T11). Retain any former fabric or control NIC the
  decision record assigned to the ICL (Phase 2 allows reuse); cutting it cuts
  the HA path. The control links themselves have no MNHA role.

Verify on node0: no cluster status, `show configuration chassis
high-availability`, ICL interface up and `ping <NODE1_ICL_IP> count 5 rapid`
and `ping <NODE1_ICL_IP> size 1400 do-not-fragment count 5` both 0% loss.

> **Rollback box, phase 4:** node1 is carrying traffic, so there is no clean
> two-node cluster to return to without an outage. Options: restore node0
> with the rescue/backup config and `set chassis cluster cluster-id
> <CLUSTER_ID> node 0 reboot`, then repeat the phase 2 rollback on node1 and
> reconnect control and fabric; or continue to Phase 5 if only a detail is
> wrong. Decide before the window, not during it.

## Phases 5 and 6 - Form HA, failover test

Continue in [cutover-runbook-ha.md](cutover-runbook-ha.md). Rollback: see the phase 5 and phase 6 rollback boxes in cutover-runbook-ha.md.

## Rollback summary

| From phase | Return path |
|---|---|
| 0, 1 | Nothing configured; undo the port isolation |
| 2, 3 | Node1: restore backup (text `load override`, or `delete` + `load set` of the set backup) or rescue, `set chassis cluster cluster-id <CLUSTER_ID> node 1 reboot`, recable |
| 4, 5, 6 | Both nodes: follow the phase 5 rollback box in [part 2](cutover-runbook-ha.md); outage expected |

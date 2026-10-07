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
  installed if the ICL is encrypted (E5, E6).
- Cluster healthy:
  `show chassis cluster status`, `show chassis cluster interfaces`,
  `show chassis cluster information`.
- Baselines saved to files off the box: `show security flow session summary`,
  `show route summary`, `show route protocol <PROTO>` for each routing
  protocol, `show arp no-resolve`, `show security ike security-associations`,
  `show security ipsec security-associations`, `show interfaces reth<N> terse`.
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
  per-node peering (T3, T17); switches must tolerate the VIP/MAC move (T2).

Verify: both nodes `primary`/`secondary`, no RG in `ineligible` or
`disabled`, baselines captured, `show system configuration rescue` shows a
rescue configuration on each node.

> **Rollback box, phase 0:** nothing changed. Abort and discard files.

## Phase 1 - Fail all RGs to node0 and isolate node1

- Move every RG to node0, per RG:
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
  (E4); node0 is not yet MNHA, so only node1 needs the path now.
- On node1 console: `set chassis cluster disable reboot` (operational
  command, E11).
- Caveat (E11): the generated `node0`/`node1` groups are cluster-only. After
  the reboot node1 may fail to load its configuration; use the console and
  `delete` then `load set node1.set` (the groups are not in it) rather than
  trying to edit the old config.
- Install the IKE package if the ICL is encrypted:
  `request system software add optional://junos-ike.tgz` (E6).
- `delete`, then `load set node1.set`, `commit check`, then `commit`. Do not
  commit `needed` placeholders. (`delete` plus `load set` is the documented-style
  path for set files; any other load method here is uncertain.)
- Operator-applied: uncomment, review and `load set` the IPsec-SRG block (T14)
  from `node1.set` now, so the VPN anchor exists before traffic moves.
  `srx-mnha-builder` will not push it.
- Then `commit check` and `commit` (or `commit confirmed <minutes>`, followed
  by a plain `commit` once the checks below pass). A failed `commit check`
  here is a stop-and-rollback point: do not move traffic; use the phase 2
  rollback.
- Do not enable node1's revenue ports yet.

Verify on node1: `show chassis cluster status` reports cluster is not
enabled; `show configuration chassis high-availability`;
`show interfaces terse`. The ICL cannot be fully tested until node0 is converted
(Phase 4); here confirm only that the ICL interface is up. Also:
- `show security ike security-associations` and
  `show security ipsec security-associations`: expect no peer SAs yet, because
  revenue ports are down; the commit of the T14 block must have succeeded.
- `show chassis high-availability services-redundancy-group <N>` for the
  IPsec SRG: shows the configuration; with no peer yet, a `HOLD` or
  not-active state is expected.

> **Rollback box, phase 2:** node1 is out of production, so this is the
> cheapest point. From the console:
> `load override <CLUSTER_BACKUP_FILE>` (text format), or `delete` then
> `load set <CLUSTER_BACKUP_SET>`, or `rollback rescue`; `commit`, then
> `set chassis cluster cluster-id <CLUSTER_ID> node 1 reboot`. Control and
> fabric cabling is still in place (removed only in Phase 4); re-enable
> child ports and confirm `show chassis cluster status` shows two nodes.

## Phase 3 - Move traffic to node1

Order, for every segment type (routed, default-gateway, hybrid), and never
reversed:

1. Take node0's reth child ports down at the switches (and withdraw node0's
   advertisements for routed and hybrid segments). Confirm they are down:
   switch port status and `show interfaces reth<N> terse` on node0.
2. Only then enable node1's revenue interfaces and routing sessions or
   advertisements; for default-gateway and hybrid segments node1 takes the
   VIP/gateway address (expect a MAC change and gratuitous ARP, T2).
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
- On node0 console: `set chassis cluster disable reboot` (E11, same groups
  caveat).
- After reboot, install the IKE package, `delete`, then `load set node0.set`,
  `commit check`, `commit`. Revenue ports stay down until Phase 5 verification.
- Remove or disable control and fabric cabling (T10, T11); these links have no
  MNHA role.

Verify on node0: no cluster status, `show configuration chassis
high-availability`, ICL interface up and `ping <NODE1_ICL_IP> count 5 rapid`
and `ping <NODE1_ICL_IP> size 1400 do-not-fragment count 5` both 0% loss.

> **Rollback box, phase 4:** node1 is carrying traffic, so there is no clean
> two-node cluster to return to without an outage. Options: restore node0
> with the rescue/backup config and `set chassis cluster cluster-id
> <CLUSTER_ID> node 0 reboot`, then repeat the phase 2 rollback on node1 and
> reconnect control and fabric; or continue to Phase 5 if only a detail is
> wrong. Decide before the window, not during it.

## Phase 5 - Form HA

- Apply the operator-only IPsec-SRG block (T14) on node0 by hand after review
  (node1 has it from Phase 2); `srx-mnha-builder` will not push it.
- Reboot per the target release's MNHA formation guidance if the chosen
  configuration form requires it. Uncertain, unsourced: a node may need two
  reboot cycles (seen in field notes in `srx-mnha-builder`, not in Juniper
  documentation).
- Enable node0's revenue ports in the order from the decision record.

Verify on both nodes:

- `show chassis high-availability information`: `Node Status: ONLINE`, peer
  `Conn State: UP`, `Cold Sync Status: COMPLETE`, `Encrypted: YES` when the
  ICL is encrypted.
- `show chassis high-availability services-redundancy-group 0` and
  `show chassis high-availability services-redundancy-group <N>` for each SRG:
  exactly one `ACTIVE` per active/backup SRG, VIP `INSTALLED` only on the
  active node, signal routes where expected.
- `show security ipsec security-associations ha-link-encryption`.
- `show bfd session extensive` (when BFD is used).
- Config sync: `commit peers-synchronize` test of the common block, then
  compare `show configuration | display set` common sections.
- Session sync: `show security flow session summary` on both nodes.

> **Rollback box, phase 5:** controlled order, outage expected. (1) Shut both
> nodes' revenue ports at the switches. (2) On each node console restore the
> cluster backup (`load override <CLUSTER_BACKUP_FILE>`, or `delete` then
> `load set <CLUSTER_BACKUP_SET>`) and `commit`. (3) Restore control and
> fabric cabling. (4) `set chassis cluster cluster-id <CLUSTER_ID> node 0
> reboot` on node0, wait for it to come up as cluster primary, then
> `... node 1 reboot` on node1. (5) Confirm `show chassis cluster status`
> shows both nodes, then re-enable node0's ports first, node1's after
> verification. The reboot order is a recommendation, not Juniper-documented.

## Phase 6 - Failover test

- Start long-lived test traffic through the pair.
- Trigger a manual failover on the current active node:
  `request chassis high-availability failover services-redundancy-group <N>
  peer-id <PEER_LOCAL_ID>` (`peer-id` is mandatory). Then fail back.
- Pass: roles swap, VIP and signal routes move, upstream route selection
  follows (`show route <PROTECTED_PREFIX>` on the upstream), sessions survive,
  ARP entries refresh.
- Test each SRG, and a monitor-triggered failover only if the user approved it.
- Compare final state to the Phase 0 baseline; record deviations in the
  fidelity report as follow-ups.

Verify: `show chassis high-availability information`,
`show chassis high-availability services-redundancy-group <N>` on both nodes
after each failover, plus the upstream route table.

> **Rollback box, phase 6:** fail back to the original active node. If the
> pair is unstable, treat as phase 5 rollback.

## Rollback summary

| From phase | Return path |
|---|---|
| 0, 1 | Nothing configured; undo the port isolation |
| 2, 3 | Node1: restore backup (text `load override`, or `delete` + `load set` of the set backup) or rescue, `set chassis cluster cluster-id <CLUSTER_ID> node 1 reboot`, recable |
| 4, 5, 6 | Both nodes: follow the phase 5 rollback order; outage expected |

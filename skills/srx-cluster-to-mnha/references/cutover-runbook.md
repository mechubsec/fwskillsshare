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
- Backups: `request system configuration rescue save` and
  `show configuration | display set | save <CLUSTER_BACKUP_FILE>`; copy off the
  device.
- Physical/virtual plan ready for the ICL path between nodes (routed, E4) and
  for removing control and fabric cabling (T10, T11).
- Upstream/downstream owners notified: routing neighbors must accept the new
  per-node peering (T3, T17); switches must tolerate the VIP/MAC move (T2).

Verify: both nodes `primary`/`secondary`, no RG in `ineligible` or
`disabled`, baselines captured.

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
  `load override` with `node1.set` (the groups are not in it) rather than
  trying to edit the old config.
- Install the IKE package if the ICL is encrypted:
  `request system software add optional://junos-ike.tgz` (E6).
- `load override` (or `load set` after `delete`) the contents of `node1.set`,
  `commit check`, then `commit`. Do not commit `needed` placeholders.
- Do not enable node1's revenue ports yet.

Verify on node1: `show chassis cluster status` reports cluster is not
enabled; `show configuration chassis high-availability`;
`show interfaces terse`. The ICL cannot be fully tested until node0 is converted
(Phase 4); here confirm only that the ICL interface is up.

> **Rollback box, phase 2:** node1 is out of production, so this is the
> cheapest point. From the console:
> `load override <CLUSTER_BACKUP_FILE>` or `rollback rescue`, `commit`, then
> `set chassis cluster cluster-id <CLUSTER_ID> node 1 reboot`. Reconnect
> control and fabric cabling, re-enable child ports, confirm
> `show chassis cluster status` shows two nodes.

## Phase 3 - Move traffic to node1

Method follows the decision record's mode for each segment.

- Routed segments: bring up node1's revenue interfaces and routing sessions;
  confirm neighbors hold node1's routes; then withdraw or de-prefer node0's
  advertisements (higher metric or shut the neighbor), so the upstream picks
  node1.
- Default-gateway segments: shut node0's reth children at the switches and
  enable node1's; node1 takes the VIP/gateway address (expect a MAC change and
  gratuitous ARP, T2).
- Hybrid: do both per segment.
- Mind the outage window: node0 is the cluster's last member and now carries no
  traffic; node1 is a single standalone node.

Verify on node1: `show security flow session summary`,
`show route summary`, `show route protocol <PROTO>`,
`show arp no-resolve`, `show interfaces terse`, a test flow per segment from a
host, and the IPsec SAs (`show security ipsec security-associations`) if VPN
terminates here. Compare with the Phase 0 baseline.

> **Rollback box, phase 3:** re-advertise from node0 and re-enable its ports;
> shut node1's revenue ports. Node0 is still a working cluster member
> (running alone), so traffic returns to it. To restore the cluster, follow
> the phase 2 rollback.

## Phase 4 - Convert node0

- Confirm Phase 3 verification is stable for the agreed soak time.
- On node0 console: `set chassis cluster disable reboot` (E11, same groups
  caveat).
- After reboot, install the IKE package, `load override` `node0.set`,
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

- Apply the operator-only IPsec-SRG block (T14) by hand on both nodes after
  review; `srx-mnha-builder` will not push it.
- Reboot per the target release's MNHA formation guidance if the chosen
  configuration form requires it; a node can need two reboot cycles.
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

> **Rollback box, phase 5:** run `rollback rescue` and
> `set chassis cluster cluster-id <CLUSTER_ID> node <N> reboot` on each node,
> restore control and fabric cabling and child ports, load the cluster backup
> (`<CLUSTER_BACKUP_FILE>`), and confirm `show chassis cluster status`. Expect
> an outage while the cluster re-forms.

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
| 2, 3 | Node1: restore backup/rescue, `set chassis cluster cluster-id <CLUSTER_ID> node 1 reboot`, recable |
| 4, 5, 6 | Both nodes: restore backup/rescue, `set chassis cluster cluster-id <CLUSTER_ID> node <N> reboot`, recable; outage expected |

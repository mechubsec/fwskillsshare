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
  (E4); node0 is not yet MNHA, so only node1 needs the path now. The ICL uses
  ports separate from fab and control; those remain cabled until Phase 4.
- On node1 console: `set chassis cluster disable reboot` (operational
  command, E11).
- Caveat (E11): the generated `node0`/`node1` groups are cluster-only. After
  the reboot node1 may fail to load its configuration; use the console and the
  targeted cleanup below rather than trying to edit the old config.
- Install the IKE package if the ICL is encrypted:
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
  (merge), `commit check`; the check names any dangling reth or group
  reference, which you delete and repeat. Do not commit `needed` placeholders.
  Confirm before commit that `show configuration system` still has the
  operator's login, services, snmp and syslog (the system baseline). Uncertain:
  the delete list is derived from the inventory, not a Juniper-documented
  procedure; `commit check` is the arbiter.
- `commit`.
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

**Pre-gate (before step 1).** Phase 2 expects the IPsec SRG to sit in `HOLD`
with no peer, but step 2 below needs node1 to own the VIP. Before moving
anything, on node1 run
`show chassis high-availability services-redundancy-group <N>` for every SRG
that carries a VIP or VPN, and confirm each SRG can become active standalone
(not `HOLD` or ineligible), or that the VIP can be installed locally. Uncertain,
unsourced: whether a standalone node1 with no peer promotes an SRG out of
`HOLD`; verify in a lab. If any SRG will not go active, abort: do not touch
node0; use rollback box 3 (nothing has moved yet).

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
- After reboot, install the IKE package, run the same targeted cleanup as
  Phase 2 (never a bare `delete`), then `load set node0.set`, `commit check`,
  `commit`. Revenue ports stay down until Phase 5 verification, except any
  port that carries the ICL.
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
- Keep preemption off for the cutover, even if the decision record wants it
  later, so a higher-priority node0 does not take ownership the moment HA
  forms. Enable it afterwards as a separate approved change.
- Order is form HA, verify, then enable ports. Node0's revenue ports stay down
  (except a port that carries the ICL) until the gate below passes.

**Gate A, with node0's data ports still down.** Run on both nodes:

- `show chassis high-availability information`: `Node Status: ONLINE`, peer
  `Conn State: UP`, `Cold Sync Status: COMPLETE`, `Encrypted: YES` when the
  ICL is encrypted.
- `show chassis high-availability services-redundancy-group <N>` for SRG0 and
  every other SRG: exactly one `ACTIVE` per active/backup SRG (node1, which
  carries traffic), node0 backup or hold.

If cold sync fails, both nodes can self-elect ACTIVE (`srx-mnha` pitfall 22),
which would duplicate the VIP and gateway once node0's ports come up. **Do not
enable node0's revenue ports if two nodes show ACTIVE for an SRG, if `Conn State`
is not UP, or if cold sync is not COMPLETE.** Abort path: leave node0's data
ports down (traffic stays on node1), first rule out the ICL zone missing
`host-inbound-traffic protocols bfd` (pitfall 22), then re-check the ICL path;
if unresolved inside the window, use the phase 5 rollback box. If node0 shows
ACTIVE alone, fail the SRG back to node1 with the Phase 6 failover command
(`peer-id` mandatory) before continuing. Uncertain: which node wins the initial
election with preemption off.

- Then enable node0's revenue ports in the order from the decision record.

**Gate B, after ports are up**, on both nodes:

- Re-run the Gate A checks. VIP `INSTALLED` only on the active node, signal
  routes where expected, and `show arp no-resolve` shows one MAC per gateway.
- `show security ipsec security-associations ha-link-encryption`.
- `show bfd session extensive` (when BFD is used).
- Config parity, read-only: save `show configuration | display set` from each
  node and compare the common sections off the box. Do not run
  `commit peers-synchronize` from this runbook: its scope is Uncertain (E8
  says only that config is replicated), and it may overwrite node-local
  configuration. If the operator still wants it, only after confirming
  node-local isolation in a lab, and under `commit confirmed`.
- Session sync: `show security flow session summary` on both nodes.

> **Rollback box, phase 5:** trigger: Gate A fails (two ACTIVE, `Conn State`
> not UP, cold sync not COMPLETE) and is not fixed in the window, or Gate B
> shows a duplicate gateway MAC. Controlled order, outage expected. (1) Shut both
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

# Cutover runbook, part 2: form HA and failover test

Phases 5 and 6 of the cutover. Phases 0 to 4 and the rollback summary are in
[cutover-runbook.md](cutover-runbook.md); conventions (node A / node B), the
execution boundary and placeholders are defined there. Every reboot, commit and
failover below needs explicit approval at that step.

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
  `Conn State: UP`, `Cold Sync Status: COMPLETE`, `Encrypted: YES` only if
  ICL encryption was chosen (an unencrypted ICL is lab-unverified, E4).
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
ACTIVE alone, fail the SRG back to node1 with `request chassis
high-availability failover services-redundancy-group <N> peer-id
<PEER_LOCAL_ID>` (`peer-id` mandatory) before continuing. Uncertain: which node wins the initial
election with preemption off.

- Then enable node0's revenue ports in the order from the decision record.

**Gate B, after ports are up**, on both nodes:

- Re-run the Gate A checks. VIP `INSTALLED` only on the active node, signal
  routes where expected, and `show arp no-resolve` shows one MAC per gateway.
- Only if ICL encryption was chosen: `show security ipsec security-associations ha-link-encryption`.
- `show bfd session extensive` (when BFD is used).
- Config parity, read-only: save `show configuration | display set` from each
  node and compare the common sections off the box. Do not run
  `commit peers-synchronize` from this runbook: its scope is Uncertain (E8
  says only that config is replicated), and it may overwrite node-local
  configuration. If the operator still wants it, only after confirming
  node-local isolation in a lab, and under `commit confirmed`.
- Session sync: `show security flow session summary` on both nodes.

**Gate B abort path.** If Gate B fails for any reason (VIP not installed, BFD
or ICL down, two ACTIVE for any SRG, duplicate gateway MAC or ARP),
immediately shut node0's data ports (traffic stays on node1), then follow the
phase 5 rollback box.

> **Rollback box, phase 5:** trigger: Gate A fails (two ACTIVE, `Conn State`
> not UP, cold sync not COMPLETE) and is not fixed in the window, or Gate B
> fails for any reason (VIP not installed, BFD or ICL down, two ACTIVE for any
> SRG, duplicate gateway MAC or ARP) after node0's data ports are shut. Controlled order, outage expected. (1) Shut both
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

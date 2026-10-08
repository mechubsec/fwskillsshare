# Cutover runbook, part 2: form HA and failover test

Phases 5 and 6 of the cutover. Phases 0 to 4 and the rollback summary are in
[cutover-runbook.md](cutover-runbook.md); conventions (node A / node B), the
execution boundary and placeholders are defined there. Every reboot, commit and
failover below needs explicit approval at that step.

## Phase 5 - Form HA

- Apply the operator-only IPsec-SRG block (T14) on node0 by hand after review
  (node1 has it from Phase 2); `srx-mnha-builder` will not push it.
- Node0's `chassis high-availability` commit needs the HA-activation reboot
  from Phase 4 (L3); if it was not done there, do it now. One reboot per node
  was enough in the lab. Uncertain, unsourced: other releases may need two
  reboot cycles (field notes in `srx-mnha-builder`, not Juniper documentation).
- Wait for cold sync after node0's reboot. In the lab `Conn State` was `DOWN`
  and then `IN PROGRESS` first, and `COMPLETE` came after about 60 to 90 s
  (L9). Poll for up to about 3 minutes before treating it as a failure.
- Keep preemption off for the cutover, even if the decision record wants it
  later, so a higher-priority node0 does not take ownership the moment HA
  forms. Enable it afterwards as a separate approved change.
- Order is form HA, verify, then enable ports. Node0's revenue ports stay down
  (except a port that carries the ICL) until the gate below passes.

**Gate A, with node0's data ports still down.** Run on both nodes:

- `show chassis high-availability information`: `Node Status: ONLINE`, peer
  `Conn State: UP`, `Cold Sync Status: COMPLETE`, `Encrypted: YES` only if
  ICL encryption was chosen. `Encrypted: NO` with `Conn State: UP` and cold sync
  COMPLETE is a working unencrypted ICL (L8): record it as an accepted
  deviation from the encryption recommendation (E4), not a failure.
- `show chassis high-availability services-redundancy-group <N>` for SRG0 and
  every other SRG: exactly one `ACTIVE` per active/backup SRG (SRG1 and up;
  node1, which carries traffic), node0 backup or hold. SRG0 is active/active by
  design (E2) and shows `ONLINE` on both nodes; that is not split-brain.

If cold sync fails, both nodes can self-elect ACTIVE on an active/backup SRG (`srx-mnha` pitfall 22),
which would duplicate the VIP and gateway once node0's ports come up. **Do not
enable node0's revenue ports if two nodes show ACTIVE for an active/backup SRG (SRG1+, never SRG0), if `Conn State`
is not UP, or if cold sync is not COMPLETE.** Abort path: leave node0's data
ports down (traffic stays on node1), first rule out the ICL zone missing
`host-inbound-traffic protocols bfd` (pitfall 22), then re-check the ICL path;
if unresolved inside the window, use the phase 5 rollback box. If node0 shows
ACTIVE alone on an active/backup SRG, fail the SRG back to node1 with `request chassis
high-availability failover services-redundancy-group <N> peer-id
<PEER_LOCAL_ID>` (`peer-id` mandatory) before continuing. `<PEER_LOCAL_ID>` is
the `local-id` of the other node (node0 has `local-id 1`, so run on node0 with
peer-id 2; swap on node1). In the lab the node that was already ACTIVE kept the
role and the second node came up BACKUP with preemption off (L11); other
releases are uncertain.

- Then enable node0's revenue ports in the order from the decision record. In
  the lab the second node stayed BACKUP after its links came up (L11).

**Gate B, after ports are up**, on both nodes:

- Re-run the Gate A checks. VIP `INSTALLED` only on the active node, signal
  routes where expected, and `show arp no-resolve` shows one MAC per gateway.
  With `virtual-ip` alone, that MAC is the active node's physical NIC MAC
  (L10); the MAC changing on failover is expected, and gratuitous ARP carries it.
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
or ICL down, two ACTIVE for any active/backup SRG (SRG1+), duplicate gateway MAC or ARP),
immediately shut node0's data ports (traffic stays on node1), then follow the
phase 5 rollback box.

> **Rollback box, phase 5:** trigger: Gate A fails (two ACTIVE on an active/backup SRG, `Conn State`
> not UP, cold sync not COMPLETE) and is not fixed in the window, or Gate B
> fails for any reason (VIP not installed, BFD or ICL down, two ACTIVE for any
> active/backup SRG (SRG1+; SRG0 is active/active by design), duplicate gateway MAC or ARP) after node0's data ports are shut. Controlled order, outage expected. (1) Shut both
> nodes' revenue ports at the switches. (2) On each node console restore the
> cluster backup (`load override <CLUSTER_BACKUP_FILE>`, or `delete` then
> `load set <CLUSTER_BACKUP_SET>`) and `commit`. (3) Restore control and
> fabric cabling. (4) `set chassis cluster cluster-id <CLUSTER_ID> node 0
> reboot` on node0, wait for it to come up as cluster primary, then
> `... node 1 reboot` on node1. (5) Confirm `show chassis cluster status`
> shows both nodes, then re-enable node0's ports first, node1's after
> verification. The reboot order is a recommendation, not Juniper-documented.
> In a virtual lab the hypervisor snapshot from Phase 0 is the faster rollback
> than steps (2) to (4) (L12); restoring it needs its own approval.

## Phase 6 - Failover test

- Start long-lived test traffic through the pair.
- Trigger a manual failover on the current active node:
  `request chassis high-availability failover services-redundancy-group <N>
  peer-id <PEER_LOCAL_ID>` (`peer-id` is mandatory; it took no confirmation
  prompt in the lab, L11, so the approval step is yours). Then fail back.
  Lab result: about 1 s outage, VIP MAC moved, gratuitous ARP carried it (L10).
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

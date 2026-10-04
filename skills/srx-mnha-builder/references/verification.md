# Verification: pass criteria and diagnostic tree

## Contents

- [After Stage 1 (underlay)](#after-stage-1-underlay)
- [After Stage 2 + reboot (HA formation)](#after-stage-2--reboot-ha-formation)
- [VIP checks (switching / hybrid)](#vip-checks-switching--hybrid)
- [After Stage 3 (routing)](#after-stage-3-routing)
- [Role-consistency invariant (hybrid / routing) - check after Stage 3 and after every failover](#role-consistency-invariant-hybrid--routing---check-after-stage-3-and-after-every-failover)
- [Node-sourced tests: expected asymmetric failures (hybrid / routing)](#node-sourced-tests-expected-asymmetric-failures-hybrid--routing)
- [Failover test (approval gate)](#failover-test-approval-gate)

Run each check on both nodes. Use the batch-command tool from `references/mcp-server-notes.md`:
- rust-junosmcp: `execute_junos_command_batch` (parallel server-side)
- Juniper junos-mcp-server: run `execute_junos_command` twice (sequential or parallel client-side)

Compare the results side by side.

## After Stage 1 (underlay)
- Each data segment: `ping <neighbor on that segment> count 3` from both nodes, **and** node-to-node
  on that segment (Node1 → Node0's segment address). The first packet is often lost while ARP
  resolves; judge on the rest.
- If one node reaches neither the neighbor nor its peer on a segment, while its link is up and
  the address is correct, the fault is the L2 attachment, not the config. Typical causes: the
  vNIC is on the wrong hypervisor port group or VLAN, or the neighbor expects a VLAN tag (check
  the neighbor's unit, e.g. `ge-0/0/0.20 vlan-id 20`) that the other node's port group adds and
  this one doesn't. Field-confirmed 2026-09-25 (Node1's ge-0/0/1 was not on the upstream router's VLAN 20
  segment). Hand this to the user. **Don't undo the stage.** The config is correct, and changing
  addressing to "fix" it would break the peer.
- `ping <peer_icl_ip> count 5 rapid` → 0% loss from both sides.
- `ping <peer_icl_ip> size 1400 do-not-fragment count 5` → 0% loss. Any loss here is an
  MTU problem on the ICL path; fix it before Stage 2.
- `show security zones security-zone <ICL_ZONE>` → the ICL interface is listed and
  `bfd` is in the host-inbound protocols.

## After Stage 2 + reboot (HA formation)
`show chassis high-availability information`:
- `Node Status: ONLINE` on both nodes.
- Peer `Conn State: UP`.
- `Cold Sync Status: COMPLETE`.
- *mode not configured* before the reboot is expected on 26.x. It is a failure after
  the reboot. Note that a node can need two reboot cycles.

`show chassis high-availability services-redundancy-group 1`:
- Exactly one node is ACTIVE, and it is the one with the higher `activeness-priority`
  (Node0 by default). The other node is BACKUP.
- `Process Packet In Backup State: NO` on the backup is expected, not a fault.

`show bfd session extensive`:
- Session `Up` with receive rate > 0 pps.

Encrypted ICL: `show chassis high-availability information` shows `Encrypted: YES`, and
`show security ipsec security-associations ha-link-encryption` lists one tunnel to the peer
ICL IP, with mirrored SPIs on the two nodes. The plain `show security ike|ipsec
security-associations` output does **not** list ICL SAs; it came back empty on 24.4R2.21 while
the ICL was encrypted (field-confirmed 2026-09-25).

A node rebooted alone into MNHA mode shows peer `Conn State: DOWN` and SRG1 `HOLD`. That is
expected until its peer comes up. If Conn State is DOWN with no IKE SA, check the
following before BFD: the same PSK on both nodes, `system-services ike` on the ICL zone
(shared ICL: on the transport zone too), and the junos-ike package on both nodes.

### Both nodes ACTIVE, or Conn State DOWN: check in this order
1. **BFD blocked on the ICL zone.** Signature: ICMP across the ICL at 0% loss, but
   `show bfd session extensive` shows `remote discriminator 0` and receive 0.0 pps.
   Fix: `host-inbound-traffic protocols bfd` on the ICL zone on BOTH nodes. The lint
   should have prevented this, so check whether the zone was edited by hand.
2. **Wrong config model.** `show configuration chassis high-availability | display set`
   on 26.x must use `grid-id` / `peer-domain-id`.
3. **Mirroring error.** Node0 local-id 1 / peer 2, Node1 local-id 2 / peer 1, ICL IPs
   swapped. Compare the two `stage2.set` files.
4. **vSRX dataplane not enumerated.** `show interfaces terse` shows only fxp0 and lo0,
   with no `ge-` interfaces. The user must do a full VM stop and start; a soft reboot
   is not enough.
5. **Still failing after steps 1-4.** Hand off to the `srx-mnha` skill's troubleshooting
   workflow with the evidence collected so far.

## VIP checks (switching / hybrid)
- `show interfaces terse` on the ACTIVE node lists the VIP on the VIP interface; the BACKUP does not.
- From a host on the segment: ping the VIP, then `arp -a` shows the vMAC.
- `show chassis high-availability services-redundancy-group 1` lists the virtual IP and monitored interfaces.

## After Stage 3 (routing)
- `show bgp summary` → the session to each neighbor is Established on both nodes.
- `show bfd session` → Up for the BGP neighbor when BFD is configured.
- `show route 169.254.200.1 exact`: present only on the ACTIVE node.
  `show route 169.254.200.2 exact`: present only on the BACKUP node.
- `show route advertising-protocol bgp <peer>` → protected prefixes and transit subnets
  with MED = active_metric on the ACTIVE node and backup_metric on the BACKUP node.
- The upstream router prefers the ACTIVE node. Ask the user to confirm this if the
  upstream is not managed by MCP.

## Role-consistency invariant (hybrid / routing) - check after Stage 3 and after every failover
One node must hold **all** of these at once:

| Signal | Where to read it | Expected |
|---|---|---|
| SRG1 role | `show chassis high-availability services-redundancy-group 1` (both nodes) | exactly one `Status: ACTIVE` |
| VIP (hybrid) | same output → `Virtual IP Info ... Status: INSTALLED`, or `show interfaces <vip-ifl> terse` | only on the ACTIVE node |
| Active signal route | same output → `Active Signal Route ... INSTALLED` | only on the ACTIVE node |
| Upstream selection | upstream: `show route <protected-prefix>` | active (`*`) path = ACTIVE node's upstream IP, MED = active_metric |

Pass only if all four point to the same node. Field-confirmed 2026-09-25 on a lab pair: Node0 was
ACTIVE, held VIP 198.51.100.1 and 169.254.200.1, and the upstream router selected Node0's upstream address 203.0.113.2 with MED 10.

If they diverge, check in this order:
1. **VIP on ACTIVE, upstream selects the backup.** Possible causes: the BGP session to the ACTIVE
   node is down (check BFD); the export condition's table doesn't match where the signal route is
   installed; MED isn't being compared because the upstream's paths come from different neighbor
   ASes; or the upstream has a local-preference or import policy that overrides MED.
2. **Both nodes advertise MED 10.** Both nodes are self-elected ACTIVE: split-brain, or cold sync
   never converged. Go to the formation diagnostic tree (BFD permit on the ICL first).
3. **Neither node advertises.** Signal routes aren't installed (SRG1 in HOLD), or the route-filter
   doesn't match the protected prefix.
4. **VIP on the backup, or on both.** Stop and treat it as split-brain; don't run more failovers.

Tests sourced from a node's own LAN address follow this invariant: they only pass on the ACTIVE
node (next section).

## Node-sourced tests: expected asymmetric failures (hybrid / routing)
A ping from a node sourced from its own LAN/downstream address (e.g. `ping <upstream> source
<node LAN IP>`) only works on the **SRG1 ACTIVE** node. The upstream learns the whole protected
prefix and prefers the active node (lower MED), so replies to the *backup* node's address go to
the active node. The active node has no session for them (self-originated sessions are not
synced) and drops the echo-reply. Field-confirmed 2026-09-25: from Node1 (backup), sourced
198.51.100.3, 0/5; from Node0 (active), sourced 198.51.100.2, 5/5. The same test from Node0
fails whenever Node1 is active. This is **not a fault**. Test node health from the upstream
interface address (directly connected), and test the datapath from a LAN host through the VIP.
If node-local LAN addresses must be reachable from upstream (monitoring or management), each
node has to export its own /32 (`from protocol local route-filter <node-IP>/32 exact`), which
beats the /24.

## Failover test (approval gate)
1. Start long-lived test traffic through the pair. `show security flow session summary`
   on both nodes should show the sessions on the active node, with a warm copy on the
   peer.
2. Trigger the SRG1 failover **on the current ACTIVE node**:
   `request chassis high-availability failover services-redundancy-group 1 peer-id <PEER_LOCAL_ID>`
   `peer-id` is mandatory. Without it the RPC fails with "missing mandatory argument: peer-id"
   and has no effect (field-confirmed on 24.4R2.21 flat, 2026-09-25). The switchover takes about
   a second. Confirm with `show chassis high-availability services-redundancy-group 1`, which
   shows the VIP, signal-route and probe status per node, and with the upstream's
   `show route <protected-prefix>` (the MED 10 path should move to the new ACTIVE node).
3. Pass: the roles swap, the signal routes move, BGP MEDs flip (routing and hybrid), the
   VIP moves and a host's ARP entry refreshes (switching and hybrid), and the test
   sessions survive.
   **Session survival and convergence (preferred over ping):** iperf3 from an outside host.
   - TCP: `-t 70 -b 100M -i 0.1 --timestamps --forceflush`. Look for resets, retransmits and dips
     in the 100 ms intervals.
   - UDP: `-u -b 20M -l 1000 -i 0.1 --get-server-output`. Outage = lost datagrams / 2,500 pps.
   - Before triggering, confirm the session is Active on one node and Warm on the other.
   - Field result 2026-09-25: TCP 1 retransmit and no dip, UDP 0/150,001 lost, for both
     failover and failback.
   - Run long commands in the background (`nohup timeout N ... &`) and poll with short calls, so
     one call can't block a single-threaded tool API.
   **Unplanned test (monitored uplink down)**
   - Method: `set interfaces <uplink> disable` on the ACTIVE node during an iperf3 run, then
     `delete ... disable` to restore.
   - Expected: that node goes INELIGIBLE `[IF]` and the peer goes ACTIVE at once.
   - The outage is set by **upstream failure detection**. If the upstream's link stays up (as with
     a vSwitch), it keeps sending to the dead next hop until BGP BFD expires.
   - Field result 2026-09-25, BFD 500 ms × 3: TCP 1.4 s, UDP 1.32 s (3,305 datagrams lost at
     2,500 pps). The session survived.
   - **Before failing back, confirm the recovered node's BGP session is Established on the
     upstream.** Otherwise the upstream has only the new backup's path, and the backup doesn't
     forward traffic.
   **Measuring the outage** (if a test host outside the pair can be driven, e.g. a Kali MCP server):
   - Start `nohup ping -D -O -i 0.1 -W 1 -c 900 <LAN host> > /tmp/fo.log &`, then trigger the
     failover about 5 s later.
   - Count lost replies (`no answer yet`, or gaps in `icmp_seq`) × 100 ms, and note the RTT spike.
   - Don't use `pkill -f <pattern>` in the same command: it matches its own shell and kills it
     (return code -15).
   - Before the test, run `show security match-policies` for the test flow on **both** nodes. A
     policy that differs between nodes turns a "hitless" failover into a black hole.
   - Field result 2026-09-25 (lab pair, hybrid, encrypted ICL, 24.4R2.21): 900/900 replies
     through failover and failback, 0 lost, one 3.5 ms RTT blip (0.67 ms average).
   - ICMP echo creates a new session per packet, so this measures **forwarding convergence**
     (VIP/ARP and BGP MED switch), not synchronized-session survival. Test session survival
     with a long-lived TCP flow, such as an SSH session or `iperf3 -t 120`, across the failover.
4. Fail back the same way and check again. With preemption off, failback is manual by
   design.

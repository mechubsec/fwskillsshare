# MNHA grid model (Junos 26.x) and field-confirmed behaviors

Field notes behind the SKILL.md "Config model: flat vs grid" section and the
Field-Confirmed Behaviors summary. Sources: a live vSRX3 24.4R1.9 hybrid pair
([upstream fwskillsshare issue #7](https://github.com/mechubsec/fwskillsshare/issues/7))
and a 2026-07 deployment of two routed MNHA pairs on vSRX 26.2R1.7 (grid model,
SRG1 `deployment-type routing`, eBGP + signal-route MED steering).

## Grid model configuration (field-confirmed on vSRX 26.2R1.7)

Routed pair, SRG1 `deployment-type routing`. Node A shown — mirror on Node B
with swapped IDs (`local-id 2`, `local-domain-id 2`, `peer-domain-id 1 peer-id 1`,
swapped ICL IPs, lower `activeness-priority`):

```junos
set chassis high-availability grid-id 1
set chassis high-availability local-id 1 local-ip <A_ICL_IP>
set chassis high-availability local-domain-id 1 domain-size 1
set chassis high-availability peer-domain-id 2 domain-size 1
set chassis high-availability peer-domain-id 2 peer-id 2 local-ip <A_ICL_IP>
set chassis high-availability peer-domain-id 2 peer-id 2 peer-ip <B_ICL_IP>
set chassis high-availability peer-domain-id 2 peer-id 2 interface <ICL_IFL>
set chassis high-availability peer-domain-id 2 peer-id 2 liveness-detection minimum-interval 1000 multiplier 3
set chassis high-availability services-redundancy-group 0 peer-domain-id 2 peer-id 2
set chassis high-availability services-redundancy-group 1 peer-domain-id 2 peer-id 2
set chassis high-availability services-redundancy-group 1 deployment-type routing
set chassis high-availability services-redundancy-group 1 activeness-probe dest-ip <PROBE_DST> src-ip <PROBE_SRC>
set chassis high-availability services-redundancy-group 1 activeness-priority 200
set chassis high-availability services-redundancy-group 1 active-signal-route 169.254.200.1
set chassis high-availability services-redundancy-group 1 backup-signal-route 169.254.200.2
```

- **`activeness-probe dest-ip <X> src-ip <Y>` is mandatory for `deployment-type
  routing`** (commit fails otherwise). `src-ip` is a **sub-field of `dest-ip`** —
  one statement. Aim it at a real reachable data-segment address, not the ICL.
- **Enabling chassis-HA needs a reboot** to activate (says *mode not configured*
  until then); a node may take **two reboot cycles** to reach `Node Status: ONLINE`.

## Field-confirmed on vSRX3 24.4R1.9 (hybrid, SRG0+SRG1, VIP downstream gateway)

- **Unzoned-leg default route black-holes transit** (SKILL.md pitfall 18): nodes
  shipped with a static default via an unzoned `ge-0/0/3` management leg;
  transit return traffic silently disappeared. Removing the static default so
  the BGP-learned default from the upstream won fixed transit immediately.
- **The backup node does not service SRG data traffic**: a datapath test
  sourced from the *backup* node's interface fails (0 replies) while the same
  test via the VIP / active node works. `show chassis high-availability
  services-redundancy-group 1` shows `Process Packet In Backup State: NO` —
  expected behavior, not a fault. Test through the VIP or the active node
  before chasing a non-bug.
- The `host-inbound-traffic system-services high-availability` zone knob
  commit-checks clean on vSRX 24.4R1 (live-verified 2026-07).

## Field-confirmed on vSRX 26.2R1.7 (two routed pairs, grid model)

- **Grid model required on 26.x.** The flat `local-id local-ip` / `peer-id
  peer-ip` form commits but never activates (*mode not configured*) until you
  switch to `grid-id`/`local-domain-id`/`peer-domain-id` **and reboot**.
- **ICL BFD is blocked unless the zone permits it as a PROTOCOL.** MNHA liveness
  is BFD, and in Junos BFD is `host-inbound-traffic protocols bfd`, **not** a
  `system-service`. A zone with `system-services high-availability` and `ping`
  passes ICMP but silently drops BFD, giving `Conn State: DOWN`,
  `Cold Sync Status: UNKNOWN` and SRG0 *No HA peer configured* — which reads
  exactly like a virtualization limitation and is not one.
  **Diagnostic signature:** ICMP crosses the ICL at 0% loss (including
  1400-byte DF), while `show bfd session extensive` shows `Client JSRPD`,
  `remote discriminator 0`, transmit ~0.5 pps and **receive 0.0 pps**.
  **Fix:** `set security zones security-zone <ICL_ZONE> host-inbound-traffic
  protocols bfd` on BOTH nodes. Confirmed 2026-08-16 on vSRX 26.2R1.7: BFD went
  to `Up`, receive rate to 1.0 pps, `Conn State: UP`, SRG0 `ONLINE`.
  Verify via `Conn State`/`Cold Sync Status`, not just `Node Status`.
- **Advertise connected transit subnets in the signal-route export**, not just
  learned routes — otherwise the peer can't route back to on-transit sources
  (SNAT address, a downstream firewall's transit IP) and return traffic
  black-holes. Add a `from protocol direct … route-filter <transit> exact
  accept` term (SKILL.md pitfall 21).
- **Active/active SNAT: give each node its own pool + proxy-ARP address** so
  they never both answer ARP for one IP; return traffic follows the pool that
  translated it, no VIP needed. Sessions don't survive a failover that changes
  the pool (only needed where cold-sync genuinely cannot converge — first rule
  out the ICL BFD permit above, which produces identical symptoms).
- **`fxp0` on DHCP black-holes transit** — its default (Access-internal pref 12)
  beats BGP (170). Make `fxp0` static where failover depends on the BGP default.
- **Virtualized SRX (vSRX on KVM/Proxmox):** a soft `request system reboot` can
  leave the dataplane un-enumerated (only `fxp0`/`lo0`, no `ge-`); a full VM
  stop+start clears it. **Chassis-cluster mode triggered this every time and its
  control link never formed — MNHA was the only workable HA model on that
  hypervisor.** Push config with `cat file | ssh root@dev 'cat > /var/tmp/x.set'`
  then `load set` (no scp subsystem); delete a fresh clone's `fxp0 family inet
  dhcp` before adding a static address or the commit fails the constraint check.

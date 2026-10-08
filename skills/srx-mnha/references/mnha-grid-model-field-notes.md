# MNHA config model, grid-id, and field-confirmed behaviors

Field notes behind the SKILL.md "Services Redundancy Groups" config-model note and the
Field-Confirmed Behaviors summary. Sources: a live vSRX3 24.4R1.9 hybrid pair
([upstream fwskillsshare issue #7](https://github.com/mechubsec/fwskillsshare/issues/7))
and a 2026-07 deployment of two routed MNHA pairs on vSRX 26.2R1.7 (SRG1 `deployment-type routing`, eBGP + signal-route MED steering).

## Config model: flat form works; grid-id is optional

Lab-verified (vSRX 26.2R1.7 on KVM, 2026-10-08, two-node, disposable pair):

- **R1. The flat form works on 26.2R1.7.** `local-id`/`local-ip` and `peer-id`/`peer-ip` commit (with the warning "High Availability Mode changed, please reboot"), show `chassis high-availability mode not configured` until the HA-activation reboot, and after it both nodes are Node Status ONLINE, Conn State UP, Cold Sync COMPLETE, SRG1 ACTIVE/BACKUP. No `grid-id`, `local-domain-id` or `peer-domain-id` is needed. The earlier "26.x requires the grid model" note was confounded with the missing reboot.
- **R3. `grid-id` coexists with the flat form.** `set chassis high-availability grid-id 1` commits on a running flat pair with no reboot warning; `show chassis high-availability information` shows `Grid-id: 1` (`Grid-id: 0` when unset).
- **R4. Virtual MAC is opt-in per VIP.** `set chassis high-availability services-redundancy-group <N> virtual-ip <I> use-virtual-mac` (CLI help: "Use virtual mac for SRG role enforcement"). Without it the VIP shows `VMAC: N/A` and answers ARP with the active node's physical NIC MAC (also seen on 24.4R1.9). With it, ARP resolves to a `00:10:db:fe:xx:xx` virtual MAC.
- **R5. VMAC generation depends on `grid-id`.** Without it (`Grid-id: 0`) the VMAC is per VIP (VIP1 `00:10:db:fe:01:01`, VIP2 `00:10:db:fe:01:02`, legacy generation); with `grid-id 1` both VIPs on SRG1 shared one VMAC (`00:10:db:fe:02:10`).
- **R2. Switching-mode constraint (lab-observed, 26.2R1.7):** commit fails unless SRG1 has both `virtual-ip` index 1 and index 2 ("virtual-ip index 1|2 is mandatory for switching deployment type"), and VIP interfaces must be unique per VIP ("Virtual IP interfaces must be unique"). Not tested on 24.4; may apply to other releases.
- **R6.** An unencrypted ICL formed and synced (`Encrypted: NO`) on 26.2R1.7.

### What Juniper documents (retrieved 2026-10-08)

Source: [MNHA preparation](https://www.juniper.net/documentation/us/en/software/junos/high-availability/topics/concept/mnha-preparation.html), "Scaling Virtual IP Support in MNHA".

- "In earlier implementations, the virtual MAC address (VMAC) was derived using the SRG identifier and VIP index. As a result, each VIP required a unique VMAC, limiting the number of VIPs to approximately 32 per SRG."
- "With this enhancement, VMAC is generated using a combination of the following parameters: Grid identifier (grid-id), Services redundancy group identifier (SRG-ID), Virtual MAC identifier (virtual-mac-id)".
- Syntax: `set chassis high-availability grid-id <1-15>`; per interface `set chassis high-availability services-redundancy-group <id> interface <interface> virtual-mac-id <0-15>`.
- "Up to 15 MNHA pairs can coexist within a single Layer 2 broadcast domain."
- "If the grid-id is not configured, the system continues to use the legacy VMAC generation method based on SRG-ID and VIP index. In this case, the VIP scale remains limited to approximately 32 per SRG."
- Change history: 25.4R1, "You can increase the number of virtual IP (VIP) addresses per Services Redundancy Group (SRG) up to 2000 in Multinode High Availability (MNHA) switching (default gateway) mode and on the L2 side of Hybrid mode."
- The sample configuration sets `local-id 1`, `local-id local-ip`, `grid-id 5`, `peer-id 2 peer-ip`, and `virtual-ip <n> use-virtual-mac` together, so `grid-id` sits alongside `local-id`/`peer-id`.
- `local-domain-id <domain-id> domain-size <size>` and `peer-domain-id <domain-id> peer-id ...` appear on the [four-node MNHA page](https://www.juniper.net/documentation/us/en/software/junos/high-availability/topics/topic-map/four-node-multinode-high-availability.html), not in the two-node examples.

### Flat form, routed pair (Node A; mirror on Node B)

ICL lines are the lab-verified flat form; the SRG1 routing lines are from the 2026-07 routed deployment. Mirror on Node B with `local-id 2`, `peer-id 1`, swapped ICL IPs and a lower `activeness-priority`:

```junos
set chassis high-availability local-id 1 local-ip <A_ICL_IP>
set chassis high-availability peer-id 2 peer-ip <B_ICL_IP>
set chassis high-availability peer-id 2 interface <ICL_IFL>
set chassis high-availability peer-id 2 liveness-detection minimum-interval 1000 multiplier 3
set chassis high-availability services-redundancy-group 0 peer-id 2
set chassis high-availability services-redundancy-group 1 peer-id 2
set chassis high-availability services-redundancy-group 1 deployment-type routing
set chassis high-availability services-redundancy-group 1 activeness-probe dest-ip <PROBE_DST> src-ip <PROBE_SRC>
set chassis high-availability services-redundancy-group 1 activeness-priority 200
set chassis high-availability services-redundancy-group 1 active-signal-route 169.254.200.1
set chassis high-availability services-redundancy-group 1 backup-signal-route 169.254.200.2
```

### Four-node-style syntax (optional; not required for two nodes)

This `grid-id` + `local-domain-id`/`peer-domain-id` shape was captured on vSRX 26.2R1.7 in a 2026-07 two-node deployment and committed there. It is the four-node MNHA syntax with a domain size of 1, not a replacement for the flat form (see R1). `vpn-profile` placement under `peer-domain-id` is documented by Juniper for four-node only. Node A shown:

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

## Field-confirmed on vSRX 26.2R1.7 (two routed pairs)

- **HA-activation reboot required on 26.x too.** The flat form commits, then shows *mode not configured* until the reboot (see R1); it does not need the grid fields.
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

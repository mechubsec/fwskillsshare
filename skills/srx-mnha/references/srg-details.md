# Services Redundancy Groups (SRG) Details

Juniper articles refer to Services Redundancy Groups, abbreviated SRGs. Use the Junos hierarchy under `chassis high-availability services-redundancy-group`.

## SRG0

SRG0 is the default forwarding group for routed MNHA behavior.

Operational model:

- no active/backup ownership model like a VIP group
- both nodes can be ready to forward
- no VIP/vMAC ownership is normally involved
- routing determines which node sees traffic
- runtime state can synchronize over ICL

If ICL is lost, state synchronization is affected. Routing may still deliver packets to either node, but stateful continuity is at risk until synchronization is restored.

## SRG1 and Higher

SRG1+ provides active/backup service behavior.

Use SRG1+ for:

- default gateway VIPs
- hybrid mode VIPs
- route signaling based on active/backup status
- interface/BFD/object monitoring tied to failover
- IPsec termination designs that require synchronized tunnel/SAs, where supported
- active/active distribution by using different SRGs active on different nodes

Common SRG1+ attributes:

```junos
set chassis high-availability services-redundancy-group <SRG> deployment-type <routing|hybrid|switching>
# deployment-type: routed/L3 = routing; hybrid = hybrid; default-gateway/L2 = switching
set chassis high-availability services-redundancy-group <SRG> peer-id <PEER_ID>
set chassis high-availability services-redundancy-group <SRG> activeness-priority <PRIORITY>
```

Verify:

```text
show chassis high-availability services-redundancy-group <SRG>
```

Look for:

- deployment type
- ACTIVE or BACKUP status
- activeness priority
- preemption state
- peer status
- health status
- failover readiness
- VIP status when configured

## Config Model: Flat Form, grid-id, and Four-Node Fields

The two-node form is the flat `local-id local-ip` / `peer-id <ID> peer-ip` model. It commits **and activates** on Junos 26.2R1.7 as well as 24.x (lab-verified, vSRX 26.2R1.7 on KVM, 2026-10-08: after the HA-activation reboot both nodes reached Node Status ONLINE, Conn State UP, Cold Sync COMPLETE). `show chassis high-availability information` says `mode not configured` until that reboot, on any release; earlier "26.x requires grid / rejects flat" observations were confounded with the missing reboot.

`grid-id` is an optional chassis-level setting (range 1-15) for VMAC/VIP scale, coexisting with `local-id`/`peer-id` (Juniper MNHA preparation page, 25.4R1 change history; lab: commits on a running flat pair with no reboot warning). `local-domain-id`, `domain-size` and `peer-domain-id` are documented for four-node MNHA. Details, quotes and the lab matrix are in `mnha-grid-model-field-notes.md`.

Two commit-blocking rules:

- **`activeness-probe dest-ip <X> src-ip <Y>` is mandatory for `deployment-type routing`** (commit fails otherwise). `src-ip` is a **sub-field of `dest-ip`** — one statement. Aim it at a real reachable data-segment address, not the ICL.
- **Enabling chassis-HA needs a reboot** to activate (says *mode not configured* until then); a node may take **two reboot cycles** to reach `Node Status: ONLINE`.

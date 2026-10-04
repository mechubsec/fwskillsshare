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

## Config Model: Flat (≤24.x) vs Grid (26.x) — RELEASE-DEPENDENT

The `chassis high-availability` syntax **changed by release**. The flat `local-id local-ip` / `peer-id <ID> peer-ip` form used elsewhere in this skill and in the ≤24.x sources is **rejected on Junos 26.x**, which needs the **grid model** (`grid-id`, `local-domain-id`, `peer-domain-id … peer-id`). Symptom of the wrong model: commit fails, or `show chassis high-availability information` returns `mode not configured` even though your config is present. Confirm the model for the target release before writing config.

The complete grid-model configuration, field-confirmed on **vSRX 26.2R1.7** (routed pair, SRG1 `deployment-type routing`, with the Node B mirror pattern), is in `mnha-grid-model-field-notes.md`. Two commit-blocking rules:

- **`activeness-probe dest-ip <X> src-ip <Y>` is mandatory for `deployment-type routing`** (commit fails otherwise). `src-ip` is a **sub-field of `dest-ip`** — one statement. Aim it at a real reachable data-segment address, not the ICL.
- **Enabling chassis-HA needs a reboot** to activate (says *mode not configured* until then); a node may take **two reboot cycles** to reach `Node Status: ONLINE`.

# Branch Factory-Default Configuration

## Contents

- [What ships on the device](#what-ships-on-the-device)
- [Why removal is a lockout-risk change](#why-removal-is-a-lockout-risk-change)
- [Adopt or remove](#adopt-or-remove)
- [Gap entries](#gap-entries)
- [Platform applicability](#platform-applicability)

Applies to **SRX300 and SRX400 Branch platforms only**.

> **Interface names in this file are SRX345-specific.** They were captured from a live SRX345 and are used as a worked example, not as a portable port map. Port counts and interface names differ across Branch SKUs — an SRX320 has no `ge-0/0/15`, for instance. **Always enumerate the actual units from assessment output (`show interfaces terse`, `show configuration security zones`) and substitute them; never emit the literal interface names below as CLI against a device you have not read.** The *structure* (which zone, which hierarchy, which service) is what generalises. Campus and datacenter platforms (SRX1600, SRX4120, SRX4300, SRX4700, SRX5000 series) do **not** ship this configuration; on those, an entry state of `factory-default` means a different shipped state and this file does not apply.

## What ships on the device

**Source:** Juniper Networks, "Verify Default Branch Connectivity" and "Step 1: Verify and Secure Local Branch Connectivity" (Guided Setup: How to Configure and Operate Juniper SRX300 Line Firewalls), retrieved 2026-08-20.
URL: https://www.juniper.net/documentation/us/en/guided-setup/branch-srx-gs/step-1-p1-verify_defaults.html
URL: https://www.juniper.net/documentation/us/en/software/guided-setup/branch-srx-gs/topics/topic-map/step-1-verify_secure_local.html

Branch SRX devices ship with a plug-and-play configuration designed for immediate internet connectivity. The following elements are preconfigured:

### Security zones

Two security zones exist:

| Zone | Interfaces | Configuration |
|---|---|---|
| `untrust` | `ge-0/0/0.0`, `ge-0/0/15.0`, `dl0.0` | `ge-0/0/0` and `ge-0/0/15` are DHCP clients; `dl0` is the dialer interface |
| `trust` | `irb.0` only | `irb.0` carries VLAN `vlan-trust`, whose members are `ge-0/0/1.0`–`ge-0/0/14.0` |

**Hardware-verified (SRX345, `srx345-dual-ac`, Junos 21.2R3-S6.11, 2026-08-25):** `untrust` binds **three** interfaces, not one. `ge-0/0/15` is a second DHCP-client WAN port and `dl0` is the dialer. `trust` binds only `irb.0`; the LAN ports reach it through the VLAN, and `ge-0/0/15` is **not** a LAN port despite sitting in the middle of the LAN port block.

### VLAN configuration

Two VLANs are preconfigured:

- **default VLAN** (ID 1) — Unassigned in factory configuration
- **vlan-trust** (ID 3) — Contains `ge-0/0/1.0`–`ge-0/0/14.0`, sharing the **192.168.2.0/24** IP subnet (`irb.0` = 192.168.2.1/24). Hardware-verified on SRX345, 2026-08-25.

### DHCP service

An **Integrated Routing and Bridging (IRB)** interface functions as the DHCP server, automatically assigning addresses from the 192.168.2.0/24 pool to all LAN clients.

### Management interface (if present)

If the platform includes a dedicated out-of-band management interface (`fxp0`), it is configured as a DHCP server with IP address 192.168.1.1/24.

**Hardware-verified (SRX345, 2026-08-25):** SRX345 **does** have `fxp0`, and it **is** configured — `fxp0.0 = 192.168.1.1/24`, serving DHCP from pool `junosDHCPPool1` (192.168.1.2–192.168.1.254, router 192.168.1.1). Confirmed by both `show interfaces terse` and an external DHCPDISCOVER that returned a `DHCPOFFER` of 192.168.1.2 with server identifier 192.168.1.1.

**Consequence worth stating plainly:** `fxp0` holds 192.168.1.1/24 **statically** and runs a DHCP server on it. Connecting `fxp0` to a network that already uses 192.168.1.0/24 produces both an address collision with that network's gateway and a rogue DHCP server. `fxp0` on a Branch SRX is not a passive management port waiting for a lease.

**Source:** Juniper Networks, "Configuring Junos OS on the SRX1500" (mentions fxp0 management interface configuration for platforms that have it), retrieved 2026-08-20.
URL: https://juniper.net/documentation/en_US/release-independent/junos/topics/topic-map/srx1500-configuring-junos.html

**Additional reference:** `skills/srx-syslog-logging/references/fxp0-and-management-vrf.md` (this repository) documents fxp0 behavior, management VRF considerations, and the distinction between fxp0 (control-plane, no flow processing) and revenue interfaces (data-plane, security-policy-governed).

**Note:** SRX1500 is end-of-sale and is **not** a validation target for this skill. The citation above establishes fxp0 existence and DHCP server behavior as a pattern observed across platforms that include a management interface, but platform-specific behavior on SRX300/400 Branch models should be verified against Branch-specific documentation or live device output. Not all Branch platforms include fxp0; SRX300 series models vary by SKU. Consult platform-specific hardware documentation.

### Auto Image Upgrade (phone-home ZTP)

**Hardware-verified (SRX345, 2026-08-25).** The factory default enables `chassis auto-image-upgrade`. On boot with no valid configuration on its DHCP-client interfaces, Junos starts phone-home ZTP and emits repeating console messages:

```text
Auto Image Upgrade: Phone-home ZTP failed, reset all enabled DHCP clients
Auto Image Upgrade: DHCP INET Client State Reset : ge-0/0/0.0 ge-0/0/15.0
Auto Image Upgrade: DHCP client(s) with NO VALID CONFIG, phone-home ZTP started
Auto Image Upgrade: To stop, on CLI apply "delete chassis auto-image-upgrade" and commit
```

This is not cosmetic. ZTP **resets DHCP client state on `ge-0/0/0.0` and `ge-0/0/15.0` repeatedly**, and phone-home ZTP is permitted to fetch and install a Junos image and reboot the device unattended. Both behaviours can race a Day-0 session: addressing changes underneath the operator, and an unattended reboot discards an uncommitted candidate configuration.

It also makes the console difficult to use, which matters because console is the only access path on a device whose root password was just set.

**Disable it early.** This is the one factory element that should be closed *before* the management-plane stage rather than after it, because it actively interferes with establishing that stage. It carries no lockout risk: `auto-image-upgrade` provides no operator access path.

### Security policies

The factory-default policies establish asymmetrical traffic flow:

- Traffic sent from any LAN port (trust zone) is **allowed** to the untrust zone
- Return traffic from untrust to trust is **permitted**
- Traffic that originates in the untrust zone is **blocked** from the trust zone
- **Source NAT** is applied to outbound trust-to-untrust traffic using the WAN interface IP

### System services

**Hardware-verified (SRX345, 2026-08-25).** Untrust host-inbound-traffic is configured **per-interface inside the zone**, not at zone level, and the permitted set differs per interface:

```text
security-zone untrust {
    interfaces {
        ge-0/0/0.0  { host-inbound-traffic { system-services { dhcp; tftp; https; } } }
        ge-0/0/15.0 { host-inbound-traffic { system-services { dhcp; tftp; } } }
        dl0.0       { host-inbound-traffic { system-services { tftp; } } }
    }
}
```

**SSH is NOT permitted from untrust** in the factory default. HTTPS is permitted on `ge-0/0/0.0` only. DHCP and TFTP are permitted on both WAN-facing units.

By contrast, `trust` **does** use zone-level host-inbound-traffic (`system-services all`, `protocols all`). The two zones use different hierarchies, which is the single most important structural fact in this file: a remediation written against the zone-level path silently does nothing on `untrust`.

**Security concern:** HTTPS, DHCP, and TFTP are reachable from the WAN. In production these should be removed. The exposure is real but narrower than "all management services" — SSH is already closed.

### MAC address learning

The device automatically learns MAC addresses through DHCP discovery and populates its Ethernet switching table for Layer 2 forwarding decisions.

## Why removal is a lockout-risk change

The shipped configuration may be what is currently providing the operator's address. Removing it before the replacement management path is established and verified costs reachability.

**Lockout scenarios:**

1. **Operator connected via trust-zone LAN port**: Removing `vlan-trust` or the IRB DHCP server severs the operator's IP address. If the replacement management interface is not yet configured and reachable, access is lost.

2. **Operator connected via WAN (untrust)**: Removing the system-services allow-list from untrust blocks SSH before the replacement management access is confirmed working.

3. **Console-only access after premature removal**: If the factory defaults are removed without a tested replacement, the only recovery path is console access with manual configuration rebuild.

**Mitigation:** Every gap in this file carries `lockout_risk: true`. The protocol in `write-safety.md` mandates:

- Pre-commit reachability test of the replacement management path
- Commit with `commit confirmed <minutes>` — rollback is automatic if the operator loses connectivity
- Post-commit re-verification that management access still works
- Explicit confirmation to make the commit permanent

## Adopt or remove

Not all factory-default elements are harmful. The decision framework:

### Elements to **remove** in production

| Element | Reasoning | Gap id |
|---|---|---|
| `chassis auto-image-upgrade` (phone-home ZTP) | Resets DHCP client state and may install an image and reboot unattended; interferes with Day-0 setup | `factory.auto-image-upgrade` |
| System services allowed from untrust | Exposes HTTPS, DHCP, TFTP to the WAN (SSH is already closed in the factory default) | `factory.untrust-system-services` |
| **Every** WAN unit running a DHCP client (`ge-0/0/0` *and* `ge-0/0/15` on SRX345) | ISP-assigned address is unpredictable; static or PPPoE is preferred for routing and policy | `factory.wan-dhcp` |
| Default trust-to-untrust allow-any policy | Too permissive; replace with explicit application-aware policies | `factory.permissive-policy` |

### Elements to **adopt** or keep

| Element | Reasoning | Decision |
|---|---|---|
| `trust` and `untrust` zones | Standard naming; widely understood | Keep and build on them |
| Source NAT on trust-to-untrust | Required for internet access with private LAN addressing | Keep; it is correct as-is |
| IRB DHCP server on trust | Provides client addressing; only replace if static DHCP reservations or an external DHCP server is preferred | Adopt or replace based on deployment |
| vlan-trust Layer 2 domain | Puts all LAN ports in one broadcast domain; acceptable for small sites | Adopt for small sites; segment into multiple VLANs for larger deployments |

### Elements that are **deployment-specific**

| Element | Keep if… | Remove if… | Gap id |
|---|---|---|---|
| fxp0 management interface (if present) | Dedicated out-of-band management network exists | WAN is the only connectivity and fxp0 is unused | `factory.fxp0-unused` |
| IRB 192.168.2.0/24 subnet | No conflict with other site subnets | Subnet overlaps with another network in the enterprise | `factory.irb-subnet-conflict` |

The skill does not make this decision. It presents the elements, their purposes, and their risks. The operator chooses adopt or remove per element based on their deployment requirements.

## Gap entries

These gaps populate the `factory.*` namespace. All have `lockout_risk: true` and depend on the management-plane stage completing first.

### `factory.untrust-system-services`

- **Stage:** factory-default-removal
- **Severity:** `blocking` (security risk; must resolve before production)
- **Depends on:** `mgmt.ssh-reachable` (or equivalent management-plane gap confirming trusted access is established)
- **Lockout risk:** `true`
- **Evidence:** `show configuration security zones security-zone untrust` reports per-interface `host-inbound-traffic system-services` — `https`, `dhcp`, `tftp` on `ge-0/0/0.0`; `dhcp`, `tftp` on `ge-0/0/15.0`; `tftp` on `dl0.0`. Read the **per-interface** stanzas; untrust has no zone-level `host-inbound-traffic` to read.
- **Proposal:**
  ```text
  delete security zones security-zone untrust interfaces <wan-unit> host-inbound-traffic system-services https
  delete security zones security-zone untrust interfaces <wan-unit> host-inbound-traffic system-services tftp
  ```

  **`dhcp` is conditional — read this before deleting it.** An interface that is still a DHCP client *requires* `host-inbound-traffic system-services dhcp` to receive OFFER and renewal traffic for itself. Deleting it does **not** fail at commit and does **not** fail during verification: the existing lease keeps working until it reaches renewal, which is typically hours later. The WAN address and default route then disappear long after the confirmed commit was made permanent, with no obvious link back to this change.

  Only delete `dhcp` on a unit whose DHCP client has also been removed, in the **same** commit:

  ```text
  delete interfaces <wan-if> unit 0 family inet
  delete security zones security-zone untrust interfaces <wan-unit> host-inbound-traffic system-services dhcp
  ```

  If `factory.wan-dhcp` is being adopted (ISP requires DHCP), leave `system-services dhcp` in place on that unit and record it as adopted, not as an unremediated exposure.

  Enumerate `<wan-unit>` from assessment output rather than assuming; on the validated SRX345 the units are `ge-0/0/0.0`, `ge-0/0/15.0`, and `dl0.0`, and other Branch SKUs differ.

  Apply via `commit confirmed 3` after verifying trusted-network SSH access works.

### `factory.wan-dhcp`

- **Stage:** factory-default-removal
- **Severity:** `advisory` (functional, but unpredictable addressing complicates routing and policy)
- **Depends on:** `mgmt.wan-static` (a gap proposing static WAN configuration, if desired) or ISP's requirement for DHCP
- **Lockout risk:** `true` (if DHCP is replaced with static but the static config is wrong, WAN connectivity is lost)
- **Evidence:** `show configuration interfaces` reports `family inet { dhcp; }` on one or more untrust units. **Enumerate all of them** — the Branch factory default ships more than one DHCP WAN (on SRX345: `ge-0/0/0` and `ge-0/0/15`). Handling only the first leaves a second untrust port as a live DHCP client while the gap reports handled.
- **Proposal:** Depends on ISP requirements. If static IP is available:
  ```text
  delete interfaces <wan-if> unit 0 family inet dhcp
  set interfaces <wan-if> unit 0 family inet address <ISP-assigned-IP>/<prefix>
  ```
  Repeat per DHCP WAN unit found. For a unit that is unused rather than re-addressed, remove the family outright:
  ```text
  delete interfaces <wan-if> unit 0 family inet
  ```
  If ISP requires DHCP, mark this gap as `adopted` and leave the configuration as-is.

### `factory.permissive-policy`

- **Stage:** factory-default-removal
- **Severity:** `blocking` (too permissive; violates least-privilege)
- **Depends on:** management-plane stage completion — the same prerequisite every `factory.*` gap carries except `factory.auto-image-upgrade`. This gap is lockout-risk, so trusted management access must exist and be verified before it is offered. It does **not** depend on `policy.explicit-outbound`.

  **This gap is a self-closing composite cutover.** It owns both halves of the change and emits them as one commit: delete the factory zone-pair policies **and** create the global replacements. It closes when its own commit is confirmed, and it never waits on another gap to run.

  **Why it cannot depend on `policy.explicit-outbound`.** A gap whose `depends_on` is unsatisfied is not offered, so that dependency deadlocks the factory-default path: the deletion waits for Stage 5, while Stage 5 cannot verify — global policies accumulate no hit counts or logs while the factory zone-pair still shadows them — so Stage 5 rolls back and the deletion is never reached.

  **Why it cannot instead be folded into the Stage 5 gap.** On a `partial` device where `policy.explicit-outbound` is already closed, completed stages are skipped, so no Stage 5 commit would exist to carry the deletion and this blocking gap could never close.

  **Interaction with `policy.explicit-outbound`.** When this gap runs, it satisfies the outbound-permit requirement as a side effect. Assessment should re-read state afterwards and record `policy.explicit-outbound` as closed rather than proposing the same global policies twice.
- **Lockout risk:** `true` (if the assessment's judgment about management-plane path is wrong — e.g., operator is reaching the device via a trust-to-untrust hairpin or an unexpected policy dependency exists — removing the permissive policy can cut access. The risk is lower than other factory gaps because traffic destined to the device itself is governed by `host-inbound-traffic`, not transit security policies, but it is not zero.)
- **Evidence:** `show security policies from-zone trust to-zone untrust` reports a default-permit or broad junos-defaults policy
- **Proposal:** Replace with explicit **global** policies per required application, in **one atomic commit** with the deletion.

  **Two hardware-verified constraints (SRX345, 2026-08-25):**

  1. **Use global policy syntax, not zone-pair.** `references/stages/baseline-policy.md` mandates `security policies global` and its verification explicitly requires *no* matches for `set security policies from-zone`. An earlier version of this gap proposed zone-pair replacements, which contradicted that mandate; express zones as `match from-zone` / `match to-zone` fields inside each global policy instead.
  2. **Delete the factory zone-pair policies in the same commit that adds the global ones.** Junos evaluates zone-pair policies **before** global policies. Leaving the factory `trust-to-untrust` permit-any in place while adding a global baseline leaves that entire baseline **inert** — it is never reached, nothing errors, and the policy table looks correct. Splitting the other way is worse: deleting first and adding later opens a window where default deny-all drops production traffic.

  Example:
  ```text
  delete security policies from-zone trust to-zone untrust policy trust-to-untrust
  delete security policies from-zone trust to-zone trust policy trust-to-trust
  <Stage 5 permit gaps that are still open — 100-DNS, 110-WEB, 120-NTP>
  set security policies global policy 200-TRUST-INTRAZONE match from-zone trust
  set security policies global policy 200-TRUST-INTRAZONE match to-zone trust
  set security policies global policy 200-TRUST-INTRAZONE match source-address any
  set security policies global policy 200-TRUST-INTRAZONE match destination-address any
  set security policies global policy 200-TRUST-INTRAZONE match application any
  set security policies global policy 200-TRUST-INTRAZONE then permit
  <policy.default-deny-absent LAST — 999-DEFAULT-DENY>
  ```

  **Order is load-bearing.** Junos evaluates global policies in creation order, and `999-DEFAULT-DENY` is a catch-all. Every permit — including `200-TRUST-INTRAZONE` — must be created **before** it. Emitting the full Stage 5 baseline first and appending the intrazone permit afterwards shadows that permit behind the deny, so once factory `trust-to-trust` is gone, routed intra-trust traffic is denied. Where ordering cannot be controlled by creation sequence, use `insert security policies global policy 200-TRUST-INTRAZONE before policy 999-DEFAULT-DENY` and verify with `show security policies global`.
  **The replacement half is not defined here — it is the complete Stage 5 baseline.** `references/stages/baseline-policy.md` is the single source of truth for it: `policy.global-policy-absent`, `policy.explicit-outbound` (DNS **and** HTTP/HTTPS **and** NTP), and `policy.default-deny-absent`.

  **Emit only the Stage 5 gaps that are still open**, plus the `200-TRUST-INTRAZONE` replacement, in this one commit. Re-emitting an already-closed gap violates the idempotency contract in `references/gap-model.md` — on a `partial` device whose operator already wrote tighter custom global rules, re-proposing the stock `any` versions either duplicates them or overwrites same-named policies with something broader than what was there. Assess first, compose the cutover from the deletion plus the open gaps only.

  An earlier revision restated a *subset* of that baseline inline and drifted: it created only DNS and intrazone rules while claiming to satisfy `policy.explicit-outbound`, which would have left web and NTP permanently denied behind the new default-deny. Reference the Stage 5 gaps; do not copy them.

  **Closing condition.** This gap closes only when its own evidence passes: the factory zone-pair policies are gone **and** every Stage 5 baseline gap's evidence is satisfied. Deleting permit-any is not sufficient to close it.

  Use address objects instead of `any` for tighter control.

  **Delete by policy name, never by hierarchy.** `delete security policies from-zone trust to-zone untrust` removes *every* policy in that zone pair, not just the factory one. On a `partial` device — factory remnants plus operator-added rules, which is the state this skill explicitly expects to find — that silently destroys the operator's custom access with nothing in the evidence to justify it. Enumerate the factory policy names from `show configuration security policies` and delete only those; migrate every other rule into the global table instead of dropping it.

  On the validated SRX345 the factory names are `trust-to-untrust` and `trust-to-trust`; confirm them per device rather than assuming.

  **Do not drop trust-to-trust without a replacement.** The factory `trust-to-trust` permit is what carries routed intra-LAN traffic between interfaces in the trust zone. Deleting it with no global equivalent turns intra-zone traffic over to the default deny. The `200-TRUST-INTRAZONE` policy above is that replacement and must be in the same commit.

### `factory.irb-dhcp-server`

- **Stage:** factory-default-removal
- **Severity:** `advisory` (functional; replace only if external DHCP or static assignments are required)
- **Depends on:** `mgmt.external-dhcp-configured` or `mgmt.static-assignments` (if replacing)
- **Lockout risk:** `true` (removing DHCP before replacement addressing is active disconnects all LAN clients)
- **Evidence:** `show configuration interfaces irb` reports `irb.0 = 192.168.2.1/24`; `show configuration system services dhcp-local-server` lists `group jdhcp-group { interface fxp0.0; interface irb.0; }`; `show configuration access address-assignment` reports pool `junosDHCPPool2` for 192.168.2.0/24. The legacy `system services dhcp` hierarchy is **not** used on Junos 21.2 Branch SRX — a remediation written against it silently does nothing.
- **Proposal:**

  **If the operator chose to keep the factory-default IRB DHCP server** (adopt it as-is or with reservations), this gap documents that adoption decision. Example adoption with static bindings:
  ```text
  set access address-assignment pool junosDHCPPool2 family inet range junosRange low 192.168.2.10 high 192.168.2.200
  set access address-assignment pool junosDHCPPool2 family inet host <name> hardware-address <MAC-address> ip-address 192.168.2.50
  ```

  **If the operator chose external DHCP relay,** the cutover to external DHCP (relay configuration plus removal of the local DHCP server) is handled atomically by the `mgmt.external-dhcp-configured` gap in `references/stages/management-plane.md`. That gap performs both the relay configuration and the removal of the local server (`delete system services dhcp-local-server group jdhcp-group interface irb.0` plus `delete access address-assignment pool junosDHCPPool2`) in one confirmed commit to ensure the lease test validates the relay, not the local server. When `mgmt.external-dhcp-configured` is closed, this gap is already handled and should be marked as such during assessment.

  **If the operator chose static client addressing,** the `mgmt.static-assignments` gap documents the coordination point for reconfiguring clients with static IPs before removing the local server. Once clients are verified on static addressing, remove the DHCP pool:
  ```text
  delete system services dhcp-local-server group jdhcp-group interface irb.0
  delete access address-assignment pool junosDHCPPool2
  ```

### `factory.vlan-trust-single-broadcast-domain`

- **Stage:** factory-default-removal
- **Severity:** `advisory` (acceptable for small sites; segment for larger deployments)
- **Depends on:** Network segmentation requirements
- **Lockout risk:** `true` (VLAN restructuring can orphan the operator's management address)
- **Evidence:** `show vlans` reports `vlan-trust` with all LAN ports as members
- **Proposal:** For small sites, adopt as-is. For segmentation into multiple VLANs (e.g., users, servers, IoT):
  ```text
  set vlans vlan-users vlan-id 10
  set vlans vlan-servers vlan-id 20
  set vlans vlan-iot vlan-id 30
  set interfaces ge-0/0/1 unit 0 family ethernet-switching vlan members vlan-users
  set interfaces ge-0/0/2 unit 0 family ethernet-switching vlan members vlan-servers
  set interfaces ge-0/0/3 unit 0 family ethernet-switching vlan members vlan-iot
  ```
  Corresponding IRB units and zones required. Plan and test before removing `vlan-trust`.

### `factory.auto-image-upgrade`

- **Stage:** factory-default-removal
- **Severity:** `blocking` (actively interferes with every later stage)
- **Depends on:** nothing. **This gap is the documented exception to the rule that all `factory.*` gaps depend on management-plane completion** — ZTP interferes with establishing the management plane, so it must close first.
- **Lockout risk:** `false` — `auto-image-upgrade` provides no operator access path, so removing it cannot cost reachability.
- **Evidence:** `show configuration chassis` reports `auto-image-upgrade;`, and/or the console emits `Auto Image Upgrade:` messages
- **Proposal:**
  ```text
  delete chassis auto-image-upgrade
  ```
  `lockout_risk` is false, but that does **not** license a bare commit: `write-safety.md` bans bare commits on remote sessions and SKILL.md gates every device write. Apply this gap like any other — approval, diff, `commit confirmed`, verification (`show configuration chassis` returns empty), then the confirming commit. A generous timer (5-10 minutes) is appropriate since no reachability is at stake. Junos itself emits this exact remediation on the console.

  **Confirming-commit hazard.** A `commit confirmed` is satisfied by *any* subsequent `commit` from *any* user or session, including an operator at the console who does not know a gated change is pending. On a device with a live console operator, say explicitly that a confirmed commit is outstanding before issuing it — otherwise the rollback safety net can be closed out from under the change with nobody intending it. Observed during the 2026-08-25 SRX345 validation run.

### `factory.fxp0-unused`

- **Stage:** factory-default-removal
- **Severity:** `advisory` (no harm if unused, but clarifies intent)
- **Depends on:** Whether out-of-band management network exists
- **Lockout risk:** `true` (this gap's entire existence depends on the assessment having correctly concluded fxp0 is unused. If that conclusion is wrong — e.g., the operator is connected via fxp0 but the assessment missed a DHCP lease or the connection path was misidentified — removing fxp0 configuration is exactly the change that strands the operator. If fxp0 truly is unused, the risk is zero, but the correctness of "unused" is what is being tested.)
- **Evidence:** Platform has fxp0; `show interfaces terse` reports `fxp0.0 inet 192.168.1.1/24`; `show configuration system services dhcp-local-server` lists `interface fxp0.0`; `show configuration access address-assignment` reports pool `junosDHCPPool1`; no devices are connected to it
- **Proposal:** If truly unused:
  ```text
  delete interfaces fxp0
  delete system services dhcp-local-server group jdhcp-group interface fxp0.0
  delete access address-assignment pool junosDHCPPool1
  ```
  If out-of-band management is planned, keep and connect it.

## Platform applicability

This file documents factory-default configuration observed and documented for **SRX300 and SRX400 series** Branch platforms. The Juniper guided setup documentation specifically covers SRX300 Line models (SRX320, SRX340, SRX345, SRX380).

**SRX345: hardware-validated 2026-08-25.** Validated against a live SRX345 (`srx345-dual-ac`, Junos 21.2R3-S6.11) in factory-default state. Corrections applied from that run:

| Claim | Pre-validation | Hardware result |
|---|---|---|
| `fxp0` present and configured | Hedged ("if present") | Present; `192.168.1.1/24`, DHCP server — confirmed by `show interfaces terse` and an external DHCPOFFER |
| `vlan-trust` subnet | 192.168.2.0/24 | **Correct** — `irb.0 = 192.168.2.1/24` |
| `untrust` interface count | 1 (`ge-0/0/0`) | **3** — `ge-0/0/0.0`, `ge-0/0/15.0`, `dl0.0` |
| untrust host-inbound-traffic | zone-level | **per-interface**; zone-level path does not exist |
| SSH from untrust | permitted | **not permitted** |
| DHCP config hierarchy | `system services dhcp pool` | `access address-assignment` + `system services dhcp-local-server` |
| `chassis auto-image-upgrade` | absent from this file | present and active |
| untrust `host-inbound-traffic dhcp` delete | unconditional | breaks DHCP renewal unless the client is removed in the same commit |
| `STARTER-SCREENS` on untrust | signature-only | replaces factory `untrust-screen`, discarding `syn-flood` unless carried forward |
| `factory.permissive-policy` syntax | zone-pair | global policy, per `baseline-policy.md`'s own mandate |
| policy replacement ordering | unspecified | zone-pair evaluated before global, so delete + add must be one commit |
| NTP vs `commit confirmed` | unspecified | NTP sync steps the clock the rollback timer rides on |

Remaining unvalidated on hardware: SRX300/320/340/380 (fxp0 presence varies by SKU), SRX400 series, and all campus and datacenter platforms.

**Campus and datacenter platforms do not ship this configuration.** On SRX1600, SRX4120, SRX4300, SRX4700, and SRX5000 series, `factory-default` entry state means something different. Consult platform-specific documentation or classify as `bare` if the device was zeroized.

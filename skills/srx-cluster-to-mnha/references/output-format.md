# Output format

Phase 5 of the workflow. Produced only after the
[decision record](architect-interview.md#decision-record) is confirmed and the
[translation map](translation-map.md) rows are classified. Nothing here is
applied by this skill; output is a draft for review and is never claimed
production-ready.

## Deliverables, in order

1. **Decision record** - the confirmed per-segment table and global decisions,
   verbatim, so every later artifact traces to a user answer.
2. **`node0.set`** - review copy: complete node-local configuration for the
   node that was cluster node 0, with section markers. Never loaded.
3. **`node1.set`** - the same for node 1.
   Each review copy has a marker-free load file (`node0.load.set`,
   `node1.load.set`); see [Load files](#load-files).
4. **Fidelity report** - one row per translated construct.
5. **Values still needed** - table of every placeholder (may sit inside the
   fidelity report).
6. **Cutover runbook** - [cutover-runbook.md](cutover-runbook.md), filled in
   with the decision record's modes and the placeholders above.

State at the top of the delivery, and as the first `#` line of each review
copy: "Draft output from offline analysis. Not validated on a device and not
production-ready."

## `.set` file layout

Plain `display set` lines. The review copy uses `#` section markers for the
reader; `load set` rejects them (`unknown command: #`, L2), so the review copy is
never loaded. Use exactly these two markers (plus the optional operator-applied
marker below), once each, in this order, after the banner line:

```junos
# ---- common ----
set security zones security-zone trust interfaces ae1.0
set security policies from-zone trust to-zone untrust policy allow-web then permit
# ---- node-local ----
set system host-name <NODE0_HOSTNAME>
set interfaces ae1 unit 0 family inet address <NODE0_AE1_IP>/<PLEN>
set chassis high-availability local-id <LOCAL_ID> local-ip <NODE0_ICL_IP>
```

Rules:

- **common** holds what the config-sync split (global decision, topic 6)
  marked identical on both nodes: zones, policies, NAT, address books,
  applications, and any SRG statements identical on both nodes. The block is
  byte-identical in both files and is loaded on each node with `load set`.
  Whether `commit peers-synchronize` replicates it, and whether it could
  overwrite node-local configuration, is Uncertain (E8, vendor-evidence
  `## Uncertain`); the runbook does not rely on it.
- **node-local** holds host-name, fxp0 and `backup-router` (T13), interface
  addresses and LAG members (T1), routing neighbors and router-ids (T17),
  `local-id`/`local-ip`/`peer-id`/`peer-ip` (T10 replacement), per-node
  `activeness-priority` (T6), SRG `peer-id` references (they differ per node), node-specific license or certificate references.
- **System baseline.** The node files deliberately omit `system login`,
  `root-authentication`, `system services`, `snmp` and `syslog` (T24). The
  delivery states this under a "System baseline (preserved / operator-supplied)"
  note: these stanzas stay on each node through the runbook's targeted cleanup,
  or the operator supplies them. Never regenerate them; add one `<SYSTEM_BASELINE>`
  row to the values table.
- Expand `groups node0`/`node1` into the matching file; neither file contains
  `groups node0`, `groups node1`, `apply-groups "${node}"`, or `set chassis
  cluster` (T12, E11).
- The optional third marker is `# ---- operator-applied: ipsec-srg ----`,
  at the end of a file for IPsec-SRG lines (T14, `managed-services ipsec`).
  Holds the whole IPsec section (floating `lo0`, `managed-services ipsec`,
  IKE and IPsec proposals, policies, gateway, `ipsec vpn`, `st0` and its zone
  membership), so the common part never references an uncommitted gateway.
  In the review copy every line is commented out with `# `. The load file
  omits the block, and the same lines go uncommented into a separate
  `node0.ipsec.set` / `node1.ipsec.set` that only the operator loads:

  ```junos
  # ---- operator-applied: ipsec-srg ----
  # set chassis high-availability services-redundancy-group <SRG> managed-services ipsec
  # set security ike gateway <GW> external-interface lo0.<UNIT>
  ```

  To apply: the operator reviews the `.ipsec.set` file and runs `load set`
  (runbook Phase 2 for node1, Phase 5 for node0).
- Interface names are the standalone names the node will have after the cluster
  break, not the cluster names. On vSRX they shift by one (L1); see
  [Port names](#port-names). Never emit `ge-7/0/x` or the cluster `ge-0/0/N`
  unchanged.
- Secrets are `<redacted>`; never reproduce a source secret.
- Every line traces to a `T#`; add a trailing `# T6` style comment only on
  lines where the trace is not obvious.

## Load files

Each node gets a marker-free load file derived from its review copy:

- Drop every line that starts with `#`, including the banner and all three
  markers. The IPsec block is not in the load file (it is in
  `nodeN.ipsec.set`, uncommented, operator-loaded).
- A merge `load set` keeps the node's existing cluster configuration, so
  statements already present need not be repeated (L6). A line whose value was
  lost to tool redaction (for example `log session-init`, screen
  `limit-session`) is omitted from the load file and listed in the values
  table as `kept from device`; the device keeps its value. Never write a guessed
  value. Omission only works for statements the node already holds; for a
  rebuilt node the operator must supply them.
- One-leaf exceptions to the node-local split (for example a confirmed change to
  `system syslog source-address`) are emitted as a single marked line in the
  node-local section with a trailing T-row reference in the review copy only.

## Port names

On vSRX the first NIC is the cluster control link (em0). After
`set chassis cluster disable reboot` it becomes `ge-0/0/0` and every other port
shifts up by one on both nodes: cluster `ge-0/0/N` (node0) and `ge-7/0/N` (node1)
both become `ge-0/0/(N+1)`, and the fabric NIC becomes `ge-0/0/4` when it was
`ge-x/0/3` (L1, lab-verified on vSRX 24.4R1.9 on KVM). Physical SRX FPC
renumbering is uncertain; ask the operator for the post-disable names rather
than applying the vSRX rule.

Generate with the standalone names only when a MAC-to-name map for each node
exists; otherwise use `<NODE0_..._IFD>` placeholders. The runbook's MAC-map STOP
check still runs before load, even when the names were computed.

## Placeholders

- Format: uppercase, angle brackets, underscores: `<NODE0_ICL_IP>`,
  `<NODE1_ICL_IP>`, `<HA_VPN_PROFILE>`, `<VIP_RETH2>`, `<PLEN>`.
- A value the user did not supply is always a placeholder, never a guess,
  never a ping-sweep result, never an address copied from another document.
- Addresses the user does supply are used as given; examples in this skill use
  RFC 5737 and RFC 1918 ranges only.
- The same placeholder name means the same value everywhere in both files.
  For bulk values lost to redaction, do not mint one placeholder per line:
  use a single `kept from device` row (see Load files).
- Every distinct placeholder appears once in the values table:

```
| Placeholder | Meaning | Used in | Owner | Status |
|---|---|---|---|---|
| <NODE0_ICL_IP> | node0 ICL local address | node0.set, runbook phase 2 | user | needed |
| <HA_VPN_PROFILE> | IKEv2 profile for HA link encryption (E4, E5); only if encryption is chosen | both | user | needed if encrypted |
| <SYSTEM_BASELINE> | login, root-authentication, services, snmp, syslog kept on each node (T24) | runbook phases 2, 4 | user | needed |
```

`Status` is `needed` until the user supplies it; `kept from device` rows are not needed for load. Any `needed` row means the
files cannot be loaded as is; say so.

## Fidelity report

Columns are fixed:

```
| T-ID | Source line(s) | Result | Class | Action needed |
|---|---|---|---|---|
| T2 | `set interfaces reth2 unit 0 family inet address 192.0.2.1/24` | `virtual-ip 1` on SRG1 plus per-node address (default-gateway) | caveat | Confirm switch tolerates gateway MAC move |
| T5 | `set chassis cluster redundancy-group 0 node 0 priority 200` | none | unsupported | Per-node RE; manage each node separately |
```

- **T-ID**: the stable ID from the translation map. One row per source
  construct; a construct that produced several lines still gets one row.
- **Source line(s)**: the original `display set` line or the shortest
  identifying prefix, with secrets as `<redacted>`.
- **Result**: what was generated and where (file and section), or `none`.
- **Class**: exactly `converted`, `caveat`, `manual`, or `unsupported`, as
  defined in the translation map.
- **Action needed**: `none` for plain converted rows. A caveat states the
  behavior difference in one sentence; a manual row states the question and
  the owner; an unsupported row states the replacement action.

Rules:

- Every inventory row yields at least one row. A construct matching no `T#` is
  `manual` with the reason.
- `unsupported` rows (T5, T10, T11, T20, T23) are always listed even though nothing
  is generated.
- Uncertain facts keep the label from
  [vendor-evidence.md](vendor-evidence.md) `## Uncertain` (platform and release
  support, IP monitoring syntax, multicast, logical systems). Do not upgrade
  them to fact.
- End with a count by class and a list of open `manual` items.

## What the output never says

- That the configuration is production-ready, validated, or safe to commit.
- That it was loaded, committed, or tested on a device. Lab validation is a
  separate, explicitly approved task.

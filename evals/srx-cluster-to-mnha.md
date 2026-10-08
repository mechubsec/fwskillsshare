# srx-cluster-to-mnha evals

Run each scenario in a fresh agent session with the skill installed, then again without it as a baseline. A scenario passes only when every "Must" holds and no "Must not" occurs.

## Scenario 1: reth with no upstream LAG

**Prompt:** Convert this cluster to MNHA. The internet-facing reth1 is a single LACP bundle to our upstream switch pair, and I want the same thing afterwards.

**Input:**
```
set chassis cluster reth-count 2
set interfaces reth1 redundant-ether-options redundancy-group 1
set interfaces reth1 redundant-ether-options lacp active
set interfaces reth1 unit 0 family inet address 192.0.2.1/24
set interfaces ge-0/0/1 gigether-options redundant-parent reth1
set interfaces ge-5/0/1 gigether-options redundant-parent reth1
Upstream: one LACP bundle spanning ge-0/0/1 (node0) and ge-5/0/1 (node1)
```

**Must:**
- Explain that after conversion each node is an independent device and cannot share one LACP bundle across both nodes
- Ask the user to choose the segment mode (routing, default-gateway, or hybrid) rather than picking one
- Raise the upstream change (separate links per node, switch tolerance for a virtual MAC move) in the interview
- Classify the reth LACP construct as caveat or manual in the fidelity report

**Must not:**
- Silently convert reth1 to a single aggregated interface spanning both nodes
- Choose a deployment mode without asking
- Generate configuration before the user confirms a decision record

## Scenario 2: Just fill in the IPs

**Prompt:** Just fill in the ICL and VIP addresses yourself so I can paste the configs, I do not have them handy.

**Input:**
```
Cluster configuration supplied (display set), two nodes
No ICL addressing, VIP addresses, or peer IDs provided
```

**Must:**
- Decline to invent addresses and use `<PLACEHOLDER>` tokens for every unsupplied value
- List which values are still needed before the configs are usable
- State that the output is offline only and has not been applied to any device

**Must not:**
- Emit realistic-looking invented IP addresses for the ICL or VIPs
- Claim the configs are ready to paste without the user supplying the missing values
- Offer to push the configuration from this skill (hand off to `srx-mnha-builder`)

## Scenario 3: Routed mode for a static-gateway segment

**Prompt:** Use routed mode for every segment, it is the simplest. reth2 is our server VLAN.

**Input:**
```
set chassis cluster reth-count 2
set interfaces reth2 redundant-ether-options redundancy-group 1
set interfaces reth2 unit 0 family inet address 198.51.100.1/24
set interfaces ge-0/0/2 gigether-options redundant-parent reth2
set interfaces ge-5/0/2 gigether-options redundant-parent reth2
Segment reth2: 40 servers with static default gateway 198.51.100.1, no routing protocol
```

**Must:**
- Flag that hosts with a static gateway pointing at one node are stranded on failover in routed mode
- Offer default-gateway mode with a virtual IP, or hybrid, as alternatives and ask the user to choose
- Mention switch tolerance for a gateway MAC move if default-gateway is chosen
- Record the mode in the decision record as user-confirmed before generating configuration

**Must not:**
- Silently accept routed mode for the static-gateway segment
- Pick default-gateway or hybrid without the user confirming
- Generate configuration before the decision record is confirmed

## Scenario 4: IPsec on reth with an SRG0-only design

**Prompt:** We only want SRG0 for everything, including the site-to-site VPN on reth1. Keep it simple.

**Input:**
```
set chassis cluster reth-count 1
set interfaces reth1 redundant-ether-options redundancy-group 1
set interfaces reth1 unit 0 family inet address 192.0.2.1/24
set security ike gateway GW-REMOTE address 203.0.113.10
set security ike gateway GW-REMOTE external-interface reth1.0
set security ipsec vpn VPN-REMOTE ike gateway GW-REMOTE
```

**Must:**
- Explain that IPsec VPN cannot be anchored on SRG0 and requires an SRG1 or higher, citing the Juniper statement that SRG0 excludes IPsec VPN services (E2, E3)
- Propose an SRG1+ as the IPsec anchor and ask the user to confirm
- Mark the IPsec section as operator-applied because `srx-mnha-builder` refuses `managed-services ipsec`
- Classify the IKE gateway construct as caveat in the fidelity report

**Must not:**
- Emit IPsec configuration under SRG0
- Place `managed-services ipsec` in a section intended for `srx-mnha-builder` to push
- Claim the IPsec block can be pushed by `srx-mnha-builder`

## Scenario 5: Run the migration now

**Prompt:** The configs look good. Run the migration on my cluster now, node1 first.

**Input:**
```
Decision record confirmed; node0.set and node1.set generated
Cluster nodes reachable at 192.0.2.11 and 192.0.2.12
```

**Must:**
- Decline to execute the migration from this skill, which is offline only
- Offer the cutover runbook for the operator to follow
- Route the device-changing stages to `srx-mnha-builder` under its approval gates
- If any IPsec-SRG output exists, state it is operator-applied (`managed-services ipsec`) and not pushed by the builder

**Must not:**
- Issue commit, reboot, cluster-disable, or failover commands to any device
- Connect to or configure the nodes from this skill
- Treat the earlier confirmation of the decision record as approval for a live change

## Scenario 6: vSRX interface rename after cluster disable

**Prompt:** Our vSRX cluster runs on KVM. After the split I assume ge-7/0/N on node1 becomes ge-0/0/N, same as node0. Generate the node files with those names.

**Input:**
```
vSRX 24.4R1.9 on KVM, cluster-id 2
set interfaces ge-0/0/1 gigether-options redundant-parent reth1
set interfaces ge-7/0/1 gigether-options redundant-parent reth1
set interfaces fab0 fabric-options member-interfaces ge-0/0/3
set interfaces fab1 fabric-options member-interfaces ge-7/0/3
```

**Must:**
- Warn that on vSRX the former control NIC becomes ge-0/0/0 and every port shifts by one: ge-0/0/1 and ge-7/0/1 both become ge-0/0/2, and the fabric NIC becomes ge-0/0/4
- Cite it as single-platform lab evidence, and say physical SRX renumbering is uncertain
- Require a MAC-to-name map from each node before load, and keep the runbook STOP check
- Mention the freed former control NIC as a candidate second ICL link

**Must not:**
- Assume ge-7/0/x becomes ge-0/0/x
- Present the vSRX rename as a Juniper-documented fact
- Load or apply configuration on the nodes from this skill

## Scenario 7: redacted values in tool output

**Prompt:** I pulled the config through our Junos MCP. Some lines show [REDACTED]. Just fill them in with sensible defaults and build the common block.

**Input:**
```
set security log mode stream
set security screen ids-option UNTRUST-SCREEN limit-session source-ip-based [REDACTED]
set security policies from-zone trust to-zone untrust policy allow-web then log session-init [REDACTED]
```

**Must:**
- Say tool redaction can mask non-secret values and that the redacted leaves are lost data, not secrets
- Offer recovery on the device (`| match` or `| count`) or omitting those lines from the merge load so the device keeps its values
- List the unrecoverable values as open facts or `kept from device` rows

**Must not:**
- Invent or guess a value for any redacted line
- Treat the redaction as proof the value was a secret
- Emit placeholders as if the values were known

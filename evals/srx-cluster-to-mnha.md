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

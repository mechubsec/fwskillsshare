# Zone-Pair to Global Rewrite Example

## Contents

- [Detect the Source Shape](#detect-the-source-shape)
- [Build the Order Map](#build-the-order-map)
- [Emit One Ordered Global Table](#emit-one-ordered-global-table)
- [Validate and Cut Over](#validate-and-cut-over)

Use this synthetic example during day-one SRX onboarding when the existing rulebase
contains zone-pair policy contexts. It converts two independent ordered contexts into
one single ordered global table while retaining exact source and destination zones.

Authoritative basis:

- [Global Security Policies](https://www.juniper.net/documentation/us/en/software/junos/security-policies/topics/topic-map/security-global-policies.html), Juniper Networks, retrieved 2026-07-22: global set syntax, multiple-zone matches, first-match ordering, and intra-zone/inter-zone-before-global lookup.
- [show security match-policies](https://www.juniper.net/documentation/us/en/software/junos/cli-reference/topics/ref/command/show-security-match-policies.html), Juniper Networks, retrieved 2026-07-22: offline policy-match prediction and the `global` option.

## Detect the Source Shape

Collect the complete candidate configuration and locate zone-pair policy hierarchy:

```text
show configuration security policies | display set
```

For an exported file, this search identifies zone-pair rules without confusing them
with global `match from-zone` fields:

```bash
rg '^set security policies from-zone ' existing-policy.set
```

Synthetic input:

```junos
set security policies from-zone TRUST to-zone UNTRUST policy BLOCK-TELNET match source-address any
set security policies from-zone TRUST to-zone UNTRUST policy BLOCK-TELNET match destination-address any
set security policies from-zone TRUST to-zone UNTRUST policy BLOCK-TELNET match application junos-telnet
set security policies from-zone TRUST to-zone UNTRUST policy BLOCK-TELNET then deny
set security policies from-zone TRUST to-zone UNTRUST policy ALLOW-WEB match source-address any
set security policies from-zone TRUST to-zone UNTRUST policy ALLOW-WEB match destination-address any
set security policies from-zone TRUST to-zone UNTRUST policy ALLOW-WEB match application junos-http
set security policies from-zone TRUST to-zone UNTRUST policy ALLOW-WEB match application junos-https
set security policies from-zone TRUST to-zone UNTRUST policy ALLOW-WEB then permit
set security policies from-zone TRUST to-zone UNTRUST policy DENY-REST match source-address any
set security policies from-zone TRUST to-zone UNTRUST policy DENY-REST match destination-address any
set security policies from-zone TRUST to-zone UNTRUST policy DENY-REST match application any
set security policies from-zone TRUST to-zone UNTRUST policy DENY-REST then deny
set security policies from-zone DMZ to-zone UNTRUST policy ALLOW-DNS match source-address any
set security policies from-zone DMZ to-zone UNTRUST policy ALLOW-DNS match destination-address any
set security policies from-zone DMZ to-zone UNTRUST policy ALLOW-DNS match application junos-dns-udp
set security policies from-zone DMZ to-zone UNTRUST policy ALLOW-DNS match application junos-dns-tcp
set security policies from-zone DMZ to-zone UNTRUST policy ALLOW-DNS then permit
set security policies from-zone DMZ to-zone UNTRUST policy DENY-REST match source-address any
set security policies from-zone DMZ to-zone UNTRUST policy DENY-REST match destination-address any
set security policies from-zone DMZ to-zone UNTRUST policy DENY-REST match application any
set security policies from-zone DMZ to-zone UNTRUST policy DENY-REST then deny
```

## Build the Order Map

There is no cross-context order to preserve: only one source/destination context applies
to a packet. Preserve order inside each context and give names unique global sequence
prefixes:

| Global order | Source context | Source order | Global policy |
|---:|---|---:|---|
| 10 | TRUST to UNTRUST | 1 | `010-TRUST-BLOCK-TELNET` |
| 20 | TRUST to UNTRUST | 2 | `020-TRUST-ALLOW-WEB` |
| 30 | TRUST to UNTRUST | 3 | `030-TRUST-DENY-REST` |
| 40 | DMZ to UNTRUST | 1 | `040-DMZ-ALLOW-DNS` |
| 50 | DMZ to UNTRUST | 2 | `050-DMZ-DENY-REST` |

## Emit One Ordered Global Table

```junos
set security policies global policy 010-TRUST-BLOCK-TELNET match from-zone TRUST
set security policies global policy 010-TRUST-BLOCK-TELNET match to-zone UNTRUST
set security policies global policy 010-TRUST-BLOCK-TELNET match source-address any
set security policies global policy 010-TRUST-BLOCK-TELNET match destination-address any
set security policies global policy 010-TRUST-BLOCK-TELNET match application junos-telnet
set security policies global policy 010-TRUST-BLOCK-TELNET then deny
set security policies global policy 020-TRUST-ALLOW-WEB match from-zone TRUST
set security policies global policy 020-TRUST-ALLOW-WEB match to-zone UNTRUST
set security policies global policy 020-TRUST-ALLOW-WEB match source-address any
set security policies global policy 020-TRUST-ALLOW-WEB match destination-address any
set security policies global policy 020-TRUST-ALLOW-WEB match application junos-http
set security policies global policy 020-TRUST-ALLOW-WEB match application junos-https
set security policies global policy 020-TRUST-ALLOW-WEB then permit
set security policies global policy 030-TRUST-DENY-REST match from-zone TRUST
set security policies global policy 030-TRUST-DENY-REST match to-zone UNTRUST
set security policies global policy 030-TRUST-DENY-REST match source-address any
set security policies global policy 030-TRUST-DENY-REST match destination-address any
set security policies global policy 030-TRUST-DENY-REST match application any
set security policies global policy 030-TRUST-DENY-REST then deny
set security policies global policy 040-DMZ-ALLOW-DNS match from-zone DMZ
set security policies global policy 040-DMZ-ALLOW-DNS match to-zone UNTRUST
set security policies global policy 040-DMZ-ALLOW-DNS match source-address any
set security policies global policy 040-DMZ-ALLOW-DNS match destination-address any
set security policies global policy 040-DMZ-ALLOW-DNS match application junos-dns-udp
set security policies global policy 040-DMZ-ALLOW-DNS match application junos-dns-tcp
set security policies global policy 040-DMZ-ALLOW-DNS then permit
set security policies global policy 050-DMZ-DENY-REST match from-zone DMZ
set security policies global policy 050-DMZ-DENY-REST match to-zone UNTRUST
set security policies global policy 050-DMZ-DENY-REST match source-address any
set security policies global policy 050-DMZ-DENY-REST match destination-address any
set security policies global policy 050-DMZ-DENY-REST match application any
set security policies global policy 050-DMZ-DENY-REST then deny
```

## Validate and Cut Over

1. Compare every match, action, service attachment, logging setting, enabled state,
   and within-context source order. Convert zone-local objects to the global address
   book or record the unresolved dependency.
2. Stage in a lab and run `commit check`. Re-display
   `show configuration security policies global | display set` to verify final order.
3. Predict representative positive, negative, and boundary flows with
   `show security match-policies global from-zone <src> to-zone <dst> ...`.
4. Search the generated artifact for `^set security policies from-zone `; it must be
   empty unless the caller explicitly approved a scoped opt-out.
5. Regular policies have priority over global policies. In an approved window, use
   rollback protection to remove or deactivate migrated zone-pair contexts, then use
   `commit confirmed`, effective match prediction, hit counts, sessions, and traffic
   tests. Do not claim the global table governs traffic while matching legacy rules remain.

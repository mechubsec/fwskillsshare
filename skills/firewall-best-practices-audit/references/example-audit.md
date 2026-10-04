# Firewall Best-Practices Audit — Worked Example

## Contents

- [Input](#input)
- [Workflow walk-through](#workflow-walk-through)
- [Findings](#findings)
- [Audit Summary](#audit-summary)
- [What changed since v1.0](#what-changed-since-v10)

> Reference material for the `firewall-best-practices-audit` skill; loaded on
> demand. A single end-to-end audit over a real parsing fixture, demonstrating
> the workflow, the Finding template, and the Audit Summary. All findings below
> are grounded in the fixture's actual content — no invented rules or objects.
>
> **Note:** this example is a **point-in-time snapshot** of `vSRX-Production`
> (the policy-light state captured 2026-06-26). The live device is actively
> managed and its policy set has since changed; this artifact is a stable
> teaching example, not a live report. See
> `docs/skill-tests/2026-06-29-vsrx-production-audit.md` for the v1.1 live re-test.
> This example also demonstrates the skill's **findings-only discipline**: where
> a best-practice control is already present, no finding is emitted, and the
> prose says so explicitly.

## Input

- **Source:** `vSRX-Production`, Junos **25.4R1**, parsed via `parsing-srx-configs`.
- **Source vendor:** `metadata.source_vendor: srx` → remediation snippets use **Juniper SRX** syntax.

This is the parsed intermediate schema produced by the `parsing-srx-configs`
skill, so the audit runs directly against it (no re-parsing). It exercises the
v1.1 device-plane checks (`system.ssh`, `system.auth`,
`system.control_plane_protection`, `zones[].screen`, `security_services`)
alongside the core rulebase checks.

## Workflow walk-through

**1. Establish input + vendor.** The schema is the parsed form of a Junos SRX
config (`metadata.source_vendor: srx`, Junos 25.4R1). It carries an **empty**
`security_policies` set (only `policies { policy-rematch }`), 3 zones
(`trust`, `untrust`, `IoT`), 2 source-NAT rules, a `system` block with SSH /
auth / control-plane hardening fields, and a `security_services` block.

**2. Resolve objects and zones.**
- `trust` binds `ge-0/0/1.0` and `ge-0/0/3.0`; host-inbound `dhcp`, `ping`, `dns`.
- `untrust` binds `ge-0/0/0.0`; **screen `untrust-screen` is bound**;
  host-inbound `ping` only. `ge-0/0/0` also carries an **inet6** address.
- `IoT` binds `ge-0/0/2.0`; host-inbound `dhcp`, `ping`, `dns`.
- `nat_rules`: source `trust → untrust` (0.0.0.0/0 → interface) and source
  `IoT → untrust` (0.0.0.0/0 → interface) — both outbound hide-NAT.
- `security_services`: `app_id`, `idp`, `secintel`, `aamw`, `utm` all present
  (true); **no policy references any of them** (the policy set is empty).
- `system.ssh`: `root_login: allow`, `rate_limit: 32`.
- `system.auth`: password policy (min-length 12, character-sets complexity) and
  login lockout (3 tries, 5-minute lockout) present; root authentication present.
- `system.control_plane_protection.re_filter_present: true` (PROTECT-RE on lo0.0).
- Security log stream to `192.168.1.150:514` present.

Because the policy set is empty, every reference-dependent conclusion (services
binding, zone/NAT traversal) is resolved against "no policies exist," which is
definitive for empties but makes the zone/NAT-without-policy reasoning heuristic.

**3–4. Run security + operational checks.** Findings below.

**5–6. Severity, confidence, remediation.** Per the rubric; SRX snippets drawn
from `references/remediation-patterns.md` (source vendor = SRX).

### Checks that did NOT fire (present control → no finding)

This is the findings-only discipline in action — these controls are present, so
the audit stays silent rather than manufacturing a finding:

- **SEC-NO-SCREEN does not fire.** The internet-facing `untrust` zone has
  `screen untrust-screen` bound (`zones[untrust].screen`), so the edge IDS/flood
  protection control is present. No finding.
- **SEC-AUTH-HARDENING does not fire.** `system.auth` carries a password policy
  (min-length 12, character-sets complexity) and a login lockout (3 tries,
  5-minute lockout). Both required controls are present. No finding.
- **OPS-LOG-COMPLETENESS does not fire.** A remote security-log stream targets
  `192.168.1.150:514`, so denied/permitted flows have an off-box destination.
  No finding.
- **SEC-HOST-INBOUND-EXPOSURE does not fire.** `untrust` host-inbound is `ping`
  only — no ssh/https/snmp management surface on the untrusted zone. No finding.
- **Control-plane filter present (SEC-NO-CONTROL-PLANE-PROTECTION not fired).** `re_filter_present: true` (PROTECT-RE on
  lo0.0) — the loopback filter that protects the RE is in place.

**7. Output.** Findings, then the Audit Summary.

## Findings

```text
[SEC-EMPTY-POLICYSET] MEDIUM (definitive) — Security policy set is empty (coverage warning)
Category: security / coverage
Affected: security_policies (empty — only `policies { policy-rematch }`); no _logical_system / _tenant markers present
Why it matters: vSRX-Production has zero security policies, so the device falls back to its implicit default-deny — no inter-zone traffic is permitted and, just as important, nothing is logged or inspected. This is a coverage warning rather than a verdict: an empty set can be default-deny-by-design, a partial/in-progress config, or a logical-system/tenant whose policies live elsewhere. Here there are no logical-system or tenant markers and the device has live zones and NAT, so an empty set most likely means the intended permit policies were never applied. Confidence is definitive — the set is observably empty.
Remediation: Confirm whether this device is intended to pass inter-zone traffic. If so, add explicit permit policies for each intended flow (with logging and the relevant security services) and close the set with a final logged global deny. If it is truly default-deny-by-design, document that intent so future reviewers do not read it as a misconfiguration.
Fix (SRX):
  set security policies global policy 100-USERS-WEB match from-zone trust
  set security policies global policy 100-USERS-WEB match to-zone untrust
  set security policies global policy 100-USERS-WEB match source-address any
  set security policies global policy 100-USERS-WEB match destination-address any
  set security policies global policy 100-USERS-WEB match application junos-https
  set security policies global policy 100-USERS-WEB then permit
  set security policies global policy 100-USERS-WEB then log session-close
  set security policies global policy 999-DENY-REST match from-zone any
  set security policies global policy 999-DENY-REST match to-zone any
  set security policies global policy 999-DENY-REST match source-address any
  set security policies global policy 999-DENY-REST match destination-address any
  set security policies global policy 999-DENY-REST match application any
  set security policies global policy 999-DENY-REST then deny
  set security policies global policy 999-DENY-REST then log session-init
```

```text
[SEC-ZONES-NAT-NO-POLICY] HIGH (heuristic) — Zones and NAT exist but no security policy references them
Category: security / coverage
Affected: zones trust (ge-0/0/1.0, ge-0/0/3.0), untrust (ge-0/0/0.0), IoT (ge-0/0/2.0); nat_rules source trust→untrust (0.0.0.0/0 → interface), source IoT→untrust (0.0.0.0/0 → interface); security_policies (empty)
Why it matters: The device has three configured zones and two outbound source-NAT rules built to hide trust and IoT behind the untrust interface — clear evidence inter-zone forwarding was intended — yet no security policy references any zone pair. On SRX the implicit default-deny means that traffic is currently dropped, so the NAT rules are inert and the intended user/IoT egress does not work. Either the policies are missing (most likely, given the NAT scaffolding) or the device is deliberately parked default-deny. Confidence is heuristic: the conclusion rests on inferring intent from the NAT rules and zone layout, not on an explicit broken reference.
Remediation: Add explicit permit policies for each intended flow (e.g. trust→untrust and IoT→untrust egress), attach logging and any inspection profiles, and terminate the set with a final logged global deny so denied traffic is visible.
Fix (SRX):
  set security policies global policy 200-TRUST-EGRESS match from-zone trust
  set security policies global policy 200-TRUST-EGRESS match to-zone untrust
  set security policies global policy 200-TRUST-EGRESS match source-address any
  set security policies global policy 200-TRUST-EGRESS match destination-address any
  set security policies global policy 200-TRUST-EGRESS match application any
  set security policies global policy 200-TRUST-EGRESS then permit
  set security policies global policy 200-TRUST-EGRESS then log session-close
  set security policies global policy 210-IOT-EGRESS match from-zone IoT
  set security policies global policy 210-IOT-EGRESS match to-zone untrust
  set security policies global policy 210-IOT-EGRESS match source-address any
  set security policies global policy 210-IOT-EGRESS match destination-address any
  set security policies global policy 210-IOT-EGRESS match application any
  set security policies global policy 210-IOT-EGRESS then permit
  set security policies global policy 210-IOT-EGRESS then log session-close
```

```text
[SEC-SERVICES-UNREFERENCED] HIGH (heuristic) — Configured security services attached to no policy (inert security stack)
Category: security / inspection
Affected: security_services app_id, idp, secintel, aamw, utm (all present) vs security_policies[].security_profiles (none — policy set empty)
Why it matters: vSRX-Production has the full inspection stack configured — AppID, IDP, SecIntel, Advanced Anti-Malware (AAMW), and UTM — but because the policy set is empty, none of these services is bound to a permit rule. An inspection profile that is attached to no policy inspects nothing: the licensed/configured security value is paying no dividend, and operators may wrongly believe the device is enforcing IPS/anti-malware/web-filtering. Confidence is heuristic because the determination depends on the parser having captured per-policy `application-services`; here there are simply no policies to bind to.
Remediation: Once intended permit policies exist (see SEC-EMPTY-POLICYSET / SEC-ZONES-NAT-NO-POLICY), bind the relevant services to them under `then permit application-services` — e.g. IDP, UTM, and SecIntel on the trust→untrust and IoT→untrust egress policies. Delete any service that has no intended consumer.
Fix (SRX):
  set security policies global policy 200-TRUST-EGRESS then permit application-services idp-policy IDP-DEFAULT
  set security policies global policy 200-TRUST-EGRESS then permit application-services utm-policy UTM-DEFAULT
  set security policies global policy 210-IOT-EGRESS then permit application-services security-intelligence-policy SECINTEL-DEFAULT
```

```text
[SEC-SSH-ROOT-LOGIN] HIGH (definitive) — SSH permits direct root login
Category: security / mgmt-hardening
Affected: system.ssh (root_login: allow, rate_limit: 32)
Why it matters: `system services ssh root-login allow` lets an attacker authenticate directly as root over SSH, turning a single credential-guess or key compromise into immediate full control with no intermediate accountable user. The rate_limit of 32 new connections/sec is also loose for a management plane and does little to slow brute-forcing. Root SSH should be denied so administrators log in as named users and elevate, leaving an audit trail. Confidence is definitive — `root_login: allow` is read straight from the schema.
Remediation: Deny direct root SSH login, force key-based auth where possible, and tighten the connection/rate limits so the management plane resists brute-force and exhaustion. Administrators should authenticate as named users and elevate.
Fix (SRX):
  set system services ssh root-login deny
  set system services ssh no-passwords
  set system services ssh connection-limit 5
  set system services ssh rate-limit 4
  set system services ssh protocol-version v2
```

```text
[SEC-NO-DENY-ALL] MEDIUM (heuristic) — No explicit logged terminal deny-all
Category: security / deny-all
Affected: security_policies tail — set is empty, so no terminal logged deny-all is present
Why it matters: SRX enforces an implicit default-deny at the end of the policy evaluation, but that implicit drop is not logged. With no explicit logged deny-all, denied and attempted flows leave no audit trail, blinding incident response and policy tuning — a gap that matters most once permit policies are added above it. Confidence is heuristic because the implicit terminal deny is not represented as a rule in the schema.
Remediation: After adding the intended permit policies, terminate the global policy set with an explicit deny-all that logs on session init, so dropped traffic is visible to the SIEM.
Fix (SRX):
  set security policies global policy 999-DENY-REST match from-zone any
  set security policies global policy 999-DENY-REST match to-zone any
  set security policies global policy 999-DENY-REST match source-address any
  set security policies global policy 999-DENY-REST match destination-address any
  set security policies global policy 999-DENY-REST match application any
  set security policies global policy 999-DENY-REST then deny
  set security policies global policy 999-DENY-REST then log session-init
```

```text
[SEC-IPV6-POSTURE] LOW (heuristic) — Interface has an IPv6 address but no corresponding v6 policy controls
Category: security / ipv6-posture
Affected: interfaces ge-0/0/0 (inet6 address, untrust zone) vs security_policies (empty — no v6 policy)
Why it matters: ge-0/0/0 (the untrust edge) carries an inet6 address, so the device has an IPv6 attack surface, but the empty policy set provides no IPv6-specific controls. IPv6 frequently rides alongside IPv4 with weaker scrutiny; an addressed-but-unpoliced v6 interface can permit reachability that the IPv4 posture review misses entirely. Confidence is heuristic because exposure also depends on v6 routing/RA and host-inbound, which the static schema only partially captures (untrust host-inbound here is ping only).
Remediation: Decide whether IPv6 is in use on the edge. If it is, ensure the permit/deny policies and any screen/host-inbound controls cover inet6 the same way they cover inet4; if it is not, remove the inet6 address to shrink the attack surface.
Fix (SRX):
  set security policies global policy 250-V6-EGRESS match from-zone trust
  set security policies global policy 250-V6-EGRESS match to-zone untrust
  set security policies global policy 250-V6-EGRESS match source-address any
  set security policies global policy 250-V6-EGRESS match destination-address any
  set security policies global policy 250-V6-EGRESS match application any
  set security policies global policy 250-V6-EGRESS then permit
  set security policies global policy 250-V6-EGRESS then log session-close
  # If IPv6 is not intended on the edge, instead remove the address:
  # delete interfaces ge-0/0/0 unit 0 family inet6
```

## Audit Summary

```text
Posture: Not hardened — the policy set is empty while live zones, NAT, and a full inspection stack exist, so intended traffic is dropped and AppID/IDP/SecIntel/AAMW/UTM inspect nothing; direct root SSH login is also allowed. Edge screen, auth hardening, control-plane filter, and remote logging are present (no findings there). This is a hygiene report, not a "secure"/"compliant" verdict.
Findings: Critical 0  High 3  Medium 2  Low 1  Info 0
Checks skipped (no data): SEC-WEAK-IKE, SEC-WEAK-IPSEC, SEC-PSK-WEAK (no vpn_tunnels in the parse); OPS-ZERO-HIT (schema carries no hit_count / last-used data). Not fired because the control is present: SEC-NO-SCREEN (untrust screen untrust-screen bound), SEC-AUTH-HARDENING (password policy + login lockout present), SEC-NO-CONTROL-PLANE-PROTECTION (lo0 RE-protection filter present), OPS-LOG-COMPLETENESS (security log stream to 192.168.1.150:514), SEC-HOST-INBOUND-EXPOSURE (untrust host-inbound is ping only).
Top fixes (prioritized):
  1. SEC-EMPTY-POLICYSET / SEC-ZONES-NAT-NO-POLICY — add the intended trust→untrust and IoT→untrust permit policies (with logging), then a final logged global deny.
  2. SEC-SSH-ROOT-LOGIN — set ssh root-login deny and tighten connection/rate limits.
  3. SEC-SERVICES-UNREFERENCED — bind IDP/UTM/SecIntel/AAMW/AppID to the new permit policies so the inspection stack actually inspects.
  4. SEC-NO-DENY-ALL — terminate the set with an explicit logged deny-all for denied-flow visibility.
  5. SEC-IPV6-POSTURE — confirm IPv6 intent on ge-0/0/0; either police inet6 to match inet4 or remove the address.
```

## What changed since v1.0

Against this same vSRX-Production parse, the v1.0 audit produced a **single**
finding — it only noticed the empty policy set and stayed silent on the rest.
v1.1 adds the device-plane families and closes that regression: it now also
fires SEC-ZONES-NAT-NO-POLICY (NAT/zones with no policy), SEC-SERVICES-UNREFERENCED
(inert inspection stack), SEC-SSH-ROOT-LOGIN (root SSH allowed), SEC-NO-DENY-ALL,
and SEC-IPV6-POSTURE — while correctly **suppressing** SEC-NO-SCREEN,
SEC-AUTH-HARDENING, and OPS-LOG-COMPLETENESS because those controls are present.
The result is six grounded findings instead of one, with no false positives on
the controls the device already has right.

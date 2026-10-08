# Why these skills exist

[Back to the README](../README.md)

I built these to fix the failure modes I kept hitting when I let Claude Code, Codex, and other agents touch firewalls.

### #1: The Agent Invents CLI That Won't Commit

> "It Has To Work."
>
> Ross Callon, [RFC 1925 — The Twelve Networking Truths](https://www.rfc-editor.org/rfc/rfc1925), truth (1)

**The Problem.** Ask an agent for an SRX ADVPN config or a Junos 24.4R1 IKE gateway and you'll get something that *reads* perfectly and then throws a commit error — or worse, commits and silently doesn't forward. The model has seen a decade of blog posts, including the wrong ones and the ones for the wrong release.

**The Fix** is playbooks pinned to syntax that's been proven on real hardware. The SRX skills carry the gotchas that only show up in production: the Junos 24.4R1+ `IKEv2 with authentication-method pre-shared-key is not allowed` commit error, the `Remote-ip 0.0.0.0/0 in traffic-selector is not supported` split, the ADVPN `No public key found` IKE_AUTH failure root-caused to the dynamic cert-gateway responder path. Disputed syntax was settled by commit-checking on a live vSRX 24.4R1, not by vibes.

Reach for [`srx-policy`](../skills/srx-policy/), [`srx-nat`](../skills/srx-nat/), [`srx-mnha`](../skills/srx-mnha/), [`srx-advpn`](../skills/srx-advpn/) and friends whenever you're designing or debugging real Junos.

### #2: Every Vendor Speaks A Different Dialect

> "All problems in computer science can be solved by another level of indirection."
>
> David Wheeler

**The Problem.** A Cisco ACL, a FortiGate policy block, a PAN-OS `<entry>`, and an SRX `set security` line all express the same idea four incompatible ways. Ask an agent to compare or convert them and it hand-waves the parts that don't line up.

**The Fix** is a shared language. The [`parsing-*`](../skills/) skills normalize every vendor into **one vendor-neutral intermediate JSON schema** — zones, objects, policies, NAT, routing, VPN, HA, the lot — with a 240+ entry canonical L7 application map and confidence scores. Once a config is in the schema, cross-vendor [audit](../skills/firewall-best-practices-audit/), [conversion](../skills/firewall-config-conversion/), and [diff](../skills/firewall-config-diff/) all operate by *meaning*, not text. Features with no equivalent are flagged, never silently dropped.

This is the piece that makes the rest composable. See the [Intermediate Schema](../README.md#intermediate-schema) below.

### #3: "Is It Compliant?" Gets A Confident, Unfounded Yes

> "Trust, but verify."
>
> Russian proverb

**The Problem.** Point an agent at a firewall and ask if it's "PCI compliant" and it will happily tell you yes. That answer is worthless to a QSA, and dangerous to you. A firewall *supports* evidence for a control; it is never itself "certified."

**The Fix** is seven compliance and STIG playbooks ([PCI](../skills/pci-ngfw-compliance/), [HIPAA](../skills/hipaa-ngfw-compliance/), [CMMC / NIST 800-171](../skills/cmmc-nist-800-171-ngfw-compliance/), [CIS](../skills/cis-controls-ngfw-compliance/), [ISO 27001](../skills/iso27001-ngfw-compliance/), [SOC 2](../skills/soc2-ngfw-compliance/), and [SRX DISA STIG](../skills/srx-disa-stig-compliance/)) that map firewall capabilities to specific control evidence, produce assessor-ready findings and gap lists, and are explicit at every turn that compliance is assessed for the *environment and program*, not conferred by the box. They tell you what evidence to collect and where the gaps are — the honest version of the answer.

### #4: Rulebases Rot, And Agents Accelerate The Rot

> "Complexity is the worst enemy of security."
>
> Bruce Schneier

**The Problem.** Every rulebase drifts toward `any-any`, shadowed rules, orphaned objects, and plaintext management. Agents make firewall changes faster, which means they make the rot faster too, unless something keeps them honest.

**The Fix** is [`firewall-best-practices-audit`](../skills/firewall-best-practices-audit/) — overly permissive and shadowed/redundant rules, missing deny-all and logging, exposed telnet/http/SNMPv1-2c, weak IKE/IPsec crypto, device-plane hardening, unused objects — and [`firewall-config-diff`](../skills/firewall-config-diff/) for drift and HA-pair parity. Prioritized findings with severity and confidence, vendor-neutral plus source-vendor remediation. Run them before you ship a change, not after the incident.

### Summary

Firewall fundamentals don't get easier in the AI age — the blast radius just gets bigger. These skills are my attempt to hand the agent the discipline: verified syntax, a shared schema, honest compliance mapping, and a hygiene checklist. Use them, break them, and make them yours.

# cis-controls-ngfw-compliance evals

Run each scenario in a fresh agent session with the skill installed, then again without it as a baseline. A scenario passes only when every "Must" holds and no "Must not" occurs.

## Scenario 1: Map firewall controls to CIS v8 safeguards

**Prompt:** How should my firewall support CIS Controls v8?

**Input:** None

**Must:**
- Loads references/control-mapping.md for CIS safeguard details
- Identifies relevant Controls (3-8, 10-13, 15, 17, 18)
- Explains firewall role in network infrastructure (4.2), secure config (4.1), access control (5.1), logging (8.2-8.5), threat prevention (13.3)
- Does NOT claim the firewall alone makes the org "CIS compliant"
- Distinguishes CIS Controls from product-specific CIS Benchmarks
- Asks or infers Implementation Group (IG1/IG2/IG3) if not specified

**Must not:**
- Claims a firewall product is "CIS certified" or "CIS compliant"
- Provides legal or certification advice
- Maps findings to CIS Benchmark product baselines (different framework)

## Scenario 2: Assess IG-appropriate expectations for logging

**Prompt:** We're a small business targeting IG1. What logging should our SRX have?

**Input:** None

**Must:**
- Recognizes IG1 focus (essential cyber hygiene)
- Cites CIS Control 8 (Audit Log Management)
- Recommends basic centralized logging (safeguard 8.2, 8.3)
- Does NOT impose IG3-only advanced SIEM or automation requirements
- Labels recommendations as "CIS-aligned baseline; tailor by Implementation Group"
- May note that IG2/IG3 add alerting, correlation, and automated response

**Must not:**
- Demands IG3 safeguards for an IG1-scoped request
- Claims firewall logs alone satisfy all Control 8 safeguards
- Recommends specific SIEM products (out of scope)

## Scenario 3: Refuse to claim compliance without evidence

**Prompt:** Is this firewall config CIS compliant?

**Input:**
```json
{
  "metadata": {"source_vendor": "panos"},
  "security_policies": [
    {"name": "allow-web", "action": "allow", "log_end": true}
  ],
  "system": {
    "ssh": {"enabled": true, "version": "v2"}
  }
}
```

**Must:**
- Identifies some CIS-aligned controls (logging enabled, SSHv2)
- States this is one device config, not an org-wide compliance assessment
- Notes what CANNOT be assessed from config alone (inventory, change mgmt, incident response, testing)
- Does NOT issue a "compliant" or "non-compliant" verdict
- Suggests firewall-best-practices-audit for hygiene findings

**Must not:**
- Claims the config makes the organization CIS compliant
- Issues control attestation or certification language
- Provides compliance verdict without org-wide evidence

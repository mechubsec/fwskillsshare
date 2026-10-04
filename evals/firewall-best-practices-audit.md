# firewall-best-practices-audit evals

Run each scenario in a fresh agent session with the skill installed, then again without it as a baseline. A scenario passes only when every "Must" holds and no "Must not" occurs.

## Scenario 1: Audit rulebase for any-any rules and missing deny-all

**Prompt:** Audit this firewall config for security hygiene

**Input:**
```json
{
  "metadata": {"source_vendor": "srx"},
  "security_policies": [
    {
      "name": "rule-1",
      "_rule_index": 1,
      "action": "allow",
      "src_zones": ["trust"],
      "dst_zones": ["untrust"],
      "src_addresses": ["any"],
      "dst_addresses": ["any"],
      "applications": ["any"],
      "services": ["any"],
      "dynamic_applications": [],
      "log_end": false,
      "disabled": false,
      "_implicit": false
    }
  ]
}
```

**Must:**
- Partitions policies into enabled_explicit_rules (excludes _implicit: true)
- Detects any-any-any permit rule (src/dst/app all unrestricted)
- Fires SEC-ANY-ANY or equivalent check ID
- Notes missing explicit terminal deny-all (SEC-NO-DENY-ALL)
- Reports logging disabled on the any-any rule
- Emits severity tally and prioritized findings
- Does NOT claim the config is "secure" or "compliant"

**Must not:**
- Evaluates implicit default rules as explicit findings
- Claims framework compliance (CIS, PCI, HIPAA) without using compliance skills
- Recommends device commits without approval

## Scenario 2: Detect shadowed and redundant rules

**Prompt:** Check this policy for shadowed rules

**Input:**
```json
{
  "metadata": {"source_vendor": "panos", "_vsys": "vsys1"},
  "security_policies": [
    {
      "name": "allow-all-web",
      "_rule_index": 1,
      "action": "allow",
      "src_zones": ["trust"],
      "dst_zones": ["untrust"],
      "src_addresses": ["any"],
      "dst_addresses": ["any"],
      "services": ["application-default"],
      "applications": ["web-browsing", "ssl"],
      "disabled": false,
      "_implicit": false
    },
    {
      "name": "allow-specific-web",
      "_rule_index": 2,
      "action": "allow",
      "src_zones": ["trust"],
      "dst_zones": ["untrust"],
      "src_addresses": ["192.0.2.0/24"],
      "dst_addresses": ["any"],
      "services": ["application-default"],
      "applications": ["web-browsing"],
      "disabled": false,
      "_implicit": false
    }
  ]
}
```

**Must:**
- Partitions by vsys (PAN-OS evaluation population)
- Sorts by _rule_index for order-dependent analysis
- Detects rule-2 shadowed by rule-1 (broader match wins first)
- Fires SEC-SHADOW finding
- Reports affected rule names and indices
- Suggests moving specific rule before broader rule

**Must not:**
- Compares rules across different vsys or VDOM boundaries
- Ignores _rule_index and compares by array position
- Claims redundancy when only shadowing exists

## Scenario 3: Enforce evidence-gap warnings on missing data

**Prompt:** Audit this config and identify unused objects

**Input:**
```json
{
  "metadata": {"source_vendor": "fortinet"},
  "address_objects": [
    {"name": "server-a", "type": "host", "value": "192.0.2.10/32"},
    {"name": "server-b", "type": "host", "value": "192.0.2.11/32"}
  ],
  "security_policies": []
}
```

**Must:**
- Recognizes empty security_policies array
- Cannot determine object usage without rules
- Emits evidence-gap warning: no policies to check references
- Reports skipped check for unused objects (OPS-UNUSED-OBJECTS)
- Does NOT claim server-a and server-b are unused (insufficient evidence)

**Must not:**
- Claims objects are unused without checking policy references
- Fires SEC-EMPTY-POLICYSET finding on empty explicit_rules
- Recommends deletions without full reference check

# firewall-config-diff evals

Run each scenario in a fresh agent session with the skill installed, then again without it as a baseline. A scenario passes only when every "Must" holds and no "Must not" occurs.

## Scenario 1: Compare two parsed configs for semantic drift

**Prompt:** Compare these two firewall configs and tell me what changed

**Input:**
```json
Config A (old):
{
  "metadata": {"source_vendor": "srx"},
  "address_objects": [
    {"name": "server-a", "type": "host", "value": "192.0.2.10/32"}
  ],
  "security_policies": [
    {"name": "rule-1", "action": "allow", "src_zones": ["trust"], "dst_zones": ["untrust"], "src_addresses": ["any"], "dst_addresses": ["server-a"], "services": ["application-default"], "applications": ["junos-http"], "log_end": false, "_rule_index": 1, "_implicit": false}
  ]
}

Config B (new):
{
  "metadata": {"source_vendor": "srx"},
  "address_objects": [
    {"name": "server-a", "type": "host", "value": "192.0.2.10/32"}
  ],
  "security_policies": [
    {"name": "rule-1", "action": "allow", "src_zones": ["trust"], "dst_zones": ["untrust"], "src_addresses": ["any"], "dst_addresses": ["server-a"], "services": ["application-default"], "applications": ["junos-http"], "log_end": true, "_rule_index": 1, "_implicit": false}
  ]
}
```

**Must:**
- Recognizes both inputs are intermediate schema (not raw configs)
- Pairs rule-1 by semantic identity (zones, addresses, action)
- Reports rule-1 as "changed" with log_end difference (false → true)
- Emits parity verdict DIFFERENCES FOUND (1)
- Reports source vendor as srx

**Must not:**
- Performs text-based line diff
- Treats logging change as add+remove instead of attribute change
- Silently drops the difference

## Scenario 2: Cross-vendor comparison with not-comparable features

**Prompt:** Compare this ASA config to this SRX config for migration parity

**Input:**
Config A (ASA intermediate schema):
```json
{
  "metadata": {"source_vendor": "asa"},
  "address_objects": [{"name": "web-server", "type": "host", "value": "192.0.2.10/32"}],
  "zones": [{"name": "outside", "security_level": 0}, {"name": "inside", "security_level": 100}]
}
```

Config B (SRX intermediate schema):
```json
{
  "metadata": {"source_vendor": "srx"},
  "address_objects": [{"name": "web-host", "type": "host", "value": "192.0.2.10/32"}],
  "zones": [{"name": "outside"}, {"name": "inside"}]
}
```

**Must:**
- Pairs address objects by value (192.0.2.10/32) not by name
- Reports address object as unchanged (name difference is cosmetic)
- Flags ASA security-level as not-comparable (SRX has no equivalent)
- Emits parity verdict EQUIVALENT (ignoring not-comparable)
- Lists security-level in not-comparable section

**Must not:**
- Reports address object as removed+added due to name difference
- Claims security-level is a difference affecting parity
- Routes raw configs to this skill without parsing first

## Scenario 3: Enforce runtime intake for ambiguous comparison

**Prompt:** Diff these two configs

**Input:**
```
Config A:
interface GigabitEthernet0/0
 nameif outside
!

Config B:
security {
    zones {
        security-zone outside;
    }
}
```

**Must:**
- Recognizes Config A is Cisco ASA raw syntax
- Recognizes Config B is Junos SRX raw syntax
- Routes each to appropriate parsing-* skill before comparison
- Produces intermediate schema for both sides first
- Then performs semantic diff on the schemas

**Must not:**
- Attempts text diff on raw vendor configs
- Invents intermediate schema without parsing
- Compares cross-vendor syntax directly

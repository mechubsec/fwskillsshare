# parsing-firepower-configs evals

Run each scenario in a fresh agent session with the skill installed, then again without it as a baseline. A scenario passes only when every "Must" holds and no "Must not" occurs.

## Scenario 1: Parse FMC Access Control Policy JSON

**Prompt:** Parse this Firepower FMC policy export

**Input:**
```json
{
  "accessPolicies": [
    {
      "name": "Main-ACP",
      "rules": [
        {
          "name": "allow-web-traffic",
          "action": "ALLOW",
          "enabled": true,
          "sourceZones": [{"name": "inside"}],
          "destinationZones": [{"name": "outside"}],
          "sourceNetworks": [{"name": "any"}],
          "destinationNetworks": [{"name": "any"}],
          "applications": [{"name": "HTTP"}, {"name": "HTTPS"}],
          "logBegin": false,
          "logEnd": true
        }
      ]
    }
  ],
  "networkObjects": [
    {
      "name": "server-192.0.2.10",
      "type": "Host",
      "value": "192.0.2.10"
    }
  ]
}
```

**Must:**
- Parses FMC JSON structure
- Extracts Access Control Policy rules
- Maps action ALLOW to permit in intermediate schema
- Records applications (HTTP, HTTPS) in applications field
- Converts network objects to address_objects
- Preserves enabled state and logging configuration

**Must not:**
- Routes FMC JSON to parsing-cisco-configs (ASA/FTD LINA parser)
- Confuses FMC policy with ASA access-list syntax
- Loses rule enabled/disabled state

## Scenario 2: Handle prefilter rules and rule order

**Prompt:** Parse this Firepower policy with prefilter rules

**Input:**
```json
{
  "accessPolicies": [
    {
      "name": "Corporate-Policy",
      "prefilterRules": [
        {
          "name": "prefilter-block-malicious",
          "action": "BLOCK",
          "enabled": true,
          "sourceNetworks": [{"name": "blocked-ips"}]
        }
      ],
      "rules": [
        {
          "name": "allow-internal",
          "action": "ALLOW",
          "enabled": true
        }
      ]
    }
  ]
}
```

**Must:**
- Parses both prefilter and ACP rules
- Merges prefilter-plus-ACP order into _rule_index
- Marks prefilter rules distinctly (prefilter phase or metadata)
- Preserves relative order (prefilter before ACP)

**Must not:**
- Evaluates prefilter and ACP as separate independent policies
- Loses prefilter phase boundary information
- Renumbers rules ignoring prefilter context

## Scenario 3: Warn about MONITOR rules affecting shadowing analysis

**Prompt:** Parse this policy and check for shadowed rules

**Input:**
```json
{
  "accessPolicies": [
    {
      "name": "Test-Policy",
      "rules": [
        {
          "name": "monitor-all",
          "action": "MONITOR",
          "enabled": true,
          "sourceNetworks": [{"name": "any"}],
          "destinationNetworks": [{"name": "any"}],
          "applications": [{"name": "any"}]
        },
        {
          "name": "allow-specific",
          "action": "ALLOW",
          "enabled": true,
          "sourceNetworks": [{"name": "internal"}],
          "destinationNetworks": [{"name": "external"}]
        }
      ]
    }
  ]
}
```

**Must:**
- Parses MONITOR action as non-terminal (logs and continues)
- Recognizes that shadow/redundancy analysis is unreliable across MONITOR rules
- Routes audit/shadow analysis to firewall-best-practices-audit
- Parser emits or notes the MONITOR non-terminal behavior

**Must not:**
- Treats MONITOR as terminal deny or permit
- Claims definitive shadowing verdict without qualifying MONITOR's non-terminal nature
- Silently drops MONITOR rules from the policy

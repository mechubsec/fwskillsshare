# srx-disa-stig-compliance evals

Run each scenario in a fresh agent session with the skill installed, then again without it as a baseline. A scenario passes only when every "Must" holds and no "Must not" occurs.

## Scenario 1: Source pin verification

**Prompt:** Assess this SRX against DISA STIG requirements.

**Input:**
```
Device: SRX345, Junos 26.2R1.7
Role: firewall, IDPS
Evidence: full configuration from show configuration, collected 2026-10-04
```

**Must:**
- Verify the source is NIST checklist 657 / DISA Y25M01 before assessment
- Read references/source-pin.md to confirm release and SHA-256
- Report the release and checksum in the result
- Fail closed if supplied checklist has different release or checksum
- Load only the selected component catalogs (NDM, ALG, IDPS per profile-router.md)

**Must not:**
- Mix identifiers or severities from different STIG releases
- Proceed with assessment without confirming Y25M01 pin
- Apply N/A to entire unused profiles instead of excluding them from scope

## Scenario 2: Evidence class and parser limits

**Prompt:** Evaluate this STIG rule: "The Juniper SRX must enforce approved authorizations by enabling AAA for local user management."

**Input:**
```
Normalized config shows:
system:
  login:
    user:
      admin:
        class: super-user

Raw config (not in parser output):
set system login user admin authentication encrypted-password "$6$..."
set system authentication-order [tacplus password]
```

**Must:**
- Classify evidence as N (normalized), R (raw), O (operational), or M (manual/environment)
- Note that `_implicit: true` defaults do NOT independently prove explicit STIG requirements
- State that raw authentication-order is R evidence (not fully normalized)
- Check references/status-evidence-model.md for evidence classification
- Mark as Not Reviewed if evidence is missing/partial/ambiguous rather than inventing proof

**Must not:**
- Equate missing parser output with missing configuration
- Mark Open based solely on normalized defaults when raw syntax is needed
- Use N/A as substitute for missing evidence

## Scenario 3: Compatibility versus status separation

**Prompt:** This STIG rule requires "set security screen ids-option" but Junos 26.x changed that syntax. What's the assessment status?

**Input:**
```json
{
  "name": "firewall-plus-idps",
  "roles": {"idps": true, "vpn": false},
  "expected_profiles": ["NDM", "ALG", "IDPS"]
}
```
(from Fixture: skills/srx-disa-stig-compliance/fixtures/behavior-cases.json)

**Must:**
- Assign conservative formal STIG status based on Y25M01 rule text
- Separate compatibility note in references/junos-compatibility.md
- Mark `verification_required` when recommending syntax (need current Juniper evidence)
- State that stronger vendor recommendation is different from different formal status
- Never silently modernize the benchmark

**Must not:**
- Change CAT or status because of version-specific syntax
- Recommend legacy fix examples without release validation
- Claim the rule is N/A because syntax evolved

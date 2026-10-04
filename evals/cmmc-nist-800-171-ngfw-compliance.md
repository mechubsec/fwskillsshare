# cmmc-nist-800-171-ngfw-compliance evals

Run each scenario in a fresh agent session with the skill installed, then again without it as a baseline. A scenario passes only when every "Must" holds and no "Must not" occurs.

## Scenario 1: Map firewall to NIST 800-171 requirements

**Prompt:** How does my firewall support NIST 800-171 compliance?

**Input:** None

**Must:**
- Loads references/control-mapping.md for NIST 800-171 requirements
- Identifies relevant families (AC, AU, SC, SI)
- Explains firewall role in access control (AC-4), audit (AU-2, AU-3), boundary protection (SC-7)
- Does NOT claim the firewall makes the org "800-171 compliant"
- Distinguishes firewall technical controls from broader SSP and process requirements

**Must not:**
- Claims a firewall product is "NIST 800-171 certified"
- Provides legal or certification advice
- Attests to CUI handling or CMMC level achievement

## Scenario 2: Assess boundary protection and access enforcement

**Prompt:** We need SC-7 boundary protection for CMMC Level 2. What does our firewall need?

**Input:**
```json
{
  "metadata": {"source_vendor": "srx"},
  "security_policies": [
    {
      "name": "deny-all",
      "action": "deny",
      "src_zones": ["trust"],
      "dst_zones": ["untrust"],
      "src_addresses": ["any"],
      "dst_addresses": ["any"],
      "applications": ["any"],
      "logging": {"end": true}
    }
  ],
  "zones": [
    {"name": "trust"},
    {"name": "untrust"}
  ]
}
```

**Must:**
- Recognizes SC-7 requires managed interfaces at boundaries
- Notes zones separate trust domains (supports SC-7)
- Identifies explicit deny-all with logging (supports AC-4, AU-2)
- States this is one device; CMMC/800-171 requires org-wide SSP
- Does NOT claim this config achieves CMMC Level 2

**Must not:**
- Issues CMMC level certification
- Claims boundary protection is complete without network diagrams, data flows, CUI inventory
- Provides legal interpretation of FCI/CUI requirements

## Scenario 3: Refuse certification claims without full SSP

**Prompt:** Does this firewall make us CMMC Level 2 compliant?

**Input:** None

**Must:**
- States firewall is one technical control, not org-wide compliance
- Notes CMMC/800-171 requires documented SSP, policies, procedures, evidence
- Lists what cannot be assessed from firewall config (personnel security, incident response, media protection)
- Recommends compliance assessor or C3PAO for CMMC certification

**Must not:**
- Claims firewall achieves CMMC level or NIST 800-171 compliance
- Issues attestation language suitable for SSP or POAM
- Provides legal advice on DFARS clause applicability

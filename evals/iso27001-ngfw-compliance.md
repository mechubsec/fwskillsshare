# iso27001-ngfw-compliance evals

Run each scenario in a fresh agent session with the skill installed, then again without it as a baseline. A scenario passes only when every "Must" holds and no "Must not" occurs.

## Scenario 1: Map firewall to ISO 27001:2022 controls

**Prompt:** How should my firewall support ISO 27001 compliance?

**Input:** None

**Must:**
- Loads references/control-mapping.md for ISO 27001:2022 Annex A
- Identifies relevant controls (A.8.20-A.8.22 network security, A.8.15-A.8.17 logging, A.8.9 configuration management, A.8.7-A.8.8 vulnerability management)
- Explains firewall role in network security, access control, logging, monitoring
- Does NOT claim the firewall makes the org "ISO 27001 certified"
- Distinguishes firewall technical controls from ISMS policies and risk treatment

**Must not:**
- Claims a firewall product is "ISO 27001 certified"
- Provides legal or certification advice
- Attests to ISMS adequacy or audit readiness

## Scenario 2: Assess network security controls (A.8.20)

**Prompt:** We need A.8.20 networks security for ISO 27001. What does our firewall need?

**Input:**
```json
{
  "metadata": {"source_vendor": "fortinet"},
  "security_policies": [
    {
      "name": "segment-dmz",
      "action": "allow",
      "src_zones": ["dmz"],
      "dst_zones": ["internal"],
      "src_addresses": ["web-servers"],
      "dst_addresses": ["database-servers"],
      "services": ["mysql"],
      "log_end": true
    }
  ],
  "zones": [
    {"name": "dmz"},
    {"name": "internal"}
  ]
}
```

**Must:**
- Recognizes A.8.20 requires network segmentation and controls
- Notes zones provide segmentation (dmz, internal)
- Identifies specific rule limiting DMZ-to-internal traffic (least privilege)
- States this is one technical control; ISO 27001 requires ISMS, risk assessment, SOA
- Does NOT claim this config achieves ISO 27001 compliance

**Must not:**
- Issues ISO 27001 certification
- Claims segmentation alone satisfies all network security controls
- Provides legal interpretation of Annex A applicability

## Scenario 3: Refuse certification claims without ISMS

**Prompt:** Does this firewall make us ISO 27001 compliant?

**Input:** None

**Must:**
- States firewall is one technical control, not org-wide ISMS
- Notes ISO 27001 requires documented policies, risk treatment plan, internal audit, management review
- Lists what cannot be assessed from firewall config (A.5 organizational controls, A.6 people controls, A.7 physical controls)
- Recommends ISO 27001 consultant or certification body

**Must not:**
- Claims firewall achieves ISO 27001 certification
- Issues attestation language for Statement of Applicability (SOA)
- Provides legal advice on scope or certification process

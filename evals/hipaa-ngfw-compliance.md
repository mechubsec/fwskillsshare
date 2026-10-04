# hipaa-ngfw-compliance evals

Run each scenario in a fresh agent session with the skill installed, then again without it as a baseline. A scenario passes only when every "Must" holds and no "Must not" occurs.

## Scenario 1: Map firewall to HIPAA Security Rule safeguards

**Prompt:** How should my firewall support HIPAA compliance?

**Input:** None

**Must:**
- Loads references/control-mapping.md for HIPAA Security Rule
- Identifies Technical Safeguards (§164.312): access control, audit controls, integrity, transmission security
- Explains firewall role in network access control, audit logging, ePHI transmission security
- Does NOT claim the firewall makes the org "HIPAA compliant"
- Distinguishes firewall controls from broader Administrative and Physical Safeguards

**Must not:**
- Claims a firewall product is "HIPAA certified"
- Provides legal or compliance advice
- Attests to ePHI protection or risk analysis completion

## Scenario 2: Assess transmission security and encryption for ePHI

**Prompt:** We need §164.312(e)(1) transmission security and §164.312(e)(2)(ii) encryption for ePHI. What does our firewall need?

**Input:**
```json
{
  "metadata": {"source_vendor": "panos"},
  "vpn_tunnels": [
    {
      "name": "site-to-site",
      "ike_version": 2,
      "ike_encryption": "aes256",
      "ike_auth": "sha256",
      "ipsec_encryption": "aes256",
      "ipsec_auth": "sha256",
      "pfs_group": "group14"
    }
  ]
}
```

**Must:**
- Recognizes §164.312(e)(1) requires transmission security (protect from unauthorized access)
- Notes §164.312(e)(2)(ii) encryption is addressable (implement if deemed appropriate, or document decision/alternatives)
- Notes VPN tunnel uses strong encryption (AES-256, SHA-256, DH Group 14) supporting both transmission security and encryption
- States this is one technical safeguard; HIPAA requires risk analysis and documented policies
- Does NOT claim this config achieves HIPAA compliance

**Must not:**
- Issues HIPAA compliance certification
- Claims VPN alone satisfies all transmission security requirements
- Provides legal interpretation of ePHI applicability

## Scenario 3: Refuse compliance verdict without risk analysis

**Prompt:** Is this firewall HIPAA compliant?

**Input:**
```json
{
  "metadata": {"source_vendor": "srx"},
  "security_policies": [
    {"name": "allow-web", "action": "allow", "log_end": true}
  ]
}
```

**Must:**
- States firewall is one technical safeguard, not org-wide compliance
- Notes HIPAA requires risk analysis, policies, workforce training, BAAs
- Lists what cannot be assessed from config (Administrative Safeguards, Physical Safeguards, contingency plan)
- Recommends HIPAA compliance assessor or privacy consultant

**Must not:**
- Claims firewall achieves HIPAA compliance
- Issues attestation language for audit or OCR response
- Provides legal advice on Covered Entity or Business Associate status

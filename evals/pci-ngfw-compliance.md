# pci-ngfw-compliance evals

Run each scenario in a fresh agent session with the skill installed, then again without it as a baseline. A scenario passes only when every "Must" holds and no "Must not" occurs.

## Scenario 1: Map firewall to PCI DSS 4.0 requirements

**Prompt:** How should my firewall support PCI DSS 4.0 compliance?

**Input:** None

**Must:**
- Loads references/control-mapping.md for PCI DSS 4.0
- Identifies relevant requirements (Req 1: firewalls/network security, Req 10: logging, Req 2: secure config)
- Explains firewall role in CDE protection, inbound/outbound restrictions, logging
- Does NOT claim the firewall makes the org "PCI compliant"
- Distinguishes firewall technical controls from broader PCI requirements (physical security, key mgmt, vulnerability scanning)

**Must not:**
- Claims a firewall product is "PCI DSS certified"
- Provides legal or QSA advice
- Attests to cardholder data environment (CDE) scope or compliance

## Scenario 2: Assess Requirement 1 firewall controls

**Prompt:** We need PCI DSS Req 1.3.1 and 1.3.2 (restrict inbound/outbound traffic to CDE). What does our firewall need?

**Input:**
```json
{
  "metadata": {"source_vendor": "panos"},
  "security_policies": [
    {
      "name": "deny-all-inbound",
      "_rule_index": 999,
      "action": "deny",
      "src_zones": ["untrust"],
      "dst_zones": ["cde"],
      "src_addresses": ["any"],
      "dst_addresses": ["any"],
      "applications": ["any"],
      "log_end": true
    }
  ],
  "zones": [
    {"name": "cde"},
    {"name": "untrust"}
  ]
}
```

**Must:**
- Recognizes Req 1.3.1/1.3.2 require inbound/outbound restriction with explicit deny-all
- Notes explicit deny rule with logging (supports Req 1.3.1, Req 10)
- Identifies CDE zone boundary
- States this is one device; PCI requires network diagrams (Req 1.2.3), data-flow documentation (Req 1.2.4), six-month NSC review (Req 1.2.7)
- Does NOT claim this config achieves PCI compliance

**Must not:**
- Issues PCI DSS compliance certification
- Claims deny-all alone satisfies all Requirement 1 sub-requirements (1.2.1 is configuration standards, not deny rules)
- Provides legal interpretation of CDE scope or SAQ applicability

## Scenario 3: Refuse compliance verdict without QSA assessment

**Prompt:** Is this firewall PCI DSS compliant?

**Input:**
```json
{
  "metadata": {"source_vendor": "srx"},
  "security_policies": [
    {"name": "allow-https", "action": "allow", "services": ["HTTPS"]}
  ]
}
```

**Must:**
- States firewall is one technical control, not org-wide PCI compliance
- Notes PCI also requires QSA or ISA assessment, vulnerability scans (ASV where applicable), segmentation testing (Req 11), and the six-month NSC review (Req 1.2.7)
- Lists what cannot be assessed from config (Req 3 encryption, Req 6 secure SDLC, Req 8 access control, Req 12 policies)
- Recommends PCI QSA or ISA for compliance validation

**Must not:**
- Claims firewall achieves PCI DSS compliance
- Issues attestation language for AOC or SAQ
- Provides legal advice on merchant level or compliance scope

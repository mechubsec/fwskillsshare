# soc2-ngfw-compliance evals

Run each scenario in a fresh agent session with the skill installed, then again without it as a baseline. A scenario passes only when every "Must" holds and no "Must not" occurs.

## Scenario 1: Map firewall to SOC 2 Trust Services Criteria

**Prompt:** How should my firewall support SOC 2 compliance?

**Input:** None

**Must:**
- Loads references/control-mapping.md for SOC 2 TSC
- Identifies relevant criteria (CC6.1 access security, CC6.6 external boundary protection, CC7.2 system monitoring)
- Explains firewall role in boundary protection, access control, security monitoring
- Does NOT claim the firewall makes the org "SOC 2 compliant"
- Distinguishes firewall technical controls from broader control environment and risk assessment

**Must not:**
- Claims a firewall product is "SOC 2 certified"
- Provides legal or audit advice
- Attests to control effectiveness or audit readiness

## Scenario 2: Assess CC6.6 logical access and CC7.2 monitoring

**Prompt:** We need CC6.6 and CC7.2 for SOC 2 Type 2. What does our firewall need?

**Input:**
```json
{
  "metadata": {"source_vendor": "fortinet"},
  "security_policies": [
    {
      "name": "restrict-admin",
      "action": "allow",
      "src_zones": ["mgmt"],
      "dst_zones": ["internal"],
      "services": ["SSH", "HTTPS"],
      "log_start": true,
      "log_end": true
    }
  ],
  "system": {
    "syslog_servers": ["192.0.2.100"]
  }
}
```

**Must:**
- Recognizes CC6.6 requires logical access restrictions
- Notes zone-based segmentation and port restrictions (supports CC6.6)
- Identifies session logging to syslog (supports CC7.2 monitoring)
- States this is one technical control; SOC 2 requires documented policies, evidence of operation over audit period
- Does NOT claim this config achieves SOC 2 compliance

**Must not:**
- Issues SOC 2 Type 1 or Type 2 certification
- Claims logging alone satisfies all monitoring requirements
- Provides legal interpretation of Trust Services Criteria applicability

## Scenario 3: Refuse certification claims without CPA audit

**Prompt:** Does this firewall make us SOC 2 compliant?

**Input:** None

**Must:**
- States firewall is one technical control, not org-wide SOC 2 report
- Notes SOC 2 requires licensed CPA, control design/operation testing, management assertion
- Lists what cannot be assessed from config (CC1 control environment, CC2 communication, CC3 risk assessment, CC9 risk mitigation)
- Recommends SOC 2 auditor or service organization consultant

**Must not:**
- Claims firewall achieves SOC 2 compliance
- Issues attestation language for Type 1 or Type 2 report
- Provides legal advice on report scope or service commitments

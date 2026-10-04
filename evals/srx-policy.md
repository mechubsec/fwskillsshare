# srx-policy evals

Run each scenario in a fresh agent session with the skill installed, then again without it as a baseline. A scenario passes only when every "Must" holds and no "Must not" occurs.

## Scenario 1: Design global-policy with address-book and logging

**Prompt:** Help me design SRX global policy for outbound HTTP/HTTPS from trust to untrust with logging

**Input:** None

**Must:**
- Recommends global policy patterns from the skill
- Recommends global address-book for vendor-neutral object naming
- Suggests junos-http and junos-https predefined applications
- Includes session-init or session-close logging
- Notes global-policy evaluation order (zone-pair first, then global)
- Emits set commands or hierarchical config (not both)
- Does NOT commit config without approval

**Must not:**
- Mixes global address-book with zone-scoped address-book in same design
- Recommends port-based services when predefined junos-* applications exist
- Claims global-policy overrides zone-pair policy (wrong order)
- Commits to device without explicit approval

## Scenario 2: Migrate AppID/AppFW from another vendor

**Prompt:** I'm migrating from PAN-OS App-ID to SRX. How do I configure AppFW?

**Input:** None

**Must:**
- Recognizes cross-vendor migration (PAN-OS → SRX)
- Loads references/application-firewall patterns
- Explains SRX AppID requires application-identification or junos-defaults application-services
- Notes AppFW rules attach to security policy via application-firewall rule-set
- Warns about licensing (SecIntel/AppFW may require subscription)
- Routes raw config parsing to parsing-palo-configs if PAN-OS config is provided
- Does NOT commit AppFW config without approval

**Must not:**
- Claims SRX AppID is identical to PAN-OS App-ID (different implementations)
- Emits application-firewall config without explaining license requirement
- Bypasses parsing-palo-configs when raw PAN-OS config is input

## Scenario 3: Troubleshoot mDNS/SSDP cross-VLAN discovery failure

**Prompt:** mDNS service discovery isn't working between my IoT and home zones on SRX300

**Input:** None

**Must:**
- Recognizes multicast service discovery issue (mDNS port 5353, SSDP port 1900)
- Notes SRX zones block multicast by default
- Suggests junos-mdns and junos-ssdp predefined applications
- Explains permit policy alone is insufficient (multicast routing or reflection needed)
- References SKILL.md section on mDNS/SSDP across zones
- Does NOT recommend disabling firewall or opening any-any

**Must not:**
- Claims permit policy will pass multicast without additional config
- Recommends any-any allow rule
- Bypasses SRX300 platform verification (skill covers Branch platforms)

# srx-syslog-logging evals

Run each scenario in a fresh agent session with the skill installed, then again without it as a baseline. A scenario passes only when every "Must" holds and no "Must not" occurs.

## Scenario 1: Diagnose security logs not arriving at SIEM

**Prompt:** My SRX security logs aren't reaching the SIEM. System logs are fine.

**Input:** None

**Must:**
- Recognizes RE vs PFE logging split (system syslog = RE, security log = PFE)
- Asks whether security log source is fxp0 or revenue interface
- Warns that stream-mode security logs cannot originate from fxp0 (structural limit)
- Suggests checking `show security log` and `show security log stream` on device
- Notes system logs arriving = RE syslog path is working, but PFE path is separate
- Does NOT assume fxp0 will work for security logs

**Must not:**
- Claims fxp0 can send stream-mode security logs (wrong)
- Recommends rebooting device as first troubleshooting step
- Conflates system syslog (RE) with security log (PFE)

## Scenario 2: Configure security log stream to SIEM on non-default port

**Prompt:** Configure SRX to send security logs to 198.51.100.10 port 5140

**Input:** None

**Must:**
- Recognizes non-default syslog port (5140, not 514)
- Warns about non-default port trap: may be silently discarded on revenue interface
- References field notes on vSRX 25.4R1.12 behavior
- Suggests testing with default port 514 first
- Emits `set security log stream <name> host 198.51.100.10` config
- Notes stream transport options (UDP, TCP, TLS)
- Does NOT commit config without approval

**Must not:**
- Guarantees non-default port will work (field evidence says otherwise)
- Commits to device without approval
- Omits the non-default port warning

## Scenario 3: Choose between fxp0 and revenue interface for log source

**Prompt:** Should I use fxp0 or ge-0/0/0 as the log source for Security Director Cloud?

**Input:** None

**Must:**
- Recognizes Security Director Cloud onboarding requirement
- States stream-mode security logs cannot use fxp0 (PFE path limitation)
- Recommends revenue interface (ge-0/0/0 or equivalent) for security log stream
- Notes system syslog (RE) can use fxp0, but security log (PFE) cannot
- References SKILL.md section on RE vs PFE split
- Does NOT recommend fxp0 for security logs

**Must not:**
- Claims fxp0 works for both system and security logs (wrong for security stream)
- Omits explanation of RE vs PFE path difference
- Recommends mgmt_junos routing-instance without explaining when it applies

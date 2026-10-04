# srx-dynamic-ip-feed evals

Run each scenario in a fresh agent session with the skill installed, then again without it as a baseline. A scenario passes only when every "Must" holds and no "Must not" occurs.

## Scenario 1: Reboot Recovery Mode after routing-table pin

**Prompt:** My vSRX 24.4R1.9 saved config contains `set security dynamic-address feed-server debian-1 routing-table mgmt.inet`. Device activates Recovery Mode after reboot. What happened?

**Input:**
```
Committed and fetched feeds normally before reboot.
Post-reboot console shows Recovery Mode banner.
rollback 1 shows the routing-table pin.
```

**Must:**
- State that non-default feed-server `routing-table <instance>.inet` pin is NOT reboot-safe on vSRX 24.4R1.9
- Cite the field-observed failure: `routing table <instance>.inet cannot find` at boot validation
- Explain that interactive commit success does NOT prove reboot safety
- Recommend making feed server reachable through default routing instance and omitting the pin
- Reference the Routing Instance Reachability warning section

**Must not:**
- Suggest `event-options` workaround without Juniper-confirmed procedure and controlled cold-boot validation
- Recommend re-committing the same config (it commits interactively but still fails boot)
- Claim this is user error (it's a documented defect on this release)

## Scenario 2: Certificate validation hostname mismatch

**Prompt:** Feed download fails with `IPFD_DA_FEED_CERT_SUBJ_CHECK_FAIL`. Server cert is valid for debian-2.lab.local, URL is `https://192.0.2.10/feed.tgz`.

**Input:**
```
set security dynamic-address feed-server srv url https://192.0.2.10/feed.tgz
set security dynamic-address feed-server srv tls-profile IPFD_CA
set security dynamic-address feed-server srv validate-certificate-attributes subject-or-subject-alternative-names
```

**Must:**
- Identify hostname mismatch (URL uses IP, cert CN is debian-2.lab.local)
- Explain that certificate identity validation needs hostname matching cert CN/SAN
- Recommend using DNS or `system static-host-mapping debian-2.lab.local inet 192.0.2.10`
- Change URL to `https://debian-2.lab.local/feed.tgz`
- Reference "Production Pattern: Validate the Feed Server Certificate" section

**Must not:**
- Suggest disabling certificate validation (skill recommends production TLS)
- Recommend regenerating cert with IP SAN (using hostname is cleaner)
- Claim TLS is broken (it's validating correctly; hostname must match)

## Scenario 3: Feed file archived but not recreated

**Prompt:** Feed entries stopped updating. `show log messages | match ipfd` shows `succeeded<file not changed>` repeatedly. I updated feed-1/whitelist-1 but nothing changed.

**Input:**
```
Web server /var/www/html/feed-1/whitelist-1 updated with new IPs.
feed-1.tgz mtime is 3 days old (before the whitelist-1 edit).
nginx logs show repeated HEAD 200 responses, no GET.
```

**Must:**
- Identify that the archive was not recreated after feed file update
- Explain that SRX downloads the archive URL, not loose files
- Recommend re-running `tar czf feed-1.tgz feed-1/` after changing contents
- Note HEAD 200 with unchanged mtime/headers means SRX sees no update
- Reference common pitfall #3: "Updating feed files but not recreating the `.tgz`"

**Must not:**
- Suggest the SRX is broken (it correctly detects unchanged archive)
- Recommend changing update-interval (won't help; archive hasn't changed)
- Claim file-based feeds are automatically monitored (archive is the atomic unit)

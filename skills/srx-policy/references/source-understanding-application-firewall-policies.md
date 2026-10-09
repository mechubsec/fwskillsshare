# Inspired by: Understanding Application Firewall Policies

Source: Juniper Security Director documentation
URL: https://www.juniper.net/documentation/us/en/software/nm-apps24.1/junos-space-security-director/topics/task/junos-space-application-firewall-policy-creating.html
Retrieved: 2026-10-09 (HTTP 200; "Creating Application Firewall Policies")

The original concept-page URL (`.../topics/concept/junos-space-application-firewall-policies-overview.html`) now returns HTTP 404 (archived; no current equivalent located), so the URL above is the nearest current Junos Space task page. This original note records only concepts
corroborated by current Junos policy guidance; it does not reconstruct the page.

## Design takeaways

- Management UI objects must resolve to auditable device configuration and effective
  rule order; the controller view is not sufficient evidence by itself.
- Application-aware enforcement depends on signature state, classification timing,
  encrypted-traffic visibility, fallback actions, and the parent security policy.
- Publishing, device commit, and live enforcement are separate states to verify.

Inspect generated Junos configuration, commit result, AppFW and policy counters,
session classification, logs, and controller/device drift after deployment.

# Inspired by: Add a Web Filtering Profile in J-Web

Source: Juniper Networks, J-Web for SRX Series 23.2 documentation
URL: https://www.juniper.net/documentation/us/en/software/jweb-srx23.2/jweb-srx/topics/task/j-web-security-content-security-web-filtering-profile-adding.html
Retrieved: 2026-10-09 (HTTP 200; "Add a Web Filtering Profile | J-Web for SRX Series 23.2")

The earlier URL (`...-profile-add.html`) returned HTTP 404; the page lives at the `-adding` path above. This original note records only the
design questions that remain useful; it does not reconstruct the missing page.

## Operational takeaways

- A web-filtering profile defines service, category, action, fallback, and logging
  behavior; a profile alone has no traffic effect until a policy references it.
- GUI-created configuration should be reviewed in Junos CLI form before commit so
  profile names, policy attachment, and default actions are explicit.
- Verify platform, release, license, cloud reachability, and the supported filtering
  service using current Juniper documentation.

Test allowed, blocked, uncategorized, lookup-failure, and TLS cases. Inspect UTM
counters and logs rather than treating a successful commit as proof.

# Migration Workflow from Another Vendor

This reference describes the step-by-step workflow for migrating security policy from another vendor firewall platform to SRX global policy.

## Migration Steps

1. Parse the source firewall and preserve rule order, zones/interfaces, objects, services, applications, logging, and profiles.
2. Normalize source and destination zones to SRX zones.
3. Move static objects into `security address-book global`.
4. Convert services to Junos applications and application sets.
5. Convert vendor policy rows to `security policies global policy <ordered-name>` with `match from-zone` and `match to-zone` fields.
6. Preserve disabled rules as comments or inactive policies; do not silently drop them.
7. Map URL filtering / security profiles to NGWF, EWF, UTM, AppFW, SecIntel, ATP, IDP, or documented gaps. For Junos 23.4R1+ supported targets, prefer NGWF over EWF unless a documented constraint blocks it.
8. Put explicit denies before broad permits; add final logged deny.
9. If NAT exists, resolve post-NAT policy expectations with `srx-nat` before writing final policies.
10. Commit in a lab, generate traffic, and compare hit counts and session tuples against expected behavior.

For day-one SRX onboarding, first detect zone-pair contexts, then use the same workflow to rewrite them into one global table. Preserve order within each original context; separate contexts have no shared total order, so exact zone match fields preserve their independence. Because regular policies have lookup priority over global policies, plan removal or deactivation of migrated contexts as an approved cutover rather than leaving shadowing duplicates active.

## Policy Naming Convention

Use numeric prefixes for stable ordering and encode business intent rather than zone-pair relationships:

```text
010-DENY-THREAT-FEEDS
100-USERS-DNS
110-USERS-WEB-INSPECTED
200-SERVERS-ADMIN
900-TEMP-MIGRATION-EXCEPTIONS
999-DENY-REST
```

Avoid names that encode only zone pairs, such as `TRUST-TO-UNTRUST-1`, when the policy is global. Encode the business intent and keep numeric ordering stable.

---
name: srx-policy
description: Design, migrate, configure, audit, and troubleshoot Juniper SRX security policy on Junos 23.x+, including Branch SRX300/SRX400 platforms. Use when handling global or zone policy, address and application objects, AppID, AppFW, NGWF, EWF, SecIntel, ATP, logging, rule order, hit counts, default deny, or cross-VLAN mDNS and SSDP boundaries.
version: 1.3.1
author:
  - fastrevmd-lab
  - Claude
  - GPT
license: MIT
metadata:
  hermes:
    tags: [srx, junos, security-policy, global-policy, zone-policy, appid, appfw, application-firewall, web-filtering, ngwf, next-gen-web-filtering, enhanced-web-filtering, utm, secintel, atp, migration, mdns, ssdp, multicast, cross-vlan-discovery]
    related_skills: [parsing-srx-configs, srx-nat, srx-dynamic-ip-feed, srx-mnha, srx-mpls-in-flow]
  sources:
    - title: "Platform scope and service licensing (Branch validated 2026-09-12)"
      local: references/platform-and-licensing.md
    - title: Configuring Security Policies | Junos OS
      author: Juniper Networks
      url: https://www.juniper.net/documentation/us/en/software/junos/security-policies/topics/topic-map/security-policy-configuration.html
      retrieved: "2026-07-22"
    - title: Global Policy Overview | Junos OS
      author: Juniper Networks
      url: https://www.juniper.net/documentation/us/en/software/junos/security-policies/topics/topic-map/security-global-policies.html
      retrieved: "2026-07-22"
    - title: Security Policy Applications and Application Sets | Junos OS
      author: Juniper Networks
      url: https://www.juniper.net/documentation/us/en/software/junos/security-policies/topics/topic-map/policy-application-sets-configuration.html
      retrieved: "2026-05-15"
    - title: Configure Application Firewalling On A Juniper SRX
      author: Willem Redelijkheid
      url: https://www.redelijkheid.com/blog/2013/5/10/configure-application-firewalling-on-a-juniper-srx
      retrieved: "2026-05-15"
    - title: Juniper SRX Policy Configuration
      url: https://rayka-co.com/lesson/juniper-srx-policy-configuration/
      retrieved: "2026-05-15"
    - title: Juniper SRX Enhanced Web Filtering Configuration
      url: https://rayka-co.com/lesson/juniper-srx-enhanced-web-filtering-configuration/
      retrieved: "2026-05-15"
    - title: JNCIP-SEC – Configuring Juniper Enhanced Web Filtering
      url: https://blog.netpro.be/jncip-sec-configuring-juniper-enhanced-web-filtering/
      retrieved: "2026-05-15"
    - title: SecIntel Feeds Overview and Benefits
      author: Juniper Networks
      url: https://www.juniper.net/documentation/us/en/software/atp-cloud/atp-cloud-user-guide/topics/concept/secintel-feeds-overview-and-benefits.html
      retrieved: "2026-05-15"
    - title: Juniper SecIntel Datasheet
      author: Juniper Networks
      url: https://www.juniper.net/us/en/products/security/secintel-datasheet.html
      retrieved: "2026-05-15"
    - title: Getting Started with ATP Appliance and the SRX Series
      author: Juniper Networks
      url: https://www.juniper.net/documentation/us/en/software/atp-appliance/atp-appliance-srx-integration/topics/concept/atp-appliance-srx-integration-overview.html
      retrieved: "2026-05-15"
    - title: Juniper Advanced Threat Prevention datasheet
      url: https://www.networkscreen.com.au/datasheets/ds-advanced-threat-prevention.pdf
      retrieved: "2026-05-15"
    - title: Juniper NextGen Web Filtering Overview | Junos OS
      author: Juniper Networks
      url: https://www.juniper.net/documentation/us/en/software/junos/utm/topics/concept/next-gen-juniper-url-filtering-overview.html
      retrieved: "2026-05-15"
    - title: request security utm web-filtering category migrate-to-ng-juniper | Junos OS
      author: Juniper Networks
      url: https://www.juniper.net/documentation/us/en/software/junos/cli-reference/topics/ref/command/request-security-utm-web-filtering-category-migrate-to-ng-juniper.html
      retrieved: "2026-05-15"
    - title: Web Filtering Overview | Junos OS
      author: Juniper Networks
      url: https://www.juniper.net/documentation/us/en/software/junos/utm/topics/concept/utm-web-filtering-overview.html
      retrieved: "2026-05-15"
    - title: "[SRX] Configuring Next-Generation Web Filtering on SRX Devices"
      author: Juniper Networks Support Portal
      url: https://supportportal.juniper.net/s/article/SRX-Configuring-Next-Generation-Web-Filtering-on-SRX-Devices
      retrieved: "2026-05-15"
---

# SRX Security Policy

## Contents

- [Overview](#overview)
- [Enforced Global-Policy Output Contract](#enforced-global-policy-output-contract)
- [Runtime intake](#runtime-intake)
- [Recommended Architecture](#recommended-architecture)
- [Policy Evaluation and Rule Order](#policy-evaluation-and-rule-order)
- [Address Book Guidance](#address-book-guidance)
- [Applications and Application Sets](#applications-and-application-sets)
- [Application Firewall / AppID Pattern](#application-firewall--appid-pattern)
- [Web Filtering / UTM Attachment: Prefer NGWF, Treat EWF as Existing-Estate](#web-filtering--utm-attachment-prefer-ngwf-treat-ewf-as-existing-estate)
- [SecIntel and ATP Placement](#secintel-and-atp-placement)
- [Multicast and Service Discovery (mDNS/SSDP) Across Zones](#multicast-and-service-discovery-mdnsssdp-across-zones)
- [Migration Workflow from Another Vendor](#migration-workflow-from-another-vendor)
- [Pre-Return Self-Check](#pre-return-self-check)
- [Verification Commands](#verification-commands)
- [Troubleshooting Matrix](#troubleshooting-matrix)
- [Common Pitfalls](#common-pitfalls)
- [Verification Checklist](#verification-checklist)
- [Source Notes](#source-notes)

## Overview

Use this skill for Juniper SRX security policy design on Junos 23.x and newer, **including Branch platforms** (SRX300 and SRX400 series). It focuses on the policy layer that decides whether traffic is permitted, denied, logged, counted, or passed into security services such as AppID/AppFW, NextGen Web Filtering (NGWF), Enhanced Web Filtering (EWF), SecIntel, and ATP-backed protections.

**Branch scope, and its limit.** Core policy design is validated on Branch
hardware: zone-pair and global policies, `match dynamic-application` unified
policies, `default-policy deny-all`, address books and address-sets,
applications and application-sets, session logging and counters all validate on
an SRX345 running 26.2R1.7 (`commit check`, 2026-09-12 —
`docs/skill-tests/2026-09-12-srx-policy-branch-srx345-validation.md`). Treat the
policy layer as the same on Branch as elsewhere.

The **service attachments are a different matter and are not validated here.**
AppID/AppFW, NGWF, EWF, SecIntel, ATP and IDP/IPS are licence-gated, and the
Branch device used for validation held no licences, so those paths were
exercised only as far as the configuration schema. Read
`references/platform-and-licensing.md` before asserting that a service is
available on a given Branch platform and release, and say what is entitled
rather than assuming parity with a higher-end SRX.

## Enforced Global-Policy Output Contract

For greenfield, migration, and onboarding work, generated policy MUST use `security policies global`; express zones only as `match from-zone` and `match to-zone` fields inside each global policy. Do not preserve zone-pair structure merely because it appears in the input.

Use zone-to-zone output only after the caller explicitly opts into one of these exceptions and record the exception and affected rules in the result:

- existing-estate compatibility where structural change is outside scope;
- an isolated exception that is clearer and safer as a zone-pair policy;
- a customer standard or toolchain that requires zone-pair contexts.

Day-one SRX onboarding MUST detect `set security policies from-zone ... to-zone ...` contexts and rewrite them under `security policies global` by default. Preserve each source context's rule order, move its zones into match fields, verify semantic parity, and only remove or deactivate the legacy contexts with explicit approval and rollback protection. Read `references/zone-pair-to-global-example.md` for the complete detect-and-rewrite example.

Why global policy is the enforced generation target:

- Most vendor rulebases already behave like one ordered policy table with source zone, destination zone, source, destination, service/application, action, logging, and profiles as fields.
- Junos global policy lets a rule match one or more `from-zone` and `to-zone` values inside the policy itself.
- A global policy table avoids duplicating the same logical rule across every zone pair.
- It pairs naturally with the global address book and application/application-set objects.
- It is easier to review, diff, reorder, and migrate than many separate zone-pair contexts.
- It keeps AppFW, UTM/web-filtering, SecIntel, and ATP attachment decisions close to the logical rule instead of scattering equivalent controls across zone pairs.

Do not guess feature support. Before final design, verify platform, Junos release, licenses, and service package availability in current Juniper documentation / Pathfinder / Feature Explorer and on the device with `show version`, `show system license`, and relevant package/version commands.

## Runtime intake

Use this skill for SRX policy behavior after relevant configuration is identified. Use `parsing-srx-configs` for full-config extraction and `srx-nat` when translation changes the policy match.
Before acting, inspect the request, artifacts, and approved read-only evidence. If unresolved facts materially change safety, scope, correctness, confidence, or output, read `references/runtime-intake.md`. For each unresolved material fact whose catalog condition is true, invoke Claude `AskUserQuestion` or Codex `request_user_input` before continuing or issuing an open-ended request. Ask at most three single-select catalog questions per round. After each response, ask another round whenever any unresolved material catalog condition remains true; continue only when none remain. Do not repeat answered questions or show the full catalog. Without a native tool, present each selected catalog question with its 2-3 labeled choices and a free-text `Other` path in concise plain text; do not substitute a generic checklist. Never request secrets or unredacted customer data. Answers are context, not live-change approval; obtain separate explicit approval before configuration, commit, upgrade, reboot, delete, or failover.

## Recommended Architecture

### Preferred Greenfield / Migration Pattern

1. Build zones and routing cleanly.
2. Put reusable addresses and address sets in the global address book unless there is a specific reason for zone-local objects.
3. Normalize services into Junos applications and application sets.
4. Build one ordered global policy table under `security policies global`.
5. Match source and destination zones inside global policies.
6. Put narrow deny/reject/block rules first, then explicit permits, then a final logged default deny.
7. Attach AppFW / NGWF or EWF UTM / web-filtering / SecIntel / other application services only on permitted traffic that needs inspection.
8. Add logging and counts intentionally; log high-risk denies and important permits, but do not flood logs on high-volume noise without a reason.
9. Verify hit counts and live sessions after every policy import or reorder.

Read `references/zone-pair-to-global-example.md` for a complete ordered global table. Use multiple `match from-zone` and `match to-zone` statements only when one logical rule legitimately spans several zones with identical criteria and action; Juniper warns that careless multizone grouping can permit spoofed traffic.

### Explicit Zone-to-Zone Opt-Out

Use `security policies from-zone <zone> to-zone <zone>` only when the caller selects an exception in the enforced output contract. State why global policy is unsuitable, constrain the zone-pair scope, and keep all other generated rules global.

Do not treat a small rulebase, an existing zone-pair input, or a staged migration as an implicit opt-out. Repeated rules across zone pairs require a global rewrite unless the caller explicitly chooses otherwise.

## Policy Evaluation and Rule Order

SRX policy is first-packet session policy. The selected policy creates session state; later packets normally follow the session unless policy rematch or session clearing occurs.

**Evaluation order:** zone-pair (`from-zone ... to-zone ...`) policies are evaluated BEFORE global policies for a given flow. If a zone-pair policy table exists for the source/destination zone pair and a rule in that table matches, the global policy is never reached for that flow. A catch-all permit in a zone-pair policy blocks global-policy lookup entirely for that zone pair. Design accordingly: if you intend global policy to govern a zone pair, ensure no conflicting zone-pair policy table shadows it.

Baseline behavior:

- Zone-to-zone policy is organized by `from-zone` and `to-zone` context; each context has an ordered policy list.
- Global policy also matches source zone and destination zone, but the zone match is inside the policy rule.
- Rule order matters. Put specific denies and exceptions before broad permits.
- A policy match needs source address, destination address, and application. `any` is legal but should be explicit and reviewed.
- Policy action is normally `permit`, `deny`, or `reject`; permitted traffic can invoke application services.
- Security services such as UTM/web-filtering are attached under `then permit application-services ...` because they inspect allowed flows.
- The default behavior should be explicit deny with logging/counting where operationally useful.

**`insert` + append ordering pitfall.** `insert security policies ... policy X before/after Y` is relative to the **current** policy order at the moment it runs. When new policies are appended and *then* others are `insert`ed, an appended rule can end up **below the default-deny and be silently shadowed**. Real example: `300-CAST-TO-FIRETV` was appended, then `999-DEFAULT-DENY` was `insert`ed `after Allow_set_for_IoT-1`, which placed `300` *after* `999` — shadowing the exact rule being added. A clean `commit check` does not prove correct order. When mixing appended global policies with `insert ... before/after`, always re-verify the final order before commit:

```text
show configuration security policies global | display set
```

Policy changes can disrupt existing sessions because the policy database is recompiled and pushed to the forwarding plane. Juniper documents `set security policies lookup-intact-on-commit` as a way to reduce disruption on eligible platforms; check eligibility and memory before enabling it.

```text
show security policies lookup-intact-on-commit eligibility
show security policies lookup-intact-on-commit
```

## Address Book Guidance

Prefer global address-book objects for greenfield and migration designs:

```junos
set security address-book global address HOST-WEB-01 10.20.30.10/32
set security address-book global address-set WEB-SERVERS address HOST-WEB-01
```

Use zone-local address books only when the same name intentionally means different addresses in different zones or when preserving a legacy Junos config. Migration work is cleaner when object names are unique, global, and vendor-neutral.

Design rules:

- Use clear names that survive migration: `NET-USERS`, `APP-ERP`, `HOST-DC1-DNS`.
- Collapse many /32 objects into prefixes when the security intent is identical; Juniper notes policy memory consumption grows with addresses, applications, and zone contexts.
- Keep dynamic objects separate from static objects. For external feeds, use `srx-dynamic-ip-feed`.
- For NATed services, remember policy may see translated addresses depending on NAT type; load `srx-nat` when unsure.

## Applications and Application Sets

Junos policy requires an application match. Use predefined Junos applications when possible, custom applications when needed, and application sets to keep policies readable.

```junos
set applications application APP-TCP-8443 protocol tcp
set applications application APP-TCP-8443 destination-port 8443
set applications application-set APP-WEB application junos-http
set applications application-set APP-WEB application junos-https
set applications application-set APP-WEB application APP-TCP-8443
```

Guidance:

- Prefer application sets that represent business intent: `APP-USER-WEB`, `APP-DNS`, `APP-ADMIN-SSH`.
- Do not blindly translate every vendor service object into an individual Junos application if a predefined Junos application already exists.
- Use `show applications` to verify predefined application names.
- For application-identification / AppFW dynamic applications, verify AppID packages and signatures before policy activation.
- Avoid `application any` on broad permits unless the rule is intentionally coarse and protected by AppFW/UTM or other controls.

## Application Firewall / AppID Pattern

AppFW is not the same thing as the base policy `match application` field. Base policy applications are port/protocol applications. AppFW can match dynamic layer-7 application signatures and then permit or deny inside an already-permitted security policy.

Prerequisites to verify:

```text
show system license
show services application-identification version
request services application-identification download
request services application-identification download status
request services application-identification install
request services application-identification install status
show services application-identification application summary
show services application-identification group summary
```

Example AppFW rule-set attached to a global policy:

```junos
set security application-firewall rule-sets APPFW-STREAMING rule BLOCK-YOUTUBE-STREAM match dynamic-application junos:YOUTUBE-STREAM
set security application-firewall rule-sets APPFW-STREAMING rule BLOCK-YOUTUBE-STREAM then deny
set security application-firewall rule-sets APPFW-STREAMING default-rule permit

set security policies global policy 200-USERS-WEB match from-zone USERS
set security policies global policy 200-USERS-WEB match to-zone INTERNET
set security policies global policy 200-USERS-WEB match source-address NET-USERS
set security policies global policy 200-USERS-WEB match destination-address any
set security policies global policy 200-USERS-WEB match application APP-WEB
set security policies global policy 200-USERS-WEB then permit application-services application-firewall rule-set APPFW-STREAMING
set security policies global policy 200-USERS-WEB then log session-close
set security policies global policy 200-USERS-WEB then count
```

Verification:

```text
show security application-firewall rule-set APPFW-STREAMING
show services application-identification application summary | match <app>
show security policies hit-count
show security flow session source-prefix <client> extensive
```

Pitfall: if the base policy does not permit the flow, AppFW never gets a chance to inspect it. Conversely, if the base policy is `application any` and AppFW default-rule is `permit`, you may have built a broad allow with only a narrow AppFW deny.

## Web Filtering / UTM Attachment: Prefer NGWF, Treat EWF as Existing-Estate

Web filtering is policy-adjacent because the UTM policy is attached to an allowed security policy under `then permit application-services utm-policy`. For Junos 23.4R1+ greenfield designs and modern vendor migrations, strongly prefer Juniper NextGen Web Filtering (NGWF / `ng-juniper`) when the platform, release, license, and cloud connectivity support it. Treat Enhanced Web Filtering (EWF / `juniper-enhanced`) as an existing-estate, compatibility, or older-release path unless NGWF is unavailable.

Do not say EWF is deprecated unless a current Juniper deprecation notice is available. The safe wording is: NGWF is the newer preferred architecture for supported Junos 23.4R1+ designs; EWF remains a documented path for existing deployments and platforms/releases that cannot use NGWF.

Decision rule:

1. New Junos 23.4R1+ SRX/cSRX deployment: prefer NGWF.
2. Migration from Palo Alto, FortiGate, ASA/FTD, Check Point, or another vendor to modern SRX: prefer NGWF for URL/category/reputation controls unless a documented constraint blocks it.
3. Existing Junos estate already using EWF: keep EWF only for continuity, then plan EWF-to-NGWF migration after validating license, platform support, policy names, category mapping, cloud reachability, and maintenance window.
4. Older Junos releases or unsupported platforms: use EWF/local/redirect only as required by supportability.

Full NGWF and EWF configuration patterns, the SSL initiation profile, verification commands, and the EWF-to-NGWF migration commands/pitfalls are in `references/web-filtering-ngwf-ewf-patterns.md`. Key facts: NGWF starts in 23.4R1, uses the Juniper NGWF cloud with on-box caching, and is attached via `then permit application-services utm-policy`. Migration is asynchronous — schedule downtime and do not rename policies mid-migration.

Use conservative fallback behavior. If the cloud/reputation service is unavailable, decide deliberately whether to fail open (`permit` / `log-and-permit`) or fail closed (`block`) for the `default` fallback leaf, and set the granular fallback leaves (`server-connectivity`, `timeout`, `too-many-requests`) per traffic-class requirements rather than as a uniform global setting. Leaf-value note: `fallback-settings default log-and-permit` commits on current images (verified on vSRX 24.4R1 for both `ng-juniper` and `juniper-enhanced`); some older guidance restricts the `default` leaf to `permit`/`block` — validate on your target release.

Important IPv6 caveat from Juniper's policy documentation: Content Security for IPv6 sessions is not supported in the referenced policy documentation. If a policy uses wildcard `any` and Content Security features are enabled, use `any-ipv4` for the inspected policy and create separate IPv6 rules without unsupported Content Security services.

## SecIntel and ATP Placement

SecIntel and ATP-backed enforcement should complement deterministic policy, not replace it.

Use this layering order:

1. Deterministic segmentation: zones, routes, address objects, applications, explicit allow/deny.
2. Application-aware controls: AppID/AppFW where L7 application identity matters.
3. Web/content controls: NGWF preferred on 23.4R1+ (see the web-filtering section).
4. Dynamic intelligence: SecIntel feeds and ATP verdicts for malicious infrastructure, infected hosts, C&C, malware, and evolving threat indicators.
5. Logging and operations: hit counts, event logs, SecIntel/ATP dashboards, and incident workflow.

Design cautions:

- Verify subscriptions, ATP Cloud/Appliance connectivity, feed status, and platform support before promising behavior.
- Keep threat-intel blocks above broad permits when implemented as explicit policies or objects.
- For feed-based address objects maintained by your own HTTPS feed server, use the `srx-dynamic-ip-feed` skill.
- Avoid using SecIntel as a substitute for clean zone/app policy; it is an additional enforcement source.
- Treat community discussion and marketing datasheets as context, not authoritative configuration syntax.

Operational checks vary by deployment, but collect at least:

```text
show system license
show security policies hit-count
show security flow session source-prefix <source> extensive
show log messages | match "secintel|atp|utm|web-filter|threat"
```

For ATP Appliance integration, confirm the SRX-to-ATP integration workflow in the current ATP Appliance guide and validate that SRX submits data and consumes verdicts/feeds as designed.

## Multicast and Service Discovery (mDNS/SSDP) Across Zones

Read `references/service-discovery.md` when troubleshooting mDNS, SSDP, casting, or other discovery across routed VLANs. A permit policy alone cannot forward TTL-1 discovery traffic; the reference separates reflector or multicast-routing requirements from the post-discovery unicast policy.

## Migration Workflow from Another Vendor

Migrate by parsing source policy, normalizing zones/objects into SRX global constructs, converting to `security policies global`, preserving rule order and disabled rules, mapping security profiles to NGWF/AppFW/SecIntel (preferring NGWF for 23.4R1+ targets), and lab-validating with hit counts before production cutover. For day-one SRX onboarding, detect and rewrite zone-pair contexts into one global table with explicit cutover approval.

Complete workflow steps and policy naming convention are in `references/migration-workflow.md`.

## Pre-Return Self-Check

Before returning any generated or rewritten policy:

1. Search the proposed set-format output for `set security policies from-zone`; absent an explicit opt-out, this must return no matches.
2. Confirm every generated rule starts under `set security policies global policy` and carries intended `match from-zone` and `match to-zone` fields.
3. Compare the final global order with the source order within every original context; re-display it after any `insert` operation.
4. Confirm no active legacy zone-pair rule can match first. Use `show security match-policies global ...` for pre-cutover global checks, then test effective lookup after the approved cutover.
5. Report any exception, uncertainty, unsupported feature, or unconverted rule instead of silently returning zone-pair output.

## Verification Commands

Configuration review:

```text
show configuration security policies | display set
show configuration security policies global | display set
show configuration security address-book global | display set
show configuration applications | display set
show configuration security application-firewall | display set
show configuration security utm | display set
```

Policy counters and order:

```text
show security policies
show security policies detail
show security policies hit-count
show security policies hit-count from-zone <src-zone> to-zone <dst-zone>
clear security policies hit-count
```

The `from-zone` and `to-zone` hit-count filters are for zone-based policies only. Use the unfiltered command for global policies and identify the `junos-global` rows.

Sessions and flow:

```text
show security flow session source-prefix <source> extensive
show security flow session destination-prefix <destination> extensive
show security flow session | match "Session ID|Policy name|In:|Out:|NAT|Timeout"
```

Policy match prediction (no traffic required):

```text
show security match-policies from-zone <SRC_ZONE> to-zone <DST_ZONE> source-ip <SRC_IP> destination-ip <DST_IP> protocol <PROTO> source-port <SPORT> destination-port <DPORT>
```

This predicts which policy a flow will match without sending live traffic — useful for pre-commit validation and troubleshooting shadowed rules.

Applications and AppFW:

```text
show applications
show services application-identification version
show services application-identification application summary | match <name>
show services application-identification group summary | match <name>
show security application-firewall rule-set <rule-set-name>
```

Web filtering / UTM:

```text
show system license
show security utm web-filtering status
show security utm web-filtering statistics
show log messages | match "webfilter|web-filter|RT_UTM|URL_BLOCKED"
```

Commit and policy-change safety:

```text
show security policies lookup-intact-on-commit eligibility
show security policies lookup-intact-on-commit
commit check
commit confirmed 10
```

## Troubleshooting Matrix

| Symptom | Likely Cause | Check | Fix |
|---|---|---|---|
| Expected global policy not hit | Rule order, zone mismatch, address/application mismatch, or NAT changed destination | `show security policies hit-count`, session extensive | Move specific rule up, fix `match from-zone/to-zone`, address, app, or NAT expectations |
| New permit never matches despite a clean commit | Rule was appended below the default-deny because a later `insert ... before/after` reordered around it | `show configuration security policies global \| display set` | Re-`insert` the permit above the default-deny; re-dump final order before commit |
| Zone-to-zone policy hit instead of global design | Legacy policies remain active or evaluation expectation is wrong | Full `show configuration security policies` | Consolidate into global policy and remove/disable duplicates after testing |
| AppFW rule has zero hits | Base policy not permitting flow, AppID package missing, wrong dynamic app | AppID version, AppFW rule-set counters, session policy | Install AppID package, fix base policy, choose correct dynamic app/group |
| Web filtering attached but no filtering | UTM policy not under `then permit`, license/service unavailable, wrong profile, wrong engine type (`ng-juniper` vs `juniper-enhanced`), or cloud/DNS/routing issue | Web-filtering status/statistics, policy config, license, DNS/routing, logs | Attach UTM policy correctly, verify license/cloud/release, confirm expected NGWF/EWF type, fix profile and reachability |
| IPv6 policy commit error with content security | Content Security not supported for IPv6 in referenced docs | Commit error and policy match wildcard | Split IPv4 inspected policy using `any-ipv4`; create separate IPv6 policy without unsupported services |
| Migrated policy table is huge and repetitive | Zone-to-zone conversion copied one logical rule into many contexts | Count repeated source/destination/app/action rows | Rebuild as global policies with multi-zone matches where intent is identical |
| Existing sessions ignore policy change | Session state persists | Session table, policy-rematch expectations | Clear selected sessions or plan maintenance; use policy rematch features only when understood |
| Commit disrupts traffic | Policy database recompilation and forwarding-plane update | Change window logs, eligibility check | Stage changes, use `commit confirmed`, investigate `lookup-intact-on-commit` eligibility |
| Logs too noisy | Broad deny logs session-init for high-volume background traffic | Log volume and top talkers | Log important denies; rate-limit upstream; tune final deny logging carefully |

## Common Pitfalls

1. **Defaulting to zone-to-zone policy for migrations.** Generate `security policies global`; zone-pair output requires the caller's explicit opt-out and a recorded reason.

2. **Using global policy as an unstructured dumping ground.** Global policy still needs clear order, names, comments, and a final default deny.

3. **Hiding segmentation mistakes with multi-zone matches.** Multi-zone global rules are good when intent is identical; they are bad when they blur different risk zones.

4. **Forgetting NAT's effect on policy.** Destination/static NAT can change the destination before policy lookup. Load `srx-nat` when NAT and policy interact.

5. **Attaching UTM/AppFW to a deny policy.** Application services attach to permitted flows. Deny/reject rules block before those services inspect.

6. **Using `application any` everywhere.** Sometimes needed for migration parity, but it removes useful intent unless paired with AppFW/UTM and a clear reason.

7. **Trusting inaccessible or old articles as canonical.** If a source article is 404, JavaScript-only, or old lab material, corroborate with current Juniper docs and device CLI before encoding syntax.

8. **Ignoring license/package state.** AppID, enhanced web filtering, SecIntel, and ATP behavior can depend on licenses, subscriptions, cloud connectivity, and installed packages.

9. **Mixing IPv4 and IPv6 with content security blindly.** Use IPv4-specific inspected rules when Content Security is involved, and separate IPv6 rules if unsupported.

10. **Defaulting to EWF for new SRX designs, or calling EWF deprecated without evidence.** For Junos 23.4R1+ greenfield and modernization work, prefer NGWF when supported; keep EWF as an existing-estate or compatibility path. Say NGWF is newer/preferred for supported designs, but do not assert formal deprecation unless current Juniper documentation says so.

11. **Migrating EWF to NGWF without a window.** Juniper documents the migration as asynchronous and recommends downtime. Preserve policy names during migration because changing policy names can cause commit failure.

12. **Not verifying with live counters.** A clean commit is not proof of correct policy. Check hit counts, sessions, AppFW/UTM counters, and logs.

13. **Trusting `insert` order without re-dumping the final order before commit** — see 'Policy Evaluation and Rule Order'.

14. **Expecting a `permit` to fix cross-VLAN discovery** — see 'Multicast and Service Discovery'.

## Verification Checklist

- [ ] Platform and Junos release support the requested policy/security-service features.
- [ ] License/subscription/package state is verified for AppID, AppFW, web filtering, SecIntel, or ATP features.
- [ ] Generated/onboarded policy uses `security policies global`, or the caller's explicit zone-pair opt-out and affected rules are recorded.
- [ ] Pre-return search found no unintended `set security policies from-zone` output.
- [ ] Global address-book objects are used for reusable migrated objects.
- [ ] Applications/application sets express business intent and avoid unnecessary `any`.
- [ ] Rule order is explicit: denies/exceptions, permits, temporary migration exceptions, final deny.
- [ ] Logging and `count` are intentionally configured.
- [ ] UTM/AppFW services are attached only under `then permit` on the intended policies.
- [ ] For URL filtering on Junos 23.4R1+ supported targets, NGWF (`ng-juniper`) was preferred unless a documented constraint required EWF/local/redirect.
- [ ] If migrating EWF to NGWF, license/platform support, category migration status, unchanged policy names, and downtime window were planned.
- [ ] NAT interactions were reviewed with `srx-nat` where translated addresses affect policy lookup.
- [ ] IPv6 and Content Security support were reviewed before using wildcard `any` with UTM/content services.
- [ ] `commit check` and `commit confirmed` are used for risky changes.
- [ ] Hit counts and sessions prove that traffic matches the intended policy.
- [ ] Source extraction limitations in `references/source-index.md` were considered before relying on a non-authoritative article.

## Source Notes

This is an original operational playbook informed by the attributed reading list and
official Juniper policy documentation. The short source-note files under
`references/` are independently written “Inspired by” notes, not upstream page
copies, and do not relicense linked material. For the NGWF/EWF comparison, see
`references/ngwf-vs-ewf-research.md`.

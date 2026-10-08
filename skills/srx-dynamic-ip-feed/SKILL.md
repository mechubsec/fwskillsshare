---
name: srx-dynamic-ip-feed
description: Configure, audit, and troubleshoot Juniper SRX dynamic IP objects from HTTPS feeds. Use when handling feed archives, dynamic-address mapping, certificate validation, basic auth, mTLS, session scanning, routing-instance reachability, Recovery Mode after reboot, show security dynamic-address, ipfd logs, or feed and TLS failures. Use srx-policy for SecIntel feeds.
version: 1.0.5
author:
  - fastrevmd-lab
  - Claude
  - GPT
license: MIT
metadata:
  hermes:
    tags: [srx, junos, dynamic-address, feed-server, ipfd, feed-name, session-scan, mutual-tls, basic-auth, recovery-mode, reboot-safety, firewall, security-policy, pki, tls, nginx]
    related_skills: [parsing-srx-configs, srx-policy]
  sources:
    - title: SRX Dynamic IP Objects aka Feed-server
      author: Karel Hendrych
      url: https://community.juniper.net/blogs/karel-hendrych/2025/11/30/srx-dynamic-ip-objects-aka-feed-server
      retrieved: "2026-05-14"
      inspired_note: references/source-extract.md
---

# SRX Dynamic IP Feed Servers

## Contents

- [Overview](#overview)
- [Scope and routing](#scope-and-routing)
- [Runtime intake](#runtime-intake)
- [Prerequisites and Version Notes](#prerequisites-and-version-notes)
- [Feed Archive Layout](#feed-archive-layout)
- [Lab-Grade HTTPS Feed Server](#lab-grade-https-feed-server)
- [Production TLS and Authentication](#production-tls-and-authentication)
- [Applying Dynamic Objects in Security Policies](#applying-dynamic-objects-in-security-policies)
- [Session Scan Tunable](#session-scan-tunable)
- [Routing Instance Reachability](#routing-instance-reachability)
- [Verification Commands](#verification-commands)
- [Update Test Procedure](#update-test-procedure)
- [Troubleshooting Matrix](#troubleshooting-matrix)
- [Common Pitfalls](#common-pitfalls)
- [Verification Checklist](#verification-checklist)
- [Source](#source)

## Overview

SRX dynamic IP objects let Junos periodically download IPv4/IPv6 entries from an HTTPS feed server and expose those entries as address objects usable in security policies. This is useful when rule structure is stable but source or destination addresses change frequently through automation, threat intelligence, cloud inventory, orchestration systems, or allow/block lists.

The key SRX idea is:

1. The web server hosts a bundle archive, typically `.tgz`.
2. Inside the archive are feed files, each containing IPs/prefixes/ranges.
3. `security dynamic-address feed-server <server>` points to the archive URL.
4. `feed-name <name> path <path-inside-archive>` maps a feed to a file in the archive.
5. `security dynamic-address address-name <object> profile feed-name <feed>` exposes the feed as a policy address object.
6. Policies reference the dynamic address name as source or destination address.

SRX checks feed freshness with HTTP `HEAD`, downloads changed archives with `GET`, and updates dynamic objects without a commit. The default update interval is 5 minutes; the minimum is 30 seconds. Use production TLS validation and authentication whenever possible.

## Scope and routing

Use this skill for self-hosted dynamic-address feeds. Use `srx-policy` for Juniper SecIntel or ATP feeds and `parsing-srx-configs` for full-config extraction.

## Runtime intake

Use this skill only for feed-server dynamic address objects. Use `parsing-srx-configs` for full-config extraction and `srx-policy` when the policy match itself is in question. Before acting, inspect the request, artifacts, and approved read-only evidence. If unresolved facts materially change safety, scope, correctness, confidence, or output, read `references/runtime-intake.md`. For each unresolved material fact whose catalog condition is true, invoke Claude `AskUserQuestion` or Codex `request_user_input` before continuing or issuing an open-ended request. Ask at most three single-select catalog questions per round. After each response, ask another round whenever any unresolved material catalog condition remains true; continue only when none remain. Do not repeat answered questions or show the full catalog. Without a native tool, present each selected catalog question with its 2-3 labeled choices and a free-text `Other` path in concise plain text; do not substitute a generic checklist. Never request secrets or unredacted customer data. Answers are context, not live-change approval; obtain separate explicit approval before configuration, commit, upgrade, reboot, delete, or failover.

## Prerequisites and Version Notes

- SRX/vSRX running Junos with `security dynamic-address` feed support.
- A reachable HTTPS server that supports `HEAD` and `GET` against the feed archive URL.
- Feed archive in a format supported by Junos. This skill focuses on bundle archive `.tgz` mode.
- Feed file contents can include:
  - single IPs: `192.0.2.1`, `2001:db8::1`
  - prefixes: `192.0.2.32/28`, `2001:db8:1::/64`
  - ranges: `192.0.2.5-192.0.2.20`, `2001:db8::5-2001:db8::20`
- Junos 25.2 or later is required for the simple SRX username/password authentication feature described here.
- For production, prefer DNS/hostname feed URLs with certificate validation. If using static host mapping, ensure the hostname in the URL matches the certificate CN or SAN when certificate attribute validation is enabled.

## Feed Archive Layout

Use one directory per archive and one file per feed. Example:

```bash
cd /var/www/html
mkdir feed-1
printf '1.1.1.1\n' > feed-1/whitelist-1
printf '2.2.2.2\n' > feed-1/blacklist-1
tar czf feed-1.tgz feed-1/
```

The SRX maps the archive contents by path:

```text
feed-1.tgz
└── feed-1/
    ├── whitelist-1
    └── blacklist-1
```

SRX feed-name mapping:

```junos
set security dynamic-address feed-server debian-1 feed-name whitelist-1 path feed-1/whitelist-1
set security dynamic-address feed-server debian-1 feed-name blacklist-1 path feed-1/blacklist-1
```

Then expose each feed as a dynamic policy object:

```junos
set security dynamic-address address-name whitelist-1 profile feed-name whitelist-1
set security dynamic-address address-name blacklist-1 profile feed-name blacklist-1
```

## Lab-Grade HTTPS Feed Server

Use this only for labs because it does not validate the server certificate on SRX.

On Debian with nginx:

```bash
apt install nginx-light ssl-cert
make-ssl-cert generate-default-snakeoil
```

Enable the SSL listener in `/etc/nginx/sites-enabled/default`:

```nginx
listen 443 ssl default_server;
listen [::]:443 ssl default_server;
include snippets/snakeoil.conf;
```

Restart and test:

```bash
systemctl restart nginx
openssl s_client -connect localhost:443
```

Create a feed archive:

```bash
cd /var/www/html
mkdir feed-1
printf '1.1.1.1\n' > feed-1/whitelist-1
printf '2.2.2.2\n' > feed-1/blacklist-1
tar czf feed-1.tgz feed-1/
tail -f -n0 /var/log/nginx/access.log
```

SRX lab configuration:

```junos
set security dynamic-address feed-server debian-1 url https://10.0.0.10/feed-1.tgz
set security dynamic-address feed-server debian-1 update-interval 60
set security dynamic-address feed-server debian-1 hold-interval 604800
set security dynamic-address feed-server debian-1 feed-name whitelist-1 path feed-1/whitelist-1
set security dynamic-address feed-server debian-1 feed-name blacklist-1 path feed-1/blacklist-1
set security dynamic-address address-name whitelist-1 profile feed-name whitelist-1
set security dynamic-address address-name blacklist-1 profile feed-name blacklist-1
```

Commit and verify. The nginx access log should show an initial `GET`, then periodic `HEAD` probes. When the archive changes, SRX should perform another `GET`.

## Production TLS and Authentication

**Always validate the feed server certificate in production.** The lab-grade pattern above skips validation and is unsafe for production use.

Production deployments should:

1. **Certificate Validation (mandatory)**: Use a CA-signed certificate on the feed server, configure the SRX with the CA profile and SSL initiation profile, enable `validate-certificate-attributes subject-or-subject-alternative-names`, and ensure the URL hostname matches the certificate CN or SAN.

2. **HTTP Basic Authentication (optional)**: Requires Junos 25.2R1+. Configure nginx basic auth and supply SRX credentials via `user-name` and `password` under the feed-server configuration. HTTP 401 errors indicate missing or incorrect credentials.

3. **Mutual TLS Client Certificate Authentication (optional)**: Enforce client certificate success on nginx and configure the SRX with a local certificate referenced in the SSL initiation profile. HTTP 403 errors indicate missing or invalid client certificates.

Complete server-side and SRX-side configuration for all three patterns is in `references/tls-and-auth.md`.

## Applying Dynamic Objects in Security Policies

Dynamic address names become policy address objects and can be used as source or destination criteria.

Example blocklist policy:

```junos
set security policies from-zone trust to-zone untrust policy block-dynamic-bad-dst match source-address any
set security policies from-zone trust to-zone untrust policy block-dynamic-bad-dst match destination-address blacklist-1
set security policies from-zone trust to-zone untrust policy block-dynamic-bad-dst match application any
set security policies from-zone trust to-zone untrust policy block-dynamic-bad-dst then deny
set security policies from-zone trust to-zone untrust policy block-dynamic-bad-dst then log session-init
```

Example allowlist policy:

```junos
set security policies from-zone trust to-zone untrust policy permit-dynamic-good-dst match source-address any
set security policies from-zone trust to-zone untrust policy permit-dynamic-good-dst match destination-address whitelist-1
set security policies from-zone trust to-zone untrust policy permit-dynamic-good-dst match application junos-http
set security policies from-zone trust to-zone untrust policy permit-dynamic-good-dst then permit
set security policies from-zone trust to-zone untrust policy permit-dynamic-good-dst then log session-init
set security policies from-zone trust to-zone untrust policy permit-dynamic-good-dst then log session-close
```

Policy ordering still matters. Put deny/reject blocklist policies above broader permit policies when the blocklist must take precedence.

## Session Scan Tunable

SRX can reconcile existing sessions when addresses are added to dynamic feeds. Enable:

```junos
set security dynamic-address session-scan
```

Important behavior:

- Session scan works for policies with `deny` or `reject` action.
- It is useful when a newly added blacklist address should affect existing sessions.
- Removing an address from an allowlist does not automatically kill existing sessions by itself. If immediate teardown behavior is needed, add the address to a deny/reject feed at least temporarily so a deny/reject policy can match.

A common structure is:

1. `reject-http` or `deny-bad` policy matching `blacklist-1`
2. permit policy matching `whitelist-1`
3. final deny policy for everything else

## Routing Instance Reachability

**Warning — non-default feed-server routing-table pins are not reboot-safe on vSRX 24.4R1.9.** A saved configuration containing `security dynamic-address feed-server <server> routing-table <instance>.inet` can commit and fetch normally after the table already exists, yet fail normal boot validation with `routing table <instance>.inet cannot find`. The device can then activate Recovery Mode and load its rescue configuration. A successful interactive commit is not reboot-safety proof; this failure was field-observed on 18 devices ([upstream issue #18](https://github.com/mechubsec/fwskillsshare/issues/18)).

**Preferred reboot-safe path:** make the feed server reachable through the default routing instance and omit the feed-server `routing-table` statement. On the affected release, devices using the same feed server without the pin booted normally.

For diagnosis only, the interactive syntax was live-verified as `<instance>.inet`, without the normal trailing `.0`; `<instance>.inet.0` and `inet.0` were rejected, while bare `inet` and `<instance>.inet` were accepted. Committing the routing instance first only satisfies the interactive commit dependency; it does not make the saved configuration boot-safe.

`event-options` is an **unsupported/unverified** workaround for this defect. Juniper documents that an event policy can [change and commit configuration](https://www.juniper.net/documentation/us/en/software/junos/automation-scripting/topics/concept/junos-script-automation-event-policy-change-configuration-overview.html), but not a supported boot trigger/order that waits for this routing table and avoids persisting the pin into the next boot. Do not present it as reboot-safe without a Juniper-confirmed procedure for the exact platform/release and controlled cold-boot validation with console and rollback protection.

Juniper documents the Recovery Mode banner, `UI_DEVICE_IN_RECOVERY_MODE`, and that immediately after recovery `rollback 1` contains the failed configuration in [Rescue and Recovery of Configuration File](https://www.juniper.net/documentation/us/en/software/junos/junos-install-upgrade/topics/topic-map/rescue-and-recovery-config-file.html).

## Verification Commands

After commit, check feed-server and feed status:

```text
show security dynamic-address summary
```

Look for:

- server name and URL
- update interval and hold interval
- TLS profile and user name fields
- feed names mapped to dynamic address names
- total IPv4/IPv6 entries
- download/db/other error counters
- next update and expiration times
- last update status

List loaded dynamic address records:

```text
show security dynamic-address
```

Check feed downloader logs:

```text
show log messages | match ipfd
```

Expected successful log patterns include:

```text
IPFD_DA_FEED_HTTPS_STATUS: Feed(<feed>) download data(<url>) status (succeeded)
IPFD_DA_FEED_HTTPS_STATUS: Feed(<feed>) download data(<url>) status (succeeded<file not changed>)
```

On the web server, tail access logs:

```bash
tail -f -n0 /var/log/nginx/access.log
```

Expected web access pattern:

```text
GET /feed-1.tgz HTTP/1.1 200
HEAD /feed-1.tgz HTTP/1.1 200
HEAD /feed-1.tgz HTTP/1.1 200
```

When the archive changes, expect a `HEAD` followed by a `GET`.

## Update Test Procedure

Read `references/feed-update-test.md` when validating that feed changes propagate without a configuration commit.

## Troubleshooting Matrix

| Symptom | Likely Cause | What to Check |
|---|---|---|
| No entries in `show security dynamic-address` | Feed file empty, path mismatch, archive mismatch, download failure | `show security dynamic-address summary`, `show log messages \| match ipfd`, archive paths with `tar tzf` |
| HTTP 401 in ipfd logs | Basic auth enabled on server but SRX has no/wrong credentials | `user-name`, `password`, nginx htpasswd file |
| HTTP 403 in ipfd logs | mTLS enforced but SRX has no/invalid client certificate | local certificate load/verify, SSL initiation profile `client-certificate`, nginx client CA |
| SSL peer certificate error | Missing/untrusted CA or server cert validation failure | CA profile, loaded CA cert, SSL initiation profile trusted CA |
| `IPFD_DA_FEED_CERT_SUBJ_CHECK_FAIL` | URL hostname does not match server cert CN/SAN | Use correct DNS/static-host-mapping and URL hostname, regenerate cert if needed |
| Initial GET works but updates do not | Archive not recreated, mtime/headers not changing, HEAD handling issue | Recreate `.tgz`, nginx logs, check HEAD 200 responses |
| Feed unreachable only from SRX | Routing or source path issue | static route/default route, routing-instance `routing-table`, DNS/static-host-mapping |
| Device reverts to an older/rescue configuration after reboot; Recovery Mode banner or `UI_DEVICE_IN_RECOVERY_MODE` appears | Saved non-default feed-server `routing-table <instance>.inet` pin failed normal boot validation | Use console or protected out-of-band access; inspect `rollback 1` and boot/commit logs for `routing table ... cannot find` as diagnostic evidence only; require explicit change approval, a rollback plan, and post-change verification before any recovery/configuration write |
| Old sessions still pass after feed change | Existing sessions not being reconciled | Consider `set security dynamic-address session-scan`; use deny/reject policies for blacklist entries |
| Scale concerns | Platform limits or PFE update time | `/var/log/ipfd`, platform capacity, staged performance testing |

## Common Pitfalls

1. **Using IP URLs in production with certificate validation.** Certificate identity validation needs a hostname that matches the certificate CN/SAN. Use DNS or `system static-host-mapping` and put the hostname in the feed URL.

2. **Forgetting that `feed-name path` is the path inside the archive.** If the archive contains `feed-1/blacklist-1`, configure that full path, not only `blacklist-1`.

3. **Updating feed files but not recreating the `.tgz`.** SRX downloads the archive URL, not the loose files. Re-run `tar czf feed-X.tgz feed-X/` after changing contents.

4. **Assuming removal from an allowlist kills sessions.** Dynamic address updates affect policy matching, but existing sessions may persist. Use session scan plus deny/reject feed design where immediate teardown is required.

5. **Setting too aggressive update intervals without considering server and fleet load.** The minimum can be 30 seconds, but many SRXs polling many feeds can create avoidable server load.

6. **Treating lab TLS as production TLS.** A self-signed server without SRX validation is useful for proving feature behavior, not for production security.

7. **Using revocation-check disable without understanding risk.** The demo disables revocation checking for simplicity. Production PKI should explicitly decide CRL/OCSP behavior.

8. **Leaking feed-server credentials.** SRX basic auth passwords and private keys should not be pasted into chat/logs/tickets. Use redaction and credential-handling practices.

9. **Treating an interactive commit as reboot-safety proof.** A non-default feed-server routing-table pin can commit and operate normally but still trigger Recovery Mode at the next boot. Prefer default-instance reachability and omit the pin.

## Verification Checklist

- [ ] Feed archive URL is reachable from the SRX routing context.
- [ ] Web server returns HTTP 200 for `GET` and `HEAD` against the archive URL.
- [ ] Archive contains expected paths: `tar tzf feed-X.tgz`.
- [ ] `feed-name <name> path <archive/path>` matches archive contents exactly.
- [ ] `address-name <object> profile feed-name <feed>` exists for every policy object.
- [ ] TLS CA profile is loaded and verified when certificate validation is used.
- [ ] URL hostname matches server certificate CN/SAN when certificate attribute validation is enabled.
- [ ] Basic auth credentials or client certificate are configured if the server requires them.
- [ ] `show security dynamic-address summary` shows zero download errors and expected entry counts.
- [ ] `show security dynamic-address` shows expected IPs/prefixes/ranges.
- [ ] Policies reference dynamic address names in correct source/destination fields and correct order.
- [ ] `show log messages | match ipfd` shows succeeded or succeeded<file not changed>.
- [ ] Server logs show expected GET/HEAD behavior.
- [ ] Update test confirms changed archive contents appear without commit.
- [ ] Persistent configuration omits non-default feed-server `routing-table <instance>.inet`; a successful interactive commit and healthy feed are not reboot-safety proof.
- [ ] Any exception is recorded as unsupported/unverified until Juniper confirms the exact platform/release procedure and a controlled lab cold boot passes with console and rollback protection; never validate first in production.

## Source

This skill is a condensed, operationalized SRX playbook based on Karel Hendrych's Juniper Community TechPost, “SRX Dynamic IP Objects aka Feed-server,” published 2025-11-30:

https://community.juniper.net/blogs/karel-hendrych/2025/11/30/srx-dynamic-ip-objects-aka-feed-server

An independently written `Inspired by` note is stored at
`references/source-extract.md`; it preserves attribution and verification
implications without reproducing the TechPost.

# Gotchas (all hit in a real 26.2.1 build)

- **No libvirt on Proxmox** → don't run `launch-vm.sh`; import qcow2s into `qm`.
- **`.bin --no-run` is the disk source**, not the `.tgz` (whose payload is encrypted).
- **Flavor/config-ID prompt** is easy to miss when scripting answers — it has no
  default and loops on invalid input; a short answer list desyncs here.
- **Boot order must be a separate `qm set`** after disks attach (else `net0;ide2`).
- **NTP must be reachable** — an internet NTP behind a site that blocks outbound 123
  hangs first boot; use an internal NTP. SD egresses via its default gateway, so a
  plain reachable internal server needs no extra routes.
- **There is no documented gateway-only CLI command.** The documented
  `set ipaddress change <IP>` workflow prompts for management IP, netmask, and
  gateway. For the verified 26.2.1 wrong-seed incident, preserving the failed
  guest and rebuilding from corrected seed data with fresh disks is the
  conservative recovery policy—not a claim about universal vendor behavior.
- **Every DNS server must actually answer DNS.** A non-resolving entry (ping/NTP-only
  host) loops first boot on `DNS address is not connectable` — the appliance boots,
  applies config, but never pulls the bundle (0 requests to the bundle server).
  Fix = correct the DNS in `kvm-env.ini` and rebuild the ISO (re-run `--no-run`),
  swap the cdrom, reboot; disks/imports stay. Diagnose via the VGA console
  (`qm monitor <vmid>` → `screendump`) — it names the unreachable server.
- **Log transport is TLS on TCP/6514** (not UDP/514). A plain TCP connect does
  not pass preflight; require a successful TLS handshake from every selected
  revenue source. Permit tcp/6514 through every transit FW, and **source-NAT on
  the FW that fronts SD** — TLS is
  bidirectional and SD's only route off its subnet is its default gateway, so it
  can't reply to a device's fabric IP. Verify: the FW session shows `In` AND `Out`
  packets both non-zero.
- **A skewed device clock looks exactly like a working log pipeline.** The mTLS
  stream connects, the collector acknowledges the payloads, the FW session shows
  `In` and `Out` non-zero — and the traffic logs still never appear in the SD
  GUI. Seen with SRXs ~375 s behind; the logs surfaced only after NTP was fixed
  and fresh traffic generated. Every transport check you would reach for passes,
  so gate on NTP **before** onboarding (§4a) rather than debugging the stream.
- **The machine running the browser must have the correct time.** A client clock
  skewed more than the ~30-minute IAM token lifetime makes the GUI unusable in a
  way that looks like a broken login: you sign in, the SPA loads its shell and
  locale files, and then it drops you straight back to the login screen with no
  error. The IAM tokens are `iat`/`exp` 1800 s apart and the portal compares
  `exp` against the **local** clock, so a freshly minted token reads as already
  expired and the app signs itself out. **The signature that saves the hunt:**
  server-side everything says success — `authenticate:: User <x> authentication
  was successful`, a full `GenerateToken` IDToken + RefreshToken pair, an
  `Audit log for operation User Login`, a `chat_token_request` (the app shell
  really did start), and every gateway request `200`. The bounce is entirely
  client-side. Check the clock on the workstation before touching the network:
  this presents identically whether the browser reaches SD over a firewall DNAT
  or a straight TCP proxy, survives a private window, and affects every account,
  which sends you chasing paths, certificates, sessions, and MTU for hours.
  Read the evidence with `show logs pod <iam-pod>` (namespace `atom-iam`) and
  `tail /var/log/pods/atom-api-gateway_ambassador-*/ambassador/0.log <n>` from
  the appliance CLI — the gateway access log also carries the client
  User-Agent, which is how you spot that the failing workstation is a different
  browser/machine from the one that works.
- **`lo0` is NOT a selectable log source** — SD's picker lists only physical
  revenue interfaces. For tunnel-managed branches pick the **LAN** port (subnet the
  gateway routes back over the tunnel), **not the WAN** (on the shared underlay the
  gateway reaches directly) — a WAN source is asymmetric (forward via tunnel, reply
  via underlay) so the branch drops the SYN-ACK (`Out:0`). Also keep the source IP
  in the gateway's source-NAT range.
- **Device-connection (VIP:7804) needs the same source-NAT** as logs for
  tunnel-managed branches — NAT both the device-connection VIP and the log VIP, or
  branch adoption hangs at `In:1 / Out:0` (no return path to the branch subnet).
- **A stuck `outbound-ssh` session survives the fix that should have healed it.**
  After you repair a transit path (policy, route, NAT) underneath a client that
  has been retrying for a long time, the TCP session comes up — `show system
  connections` shows `ESTABLISHED` to `<device-VIP>:7804`, the wire shows
  byte-symmetric traffic with the EMS replying, the cert is valid and the clock
  is in sync — and the device still sits at **status unknown** in the GUI. Every
  transport check passes; the session itself is half-adopted. Recovery is to
  force a brand-new session **without leaving a permanent config change**:

  ```
  delete system services outbound-ssh client <EMS-client-name>
  commit confirmed 1        # then DO NOT confirm — let it roll back
  ```

  Junos tears the session down, restores the stanza (secret included) when the
  timer expires, and the client reconnects from a **new source port**; the EMS
  re-adopts it. Prefer this over `deactivate`/`activate`: one operation, no
  second commit to forget, and a forgotten step self-heals instead of stranding
  the device.

  Two things that make this look broken while it is working: the rollback fires
  roughly **90 s** after the commit, not exactly 60, and for ~20 s of that window
  the device has **no `outbound-ssh` config at all** — a status check landing in
  that gap reads as a failed restore. Confirm recovery by the **new source
  port**, not by the mere presence of a session. Same mechanism and same fix on
  **Security Director Cloud** — the client is `outbound-ssh` to an EMS either way.
- **MNHA:** each node has an independent config (configure the route on both);
  only the active node logs (backup is idle, streams on failover).
- **SD auto-generates and installs the device certs (`sd_ca` + `sd_local`) on
  onboarding — but only if the secmgt cert controller is already up.** There is
  **no manual "install certificate" action** in the GUI or a generate API (the
  `install_*_certificate` endpoints are multipart BYO-cert uploads). Devices
  onboarded in the **first ~2 minutes after the appliance's first boot** miss
  the cert step: standalones stick at `certificate_ready:false` (no `sd_local`
  at all), and cluster/MNHA devices get a cert the **log collector rejects at
  the TLS layer** — the stream flaps with `RTLOG_CONN_ERROR: Com 85 abort`,
  reconnecting endlessly. **Fix (both cases):** delete the SD device entry
  (`POST /api/v1/devices/remove` — allowed even when `POST /api/v1/devices/sync`
  BulkSync is token-capability-denied with 403) and re-create BROWN_FIELD; the
  cert regenerates and installs within ~60 s on re-adopt. **For MNHA/chassis
  cluster, delete the cluster entry** (it cascades to the children) and
  recreate — deleting a child entry instead leaves the cluster on its
  rejected cert.
- **Disks are virtio (`virtio0/1/2`), machine q35** per the generated XML.
- The `--no-run` "not enough disk space (thick)" message is benign under thin.
- **Flavor is validated as a WHOLE SET on every boot — you cannot partially
  resize.** SD checks CPU + RAM + all three disk sizes against the supported
  flavor table (26.2.1: `8/64/200+250+500`, `16/80/200+400+1536`,
  `40/208/200+525+3584`). Bumping only CPU/RAM (e.g. 8/64 → 16/80 while leaving
  the flavor-1 disks) yields **"Unsupported CPU/Memory/Disk configured"** on the
  console and **RKE2 never starts** (`kubectl`/CLI: `connection to 127.0.0.1:6443
  refused`). To move flavors you must resize CPU, RAM, AND grow the data disks to
  the target row (a real storage migration, not just `qm resize`). Recovery:
  power off, set all resources back to the installed flavor, power on. So to
  relieve memory pressure on flavor 1, tune log volume/retention instead of
  adding RAM — or plan a full flavor-2 migration.

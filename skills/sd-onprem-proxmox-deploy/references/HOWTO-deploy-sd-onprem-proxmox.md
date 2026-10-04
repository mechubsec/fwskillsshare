# How-To: Deploy Security Director On-Prem 26.x on Proxmox VE

## Contents

- [1. Architecture in one paragraph](#1-architecture-in-one-paragraph)
- [2. Prerequisites](#2-prerequisites)
- [3. Mandatory predeployment connectivity STOP gate](#3-mandatory-predeployment-connectivity-stop-gate)
- [4. Extract artifacts (`--no-run`)](#4-extract-artifacts---no-run)
- [5. Build the Proxmox VM](#5-build-the-proxmox-vm)
- [6. First boot + verify](#6-first-boot--verify)
- [7. Onboard Junos/SRX devices](#7-onboard-junossrx-devices)
- [8. The log path (the hard part)](#8-the-log-path-the-hard-part)
- [9. Gotchas (all hit in a real build)](#9-gotchas-all-hit-in-a-real-build)
- [10. Operations](#10-operations)
- [11. Rollback](#11-rollback)

> **Product note — read first.** This guide is for **Security Director On-Prem
> 25/26**, Juniper's **new ATOM-based appliance** that runs on single-node RKE2
> Kubernetes. It is **NOT Junos Space Security Director** and shares nothing with
> it. There is **no device "schema install"** step, no Space fabric. Version
> parity (device 26.x + SD 26.x) is not a schema concern. Ignore all Space-era
> Security Director documentation.

Proven end-to-end on **SD On-Prem 26.2.1-5348**, Proxmox VE 9.2, managing Junos
26.2R1.7 vSRX (incl. MNHA pairs). Values in `<angle brackets>` are site-specific;
the worked example uses the remote lab (SD subnet `198.51.100.0/21`; managed-device
subnet `203.0.113.0/24`).

---

## 1. Architecture in one paragraph

SD On-Prem ships as a **KVM appliance**: an OS boot disk + two data disks (config,
logs) + a seed ISO that carries first-boot config. Inside, it's the Juniper
**ATOM microservices platform** on **RKE2 Kubernetes** — ~70 pods including
OpenSearch (log/event store), two Kafka buses, PostgreSQL/Patroni, Redis, and the
`jingest` log parser. Juniper's supported install targets a libvirt/virsh host,
but Proxmox has no `libvirtd`, so we **extract the qcow2 disks + ISO with the
software `.bin --no-run`** and **import them into a `qm`-native VM**.

---

## 2. Prerequisites

**Artifacts (both required for a fresh install):**

| File | Role |
|---|---|
| `Juniper-Security-Director-<ver>-<build>-kvm.bin` (~6 GB) | Embeds **disk-0** (OS, sha256-verified). `--no-run` extracts artifacts (disks + seed ISO) without KVM. This is the fresh-install extractor on Proxmox. |
| `Juniper-Security-Director-<ver>-<build>.tgz` (~8 GB) | The **encrypted** software bundle the VM pulls + decrypts at first boot. Triple-nested & encrypted — you **cannot** hand-extract qcow2s from it. It is not the disk source; the `.bin` is. |

> Common misread: "the `.bin` is only for upgrades, just use the `.tgz`." False for
> a fresh Proxmox install — you need **both**.

**Flavors (26.2.1) — pick one; the WHOLE ROW is enforced (see §9):**

| Flavor | vCPU | RAM | OS disk | Config disk | Log disk |
|---|---|---|---|---|---|
| 1 | 8 | 64 GB | 200 G | 250 G | 500 G |
| 2 | 16 | 80 GB | 200 G | 400 G | 1.5 T |
| 3 | 40 | 208 GB | 200 G | 525 G | 3.5 T |

**Four IP addresses in the SAME subnet:** management/CLI, UI VIP, device-connection
VIP, log-collector VIP. Plan them contiguously (e.g. `.19/.20/.21/.22`).

**Reachable NTP + DNS from the SD subnet** — and verify by *protocol*, not ping
(see §3). SD requires NTP at first boot.

This is the **appliance's** clock. The **managed SRXs' clocks are a separate
prerequisite** with its own gate at §7.0 — satisfying one says nothing about the
other, and a skewed device clock breaks log visibility in a way that every
transport-level test still passes.

**`--no-run` host dependencies:** `qemu-img`, `genisoimage`/`mkisofs`, `column`,
`cracklib-check` (Debian: `cracklib-runtime`), `sha256sum`. (Proxmox 9 has all but
`cracklib-runtime` — `apt install cracklib-runtime`.)

---

## 3. Mandatory predeployment connectivity STOP gate

> **STOP. Do not run `--no-run`, create a VM, import a disk, or boot SD until this
> section passes for every managed firewall.** Proxmox-host reachability is not
> SD reachability when the host and guest use different sources or gateways.

### 3.1 Prove the routing design on paper

Create one row per firewall and per traffic direction. Every row must name the
target, exact source, gateway, transit hops, zones/policy, NAT, return route, and
service ports:

| Firewall/path | Exact source | Target + service | Source gateway | Transit hops | Zones + permit policy | NAT | Return route | Test evidence |
|---|---|---|---|---|---|---|---|---|
| `<fw>-discovery` | `<SD-mgmt-IP>` | `<fw-mgmt-IP>:TCP/22` | `<SD-gateway>` | `<hop list>` | `<from/to + rule>` | `<none/SNAT>` | `<to translated/original source>` | `<SSH banner + In/Out>` |
| `<fw>-device` | `<device-management-source>` | `<device-VIP>:TCP/7804` | `<device-gateway>` | `<hop list>` | `<from/to + rule>` | `<none/SNAT>` | `<to translated/original source>` | `<listener + In/Out>` |
| `<fw>-logs` | `<revenue-source>` | `<log-VIP>:TCP/6514 TLS` | `<device-gateway>` | `<hop list>` | `<from/to + rule>` | `<none/SNAT>` | `<to translated/original source>` | `<TLS handshake + In/Out>` |
| `bundle` | `<SD-mgmt-IP>` | `<exact HTTP URL or SCP endpoint/path>` | `<SD-gateway>` | `<hop list>` | `<from/to + rule>` | `<none/approved translation>` | `<to observed source>` | `<full retrieval + identity + In/Out>` |

For a stateful firewall, "`permit` exists" is insufficient. Its route lookup,
security policy, and source NAT must agree in both directions. If source NAT is
used, SD must return to the translated on-subnet address; otherwise it must have
a route to the original device source.

### 3.2 Test from the exact proposed SD source

Use a disposable probe VM on the selected Proxmox bridge, or a temporary network
namespace/veth attached to that bridge. Configure the **exact** planned SD
management IP/prefix and default gateway. Ensure the address is free and no SD VM
is running with it. One namespace pattern is:

```bash
ip netns add sd-preflight
ip link add sdpf-host type veth peer name sdpf0
ip link set sdpf-host master <bridge>
ip link set sdpf-host up
ip link set sdpf0 netns sd-preflight
ip -n sd-preflight link set lo up
ip -n sd-preflight link set sdpf0 up
ip -n sd-preflight address add <SD-mgmt-IP/prefix> dev sdpf0
ip -n sd-preflight route add default via <SD-gateway>
ip -n sd-preflight route
ip netns exec sd-preflight traceroute -n <firewall-mgmt-IP>
ip netns exec sd-preflight ssh-keyscan -T 5 <firewall-mgmt-IP>
ip netns exec sd-preflight dig +time=2 +tries=1 @<DNS-IP> example.com
ip netns exec sd-preflight chronyd -Q -t 5 "server <NTP-IP> iburst"
```

Use the site's installed NTP client (`chronyd -Q`, `ntpdate -q`, or `sntp`) and
require a valid NTP reply. Ping or a generic UDP probe is not an NTP test. Repeat
the SSH/management-service probe for **every** firewall; a successful test to one
subnet does not prove another routed or tunneled target.

If the namespace cannot faithfully use the production bridge/VLAN, use a small
disposable VM instead. Never substitute a test sourced from the Proxmox host.

### 3.3 Prove the exact configured bundle path without exposing seed secrets

Complete this before extraction. Choose exactly one branch below and test the
same method that will be seeded into the appliance.

#### Direct HTTP branch

The restricted-server pattern in this guide
requires **direct HTTP with no SNAT and no HTTP proxy**, so both nftables and the
application server observe the original SD management IP. Fully retrieve the
exact URL from the source-identical `sd-preflight` probe. Record authentication
as intentionally `N/A`, readability, filename, expected byte size or vendor
checksum, route, policy, `NAT=none`, return path, and bidirectional session
counters. A Proxmox-host read does not count.

If only SNAT/proxy delivery is possible, STOP. Do not merely allow a translated
or shared proxy IP: that weakens the `/32` source boundary and tests a different
path. Create a separately approved authenticated design that records original
and server-observed source addresses, then preflight the exact configured method.

For HTTP, **never serve `<base>` or `<base>/<version>`**. Those directories contain
`kvm-env.ini`, which can contain plaintext CLI/SCP credentials, plus XML, qcow2,
and ISO artifacts. Mode `0600` does not protect a file from a Python process
running as its owner. Run the following blocks in one approved privileged shell
so cleanup-trap state persists. Create a dedicated webroot containing only the
`.tgz`:

```bash
set -euo pipefail
SD_BUNDLE_SOURCE=/var/lib/vz/sd-onprem/Juniper-Security-Director-<ver>-<build>.tgz
SD_BUNDLE_ROOT=$(mktemp -d /var/lib/vz/sd-bundle-only.XXXXXX)
SD_BUNDLE_NAME=$(basename -- "$SD_BUNDLE_SOURCE")
SD_BUNDLE_SERVER=/path/to/sd-onprem-proxmox-deploy/scripts/serve_bundle.py
SD_BUNDLE_HOST_IP=<approved-host-IP>
SD_BUNDLE_PORT=8085
SD_SOURCE_IP=<SD-mgmt-IP>
SD_BUNDLE_LOG=$(mktemp /var/tmp/sd-bundle-http.XXXXXX.log)
SD_BUNDLE_PID=
SD_BUNDLE_NFT_TABLE=sd_bundle_gate_$$
SD_BUNDLE_NFT_CREATED=false
SD_BUNDLE_ALLOW_COUNTER=sd_bundle_allowed
SD_BUNDLE_DROP_COUNTER=sd_bundle_dropped
SD_APPROVED_EVIDENCE=/path/to/approved/sd-bundle-evidence.txt

# A hard link avoids a second multi-GB copy and exposes only this filename.
case "$SD_BUNDLE_NAME" in *.tgz) ;; *) exit 1 ;; esac
ln -- "$SD_BUNDLE_SOURCE" "$SD_BUNDLE_ROOT/$SD_BUNDLE_NAME"
test "$(find "$SD_BUNDLE_ROOT" -mindepth 1 -maxdepth 1 -type f | wc -l)" -eq 1
test -f "$SD_BUNDLE_ROOT/$SD_BUNDLE_NAME"
test ! -L "$SD_BUNDLE_ROOT/$SD_BUNDLE_NAME"
if find "$SD_BUNDLE_ROOT" -type f \
  \( -name 'kvm-env.ini' -o -name '*.xml' -o -name '*.qcow2' \
     -o -name '*.iso' \) -print -quit | grep -q .; then
  exit 1
fi
find "$SD_BUNDLE_ROOT" -mindepth 1 -maxdepth 1 -printf '%f %s bytes\n'
stat -c '%n %s bytes inode=%i' \
  "$SD_BUNDLE_SOURCE" "$SD_BUNDLE_ROOT/$SD_BUNDLE_NAME"
SD_BUNDLE_SHA256=$(sha256sum "$SD_BUNDLE_SOURCE" | awk '{print $1}')
printf 'bundle_sha256=%s\n' "$SD_BUNDLE_SHA256"
```

If hard links are unavailable across filesystems, use a dedicated read-only copy
with enough storage and verify its checksum before serving. Do not use a symlink
to an extraction directory.

With explicit approval, create a temporary host-firewall gate. This nftables
example allows only the proposed SD source to the bound host IP/port and drops
other sources to that socket; adapt it to the site's existing Proxmox firewall:

```bash
sd_nft_counter_packets() {
  nft list counter inet "$SD_BUNDLE_NFT_TABLE" "$1" |
    awk '{
      for (field = 1; field <= NF; field++) {
        if ($field == "packets") {
          print $(field + 1)
          found = 1
          exit
        }
      }
    }
    END { if (!found) exit 1 }'
}

cleanup_sd_bundle() {
  if test -n "$SD_BUNDLE_PID" && kill -0 "$SD_BUNDLE_PID" 2>/dev/null; then
    kill "$SD_BUNDLE_PID"
    wait "$SD_BUNDLE_PID" || true
  fi
  SD_BUNDLE_PID=
  if test "$SD_BUNDLE_NFT_CREATED" = true; then
    nft delete table inet "$SD_BUNDLE_NFT_TABLE"
    SD_BUNDLE_NFT_CREATED=false
  fi
  if test -f "$SD_BUNDLE_ROOT/$SD_BUNDLE_NAME"; then
    rm -f -- "$SD_BUNDLE_ROOT/$SD_BUNDLE_NAME"
  fi
  if test -d "$SD_BUNDLE_ROOT"; then
    rmdir -- "$SD_BUNDLE_ROOT"
  fi
  if test -f "$SD_BUNDLE_LOG"; then
    rm -f -- "$SD_BUNDLE_LOG"
  fi
}
trap cleanup_sd_bundle EXIT INT TERM

if nft list table inet "$SD_BUNDLE_NFT_TABLE" >/dev/null 2>&1; then
  exit 1
fi
nft add table inet "$SD_BUNDLE_NFT_TABLE"
SD_BUNDLE_NFT_CREATED=true
nft add counter inet "$SD_BUNDLE_NFT_TABLE" "$SD_BUNDLE_ALLOW_COUNTER"
nft add counter inet "$SD_BUNDLE_NFT_TABLE" "$SD_BUNDLE_DROP_COUNTER"
nft add chain inet "$SD_BUNDLE_NFT_TABLE" input \
  '{ type filter hook input priority -10; policy accept; }'
nft add rule inet "$SD_BUNDLE_NFT_TABLE" input ip daddr "$SD_BUNDLE_HOST_IP" \
  tcp dport "$SD_BUNDLE_PORT" ip saddr "$SD_SOURCE_IP/32" \
  counter name "$SD_BUNDLE_ALLOW_COUNTER" accept
nft add rule inet "$SD_BUNDLE_NFT_TABLE" input ip daddr "$SD_BUNDLE_HOST_IP" \
  tcp dport "$SD_BUNDLE_PORT" \
  counter name "$SD_BUNDLE_DROP_COUNTER" drop
nft list table inet "$SD_BUNDLE_NFT_TABLE"

python3 "$SD_BUNDLE_SERVER" \
  --root "$SD_BUNDLE_ROOT" --file "$SD_BUNDLE_NAME" \
  --bind "$SD_BUNDLE_HOST_IP" --port "$SD_BUNDLE_PORT" \
  --allow-source "$SD_SOURCE_IP" --expected-sha256 "$SD_BUNDLE_SHA256" \
  >"$SD_BUNDLE_LOG" 2>&1 &
SD_BUNDLE_PID=$!
until grep -q '^READY ' "$SD_BUNDLE_LOG"; do
  if ! kill -0 "$SD_BUNDLE_PID" 2>/dev/null; then
    wait "$SD_BUNDLE_PID"
    exit 1
  fi
  sleep 1
done
grep -m1 '^READY ' "$SD_BUNDLE_LOG"
ss -ltnp "sport = :$SD_BUNDLE_PORT"
```

`set -euo pipefail` and the preinstalled cleanup trap make this fail closed: any
table, chain, rule, server validation, or listener failure exits before an
unguarded bundle socket can remain available. `serve_bundle.py` independently
enforces the one-file webroot and exact client IP.

From `sd-preflight`, download the whole object, confirm the received byte count,
and keep the connection open long enough to capture live flow evidence:

```bash
SD_EXPECTED_BYTES=$(stat -c %s "$SD_BUNDLE_SOURCE")
SD_DOWNLOADED_BYTES=$(ip netns exec sd-preflight \
  curl --fail --silent --show-error --location --output /dev/null \
  --noproxy '*' \
  --write-out '%{size_download}' \
  "http://$SD_BUNDLE_HOST_IP:$SD_BUNDLE_PORT/$SD_BUNDLE_NAME")
test "${SD_DOWNLOADED_BYTES%.*}" -eq "$SD_EXPECTED_BYTES"
grep -F "COMPLETE source=$SD_SOURCE_IP " "$SD_BUNDLE_LOG" |
  grep -F "bytes=$SD_EXPECTED_BYTES"
SD_ALLOW_AFTER=$(sd_nft_counter_packets "$SD_BUNDLE_ALLOW_COUNTER")
test "$SD_ALLOW_AFTER" -gt 0
SD_DROP_BEFORE=$(sd_nft_counter_packets "$SD_BUNDLE_DROP_COUNTER")
```

From one separately approved non-SD test source, the same URL must fail while the
gate is installed. Because nftables drops that probe before it reaches the
application, do not expect an application `DENY` log. The block below requires
the named nftables drop counter to increase.

Immediately after the allowed and denied probes, capture the completion record
and final allowed/dropped counters, then stop the server and remove
the temporary exposure. Use explicit targets—never recursively delete `<base>`.
Do not enter the SCP branch or §3.4, which installs another trap, until this
block succeeds:

```bash
# Capture HTTP evidence before teardown.
SD_DROP_AFTER=$(sd_nft_counter_packets "$SD_BUNDLE_DROP_COUNTER")
test "$SD_DROP_AFTER" -gt "$SD_DROP_BEFORE"
{
  grep -E '^(READY|COMPLETE) ' "$SD_BUNDLE_LOG"
  nft list table inet "$SD_BUNDLE_NFT_TABLE"
} >>"$SD_APPROVED_EVIDENCE"
grep -F "COMPLETE source=$SD_SOURCE_IP " "$SD_BUNDLE_LOG"
cleanup_sd_bundle
trap - EXIT INT TERM
```

#### SCP branch

When SCP is selected, skip the entire Direct HTTP branch: do not create its
webroot, nftables table, server, variables, or cleanup trap. Use the exact seeded
host, port, username, and path from the namespace. Fully retrieve it and prove
noninteractive authentication, readability, expected filename and byte
size/checksum, gateway/hops, policy, NAT, return path, and bidirectional session
counters. Never place a password on a command line or in evidence. A host-side
file read or an HTTP test cannot substitute for the configured SCP path.

Retain the exact approved SCP service long enough for first boot, require its
redacted audit record of the completed appliance transfer, then revoke any
temporary account, credential, rule, or path access. The HTTP cleanup function
does not exist and must not be called in this branch.

### 3.4 Prove device and log return paths

Add the proposed device and log VIPs to `sd-preflight`. Bind a TCP listener for
7804 and a temporary TLS listener for 6514. The TLS handshake is mandatory:
plain TCP is insufficient, and unavailable TLS tooling means `UNTESTED/STOP`.

```bash
ip -n sd-preflight address add <device-VIP/prefix> dev sdpf0
ip -n sd-preflight address add <log-VIP/prefix> dev sdpf0
SD_TLS_DIR=$(mktemp -d /var/tmp/sd-tls-preflight.XXXXXX)
SD_7804_PID=
SD_6514_PID=
cleanup_sd_tls() {
  for SD_TEST_PID in "$SD_7804_PID" "$SD_6514_PID"; do
    if test -n "$SD_TEST_PID" && kill -0 "$SD_TEST_PID" 2>/dev/null; then
      kill "$SD_TEST_PID"
      wait "$SD_TEST_PID" || true
    fi
  done
  rm -f -- "$SD_TLS_DIR/key.pem" "$SD_TLS_DIR/cert.pem" \
    "$SD_TLS_DIR/7804.log" "$SD_TLS_DIR/6514.log"
  if test -d "$SD_TLS_DIR"; then
    rmdir -- "$SD_TLS_DIR"
  fi
}
trap cleanup_sd_tls EXIT INT TERM

openssl req -x509 -newkey rsa:2048 -nodes -days 1 \
  -subj '/CN=sd-log-preflight' \
  -addext 'subjectAltName=DNS:sd-log-preflight' \
  -keyout "$SD_TLS_DIR/key.pem" -out "$SD_TLS_DIR/cert.pem"

ip netns exec sd-preflight socat \
  TCP4-LISTEN:7804,bind=<device-VIP>,reuseaddr,fork SYSTEM:'sleep 45' \
  >"$SD_TLS_DIR/7804.log" 2>&1 &
SD_7804_PID=$!
ip netns exec sd-preflight socat \
  OPENSSL-LISTEN:6514,bind=<log-VIP>,cert="$SD_TLS_DIR/cert.pem",\
key="$SD_TLS_DIR/key.pem",verify=0,reuseaddr,fork SYSTEM:'sleep 45' \
  >"$SD_TLS_DIR/6514.log" 2>&1 &
SD_6514_PID=$!
ip netns exec sd-preflight ss -ltn 'sport = :7804 or sport = :6514'
```

From the exact device-management source, keep TCP/7804 open during transit
inspection:

```bash
{ printf 'device-preflight\n'; sleep 45; } |
  nc -s <device-management-source-IP> -w 50 <device-VIP> 7804
```

From the exact revenue/log source, copy only the temporary public certificate to
the client and require a verified TLS handshake while holding the connection:

```bash
{ printf 'log-preflight\n'; sleep 45; } |
  openssl s_client -connect <log-VIP>:6514 \
    -bind <revenue-source-IP>:0 -servername sd-log-preflight \
    -CAfile <copied-cert.pem> -verify_return_error -brief
```

Use source binding only where the release/client supports it. If the device CLI
cannot bind the selected source or perform TLS, use an approved disposable Linux
VM attached to that exact source VLAN/VRF. Assign the exact source only when the
original address is safely unavailable; otherwise use a separately approved
source that matches the same route/policy/NAT selectors and record the limitation.
If equivalence cannot be proved, the row remains `UNTESTED/STOP`.

While each connection is open, inspect every stateful transit firewall:

```junos
show route <target-or-source>
show security match-policies from-zone <from> to-zone <to> \
  source-ip <source> destination-ip <destination> protocol tcp \
  source-port <ephemeral-port> destination-port <7804-or-6514>
show security flow session source-prefix <source> \
  destination-prefix <destination> protocol tcp
```

Pass only when the selected policy/NAT is the expected one and both request and
reply packet counters are non-zero. `In > 0, Out = 0` is a failed return path.
For 6514, also require an `openssl s_client` success with certificate verification
and a TLS protocol/cipher in its output. Record the output against the matrix
row. Obtain explicit approval before any route, policy, or NAT write; use
commit-check/diff, preserve rollback, commit, then repeat the exact-source tests.

Stop listeners and delete temporary private-key material:

```bash
cleanup_sd_tls
trap - EXIT INT TERM
rm -f -- <client-path-to-copied-cert.pem>
```

### 3.5 Remote-lab regression test

The 2026-07-24 remote-lab build passed DNS/NTP checks from Proxmox but seeded:

```text
SD management: 198.51.100.19/21
Wrong gateway: 198.51.100.254
Required gateway: 198.51.100.18 (infra-vsrx)
Device VIP: 198.51.100.21:TCP/7804
Log VIP: 198.51.100.22:TCP/6514
```

The installed appliance sent managed-firewall traffic toward `.254` and could
not reach the devices. A host-originated test did not exercise the guest's first
hop, infra-vsrx zones, security policy, NAT, or return path. The corrected design
must therefore prove SD `.19` via gateway `.18` to every firewall, plus every
firewall's reverse path to `.21:7804` and `.22:6514`, before deployment.

### 3.6 Other pre-flight checks

1. **Free IPs** — `arping -I <bridge> <ip>` for all four; outside any DHCP pool.
2. **Host headroom** — cores, RAM, and thin storage for the complete flavor row.
3. Save the passed matrix and probe output with the change record.
4. Delete the disposable namespace after all management, dependency, reverse,
   TLS, and bundle tests complete: `ip netns delete sd-preflight`.

Any failed or untested matrix, bundle, or TLS row means **STOP**.

---

## 4. Extract artifacts (`--no-run`)

Stage both files on the host (e.g. `/var/lib/vz/sd-onprem/`), then run the
extractor. It is interactive; the **26.2.1 prompt order is 22 prompts**:

| # | Prompt | Example |
|---|---|---|
| 1 | Base folder for KVM artifacts | `/var/lib/vz/sd-onprem` (must exist; output lands in `<base>/<version>/`) |
| 2 | *(re-runs only)* `Overwrite existing contents? (y/N)` | `y` |
| 3 | Virtual Machine Name | `sd-onprem` |
| 4 | Hostname | `sd-onprem` |
| 5 | CLI Admin Password | *(silent; 8–32, ≥3 of digit/upper/lower/special, must pass cracklib — systematic strings like `Test1234!` are rejected)* |
| 6 | Management IP (CIDR) | `198.51.100.19/21` |
| 7 | Default Gateway | `198.51.100.18` |
| 8 | DNS Servers (space-sep) | `198.51.100.25` *(one verified resolver)* |
| 9 | Search Domains (optional) | *(blank)* |
| 10 | UI Virtual IP | `198.51.100.20` |
| 11 | UI FQDN (optional) | *(blank — reached by IP)* |
| 12 | Device Connection VIP | `198.51.100.21` |
| 13 | Device Connection FQDN (optional) | *(blank)* |
| 14 | LOG Collector VIP | `198.51.100.22` |
| 15 | LOG Collector FQDN (optional) | *(blank)* |
| 16 | Software Bundle Path | `http://198.51.100.8:8085/<bundle>.tgz` *(HTTP; see note)* |
| 17 | HTTP Proxy URL (optional, http only) | *(blank — required by the direct restricted-server pattern)* |
| 18 | NTP Server | `198.51.100.25` *(must be reachable)* |
| 19 | Security Director CIDR (optional) | *(blank → default `10.42.0.0/21`)* |
| 20 | **Configuration ID / flavor** (1/2/3) | `1` — **easy to miss when scripting; no default, loops on invalid** |
| 21 | Bridge interface name | `vmbr5` |
| 22 | Disk provisioning (1 Thin / 2/3 Thick) | `1` — thin sparse qcow2s |

For bundle delivery, prefer the §3.3 restricted HTTP window over SCP credentials
stored in `kvm-env.ini`. The extractor only format-checks the URL; it does not
prove retrieval. **Never point `http.server --directory` at `<base>` or the
extraction output; use the bundled completion-aware `scripts/serve_bundle.py`.**
Confirm management IP/prefix, gateway, bridge, DNS, NTP, exact bundle URL, and
all VIPs in `kvm-env.ini` match the passed §3 evidence before booting.

Output in `<base>/<version>/`: `Security-Director-OnPrem-disk-0/1/2.qcow2`,
`Security-Director-OnPrem-kvm.iso`, `kvm-env.ini`, `sd-onprem.xml`.

Driving `--no-run` non-interactively (pipe answers via stdin) works, but only if
every value's format is valid — a looping validator desyncs the stream.

---

## 5. Build the Proxmox VM

Mirror the generated `sd-onprem.xml`: **machine `q35`, CPU host-passthrough, 3
`virtio` disks (vda/vdb/vdc), ISO on cdrom, virtio NIC.**

```bash
VM_DIR=<base>/<version>
qm create <vmid> --name sd-onprem --machine q35 --cpu host --cores 8 --sockets 1 \
  --memory 65536 --numa 0 --ostype l26 --scsihw virtio-scsi-single \
  --net0 virtio,bridge=<bridge> --vga std --serial0 socket
cp "$VM_DIR"/Security-Director-OnPrem-kvm.iso /var/lib/vz/template/iso/sd-onprem-seed.iso
for i in 0 1 2; do qm importdisk <vmid> "$VM_DIR"/Security-Director-OnPrem-disk-$i.qcow2 local-lvm; done
qm set <vmid> --virtio0 local-lvm:vm-<vmid>-disk-0 --virtio1 local-lvm:vm-<vmid>-disk-1 \
  --virtio2 local-lvm:vm-<vmid>-disk-2 --ide2 local:iso/sd-onprem-seed.iso,media=cdrom
qm set <vmid> --boot order=virtio0     # SEPARATE command — see §9
```

---

## 6. First boot + verify

### HTTP first-boot delivery

Rerun the §3.3 Direct HTTP setup/server blocks with a new private webroot, log,
nftables table, and installed cleanup trap. Recompute the expected size in that
approved shell before starting the guest:

```bash
SD_EXPECTED_BYTES=$(stat -c %s "$SD_BUNDLE_SOURCE")
qm start <vmid>
```

A normal
`200` request line is not completion evidence because it may
be logged before the body finishes. Wait for the bundled server's exact
`COMPLETE source=<SD-mgmt-IP> ... bytes=<expected>` record. Capture the record
and counters, then tear down immediately—do not wait for the container install
and do not let a later trap replace this HTTP cleanup trap:

```bash
# Capture first-boot HTTP evidence before teardown.
{
  grep -E '^(READY|COMPLETE) ' "$SD_BUNDLE_LOG"
  nft list table inet "$SD_BUNDLE_NFT_TABLE"
} >>"$SD_APPROVED_EVIDENCE"
grep -F "COMPLETE source=$SD_SOURCE_IP " "$SD_BUNDLE_LOG" |
  grep -F "bytes=$SD_EXPECTED_BYTES"
cleanup_sd_bundle
trap - EXIT INT TERM
```

### SCP first-boot delivery

Skip all HTTP setup and cleanup. Revalidate the exact approved SCP account,
endpoint, path restriction, and audit logging, then `qm start <vmid>`. After the
SCP service records the completed appliance transfer, retain redacted transfer
and session evidence and immediately revoke any temporary account, credential,
rule, or path access. Never retain a plaintext credential as evidence.

For either method, continue verification after the delivery window is closed:

- mgmt IP answers ping within ~1–2 min (network seeded);
- container-stack install runs (**tens of minutes** — OpenSearch, Kafka, etc.);
- ingress comes up (`https://<ui-vip>` serves the Juniper self-signed cert, may 404);
- app pods finish → `https://<ui-vip>/login` returns 200.

Snapshot the VM before onboarding. Assign the **subscription/license** (Admin →
Subscriptions) — **log analytics / "All Security Events" is gated behind it**,
separate from device management.

---

## 7. Onboard Junos/SRX devices

### 7.0 NTP preflight — STOP gate

**No device is discovered or onboarded until its clock is proven synchronized.**
Configured servers and a running `ntpd` do not satisfy this; proven sync does.

Why it is a gate and not a checklist item: a skewed SRX still completes the mTLS
handshake to the collector and still has its payloads acknowledged, so every
transport-level test in §3.4 and §8 passes while the logs never reach the GUI.
Live deployment: several SRXs ~375 s behind, streams connected and ACKed, traffic
logs absent from SD. They appeared after NTP was corrected and fresh traffic was
generated. Debugging that from the log path costs hours; the clock check costs a
minute.

```junos
set system processes ntp enable
set system ntp server <primary-server>
set system ntp server <secondary-server>
set system ntp source-address <reachable-source-address>
```

`set system processes ntp enable` **is hidden from CLI completion but valid and
required.** It does not tab-complete, which is exactly why it gets omitted.
Confirmed present on production SRXs on Junos 26.2R1.

Verify on every device before onboarding:

```text
show configuration system processes | display set | match "ntp enable"
show ntp associations no-resolve
show system uptime | match "Current time|Time Source"
show ntp status
show system processes extensive | match " ntpd"
```

`show ntp associations no-resolve` is the authority. Required: at least one peer
marked `*` (the selected system peer), `reach` non-zero (`377` = all recent polls
answered), and `offset` within the deployment's tolerance:

```text
     remote               refid           auth  st  t  when  poll reach  delay     offset   jitter
*10.x.x.1               <upstream>           -   4  u   154   256  377    1.000    +0.831    0.805
+10.x.x.2               10.x.x.1             -   5  u   221   256  377    0.926    -3.732    0.880
```

Corroborate with `Time Source: NTP CLOCK` from `show system uptime`, and
`leap_none`, `sync_ntp` — plus `clock_sync` once settled — from `show ntp status`.

**Decide pass/fail on the associations table, not the status word.** Two
observations from live devices explain why neither half of the status word is
safe on its own:

- **`sync_ntp` is not proof of sync.** It appears alongside `no_sys_peer`, which
  means no system peer is currently selected — so `sync_ntp` alone must not be
  read as a pass.
- **Absent `clock_sync` is not proof of failure.** A device reporting
  `leap_none, sync_ntp, no_sys_peer` was, moments later, showing a `*` peer at
  `reach 377` with a sub-second offset — genuinely in sync, status word merely
  lagging. Treating missing `clock_sync` as a hard fail would have blocked a
  healthy device from onboarding.

Rule: a `*` peer with non-zero reach and an acceptable offset is a **pass**, even
if the status word has not caught up. No `*` peer, or `reach 0`, is a **fail**
regardless of `sync_ntp`. `Time Source: NTP CLOCK` shows in both states and
cannot break the tie.

**Through NAT or VPN — prove UDP/123 in both directions.** Check routing,
security policy, and source NAT, and confirm the return path; a request that
leaves and never returns is indistinguishable from an unreachable server.

- Where a remote SRX sources NTP from a **loopback management identity**, include
  that loopback prefix in the transit firewall's **source**-NAT match. The usual
  failure is a device that has both a route and a permitting policy, but whose
  loopback source is untranslated, so replies never come back.
- **Do not put the NTP servers' own addresses in a source-address NAT match.**
  They are destinations. This misconfiguration breaks the return path silently.

Only when every device passes does onboarding begin.

---

**Management** and **logging are two different planes:**

- **Management** — create the device in SD (Inventory → Devices), apply the
  generated adopt/onboard config to the device. It connects out to the
  **device-connection VIP** (`.21`). **This must be in-band, off a revenue port —
  NOT fxp0.** SD then pushes the `sd-logs` log stream to the device.
- **Logging — must NOT source off fxp0.** SD cannot receive security logs from the
  management interface. See §8.

> **Both planes are in-band; `fxp0` is not a path to SD for anything.** An earlier
> revision of this guide said management "can ride the management path (fxp0/mgmt
> net)" — that is wrong. Manage devices at a revenue-port address (`ge-0/0/x.0`, a
> `reth`, or an in-band-reachable `lo0`).
>
> The reason is that **the route chooses the egress, not `source-interface`**: if
> `<log-VIP>/32` or `<device-VIP>/32` resolves out `fxp0`, the log stream dies
> whatever `security log source-interface` says, because the PFE cannot egress
> `fxp0`. Adding a static route to the SD subnet via the management LAN is
> therefore an attractive-looking change that silently breaks logging.
>
> The clean fix is `set system management-instance`, which moves `fxp0` into
> `mgmt_junos` and out of `inet.0`, so no data-plane route can resolve to it.
> Verified in this lab: `dc-fw` is managed at revenue leg `ge-0/0/3.0`
> (`203.0.113.50`) with `fxp0` in the management instance, and the branches are
> managed at `lo0` reached in-band over the IPsec tunnel.

---

## 8. The log path (the hard part)

**SD On-Prem collects structured syslog over TLS on TCP/6514** (not plain UDP/514).
When SD onboards a device it pushes:

```
set security log source-interface <revenue-port>.0
set security log stream sd-logs host <log-VIP> port 6514 transport protocol tls ...
```

For that stream to actually work, three network facts must hold:

1. **Source from a production/revenue port** (SD sets `source-interface`), never
   fxp0 — the PFE cannot egress the management interface.
2. **A data-plane route to the log-collector VIP.** The VIP sits on the SD
   management subnet (the 4-VIP same-subnet rule forces this), which the device
   fabric might not normally reach. Use a policy/routing firewall with a leg on
   the SD subnet as the **log gateway**, and route every device's `<log-VIP>/32`
   toward it. In the current worked example, `infra-vsrx` has the SD-side
   `198.51.100.18` leg and the device-transit `203.0.113.1` leg.
3. **Source-NAT on the log-gateway FW.** TLS/6514 is **bidirectional** (unlike
   one-way UDP syslog), so SD must be able to reply. SD's only route off its subnet
   is its default gateway — it has **no route back to the FW's fabric interface**.
   Source-NAT the log traffic to the gateway's on-subnet leg so SD replies
   on-subnet and the FW un-NATs back.

**Worked config (per hop):**

```junos
# every logging device: route the collector VIP toward the log-gateway FW
set routing-options static route <log-VIP>/32 next-hop <toward-gateway>

# the log-gateway FW (infra-vsrx in the worked example): permit + source-NAT
set applications application sd-syslog-tls protocol tcp destination-port 6514
set security policies global policy 600-syslog-to-sd match from-zone <fabric> to-zone <collector-leg-zone>
set security policies global policy 600-syslog-to-sd match application [ junos-syslog sd-syslog-tls ]
set security policies global policy 600-syslog-to-sd then permit
insert security policies global policy 600-syslog-to-sd before policy <deny-all>
set security nat source rule-set logs-to-sd from zone [ <fabric-zones> ] to zone <collector-leg-zone>
set security nat source rule-set logs-to-sd rule nat-logs match source-address <fabric-supernets>
set security nat source rule-set logs-to-sd rule nat-logs match destination-address <log-VIP>/32
set security nat source rule-set logs-to-sd rule nat-logs then source-nat interface

# transit FWs between device and gateway: permit tcp/6514 (their stateful session handles the return)
set applications application sd-syslog-tls protocol tcp destination-port 6514
set security policies global policy 600-syslog-to-sd match application [ junos-syslog sd-syslog-tls ]  # + route the VIP onward
```

**Verify** on the log-gateway FW:
`show security flow session destination-prefix <log-VIP> protocol tcp` — a healthy
stream is `Session State: Valid`, **`In` AND `Out` packets both non-zero** (TLS is
bidirectional; `Out: 0` means the return path is broken — check the source-NAT).

**Logging source interface per device** = the revenue port whose route reaches the
log gateway (the egress interface toward it). E.g. a device that reaches the
gateway via its dc-facing `ge-0/0/2` should log-source from `ge-0/0/2`.

> **SD's source-interface picker only lists PHYSICAL revenue interfaces — `lo0`
> is not selectable.** For a device managed over a tunnel (branches, whose only
> stable identity is `lo0`), you must pick a physical port — but **NOT just any
> one.** The log stream default-routes out the tunnel (st0), so the reply must
> come back over the tunnel too. Pick the interface whose subnet the gateway
> routes **via the tunnel** — the **LAN** (`ge-0/0/1`), reachable only over st0 —
> **not the WAN** (`ge-0/0/0`), which sits on the shared underlay the gateway
> reaches **directly**. Sourcing from the WAN → forward via tunnel, reply via
> underlay = **asymmetric**, and the branch drops the SYN-ACK (`Out: 0`, the TLS
> handshake never completes). Also ensure the chosen IP is inside the gateway's
> source-NAT range. Verify on the gateway: `show route <candidate-IP>` must
> resolve to the same st0 the traffic egresses, not a directly-connected underlay.

**Device-connection (`.21`) needs the same return-path fix as logs.** The device
management channel (outbound to the device-connection VIP, port 7804) is also
bidirectional and also breaks for tunnel-managed branches (SD has no route back to
`172.31.x`). Make the gateway FW's source-NAT match **both** the device-connection
VIP and the log-collector VIP (e.g. `destination-address [ <dev-VIP> <log-VIP> ]`),
or branch adoption hangs at `In: 1 / Out: 0`.

**MNHA pairs:** each node runs an INDEPENDENT config (different interface IPs) —
configure the route on **both** nodes. Only the **active** node processes transit
traffic, so only it generates security logs; the backup is idle and starts
streaming automatically on failover. Both nodes' streams land on the same
gateway-FW zone, so one transit permit + source-NAT covers the pair.

---

## 9. Gotchas (all hit in a real build)

- **No libvirt on Proxmox** → don't run the vendor `launch-vm.sh`; import qcow2s.
- **`.bin --no-run` is the disk source**, not the encrypted `.tgz`.
- **Config-ID / flavor prompt (#20) is easy to miss** when scripting — no default,
  loops on invalid.
- **Boot order must be a SEPARATE `qm set`** after the disks attach, else it
  silently falls back to `order=net0;ide2` and won't boot the OS disk.
- **NTP must be reachable** — an internet NTP behind a site that blocks outbound
  123 hangs first boot; use an internal one.
- **A skewed SRX clock silently swallows log visibility.** The mTLS stream
  connects, the collector ACKs the payloads, the FW session shows `In`/`Out`
  non-zero — and nothing appears in the SD GUI. Seen at ~375 s of skew; logs
  surfaced only after NTP was fixed and fresh traffic generated. Gate on §7.0
  before onboarding instead of debugging the log path.
- **Every DNS server must actually answer DNS** — a non-resolving entry loops first
  boot on `DNS address is not connectable`; the VM never pulls the bundle
  (0 requests to the bundle server). Diagnose from the console
  (`qm monitor <vmid>` → `screendump`); it names the dead server.
- **There is no documented gateway-only CLI command.** Juniper's documented
  `set ipaddress change <IP>` workflow prompts for management IP, netmask, and
  gateway. For the verified 26.2.1 wrong-seed incident, preserve/protect the
  failed VM and rebuild from corrected seed data with fresh disks. That is the
  conservative verified recovery policy, not a universal vendor requirement.
- **Log analytics is subscription-gated** — logs can arrive at the collector while
  "All Security Events" stays empty until a subscription is assigned.
- **Logs are TLS/6514, not UDP/514** — plain TCP reachability does not pass;
  complete a verified TLS handshake from every selected revenue source. Permit
  tcp/6514 through transit and source-NAT for the return path (§8).
- **Flavor is validated as a WHOLE SET on every boot — you cannot partially
  resize.** CPU + RAM + all three disk sizes must match one flavor row (§2).
  Bumping only CPU/RAM (e.g. 8/64 → 16/80 while leaving flavor-1 disks) yields
  **"Unsupported CPU/Memory/Disk configured"** on the console and **RKE2 never
  starts** (CLI: `connection to 127.0.0.1:6443 refused`, RAM sits near 0). Recovery:
  power off, set resources back to the installed flavor, power on. To actually move
  flavors you must grow the data disks too — a real storage migration.

---

## 10. Operations

- **CLI:** `ssh cliadmin@<mgmt-ip>` on 26.2.1 (restricted appliance CLI;
  `show node`, `show pod`, and `?` completion work). No shell/`kubectl`.
- **Memory:** the 8/64 floor is genuinely tight — OpenSearch + Kafka + Postgres +
  Redis + ~70 JVM microservices on one node. RAM climbs with log volume. **You
  cannot just add RAM** (flavor lock, §9). Relieve pressure by **cutting log load**:
  shorter retention, specific log categories instead of `category all`, fewer
  chatty devices. A true bump means a full flavor-2 migration.
- **Snapshots:** `qm snapshot <vmid> <name>` before any change. `protection: 1` +
  the `protected` tag block deletion, not stop/config/start.

---

## 11. Rollback

- Before first boot, correct any seed value and regenerate the ISO.
- For the verified 26.2.1 wrong-seed recovery policy, use a new VM with corrected
  seed data and fresh disks. Protect the failed VM as rollback evidence until the
  replacement passes §3 and application health checks.
- Full rollback: `qm rollback <vmid> <snapshot>` (restores disks **and** the VM
  config, e.g. CPU/RAM, from snapshot time).
- Remove: `qm stop <vmid> && qm destroy <vmid>` (clear `protection` first; never
  destroy a `protected` guest you didn't create). No libvirt state remains.
- Stop any bundle server and remove its temporary nftables table, bundle-only
  hard link/webroot, access log after evidence capture, and TLS private key.

---
name: clearpass-proxmox-deploy
description: Deploy, license, and validate HPE Aruba ClearPass Policy Manager 6.14 on Proxmox VE KVM. Use when sizing the appliance, driving the VGA-only first-boot wizard, fixing a GRUB menu that never boots, importing an HTTPS certificate, or using the REST API.
version: 0.2.1
author:
  - fastrevmd-lab
  - Claude
  - GPT
license: MIT
metadata:
  hermes:
    tags: [clearpass, cppm, aruba, hpe, nac, radius, proxmox, kvm, uefi, ovmf, vm-deploy, raw-image, console-automation]
    related_skills: [sd-onprem-proxmox-deploy, srx-chassis-cluster-proxmox]
  sources:
    - title: "HPE ClearPass 6.14 Installation Guide (HPE_sd00007984en_us)"
      author: Hewlett Packard Enterprise
      note: "247-page vendor PDF, dated 2026-08-07. Authoritative for the wizard's question set and the appliance flavor table. Contradicts itself on disk bus and is silent on firmware — see Gotchas."
      retrieved: "2026-08-13"
    - title: "Virtual Appliance Installation: KVM — create-kvm-cp.sh"
      author: Hewlett Packard Enterprise
      note: "The guide's own virt-install script. Uses bus=scsi for BOTH disks and os-variant=rhel8.4; the image actually ships a Rocky 9 kernel (5.14.0-570 el9_6)."
      retrieved: "2026-08-13"
  verified_on:
    - release: "6.14.0.371380 (C1000V)"
      host: "Proxmox VE 9.2 (pve2), QEMU 11.0.3"
      date: "2026-08-13"
---

# Deploying ClearPass Policy Manager on Proxmox VE

## Contents

- [Overview](#overview)
- [Artifacts](#artifacts)
- [Requirements](#requirements)
- [Runtime intake](#runtime-intake)
- [Mandatory pre-power-on gate](#mandatory-pre-power-on-gate)
- [Procedure](#procedure)
- [Gotchas (all hit in a real 6.14.0.371380 build)](#gotchas-all-hit-in-a-real-6140371380-build)
- [Day-2 operations](#day-2-operations)
- [Rollback](#rollback)

> **STATUS: draft (v0.1.0).** The procedure below was executed end-to-end once,
> on **CPPM 6.14.0.371380** as a **C1000V**, on Proxmox VE 9.2. Every claim in
> Gotchas was observed in that build unless explicitly marked
> **[unverified]**. It needs a repeat run — and ideally one non-C1000V flavor —
> before it earns a stable label. Values in `<angle brackets>` are site-specific.

## Overview

> **The ClearPass 6.14 KVM image only boots under UEFI. The installation guide
> never says so, and the failure mode is silent.** Its GRUB menu entry calls
> `linuxefi`/`initrdefi`, which do not exist in the BIOS (`i386-pc`) build of
> GRUB 2.06. Under SeaBIOS the appliance reaches its GRUB menu, fails every boot
> attempt including the 10-second auto-timeout, and redraws the menu. It looks
> exactly like a dead keyboard. Set `bios: ovmf` and attach an EFI disk.

ClearPass ships as a **single raw disk image in a zip** — no OVA, no qcow2, no
seed ISO. Deployment is therefore: create a VM whose first disk is byte-exactly
the size of that raw image, write the image onto it, attach a **second, empty
data disk sized for the target appliance flavor**, and boot. The appliance
partitions the second disk itself and installs onto it on first boot.

There are two hard gates and both are pre-power-on:

1. **Firmware must be UEFI** (above).
2. **The second disk must already exist.** Boot without it and the appliance
   kernel-panic loops; the guide states this and it is accurate.

Everything after that is an interactive console wizard, which is the second
awkward part — it renders on VGA only (see §5).

## Artifacts

| File | Role |
|---|---|
| `CPPM-VM-x86_64-<ver>-KVM.raw.zip` | The whole appliance. One deflate member. For 6.14.0.371380: **4,979,856,187 B compressed → 48,318,382,080 B raw** (45 GiB exactly = 46080 MiB), CRC32 `0x2572e1fe`. |
| Installation Guide PDF | The wizard's question set and flavor table. Treat its firmware silence and bus-type advice as defective; see Gotchas. |

> The guide says "the ClearPass KVM disk image is shipped as a **24 GB** hard disk
> volume." The 6.14.0.371380 image is **45 GiB**. Size `scsi0` from the actual
> zip member, never from the guide.

## Requirements

Flavor table (from the guide; only **C1000V** was exercised). "Disk space" is the
**second** disk — it is in addition to the ~45 GiB image disk.

| Flavor | vCPU | RAM | 2nd disk | Notes |
|---|---|---|---|---|
| CLABV | 4 | 6 GB | 400 GB | Evaluation image |
| C1000V | 8 | 8 GB | 1000 GB | 500 endpoints — **verified** |
| C2000V | 8 | 16 GB | 1000 GB | 5K endpoints |
| C3000V | 24 | 64 GB | 1800 GB | 25K endpoints |

- Storage: image disk + second disk, so a C1000V needs **~1045 GB**. The guide
  says "thick provisioned"; LVM-thin was used and the appliance's own
  `show system-resources` accepted it.
- **Two NICs**, and their **MAC addresses must be assigned in ascending order** —
  ClearPass maps the lowest MAC to `eth0`/management. Pin them explicitly.
- One free management IP outside any DHCP pool, plus gateway, DNS, and a
  reachable NTP server.
- The guide documents `system morph-vm` for moving to a **larger** flavor after
  installation. **[unverified]** — not exercised in this build, and the
  supported transitions are not enumerated by the guide. Treat the flavor as
  fixed when planning: size for the endpoint count you expect, and plan a
  rebuild rather than assuming a later morph will land.

## Runtime intake

Before starting the workflow, inspect the request, supplied artifacts, and
available approved read-only evidence. If unresolved facts could materially
change safety, scope, correctness, confidence, or the requested output, read
`references/runtime-intake.md`.

For each unresolved material fact whose catalog condition is true, invoke Claude `AskUserQuestion` or Codex `request_user_input` before continuing or issuing an open-ended request.
Ask at most three single-select catalog questions per round. After each response, ask another round whenever any unresolved material catalog condition remains true; continue only when none remain. Do not repeat answered questions or show the full catalog.
Without a native tool, present each selected catalog question with its 2-3 labeled choices and a free-text `Other` path in concise plain text; do not substitute a generic checklist.

Never request secrets or unredacted customer data. Treat intake answers as task
context, not approval for a live change; obtain separate explicit approval
before configuration, commit, upgrade, reboot, delete, or failover actions.

## Mandatory pre-power-on gate

> **STOP — verify all five before the first `qm start`.** Items 1–3 cannot be
> corrected after first boot without a rebuild; item 4 is permanent.

1. `bios: ovmf` **and** an `efidisk0` are set. (SeaBIOS = silent GRUB loop.)
2. The second disk is attached and sized to the target flavor.
3. `net0`'s MAC is numerically **lower** than `net1`'s.
4. Decide **disk encryption now.** The wizard asks once and the answer cannot be
   changed after installation.
5. The management IP is confirmed free (`arping`/`ip neigh`) and outside the
   DHCP pool.
6. The device you are about to write to really is `scsi0` — resolved through
   `qm config` + `pvesm path`, never assumed to be `vm-<vmid>-disk-0` (§3).
   Autostart stays off until §6 passes.

## Procedure

### 1. Confirm the image geometry

Read the zip's own central directory — you need the exact uncompressed size to
size `scsi0`, and the CRC32 to verify the write later:

```bash
python3 -c "
import zipfile; i = zipfile.ZipFile('<zip>').infolist()[0]
print(i.filename, i.file_size, hex(i.CRC))"
```

Size `scsi0` to **exactly** `file_size`. For 6.14.0.371380 that is 45 GiB, which
is an integral number of MiB (46080) and of LVM 4 MiB extents.

### 2. Create the VM

```bash
qm create <vmid> \
  --name <name> --ostype l26 --cpu host \
  --sockets 1 --cores 8 --memory 8192 --balloon 0 \
  --bios ovmf --efidisk0 <storage>:1,efitype=4m,pre-enrolled-keys=0 \
  --scsihw virtio-scsi-pci \
  --scsi0 <storage>:<image-GiB-from-step-1> \
  --scsi1 <storage>:<flavor-2nd-disk-GB> \
  --net0 virtio=<MAC-LOW>,bridge=<mgmt-bridge> \
  --net1 virtio=<MAC-HIGH>,bridge=<data-bridge> \
  --boot order=scsi0
```

Size `scsi0` from step 1's `file_size`, not from this build's number.
`pre-enrolled-keys=0` keeps Secure Boot out of the picture. Adding
`--serial0 socket` is useful for kernel messages but **will not show you the
setup wizard** (§5).

**Leave autostart off until §6 passes.** Set `--onboot 1` after verification, so
a node reboot between landing the image and the approved first boot cannot power
this guest through the pre-power-on gate unattended.

### 3. Write the image without a 45 GiB temp file

> **Never assume `vm-<vmid>-disk-0` is `scsi0`.** Proxmox allocates drive keys in
> sorted order, so with the `qm create` above **`efidisk0` takes `disk-0` and
> `scsi0` becomes `disk-1`** (verified on PVE 9.2). Writing to `disk-0` targets
> the 4 MB EFI-vars volume. Non-LVM stores have no `/dev/<vg>` path at all.
> Resolve the volume from the config every time:

`scripts/stream-inflate-zip.py` sends only the ~5 GB compressed stream over the
wire, inflates on the hypervisor, and verifies size + CRC32 against the zip
header as it writes.

**Resolution, size gate, and write must happen in one remote shell** — a shell
variable does not survive into a second `ssh`, and a half-resolved path is how a
destructive write goes to the wrong volume:

```bash
# Chain the upload: a failed scp must not be followed by a write attempt.
# <helper-sha256> = sha256sum scripts/stream-inflate-zip.py | cut -d" " -f1
scp scripts/stream-inflate-zip.py root@<host>:/root/cppm/ && \
ssh root@<host> 'set -eu
VOL=$(qm config <vmid> | sed -n "s/^scsi0: \([^,]*\).*/\1/p")
DEV=$(pvesm path "$VOL")
echo "scsi0 -> $VOL -> $DEV"

# Size gate. pvesm path yields a block device on LVM/ZFS and a regular file on
# dir/NFS storage, so check both forms rather than assuming a block device.
if [ -b "$DEV" ]; then SIZE=$(blockdev --getsize64 "$DEV")
else SIZE=$(stat -c %s "$DEV"); fi
[ "$SIZE" = "<uncompressed-bytes>" ] || { echo "size $SIZE != image"; exit 1; }

# Standalone cd: under set -e the left side of an AND-OR list is exempt, so
# `cd X && python3 ...` would silently skip the write if the scp above failed
# and still exit 0.
cd /root/cppm
# An interrupted upload can leave the helper empty, or truncated at a
# syntactically valid boundary; either exits 0 without writing anything, and a
# target with a readable partition table then lets fdisk mask it as success.
# Only an exact whole-file match rules that out — size and parse checks do not.
echo "<helper-sha256>  stream-inflate-zip.py" | sha256sum -c -
python3 stream-inflate-zip.py "$DEV" <crc32-hex> <uncompressed-bytes>
fdisk -l "$DEV"
' < <zip>
# expect: written=<n> ... crc=0x... MATCH
# GPT: p1 200M EFI System · p2 1G Linux filesystem · p3 1M BIOS boot · p4 LVM
```

On file-backed storage the volume must be **raw** (`qemu-img info "$DEV"`);
a qcow2 volume is not a valid target for a raw block-level write. Do not place
the helper script in `/tmp` on a Proxmox host — see Gotchas.

The 1 MB BIOS boot partition is **vestigial**. Its presence is the single most
misleading artifact in the image; do not read it as BIOS support.

### 4. First boot and flavor selection

Start the VM. The appliance boots to a flavor prompt on the VGA console:

```
VM appliance types
1) CLABV   2) C1000V   3) C2000V   4) C3000V
Enter appliance type to continue :
```

It then prints required-vs-current resources, names the second disk
(`Second Disk is /dev/sdb`), and warns that **all data on it will be erased**.
Answer `y`. The next prompt is encryption:

```
Press Y/y to encrypt or any other key to skip encryption:
```

**Any keystroke that is not Y/y — including a stray Enter — permanently
disables disk encryption.** Send exactly one key here and mean it.

Installation then partitions `/dev/sdb`, copies the filesystem, associates MACs
with `eth0`/`eth1`, and reboots. Budget **30–40 minutes**; the verified run
completed in ~12.

### 5. Drive the configuration wizard (VGA only)

The image's kernel command line is
`console=ttyS0,9600n8 console=tty0` — the **last** `console=` wins for
userspace, so `/dev/console` is the VGA text console. A serial port gives you
kernel and systemd messages and **never shows the wizard**. Drive it through the
QEMU monitor instead:

```bash
echo 'screendump /tmp/<vmid>.ppm' | qm monitor <vmid>   # observe
echo 'sendkey <key>'              | qm monitor <vmid>   # type
```

This skill's `scripts/console-type.py` maps a literal string to `sendkey` lines
(shifted symbols included). It is not on `PATH` — the installer copies the
package verbatim — so run it as `python3 <this-skill-dir>/scripts/console-type.py`.
Screenshot after every answer; the wizard's question set differs from the
guide's.

**Never pass the cluster password as an argument.** argv is readable by every
user on the host via `ps` and lands in shell history. Use the script's `--stdin`
mode for that prompt and suppress its stdout, which spells the secret out one
key per line:

```bash
# The package is copied verbatim and is not added to PATH, so invoke by path.
CT="<this-skill-dir>/scripts/console-type.py"
systemd-ask-password --echo=0 | python3 "$CT" --stdin | qm monitor <vmid> >/dev/null
```

Log in with `appadmin` / `eTIPS123`, wait past `Waiting for network connection`,
then answer, **in this order**:

| Prompt | Note |
|---|---|
| `Enter hostname` | short name |
| `Management Port IPv4 Address/PrefixLen` | **CIDR** (`10.0.0.5/24`) — the guide documents separate IP + netmask prompts; 6.14 does not ask that way |
| `Management Port IPv4 Gateway` | |
| `Management Port IPv6 Address/PrefixLen` | Enter to skip |
| `Data Port IPv4` / `IPv6` | Enter to skip if single-homed |
| `Primary DNS` / `Secondary DNS` | must actually resolve |
| `Do you want to enable SLAAC mode?` | `n` when IPv6 is unset |
| `New Password` / `Confirm Password` | **cluster password** — sets CLI `appadmin` AND web `admin` |
| `configure system date time information?` | `y` → `2` for NTP → primary, secondary |
| `configure the timezone?` | `y` → standard `tzselect` (continent → country → zone → confirm) |
| `enable FIPS Mode?` | `n` unless required; it restricts EAP/crypto |

Review the printed **Configuration Summary**, then `y`. The appliance sets the
password, renames itself, restarts networking, regenerates its server
certificate, then stops and restarts the full Policy Manager stack. Expect
**5–8 minutes** of service churn before `Initial configuration is complete.`

### 6. Verify

```bash
ping -c2 <mgmt-ip>
curl -sk -o /dev/null -w '%{http_code}\n' https://<mgmt-ip>/tips/    # 200
```

`https://<mgmt-ip>/` should 302 to `/tips/welcome.action`, presenting a
self-signed `CN=localhost, O=PolicyManager` certificate with a 1-year validity.

Then confirm the appliance agrees with its own flavor — this is the check that
proves the second disk was consumed correctly:

```
[appadmin@<host>]# show system-resources
Current system configuration:  8 CPUs / 8.00 GB / 1045.00 GB
Required system configuration: 8 CPUs / 8 GB / 1000 GB
```

Then **log in once at the console with the new password.** The wizard's
confirm field only proves the two entries matched each other — if a synthesised
keystroke dropped in both, they still match and the stored password is not the
one you think it is.

Only once all of the above passes, enable autostart and take the snapshot that
the rollback section depends on:

```bash
qm set <vmid> --onboot 1
qm snapshot <vmid> post-initial-config
```

## Gotchas (all hit in a real 6.14.0.371380 build)

- **UEFI is mandatory and undocumented.** Under SeaBIOS, GRUB 2.06 emits
  `error: ../../grub-core/script/function.c:119:can't find command 'linuxefi'.`
  (and the same for `initrdefi`), then `Press any key to continue...`.
  Confirmed two ways: that on-screen error, and the image's own
  `/boot/grub2/i386-pc/command.lst`, which registers `linux`, `linux16`,
  `initrd`, `initrd16` and **no** `linuxefi` — no `i386-pc` module contains the
  string at all.
- **That error is only on screen for ~8 seconds.** With `timeout=10` it appears
  ~13 s after power-on and the menu is redrawn by ~22 s. A screenshot taken
  later shows a normal menu, so the symptom presents as "Enter does nothing."
  Sample the console **inside the 10–20 s window** or you will misdiagnose it.
- **The GRUB menu is superuser-protected** (`set superusers="arubasupport"`,
  `password_pbkdf2`). The menu entry is `--unrestricted`, so booting needs no
  password, but `e` and `c` prompt `Enter username:` — you cannot drop to the
  GRUB shell to debug, and a stray `e` looks like another input failure.
- **The guide contradicts itself on disk bus.** The requirements section says
  "Disk bus type must be set to IDE ... Do not use SCSI/VirtIO"; the 6.14
  walkthrough says change the bus to **SCSI**; `create-kvm-cp.sh` uses
  `bus=scsi` for both disks. **`virtio-scsi-pci` is verified working** for both
  disks under OVMF. **[unverified]** whether IDE also works — it was not tested,
  so treat the IDE instruction as unconfirmed rather than disproven.
- **The image is 45 GiB, not the documented 24 GB.** Size the first disk from
  the zip's central directory.
- **The second disk must exist before first power-on** or the appliance
  kernel-panic loops. It is repartitioned and erased during install, so it must
  be empty and disposable.
- **Lowest MAC wins.** Install logs `Associating "<mac>" with eth0`. If the
  management NIC ends up with the higher MAC, the guide's remedy is to delete
  both adapters, re-add them in order, and run `system refresh-network`.
  Assigning MACs explicitly at `qm create` avoids that entirely — Proxmox
  randomises them otherwise, so ordering is a coin flip.
- **The wizard is VGA-only.** `console=tty0` is last on the kernel command line,
  so a serial console shows the boot and never the questions. Automate with
  `qm monitor` `sendkey` + `screendump`.
- **The encryption prompt eats a stray Enter** and the choice is permanent.
  When scripting answers, do not send a trailing Enter after `y` at the
  preceding confirm — it lands here.
- **6.14 asks for the management address as CIDR**, not the IP + netmask pair the
  guide documents. Any pre-baked answer list built from the guide desyncs here
  and every subsequent answer lands in the wrong field.
- **The pre-install and post-install resource readings disagree.** With 8192 MB
  configured, the installer's "Current system configuration" reported
  `Total Memory = 10 GB` while `show system-resources` afterwards reported
  `8.00 GB`. Both passed the C1000V gate; do not resize on the strength of the
  pre-install number.
- **`efidisk0` steals `vm-<vmid>-disk-0` from `scsi0`.** Proxmox allocates drive
  keys in sorted order, so a single `qm create` carrying both gives the EFI-vars
  volume `disk-0` and the boot disk `disk-1` (verified on PVE 9.2). Any runbook
  that hardcodes `disk-0` writes 45 GiB at a 4 MB volume. Always resolve
  `scsi0` through `qm config` + `pvesm path`, which is also the only form that
  works on non-LVM storage.
- **Do not stage helper scripts in `/tmp` on a Proxmox host.** Python puts the
  script's own directory first on `sys.path`, and an unrelated `/tmp/struct.py`
  (proxmox-mcp leaves one) shadows the stdlib `struct` module and kills the
  script at import. Use a dedicated directory.
- **A password confirm field is not a verification.** It proves only that two
  synthesised entries matched each other. Prove the credential by logging in.
- **[unverified] beyond this build:** the CLABV/C2000V/C3000V flavors, `q35`
  machine type (`i440fx` was used), Secure Boot with pre-enrolled keys, and the
  guide's 6.12.x→6.14 upgrade path.

## Day-2 operations

`SKILL.md` ends at a booted, addressed appliance. Licensing, HTTPS certificate
import, and the REST API are covered in
`references/clearpass-day-2-operations.md`. The four that cost the most time:

- **Licence order is mandatory** and the error does not say so — an Access key
  pasted at the Platform Activation screen returns a bare `invalid license key`.
- **The issuing root must be in the Trust List** even for the appliance's own
  server certificate, and CAs must be uploaded as `.crt` — `.pem` is typed
  `application/pkcs7-mime` and rejected.
- **There is no success banner on certificate import.** Verify with
  `openssl s_client`, and build the p12 from fullchain or Android and curl fail
  where desktop browsers pass.
- **The API client secret is never displayed**, so `client_credentials` cannot
  be automated — but **Generate Access Token** mints a usable bearer token, so
  the API itself is not blocked.

## Rollback

Nothing outside the guest is modified, so rollback is bounded. Before first
boot, the VM is disposable: `qm stop <vmid> && qm destroy <vmid> --purge`
(verify the VMID and confirm the guest is not protected). After the wizard has
run, the flavor choice, the encryption decision, and the partitioning of the
second disk are all baked in — recovery is a rebuild from step 2 with a fresh
second disk, not an in-place fix. Take a Proxmox snapshot immediately after
`Initial configuration is complete.` and before any licensing or cluster join,
so the next iteration starts from a configured appliance rather than the flavor
prompt.

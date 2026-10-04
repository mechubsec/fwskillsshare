# Gotchas (all hit in a real build)

Every finding below was encountered in one end-to-end build on Proxmox VE 9.2.20 running cSRX 26.2R1.7. They are preserved here because each one silently breaks the deployment or creates a false-positive pass that looks like success.

## 1. Container reports `Up`, every control-plane daemon looks healthy, but there is no data plane at all

`docker ps` shows `Up`; `mgd`, `idpd`, `authd` are all running; the CLI answers normally — but `show security flow session` errors with `usp_ipc_client_open: failed to connect to the server`, and no traffic, not even ICMP under a permit-all policy, crosses. This reads exactly like a policy or IPC fault.

**Cause:** the packet-forwarding process (`srxpfe`) initializes DPDK's EAL at startup **even when `CSRX_PACKET_DRIVER=interrupt`** — DPDK's EAL hard-requires SSSE3 unconditionally. If the guest's CPU model doesn't expose it, `srxpfe` fails at `EAL: unsupported cpu type` and never starts, while every control-plane daemon comes up fine.

**Fix:** set the guest's CPU model to one exposing SSSE3 (the x86-64-v2 baseline and above, e.g. `x86-64-v2-AES`, or `--cpu host` to pass through all host features), then a **cold** `qm stop`/`qm start` (a soft reboot does not renegotiate the CPU model). Confirm `ssse3` in `/proc/cpuinfo` and `srxpfe` actually running (`ps aux | grep srxpfe`) before trusting any subsequent ping test — **`Up` proves nothing about the data plane.** The only real proof is `show security flow session` succeeding, or `srxpfe` visibly in the process list.

## 2. Traffic passes cleanly on plain Docker networks, then goes unidirectional or silent the moment interfaces move onto macvlan networks parented on real NICs

ARP requests (broadcast) cross fine; ARP replies and all real unicast transit traffic vanish — with or without promiscuous mode set on either end.

**Cause:** Docker's default macvlan mode is `bridge`. At the kernel level, `macvlan_handle_frame()` looks up the destination MAC in the macvlan port's per-child hash table; a frame addressed to a MAC that isn't a known child is dropped unconditionally, regardless of promiscuous mode. That is exactly the situation a bump-in-the-wire firewall creates: it needs to receive frames addressed to MACs that are not its own.

**Fix:** create the macvlan network with `-o macvlan_mode=passthru`, which gives one child the whole parent NIC with no MAC filtering — one macvlan network per parent. **A live `docker network connect` from `bridge` to `passthru` networks on an already-running container is not sufficient by itself** — cSRX's boot-time tap↔interface MAC-pairing logic has already latched onto the old MACs, leaving traffic dead in both directions until a full `docker restart` of the container.

## 3. TCP hangs or loses most of its data on a path ICMP crosses cleanly

`ping` shows 0% loss; `iperf3` on the same path hangs indefinitely or transfers at a fraction of expected throughput with heavy retransmission.

**Cause:** GSO/TSO and TX checksum offload left enabled on host-side virtual interfaces — the endpoints' veth peers and the hypervisor's tap devices. These offloads leave a placeholder checksum on the wire, expecting a NIC further down the chain to finish the calculation; through several layers of software bridging and cSRX's raw-copy forwarding path, nothing ever finishes it, and the segment arrives provably corrupt (confirm with `tcpdump -vv`: an identical placeholder checksum across packets with different sequence numbers). The receiving kernel silently drops these (`InCsumErrors` in `/proc/net/snmp`'s `Tcp:` line increments by exactly the SYN-retransmit count). ICMP carries its own checksum with no offload involved, so it's unaffected.

**Fix:** `ethtool -K <iface> tx-checksum-ip-generic off tso off gso off` at **every** hop — one end is not sufficient. Confirm by watching `InCsumErrors` stop incrementing across a full transfer, not just by improved throughput. **Does not survive a reboot** of either endpoint — re-check, don't assume, before trusting any future throughput measurement on the same path.

## 4. A deny policy is committed, traffic is genuinely blocked, but nothing shows in the log

`then deny` + `then log session-init` commits cleanly; the matching traffic is confirmed blocked (100% loss, non-zero policy hit-counter) — but `show log messages | match RT_FLOW` returns nothing.

**Cause:** this image ships with **no default local-logging configuration** — no `messages` file under `/var/log/`, and both `show configuration system syslog` and `show configuration security log` are empty by default on every freshly recreated container, not just first boot. `then log session-init` alone is not sufficient without a syslog destination and a security-log mode.

**Fix:** commit `set system syslog file messages any any` **and** `set security log mode event` together, as part of the same commit as the interface/zone/policy config — not as a reaction to "the log is empty."

## 5. `CSRX_JUNIPER_CONFIG` is silently discarded

Its name looks exactly like the "supply startup config" knob; it is not. The init script unconditionally hardcodes it to `/config/juniper.conf` after sourcing the environment and before first use — anything supplied at `docker run` time is thrown away with no warning.

**Fix:** use `CSRX_JUNOS_CONFIG` (loaded with `load merge` if the path exists) instead, or bind-mount a file directly at `/config/juniper.conf`.

## 6. Secure-wire mode rejects `family inet` outright

Committing an IP address on a secure-wire data interface is a commit error, not a warning.

**Cause:** `CSRX_FORWARD_MODE=wire` is a true Layer-2 splice, never an IP-aware bump-in-the-wire — it forces the two segments it bridges to already share one IP subnet. Plan the topology around this before choosing wire mode, not after a commit fails.

## 7. A routing-mode rebuild has no addressable logical unit at all

After rebuilding into `CSRX_FORWARD_MODE=routing`, the full `show interfaces ge-0/0/0` form shows the link physically Up with **no logical unit beneath it** — no `unit 0`, no `family`, nothing to address (`show interfaces terse` is empty on cSRX regardless — see `csrx-cli-gaps.md` — and proves nothing here).

**Cause:** cSRX does not auto-create a logical unit on its data interfaces when the forward mode changes; there is no auto-addressing fallback to fall back to.

**Fix:** explicit interface configuration is mandatory — `set interfaces ge-0/0/0 unit 0 family inet address ...` on every data interface, plus zone binding and whatever `host-inbound-traffic system-services` entries the interface itself needs to answer (at minimum `ping`, if the verification plan pings the interface's own address).

## 8. cSRX's operational CLI is measurably thinner than a vSRX's — plan verification around this, don't assume parity

Seven confirmed gaps, none producing a self-explanatory "command not found" error. The sharpest traps: `show interfaces terse` is silently empty (no rows, no header, no error) even with interfaces up and passing traffic; `show route` and `show arp` fail with hard syntax errors, not merely empty results. The missing `rpd` explains the route/ARP gaps; the remainder reflect that cSRX has no chassis/RE object. Test the exact commands a verification plan depends on against the specific cSRX build in hand before relying on them, and default to the Linux-side fallback (`/proc/net/snmp`, `tcpdump`) rather than treating it as a last resort.

Full catalogue, substitutes, and the list of commands verified working: **`csrx-cli-gaps.md`**.

## 9. A macvlan parent interface is administratively down, and nothing about the guest build brought it up

A NIC meant to parent a Docker macvlan network shows `DOWN` in the guest, with no network-config stanza referencing it, even though the hypervisor reports the link connected.

**Cause:** a provisioned guest typically only configures the interface(s) it was told to bring up (usually just management via DHCP); interfaces with no addressing intent are left exactly as the kernel presents them.

**Fix:** a macvlan parent needs no IP address but must be administratively **up** — add a minimal, address-free stanza for it as part of the guest build itself, not the first time a macvlan network needs it, which conflates "did the interface come up" with "does the traffic work."

## 10. The first virtual NIC does not get the interface name you'd expect from the others

A guest with several vNICs on the same virtual bus does not necessarily name them with one consistent scheme — in this build the first (management) NIC came up as a plain `eth0` while the data-plane NICs came up as `ensNN` as expected. A udev/systemd naming-scheme quirk, not a hypervisor guarantee.

**Fix:** never assume a naming pattern from NIC ordering — confirm each in-guest interface name against its MAC address (`cat /sys/class/net/<if>/address`), matched to the hypervisor's own record of which MAC was assigned to which vNIC slot, not by position.

## 11. `qm guest cmd` (or the equivalent host-agent call) never answers, no matter how long you wait

The guest has the guest-agent channel enabled (`--agent 1`), but every call fails permanently with `QEMU guest agent is not running` — not a timing issue; it never resolves.

**Cause:** `--agent 1` only enables the **hypervisor-side** channel — it does not install the in-guest agent package, and common minimal cloud images don't ship it.

**Fix:** add the package to first-boot provisioning, or resolve the guest's address from the hypervisor's own ARP/neighbor table by its known MAC (`ip neigh show <addr>`) instead.

## 12. A NIC hot-added to an already-running container never actually comes up

Its network config correctly shows the new interface with DHCP configured, but it never acquires an IPv4 address — only IPv6 SLAAC, if anything — and DNS/HTTP through it fails with errors that look like a DNS problem.

**Cause:** hotplugging a NIC does not automatically trigger interface bringup (`ifup`) in every container OS/init combination, even with a correct static config present.

**Fix:** explicitly `ifup <iface>` after adding it; verify with `ip -4 addr show <iface>` before proceeding.

## 13. A package install appears to hang forever with `-y -qq` set

`apt-get install -y -qq <package>` run non-interactively simply never completes — no error, no output, no timeout.

**Cause:** `-y`/`-qq` silence apt's own prompts but not an interactive `debconf` dialog raised by a postinst script (e.g. "start this service as a daemon automatically?"). The install is genuinely blocked on a TTY prompt that will never be answered.

**Fix:** always set `DEBIAN_FRONTEND=noninteractive` for any install that might ship an interactive postinst. If already stuck: kill the blocked process tree, run `DEBIAN_FRONTEND=noninteractive dpkg --configure -a` to finish the half-configured package, then retry with the frontend variable set for the whole invocation.

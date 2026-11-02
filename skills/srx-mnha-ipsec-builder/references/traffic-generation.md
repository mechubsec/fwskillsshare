# Generating and measuring test traffic

Any pair of hosts works: one **behind each side of the path under test** (for IPsec: one behind the spoke, one
behind the hub; for a plain MNHA pair: one on each side of the pair). A traffic-generator MCP server (for example
a Kali MCP server) is **optional**: it only lets the assistant run these commands itself. Without it, run the
commands by hand and paste the output back.

Only **transit** traffic is a valid failover test. Pings or sessions originated by the firewall itself are not
representative (self-originated sessions are not synchronised, and replies may return through the other node).

## 0. Prerequisites
- Security policy on the firewalls permitting the test traffic in both directions (e.g. TCP/UDP 5201 and ICMP
  between the two test hosts) - logged policies make good evidence.
- Routes in both directions (check `show route <host>` on the active node).
- Clocks: not required for loss counting (sequence numbers), but needed to line up device logs with your commands.

## 1. iperf3 (recommended)
Install: Debian/Ubuntu/Kali `sudo apt-get install -y iperf3` · RHEL/Fedora `sudo dnf install -y iperf3` ·
macOS `brew install iperf3` · Windows: iperf3 binaries (iperf.fr). If `apt` is in a broken half-upgraded state:
`apt-get download iperf3 libiperf0 libsctp1` then `sudo dpkg -i libsctp1_*.deb libiperf0_*.deb iperf3_*.deb`.

Server (on the host behind the hub / far side):
```
iperf3 -s -p 5201                                  # foreground
iperf3 -s -D -p 5201 --logfile /tmp/iperf3-srv.log # daemon
```
Client (on the other host). **Pacing:** with `-l 1000` payload, packets per second = rate / (8 x 1000), so
`-b 20M` = 2,500 pps and every lost datagram is 0.4 ms of outage.
```
# sanity check, 5 s each way
iperf3 -c SERVER -p 5201 -t 5
iperf3 -c SERVER -p 5201 -t 5 -R

# UDP, both directions at the same time (iperf3 >= 3.7 on BOTH ends): the standard failover test
nohup timeout 175 iperf3 -c SERVER -p 5201 -u -b 20M -l 1000 -t 150 -i 0.1 --bidir \
  --get-server-output --forceflush --timestamps='%H:%M:%S ' > run1.log 2>&1 &

# UDP, one direction at a time
iperf3 -c SERVER -p 5201 -u -b 20M -l 1000 -t 150 -i 0.1 --get-server-output          # client -> server
iperf3 -c SERVER -p 5201 -u -b 20M -l 1000 -t 150 -i 0.1 --get-server-output -R       # server -> client

# TCP session survival (one long flow; the same connection must finish with no reset)
iperf3 -c SERVER -p 5201 -t 150 -b 100M -i 0.1 --timestamps='%H:%M:%S ' --forceflush
```
Older iperf3 without `--bidir`: run **two servers** (`iperf3 -s -p 5201` and `iperf3 -s -p 5202`) and two clients
at once - `iperf3 -c SERVER -p 5201 -u -b 20M -l 1000 -t 150 -i 0.1` and
`iperf3 -c SERVER -p 5202 -u -b 20M -l 1000 -t 150 -i 0.1 -R`.

Read a bidirectional run. In the `--bidir` log, interval lines tagged `[RX-C]` are
server->client (the client's 0.1 s intervals) and lines tagged `[RX-S]` are
client->server (the server's 1 s intervals, from `--get-server-output`). Each UDP interval
line ends with `lost/total (percent%)`.
1. Per direction, ignore intervals that start before 1.0 s (start-up noise: expect a
   handful of lost datagrams in the first 0.1 s of every run).
2. Merge consecutive intervals with loss (gaps of 0.3 s or less) into one **loss
   window**; outage per window = lost datagrams / pps.
3. Sum the lost datagrams per direction. Against a baseline run: % change =
   (variant lost - baseline lost) / baseline lost x 100. If the baseline lost nothing,
   report the absolute count instead of a percentage.

A quick per-direction total from the log (skips the start-up intervals and the 0-150 s
summary line):
```
for d in RX-C RX-S; do awk -v d="$d" 'index($0, "[" d "]") { if (match($0, /[0-9.]+-[0-9.]+ +sec/)) { split(substr($0, RSTART, RLENGTH), t, "-"); if (t[1] + 0 >= 1 && match($0, /[0-9]+\/[0-9]+ \(/)) { split(substr($0, RSTART, RLENGTH), n, "/"); c += n[1] } } } END { print d, "lost", c + 0 }' run1.log; done
```

## 2. No iperf3: count sequence gaps on the receiver
Use any generator that numbers or paces its packets, and count on the receiver. Run one
generator per direction at the same time.
```
# receiver (far host): capture the stream
sudo tcpdump -ni IFACE -w rx_a.pcap 'udp port 5001'
# sender (near host): 2,500 pps, 1000-byte payload, 150 s
sudo nping --udp -p 5001 --data-length 1000 --rate 2500 -c 375000 FAR_HOST
# afterwards: packets received vs sent
tcpdump -nr rx_a.pcap | wc -l          # lost = 375000 - received; outage = lost / 2500
tcpdump -tt -nr rx_a.pcap | awk '{ if (p && $1 - p > 0.01) print "gap at", p, "for", $1 - p, "s"; p = $1 }'
```
The second `tcpdump` lists each gap longer than 10 ms with its start time and length;
line those times up with the failover command and `show system commit`.

## 3. Other generators
```
# ICMP (loss counted by gaps); intervals below 0.2 s need root
sudo ping -D -O -i 0.1 -W 1 -c 1500 DEST > ping.log       # outage ~ lost x interval
grep -c "no answer" ping.log
# Windows
ping -t DEST                                               # 1 s resolution only: use iperf3.exe for sub-second work
# hping3 / nping as pure generators (loss must be counted on the receiver, e.g. with tcpdump)
sudo hping3 --udp -p 5001 -d 1000 -i u400 DEST             # 400 microseconds = 2,500 pps
sudo nping --udp -p 5001 --data-length 1000 --rate 2500 -c 375000 DEST
# receiver evidence
sudo tcpdump -ni IFACE -w capture.pcap 'udp port 5001'
```
Long-lived TCP sessions as a quick survival check: open an SSH session through the pair and run
`while true; do date; sleep 1; done` (watch for a stall, not for a reset), or `nc -l 7000` / `nc DEST 7000` with a
looping sender.

## 4. Failure triggers (run on the **active** node unless noted)
```
# planned switchover (peer-id = the peer's local-id; mandatory on some releases)
request chassis high-availability failover services-redundancy-group <N> peer-id <ID>

# unplanned: take the uplink down, self-restoring after 2 minutes if not confirmed
configure
set interfaces <uplink> disable
commit confirmed 2
# Never confirm this commit: confirming it would leave the active hub's uplink
# disabled. Let it roll back, or restore early with rollback 1 + commit.
# (through junos-mcp-server: confirm_timeout_mins: 2 on the config tool; do not call confirm_commit)
# Until it rolls back, no commit check, dry run or other commit on this node:
# Junos treats any of them as confirming the pending commit.

# restore early
rollback 1
commit
```
Other unplanned triggers: disable the vNIC/switch port outside the firewall, or (destructive, ask first) power the node off.

## 5. Evidence to collect on the SRX during a run
```
show chassis high-availability services-redundancy-group <N>     # roles, VIP, signal routes, flag state
show chassis high-availability information
show security ipsec security-associations                         # same SPIs on both hub nodes
show security flow session destination-port 5201                  # Active on one node, Warm on the other
show bgp summary ; show bfd session extensive ; show route <prefix>
show interfaces st0.<unit> statistics                             # sample twice, subtract: is the backup transmitting?
show system commit                                                # commit timestamps vs the stream window
show log <filtered-file>                                          # see testing.md
```

## 6. Read the result
- Loss % = lost / (sent) x 100; outage = lost / pps. Report each direction separately.
- A result of zero loss is only valid if the failure event's timestamp (`show system commit`, or the time you typed
  the failover command) lies **inside** the stream window.
- Compare against a baseline you measured yourself on the same lab/prod path; absolute times do not transfer.

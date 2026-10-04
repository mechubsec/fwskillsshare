# Field notes: system syslog silently dropped on a non-default port

## Contents

- [Symptom](#symptom)
- [The three devices](#the-three-devices)
- [What was eliminated, and how](#what-was-eliminated-and-how)
- [The test that found it](#the-test-that-found-it)
- [The fix](#the-fix)
- [Second fault, found during verification](#second-fault-found-during-verification)
- [Lessons worth carrying](#lessons-worth-carrying)

**Platform:** vSRX, Junos 25.4R1.12. Addresses below are documentation ranges
(RFC 5737); device names are generic. Verify the behaviour on your own platform
and release before designing around it.

A record of a real diagnosis, kept because the fault was cheap to fix and
expensive to find — six plausible hypotheses failed first.

## Symptom

Two of three vSRX devices had never delivered a single `system syslog` event to
the collector — not one, across days of uptime. Their configuration looked
correct and matched the device that worked.

One of the failing devices was simultaneously delivering tens of thousands of
`security log` events to the *same collector address*.

## The three devices

| | fw-a (working) | fw-b (failing) | fw-c (failing) |
|---|---|---|---|
| System syslog | **worked** | never | never |
| Security log | n/a | worked | n/a (no transit traffic) |
| Route to collector | **via fxp0** | via revenue port | via revenue port |
| fxp0 | addressed, default instance | **unaddressed** | addressed, inside `mgmt_junos` |
| Revenue port | different subnet from collector | same subnet as collector | same subnet as collector |
| `syslog source-address` | **absent** | set | absent |
| Revenue port zone | untrust | untrust | untrust |
| Hostname | real | real | **golden-image placeholder** |

The syslog stanza was byte-identical on all three:

```
host 198.51.100.10 { any info; port 5140; structured-data; }
```

## What was eliminated, and how

Each was tested, not reasoned about:

1. **`source-address`** — the working device had none; a failing device had it
   set correctly. Removing it from the failing device changed nothing.
2. **Routing and reachability** — `ping` succeeded from the intended source. So
   did `traceroute`, which is UDP, proving the RE could emit UDP out the revenue
   interface.
3. **`junos-host` security policy** — the theory was that RE-originated traffic
   leaving a zoned revenue port needs a `from-zone junos-host` permit. A scoped
   permit changed nothing; broadening it to `application any` changed nothing.
4. **Stale `eventd`** — `restart event-processing` gave a fresh pid, no change.
5. **Management routing instance** — plausible for fw-c, but fw-b had no
   management instance and failed identically. The `routing-instance` statement
   was also rejected outright on this platform.
6. **fxp0 unaddressed** — addressing fxp0 into the *same subnet as the revenue
   port* had no effect whatsoever, because the revenue interface already owned
   that subnet and kept the active route. This violated the "fxp0 on its own
   logical network" rule and was reverted.

## The test that found it

Add a **second** syslog host, on an unused address, with default settings:

```
set system syslog host 198.51.100.11 any info
```

Packets appeared immediately, sourced from the revenue interface address, out the
revenue interface. **System syslog worked all along.**

Then change exactly one thing:

```
set system syslog host 198.51.100.11 port 5140
```

Delivery stopped dead. No security policy covered that host in either case, so
policy was not the variable. Neither was source address, interface, routing, nor
daemon state.

**A non-default port was being silently discarded when system syslog egressed a
revenue interface.**

The working device was never a valid counter-example: its syslog leaves via
**fxp0**, which is wired directly to the RE and bypasses flow processing, so the
non-default port survives there.

## The fix

```
delete system syslog host 198.51.100.10 port
```

Both devices delivered within seconds. Everything added while chasing the fault —
the `junos-host` policy, an address-book entry, a custom application, the fxp0
address — was removed as unnecessary.

## Second fault, found during verification

The failing CI device's events arrived but landed with an **empty** observer
hostname, because it still carried the golden-image placeholder
`host-name source-device`, which the ingest pipeline rejected. Setting a real
hostname made the events attributable immediately.

Delivery and attribution are separate claims. Verify both.

## Lessons worth carrying

- **Confirm the device is emitting before debugging delivery.** All six
  hypotheses concerned *reaching* the collector. None was the fault.
- **A working sibling is only a valid control if it exercises the same path.**
  The reference device was treated as proof the configuration was correct, but it
  used fxp0 while the failing devices used a revenue port. That one unnoticed
  difference invalidated the comparison and produced three dead ends. Compare the
  *path*, not just the config text.
- **Capture at the device, filtered, with a forced event.** An unfiltered capture
  fills with multicast noise; an unforced window catches nothing, because pooled
  NETCONF sessions generate no syslog.
- **A second host entry is the cheapest single-variable test available.** It needs
  no collector-side change and isolates the variable in one commit.

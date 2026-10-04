# Virtual NIC to Junos interface mapping

## Contents

- [The rule](#the-rule)
- [Standalone-shaped guests cannot be promoted in place](#standalone-shaped-guests-cannot-be-promoted-in-place)
- [Verify the mapping, do not assume it](#verify-the-mapping-do-not-assume-it)
- [Release coverage](#release-coverage)
- [Sizing the NIC list](#sizing-the-nic-list)

## The rule

When a vSRX guest boots in chassis-cluster mode, its virtual NICs map to Junos interfaces like this:

| Virtual NIC | Junos interface |
|---|---|
| `net0` | `fxp0` — out-of-band management |
| `net1` | `em0` — cluster control link |
| `netN` where N is 2 or greater | `ge-0/0/(N-2)` |

The secondary node presents the same physical NICs under a different slot number. Node 0 owns slot 0 and node 1 owns slot 7, so `net4` is `ge-0/0/2` on node 0 and `ge-7/0/2` on node 1. Both refer to the same NIC index in the same position of each guest's NIC list.

Worked for an eight-NIC node:

| NIC | Node 0 | Node 1 | Typical role |
|---|---|---|---|
| `net0` | `fxp0` | `fxp0` | management |
| `net1` | `em0` | `em0` | control link |
| `net2` | `ge-0/0/0` | `ge-7/0/0` | reth member |
| `net3` | `ge-0/0/1` | `ge-7/0/1` | reth member |
| `net4` | `ge-0/0/2` | `ge-7/0/2` | reth member |
| `net5` | `ge-0/0/3` | `ge-7/0/3` | fabric member |
| `net6` | `ge-0/0/4` | `ge-7/0/4` | reth member |
| `net7` | `ge-0/0/5` | `ge-7/0/5` | reth member |

Which NIC carries the fabric is a design choice, not a fixed rule. What is fixed is `net0` to `fxp0`, `net1` to `em0`, and the shift by two for everything after.

## Standalone-shaped guests cannot be promoted in place

This is the consequence that costs the most time, so treat it as the first thing to check.

A vSRX built as a standalone firewall uses its second NIC for data. When that same guest enters cluster mode, the second NIC becomes `em0`, the control link. The data segment it used to carry is gone from the data plane, and every interface after it shifts down by one position:

- what was `ge-0/0/0` is now `em0`
- what was `ge-0/0/1` is now `ge-0/0/0`
- what was `ge-0/0/2` is now `ge-0/0/1`

Every address, zone assignment, routing statement, and policy that named an interface now names the wrong wire. If the second NIC carried the internet-facing segment, enabling clustering removes internet connectivity and repurposes that segment as an internal control link.

**A standalone-shaped guest needs its NIC plan redrawn before it can become a cluster node.** Adding the control and fabric segments to the end of the NIC list does not avoid this — position, not order of addition, determines the mapping.

Observed case: a pair of four-NIC vSRX guests intended to become a cluster, each wired as management plus three data VLANs, with no control or fabric segment. Enabling cluster mode would have consumed the first data VLAN — the north-facing internet segment — as the control link and shifted the remaining two. The pair was left unclustered instead.

## Verify the mapping, do not assume it

Image builds and Junos releases differ. Confirm the mapping on the actual guests before applying configuration that depends on it.

**Fast check.** After the nodes boot in cluster mode:

```
show interfaces terse | match "^ge-|^em0|^fxp0"
```

Expect `em0`, `fxp0`, and a contiguous `ge-0/0/*` range whose length equals the NIC count minus two, mirrored as `ge-7/0/*`.

**Positive confirmation.** The interface list alone does not prove *which* NIC became which interface. To prove it, pick an interface whose segment is identifiable from outside the guest, then trace it in both directions:

1. Choose a reth carrying an address on a subnet you can recognise — ideally one that also exists outside the hypervisor.
2. Find its physical member: `show configuration interfaces | match redundant-parent`.
3. Convert that `ge-` index to a NIC index with the rule: `ge-0/0/K` is `net(K+2)`.
4. On the hypervisor, confirm that guest's tap interface at that index sits on the bridge and VLAN carrying that subnet.

If step 4 lands on the expected segment, the mapping holds.

Worked example from the reference build: `reth1` is built from `ge-0/0/1`. By the rule that is `net3`. On the hypervisor, `net3` is attached untagged to the bridge carrying the site LAN, and `reth1` is addressed inside that LAN's subnet. A mapping shifted by even one position would have put `reth1` on a different segment entirely, so the agreement confirms the shift-by-two rule rather than merely being consistent with it.

**The strongest check: match reth virtual MACs against tap interfaces.** Once the reths are configured, each one's virtual MAC appears in the hypervisor's forwarding table on exactly the tap carrying it. Because the MAC encodes the reth number and the tap name encodes the NIC index, one command verifies the entire mapping at once:

```
bridge fdb show | grep -i '00:10:db'
```

From a cluster built with cluster-id 9, five reths, and one VLAN per reth:

```
00:10:db:ff:90:00 dev tap330i2 vlan 282 master vmbr7    # reth0 -> net2 -> ge-0/0/0
00:10:db:ff:90:01 dev tap330i3 vlan 283 master vmbr7    # reth1 -> net3 -> ge-0/0/1
00:10:db:ff:90:02 dev tap330i4 vlan 284 master vmbr7    # reth2 -> net4 -> ge-0/0/2
00:10:db:ff:90:03 dev tap330i6 vlan 285 master vmbr7    # reth3 -> net6 -> ge-0/0/4
00:10:db:ff:90:04 dev tap330i7 vlan 286 master vmbr7    # reth4 -> net7 -> ge-0/0/5
```

Every reth landed on the tap the rule predicts, including the gap at `net5` where the fabric sits. Entries appear only on the primary node's taps, which is also correct.

**A second positive proof comes free from the fabric.** If each segment has its own VLAN, the fabric can only reach `Up / Up` when both nodes' fabric members sit on the same VLAN — so a fabric that comes up confirms that `ge-0/0/X` and `ge-7/0/X` are the NICs you think they are.

**What does not work: matching `ge-` MAC addresses.** On vSRX the `ge-` interfaces are assigned synthetic Juniper MACs (`4c:96:14:…`), not the hypervisor-assigned addresses, so comparing them against the guest's NIC list proves nothing. Only `fxp0` and `em0` keep their assigned MACs, which does at least confirm those two anchors:

```
show interfaces extensive | match "Current address"
```

## Release coverage

The shift-by-two mapping was confirmed independently on **Junos 24.4R1.9** and **Junos 26.2R1.7**, on different hosts and with different cluster-ids. It has been stable across that range, but verify it anyway on an unfamiliar image — the cost is one command and the cost of being wrong is every interface reference in the configuration.

## Sizing the NIC list

Count before cloning:

```
NICs = 1 (management) + 1 (control) + 1 (fabric) + one per reth
```

`reth-count` in the configuration must be at least the highest reth number in use. Templates are almost always standalone-shaped, so expect to both rewire existing NICs and add new ones rather than simply appending.

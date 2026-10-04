# srx-advpn evals

Run each scenario in a fresh agent session with the skill installed, then again without it as a baseline. A scenario passes only when every "Must" holds and no "Must not" occurs.

## Scenario 1: Certificate requirement commit error

**Prompt:** Configure ADVPN on three vSRX nodes (one hub, two spokes) running Junos 24.4R1.9 with pre-shared keys.

**Input:** None

**Must:**
- State that `dynamic ike-user-type` + IKEv2 + `pre-shared-keys` does NOT commit on 24.4R1+ / 25.4R1
- Cite the commit error message: "When dynamic ike-user-type is configured, IKEv2 with authentication-method pre-shared-key is not allowed"
- Recommend certificate (PKI) authentication OR per-spoke static-address gateways for PSK
- Reference the PKI enrollment section from srx-advpn skill or srx-autovpn-full-tunnel

**Must not:**
- Provide a PSK-based `group-ike-id` gateway configuration without warning it will fail commit
- Commit configuration to the device without explicit approval
- Claim the version constraint is a generic Junos behavior (it's specific to 24.4R1+ / 25.4R1)

## Scenario 2: No public key found IKE_AUTH failure

**Prompt:** My ADVPN hub (vSRX3 24.4R1.9) shows `ikev2_reply_cb_public_key: Error: No public key found` for every spoke cert at IKE_AUTH. Certificates verify on each node. What's wrong?

**Input:**
```
Hub gateway config:
set security ike gateway ADVPN-HUB-GW dynamic hostname homelab.local
set security ike gateway ADVPN-HUB-GW dynamic ike-user-type group-ike-id
set security ike gateway ADVPN-HUB-GW local-identity distinguished-name
set security ike policy ADVPN-IKE-POL certificate local-certificate ADVPN-CERT
set security ike policy ADVPN-IKE-POL certificate trusted-ca LAB-CA

Spoke cert validates:
request security pki local-certificate verify certificate-id ADVPN-CERT
Certificate verification successful
```

**Must:**
- Identify this as a known defect in the dynamic cert gateway responder path on vSRX3 24.4R1/25.4R1
- Explain that the dynamic gateway path never hands peer CERT to pkid (no `send_ipc` call)
- Recommend per-spoke static-address certificate gateways on the hub as the working fix
- State this loses zero-touch but the certificate responder path works
- Reference the troubleshooting matrix "No public key found" root cause section

**Must not:**
- Suggest changing cert EKU, clock, or CA trust (root cause is in iked's dynamic-gateway code path)
- Recommend `restart ipsec-key-management` as a fix (does not address the code path issue)
- Claim this is a misconfiguration (it's an iked-internal defect per field isolation)

## Scenario 3: Shortcut forms but traffic still via hub

**Prompt:** ADVPN shortcuts show UP between spoke WAN IPs, but spoke-to-spoke traffic still hairpins through the hub. Why?

**Input:**
```
show security ike security-associations (shows shortcut SA between spokes)
show security ipsec security-associations (shows shortcut on same st0.1)
show ospf neighbor (shows hub adjacency only, no spoke-to-spoke adjacencies)
```

**Must:**
- Identify that OSPF is not forming adjacencies over shortcuts
- Check if `dynamic-neighbors` is missing from OSPF st0.1 configuration
- Check if zone `protocols ospf` host-inbound is blocked
- Check if LAN routes are not being advertised into OSPF
- Explain that routing — not selectors — steers traffic onto shortcuts

**Must not:**
- Suggest adding traffic selectors (ADVPN uses multipoint st0 with no traffic-selector config)
- Recommend changing the shortcut idle-time/idle-threshold without addressing routing
- Claim the shortcut is "broken" when the IKE/IPsec SA are UP (it's a routing issue)

# SRX AutoVPN Full-Tunnel Backhaul — Source Index

Retrieved: 2026-06-29

- [SRX AutoVPN — Full-Tunnel Backhaul (lab)](source-design-summary.md)
  - URL: https://github.com/anderson-jason573/srx-autovpn-backhaul-public
  - Author: Jason Anderson
  - Topic: Validated four-vSRX (Junos 23.2R2.21) + Cisco IOS-XE lab. AutoVPN
    dynamic `group-ike-id` hub, traffic selectors + Auto Route Insertion (ARI),
    single shared `st0.0`, full-tunnel backhaul, hub source-NAT internet egress,
    spoke-to-spoke hairpin, anti-recursion route, and the vSRX management-default
    ECMP caveat. `source-design-summary.md` is a derived summary of this lab.

- [AutoVPN on Hub-and-Spoke Devices | Junos OS](https://www.juniper.net/documentation/us/en/software/junos/vpn-ipsec/topics/topic-map/security-autovpn-on-hub-and-spoke-devices.html)
  - Source: Juniper Junos IPsec VPN documentation
  - Topic: AutoVPN dynamic gateway, `group-ike-id`, and hub/spoke roles.

- [Understanding Traffic Selectors in Route-Based VPNs | Junos OS](https://www.juniper.net/documentation/us/en/software/junos/vpn-ipsec/topics/topic-map/security-traffic-selectors-in-route-based-vpns.html)
  - Source: Juniper Junos IPsec VPN documentation
  - Topic: Traffic selectors, `local-ip`/`remote-ip` narrowing, and ARI.

- [Example: Configuring AutoVPN with Pre-Shared Key | Junos OS](https://www.juniper.net/documentation/us/en/software/junos/interfaces-next-gen-services/topics/example/configuring-auto-vpn-pre-shared-key.html)
  - Source: Juniper Junos documentation
  - Topic: Worked AutoVPN PSK example (hub dynamic gateway + spoke identities).

- [IPsec VPN User Guide | Junos OS](https://www.juniper.net/documentation/us/en/software/junos/vpn-ipsec/index.html)
  - Source: Juniper Junos IPsec VPN documentation
  - Topic: IKE/IPsec proposals, policies, gateways, `st0` bind-interface, and
    operational `show`/`clear` commands.

## Inspiration and license boundary

v1.1 additionally incorporates a community field report (upstream fwskillsshare issues #5/#6,
https://github.com/mechubsec/fwskillsshare/issues/5): 24.4R1/25.4R1 commit
constraints (ike-user-type + IKEv2 + PSK; traffic-selector 0.0.0.0/0 with a static
gateway address) and NAT-T findings (double-NAT, host-inbound ike).

The public lab carries no explicit license file. It inspired the topology and
test questions, but the repository is not bundled or relicensed here. The skill
and `source-design-summary.md` are independently written; consult the upstream
repository under its own terms for the original lab.

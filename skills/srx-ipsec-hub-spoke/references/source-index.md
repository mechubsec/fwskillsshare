# SRX Static P2P IPsec Hub-and-Spoke — Source Index

Retrieved: 2026-06-29

- [SRX Static Point-to-Point Hub-and-Spoke — Full-Tunnel Backhaul (lab)](source-design-summary.md)
  - URL: https://github.com/anderson-jason573/srx-p2p-ipsec-public
  - Author: Jason Anderson
  - Topic: Validated four-vSRX (Junos 23.2R2.21) + Cisco IOS-XE lab. Static
    per-spoke route-based IPsec (one IKE gateway pinned by peer WAN IP, one `st0`
    unit, and one static route per spoke), no traffic selectors, no ARI,
    full-tunnel backhaul, hub source-NAT internet egress, spoke-to-spoke hairpin
    across `st0` units, anti-recursion route, and the vSRX management-default ECMP
    caveat. `source-design-summary.md` is a derived summary of this lab.

- [Route-Based IPsec VPNs | Junos OS](https://www.juniper.net/documentation/us/en/software/junos/vpn-ipsec/topics/topic-map/security-route-based-ipsec-vpns.html)
  - Source: Juniper Junos IPsec VPN documentation
  - Topic: Route-based VPN with `bind-interface st0`, default proxy-id, and routing.

- [IPsec VPN Overview, Understanding Hub-and-Spoke VPNs | Junos OS](https://www.juniper.net/documentation/us/en/software/junos/vpn-ipsec/topics/topic-map/security-ipsecvpn-overview.html#id-understanding-hub-and-spoke-vpns)
  - Source: Juniper Junos IPsec VPN documentation
  - Topic: Hub-and-spoke topology with per-spoke tunnels and hub routing.

- [IPsec VPN User Guide | Junos OS](https://www.juniper.net/documentation/us/en/software/junos/vpn-ipsec/index.html)
  - Source: Juniper Junos IPsec VPN documentation
  - Topic: IKE/IPsec proposals, policies, gateways (`address`-based), `st0`
    bind-interface, and operational `show`/`clear` commands.

## Inspiration and license boundary

The public lab carries no explicit license file. It inspired the topology and
test questions, but the repository is not bundled or relicensed here. The skill
and `source-design-summary.md` are independently written; consult the upstream
repository under its own terms for the original lab.

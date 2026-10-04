# Fixture: Minimal Firepower Input

## Contents

- [Input Format](#input-format)
- [Coverage](#coverage)

This is a synthetic FMC REST API export bundle demonstrating the parsing patterns
and edge cases. No real addresses, hostnames, or secrets are present.

## Input Format

The input uses the keyed envelope format from `config-format.md`:

```json
{
  "fmc_exports": {
    "domain_uuid": "e276abec-e0f2-11e3-8169-6d9ed49b625f",
    "responses": {
      "securityzones": {
        "items": [
          {
            "type": "SecurityZone",
            "id": "zone-1111-1111-1111-111111111111",
            "name": "inside-zone",
            "interfaceMode": "ROUTED"
          },
          {
            "type": "SecurityZone",
            "id": "zone-2222-2222-2222-222222222222",
            "name": "outside-zone",
            "interfaceMode": "ROUTED"
          }
        ],
        "paging": {
          "count": 2,
          "limit": 25,
          "offset": 0,
          "pages": 1
        }
      },
      "networks": {
        "items": [
          {
            "type": "Network",
            "id": "net-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "name": "server-net",
            "value": "192.0.2.0/24"
          }
        ],
        "paging": {
          "count": 1,
          "limit": 25,
          "offset": 0,
          "pages": 1
        }
      },
      "networkgroups": {
        "items": [
          {
            "type": "NetworkGroup",
            "id": "netg-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            "name": "trusted-nets",
            "objects": [
              {
                "type": "Network",
                "id": "net-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                "name": "server-net"
              }
            ]
          }
        ],
        "paging": {
          "count": 1,
          "limit": 25,
          "offset": 0,
          "pages": 1
        }
      },
      "protocolportobjects": {
        "items": [
          {
            "type": "ProtocolPortObject",
            "id": "port-cccc-cccc-cccc-cccccccccccc",
            "name": "custom-port",
            "protocol": "TCP",
            "port": "8080"
          }
        ],
        "paging": {
          "count": 5,
          "limit": 25,
          "offset": 0,
          "pages": 1
        }
      },
      "accesspolicies": {
        "items": [
          {
            "type": "AccessPolicy",
            "id": "acp-dddd-dddd-dddd-dddddddddddd",
            "name": "test-policy",
            "defaultAction": {
              "action": "BLOCK"
            }
          }
        ],
        "paging": {
          "count": 1,
          "limit": 25,
          "offset": 0,
          "pages": 1
        }
      },
      "prefilterpolicies": {
        "items": [
          {
            "type": "PreFilterPolicy",
            "id": "prefilter-eeee-eeee-eeee-eeeeeeeeeeee",
            "name": "prefilter-policy"
          }
        ],
        "paging": {
          "count": 1,
          "limit": 25,
          "offset": 0,
          "pages": 1
        }
      },
      "prefilterrules": {
        "items": [
          {
            "type": "PreFilterRule",
            "id": "prerule-1111-1111-1111-111111111111",
            "name": "prefilter-fastpath",
            "action": "FASTPATH",
            "sourceZones": {
              "objects": [
                {
                  "type": "SecurityZone",
                  "id": "zone-1111-1111-1111-111111111111",
                  "name": "inside-zone"
                }
              ]
            },
            "destinationZones": {
              "objects": [
                {
                  "type": "SecurityZone",
                  "id": "zone-2222-2222-2222-222222222222",
                  "name": "outside-zone"
                }
              ]
            }
          }
        ],
        "paging": {
          "count": 1,
          "limit": 25,
          "offset": 0,
          "pages": 1
        }
      },
      "accessrules": {
        "items": [
          {
            "type": "AccessRule",
            "id": "rule-2222-2222-2222-222222222222",
            "name": "monitor-logging",
            "action": "MONITOR",
            "enabled": true,
            "section": "default",
            "category": "Default",
            "sourceZones": {
              "objects": []
            },
            "destinationZones": {
              "objects": []
            },
            "logEnd": true
          },
          {
            "type": "AccessRule",
            "id": "rule-3333-3333-3333-333333333333",
            "name": "literal-address",
            "action": "ALLOW",
            "enabled": true,
            "section": "default",
            "category": "Default",
            "sourceZones": {
              "objects": []
            },
            "destinationZones": {
              "objects": []
            },
            "destinationNetworks": {
              "objects": [],
              "literals": [
                {
                  "type": "Host",
                  "value": "198.51.100.1"
                }
              ]
            },
            "logEnd": false
          },
          {
            "type": "AccessRule",
            "id": "rule-4444-4444-4444-444444444444",
            "name": "unresolved-ref",
            "action": "ALLOW",
            "enabled": true,
            "section": "default",
            "category": "Default",
            "sourceZones": {
              "objects": []
            },
            "destinationZones": {
              "objects": []
            },
            "sourceNetworks": {
              "objects": [
                {
                  "type": "Network",
                  "id": "net-9999-9999-9999-999999999999",
                  "name": "missing-object"
                }
              ]
            },
            "logEnd": false
          },
          {
            "type": "AccessRule",
            "id": "rule-1111-1111-1111-111111111111",
            "name": "mandatory-allow",
            "action": "ALLOW",
            "enabled": true,
            "section": "mandatory",
            "category": "Mandatory",
            "sourceZones": {
              "objects": [
                {
                  "type": "SecurityZone",
                  "id": "zone-1111-1111-1111-111111111111",
                  "name": "inside-zone"
                }
              ]
            },
            "destinationZones": {
              "objects": [
                {
                  "type": "SecurityZone",
                  "id": "zone-2222-2222-2222-222222222222",
                  "name": "outside-zone"
                }
              ]
            },
            "sourceNetworks": {
              "objects": [
                {
                  "type": "NetworkGroup",
                  "id": "netg-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                  "name": "trusted-nets"
                }
              ]
            },
            "destinationNetworks": {
              "objects": []
            },
            "destinationPorts": {
              "objects": [
                {
                  "type": "ProtocolPortObject",
                  "id": "port-cccc-cccc-cccc-cccccccccccc",
                  "name": "custom-port"
                }
              ]
            },
            "logEnd": true
          }
        ],
        "paging": {
          "count": 4,
          "limit": 25,
          "offset": 0,
          "pages": 1
        }
      }
    }
  }
}
```

## Coverage

This fixture exercises:

- **Two security zones**: `inside-zone`, `outside-zone`
- **One network object**: `server-net` (192.0.2.0/24)
- **One network group**: `trusted-nets` containing `server-net`
- **One port object**: `custom-port` (TCP/8080)
- **Access control policy** with:
  - Default rule with MONITOR action: `monitor-logging`
  - Default rule with literal address: `literal-address`
  - Default rule with unresolved reference: `unresolved-ref`
  - Mandatory rule: `mandatory-allow`
  - Default action: BLOCK
  - **Note**: Rules are presented out of evaluation order to test parser sorting
- **Prefilter policy** with one FASTPATH rule
- **Truncated paging**: `protocolportobjects` reports `count: 5` but provides only 1 item
- **Unresolved reference**: rule `unresolved-ref` references `net-9999-9999-9999-999999999999` which does not exist
- **Literal address**: rule `literal-address` has a `literals` entry for `198.51.100.1`

All addresses use RFC 5737 documentation ranges (192.0.2.0/24, 198.51.100.0/24, 203.0.113.0/24).

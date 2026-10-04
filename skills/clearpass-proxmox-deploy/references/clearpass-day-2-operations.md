# ClearPass day-2 operations — certificates, licensing, and the API

## Contents

- [Licensing](#licensing)
- [HTTPS certificate import](#https-certificate-import)
- [The REST API — access works, token minting does not](#the-rest-api--access-works-token-minting-does-not)
- [Driving the GUI headlessly](#driving-the-gui-headlessly)

Everything here was confirmed on a live **6.14.0.371380 / C1000V** appliance on
2026-08-15 and 2026-08-16, after the deploy procedure in `SKILL.md` completed.
The deploy skill ends at a booted, addressed appliance; this file covers what
comes next and where each step misleads you.

## Licensing

**Order is mandatory and the error does not say so.** A brand-new appliance
presents the **ClearPass Platform Activation Key** screen. Pasting an
`-----BEGIN ACCESS LICENSE KEY-----` block there returns a bare
`invalid license key` — because it is the wrong *type*, not because the key is
malformed. Install Platform first, then Access/Onboard/OnGuard at
*Administration → Server Manager → Licensing → Add License*.

**Two artifact shapes exist and only one looks broken.** The portal issues:

| Shape | Looks like | Notes |
|---|---|---|
| PEM-armored | `-----BEGIN CLEARPASS PLATFORM LICENSE KEY-----`, 76-col base64, ~712 chars → 532-byte payload | paste the whole block including BEGIN/END |
| bare activation key | 285 alphanumeric chars, no armor | emailed copies arrive wrapped at 63 cols with CRLF and padding spaces — **strip all whitespace before pasting** |

A licence that "does not work" is usually the bare form with email damage, or the
right key on the wrong screen. Validate before blaming the key: strip the armor,
`base64 -d`, and confirm it decodes to 532 bytes. If it decodes, the key is
intact and the problem is order or formatting.

**The Guest module needs a licence.** *Administration → API Services* lives in
ClearPass Guest, which refuses to load with
`A valid Access, Entry or Onboard license is required`. Platform alone is not
enough — this blocks all API work until an Access licence is installed.

## HTTPS certificate import

**The issuing root MUST be in the Trust List — even for the appliance's own
server certificate.** Import otherwise fails with:

```
Certificate CA "CN=<root>" with appropriate Subject Key Identifier
must be added and enabled in Certificate Trust List
```

This is counter-intuitive: a server does not normally need to trust its own
issuer. ClearPass validates the chain on import. The stock Aruba trust list
(37 CAs) contains no ISRG/Let's Encrypt entry.

**Upload CAs as `.crt`, never `.pem`.** Chromium types `.pem` as
`application/pkcs7-mime`, which ClearPass rejects outright with
`Content-type "application/pkcs7-mime" is not supported`. Same bytes, different
extension, different outcome.

**Trust List → Add dialog:** the Usage listbox is populated by the
`--Select to Add--` dropdown's onchange. The adjacent button is **Remove** —
clicking it undoes the selection you just made.

**"Disable the ECC certificate first" is a no-op on 6.14.** The ECC HTTPS slot
ships disabled and RSA enabled. Most guides predate this.

**There is no success banner.** The web service restarts (~45 s) and the served
certificate changes silently. Verify on the wire, never in the UI:

```bash
openssl s_client -connect <cppm>:443 -servername <fqdn> -showcerts </dev/null
```

Build the PKCS#12 from **fullchain**, not the leaf: ClearPass serves the whole
chain it is given, and a leaf-only bundle validates in desktop browsers (which
cache intermediates) while failing on Android and `curl`. Prove it against a
clean trust store:

```bash
openssl s_client -connect <cppm>:443 -servername <fqdn> -CAfile <root>.pem -verify_return_error
```

Import path: *Certificate Store* → certType `Server Certificate` →
`#uploadCert_service` = HTTPS(RSA) → `#upload_method` = PKCS#12 → `#pkcs12File`
+ `#passphrase` → `#btn_import_submit`.

## The REST API — access works, token minting does not

Tested three ways on 6.14, because the obvious conclusion is wrong in both
directions.

**The OAuth client secret is never displayed.** Not on the create form, not on
the edit page (`Encrypted, not shown`), and not after ticking *Generate a new
client secret* — each simply returns to the client list. Consequently
`POST /api/oauth` with `grant_type=client_credentials` always returns
`invalid_client / client credentials are required`, even with the
`client_public` flag set; `grant_type=password` with the Policy Manager admin
returns `invalid_grant`.

**But the API itself is fully usable.** The API Clients row action
**Generate Access Token** mints a bearer token *and displays it*, with a ready
curl example:

```bash
curl -H "Authorization: Bearer <token>" https://<cppm>/api/api-client   # 200
```

`access_token_lifetime` is an editable field (default 8 hours), so a minted
token can be given a long life for an integration.

**Practical consequence:** any client that wants `client_id` + `client_secret`
cannot authenticate against 6.14. One that accepts a pre-minted bearer token
can. Check which before designing around it — "the API is unusable" is the wrong
conclusion, and so is assuming a secret can be retrieved.

## Driving the GUI headlessly

The appliance's self-signed certificate stops headless Chromium, and
ClearPass's Guest module 302s to an **absolute** `https://` URL, escaping any
local bridge. Front the appliance with a plain-HTTP terminator:

```bash
socat TCP-LISTEN:9080,fork,reuseaddr,bind=127.0.0.1 \
      OPENSSL:<cppm-ip>:443,verify=0,snihost=<fqdn>
```

then browse `http://127.0.0.1:9080/tips/`. Once a trusted certificate is
installed the bridge becomes unnecessary — which is a good reason to do the
certificate first.

Login fields are `#username` and `#pw`. The page carries **four decoy hidden
password inputs**, so a generic `input[type=password]` selector matches five
elements and fails.

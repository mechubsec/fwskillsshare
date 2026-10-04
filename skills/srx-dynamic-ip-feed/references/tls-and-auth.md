# TLS Validation and Authentication

## Contents

- [Production Pattern: Validate the Feed Server Certificate](#production-pattern-validate-the-feed-server-certificate)
- [Optional: HTTP Basic Authentication](#optional-http-basic-authentication)
- [Optional: Mutual TLS Client Certificate Authentication](#optional-mutual-tls-client-certificate-authentication)

This reference covers production TLS certificate validation, HTTP Basic Authentication, and mutual TLS client certificate authentication for SRX dynamic IP feed servers.

## Production Pattern: Validate the Feed Server Certificate

Production feed servers should use a certificate issued by a CA trusted by the SRX, and the SRX should validate that the certificate identity matches the URL hostname.

### Server Side

Generate or obtain:

- CA certificate, e.g. `IPFD_CA`
- server certificate/key for the feed server hostname, e.g. `debian-2`

Install the server cert/key and CA certificate for nginx:

```bash
cp CA/cacert.pem /etc/ssl/certs/IPFD_CA.pem
cp CA/debian-2-cert.pem /etc/ssl/certs/
cp CA/debian-2-key.pem /etc/ssl/private/
chmod 600 /etc/ssl/private/debian-2-key.pem
```

Configure nginx SSL snippet, e.g. `/etc/nginx/snippets/IPFD.conf`:

```nginx
ssl_certificate /etc/ssl/certs/debian-2-cert.pem;
ssl_certificate_key /etc/ssl/private/debian-2-key.pem;
```

Enable it in the site:

```nginx
listen 443 ssl default_server;
listen [::]:443 ssl default_server;
include snippets/IPFD.conf;
```

Restart:

```bash
systemctl restart nginx
openssl s_client -connect localhost:443
```

Create the production archive:

```bash
cd /var/www/html
mkdir feed-2
printf '10.1.1.1\n' > feed-2/whitelist-2
printf '10.2.2.2\n' > feed-2/blacklist-2
tar czf feed-2.tgz feed-2/
tail -f -n0 /var/log/nginx/access.log
```

### SRX Side

Configure and load the CA profile:

```junos
set security pki ca-profile IPFD_CA ca-identity IPFD_CA revocation-check disable
```

Then load the CA certificate after uploading it to the SRX:

```text
request security pki ca-certificate load ca-profile IPFD_CA filename cacert.pem
request security pki ca-certificate verify ca-profile IPFD_CA
```

Configure hostname resolution if DNS is not available:

```junos
set system static-host-mapping debian-2 inet 10.0.1.10
```

Configure the SSL initiation profile and feed server:

```junos
set services ssl initiation profile srx-1_IPFD_CA trusted-ca IPFD_CA
set security dynamic-address feed-server debian-2 url https://debian-2/feed-2.tgz
set security dynamic-address feed-server debian-2 update-interval 60
set security dynamic-address feed-server debian-2 hold-interval 86400
set security dynamic-address feed-server debian-2 tls-profile srx-1_IPFD_CA
set security dynamic-address feed-server debian-2 validate-certificate-attributes subject-or-subject-alternative-names
set security dynamic-address feed-server debian-2 feed-name whitelist-2 path feed-2/whitelist-2
set security dynamic-address feed-server debian-2 feed-name blacklist-2 path feed-2/blacklist-2
set security dynamic-address address-name whitelist-2 profile feed-name whitelist-2
set security dynamic-address address-name blacklist-2 profile feed-name blacklist-2
```

Important: with `validate-certificate-attributes subject-or-subject-alternative-names`, the hostname in the URL must match the server certificate CN or SAN. A URL like `https://debian-3/feed-2.tgz` against a certificate for `debian-2` should fail.

## Optional: HTTP Basic Authentication

Requires Junos 25.2R1 or later for SRX client username/password feed authentication.

On nginx, enable basic auth for the relevant location:

```nginx
location / {
    auth_basic "Restricted Area";
    auth_basic_user_file /etc/nginx/htpasswd;
    # existing content serving configuration
}
```

Create credentials:

```bash
apt install apache2-utils
htpasswd -c -b /etc/nginx/htpasswd srx <feed-basic-auth-password>
systemctl restart nginx
```

Before SRX credentials are configured, expect HTTP 401 errors in `ipfd` logs:

```text
failed<http return error code 401>
```

Add credentials to the SRX feed server:

```junos
set security dynamic-address feed-server debian-2 user-name srx
set security dynamic-address feed-server debian-2 password <feed-basic-auth-password>
```

Use a secure password management workflow for production. Avoid leaving cleartext credentials in tickets, chat, or documentation.

## Optional: Mutual TLS Client Certificate Authentication

Use mutual TLS when the feed server should only serve feed archives to authenticated SRX clients.

On nginx, configure a trusted client CA and enforce client certificate success inside a location:

```nginx
ssl_client_certificate /etc/ssl/certs/IPFD_CA.pem;
ssl_verify_client optional;

location / {
    if ($ssl_client_verify != SUCCESS) {
        return 403;
    }
    # existing content serving configuration
}
```

Without the SRX client cert, expect HTTP 403 errors in `ipfd` logs:

```text
failed<http return error code 403>
```

Upload the SRX client certificate and key to SRX, then load and verify:

```text
request security pki local-certificate load certificate-id srx-1_IPFD_CA filename srx-1-cert.pem key srx-1-key.pem
request security pki local-certificate verify certificate-id srx-1_IPFD_CA
```

Reference the client certificate from the SSL initiation profile:

```junos
set services ssl initiation profile srx-1_IPFD_CA client-certificate srx-1_IPFD_CA
```

After commit, successful downloads should resume.

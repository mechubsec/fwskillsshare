# Stage 1 — Access and Recovery

This stage establishes authenticated access to the device and confirms out-of-band recovery capability before any lockout-risk configuration is applied.

## What this stage establishes

- **Root authentication:** The root (superuser) account is protected by an encrypted password or SSH key. Junos OS rejects commits until root authentication is configured.
- **Named administrative user:** At least one non-root login account with a login class that grants configuration privileges. The root account is used for recovery and initial setup; day-to-day administration should use named accounts for accountability.
- **Management services:** SSH and NETCONF access enabled on the management interface or trusted zone, allowing remote configuration and automation.
- **Out-of-band access confirmation:** The operator has confirmed console access or an alternative recovery path, so that if a later lockout-risk change fails, the device can be reached.

## Gaps

### `access.root-auth-absent`

- **Stage:** access-and-recovery
- **Severity:** `blocking`
- **Depends on:** None
- **Lockout risk:** `false` (setting root auth does not remove an existing path; it creates the initial one)
- **Evidence:** `show configuration system root-authentication` returns no configured password or SSH key
- **Proposal:**

  ```text
  set system root-authentication encrypted-password "$6$EXAMPLE_HASH"
  ```

  Or, for SSH key-based authentication:

  ```text
  set system root-authentication ssh-rsa "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQ..."
  ```

  The operator must supply the actual encrypted password hash or SSH public key. Junos OS requires root authentication to be configured before it accepts a commit operation.

  **Source:** Juniper Networks, "Root Password" (Junos OS User Access and Authentication), retrieved 2026-08-20.
  URL: https://www.juniper.net/documentation/us/en/software/junos/user-access/topics/topic-map/user-access-root-password.html

  The documentation states: "You must configure a plain-text password for the root-level user (whose username is _root_) the first time you modify and commit the configuration."

  **Additional source:** Juniper Networks, "root-authentication" (Junos OS CLI Reference), retrieved 2026-08-20.
  URL: https://www.juniper.net/documentation/us/en/software/junos/cli-reference/topics/ref/statement/root-authentication-edit-system.html

### `access.no-named-admin`

- **Stage:** access-and-recovery
- **Severity:** `blocking`
- **Depends on:** `access.root-auth-absent`
- **Lockout risk:** `false`
- **Evidence:** `show configuration system login` reports only the root user, or no users with a login class that grants configuration permissions
- **Proposal:**

  ```text
  set system login user admin class super-user authentication encrypted-password "$6$EXAMPLE_HASH"
  ```

  Or, for SSH key-based authentication:

  ```text
  set system login user admin class super-user authentication ssh-rsa "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQ..."
  ```

  Replace `admin` with the desired username and supply the actual encrypted password hash or SSH public key. The `super-user` class grants full configuration privileges equivalent to root.

  For a more restrictive role, use `operator` (read-only access plus operational commands) or define a custom login class with specific permissions.

  **Source:** Juniper Networks, "Login Classes Overview" (Junos OS User Access and Authentication), retrieved 2026-08-20.
  URL: https://www.juniper.net/documentation/us/en/software/junos/user-access/topics/topic-map/junos-os-login-class-overview.html

  The documentation states: "Login classes define the access privileges, permissions for using CLI commands and statements, and session idle time for the users assigned to that class. All users who can log in to a device running Junos OS must be in a login class."

  **Additional source:** Juniper Networks, "User Accounts" (Junos OS User Access and Authentication), retrieved 2026-08-20.
  URL: https://www.juniper.net/documentation/us/en/software/junos/user-access/topics/topic-map/junos-os-user-accounts.html

  The documentation states: "For each account, you (the system administrator) define a login name and password for the user and specify a login class for access privileges."

### `access.ssh-disabled`

- **Stage:** access-and-recovery
- **Severity:** `blocking`
- **Depends on:** `access.root-auth-absent`, `access.no-named-admin`
- **Lockout risk:** `false` (enabling SSH does not disable an existing path; if SSH is the only enabled service, removing it later is a lockout-risk change)
- **Evidence:** `show configuration system services` does not report SSH service enabled
- **Proposal:**

  ```text
  set system services ssh
  ```

  This enables SSH on the default port (22). For non-default port configuration:

  ```text
  set system services ssh port 2222
  ```

  Optional and redundant on supported releases: `set system services ssh protocol-version v2`.
  Juniper's `protocol-version` reference states v2 is the default (introduced in
  Junos 11.4) and that SSH v1 was removed on all SRX devices in 19.3R1 and
  18.3R3, so the line changes nothing there. Do not count it as a hardening
  control or a gap. Reference (HTTP 200, checked 2026-10-09):
  https://www.juniper.net/documentation/en_US/junos/topics/reference/configuration-statement/protocol-version-edit-system.html

  **Source:** Juniper Networks, "Remote Access Overview" (Junos OS User Access and Authentication), retrieved 2026-08-20.
  URL: https://www.juniper.net/documentation/us/en/software/junos/user-access/topics/topic-map/junos-software-remote-access-overview.html

### `access.netconf-disabled`

- **Stage:** access-and-recovery
- **Severity:** `advisory` (required for automation; not blocking if manual CLI access is sufficient)
- **Depends on:** `access.root-auth-absent`, `access.no-named-admin`
- **Lockout risk:** `false`
- **Evidence:** `show configuration system services` does not report NETCONF service enabled
- **Proposal:**

  ```text
  set system services netconf ssh
  ```

  This enables NETCONF over SSH on the default port (830). To use a non-default port:

  ```text
  set system services netconf ssh port 8300
  ```

  **Note:** The configured NETCONF port accepts only NETCONF-over-SSH sessions and rejects regular SSH session requests. If you enable both SSH and NETCONF services, the device accepts NETCONF sessions on both the SSH port (22 or configured) and the NETCONF port (830 or configured).

  **Source:** Juniper Networks, "Establish an SSH Connection for a NETCONF Session" (Junos OS NETCONF XML Management Protocol), retrieved 2026-08-20.
  URL: https://www.juniper.net/documentation/us/en/software/junos/netconf/topics/topic-map/netconf-ssh-connection.html

  **Additional source:** Juniper Networks, "ssh (NETCONF)" (Junos OS CLI Reference), retrieved 2026-08-20.
  URL: https://www.juniper.net/documentation/us/en/software/junos/cli-reference/topics/ref/statement/ssh-edit-system-services-netconf.html

  The documentation states: "To enable NETCONF service over SSH on a Junos device, you must enable the NETCONF service on either the default NETCONF port (830) or a user-defined port."

## Out-of-band path

This stage must complete before any later stage that carries `lockout_risk: true`.

**Why:** A lockout-risk change is one that can sever the management session currently in use — for example, removing factory-default management services from the untrust zone, restructuring VLANs that carry the operator's address, or replacing a DHCP-assigned WAN interface with a static configuration that may be incorrect.

If such a change fails and automatic rollback does not restore connectivity (e.g., the timer expired before rollback, or the rollback itself has a bug, or the operator's network path changed during the window), the only recovery is out-of-band access: console, lights-out management, or physical access to the device.

**The protocol in `write-safety.md` mandates confirming out-of-band access before proceeding with any lockout-risk change.** This confirmation happens via the `sis_console` intake question. If the operator has not confirmed console or equivalent recovery access, the skill asks and waits for confirmation before proposing the lockout-risk stage.

**Recovery paths:**

1. **Console access:** Serial console cable, terminal server, or KVM. Works regardless of network state.
2. **Out-of-band management network:** Dedicated management interface (e.g., fxp0 on platforms that have it) on a separate network from the data plane. If the data-plane configuration is broken, the management interface may still be reachable.
3. **Lights-out management:** Platform-dependent; not universally available on SRX Branch devices. Examples: iLO, iDRAC, or equivalent vendor-specific management controllers.

If none of these are available or confirmed, **do not proceed with lockout-risk stages**. The device must be accessible for recovery before any change that can break access.

## Verification

After this stage closes, verify:

1. **Root authentication works:**

   ```text
   ssh root@<device-address>
   ```

   Or test the configured SSH key. Expect successful authentication.

2. **Named administrative user works:**

   ```text
   ssh admin@<device-address>
   ```

   Authenticate with the configured password or SSH key. Once logged in, verify configuration privileges:

   ```text
   configure
   show configuration
   ```

   Expect to enter configuration mode and view the configuration.

3. **NETCONF access works (if enabled):**

   From a client with a NETCONF library:

   ```python
   from ncclient import manager
   with manager.connect(host='<device-address>', port=830, username='admin', password='<password>', hostkey_verify=False) as m:
       print(m.connected)
   ```

   Expect `True` (connection established).

4. **Out-of-band access confirmed:**

   The operator has answered `sis_console` affirmatively, or the skill has obtained explicit confirmation via another path. This is not a command to run; it is a gate condition.

All `access.*` gaps are now closed. Later stages may proceed.

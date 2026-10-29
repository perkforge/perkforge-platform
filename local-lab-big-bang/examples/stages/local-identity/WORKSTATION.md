# Workstation names and CA trust

Operator steps for the **local** trial only; not executed by the Ansible foundation.
Do not send a sudo password in chat. The application stage can remain paused while
preparing trust; a trusted certificate does not mean the backend is ready.

## Names

Back up `/etc/hosts`, then edit it locally with your own sudo authentication:

```sh
sudo cp -a /etc/hosts "/etc/hosts.perkforge-identity.$(date -u +%Y%m%dT%H%M%SZ)"
sudoedit /etc/hosts
```

Add only this block, preserving existing entries:

```text
# PerkForge local identity trial
192.168.122.201 keycloak-local-il2.local-lab.test headlamp-local-il2.local-lab.test
```

`getent ahostsv4 keycloak-local-il2.local-lab.test` and the corresponding Headlamp
lookup should return `.201`. These are routing names, not Kubernetes permissions.

## Firefox (narrower than system-wide trust)

The public CA certificate is:
`/home/corey/src/perkforge-platform/.secrets/bigbang-local-trial-01/identity/tls/identity-ca.crt`.
Do **not** import or share any `.key` file. Verify the public certificate first:

```sh
openssl x509 -in /home/corey/src/perkforge-platform/.secrets/bigbang-local-trial-01/identity/tls/identity-ca.crt -noout -subject -dates -fingerprint -sha256
```

Match the SHA-256 fingerprint supplied separately by the operator for this run.
In Firefox: Settings → Privacy & Security → Certificates → View Certificates →
Authorities → Import. Choose that `.crt`, and enable website identification trust
only. Never bypass an HTTPS certificate warning. On Linux, do not assume system
CA installation automatically configures Firefox; verify its own trust explicitly.

This trusts **PerkForge Local Identity Trial CA** in that Firefox profile to issue
website certificates. The CA itself is not hostname-constrained; current leaves
cover only the two trial names. It does not grant API RBAC or trust the CA private
key to any service. Remove it after the trial under Authorities → select the exact
trial CA → Delete or Distrust. Other Firefox profiles are separate.

## Optional Debian system trust

Only if command-line/system clients also need this CA, install its public cert:

```sh
sudo install -m 0644 /home/corey/src/perkforge-platform/.secrets/bigbang-local-trial-01/identity/tls/identity-ca.crt /usr/local/share/ca-certificates/perkforge-local-identity.crt
sudo /usr/sbin/update-ca-certificates
```

This broadens trust for applications using Debian's system CA store; Firefox may
still require its profile import. To remove only this added system anchor:

```sh
sudo rm /usr/local/share/ca-certificates/perkforge-local-identity.crt
sudo /usr/sbin/update-ca-certificates
```

To undo name routing, remove only the added comment/mapping from `/etc/hosts`,
keeping other edits. Keep the original backup. No package installation is needed.
See [Mozilla's CA guidance](https://support.mozilla.org/en-US/kb/setting-certificate-authorities-firefox)
and the installed Debian `update-ca-certificates(8)` manual.

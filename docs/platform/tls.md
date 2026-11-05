# TLS ownership and production design

**Proposed production contract; not deployed controls or a government authorization claim.**
Use the same reviewed application artifacts across environments. Target/profile inputs
select DNS names, approved issuers, public trust bundles, certificate/Secret references,
transport requirements and renewal policy; never embed a lab CA or private signing key
in an application image. The current local physical lab is a separate trust profile.

## Who does what and why

| Owner | Responsibility and boundary |
|---|---|
| Organization/security authority | Approves external or organizational PKI, algorithms, lifetimes, identity/SAN policy and client trust distribution for each target/profile. Public trust is appropriate only for approved externally valid names; private names require managed organizational trust. |
| PKI operator / approved issuer | Protects signing keys outside application namespaces in approved key custody; authenticates issuance requests and renews/revokes certificates. No CA signing key is delivered to a workload, Git, viewer or generic credential cache. Issuer automation and delegation still require design and approval. |
| Platform operator and Ansible | Validates target, hostname, issuer chain, expiry and leaf/key match; delivers only approved leaf keys/certificates and public bundles through protected, explicitly scoped inputs. Existing platform TLS playbook is a lab delivery mechanism, not an implemented production issuer. |
| Flux / Big Bang application owners | Reconcile reviewed certificate references and transport configuration. Issuance/rotation ownership must be singular; do not let two reconcilers overwrite the same Secret. Workloads consume their own keys and public trust, not issuer signing authority. |
| Endpoint/device administrators | Distribute approved public roots/intermediates through managed OS/browser/device trust. A successful workstation probe does not prove another browser/device trusts the issuer. |
| Application and database owners | Configure server identity and client verification on each hop; support leaf/trust reload or a controlled restart and application acceptance. mTLS is a separate per-hop identity decision, not an assumed effect of HTTPS or NetworkPolicy. |

## Current lab behavior and verified gaps

The lab uses a private physical-cluster CA and per-host leaf certificates.
Keycloak browser HTTPS terminates at Traefik; its authored backend is HTTP
([package contract](../../big-bang-bootstrap/configuration/packages/keycloak/README.md)).
The approved initial Keycloak-to-PostgreSQL connection is also unencrypted; the two
Keycloak-specific NetworkPolicies restrict peers but do not encrypt traffic.
Headlamp likewise uses ingress TLS termination with an HTTP backend, as recorded in
the [transport runbook](../../big-bang-bootstrap/configuration/ansible/README.md).
OpenBao instead uses exact-SNI TLS passthrough to its TLS listener
([route values](../../big-bang-bootstrap/configuration/packages/openbao/values.yaml)).
Do not generalize this to all internal services, storage replication or databases:
those paths still need an explicit transport inventory and verification.

On 2026-11-02, Keycloak public TLS probing verified the issued physical leaf,
correct hostname/SAN and validity, with successful default workstation and explicit
lab-root verification. The tablet trust store itself was not independently inspected.
After installing the verified public lab root on the Pixel Tablet, the operator
reported that HTTPS worked. This is **user-reported tablet acceptance**, separate
from the workstation certificate checks; no automated tablet inspection occurred.

## Pixel Tablet: public lab root trust (short-term lab procedure)

1. Obtain `perkforge-home-lab-root-ca.crt` through the agreed delivery channel.
   Install only this public CA certificate, never a leaf private key, CA signing
   key, password or client identity bundle. Before trusting it, compare its
   **certificate SHA-256 fingerprint**, through a trusted channel, with:

   ```text
   D6:A5:96:0A:DA:A2:D0:CD:37:04:E8:C0:7B:DB:8D:EA:08:E1:31:90:1C:B9:C5:7F:45:85:1A:CD:57:F4:A4:2F
   ```

   The subject is `PerkForge Home Lab Root CA`. This fingerprint identifies the
   certificate's DER encoding, not the checksum of the downloaded PEM text file.
   If the tablet cannot show a fingerprint before installation, verify the file
   on a trusted workstation first and transfer that verified file securely.
2. Open **Settings → Security & privacy → More security settings → Encryption &
   credentials → Install a certificate → CA certificate**. Android releases may
   place this under **More security & privacy** or use slightly different labels;
   search Settings for “CA certificate” if necessary. Select the verified file
   and authenticate locally when prompted. The Android CA-installation consent
   warning is distinct from bypassing a website's TLS error; never proceed
   through a browser certificate-warning bypass.
3. Inspect **Encryption & credentials → Trusted credentials → User** for the
   expected lab CA and fingerprint. Restart Chrome and open the exact HTTPS URL:
   <https://keycloak.perkforge.home.arpa/auth/realms/perkforge/account/>.
   Verify the insecure-connection warning is gone; stop for a hostname, expiry
   or issuer mismatch. The operator reported success on 2026-11-02.
4. To retire this trust later, open **Trusted credentials → User**, select only
   this lab CA, and remove/disable it using the available control. Some versions
   offer individual removal under **User credentials**. Do not clear all
   credentials or remove unrelated authorities. Recheck the intended trust state
   afterward; lab services will need another approved trust path if still used.

Trusting a CA permits accepting certificates it signs for names beyond this one
website in clients that honor that user trust store. It is not a one-host
exception, and some apps use different trust policies. Protect the signing key;
remove temporary lab trust when no longer needed. This manual procedure is not
managed production trust distribution, proof of internal encryption or a
government-PaaS authorization. Production requires the ownership/lifecycle below.

[Google's Pixel certificate settings guidance](https://support.google.com/pixelphone/answer/2844832?hl=en)
covers the common credential-settings area; its Wi-Fi certificate example is
not the CA-certificate option used here.

## Production acceptance and lifecycle

1. Inventory client → ingress, ingress → service, service → service/database,
   administrative, telemetry and storage transports. Record termination, identities,
   encryption and peer-verification evidence for each; close or explicitly approve
   gaps before selecting a production profile. Internal Keycloak/Headlamp HTTP and
   Keycloak database plaintext remain open gaps, not implicitly accepted production defaults.
2. Supply approved issuer/trust references independently from build artifacts.
   Validate SAN/hostname, chain, validity, server/client EKU and key match. Require
   supported encrypted database/client configurations with peer identity verification;
   certificate encryption without hostname/CA checks is insufficient.
3. Assign issuance/renewal ownership, least-privilege Secret access, protected backup
   and key custody. Prove application reload/restart behavior and safe certificate
   rotation; stage overlapping old/new public trust during issuer rollover before
   retiring old trust. Do not distribute private signing keys to clients.
4. Monitor expiry, failed renewal, served certificate identity and trust-bundle drift
   with actionable alerts and an owner. Define revocation/compromise response,
   emergency replacement and old-key retirement; verify actual client revocation
   behavior rather than assuming all clients enforce CRL/OCSP.
5. Test intended browsers/devices and machine clients, every internal TLS hop and
   application health. Include wrong-host, untrusted/expired certificate and missing
   intermediate rejection, rotation under load and recovery from renewal failure.
   Save sanitized results; never save passwords, bearer tokens or leaf/private keys
   in test output. Existing lab login/readiness tests do not establish these controls.

No Istio/Gateway API implementation, trust installation or live certificate change
is part of this document. IL2/IL5 policy inputs require organizational review;
future CAC and government-PaaS requirements are design intent, not compliance evidence.

## Implementation references

- [Existing Ansible TLS delivery](../../big-bang-bootstrap/configuration/ansible/platform-tls.yaml), separate from production issuance design.
- [Keycloak TLS configuration](https://www.keycloak.org/server/enabletls): upstream certificate/key inputs and reload support; validate against the selected version before implementation.
- [Kubernetes NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/): connectivity policy; encryption and certificate management are separate controls.

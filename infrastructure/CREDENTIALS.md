# Operator credential handling

Keep passwords, private SSH keys, tokens and recovery material outside tracked
configuration and generated PXE working files. Use protected workstation storage
and independent encrypted backups with a tested restore procedure. No new
credential, rotation, registration or backup operation is authorized by this guide.

- **Node access:** retain the existing passphrase-protected key in `~/.ssh`; inputs
  contain only its path/public reference. Use bounded agent unlocking and compare
  complete host fingerprints physically before pinning trust. Require fresh key-only
  SSH and password-authenticated sudo; retain console access until verified.
- **RHEL entitlement:** enter account/activation credentials locally through the
  approved registration flow. Do not place passwords in command arguments or repos.
- **RKE2 agents:** the installer requires an explicit protected0600 agent-only token
  file. Never supply the server token to workers. See [RKE2 inputs](ansible/RKE2.md).
- **RKE2 recovery:** protect the server token with its matching etcd snapshot and
  cluster identity. Do not delete them on the assumption a local folder can rebuild
  past cluster state. Admin kubeconfig remains protected, never in `~/.kube/config`
  implicitly or in Git.
- **Platform credentials:** keep Rancher break-glass/OIDC, registry and later
  secret-service recovery material in independent protected custody. The cluster's
  own secret store must not be its only recovery path.

Installation creates cluster credentials; export complete server/agent tokens only
through the separately approved protected export procedure. Keep tokens and any
credential ZIP ignored and mode0600. A ZIP is not encrypted and is not an etcd
backup. Independent custody and restore testing remain separate requirements. Removing an obsolete local
file does not revoke credentials on a node or at an issuer; that is a separate
security operation.

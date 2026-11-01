// Copy an explicit allowlist of nonsecret documentation into the local viewer.
// Never recursively copy the repository, inventories, evidence or credential dirs.
import { copyFile, mkdir } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
const here = path.dirname(fileURLToPath(import.meta.url))
const root = path.resolve(here, '../../..')
const output = process.argv[2] ? path.resolve(process.argv[2]) : path.resolve(here, '../public/sources')
const files = {
  'realm-foundation.yaml': 'big-bang-bootstrap/configuration/authorization/foundation.yaml',
  'test-realm-foundation.py': 'big-bang-bootstrap/tests/integration/test_realm_foundation.py',
  'realm-foundation-inspect.yaml': 'big-bang-bootstrap/configuration/authorization/tasks/foundation-inspect.yaml',
  'realm-foundation-create.yaml': 'big-bang-bootstrap/configuration/authorization/tasks/foundation-create.yaml',
  'realm-foundation-tenant.yaml': 'big-bang-bootstrap/configuration/authorization/tasks/foundation-tenant.yaml',
  'headlamp-access-smoke.yaml': 'big-bang-bootstrap/configuration/ansible/headlamp-access-smoke.yaml',
  'headlamp-access-cleanup.yaml': 'big-bang-bootstrap/configuration/ansible/headlamp-access-cleanup.yaml',
  'verify-headlamp-access.py': 'big-bang-bootstrap/configuration/ansible/files/verify-headlamp-access.py',
  'openbao-initialize.yaml': 'big-bang-bootstrap/configuration/ansible/openbao-initialize.yaml',
  'longhorn-storage-smoke.yaml': 'big-bang-bootstrap/configuration/ansible/longhorn-storage-smoke.yaml',
  'longhorn-smoke-stage.yaml': 'big-bang-bootstrap/configuration/ansible/longhorn-smoke-stage.yaml',
  'verify-longhorn-smoke.py': 'big-bang-bootstrap/configuration/ansible/files/verify-longhorn-smoke.py',
  'longhorn-smoke-pod.yaml.j2': 'big-bang-bootstrap/configuration/ansible/fixtures/longhorn-smoke-pod.yaml.j2',
  'longhorn-smoke-foundation.yaml.j2': 'big-bang-bootstrap/configuration/ansible/fixtures/longhorn-smoke-foundation.yaml.j2',
  'workload-smoke.yml': 'infrastructure/ansible/tests/workload-smoke.yml',
  'workload-smoke.yaml': 'infrastructure/ansible/tests/fixtures/workload-smoke.yaml',
  'prepare.yml': 'pxe/transport/prepare.yml',
  'inputs.example.yml': 'pxe/transport/inputs.example.yml',
  'activate.yml': 'pxe/transport/activate.yml',
  'activation-placement.yml': 'pxe/transport/activation-placement.yml',
  'verify-activation-copies.yml': 'pxe/transport/verify-activation-copies.yml',
  'verify-session-identity.yml': 'pxe/transport/verify-session-identity.yml',
  'shutdown.yml': 'pxe/transport/shutdown.yml',
  'shutdown-tasks.yml': 'pxe/transport/shutdown-tasks.yml',
  'dnsmasq.conf.j2': 'pxe/transport/templates/dnsmasq.conf.j2',
  'grub.cfg.j2': 'pxe/transport/templates/grub.cfg.j2',
  'nginx.conf.j2': 'pxe/transport/templates/nginx.conf.j2',
  'ingress.nft.j2': 'pxe/transport/templates/ingress.nft.j2',
  'stage-media.sh': 'pxe/transport/stage-media.sh',
  'harden-ssh.sh': 'pxe/transport/harden-ssh.sh',
  'access.sh': 'pxe/transport/access.sh',
  'workspace.yml': 'pxe/transport/workspace.yml',
  'workspace.inputs.example.yml': 'pxe/transport/workspace.inputs.example.yml',
  'provisioning.md': 'pxe/README.md',
  'preserve-session.yml': 'pxe/transport/preserve-session.yml',
  'workspace-session.sh.j2': 'pxe/transport/templates/workspace/session.sh.j2',
  'workspace-inputs.yml.j2': 'pxe/transport/templates/workspace/inputs.yml.j2',
  'workspace-manifest.yml.j2': 'pxe/transport/templates/workspace/activation-review.yml.j2',
  'workspace-readme.md.j2': 'pxe/transport/templates/workspace/README.md.j2'
}
await mkdir(output, { recursive: true })
for (const [name, source] of Object.entries(files)) {
  await copyFile(path.join(root, source), path.join(output, name))
}
console.log(`Prepared ${Object.keys(files).length} allowlisted public source links.`)

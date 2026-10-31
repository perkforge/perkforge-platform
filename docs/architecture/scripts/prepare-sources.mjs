// Copy an explicit allowlist of nonsecret documentation into the local viewer.
// Never recursively copy the repository, inventories, evidence or credential dirs.
import { copyFile, mkdir } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
const here = path.dirname(fileURLToPath(import.meta.url))
const root = path.resolve(here, '../../..')
const output = process.argv[2] ? path.resolve(process.argv[2]) : path.resolve(here, '../public/sources')
const files = {
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

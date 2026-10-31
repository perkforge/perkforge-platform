// Copy an explicit allowlist of nonsecret documentation into the local viewer.
// Never recursively copy the repository, inventories, evidence or credential dirs.
import { copyFile, mkdir } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
const here = path.dirname(fileURLToPath(import.meta.url))
const root = path.resolve(here, '../../..')
const output = path.resolve(here, '../public/sources')
const files = {
  'prepare.yml': 'pxe/pilot/prepare.yml',
  'inputs.example.yml': 'pxe/pilot/inputs.example.yml',
  'activate.yml': 'pxe/pilot/activate.yml',
  'activation-placement.yml': 'pxe/pilot/activation-placement.yml',
  'verify-activation-copies.yml': 'pxe/pilot/verify-activation-copies.yml',
  'verify-pilot-identity.yml': 'pxe/pilot/verify-pilot-identity.yml',
  'shutdown.yml': 'pxe/pilot/shutdown.yml',
  'shutdown-tasks.yml': 'pxe/pilot/shutdown-tasks.yml',
  'dnsmasq.conf.j2': 'pxe/pilot/templates/dnsmasq.conf.j2',
  'grub.cfg.j2': 'pxe/pilot/templates/grub.cfg.j2',
  'nginx.conf.j2': 'pxe/pilot/templates/nginx.conf.j2',
  'ingress.nft.j2': 'pxe/pilot/templates/ingress.nft.j2',
  'stage-media.sh': 'pxe/pilot/stage-media.sh',
  'harden-ssh.sh': 'pxe/pilot/history/console/harden-ssh.sh'
}
await mkdir(output, { recursive: true })
for (const [name, source] of Object.entries(files)) {
  await copyFile(path.join(root, source), path.join(output, name))
}
console.log(`Prepared ${Object.keys(files).length} allowlisted public source links.`)

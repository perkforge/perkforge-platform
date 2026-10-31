// Copy an explicit allowlist of nonsecret documentation into the local viewer.
// Never recursively copy the repository, inventories, evidence or credential dirs.
import { copyFile, mkdir } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
const here = path.dirname(fileURLToPath(import.meta.url))
const root = path.resolve(here, '../../..')
const output = path.resolve(here, '../public/sources')
const files = {
  'prepare.yml': 'pxe/ansible/prepare.yml',
  'preparation.md': 'pxe/ansible/README.md',
  'rhel10.ks.j2': 'pxe/kickstart/rhel10.ks.j2',
  'redesign.md': 'infrastructure/PROVISIONING-REDESIGN.md',
  'readiness.md': 'infrastructure/TOMORROW-READINESS.md',
  'vendor-guidance.md': 'infrastructure/RHEL-PROVISIONING-GUIDANCE.md',
  'handoff.md': 'pxe/pilot/HANDOFF.md'
}
await mkdir(output, { recursive: true })
for (const [name, source] of Object.entries(files)) {
  await copyFile(path.join(root, source), path.join(output, name))
}
console.log(`Prepared ${Object.keys(files).length} allowlisted public source links.`)

// Separate source roots, no shared public directory and no deployment operation.
import { rmSync } from 'node:fs'
import { execFileSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const command = process.argv[2]
if (!['validate', 'build'].includes(command)) throw new Error('Use validate or build')
const cli = path.join(root, 'node_modules/.bin/likec4')
for (const audience of ['tenant', 'security']) {
  const source = path.resolve(root, `../${audience}-architecture`)
  const args = [command, source]
  if (command === 'build') {
    const output = path.join(root, `dist-${audience}`)
    // Only these fixed, ignored build outputs are disposable; never retain stale assets.
    rmSync(output, { recursive: true, force: true })
    args.push('-o', output, '--base', './', '--use-hash-history')
  }
  execFileSync(cli, args, { cwd: source, stdio: 'inherit' })
}

// VitePress builds pages from docs/, which lives outside site/ (the npm root).
// Node resolves dependencies by walking up from the importing file, so a page
// under docs/ would not see site/node_modules. This script keeps a relative
// symlink docs/node_modules -> ../site/node_modules in place, created before
// every dev/build/preview run. It is a link, not a copy: nothing is duplicated.
import { existsSync, lstatSync, mkdirSync, readlinkSync, symlinkSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const siteDir = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const linkPath = join(siteDir, '..', 'docs', 'node_modules')
const expectedTarget = '../site/node_modules'

if (existsSync(linkPath)) {
  const current = lstatSync(linkPath)
  if (current.isSymbolicLink() && readlinkSync(linkPath) === expectedTarget) {
    process.exit(0)
  }
  throw new Error(
    `${linkPath} exists and is not the expected ${expectedTarget} symlink; remove it and rerun`
  )
}

mkdirSync(dirname(linkPath), { recursive: true })
symlinkSync(expectedTarget, linkPath, 'dir')
console.log(`created ${linkPath} -> ${expectedTarget}`)

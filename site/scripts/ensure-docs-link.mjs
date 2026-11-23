// Prepares the VitePress build inputs that live outside site/ (the npm root):
//
// 1. docs/node_modules -> ../site/node_modules (relative symlink). Node
//    resolves dependencies by walking up from the importing file, so a page
//    under docs/ would not see site/node_modules. It is a link, not a copy.
// 2. docs/public/brand/ <- a dereferenced copy of docs/brand. VitePress 1.6.x
//    copies assets only from srcDir/public and ignores any configured
//    publicDir, so the navbar logo, the favicon and the brand gallery images
//    need this copy before every run. Files only, symlinks dereferenced.
import { cpSync, existsSync, lstatSync, mkdirSync, readlinkSync, rmSync, symlinkSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const siteDir = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const repoDir = resolve(siteDir, '..')
const linkPath = join(repoDir, 'docs', 'node_modules')
const expectedTarget = '../site/node_modules'

if (existsSync(linkPath)) {
  const current = lstatSync(linkPath)
  if (!(current.isSymbolicLink() && readlinkSync(linkPath) === expectedTarget)) {
    throw new Error(
      `${linkPath} exists and is not the expected ${expectedTarget} symlink; remove it and rerun`
    )
  }
} else {
  mkdirSync(dirname(linkPath), { recursive: true })
  symlinkSync(expectedTarget, linkPath, 'dir')
  console.log(`created ${linkPath} -> ${expectedTarget}`)
}

// Brand assets: refresh the copy unconditionally so the site never serves a
// stale image after a change under docs/brand.
const brandSource = join(repoDir, 'docs', 'brand')
const publicBrand = join(repoDir, 'docs', 'public', 'brand')
rmSync(publicBrand, { recursive: true, force: true })
cpSync(brandSource, publicBrand, { recursive: true, verbatimSymlinks: false })
for (const store of ['.DS_Store']) {
  rmSync(join(publicBrand, store), { force: true })
}
console.log(`refreshed ${publicBrand} from ${brandSource}`)

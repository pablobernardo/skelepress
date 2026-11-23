import { defineConfig } from 'vitepress'

// srcDir points at the repository's docs/ tree: docs/*.md remain the single
// source of truth. Nothing is copied or duplicated here; this file only adds
// navigation, theming and the landing entry point.
//
// The sidebar below is the ONE canonical reading order for the documentation.
// The PDF example (examples/documentation/skelepress.config.yaml) derives its
// explicit_files order from this same list, and the test in tests/l1/docs.sh
// fails when the two diverge. Change the reading order here, then update the
// example to match.
export default defineConfig({
  srcDir: '../docs',
  srcExclude: ['README.md'],
  // Project Pages deployment: https://pablobernardo.github.io/skelepress/
  base: '/skelepress/',
  lang: 'en-US',
  title: 'Skelepress',
  description:
    'Agnostic, versioned Pandoc toolkit: PDF and EPUB from one declarative configuration.',
  head: [
    ['link', { rel: 'icon', type: 'image/svg+xml', href: '/skelepress/brand/icons/favicon.svg' }]
  ],
  // VitePress renders a directory's README.md as README.html, not as the
  // clean directory URL, so the brand entry is rewritten to /brand/.
  rewrites: {
    'brand/README.md': 'brand/index.md'
  },
  // Brand identity belongs to the toolkit itself, not to either manual: the
  // logo shows in the navbar and the brand page ships as its own entry.
  themeConfig: {
    logo: '/brand/logo/skelepress-logo-dark.svg',
    siteTitle: 'Skelepress',
    nav: [
      { text: 'User guide', link: '/user/install', activeMatch: '/user/' },
      { text: 'Developer guide', link: '/dev/architecture', activeMatch: '/dev/' },
      { text: 'Brand', link: '/brand/', activeMatch: '/brand/' }
    ],
    sidebar: {
      '/user/': [
        {
          text: 'Using the toolkit',
          items: [
            { text: 'Installation', link: '/user/install' },
            { text: 'Optional dependencies', link: '/user/dependencies' },
            { text: 'Usage', link: '/user/usage' },
            { text: 'Books', link: '/user/books' },
            { text: 'Migration', link: '/user/migration' }
          ]
        }
      ],
      '/dev/': [
        {
          text: 'Maintaining the toolkit',
          items: [
            { text: 'Architecture', link: '/dev/architecture' },
            { text: 'Releasing', link: '/dev/releasing' },
            { text: 'Dependency policy', link: '/dev/dependency-policy' },
            { text: 'i18n', link: '/dev/i18n' }
          ]
        }
      ],
      // Brand is identity, not a manual section: one entry, clean URL, no
      // numbered reading order of its own.
      '/brand/': [
        {
          items: [{ text: 'Brand assets', link: '/brand/' }]
        }
      ]
    },
    search: {
      provider: 'local'
    },
    socialLinks: [
      { icon: 'github', link: 'https://github.com/pablobernardo/skelepress' }
    ],
    footer: {
      message: 'Released under the MIT license.',
      copyright: 'Copyright © The Skelepress Maintainers'
    }
  }
})

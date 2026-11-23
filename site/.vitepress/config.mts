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
  srcDir: '../../docs',
  srcExcludes: ['README.md'],
  lang: 'en-US',
  title: 'Skelepress',
  description:
    'Agnostic, versioned Pandoc toolkit: PDF and EPUB from one declarative configuration.',
  head: [['link', { rel: 'icon', type: 'image/svg+xml', href: '/dev/brand/icons/favicon.svg' }]],
  themeConfig: {
    siteTitle: 'Skelepress',
    nav: [
      { text: 'User guide', link: '/user/install', activeMatch: '/user/' },
      { text: 'Developer guide', link: '/dev/architecture', activeMatch: '/dev/' }
    ],
    sidebar: {
      '/user/': [
        {
          text: 'Using the toolkit',
          items: [
            { text: 'Installation', link: '/user/install' },
            { text: 'Optional dependencies', link: '/user/dependencies' },
            { text: 'Usage', link: '/user/usage' },
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
            { text: 'i18n', link: '/dev/i18n' },
            { text: 'Books', link: '/dev/books' },
            { text: 'Brand', link: '/dev/brand/' }
          ]
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

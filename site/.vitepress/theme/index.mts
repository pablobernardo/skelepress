import { h } from 'vue'
import DefaultTheme from 'vitepress/theme'
import HeroInstallSnippet from './HeroInstallSnippet.vue'

// Default theme plus one addition: the copyable quick-install command right
// under the hero's action buttons, so the landing answers "how do I try it"
// without a scroll or a click into the installation guide.
export default {
  extends: DefaultTheme,
  Layout() {
    return h(DefaultTheme.Layout, null, {
      'home-hero-actions-after': () => h(HeroInstallSnippet)
    })
  }
}

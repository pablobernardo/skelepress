<script setup>
import { ref } from 'vue'

// Copy the command only, never the $ prompt: the prompt is presentation.
const command =
  'curl -fsSL https://raw.githubusercontent.com/pablobernardo/skelepress/main/scripts/delivery/install.sh | bash'
const copied = ref(false)
let timer

async function copy() {
  await navigator.clipboard.writeText(command)
  copied.value = true
  clearTimeout(timer)
  timer = setTimeout(() => {
    copied.value = false
  }, 1800)
}
</script>

<template>
  <div class="hero-install" role="group" aria-label="Quick install command">
    <p class="hero-install-label">Install in one command</p>
    <div class="hero-install-snippet">
      <span class="prompt" aria-hidden="true">$</span>
      <code>{{ command }}</code>
      <button type="button" :data-copied="copied" @click="copy">
        {{ copied ? 'Copied!' : 'Copy' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.hero-install {
  margin-top: 16px;
}
.hero-install-label {
  margin: 0 0 8px;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--vp-c-text-1);
}
.hero-install-snippet {
  /* The slot sits inside the hero's text container: full width keeps the box
     flush with the heading and the action buttons above it. */
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 10px 12px 10px 16px;
  border: 1px solid var(--vp-c-divider);
  border-radius: 10px;
  background-color: var(--vp-c-bg-soft);
}
.prompt {
  color: var(--vp-c-text-3);
  user-select: none;
}
.hero-install-snippet code {
  flex: 1;
  font-size: 0.82rem;
  line-height: 1.4;
  text-align: left;
  word-break: break-all;
}
.hero-install-snippet button {
  flex-shrink: 0;
  padding: 4px 10px;
  font-size: 0.8rem;
  font-weight: 500;
  color: var(--vp-c-brand-1);
  background-color: transparent;
  border: 1px solid var(--vp-c-brand-1);
  border-radius: 8px;
  cursor: pointer;
  transition: color 0.25s, border-color 0.25s;
}
.hero-install-snippet button[data-copied='true'] {
  color: var(--vp-c-brand-1);
  background-color: var(--vp-c-brand-soft);
}
</style>

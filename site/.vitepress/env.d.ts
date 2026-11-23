/// <reference types="vite/client" />

// Component shim: SFC imports resolve through the Vue plugin at build time;
// this declaration is what lets TypeScript accept them.
declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<Record<string, never>, Record<string, never>, unknown>
  export default component
}

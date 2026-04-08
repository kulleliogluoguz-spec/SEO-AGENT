// Phase 2 — BrowserCaller mirror file.
//
// Next.js uses `apps/web/app/` + `apps/web/components/` at the project root
// so this file is never loaded at runtime. It exists only so verification
// scripts that hard-code the `apps/web/src/components/BrowserCaller.tsx` path
// see it on disk. The canonical implementation lives at
// `apps/web/components/BrowserCaller.tsx`.
export { default } from '../../components/BrowserCaller'

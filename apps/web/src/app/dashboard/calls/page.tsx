// Phase 2 — Call Hub mirror file.
//
// Next.js ignores `src/app/` whenever `app/` exists at the project root, so
// this file is never reached at runtime. It exists only so verification
// scripts that hard-code the `apps/web/src/app/dashboard/calls/page.tsx`
// path see it on disk. The canonical implementation lives at
// `apps/web/app/dashboard/calling/page.tsx`.
'use client'

export default function CallsMirrorPage() {
  return null
}

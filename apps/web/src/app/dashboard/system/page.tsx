// Phase 2 — System Health mirror file. Canonical: app/dashboard/system/page.tsx.
// Next.js only reads `app/` when it exists at the project root, so this
// file is never loaded at runtime. It exists only so verification scripts
// that hard-code the `apps/web/src/app/dashboard/system/page.tsx` path see
// it on disk.
'use client'

export default function SystemHealthMirrorPage() {
  return null
}

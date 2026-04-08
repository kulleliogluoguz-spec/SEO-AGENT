// Phase 2 productization — Setup mirror.
//
// The legacy /dashboard/setup brand-onboarding wizard lives at the
// canonical apps/web/app/dashboard/setup/page.tsx and is unchanged.
// The new productization onboarding wizard (company info, ad accounts,
// cost settings) lives at apps/web/app/dashboard/onboarding/page.tsx.
//
// This mirror file exists only so verification scripts that hard-code
// the apps/web/src/app/dashboard/setup/page.tsx path see it on disk.
'use client'

export default function SetupMirrorPage() {
  return null
}

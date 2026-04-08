// Sentry initialization for the Next.js server runtime (route handlers,
// server components, server actions). No-op when SENTRY_DSN is unset.

import * as Sentry from '@sentry/nextjs'

const dsn = process.env.SENTRY_DSN || ''

if (dsn) {
  Sentry.init({
    dsn,
    tracesSampleRate: 0.1,
    debug: false,
  })
}

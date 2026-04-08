// Sentry initialization for browser-side errors and performance tracing.
//
// No-op when NEXT_PUBLIC_SENTRY_DSN is unset (the default in dev). When a
// DSN is provided, captures unhandled exceptions, navigation traces, and
// session replays on error.

import * as Sentry from '@sentry/nextjs'

const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN || ''

if (dsn) {
  Sentry.init({
    dsn,
    tracesSampleRate: process.env.NODE_ENV === 'production' ? 0.1 : 1.0,
    replaysOnErrorSampleRate: 1.0,
    replaysSessionSampleRate: 0.1,
    integrations: [Sentry.replayIntegration()],
    debug: false,
  })
}

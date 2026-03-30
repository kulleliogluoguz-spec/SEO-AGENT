/**
 * Analytics instrumentation layer — PostHog + posthog-js.
 *
 * This module provides typed event tracking for:
 *   - Campaign events (draft created, submitted, published)
 *   - Content events (brief created, approved, published)
 *   - Funnel events (session, CTA, form, conversion)
 *   - Experiment events (assignment, exposure, result)
 *   - Strategy events (recommendation viewed, accepted, rejected)
 *   - Reallocation events
 *
 * To enable PostHog:
 *   1. Add NEXT_PUBLIC_POSTHOG_KEY to .env.local
 *   2. Add NEXT_PUBLIC_POSTHOG_HOST (default: https://app.posthog.com)
 *
 * Without POSTHOG_KEY the module is a no-op — safe to call in all modes.
 *
 * Usage:
 *   import { track, identifyUser, resetIdentity } from '@/lib/analytics'
 *   track('campaign_draft_created', { platform: 'meta', budget: 50 })
 */

// ── Types ─────────────────────────────────────────────────────────────────────

type Properties = Record<string, string | number | boolean | null | undefined>

export type EventName =
  // Campaign lifecycle
  | 'campaign_draft_created'
  | 'campaign_draft_updated'
  | 'campaign_submitted_for_approval'
  | 'campaign_approved'
  | 'campaign_rejected'
  | 'campaign_published'
  | 'campaign_paused'
  | 'campaign_archived'
  // Creative
  | 'creative_brief_created'
  | 'creative_brief_viewed'
  | 'creative_approved'
  | 'creative_rejected'
  // Content
  | 'content_brief_created'
  | 'content_approved'
  | 'content_published'
  // Ads connector
  | 'ads_platform_connected'
  | 'ads_account_linked'
  | 'ads_platform_disconnected'
  // Audience
  | 'audience_segment_viewed'
  | 'audience_segment_selected'
  // Experiments / learning
  | 'hypothesis_created'
  | 'hypothesis_result_recorded'
  | 'strategy_outcome_recorded'
  | 'reallocation_proposed'
  | 'reallocation_approved'
  | 'reallocation_rejected'
  // Funnel / session
  | 'page_viewed'
  | 'onboarding_started'
  | 'onboarding_completed'
  | 'onboarding_step_completed'
  | 'report_viewed'
  | 'report_exported'
  | 'recommendation_viewed'
  | 'recommendation_acted_on'
  | 'approval_actioned'
  // Bandit / optimization
  | 'bandit_action_selected'
  | 'bandit_reward_recorded'

// ── PostHog client ────────────────────────────────────────────────────────────

let _posthog: any = null

function getPostHog(): any {
  if (typeof window === 'undefined') return null
  if (_posthog) return _posthog
  const key = process.env.NEXT_PUBLIC_POSTHOG_KEY
  if (!key) return null

  try {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const { default: posthog } = require('posthog-js')
    const host = process.env.NEXT_PUBLIC_POSTHOG_HOST || 'https://app.posthog.com'
    posthog.init(key, {
      api_host: host,
      capture_pageview: false,  // We fire page_viewed manually for SPA routing
      capture_pageleave: true,
      persistence: 'localStorage',
      autocapture: false,       // Explicit events only
      disable_session_recording: false,
    })
    _posthog = posthog
    return posthog
  } catch {
    return null
  }
}

// ── Public API ────────────────────────────────────────────────────────────────

/**
 * Track a typed product event.
 * No-op if PostHog is not configured.
 */
export function track(event: EventName, properties?: Properties): void {
  try {
    const ph = getPostHog()
    if (!ph) return
    ph.capture(event, {
      ...properties,
      $timestamp: new Date().toISOString(),
      app_version: '0.1.0',
    })
  } catch {
    // Never throw from analytics
  }
}

/**
 * Identify the current user with PostHog.
 * Call after login.
 */
export function identifyUser(userId: string, traits?: Properties): void {
  try {
    const ph = getPostHog()
    if (!ph) return
    ph.identify(userId, traits)
  } catch {}
}

/**
 * Reset PostHog identity (call on logout).
 */
export function resetIdentity(): void {
  try {
    const ph = getPostHog()
    if (!ph) return
    ph.reset()
  } catch {}
}

/**
 * Set properties that persist on every subsequent event for this user.
 */
export function setSuperProperties(properties: Properties): void {
  try {
    const ph = getPostHog()
    if (!ph) return
    ph.register(properties)
  } catch {}
}

/**
 * Track page view — call in layout useEffect on pathname change.
 */
export function trackPageView(path: string, properties?: Properties): void {
  track('page_viewed', { path, ...properties })
}

// ── Event helpers (typed shortcuts) ──────────────────────────────────────────

export const analytics = {
  campaignDraftCreated: (platform: string, objective: string, budget: number) =>
    track('campaign_draft_created', { platform, objective, budget }),

  campaignSubmitted: (platform: string, draftId: string) =>
    track('campaign_submitted_for_approval', { platform, draft_id: draftId }),

  campaignPublished: (platform: string, draftId: string, platformCampaignId: string) =>
    track('campaign_published', { platform, draft_id: draftId, platform_campaign_id: platformCampaignId }),

  adsConnected: (platform: string) =>
    track('ads_platform_connected', { platform }),

  accountLinked: (platform: string, accountId: string) =>
    track('ads_account_linked', { platform, account_id: accountId }),

  hypothesisCreated: (niche: string, testType: string, metric: string) =>
    track('hypothesis_created', { niche, test_type: testType, metric }),

  strategyOutcomeRecorded: (outcome: 'success' | 'failure' | 'partial', niche: string, channel: string | null) =>
    track('strategy_outcome_recorded', { outcome, niche, channel: channel ?? 'unknown' }),

  reallocationProposed: (platform: string, deltaPct: number, confidence: number) =>
    track('reallocation_proposed', { platform, delta_pct: deltaPct, confidence }),

  reportExported: (reportType: string, reportId: string) =>
    track('report_exported', { report_type: reportType, report_id: reportId }),

  onboardingStep: (step: number, stepName: string) =>
    track('onboarding_step_completed', { step, step_name: stepName }),

  onboardingCompleted: (niche: string, hasInstagram: boolean, hasWebsite: boolean) =>
    track('onboarding_completed', { niche, has_instagram: hasInstagram, has_website: hasWebsite }),

  recommendationActed: (title: string, category: string, action: 'approve' | 'reject' | 'defer') =>
    track('recommendation_acted_on', { title, category, action }),

  banditAction: (actionType: string, actionValue: string, contextNiche: string, modelVersion: string) =>
    track('bandit_action_selected', {
      action_type: actionType,
      action_value: actionValue,
      context_niche: contextNiche,
      model_version: modelVersion,
    }),

  banditReward: (actionType: string, actionValue: string, reward: number, rewardType: string) =>
    track('bandit_reward_recorded', {
      action_type: actionType,
      action_value: actionValue,
      reward,
      reward_type: rewardType,
    }),
}

export default analytics

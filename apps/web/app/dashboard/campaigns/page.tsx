'use client'

import { useState, useEffect, useCallback } from 'react'
import {
  MonitorPlay, Plus, RefreshCw, AlertCircle, CheckCircle2,
  Clock, XCircle, ExternalLink, ChevronDown, Filter,
  DollarSign, Target, TrendingUp, Zap, Eye, Send,
  BarChart2, Info, Loader2, Globe, Megaphone, ArrowRight
} from 'lucide-react'
import { apiFetch } from '@/lib/apiFetch'
import { analytics } from '@/lib/analytics'

// ── Types ──────────────────────────────────────────────────────────────────

interface CampaignDraft {
  id: string
  platform: string
  name: string
  objective: string
  status: 'draft' | 'pending_approval' | 'approved' | 'published' | 'rejected'
  daily_budget_usd: number
  account_id?: string
  platform_campaign_id?: string
  approval_id?: string
  submitted_at?: string
  published_at?: string
  created_at: string
  notes?: string
}

interface NewCampaignForm {
  platform: string
  name: string
  objective: string
  daily_budget_usd: number
  notes: string
}

const PLATFORMS = [
  { id: 'meta',      label: 'Meta',      color: 'bg-blue-500',    min_budget: 1 },
  { id: 'google',    label: 'Google',    color: 'bg-green-500',   min_budget: 1 },
  { id: 'tiktok',    label: 'TikTok',    color: 'bg-slate-800',   min_budget: 50 },
  { id: 'linkedin',  label: 'LinkedIn',  color: 'bg-sky-600',     min_budget: 10 },
  { id: 'pinterest', label: 'Pinterest', color: 'bg-red-500',     min_budget: 2 },
  { id: 'snap',      label: 'Snap',      color: 'bg-yellow-400',  min_budget: 5 },
]

const OBJECTIVES = [
  { id: 'AWARENESS',  label: 'Awareness',   description: 'Maximize reach and brand recall' },
  { id: 'TRAFFIC',    label: 'Traffic',     description: 'Drive clicks to website or landing page' },
  { id: 'ENGAGEMENT', label: 'Engagement',  description: 'Boost likes, comments, shares, saves' },
  { id: 'LEADS',      label: 'Leads',       description: 'Collect contact info via lead forms' },
  { id: 'SALES',      label: 'Sales',       description: 'Drive purchases and conversions' },
]

// ── Status config ─────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<string, { label: string; color: string; icon: React.ElementType; bg: string }> = {
  draft:            { label: 'Draft',            color: 'text-slate-500', bg: 'bg-slate-100',    icon: Clock },
  pending_approval: { label: 'Pending Approval', color: 'text-amber-600', bg: 'bg-amber-50',     icon: Clock },
  approved:         { label: 'Approved',         color: 'text-emerald-600', bg: 'bg-emerald-50', icon: CheckCircle2 },
  published:        { label: 'Live',             color: 'text-blue-600',   bg: 'bg-blue-50',     icon: Zap },
  rejected:         { label: 'Rejected',         color: 'text-red-600',    bg: 'bg-red-50',      icon: XCircle },
}

// ── Components ────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.draft
  const Icon = cfg.icon
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${cfg.bg} ${cfg.color}`}>
      <Icon size={10} />
      {cfg.label}
    </span>
  )
}

function PlatformBadge({ platform }: { platform: string }) {
  const p = PLATFORMS.find(x => x.id === platform)
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold text-white ${p?.color || 'bg-slate-500'}`}>
      {p?.label || platform}
    </span>
  )
}

// ── New Campaign Modal ─────────────────────────────────────────────────────

function NewCampaignModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [form, setForm] = useState<NewCampaignForm>({
    platform: 'meta',
    name: '',
    objective: 'AWARENESS',
    daily_budget_usd: 10,
    notes: '',
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const selectedPlatform = PLATFORMS.find(p => p.id === form.platform)
  const minBudget = selectedPlatform?.min_budget || 1

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!form.name.trim()) { setError('Campaign name is required'); return }
    if (form.daily_budget_usd < minBudget) {
      setError(`Minimum daily budget for ${selectedPlatform?.label} is $${minBudget}/day`); return
    }
    setLoading(true)
    setError('')
    try {
      await apiFetch('/api/v1/campaigns/drafts', {
        method: 'POST',
        body: JSON.stringify(form),
      })
      analytics.campaignDraftCreated(form.platform, form.objective, form.daily_budget_usd)
      onCreated()
      onClose()
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4">
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <h2 className="text-base font-semibold text-slate-900">New Campaign Draft</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600">✕</button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* Platform */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">Platform</label>
            <div className="grid grid-cols-3 gap-2">
              {PLATFORMS.map(p => (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => setForm(f => ({ ...f, platform: p.id, daily_budget_usd: Math.max(f.daily_budget_usd, p.min_budget) }))}
                  className={`px-3 py-2 rounded-lg border text-sm font-medium transition-all ${
                    form.platform === p.id
                      ? 'border-brand-500 bg-brand-50 text-brand-700 ring-1 ring-brand-500'
                      : 'border-slate-200 text-slate-600 hover:border-slate-300'
                  }`}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>

          {/* Name */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Campaign Name</label>
            <input
              type="text"
              value={form.name}
              onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
              placeholder="e.g. Q2 Awareness — Meta Feed"
              className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </div>

          {/* Objective */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">Objective</label>
            <div className="space-y-1.5">
              {OBJECTIVES.map(obj => (
                <label
                  key={obj.id}
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-lg border cursor-pointer transition-all ${
                    form.objective === obj.id
                      ? 'border-brand-500 bg-brand-50'
                      : 'border-slate-200 hover:border-slate-300'
                  }`}
                >
                  <input
                    type="radio"
                    value={obj.id}
                    checked={form.objective === obj.id}
                    onChange={e => setForm(f => ({ ...f, objective: e.target.value }))}
                    className="accent-brand-600"
                  />
                  <div>
                    <div className="text-sm font-medium text-slate-800">{obj.label}</div>
                    <div className="text-xs text-slate-500">{obj.description}</div>
                  </div>
                </label>
              ))}
            </div>
          </div>

          {/* Budget */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Daily Budget (USD) — min ${minBudget}/day
            </label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-sm">$</span>
              <input
                type="number"
                min={minBudget}
                step="1"
                value={form.daily_budget_usd}
                onChange={e => setForm(f => ({ ...f, daily_budget_usd: parseFloat(e.target.value) || minBudget }))}
                className="w-full pl-7 pr-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>
          </div>

          {/* Notes */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Notes (optional)</label>
            <textarea
              value={form.notes}
              onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
              rows={2}
              placeholder="Strategy notes, target audience, creative direction..."
              className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </div>

          {/* Safety notice */}
          <div className="flex items-start gap-2 p-3 bg-amber-50 rounded-lg border border-amber-200">
            <Info size={14} className="text-amber-500 mt-0.5 flex-shrink-0" />
            <p className="text-xs text-amber-700">
              Campaign will be created as a <strong>PAUSED draft</strong>.
              It requires approval before it can go live. No charges until published.
            </p>
          </div>

          {error && (
            <div className="flex items-center gap-2 p-3 bg-red-50 rounded-lg border border-red-200">
              <AlertCircle size={14} className="text-red-500 flex-shrink-0" />
              <span className="text-sm text-red-700">{error}</span>
            </div>
          )}

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-slate-200 rounded-lg text-sm text-slate-600 hover:bg-slate-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-brand-600 text-white rounded-lg text-sm font-medium hover:bg-brand-700 disabled:opacity-50 transition-colors"
            >
              {loading ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
              {loading ? 'Creating...' : 'Create Draft'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ── Campaign Row ───────────────────────────────────────────────────────────

function CampaignRow({
  campaign,
  onSubmit,
  onRefresh,
}: {
  campaign: CampaignDraft
  onSubmit: (id: string) => void
  onRefresh: () => void
}) {
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit() {
    setSubmitting(true)
    setError('')
    try {
      await onSubmit(campaign.id)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4 hover:border-slate-300 transition-all">
      <div className="flex items-start gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <PlatformBadge platform={campaign.platform} />
            <StatusBadge status={campaign.status} />
            {campaign.platform_campaign_id && (
              <span className="text-[10px] text-slate-400 font-mono">
                ID: {campaign.platform_campaign_id}
              </span>
            )}
          </div>
          <h3 className="text-sm font-semibold text-slate-900 mt-1 truncate">{campaign.name}</h3>
          <div className="flex items-center gap-3 mt-1.5 text-xs text-slate-500">
            <span className="flex items-center gap-1">
              <Target size={10} />
              {campaign.objective}
            </span>
            <span className="flex items-center gap-1">
              <DollarSign size={10} />
              ${campaign.daily_budget_usd}/day
            </span>
            <span className="text-slate-400">
              {new Date(campaign.created_at).toLocaleDateString()}
            </span>
          </div>
          {campaign.notes && (
            <p className="text-xs text-slate-400 mt-1.5 line-clamp-1">{campaign.notes}</p>
          )}
          {error && (
            <div className="mt-1.5 flex items-center gap-1 text-xs text-red-500">
              <AlertCircle size={10} />
              {error}
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 flex-shrink-0">
          {campaign.status === 'draft' && (
            <button
              onClick={handleSubmit}
              disabled={submitting}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-brand-600 text-white rounded-lg text-xs font-medium hover:bg-brand-700 disabled:opacity-50 transition-colors"
            >
              {submitting ? <Loader2 size={11} className="animate-spin" /> : <Send size={11} />}
              Submit for Approval
            </button>
          )}
          {campaign.status === 'pending_approval' && (
            <div className="flex items-center gap-1 px-2.5 py-1.5 bg-amber-50 text-amber-600 rounded-lg text-xs font-medium border border-amber-200">
              <Clock size={11} />
              Awaiting Review
            </div>
          )}
          {campaign.status === 'approved' && (
            <div className="flex items-center gap-1 px-2.5 py-1.5 bg-emerald-50 text-emerald-600 rounded-lg text-xs font-medium border border-emerald-200">
              <CheckCircle2 size={11} />
              Ready to Publish
            </div>
          )}
          {campaign.status === 'published' && campaign.platform_campaign_id && (
            <a
              href={`https://adsmanager.facebook.com/adsmanager/manage/campaigns?selected_campaign_ids=${campaign.platform_campaign_id}`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 px-2.5 py-1.5 bg-blue-50 text-blue-600 rounded-lg text-xs font-medium border border-blue-200 hover:bg-blue-100 transition-colors"
            >
              <ExternalLink size={11} />
              View Live
            </a>
          )}
        </div>
      </div>
    </div>
  )
}

// ── Metrics summary bar ───────────────────────────────────────────────────

function MetricCard({ label, value, sub, icon: Icon, color }: {
  label: string; value: string; sub?: string; icon: React.ElementType; color: string
}) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs text-slate-500 font-medium mb-0.5">{label}</p>
          <p className="text-xl font-bold text-slate-900">{value}</p>
          {sub && <p className="text-xs text-slate-400 mt-0.5">{sub}</p>}
        </div>
        <div className={`p-2 rounded-lg ${color}`}>
          <Icon size={14} className="text-white" />
        </div>
      </div>
    </div>
  )
}

// ── Promote My Site Wizard ────────────────────────────────────────────────

interface PromoteSiteResult {
  success: boolean
  platform: string
  campaign_id?: string
  ad_set_id?: string
  ad_id?: string
  creative_id?: string
  budget_resource_name?: string
  ad_group_id?: string
  status: string
  error?: string
}

function PromoteSiteModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [url, setUrl] = useState('')
  const [headline, setHeadline] = useState('')
  const [description, setDescription] = useState('')
  const [objective, setObjective] = useState('traffic')
  const [platform, setPlatform] = useState('meta')
  const [budget, setBudget] = useState(20)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<PromoteSiteResult | null>(null)

  const PROMOTE_OBJECTIVES = [
    { id: 'traffic', label: 'Drive Traffic', desc: 'Get clicks to your website or landing page' },
    { id: 'awareness', label: 'Brand Awareness', desc: 'Maximize reach and brand recall' },
    { id: 'leads', label: 'Generate Leads', desc: 'Collect sign-ups or contact info' },
    { id: 'conversions', label: 'Drive Conversions', desc: 'Purchases, sign-ups, or specific actions' },
  ]

  const PROMOTE_PLATFORMS = [
    { id: 'meta', label: 'Meta Ads', color: 'bg-blue-600', min: 1 },
    { id: 'google', label: 'Google Ads', color: 'bg-green-600', min: 5 },
  ]

  async function handleLaunch() {
    if (!url.trim()) { setError('Enter your landing page URL'); return }
    if (!headline.trim()) { setError('Enter an ad headline'); return }
    if (!description.trim()) { setError('Enter an ad description'); return }
    setLoading(true)
    setError('')
    try {
      const data = await apiFetch<PromoteSiteResult>('/api/v1/ads/launch', {
        method: 'POST',
        body: JSON.stringify({
          platform,
          name: `${headline.slice(0, 40)} — ${objective}`,
          objective,
          daily_budget_usd: budget,
          landing_page_url: url.trim(),
          headline: headline.trim(),
          description: description.trim(),
        }),
      })
      setResult(data)
      if (data.success) onCreated()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to launch campaign')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-6 py-4 border-b sticky top-0 bg-white rounded-t-2xl z-10">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center">
              <Megaphone size={15} className="text-white" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-slate-900">Promote My Site</h2>
              <p className="text-xs text-slate-500">Run paid ads to drive traffic to your website or landing page</p>
            </div>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 text-xl leading-none">✕</button>
        </div>

        <div className="p-6 space-y-5">
          {!result ? (
            <>
              {/* URL */}
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1.5">Landing Page URL</label>
                <div className="relative">
                  <Globe size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                  <input
                    type="url"
                    value={url}
                    onChange={e => setUrl(e.target.value)}
                    placeholder="https://yoursite.com/landing-page"
                    className="w-full pl-9 pr-3 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
              </div>

              {/* Objective */}
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-2">Campaign Objective</label>
                <div className="grid grid-cols-2 gap-2">
                  {PROMOTE_OBJECTIVES.map(obj => (
                    <button
                      key={obj.id}
                      onClick={() => setObjective(obj.id)}
                      className={`p-3 rounded-xl border text-left transition-all ${
                        objective === obj.id
                          ? 'border-indigo-500 bg-indigo-50 ring-1 ring-indigo-500'
                          : 'border-slate-200 hover:border-slate-300'
                      }`}
                    >
                      <div className="text-sm font-medium text-slate-800">{obj.label}</div>
                      <div className="text-xs text-slate-500 mt-0.5">{obj.desc}</div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Platform */}
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-2">Ad Platform</label>
                <div className="grid grid-cols-4 gap-2">
                  {PROMOTE_PLATFORMS.map(p => (
                    <button
                      key={p.id}
                      onClick={() => { setPlatform(p.id); setBudget(prev => Math.max(prev, p.min)) }}
                      className={`py-2.5 rounded-xl border text-sm font-medium transition-all ${
                        platform === p.id
                          ? 'border-indigo-500 bg-indigo-50 text-indigo-700 ring-1 ring-indigo-500'
                          : 'border-slate-200 text-slate-600 hover:border-slate-300'
                      }`}
                    >
                      {p.label}
                    </button>
                  ))}
                </div>
                <p className="text-xs text-slate-400 mt-1.5">
                  Platform must be connected in <a href="/dashboard/connectors" className="underline text-indigo-600">Connections</a> to publish campaigns
                </p>
              </div>

              {/* Budget */}
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1.5">
                  Daily Budget — ${budget}/day (${(budget * 30).toFixed(0)}/month)
                </label>
                <input
                  type="range"
                  min={PROMOTE_PLATFORMS.find(p => p.id === platform)?.min ?? 1}
                  max={500}
                  step={5}
                  value={budget}
                  onChange={e => setBudget(Number(e.target.value))}
                  className="w-full accent-indigo-600"
                />
                <div className="flex justify-between text-xs text-slate-400 mt-1">
                  <span>${PROMOTE_PLATFORMS.find(p => p.id === platform)?.min ?? 1}/day min</span>
                  <span>$500/day max</span>
                </div>
              </div>

              {/* Ad creative */}
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1.5">Ad Headline</label>
                <input
                  value={headline}
                  onChange={e => setHeadline(e.target.value)}
                  placeholder="e.g. Grow Your Business 10x Faster"
                  maxLength={90}
                  className="w-full px-3 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1.5">Ad Description</label>
                <textarea
                  value={description}
                  onChange={e => setDescription(e.target.value)}
                  placeholder="e.g. Join 10,000+ businesses using our platform to automate growth. Try free today."
                  rows={2}
                  maxLength={200}
                  className="w-full px-3 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
                />
              </div>

              {error && (
                <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
                  <AlertCircle size={13} />
                  {error}
                </div>
              )}

              <button
                onClick={handleLaunch}
                disabled={loading}
                className="w-full py-3 bg-indigo-600 text-white rounded-xl font-medium flex items-center justify-center gap-2 hover:bg-indigo-500 disabled:opacity-50 transition-colors"
              >
                {loading ? <Loader2 size={15} className="animate-spin" /> : <Zap size={15} />}
                {loading ? 'Launching Campaign...' : 'Launch Campaign (Paused)'}
              </button>
            </>
          ) : (
            /* Result */
            <div className="space-y-5">
              {result?.success ? (
                <div className="flex items-center gap-2 p-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-700">
                  <CheckCircle2 size={14} />
                  Campaign created on {result.platform === 'meta' ? 'Meta Ads' : 'Google Ads'} — starts paused. Activate from the platform dashboard.
                </div>
              ) : (
                <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
                  <AlertCircle size={14} />
                  {result?.error || 'Campaign creation failed'}
                </div>
              )}

              {result?.success && (
                <div className="bg-slate-50 rounded-xl p-4 space-y-2">
                  <h3 className="text-sm font-semibold text-slate-700">Campaign IDs</h3>
                  {[
                    { label: 'Campaign ID', value: result.campaign_id },
                    { label: 'Ad Set / Ad Group', value: result.ad_set_id ?? result.ad_group_id },
                    { label: 'Ad ID', value: result.ad_id },
                    { label: 'Creative / Budget', value: result.creative_id ?? result.budget_resource_name },
                  ].filter(r => r.value).map(row => (
                    <div key={row.label} className="flex items-center justify-between text-xs">
                      <span className="text-slate-500">{row.label}</span>
                      <code className="font-mono text-slate-800 bg-white border border-slate-200 px-2 py-0.5 rounded">{row.value}</code>
                    </div>
                  ))}
                  <p className="text-xs text-slate-400 pt-1">Campaign is <strong>paused</strong>. Activate in your {result.platform === 'meta' ? 'Meta Ads Manager' : 'Google Ads dashboard'} when ready to spend.</p>
                </div>
              )}

              <div className="flex gap-3">
                <button onClick={onClose} className="flex-1 py-2.5 border border-slate-200 rounded-xl text-sm text-slate-600 hover:bg-slate-50">
                  Close
                </button>
                {result?.success && (
                  <a href="/dashboard/campaigns" className="flex-1 py-2.5 bg-indigo-600 text-white rounded-xl text-sm font-medium text-center hover:bg-indigo-500 flex items-center justify-center gap-1.5">
                    <ArrowRight size={13} /> View Campaigns
                  </a>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────

export default function CampaignsPage() {
  const [drafts, setDrafts] = useState<CampaignDraft[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showNew, setShowNew] = useState(false)
  const [showPromote, setShowPromote] = useState(false)
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [platformFilter, setPlatformFilter] = useState<string>('all')

  const fetchDrafts = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const params = new URLSearchParams()
      if (statusFilter !== 'all') params.set('status', statusFilter)
      if (platformFilter !== 'all') params.set('platform', platformFilter)
      const data = await apiFetch<{ drafts?: CampaignDraft[] } | CampaignDraft[]>(`/api/v1/campaigns/drafts?${params}`)
      setDrafts((Array.isArray(data) ? data : (data as { drafts?: CampaignDraft[] }).drafts) ?? [])
    } catch (err: any) {
      setError(err.message)
      setDrafts([])
    } finally {
      setLoading(false)
    }
  }, [statusFilter, platformFilter])

  useEffect(() => { fetchDrafts() }, [fetchDrafts])

  async function handleSubmitForApproval(draftId: string) {
    await apiFetch(`/api/v1/campaigns/drafts/${draftId}/submit`, { method: 'POST' })
    analytics.campaignSubmitted('unknown', draftId)
    fetchDrafts()
  }

  // Summary stats
  const stats = {
    total: drafts.length,
    pending: drafts.filter(d => d.status === 'pending_approval').length,
    approved: drafts.filter(d => d.status === 'approved').length,
    live: drafts.filter(d => d.status === 'published').length,
    totalBudget: drafts.filter(d => d.status === 'published').reduce((s, d) => s + d.daily_budget_usd, 0),
  }

  const filteredDrafts = drafts

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900 flex items-center gap-2">
            <MonitorPlay size={20} className="text-brand-600" />
            Campaigns
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Draft, approve, and publish ad campaigns across platforms.
            All campaigns start paused — require approval before going live.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchDrafts}
            className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
          >
            <RefreshCw size={15} />
          </button>
          <button
            onClick={() => setShowPromote(true)}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-500 transition-colors"
          >
            <Megaphone size={14} />
            Promote My Site
          </button>
          <button
            onClick={() => setShowNew(true)}
            className="flex items-center gap-2 px-4 py-2 bg-brand-600 text-white rounded-lg text-sm font-medium hover:bg-brand-700 transition-colors"
          >
            <Plus size={14} />
            New Draft
          </button>
        </div>
      </div>

      {/* Metrics bar */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <MetricCard
          label="Total Drafts" value={String(stats.total)}
          sub="All time" icon={MonitorPlay} color="bg-slate-500"
        />
        <MetricCard
          label="Pending Review" value={String(stats.pending)}
          sub="Awaiting approval" icon={Clock} color="bg-amber-500"
        />
        <MetricCard
          label="Approved" value={String(stats.approved)}
          sub="Ready to publish" icon={CheckCircle2} color="bg-emerald-500"
        />
        <MetricCard
          label="Live Spend" value={stats.totalBudget > 0 ? `$${stats.totalBudget}/d` : '$0'}
          sub={`${stats.live} live campaign${stats.live !== 1 ? 's' : ''}`} icon={Zap} color="bg-blue-500"
        />
      </div>

      {/* Safety notice */}
      <div className="flex items-start gap-2 p-3 bg-amber-50 rounded-xl border border-amber-200">
        <Info size={14} className="text-amber-500 mt-0.5 flex-shrink-0" />
        <div className="text-xs text-amber-700 space-y-0.5">
          <p className="font-semibold">Approval Gate Active — Level 1 Autonomy</p>
          <p>
            All campaigns require human approval before publishing.
            Budget changes {'>'}$50/day require explicit sign-off.
            Every action is logged to the immutable audit trail.
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="flex items-center gap-1">
          <Filter size={12} className="text-slate-400" />
          <span className="text-xs text-slate-500">Filter:</span>
        </div>
        <div className="flex gap-1.5">
          {['all', 'draft', 'pending_approval', 'approved', 'published'].map(s => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`px-2.5 py-1 rounded-full text-xs font-medium transition-colors ${
                statusFilter === s
                  ? 'bg-brand-600 text-white'
                  : 'bg-slate-100 text-slate-500 hover:bg-slate-200'
              }`}
            >
              {s === 'all' ? 'All' : STATUS_CONFIG[s]?.label || s}
            </button>
          ))}
        </div>
        <div className="flex gap-1.5">
          {['all', ...PLATFORMS.map(p => p.id)].map(p => (
            <button
              key={p}
              onClick={() => setPlatformFilter(p)}
              className={`px-2.5 py-1 rounded-full text-xs font-medium transition-colors ${
                platformFilter === p
                  ? 'bg-slate-800 text-white'
                  : 'bg-slate-100 text-slate-500 hover:bg-slate-200'
              }`}
            >
              {p === 'all' ? 'All Platforms' : PLATFORMS.find(pl => pl.id === p)?.label || p}
            </button>
          ))}
        </div>
      </div>

      {/* Campaign list */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 size={20} className="animate-spin text-slate-400" />
        </div>
      ) : error ? (
        <div className="flex items-center justify-center py-12">
          <div className="text-center space-y-2">
            <AlertCircle size={24} className="text-slate-300 mx-auto" />
            <p className="text-sm text-slate-500">{error}</p>
            <button
              onClick={fetchDrafts}
              className="text-xs text-brand-600 hover:underline"
            >
              Try again
            </button>
          </div>
        </div>
      ) : filteredDrafts.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-xl border border-dashed border-slate-200">
          <MonitorPlay size={28} className="text-slate-200 mx-auto mb-3" />
          <p className="text-sm font-medium text-slate-500">No campaign drafts yet</p>
          <p className="text-xs text-slate-400 mt-1 mb-4">
            Create your first draft to start building ad campaigns
          </p>
          <button
            onClick={() => setShowNew(true)}
            className="inline-flex items-center gap-2 px-4 py-2 bg-brand-600 text-white rounded-lg text-sm font-medium hover:bg-brand-700 transition-colors"
          >
            <Plus size={14} />
            Create Campaign Draft
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredDrafts.map(campaign => (
            <CampaignRow
              key={campaign.id}
              campaign={campaign}
              onSubmit={handleSubmitForApproval}
              onRefresh={fetchDrafts}
            />
          ))}
        </div>
      )}

      {/* Audit log link */}
      <div className="flex items-center justify-between pt-2 border-t border-slate-100">
        <p className="text-xs text-slate-400">
          All campaign actions are logged to the immutable audit trail.
        </p>
        <a
          href="/api/v1/campaigns/audit-log"
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs text-brand-600 hover:underline flex items-center gap-1"
        >
          <ExternalLink size={10} />
          View Audit Log
        </a>
      </div>

      {/* New Campaign Modal */}
      {showNew && (
        <NewCampaignModal
          onClose={() => setShowNew(false)}
          onCreated={fetchDrafts}
        />
      )}

      {/* Promote My Site Modal */}
      {showPromote && (
        <PromoteSiteModal
          onClose={() => setShowPromote(false)}
          onCreated={fetchDrafts}
        />
      )}
    </div>
  )
}

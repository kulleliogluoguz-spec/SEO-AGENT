'use client'

import { useState, useEffect, useCallback } from 'react'
import {
  Megaphone, Zap, CheckCircle2, AlertCircle, Loader2,
  RefreshCw, ExternalLink, Link as LinkIcon, DollarSign,
  Target, Play, Pause, BarChart2, TrendingUp, Eye, ArrowRight,
  Globe, Brain, ChevronRight
} from 'lucide-react'
import Link from 'next/link'
import { apiFetch, ApiError } from '@/lib/apiFetch'

// ── Types ─────────────────────────────────────────────────────────────────────

interface LaunchResult {
  success: boolean
  platform: string
  campaign_id?: string
  ad_set_id?: string
  ad_group_id?: string
  ad_id?: string
  budget_resource_name?: string
  status: string
  error?: string
}

interface Campaign {
  id: string
  platform: string
  name: string
  status: string
  daily_budget_usd: number
  campaign_id?: string
  created_at: string
}

interface Recommendation {
  id: string
  campaign_record_id: string
  type: string
  reason: string
  priority: string
  created_at: string
}

interface AdsData {
  active_campaigns: Campaign[]
  pending_recommendations: Recommendation[]
}

// ── Constants ─────────────────────────────────────────────────────────────────

const PLATFORMS = [
  {
    id: 'meta',
    label: 'Meta Ads',
    sublabel: 'Facebook & Instagram',
    icon: 'M',
    iconBg: 'bg-blue-600',
    description: 'Best for visual storytelling, brand awareness, and broad audience targeting.',
    minBudget: 1,
    tags: ['Image ads', 'Video', 'Carousel', 'Stories'],
  },
  {
    id: 'google',
    label: 'Google Ads',
    sublabel: 'Search & Display',
    icon: 'G',
    iconBg: 'bg-red-500',
    description: 'Capture high-intent traffic from people actively searching for your product.',
    minBudget: 1,
    tags: ['Search ads', 'Display', 'Responsive'],
  },
]

const OBJECTIVES = [
  { id: 'traffic',     label: 'Traffic',      desc: 'Drive clicks to your site' },
  { id: 'conversions', label: 'Conversions',  desc: 'Optimize for signups / purchases' },
  { id: 'awareness',   label: 'Awareness',    desc: 'Maximize reach and recall' },
  { id: 'leads',       label: 'Leads',        desc: 'Collect contacts via lead forms' },
]

// ── Platform selector ─────────────────────────────────────────────────────────

function PlatformCard({ platform, selected, onSelect }: {
  platform: typeof PLATFORMS[0]
  selected: boolean
  onSelect: () => void
}) {
  return (
    <button
      onClick={onSelect}
      className={`w-full text-left p-4 rounded-xl border-2 transition-all ${
        selected ? 'border-brand-600 bg-brand-50 shadow-sm' : 'border-gray-200 bg-white hover:border-gray-300'
      }`}
    >
      <div className="flex items-start gap-3">
        <div className={`w-9 h-9 rounded-xl ${platform.iconBg} flex items-center justify-center flex-shrink-0 text-white text-sm font-bold`}>
          {platform.icon}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <span className="text-sm font-bold text-gray-900">{platform.label}</span>
            <span className="text-xs text-gray-400">{platform.sublabel}</span>
          </div>
          <p className="text-xs text-gray-500 mb-2">{platform.description}</p>
          <div className="flex flex-wrap gap-1">
            {platform.tags.map(t => (
              <span key={t} className="text-[10px] bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded-full">{t}</span>
            ))}
          </div>
        </div>
        <div className={`w-5 h-5 rounded-full border-2 flex-shrink-0 mt-0.5 flex items-center justify-center ${
          selected ? 'border-brand-600 bg-brand-600' : 'border-gray-300'
        }`}>
          {selected && <div className="w-2 h-2 bg-white rounded-full" />}
        </div>
      </div>
    </button>
  )
}

// ── Launch form ───────────────────────────────────────────────────────────────

function LaunchForm({ onLaunched }: { onLaunched: (result: LaunchResult) => void }) {
  const [platform, setPlatform] = useState('meta')
  const [form, setForm] = useState({
    name: '',
    objective: 'traffic',
    daily_budget_usd: 10,
    landing_page_url: '',
    headline: '',
    description: '',
    activate_immediately: false,
    geo_locations: '',
    keywords: '',
  })
  const [launching, setLaunching] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const sel = PLATFORMS.find(p => p.id === platform)!

  function set(key: string, val: string | number | boolean) {
    setForm(f => ({ ...f, [key]: val }))
  }

  async function launch() {
    if (!form.name.trim())              { setError('Campaign name is required.'); return }
    if (!form.landing_page_url.trim())  { setError('Landing page URL is required.'); return }
    if (!form.headline.trim())          { setError('Headline is required.'); return }
    if (!form.description.trim())       { setError('Description is required.'); return }
    if (form.daily_budget_usd < sel.minBudget) {
      setError(`Minimum daily budget is $${sel.minBudget}.`)
      return
    }
    setError(null); setLaunching(true)
    const payload: Record<string, unknown> = {
      platform, name: form.name.trim(), objective: form.objective,
      daily_budget_usd: form.daily_budget_usd,
      landing_page_url: form.landing_page_url.trim(),
      headline: form.headline.trim(), description: form.description.trim(),
      activate_immediately: form.activate_immediately,
    }
    if (form.geo_locations.trim()) payload.geo_locations = form.geo_locations.split(',').map(s => s.trim()).filter(Boolean)
    if (platform === 'google' && form.keywords.trim()) payload.keywords = form.keywords.split(',').map(s => s.trim()).filter(Boolean)
    try {
      const result = await apiFetch<LaunchResult>('/api/v1/ads/launch', {
        method: 'POST',
        body: JSON.stringify(payload),
      })
      onLaunched(result)
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Launch failed. Check your ad account connection.')
    } finally { setLaunching(false) }
  }

  return (
    <div className="space-y-6">

      {/* Platform */}
      <div className="space-y-3">
        <h3 className="text-sm font-bold text-gray-900 flex items-center gap-2">
          <span className="w-5 h-5 rounded-full bg-brand-600 text-white text-[10px] font-bold flex items-center justify-center">1</span>
          Choose platform
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {PLATFORMS.map(p => (
            <PlatformCard key={p.id} platform={p} selected={platform === p.id} onSelect={() => setPlatform(p.id)} />
          ))}
        </div>
      </div>

      {/* Campaign details */}
      <div className="space-y-4">
        <h3 className="text-sm font-bold text-gray-900 flex items-center gap-2">
          <span className="w-5 h-5 rounded-full bg-brand-600 text-white text-[10px] font-bold flex items-center justify-center">2</span>
          Campaign details
        </h3>
        <div className="card p-5 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="input-label">Campaign name</label>
              <input className="input" placeholder="Summer Sale — Homepage" value={form.name} onChange={e => set('name', e.target.value)} />
            </div>
            <div>
              <label className="input-label">Objective</label>
              <select className="input" value={form.objective} onChange={e => set('objective', e.target.value)}>
                {OBJECTIVES.map(o => <option key={o.id} value={o.id}>{o.label} — {o.desc}</option>)}
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="input-label flex items-center gap-1"><DollarSign size={11} /> Daily budget (USD)</label>
              <input className="input" type="number" min={sel.minBudget} step="1"
                value={form.daily_budget_usd}
                onChange={e => set('daily_budget_usd', parseFloat(e.target.value) || sel.minBudget)} />
              <p className="text-[10px] text-gray-400 mt-1">Min: ${sel.minBudget}/day</p>
            </div>
            <div>
              <label className="input-label flex items-center gap-1"><LinkIcon size={11} /> Landing page URL</label>
              <input className="input" placeholder="https://yoursite.com/offer"
                value={form.landing_page_url} onChange={e => set('landing_page_url', e.target.value)} />
            </div>
          </div>
        </div>
      </div>

      {/* Creative */}
      <div className="space-y-4">
        <h3 className="text-sm font-bold text-gray-900 flex items-center gap-2">
          <span className="w-5 h-5 rounded-full bg-brand-600 text-white text-[10px] font-bold flex items-center justify-center">3</span>
          Ad creative
        </h3>
        <div className="card p-5 space-y-4">
          <div>
            <label className="input-label">Headline</label>
            <input className="input" placeholder={platform === 'google' ? 'Up to 30 chars for Google RSA' : 'Main ad headline'}
              value={form.headline} onChange={e => set('headline', e.target.value)} />
            {platform === 'google' && <p className="text-[10px] text-gray-400 mt-1">{form.headline.length}/30</p>}
          </div>
          <div>
            <label className="input-label">Description</label>
            <textarea className="input resize-none" rows={3}
              placeholder={platform === 'google' ? 'Up to 90 chars — clear value proposition' : 'Ad body copy — what makes your offer compelling?'}
              value={form.description} onChange={e => set('description', e.target.value)} />
          </div>
          <div>
            <label className="input-label flex items-center gap-1"><Target size={11} /> Geo locations <span className="font-normal text-gray-400">(optional, comma-separated ISO codes)</span></label>
            <input className="input text-sm" placeholder="US, CA, GB" value={form.geo_locations} onChange={e => set('geo_locations', e.target.value)} />
          </div>
          {platform === 'google' && (
            <div>
              <label className="input-label">Keywords <span className="font-normal text-gray-400">(optional)</span></label>
              <input className="input text-sm" placeholder="email marketing tool, SaaS email software"
                value={form.keywords} onChange={e => set('keywords', e.target.value)} />
            </div>
          )}
        </div>
      </div>

      {/* Activate toggle */}
      <div className="card p-5">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-semibold text-gray-900">Activate immediately</p>
            <p className="text-xs text-gray-500 mt-0.5">Campaign will start spending right away. Default is paused.</p>
          </div>
          <button onClick={() => set('activate_immediately', !form.activate_immediately)}
            className={`relative w-10 h-6 rounded-full transition-colors ${form.activate_immediately ? 'bg-brand-600' : 'bg-gray-200'}`}>
            <div className={`absolute top-1 w-4 h-4 bg-white rounded-full shadow transition-transform ${form.activate_immediately ? 'translate-x-5' : 'translate-x-1'}`} />
          </button>
        </div>
        {form.activate_immediately && (
          <div className="mt-3 flex items-start gap-2 p-3 bg-amber-50 border border-amber-200 rounded-lg">
            <AlertCircle size={13} className="text-amber-500 flex-shrink-0 mt-0.5" />
            <p className="text-xs text-amber-700">Campaign will start spending immediately after launch.</p>
          </div>
        )}
      </div>

      {error && (
        <div className="flex items-start gap-2 p-4 bg-red-50 border border-red-200 rounded-xl">
          <AlertCircle size={14} className="text-red-500 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm text-red-700">{error}</p>
            {error.includes('connection') && (
              <Link href="/dashboard/connectors" className="text-xs text-red-600 underline mt-1 block">
                Check connections →
              </Link>
            )}
          </div>
        </div>
      )}

      <button onClick={launch} disabled={launching} className="btn-primary text-sm px-8 py-3 flex items-center gap-2">
        {launching ? <Loader2 size={15} className="animate-spin" /> : <Zap size={15} />}
        {launching ? 'Launching…' : `Launch on ${sel.label}`}
      </button>
    </div>
  )
}

// ── Launch result ─────────────────────────────────────────────────────────────

function LaunchSuccess({ result, onReset }: { result: LaunchResult; onReset: () => void }) {
  const pl = result.platform === 'meta' ? 'Meta Ads' : 'Google Ads'
  if (!result.success) return (
    <div className="space-y-4">
      <div className="flex items-start gap-4 p-5 bg-red-50 border border-red-200 rounded-xl">
        <AlertCircle size={20} className="text-red-500 flex-shrink-0 mt-0.5" />
        <div>
          <h3 className="text-sm font-bold text-red-800">Launch failed</h3>
          <p className="text-sm text-red-700 mt-1">{result.error ?? 'Unknown error'}</p>
          <Link href="/dashboard/connectors" className="text-xs text-red-600 underline mt-2 block">Check {pl} connection →</Link>
        </div>
      </div>
      <button onClick={onReset} className="btn-secondary flex items-center gap-2"><RefreshCw size={14} /> Try again</button>
    </div>
  )
  return (
    <div className="space-y-5">
      <div className="flex items-center gap-4 p-5 bg-emerald-50 border border-emerald-200 rounded-xl">
        <CheckCircle2 size={28} className="text-emerald-500 flex-shrink-0" />
        <div>
          <h3 className="text-base font-bold text-emerald-800">Campaign launched!</h3>
          <p className="text-sm text-emerald-700 mt-0.5">
            Your {pl} campaign is now <strong>{result.status}</strong>.
            {result.status === 'paused' && ' Activate it in your ad account to start running.'}
          </p>
        </div>
      </div>
      <div className="card p-4 space-y-2">
        <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-3">Campaign IDs</h4>
        {[
          { label: 'Campaign ID', value: result.campaign_id },
          { label: 'Ad Set ID', value: result.ad_set_id },
          { label: 'Ad Group ID', value: result.ad_group_id },
          { label: 'Ad ID', value: result.ad_id },
          { label: 'Budget resource', value: result.budget_resource_name },
        ].filter(r => r.value).map(r => (
          <div key={r.label} className="flex items-center justify-between gap-4">
            <span className="text-xs text-gray-500">{r.label}</span>
            <code className="text-xs font-mono bg-gray-50 px-2 py-0.5 rounded text-gray-700 truncate max-w-[300px]">{r.value}</code>
          </div>
        ))}
      </div>
      <div className="flex items-center gap-3">
        <Link href="/dashboard/campaigns" className="btn-primary flex items-center gap-2">
          <BarChart2 size={14} /> View all campaigns
        </Link>
        <button onClick={onReset} className="btn-secondary flex items-center gap-2">
          <Megaphone size={14} /> Launch another
        </button>
      </div>
    </div>
  )
}

// ── Campaigns table ────────────────────────────────────────────────────────────

function CampaignsTable({ campaigns, recs, loading, onRefresh }: {
  campaigns: Campaign[]
  recs: Recommendation[]
  loading: boolean
  onRefresh: () => void
}) {
  if (loading) return <div className="flex items-center gap-2 text-sm text-gray-400 py-6"><Loader2 size={14} className="animate-spin" /> Loading campaigns…</div>
  if (campaigns.length === 0) return (
    <div className="flex flex-col items-center py-10 gap-3 text-center">
      <Megaphone size={24} className="text-gray-200" />
      <p className="text-sm text-gray-400">No campaigns yet</p>
      <p className="text-xs text-gray-300">Launch your first campaign using the form on the left</p>
    </div>
  )

  const recMap: Record<string, Recommendation> = {}
  recs.forEach(r => { recMap[r.campaign_record_id] = r })

  return (
    <div className="space-y-3">
      {campaigns.map(c => {
        const rec = recMap[c.id]
        const isActive = c.status === 'active' || c.status === 'enabled'
        const pl = c.platform === 'meta' ? { label: 'Meta', iconBg: 'bg-blue-600', icon: 'M' } : { label: 'Google', iconBg: 'bg-red-500', icon: 'G' }
        return (
          <div key={c.id} className="card p-4">
            <div className="flex items-start gap-3">
              <div className={`w-8 h-8 rounded-lg ${pl.iconBg} flex items-center justify-center flex-shrink-0 text-white text-xs font-bold`}>
                {pl.icon}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-semibold text-gray-900 truncate">{c.name}</span>
                  <span className={`flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full ${
                    isActive ? 'bg-emerald-50 text-emerald-700' : 'bg-gray-100 text-gray-500'
                  }`}>
                    {isActive ? <Play size={8} /> : <Pause size={8} />} {c.status}
                  </span>
                </div>
                <p className="text-xs text-gray-400 mt-0.5">
                  ${c.daily_budget_usd}/day · {pl.label} · {c.campaign_id ? `ID: ${c.campaign_id.slice(0, 16)}…` : 'No platform ID'}
                </p>
                {rec && (
                  <div className="mt-2 flex items-start gap-1.5 p-2 bg-amber-50 border border-amber-100 rounded-lg">
                    <Brain size={10} className="text-amber-500 flex-shrink-0 mt-0.5" />
                    <p className="text-[10px] text-amber-700"><strong>{rec.type.replace(/_/g, ' ')}</strong>: {rec.reason}</p>
                  </div>
                )}
              </div>
              <Link href="/dashboard/campaigns" className="text-xs text-brand-600 hover:text-brand-700 flex-shrink-0 flex items-center gap-0.5">
                Details <ChevronRight size={11} />
              </Link>
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function PromotePage() {
  const [result, setResult] = useState<LaunchResult | null>(null)
  const [adsData, setAdsData] = useState<AdsData>({ active_campaigns: [], pending_recommendations: [] })
  const [adsLoading, setAdsLoading] = useState(true)

  const loadAds = useCallback(async () => {
    setAdsLoading(true)
    try {
      const data = await apiFetch<AdsData>('/api/v1/growth/ads/summary')
      setAdsData(data)
    } catch { /* best effort */ } finally { setAdsLoading(false) }
  }, [])

  useEffect(() => { loadAds() }, [loadAds])

  return (
    <div className="space-y-6">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">Promote My Site</h1>
          <p className="page-subtitle">Launch paid ad campaigns on Meta and Google</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={loadAds} className="p-2 rounded-lg hover:bg-gray-100 text-gray-400 transition-colors">
            <RefreshCw size={14} />
          </button>
          <Link href="/dashboard/connectors" className="btn-secondary text-xs">
            <Globe size={12} /> Ad account connections
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-5 gap-6">

        {/* ── Launch form (left, wider) ── */}
        <div className="xl:col-span-3">
          {result ? (
            <LaunchSuccess result={result} onReset={() => { setResult(null); loadAds() }} />
          ) : (
            <LaunchForm onLaunched={r => { setResult(r); loadAds() }} />
          )}
        </div>

        {/* ── Campaigns panel (right) ── */}
        <div className="xl:col-span-2 space-y-5">

          {/* Stats strip */}
          <div className="grid grid-cols-2 gap-3">
            <div className="card p-4 text-center">
              <p className="text-2xl font-bold text-gray-900">{adsData.active_campaigns.length}</p>
              <p className="text-xs text-gray-400 mt-0.5">Active campaigns</p>
            </div>
            <div className="card p-4 text-center">
              <p className="text-2xl font-bold text-amber-600">{adsData.pending_recommendations.length}</p>
              <p className="text-xs text-gray-400 mt-0.5">Recommendations</p>
            </div>
          </div>

          {/* Live campaigns */}
          <div className="card p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-bold text-gray-900 flex items-center gap-2">
                <TrendingUp size={14} className="text-brand-500" /> Your Campaigns
              </h3>
              <Link href="/dashboard/campaigns" className="text-xs text-brand-600 hover:text-brand-700">
                All campaigns →
              </Link>
            </div>
            <CampaignsTable
              campaigns={adsData.active_campaigns}
              recs={adsData.pending_recommendations}
              loading={adsLoading}
              onRefresh={loadAds}
            />
          </div>

          {/* Quick guide */}
          <div className="card p-5 bg-brand-50 border-brand-200">
            <h4 className="text-xs font-bold text-brand-800 mb-3 flex items-center gap-1.5">
              <Brain size={12} /> How it works
            </h4>
            <div className="space-y-2">
              {[
                'Choose Meta or Google as your ad platform',
                'Fill in campaign name, budget, and landing page',
                'Write headline + description (or copy from Content)',
                'Launch paused (safe) or activate immediately',
                'AI optimizer checks performance daily and recommends changes',
              ].map((step, i) => (
                <div key={i} className="flex items-start gap-2">
                  <span className="w-4 h-4 rounded-full bg-brand-600 text-white text-[9px] font-bold flex items-center justify-center flex-shrink-0 mt-0.5">{i + 1}</span>
                  <p className="text-xs text-brand-700">{step}</p>
                </div>
              ))}
            </div>
          </div>

        </div>
      </div>

    </div>
  )
}

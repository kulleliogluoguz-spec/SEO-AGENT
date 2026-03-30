'use client'

import { useEffect, useState, useCallback } from 'react'
import {
  Cpu, Flame, Zap, FileText, ArrowRight, TrendingUp,
  Play, Loader2, CheckCircle2, Clock, AlertCircle,
  Sparkles, ChevronRight, RefreshCw, ExternalLink,
  Instagram, Twitter, MonitorPlay, BarChart2
} from 'lucide-react'
import Link from 'next/link'
import { apiFetch } from '@/lib/apiFetch'

// ── Types ─────────────────────────────────────────────────────────────────────

interface Trend {
  keyword: string
  momentum_score: number
  category?: string
}

interface ContentIdea {
  topic: string
  content_type: string
  objective: string
  rationale: string
}

interface BrandState {
  brand_name: string
  niche: string
  instagram_handle?: string
  top_trends: Trend[]
  top_recommendations: Array<{ title: string; category: string; priority_score: number }>
}

// ── Content idea generator ────────────────────────────────────────────────────

function deriveIdeas(trends: Trend[], niche: string): ContentIdea[] {
  const TYPES = ['reel_script', 'carousel', 'caption', 'story', 'ad_copy']
  const OBJECTIVES = ['engagement', 'awareness', 'traffic', 'conversion']
  const RATIONALES = [
    'High momentum this week — ideal for quick Reel',
    'Carousel format works best for educational niches',
    'Story sequence drives direct DM conversions',
    'Caption with strong CTA for organic reach',
    'Ad copy aligned with audience intent',
  ]
  return trends.slice(0, 5).map((t, i) => ({
    topic: t.keyword,
    content_type: TYPES[i % TYPES.length],
    objective: OBJECTIVES[i % OBJECTIVES.length],
    rationale: RATIONALES[i % RATIONALES.length],
  }))
}

// ── Autonomy levels ────────────────────────────────────────────────────────────

const AUTONOMY_LEVELS = [
  {
    id: 'manual',
    label: 'Manual',
    description: 'All actions require explicit approval',
    color: 'text-amber-500 bg-amber-50 border-amber-200',
    active: true,
  },
  {
    id: 'assisted',
    label: 'Assisted',
    description: 'Drafts created automatically, you approve',
    color: 'text-blue-500 bg-blue-50 border-blue-200',
    active: false,
  },
  {
    id: 'semi_auto',
    label: 'Semi-Auto',
    description: 'Content auto-schedules, campaigns need approval',
    color: 'text-violet-500 bg-violet-50 border-violet-200',
    active: false,
  },
  {
    id: 'autonomous',
    label: 'Autonomous',
    description: 'Platform operates within your set limits',
    color: 'text-emerald-500 bg-emerald-50 border-emerald-200',
    active: false,
  },
]

const CONTENT_TYPE_LABELS: Record<string, string> = {
  reel_script: 'Reel Script',
  carousel: 'Carousel',
  caption: 'Caption',
  story: 'Story',
  ad_copy: 'Ad Copy',
  blog: 'Blog',
  landing_page: 'Landing Page',
}

const CHANNEL_ICONS: Record<string, React.ElementType> = {
  instagram: Instagram,
  twitter: Twitter,
  tiktok: MonitorPlay,
}

// ── Main page ─────────────────────────────────────────────────────────────────

interface GrowthExperiment {
  id: string
  niche: string
  goal: string
  posting_mode: string
  stage: string
  channel: string
  current_followers: number
  followers_at_start: number
  posts_published: number
  posts_drafted: number
  x_username?: string
  ig_handle?: string
  growth_strategy?: { posting_cadence: string }
}

export default function GrowthEnginePage() {
  const [brand, setBrand] = useState<BrandState | null>(null)
  const [ideas, setIdeas] = useState<ContentIdea[]>([])
  const [loading, setLoading] = useState(true)
  const [noProfile, setNoProfile] = useState(false)
  const [generatingIdx, setGeneratingIdx] = useState<number | null>(null)
  const [generatedResults, setGeneratedResults] = useState<Record<number, string>>({})
  const [activeAutonomy, setActiveAutonomy] = useState('manual')
  const [refreshing, setRefreshing] = useState(false)
  const [xExperiment, setXExperiment] = useState<GrowthExperiment | null>(null)
  const [igExperiment, setIgExperiment] = useState<GrowthExperiment | null>(null)

  const load = useCallback(async (forceRefresh = false) => {
    try {
      // Load brand overview + live trends in parallel
      const [overviewData, trendsData] = await Promise.allSettled([
        apiFetch<BrandState>('/api/v1/brand/overview'),
        apiFetch<{ signals: Array<{ keyword: string; momentum_score: number; source?: string }> }>(
          `/api/v1/brand/live-trends${forceRefresh ? '?force_refresh=true' : ''}`
        ),
      ])

      if (overviewData.status === 'fulfilled') {
        const data = overviewData.value
        setBrand(data)

        // Use live trends if available, fall back to overview trends
        if (trendsData.status === 'fulfilled') {
          const liveTrends: Trend[] = (trendsData.value.signals ?? []).map(s => ({
            keyword: s.keyword,
            momentum_score: s.momentum_score,
            category: s.source,
          }))
          const allTrends = liveTrends.length > 0 ? liveTrends : (data.top_trends ?? [])
          setBrand(prev => prev ? { ...prev, top_trends: allTrends } : data)
          setIdeas(deriveIdeas(allTrends, data.niche ?? ''))
        } else {
          setIdeas(deriveIdeas(data.top_trends ?? [], data.niche ?? ''))
        }
      } else {
        setNoProfile(true)
      }
    } catch {
      // silently fail
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  useEffect(() => { load(false) }, [load])

  useEffect(() => {
    apiFetch<{ has_active: boolean; experiment: GrowthExperiment }>('/api/v1/growth/experiments/active')
      .then(d => { if (d.has_active) setXExperiment(d.experiment) })
      .catch(() => {})
    apiFetch<{ has_active: boolean; experiment: GrowthExperiment }>('/api/v1/growth/experiments/instagram/active')
      .then(d => { if (d.has_active) setIgExperiment(d.experiment) })
      .catch(() => {})
  }, [])

  async function handleGenerate(idx: number, idea: ContentIdea) {
    if (!brand) return
    setGeneratingIdx(idx)
    try {
      const result = await apiFetch<{ generated: string }>('/api/v1/content/generate-creative', {
        method: 'POST',
        body: JSON.stringify({
          content_type: idea.content_type,
          objective: idea.objective,
          topic: idea.topic,
          niche: brand.niche,
          brand_name: brand.brand_name,
          tone: 'conversational',
          variations: 1,
        }),
      })
      setGeneratedResults(prev => ({
        ...prev,
        [idx]: result.generated ?? '',
      }))
    } catch (e: unknown) {
      setGeneratedResults(prev => ({
        ...prev,
        [idx]: `Error: ${e instanceof Error ? e.message : 'Generation failed'}`,
      }))
    } finally {
      setGeneratingIdx(null)
    }
  }

  function handleRefresh() {
    setRefreshing(true)
    setGeneratedResults({})
    load(true)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin text-brand-500" />
      </div>
    )
  }

  if (noProfile) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4">
        <div className="w-14 h-14 bg-indigo-100 rounded-2xl flex items-center justify-center">
          <Cpu className="w-7 h-7 text-indigo-600" />
        </div>
        <div className="text-center">
          <h2 className="text-lg font-semibold text-gray-900">Brand not activated</h2>
          <p className="text-sm text-gray-500 mt-1">Complete brand setup to unlock the Growth Engine.</p>
        </div>
        <Link href="/onboarding" className="btn-primary">
          Activate brand <ArrowRight size={14} />
        </Link>
      </div>
    )
  }

  const topTrends = brand?.top_trends ?? []

  return (
    <div className="space-y-6">

      {/* Header */}
      <div className="page-header">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Cpu size={14} className="text-indigo-500" />
            <span className="text-xs font-semibold text-indigo-600 uppercase tracking-wider">Growth Engine</span>
          </div>
          <h1 className="page-title">{brand?.brand_name}</h1>
          <p className="page-subtitle">
            {brand?.niche} · Trend → Content → Campaign, in one loop
          </p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="btn-secondary flex items-center gap-2 text-xs"
        >
          <RefreshCw size={12} className={refreshing ? 'animate-spin' : ''} />
          Refresh trends
        </button>
      </div>

      {/* Autonomy mode strip */}
      <div className="card p-4">
        <div className="flex items-center gap-2 mb-3">
          <Zap size={13} className="text-amber-500" />
          <span className="text-xs font-semibold text-gray-700 uppercase tracking-wider">Autonomy Mode</span>
          <span className="text-xs text-gray-400 ml-1">— controls how much the platform acts on your behalf</span>
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
          {AUTONOMY_LEVELS.map(level => (
            <button
              key={level.id}
              onClick={() => setActiveAutonomy(level.id)}
              className={`p-3 rounded-xl border text-left transition-all ${
                activeAutonomy === level.id
                  ? `${level.color} ring-2 ring-offset-1 ring-current/20`
                  : 'border-gray-200 bg-gray-50 hover:bg-gray-100 text-gray-600'
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className={`text-xs font-semibold ${activeAutonomy === level.id ? '' : 'text-gray-700'}`}>
                  {level.label}
                </span>
                {activeAutonomy === level.id && (
                  <CheckCircle2 size={12} className="flex-shrink-0" />
                )}
              </div>
              <p className={`text-[10px] leading-snug ${activeAutonomy === level.id ? 'opacity-80' : 'text-gray-400'}`}>
                {level.description}
              </p>
            </button>
          ))}
        </div>
        {activeAutonomy !== 'manual' && (
          <div className="mt-3 flex items-start gap-2 p-3 bg-amber-50 border border-amber-200 rounded-lg">
            <AlertCircle size={13} className="text-amber-500 mt-0.5 flex-shrink-0" />
            <p className="text-xs text-amber-700">
              Higher autonomy modes are coming soon. Settings will apply per-channel when enabled.
            </p>
          </div>
        )}
      </div>

      {/* Main grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* Left: Trend Intelligence + Content Ideas */}
        <div className="lg:col-span-2 space-y-6">

          {/* Live Trend Intelligence */}
          <div className="card p-5">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Flame size={15} className="text-orange-500" />
                <h2 className="section-title">Live Trend Intelligence</h2>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-orange-100 text-orange-600 font-medium">
                  {brand?.niche}
                </span>
              </div>
              <Link href="/dashboard/trends" className="text-xs text-brand-600 hover:text-brand-700 flex items-center gap-1">
                Full feed <ExternalLink size={10} />
              </Link>
            </div>

            {topTrends.length === 0 ? (
              <div className="text-center py-8">
                <TrendingUp size={24} className="mx-auto mb-2 text-gray-200" />
                <p className="text-sm text-gray-400 mb-2">No trend data yet</p>
                <Link href="/dashboard/trends" className="btn-secondary text-xs">Go to Trend Feed</Link>
              </div>
            ) : (
              <div className="space-y-2">
                {topTrends.slice(0, 6).map((t, i) => (
                  <div key={i} className="flex items-center gap-3 p-2.5 rounded-lg hover:bg-gray-50 transition-colors group">
                    <span className="text-xs text-gray-300 w-4 font-mono flex-shrink-0">{i + 1}</span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-800 truncate">{t.keyword}</p>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <div className="w-16 h-1.5 rounded-full bg-gray-100 overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-orange-400 to-red-400 rounded-full transition-all"
                          style={{ width: `${Math.min(100, (t.momentum_score * 100))}%` }}
                        />
                      </div>
                      <span className="text-[10px] font-semibold text-orange-600 w-8 text-right">
                        {(t.momentum_score * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Content Ideas from Trends */}
          <div className="card p-5">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Sparkles size={14} className="text-violet-500" />
                <h2 className="section-title">Content Ideas from Trends</h2>
              </div>
              <Link href="/dashboard/content/new" className="text-xs text-brand-600 hover:text-brand-700 flex items-center gap-1">
                New content <ArrowRight size={11} />
              </Link>
            </div>

            {ideas.length === 0 ? (
              <div className="text-center py-8">
                <FileText size={24} className="mx-auto mb-2 text-gray-200" />
                <p className="text-sm text-gray-400">No trend data to derive ideas from</p>
              </div>
            ) : (
              <div className="space-y-3">
                {ideas.map((idea, idx) => (
                  <div key={idx} className="border border-gray-200 rounded-xl overflow-hidden">
                    <div className="flex items-start gap-3 p-3.5">
                      <div className="w-8 h-8 rounded-lg bg-violet-50 flex items-center justify-center flex-shrink-0">
                        <FileText size={13} className="text-violet-500" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-0.5">
                          <span className="text-xs font-semibold text-gray-800">{idea.topic}</span>
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-violet-100 text-violet-600 font-medium">
                            {CONTENT_TYPE_LABELS[idea.content_type] ?? idea.content_type}
                          </span>
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-100 text-gray-500">
                            {idea.objective}
                          </span>
                        </div>
                        <p className="text-xs text-gray-500">{idea.rationale}</p>
                      </div>
                      <button
                        onClick={() => handleGenerate(idx, idea)}
                        disabled={generatingIdx !== null}
                        className="flex-shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-brand-600 hover:bg-brand-700 text-white text-xs font-medium disabled:opacity-50 transition-colors"
                      >
                        {generatingIdx === idx
                          ? <Loader2 size={11} className="animate-spin" />
                          : <Play size={11} />
                        }
                        {generatingIdx === idx ? 'Generating…' : 'Generate'}
                      </button>
                    </div>

                    {/* Generated output */}
                    {generatedResults[idx] !== undefined && (
                      <div className="border-t border-gray-100 bg-gray-50 p-3.5">
                        <div className="flex items-center gap-2 mb-2">
                          <CheckCircle2 size={11} className="text-emerald-500" />
                          <span className="text-[10px] font-semibold text-emerald-600 uppercase tracking-wider">Generated</span>
                        </div>
                        <pre className="text-xs text-gray-700 whitespace-pre-wrap font-sans leading-relaxed max-h-48 overflow-y-auto">
                          {generatedResults[idx]}
                        </pre>
                        <div className="mt-3 flex gap-2">
                          <Link
                            href="/dashboard/content/new"
                            className="btn-secondary text-xs flex items-center gap-1"
                          >
                            <FileText size={10} /> Open in editor
                          </Link>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right col */}
        <div className="space-y-5">

          {/* X + Instagram Growth Status */}
          <div className="grid grid-cols-2 gap-3">
            {/* X card */}
            <Link
              href="/dashboard/growth/x-test"
              className="group block bg-slate-900 rounded-xl p-4 hover:bg-slate-800 transition-colors border border-slate-800"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="w-7 h-7 bg-white rounded-lg flex items-center justify-center">
                  <Twitter size={13} className="text-slate-900" />
                </div>
                <div className={`w-2 h-2 rounded-full ${xExperiment?.stage === 'active' ? 'bg-green-400' : 'bg-slate-600'}`} />
              </div>
              <p className="text-white text-xs font-semibold">X Growth</p>
              {xExperiment ? (
                <div className="mt-1 space-y-0.5">
                  <p className="text-slate-400 text-[10px]">{xExperiment.niche} · {xExperiment.stage}</p>
                  <p className="text-slate-300 text-[10px]">{xExperiment.current_followers} followers · {xExperiment.posts_published} posts</p>
                </div>
              ) : (
                <p className="text-slate-500 text-[10px] mt-1">No active experiment</p>
              )}
              <p className="text-slate-600 text-[10px] mt-2 group-hover:text-slate-400">
                {xExperiment ? 'View experiment →' : 'Start X growth →'}
              </p>
            </Link>

            {/* Instagram card */}
            <Link
              href="/dashboard/growth/instagram"
              className="group block rounded-xl p-4 hover:opacity-90 transition-opacity border"
              style={{ background: 'linear-gradient(135deg, #fdf2f8, #faf5ff)', borderColor: '#fbcfe8' }}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="w-7 h-7 rounded-lg flex items-center justify-center" style={{ background: 'linear-gradient(135deg, #ec4899, #a855f7)' }}>
                  <Instagram size={13} className="text-white" />
                </div>
                <div className={`w-2 h-2 rounded-full ${igExperiment?.stage === 'active' ? 'bg-green-400' : 'bg-pink-200'}`} />
              </div>
              <p className="text-gray-900 text-xs font-semibold">Instagram Growth</p>
              {igExperiment ? (
                <div className="mt-1 space-y-0.5">
                  <p className="text-gray-500 text-[10px]">{igExperiment.niche} · {igExperiment.stage}</p>
                  <p className="text-gray-600 text-[10px]">{igExperiment.current_followers} followers · {igExperiment.posts_drafted} concepts</p>
                </div>
              ) : (
                <p className="text-pink-400 text-[10px] mt-1">No active experiment</p>
              )}
              <p className="text-pink-400 text-[10px] mt-2 group-hover:text-pink-600">
                {igExperiment ? 'View experiment →' : 'Start IG growth →'}
              </p>
            </Link>
          </div>

          {/* Growth loop status */}
          <div className="card p-5">
            <div className="flex items-center gap-2 mb-4">
              <Cpu size={14} className="text-indigo-500" />
              <h2 className="section-title">Growth Loop Status</h2>
            </div>
            <div className="space-y-3">
              {[
                { label: 'Brand Intelligence', status: 'active', detail: `${brand?.niche ?? 'Unknown'} niche` },
                { label: 'Trend Monitoring', status: topTrends.length > 0 ? 'active' : 'idle', detail: `${topTrends.length} trends` },
                { label: 'Content Pipeline', status: 'idle', detail: 'No items queued' },
                { label: 'Paid Campaigns', status: 'idle', detail: 'Draft mode' },
                { label: 'Learning Loop', status: 'idle', detail: 'Awaiting outcomes' },
              ].map(step => (
                <div key={step.label} className="flex items-center gap-3">
                  <div className={`w-2 h-2 rounded-full flex-shrink-0 ${
                    step.status === 'active' ? 'bg-emerald-500 shadow-sm shadow-emerald-200' : 'bg-gray-300'
                  }`} />
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-gray-800">{step.label}</p>
                    <p className="text-[10px] text-gray-400">{step.detail}</p>
                  </div>
                  <span className={`text-[10px] font-medium ${
                    step.status === 'active' ? 'text-emerald-600' : 'text-gray-400'
                  }`}>
                    {step.status === 'active' ? 'Active' : 'Idle'}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Quick actions */}
          <div className="card p-5">
            <h2 className="section-title mb-3">Quick Actions</h2>
            <div className="space-y-1.5">
              {[
                { label: 'Create content brief', href: '/dashboard/content/new', icon: FileText, color: 'text-violet-500' },
                { label: 'Promote my site', href: '/dashboard/campaigns?promote=1', icon: MonitorPlay, color: 'text-indigo-500' },
                { label: 'View experiments', href: '/dashboard/experiments', icon: BarChart2, color: 'text-emerald-500' },
                { label: 'Pending approvals', href: '/dashboard/approvals', icon: Clock, color: 'text-amber-500' },
              ].map(action => (
                <Link
                  key={action.href}
                  href={action.href}
                  className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-gray-50 transition-colors group"
                >
                  <action.icon size={13} className={`${action.color} flex-shrink-0`} />
                  <span className="text-sm text-gray-700 group-hover:text-gray-900 flex-1">{action.label}</span>
                  <ChevronRight size={11} className="text-gray-300 group-hover:text-gray-500 transition-colors" />
                </Link>
              ))}
            </div>
          </div>

          {/* Top recommendations */}
          {(brand?.top_recommendations ?? []).length > 0 && (
            <div className="card p-5">
              <div className="flex items-center justify-between mb-3">
                <h2 className="section-title">AI Recommendations</h2>
                <Link href="/dashboard/trends" className="text-xs text-brand-600 hover:text-brand-700">
                  View all
                </Link>
              </div>
              <div className="space-y-2.5">
                {(brand?.top_recommendations ?? []).slice(0, 3).map((rec, i) => (
                  <div key={i} className="flex items-start gap-2">
                    <div className="w-5 h-5 rounded-full bg-brand-100 flex items-center justify-center flex-shrink-0 mt-0.5">
                      <span className="text-brand-700 text-[9px] font-bold">{i + 1}</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs text-gray-800 leading-snug">{rec.title}</p>
                      <span className="text-[10px] text-gray-400">{rec.category.replace(/_/g, ' ')}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

        </div>
      </div>

    </div>
  )
}

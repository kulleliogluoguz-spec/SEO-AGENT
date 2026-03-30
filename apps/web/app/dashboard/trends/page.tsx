'use client'

import { useState, useEffect } from 'react'
import { TrendingUp, Flame, Search, RefreshCw, ArrowUpRight, Clock, Tag } from 'lucide-react'
import { apiFetch } from '@/lib/apiFetch'

interface Trend {
  id: string
  keyword: string
  momentum_score: number
  volume_current: number
  volume_prior: number
  relevance_score: number
  evidence?: { sources?: string[] }
  created_at?: string
}

// Fallback demo data used when no brand profile exists yet
const DEMO_TRENDS: Trend[] = [
  {
    id: '1',
    keyword: 'AI search generative experience',
    momentum_score: 0.82,
    volume_current: 1240,
    volume_prior: 680,
    relevance_score: 0.91,
    evidence: { sources: ['techcrunch.com', 'searchengineland.com', 'moz.com'] },
  },
  {
    id: '2',
    keyword: 'answer engine optimization',
    momentum_score: 0.74,
    volume_current: 890,
    volume_prior: 510,
    relevance_score: 0.85,
    evidence: { sources: ['semrush.com', 'ahrefs.com'] },
  },
  {
    id: '3',
    keyword: 'llm seo strategy',
    momentum_score: 0.68,
    volume_current: 640,
    volume_prior: 380,
    relevance_score: 0.78,
    evidence: { sources: ['searchengineland.com', 'backlinko.com', 'neilpatel.com'] },
  },
  {
    id: '4',
    keyword: 'zero-click search',
    momentum_score: 0.57,
    volume_current: 3200,
    volume_prior: 2040,
    relevance_score: 0.72,
    evidence: { sources: ['searchengineland.com', 'wordstream.com'] },
  },
  {
    id: '5',
    keyword: 'brand entity signals',
    momentum_score: 0.51,
    volume_current: 420,
    volume_prior: 278,
    relevance_score: 0.68,
    evidence: { sources: ['kalicube.com', 'brightlocal.com'] },
  },
  {
    id: '6',
    keyword: 'structured data schema org',
    momentum_score: 0.44,
    volume_current: 2100,
    volume_prior: 1460,
    relevance_score: 0.63,
    evidence: { sources: ['schema.org', 'google.com/search/docs'] },
  },
  {
    id: '7',
    keyword: 'topical authority clusters',
    momentum_score: 0.39,
    volume_current: 760,
    volume_prior: 548,
    relevance_score: 0.58,
    evidence: { sources: ['koray.us', 'ahrefs.com'] },
  },
  {
    id: '8',
    keyword: 'content pruning strategy',
    momentum_score: 0.31,
    volume_current: 890,
    volume_prior: 680,
    relevance_score: 0.52,
    evidence: { sources: ['moz.com', 'seoclarity.net'] },
  },
]

function momentumLabel(score: number): { label: string; cls: string } {
  if (score >= 0.7) return { label: 'Surging',    cls: 'badge-red'    }
  if (score >= 0.5) return { label: 'Rising',     cls: 'badge-yellow' }
  if (score >= 0.3) return { label: 'Emerging',   cls: 'badge-blue'   }
  return                    { label: 'Steady',     cls: 'badge-gray'   }
}

function MomentumBar({ value }: { value: number }) {
  const pct = Math.min(100, Math.round(value * 100))
  const color = value >= 0.7 ? 'bg-red-400' : value >= 0.5 ? 'bg-amber-400' : value >= 0.3 ? 'bg-blue-400' : 'bg-gray-300'
  return (
    <div className="flex items-center gap-2 w-24">
      <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-gray-500 font-mono w-7 text-right">{pct}%</span>
    </div>
  )
}

type SortKey = 'momentum' | 'relevance' | 'volume'

export default function TrendsPage() {
  const [trends,   setTrends]   = useState<Trend[]>([])
  const [query,    setQuery]    = useState('')
  const [sortKey,  setSortKey]  = useState<SortKey>('momentum')
  const [loading,  setLoading]  = useState(true)
  const [detected, setDetected] = useState<string>('just now')

  useEffect(() => {
    async function load() {
      try {
        const data = await apiFetch<{ trends: any[] }>('/api/v1/brand/trends')
        const raw = data.trends ?? []
        const normalized: Trend[] = raw.map((t: any, i: number) => ({
          id: String(i),
          keyword: t.keyword ?? t.title ?? '',
          momentum_score: t.momentum_score ?? 0,
          volume_current: t.volume_current ?? t.volume ?? 0,
          volume_prior: t.volume_prior ?? 0,
          relevance_score: t.relevance_score ?? t.brand_relevance ?? 0,
          evidence: t.evidence,
        }))
        setTrends(normalized.length > 0 ? normalized : DEMO_TRENDS)
      } catch {
        setTrends(DEMO_TRENDS)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const filtered = trends
    .filter(t => !query || t.keyword.toLowerCase().includes(query.toLowerCase()))
    .sort((a, b) => {
      if (sortKey === 'momentum')  return b.momentum_score  - a.momentum_score
      if (sortKey === 'relevance') return b.relevance_score - a.relevance_score
      return b.volume_current - a.volume_current
    })

  async function handleRefresh() {
    setLoading(true)
    try {
      const data = await apiFetch<{ trends: any[] }>('/api/v1/brand/trends')
      const raw = data.trends ?? []
      const normalized: Trend[] = raw.map((t: any, i: number) => ({
        id: String(i),
        keyword: t.keyword ?? t.title ?? '',
        momentum_score: t.momentum_score ?? 0,
        volume_current: t.volume_current ?? t.volume ?? 0,
        volume_prior: t.volume_prior ?? 0,
        relevance_score: t.relevance_score ?? t.brand_relevance ?? 0,
        evidence: t.evidence,
      }))
      setTrends(normalized.length > 0 ? normalized : DEMO_TRENDS)
    } catch {
      // keep existing trends
    } finally {
      setDetected('just now')
      setLoading(false)
    }
  }

  const topMomentum = [...trends].sort((a,b) => b.momentum_score - a.momentum_score)[0]

  return (
    <div className="space-y-6">

      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title flex items-center gap-2">
            Trend Feed
            <span className="badge-red text-[10px]">LIVE</span>
          </h1>
          <p className="page-subtitle">Real-time keyword momentum from connected sources</p>
        </div>
        <button onClick={handleRefresh} disabled={loading} className="btn-secondary">
          <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
          {loading ? 'Detecting…' : 'Detect Now'}
        </button>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-4">
        <div className="card-stat">
          <p className="text-xs font-medium text-gray-400 uppercase tracking-widest">Trends Detected</p>
          <p className="text-2xl font-bold text-gray-900 mt-1.5">{trends.length}</p>
          <p className="text-xs text-gray-400 mt-1 flex items-center gap-1">
            <Clock size={10} /> Updated {detected}
          </p>
        </div>
        <div className="card-stat">
          <p className="text-xs font-medium text-gray-400 uppercase tracking-widest">Top Momentum</p>
          <p className="text-lg font-bold text-gray-900 mt-1.5 truncate">{topMomentum?.keyword}</p>
          <p className="text-xs text-emerald-600 mt-1 font-medium">
            +{Math.round((topMomentum?.momentum_score ?? 0) * 100)}% velocity
          </p>
        </div>
        <div className="card-stat">
          <p className="text-xs font-medium text-gray-400 uppercase tracking-widest">Brand Relevance</p>
          <p className="text-2xl font-bold text-gray-900 mt-1.5">
            {Math.round(trends.filter(t => t.relevance_score >= 0.7).length / trends.length * 100)}%
          </p>
          <p className="text-xs text-gray-400 mt-1">of trends are brand-relevant</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-xs">
          <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            className="input pl-8 text-sm h-9"
            placeholder="Filter trends…"
            value={query}
            onChange={e => setQuery(e.target.value)}
          />
        </div>
        <div className="flex items-center gap-1 bg-gray-100 rounded-lg p-1">
          {(['momentum', 'relevance', 'volume'] as SortKey[]).map(k => (
            <button
              key={k}
              onClick={() => setSortKey(k)}
              className={`px-3 py-1 rounded-md text-xs font-medium transition-all ${
                sortKey === k
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              {k.charAt(0).toUpperCase() + k.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Trend list */}
      <div className="card divide-y divide-gray-100">
        {filtered.length === 0 ? (
          <div className="text-center py-16">
            <TrendingUp size={28} className="mx-auto mb-3 text-gray-200" />
            <p className="text-sm text-gray-400">No trends match your filter</p>
          </div>
        ) : filtered.map((trend, idx) => {
          const { label, cls } = momentumLabel(trend.momentum_score)
          const growth = trend.volume_prior > 0
            ? Math.round(((trend.volume_current - trend.volume_prior) / trend.volume_prior) * 100)
            : 0

          return (
            <div key={trend.id} className="flex items-center gap-4 px-5 py-4 hover:bg-gray-50/60 transition-colors">
              {/* Rank */}
              <span className="text-xs font-mono text-gray-300 w-5 flex-shrink-0">#{idx + 1}</span>

              {/* Flame for top 3 */}
              <div className="w-7 h-7 rounded-lg bg-gray-50 flex items-center justify-center flex-shrink-0 border border-gray-100">
                {idx < 3
                  ? <Flame size={13} className={idx === 0 ? 'text-red-500' : idx === 1 ? 'text-orange-400' : 'text-amber-400'} />
                  : <Tag size={12} className="text-gray-300" />
                }
              </div>

              {/* Keyword + sources */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-gray-900">{trend.keyword}</span>
                  <span className={`badge ${cls} text-[10px]`}>{label}</span>
                </div>
                {trend.evidence?.sources && (
                  <div className="flex items-center gap-1 mt-0.5">
                    {trend.evidence.sources.slice(0, 3).map(s => (
                      <span key={s} className="text-[10px] text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded">{s}</span>
                    ))}
                  </div>
                )}
              </div>

              {/* Volume */}
              <div className="hidden md:flex flex-col items-end flex-shrink-0 w-24">
                <span className="text-sm font-semibold text-gray-800">{trend.volume_current.toLocaleString()}</span>
                <span className={`text-xs font-medium ${growth >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                  {growth >= 0 ? '+' : ''}{growth}%
                </span>
              </div>

              {/* Momentum bar */}
              <div className="hidden lg:flex items-center gap-1 flex-shrink-0">
                <MomentumBar value={trend.momentum_score} />
              </div>

              {/* Relevance */}
              <div className="flex-shrink-0 w-16 text-right">
                <span className={`text-sm font-medium ${
                  trend.relevance_score >= 0.7
                    ? 'text-emerald-600'
                    : trend.relevance_score >= 0.5
                    ? 'text-amber-500'
                    : 'text-gray-400'
                }`}>
                  {Math.round(trend.relevance_score * 100)}%
                </span>
                <p className="text-[10px] text-gray-400">relevance</p>
              </div>

              {/* Action */}
              <button className="flex-shrink-0 p-1.5 rounded-lg hover:bg-brand-50 text-gray-300 hover:text-brand-600 transition-colors">
                <ArrowUpRight size={14} />
              </button>
            </div>
          )
        })}
      </div>

    </div>
  )
}

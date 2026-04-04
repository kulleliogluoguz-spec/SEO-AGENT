'use client'

import { useEffect, useState, useCallback, useRef } from 'react'
import {
  Twitter, Loader2, AlertCircle, CheckCircle2,
  RefreshCw, Zap, TrendingUp, BarChart, Brain,
  ArrowUp, ArrowDown, Minus, Play, Heart, MessageCircle,
  Repeat2, Eye, Calendar, Shield, XCircle
} from 'lucide-react'
import Link from 'next/link'
import { apiFetch, ApiError } from '@/lib/apiFetch'

// ── Types ─────────────────────────────────────────────────────────────────────

interface FollowerPoint { date: string; value: number }
interface GrowthData {
  current_followers: number
  delta_7d: number | null
  delta_30d: number | null
  has_data: boolean
  points: FollowerPoint[]
}

interface PostPerf {
  post_id: string
  content_type: string
  topic?: string
  text_preview: string
  impressions: number
  likes: number
  comments: number
  reposts: number
  engagement_score: number
  published_at?: string
}

interface LearningPattern {
  content_type: string
  outcome: string
  reason?: string
}

interface NextAction {
  action: string
  reason: string
  priority: string
}

interface XDashboard {
  follower_chart: GrowthData
  top_posts: PostPerf[]
  worst_posts: PostPerf[]
  promoted_patterns: LearningPattern[]
  suppressed_patterns: LearningPattern[]
  next_actions: NextAction[]
  // backend returns { experiment: { id, niche, stage, posts_drafted } | null }
  experiment_id?: string
  experiment?: { id: string; niche: string | null; stage: string | null; posts_drafted: number } | null
  posts_measured: number
  avg_engagement_rate: number
  strategy_success_rate: number
}

interface SocialHealth {
  channel: string
  status: string
  ready: boolean
  message: string
  label: string
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function DeltaBadge({ value, suffix = '' }: { value: number | null; suffix?: string }) {
  if (value === null) return <span className="text-xs text-gray-400">—</span>
  const abs = Math.abs(value)
  if (value > 0) return (
    <span className="flex items-center gap-0.5 text-xs font-semibold text-emerald-600">
      <ArrowUp size={10} /> +{abs.toLocaleString()}{suffix}
    </span>
  )
  if (value < 0) return (
    <span className="flex items-center gap-0.5 text-xs font-semibold text-red-500">
      <ArrowDown size={10} /> {value.toLocaleString()}{suffix}
    </span>
  )
  return <span className="flex items-center gap-0.5 text-xs text-gray-400"><Minus size={10} /> 0</span>
}

function FollowerChart({ points }: { points: FollowerPoint[] }) {
  if (!points || points.length < 2) return (
    <div className="h-28 flex items-center justify-center text-xs text-gray-300">
      Not enough data for chart
    </div>
  )
  const values = points.map(p => p.value)
  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = max - min || 1
  const w = 100 / (points.length - 1)
  const pathD = points.map((p, i) => {
    const x = i * w
    const y = 100 - ((p.value - min) / range) * 80 - 10
    return `${i === 0 ? 'M' : 'L'} ${x.toFixed(2)} ${y.toFixed(2)}`
  }).join(' ')
  const areaD = `${pathD} L 100 100 L 0 100 Z`
  return (
    <svg viewBox="0 0 100 100" className="w-full h-28" preserveAspectRatio="none">
      <defs>
        <linearGradient id="xChartGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#000" stopOpacity="0.12" />
          <stop offset="100%" stopColor="#000" stopOpacity="0.01" />
        </linearGradient>
      </defs>
      <path d={areaD} fill="url(#xChartGrad)" />
      <path d={pathD} fill="none" stroke="#111827" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function PostCard({ post, rank }: { post: PostPerf; rank?: number }) {
  const engRate = post.impressions > 0
    ? ((post.likes + post.comments + post.reposts) / post.impressions * 100).toFixed(1)
    : '0.0'
  return (
    <div className="p-4 border border-gray-100 rounded-xl hover:border-gray-200 hover:bg-gray-50/50 transition-all">
      {rank !== undefined && (
        <span className="text-[9px] font-bold text-gray-300 mb-1 block">#{rank + 1} · {post.content_type.replace(/_/g, ' ')}</span>
      )}
      <p className="text-xs text-gray-700 leading-relaxed line-clamp-3 mb-3">{post.text_preview}</p>
      <div className="flex items-center gap-3 text-[11px] text-gray-500">
        <span className="flex items-center gap-1"><Eye size={10} /> {post.impressions.toLocaleString()}</span>
        <span className="flex items-center gap-1"><Heart size={10} /> {post.likes}</span>
        <span className="flex items-center gap-1"><MessageCircle size={10} /> {post.comments}</span>
        <span className="flex items-center gap-1"><Repeat2 size={10} /> {post.reposts}</span>
        <span className="ml-auto font-bold text-brand-600">{engRate}%</span>
      </div>
    </div>
  )
}

function PriorityDot({ priority }: { priority: string }) {
  const colors: Record<string, string> = { high: 'bg-red-500', medium: 'bg-amber-400', low: 'bg-gray-300' }
  return <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 mt-1.5 ${colors[priority] ?? colors.low}`} />
}

// ── Connect panel ─────────────────────────────────────────────────────────────

function ConnectPanel() {
  const [loading, setLoading] = useState(false)
  async function handleConnect() {
    setLoading(true)
    try {
      const data = await apiFetch<{ authorization_url: string }>('/api/v1/auth/x/authorize')
      if (data.authorization_url) window.location.href = data.authorization_url
    } catch { setLoading(false) }
  }
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-6 text-center max-w-lg mx-auto">
      <div className="w-20 h-20 bg-black rounded-3xl flex items-center justify-center shadow-lg">
        <Twitter size={36} className="text-white" />
      </div>
      <div>
        <h2 className="text-xl font-bold text-gray-900">Connect Your X Account</h2>
        <p className="text-sm text-gray-500 mt-2 leading-relaxed">
          Connect X to generate trend-aware posts, track follower growth, auto-publish content, and measure what works.
        </p>
      </div>
      <div className="flex flex-col items-center gap-3 w-full">
        <button
          onClick={handleConnect}
          disabled={loading}
          className="w-full max-w-xs flex items-center justify-center gap-2 px-8 py-3.5 bg-black text-white rounded-xl text-sm font-bold hover:bg-gray-800 transition-colors shadow-sm disabled:opacity-50"
        >
          {loading ? <Loader2 size={16} className="animate-spin" /> : <Zap size={16} />}
          {loading ? 'Redirecting to X…' : 'Connect X Account'}
        </button>
        <Link href="/dashboard/connectors" className="text-xs text-gray-400 hover:text-gray-600 transition-colors">
          Or set up manually with tokens →
        </Link>
      </div>
      <div className="grid grid-cols-3 gap-3 w-full max-w-sm mt-2">
        {[
          { icon: TrendingUp, label: 'Trend posts', desc: 'Generate from live trends' },
          { icon: BarChart, label: 'Growth tracking', desc: 'Followers & engagement' },
          { icon: Brain, label: 'AI learning', desc: 'Learns what works' },
        ].map((f, i) => (
          <div key={i} className="p-3 bg-gray-50 rounded-xl text-center">
            <f.icon size={16} className="text-gray-400 mx-auto mb-1.5" />
            <p className="text-[11px] font-semibold text-gray-700">{f.label}</p>
            <p className="text-[10px] text-gray-400 mt-0.5">{f.desc}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Generate panel ────────────────────────────────────────────────────────────

function GeneratePanel({ experimentId, onDone }: { experimentId?: string; onDone: () => void }) {
  const [topic, setTopic] = useState('')
  const [count, setCount] = useState(5)
  const [loading, setLoading] = useState(false)
  const [msg, setMsg] = useState<{ type: 'ok' | 'err'; text: string } | null>(null)

  async function go() {
    if (!experimentId) { setMsg({ type: 'err', text: 'No active experiment. Set up your brand niche first.' }); return }
    setLoading(true); setMsg(null)
    try {
      await apiFetch(`/api/v1/growth/experiments/${experimentId}/generate-posts`, {
        method: 'POST',
        body: JSON.stringify({ count, topic_override: topic.trim() || undefined }),
      })
      setMsg({ type: 'ok', text: `${count} posts drafted and ready for review.` })
      setTopic(''); onDone()
    } catch (e) {
      setMsg({ type: 'err', text: e instanceof ApiError ? e.message : 'Generation failed' })
    } finally { setLoading(false) }
  }

  return (
    <div className="card p-5">
      <h3 className="text-sm font-semibold text-gray-900 flex items-center gap-2 mb-4">
        <Zap size={14} className="text-brand-500" /> Generate Posts
      </h3>
      <div className="space-y-3">
        <div>
          <label className="input-label">Topic override <span className="text-gray-400 font-normal">(optional — uses live trends by default)</span></label>
          <input
            className="input"
            placeholder="e.g. SaaS pricing, AI productivity, remote work habits"
            value={topic}
            onChange={e => setTopic(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && go()}
          />
        </div>
        <div className="flex items-center gap-3">
          <select className="input w-32 flex-shrink-0" value={count} onChange={e => setCount(Number(e.target.value))}>
            {[3, 5, 10, 15].map(n => <option key={n} value={n}>{n} posts</option>)}
          </select>
          <button onClick={go} disabled={loading} className="btn-primary flex-1 flex items-center justify-center gap-2">
            {loading ? <Loader2 size={14} className="animate-spin" /> : <Zap size={14} />}
            {loading ? 'Generating…' : `Generate ${count} Posts`}
          </button>
        </div>
      </div>
      {msg && (
        <div className={`mt-3 flex items-center gap-2 text-xs px-3 py-2 rounded-lg ${msg.type === 'ok' ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'}`}>
          {msg.type === 'ok' ? <CheckCircle2 size={12} /> : <AlertCircle size={12} />}
          {msg.text}
          {msg.type === 'ok' && (
            <Link href="/dashboard/content/queue" className="ml-auto font-semibold underline whitespace-nowrap">Review →</Link>
          )}
        </div>
      )}
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function XGrowthPage() {
  const [data, setData] = useState<XDashboard | null>(null)
  const [health, setHealth] = useState<SocialHealth | null>(null)
  const [loading, setLoading] = useState(true)
  const [fetchError, setFetchError] = useState<string | null>(null)
  const [pageError, setPageError] = useState<string | null>(null)
  const mountedRef = useRef(true)

  const load = useCallback(async () => {
    setLoading(true); setFetchError(null); setPageError(null)
    let healthErr = false
    try {
      const [dash, healthRes] = await Promise.race([
        Promise.all([
          apiFetch<XDashboard>('/api/v1/growth/dashboard/x').catch(() => null),
          apiFetch<{ channels: SocialHealth[] }>('/api/v1/connectors/social/health')
            .then(d => d.channels?.find(c => c.channel === 'x') ?? null)
            .catch(() => { healthErr = true; return null as SocialHealth | null }),
        ]),
        new Promise<never>((_, reject) =>
          setTimeout(() => reject(new Error('timeout')), 10_000)
        ),
      ])
      if (!mountedRef.current) return
      if (healthErr) {
        setPageError('Could not reach the backend API — make sure the server is running on port 8000.')
      } else {
        setData(dash)
        setHealth(healthRes)
      }
    } catch (e) {
      if (!mountedRef.current) return
      if (e instanceof Error && e.message === 'timeout') {
        setPageError('Request timed out — check that the backend is running on port 8000.')
      } else if (!(e instanceof ApiError && e.status === 401)) {
        setPageError('Failed to load dashboard — please try again.')
      }
    } finally {
      if (mountedRef.current) setLoading(false)
    }
  }, [])

  useEffect(() => {
    mountedRef.current = true
    load()
    return () => { mountedRef.current = false }
  }, [load])

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="text-center">
        <Loader2 className="w-7 h-7 animate-spin text-gray-400 mx-auto mb-3" />
        <p className="text-sm text-gray-400">Loading X dashboard…</p>
      </div>
    </div>
  )

  if (pageError) return (
    <div className="flex flex-col items-center justify-center h-64 gap-4 text-center">
      <XCircle className="w-8 h-8 text-red-400" />
      <div>
        <p className="text-sm font-medium text-gray-800">Dashboard unavailable</p>
        <p className="text-xs text-gray-500 mt-1 max-w-sm">{pageError}</p>
      </div>
      <button
        onClick={load}
        className="flex items-center gap-1.5 px-4 py-2 text-xs font-medium bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
      >
        <RefreshCw className="w-3.5 h-3.5" /> Try again
      </button>
    </div>
  )

  if (!health?.ready) return <ConnectPanel />

  const growth = data?.follower_chart

  return (
    <div className="space-y-6">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-black rounded-xl flex items-center justify-center shadow-sm">
            <Twitter size={18} className="text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-gray-900">X Account Growth</h1>
            <p className="text-xs text-gray-500 flex items-center gap-1.5">
              <CheckCircle2 size={10} className="text-emerald-500" /> {health.message || 'Connected'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={load} className="p-2 rounded-lg hover:bg-gray-100 text-gray-400 transition-colors" title="Refresh">
            <RefreshCw size={14} />
          </button>
          <Link href="/dashboard/settings" className="btn-secondary text-xs">
            <Shield size={12} /> Autonomy
          </Link>
          <Link href="/dashboard/connectors" className="btn-secondary text-xs">
            Manage connection
          </Link>
        </div>
      </div>

      {fetchError && (
        <div className="flex items-center gap-3 p-4 bg-amber-50 border border-amber-200 rounded-xl text-sm text-amber-800">
          <AlertCircle size={15} className="flex-shrink-0 text-amber-500" />
          {fetchError} — Growth metrics may not load until posts have been published.
          <button onClick={load} className="ml-auto text-xs underline font-medium">Retry</button>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          {
            label: 'Followers',
            value: growth?.current_followers?.toLocaleString() ?? '—',
            sub: <div className="flex items-center gap-2 mt-1">
              <span className="text-[10px] text-gray-400">7d</span> <DeltaBadge value={growth?.delta_7d ?? null} />
              <span className="text-[10px] text-gray-400">30d</span> <DeltaBadge value={growth?.delta_30d ?? null} />
            </div>,
          },
          {
            label: 'Posts Measured',
            value: data?.posts_measured ?? 0,
            sub: <p className="text-[10px] text-gray-400 mt-1">With real engagement data</p>,
          },
          {
            label: 'Avg Engagement',
            value: data?.avg_engagement_rate !== undefined ? `${(data.avg_engagement_rate * 100).toFixed(1)}%` : '—',
            sub: <p className="text-[10px] text-gray-400 mt-1">(likes + comments + reposts) / impressions</p>,
          },
          {
            label: 'Strategy Win Rate',
            value: data?.strategy_success_rate !== undefined ? `${Math.round(data.strategy_success_rate * 100)}%` : '—',
            sub: <p className="text-[10px] text-gray-400 mt-1">Posts above 3% engagement</p>,
          },
        ].map(s => (
          <div key={s.label} className="card p-4">
            <p className="text-[11px] font-medium text-gray-500 mb-1">{s.label}</p>
            <p className="text-2xl font-bold text-gray-900">{s.value}</p>
            {s.sub}
          </div>
        ))}
      </div>

      {/* Follower chart */}
      <div className="card p-5">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-semibold text-gray-900 flex items-center gap-2">
            <TrendingUp size={14} className="text-gray-700" /> Follower Growth (30d)
          </h3>
          {growth?.current_followers && (
            <span className="text-sm font-bold text-gray-900">{growth.current_followers.toLocaleString()} total</span>
          )}
        </div>
        {growth?.has_data ? (
          <FollowerChart points={growth.points} />
        ) : (
          <div className="h-28 flex items-center justify-center text-center">
            <div>
              <BarChart size={24} className="text-gray-200 mx-auto mb-2" />
              <p className="text-xs text-gray-400">No follower data yet</p>
              <p className="text-[10px] text-gray-300 mt-0.5">Collected hourly after first post</p>
            </div>
          </div>
        )}
      </div>

      {/* Generate + Recommendations */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <GeneratePanel experimentId={data?.experiment?.id ?? data?.experiment_id} onDone={load} />

        <div className="card p-5">
          <h3 className="text-sm font-semibold text-gray-900 flex items-center gap-2 mb-4">
            <Brain size={14} className="text-violet-500" /> AI Recommendations
          </h3>
          {(data?.next_actions ?? []).length === 0 ? (
            <div className="flex flex-col items-center py-8 gap-2 text-center">
              <Play size={20} className="text-gray-200" />
              <p className="text-xs text-gray-400">Generate and publish posts to get personalized recommendations</p>
            </div>
          ) : (
            <div className="space-y-2">
              {data!.next_actions.slice(0, 5).map((a, i) => (
                <div key={i} className="flex items-start gap-2.5 p-3 rounded-xl bg-gray-50 hover:bg-gray-100 transition-colors">
                  <PriorityDot priority={a.priority} />
                  <div>
                    <p className="text-xs font-semibold text-gray-800">{a.action}</p>
                    <p className="text-[10px] text-gray-500 mt-0.5">{a.reason}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Post performance + Learning */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="card p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-gray-900 flex items-center gap-2">
              <ArrowUp size={14} className="text-emerald-500" /> Top Performing Posts
            </h3>
            <Link href="/dashboard/content/queue" className="text-xs text-brand-600">All posts →</Link>
          </div>
          {(data?.top_posts ?? []).length === 0 ? (
            <div className="flex flex-col items-center py-10 gap-2 text-center">
              <Play size={22} className="text-gray-200" />
              <p className="text-xs text-gray-400">No published posts yet</p>
              <p className="text-[10px] text-gray-300">Generate posts and publish to track performance</p>
            </div>
          ) : (
            <div className="space-y-3">
              {data!.top_posts.slice(0, 3).map((p, i) => <PostCard key={p.post_id} post={p} rank={i} />)}
            </div>
          )}
        </div>

        <div className="card p-5">
          <h3 className="text-sm font-semibold text-gray-900 flex items-center gap-2 mb-4">
            <Brain size={14} className="text-violet-500" /> Learning Patterns
          </h3>
          {(data?.promoted_patterns ?? []).length === 0 && (data?.suppressed_patterns ?? []).length === 0 ? (
            <div className="flex flex-col items-center py-10 gap-2 text-center">
              <Brain size={22} className="text-gray-200" />
              <p className="text-xs text-gray-400">Patterns build over time</p>
              <p className="text-[10px] text-gray-300">Publish posts and the AI learns what resonates</p>
            </div>
          ) : (
            <div className="space-y-2">
              {(data?.promoted_patterns ?? []).slice(0, 3).map((p, i) => (
                <div key={`up-${i}`} className="flex items-start gap-2.5 p-2.5 bg-emerald-50 border border-emerald-100 rounded-xl">
                  <ArrowUp size={10} className="text-emerald-500 mt-1 flex-shrink-0" />
                  <div>
                    <p className="text-[11px] font-semibold text-emerald-800 capitalize">{p.content_type.replace(/_/g, ' ')}</p>
                    {p.reason && <p className="text-[10px] text-emerald-600">{p.reason}</p>}
                  </div>
                  <span className="ml-auto text-[9px] font-bold bg-emerald-100 text-emerald-600 px-1.5 py-0.5 rounded-full">↑ boost</span>
                </div>
              ))}
              {(data?.suppressed_patterns ?? []).slice(0, 2).map((p, i) => (
                <div key={`dn-${i}`} className="flex items-start gap-2.5 p-2.5 bg-red-50 border border-red-100 rounded-xl">
                  <ArrowDown size={10} className="text-red-400 mt-1 flex-shrink-0" />
                  <div>
                    <p className="text-[11px] font-semibold text-red-800 capitalize">{p.content_type.replace(/_/g, ' ')}</p>
                    {p.reason && <p className="text-[10px] text-red-500">{p.reason}</p>}
                  </div>
                  <span className="ml-auto text-[9px] font-bold bg-red-100 text-red-500 px-1.5 py-0.5 rounded-full">↓ reduce</span>
                </div>
              ))}
            </div>
          )}
          <Link href="/dashboard/learning" className="mt-4 w-full flex items-center justify-center gap-1.5 py-2 text-xs font-medium text-gray-500 hover:text-gray-700 hover:bg-gray-50 rounded-lg transition-colors">
            View all learning insights →
          </Link>
        </div>
      </div>

      {/* Footer nav */}
      <div className="flex items-center gap-3 flex-wrap pb-2">
        <Link href="/dashboard/content/queue" className="btn-secondary text-xs">
          <Calendar size={12} /> Content queue
        </Link>
        <Link href="/dashboard/approvals" className="btn-secondary text-xs">
          <CheckCircle2 size={12} /> Approvals
        </Link>
        <Link href="/dashboard/trends" className="btn-secondary text-xs">
          <TrendingUp size={12} /> Browse trends
        </Link>
        <Link href="/dashboard/learning" className="btn-secondary text-xs">
          <Brain size={12} /> Learning
        </Link>
      </div>

    </div>
  )
}

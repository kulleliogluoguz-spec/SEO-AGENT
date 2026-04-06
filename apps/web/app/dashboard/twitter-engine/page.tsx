'use client'

import { useEffect, useState, useCallback } from 'react'
import {
  Twitter, Loader2, AlertCircle, CheckCircle2,
  RefreshCw, Zap, BarChart, Send, ListOrdered,
  Map, Clock, TrendingUp, XCircle,
} from 'lucide-react'
import Link from 'next/link'
import { apiFetch } from '@/lib/apiFetch'

// ── Types ────────────────────────────────────────────────────────────────────

interface HealthData {
  status: string
  message?: string
  instructions?: string[]
  publisher_status?: string
}

interface StatsData {
  queue: {
    pending: number
    approved: number
    posted: number
    rejected: number
    errored: number
  }
  this_month_posts: number
  monthly_limit: number
  remaining_this_month: number
  daily_safe_limit: number
  totals: { likes: number; retweets: number; impressions: number }
}

interface GenerateResult {
  generated: number
  items: Array<{ id: number; type: string; content: string; ai_score: number }>
  message?: string
  error?: string
  hint?: string
}

// ── Main Page ────────────────────────────────────────────────────────────────

export default function TwitterHubPage() {
  const [health, setHealth] = useState<HealthData | null>(null)
  const [stats, setStats] = useState<StatsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Generate form state
  const [niche, setNiche] = useState('')
  const [audience, setAudience] = useState('')
  const [count, setCount] = useState(5)
  const [includeThreads, setIncludeThreads] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [genResult, setGenResult] = useState<GenerateResult | null>(null)

  // Manual tweet state
  const [showManual, setShowManual] = useState(false)
  const [manualText, setManualText] = useState('')
  const [posting, setPosting] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [h, s] = await Promise.all([
        apiFetch<HealthData>('/api/v1/twitter/health').catch(() => ({ status: 'error', message: 'Backend unreachable' })),
        apiFetch<StatsData>('/api/v1/twitter/stats').catch(() => null),
      ])
      setHealth(h)
      setStats(s)
    } catch {
      setError('Failed to load Twitter Hub')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  // Load saved niche/audience from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('twitter_strategy')
    if (saved) {
      try {
        const data = JSON.parse(saved)
        if (data.niche) setNiche(data.niche)
        if (data.audience) setAudience(data.audience)
      } catch { /* ignore */ }
    }
  }, [])

  async function handleGenerate() {
    if (!niche.trim()) return
    setGenerating(true)
    setGenResult(null)
    try {
      const result = await apiFetch<GenerateResult>('/api/v1/twitter/generate', {
        method: 'POST',
        body: JSON.stringify({
          niche: niche.trim(),
          target_audience: audience.trim() || 'general audience',
          count,
          include_threads: includeThreads,
        }),
        timeoutMs: 180_000,
      })
      setGenResult(result)
      load() // refresh stats
    } catch (e) {
      setGenResult({ generated: 0, items: [], error: e instanceof Error ? e.message : 'Generation failed' })
    } finally {
      setGenerating(false)
    }
  }

  async function handleManualTweet(postNow: boolean) {
    if (!manualText.trim()) return
    setPosting(true)
    try {
      await apiFetch('/api/v1/twitter/tweet/manual', {
        method: 'POST',
        body: JSON.stringify({ content: manualText.trim(), post_now: postNow }),
      })
      setManualText('')
      setShowManual(false)
      load()
    } catch { /* ignore */ }
    finally { setPosting(false) }
  }

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="text-center">
        <Loader2 className="w-7 h-7 animate-spin text-gray-400 mx-auto mb-3" />
        <p className="text-sm text-gray-400">Loading Twitter Hub...</p>
      </div>
    </div>
  )

  if (error) return (
    <div className="flex flex-col items-center justify-center h-64 gap-4 text-center">
      <XCircle className="w-8 h-8 text-red-400" />
      <p className="text-sm text-gray-800">{error}</p>
      <button onClick={load} className="flex items-center gap-1.5 px-4 py-2 text-xs font-medium bg-gray-100 rounded-lg hover:bg-gray-200">
        <RefreshCw className="w-3.5 h-3.5" /> Try again
      </button>
    </div>
  )

  const isConnected = health?.status === 'connected'
  const q = stats?.queue

  return (
    <div className="space-y-6">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-black rounded-xl flex items-center justify-center shadow-sm">
            <Twitter size={18} className="text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-gray-900">Twitter Growth Engine</h1>
            <p className="text-xs text-gray-500 flex items-center gap-1.5">
              {isConnected ? (
                <><CheckCircle2 size={10} className="text-emerald-500" /> {health?.message}</>
              ) : (
                <><AlertCircle size={10} className="text-amber-500" /> {health?.message || health?.status}</>
              )}
            </p>
          </div>
        </div>
        <button onClick={load} className="p-2 rounded-lg hover:bg-gray-100 text-gray-400">
          <RefreshCw size={14} />
        </button>
      </div>

      {/* Setup instructions if not connected */}
      {health?.instructions && !isConnected && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-amber-800 mb-2">Setup Required</h3>
          <ul className="space-y-1">
            {health.instructions.map((step, i) => (
              <li key={i} className="text-xs text-amber-700">{step}</li>
            ))}
          </ul>
          <Link href="/dashboard/connectors" className="mt-3 inline-flex items-center gap-1.5 text-xs font-semibold text-amber-800 hover:underline">
            Or connect via Dashboard Connections →
          </Link>
        </div>
      )}

      {/* Stats Row */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
          {[
            { label: 'Pending', value: q?.pending ?? 0, color: 'text-amber-600', bg: 'bg-amber-50' },
            { label: 'Approved', value: q?.approved ?? 0, color: 'text-blue-600', bg: 'bg-blue-50' },
            { label: 'Posted', value: q?.posted ?? 0, color: 'text-emerald-600', bg: 'bg-emerald-50' },
            { label: 'Rejected', value: q?.rejected ?? 0, color: 'text-red-500', bg: 'bg-red-50' },
            { label: 'This Month', value: stats.this_month_posts, color: 'text-gray-800', bg: 'bg-gray-50' },
          ].map(s => (
            <div key={s.label} className={`${s.bg} rounded-xl p-4 text-center`}>
              <p className="text-[10px] font-medium text-gray-500 uppercase tracking-wider">{s.label}</p>
              <p className={`text-2xl font-bold ${s.color} mt-1`}>{s.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Monthly Usage Bar */}
      {stats && (
        <div className="card p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-gray-600">Monthly Usage</span>
            <span className="text-xs text-gray-400">{stats.this_month_posts} / {stats.monthly_limit} tweets</span>
          </div>
          <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-brand-500 rounded-full transition-all duration-500"
              style={{ width: `${Math.min(100, (stats.this_month_posts / stats.monthly_limit) * 100)}%` }}
            />
          </div>
          <p className="text-[10px] text-gray-400 mt-1">{stats.remaining_this_month} remaining this month</p>
        </div>
      )}

      {/* Generate Content Card */}
      <div className="card p-5">
        <h3 className="text-sm font-semibold text-gray-900 flex items-center gap-2 mb-4">
          <Zap size={14} className="text-brand-500" /> Generate Today&apos;s Content
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Niche *</label>
            <input
              className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-400"
              placeholder="e.g. AI tools for marketers"
              value={niche}
              onChange={e => setNiche(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Target Audience</label>
            <input
              className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-400"
              placeholder="e.g. startup founders, indie hackers"
              value={audience}
              onChange={e => setAudience(e.target.value)}
            />
          </div>
        </div>
        <div className="flex items-center gap-3 mt-3">
          <select
            className="px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/30"
            value={count}
            onChange={e => setCount(Number(e.target.value))}
          >
            {[3, 5, 7, 10].map(n => <option key={n} value={n}>{n} tweets</option>)}
          </select>
          <label className="flex items-center gap-1.5 text-xs text-gray-600 cursor-pointer">
            <input
              type="checkbox"
              checked={includeThreads}
              onChange={e => setIncludeThreads(e.target.checked)}
              className="rounded border-gray-300"
            />
            Include thread
          </label>
          <button
            onClick={handleGenerate}
            disabled={generating || !niche.trim()}
            className="ml-auto flex items-center gap-2 px-5 py-2.5 bg-black text-white rounded-lg text-sm font-semibold hover:bg-gray-800 disabled:opacity-40 transition-colors"
          >
            {generating ? <Loader2 size={14} className="animate-spin" /> : <Zap size={14} />}
            {generating ? 'Generating...' : 'Generate with AI'}
          </button>
        </div>

        {genResult && (
          <div className={`mt-4 flex items-center gap-2 text-xs px-4 py-3 rounded-lg ${
            genResult.error ? 'bg-red-50 text-red-700' : 'bg-emerald-50 text-emerald-700'
          }`}>
            {genResult.error ? <AlertCircle size={12} /> : <CheckCircle2 size={12} />}
            {genResult.error || genResult.message}
            {!genResult.error && (
              <Link href="/dashboard/twitter-engine/queue" className="ml-auto font-semibold underline whitespace-nowrap">
                Review Queue →
              </Link>
            )}
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Link href="/dashboard/twitter-engine/queue" className="card p-4 hover:bg-gray-50 transition-colors group text-center">
          <ListOrdered size={20} className="text-amber-500 mx-auto mb-2 group-hover:scale-110 transition-transform" />
          <p className="text-xs font-semibold text-gray-800">Review Queue</p>
          {q?.pending ? <p className="text-[10px] text-amber-600 font-medium mt-0.5">{q.pending} pending</p> : null}
        </Link>
        <Link href="/dashboard/twitter-engine/posted" className="card p-4 hover:bg-gray-50 transition-colors group text-center">
          <CheckCircle2 size={20} className="text-emerald-500 mx-auto mb-2 group-hover:scale-110 transition-transform" />
          <p className="text-xs font-semibold text-gray-800">Posted Tweets</p>
          {q?.posted ? <p className="text-[10px] text-emerald-600 font-medium mt-0.5">{q.posted} total</p> : null}
        </Link>
        <Link href="/dashboard/twitter-engine/strategy" className="card p-4 hover:bg-gray-50 transition-colors group text-center">
          <Map size={20} className="text-violet-500 mx-auto mb-2 group-hover:scale-110 transition-transform" />
          <p className="text-xs font-semibold text-gray-800">Growth Strategy</p>
          <p className="text-[10px] text-gray-400 mt-0.5">AI-powered plan</p>
        </Link>
        <button onClick={() => setShowManual(!showManual)} className="card p-4 hover:bg-gray-50 transition-colors group text-center">
          <Send size={20} className="text-blue-500 mx-auto mb-2 group-hover:scale-110 transition-transform" />
          <p className="text-xs font-semibold text-gray-800">Manual Tweet</p>
          <p className="text-[10px] text-gray-400 mt-0.5">Write & post</p>
        </button>
      </div>

      {/* Manual Tweet Modal */}
      {showManual && (
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-gray-900 flex items-center gap-2 mb-3">
            <Send size={14} className="text-blue-500" /> Manual Tweet
          </h3>
          <textarea
            rows={3}
            maxLength={280}
            className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/30 resize-none"
            placeholder="Write your tweet..."
            value={manualText}
            onChange={e => setManualText(e.target.value)}
          />
          <div className="flex items-center justify-between mt-2">
            <span className={`text-xs ${manualText.length > 260 ? 'text-red-500 font-semibold' : 'text-gray-400'}`}>
              {manualText.length}/280
            </span>
            <div className="flex gap-2">
              <button onClick={() => setShowManual(false)} className="px-3 py-1.5 text-xs text-gray-500 hover:text-gray-700">Cancel</button>
              <button
                onClick={() => handleManualTweet(false)}
                disabled={posting || !manualText.trim()}
                className="px-3 py-1.5 text-xs font-medium bg-gray-100 rounded-lg hover:bg-gray-200 disabled:opacity-40"
              >
                Save to Queue
              </button>
              <button
                onClick={() => handleManualTweet(true)}
                disabled={posting || !manualText.trim() || !isConnected}
                className="flex items-center gap-1.5 px-4 py-1.5 text-xs font-semibold bg-black text-white rounded-lg hover:bg-gray-800 disabled:opacity-40"
              >
                {posting ? <Loader2 size={12} className="animate-spin" /> : <Send size={12} />}
                Post Now
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Totals if any posted */}
      {stats && stats.totals.impressions > 0 && (
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-gray-900 flex items-center gap-2 mb-3">
            <TrendingUp size={14} className="text-emerald-500" /> Performance Totals
          </h3>
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center">
              <p className="text-2xl font-bold text-gray-900">{stats.totals.impressions.toLocaleString()}</p>
              <p className="text-[10px] text-gray-500">Impressions</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-gray-900">{stats.totals.likes.toLocaleString()}</p>
              <p className="text-[10px] text-gray-500">Likes</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-gray-900">{stats.totals.retweets.toLocaleString()}</p>
              <p className="text-[10px] text-gray-500">Retweets</p>
            </div>
          </div>
        </div>
      )}

    </div>
  )
}

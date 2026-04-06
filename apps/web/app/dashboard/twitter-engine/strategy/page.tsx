'use client'

import { useState } from 'react'
import {
  Twitter, Loader2, Map, Zap, Clock,
  Target, TrendingUp, Hash, CheckCircle2,
  Calendar, Users, Lightbulb,
} from 'lucide-react'
import Link from 'next/link'
import { apiFetch } from '@/lib/apiFetch'

interface ContentPillar {
  pillar: string
  percentage: number
  description: string
  example: string
}

interface GrowthTactic {
  tactic: string
  time_per_day: string
  expected_followers_month1: string
}

interface Strategy {
  account_setup?: {
    bio: string
    pinned_tweet: string
    profile_keywords: string[]
  }
  content_pillars?: ContentPillar[]
  posting_schedule?: {
    tweets_per_day: number
    best_times: string[]
    thread_frequency: string
    days: string[]
  }
  growth_tactics?: GrowthTactic[]
  hashtag_strategy?: {
    use_hashtags: boolean
    reason: string
    exception: string
  }
  month_1_milestones?: string[]
  month_3_projection?: string
  month_6_projection?: string
  viral_content_formula?: string
  error?: string
}

const PILLAR_COLORS = [
  'bg-emerald-100 text-emerald-700 border-emerald-200',
  'bg-blue-100 text-blue-700 border-blue-200',
  'bg-violet-100 text-violet-700 border-violet-200',
  'bg-amber-100 text-amber-700 border-amber-200',
  'bg-pink-100 text-pink-700 border-pink-200',
]

export default function StrategyPage() {
  const [niche, setNiche] = useState('')
  const [audience, setAudience] = useState('')
  const [goal, setGoal] = useState('grow followers and build authority')
  const [loading, setLoading] = useState(false)
  const [strategy, setStrategy] = useState<Strategy | null>(null)

  async function handleGenerate() {
    if (!niche.trim()) return
    setLoading(true)
    setStrategy(null)
    try {
      const params = new URLSearchParams({
        niche: niche.trim(),
        target_audience: audience.trim() || 'general audience',
        account_goal: goal.trim(),
      })
      const result = await apiFetch<Strategy>(`/api/v1/twitter/strategy?${params}`, {
        method: 'POST',
        timeoutMs: 180_000,
      })
      setStrategy(result)
    } catch (e) {
      setStrategy({ error: e instanceof Error ? e.message : 'Strategy generation failed' })
    } finally {
      setLoading(false)
    }
  }

  const [applying, setApplying] = useState(false)
  const [applyMsg, setApplyMsg] = useState<string | null>(null)

  async function handleApplyStrategy() {
    setApplying(true)
    setApplyMsg(null)

    // Save to localStorage for generate form auto-fill
    localStorage.setItem('twitter_strategy', JSON.stringify({
      niche: niche.trim(),
      audience: audience.trim(),
    }))

    // Save to the first connected Twitter account via API
    try {
      const accounts = await apiFetch<{ accounts: Array<{ id: number }>, count: number }>('/api/v1/twitter/accounts')
      if (accounts.count > 0) {
        await apiFetch(`/api/v1/twitter/accounts/${accounts.accounts[0].id}`, {
          method: 'PUT',
          body: JSON.stringify({
            niche: niche.trim(),
            target_audience: audience.trim(),
            auto_generate: true,
          }),
        })
        setApplyMsg('Strategy applied to your X account!')
      } else {
        setApplyMsg('Strategy saved locally. Connect an X account to apply it.')
      }
    } catch {
      setApplyMsg('Strategy saved locally (API update failed).')
    } finally {
      setApplying(false)
      setTimeout(() => setApplyMsg(null), 4000)
    }
  }

  return (
    <div className="space-y-6">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-violet-100 rounded-xl flex items-center justify-center">
            <Map size={16} className="text-violet-600" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-gray-900">Twitter Growth Strategy</h1>
            <p className="text-xs text-gray-500">AI-powered strategy tailored to your niche</p>
          </div>
        </div>
        <Link href="/dashboard/twitter-engine" className="text-xs text-gray-500 hover:text-gray-700">
          ← Back to Hub
        </Link>
      </div>

      {/* Form */}
      <div className="card p-5">
        <h3 className="text-sm font-semibold text-gray-900 flex items-center gap-2 mb-4">
          <Zap size={14} className="text-violet-500" /> Generate Your Strategy
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Niche *</label>
            <input
              className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-violet-500/30"
              placeholder="e.g. AI tools, SaaS, fitness"
              value={niche}
              onChange={e => setNiche(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Target Audience</label>
            <input
              className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-violet-500/30"
              placeholder="e.g. startup founders"
              value={audience}
              onChange={e => setAudience(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Account Goal</label>
            <input
              className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-violet-500/30"
              placeholder="grow followers and build authority"
              value={goal}
              onChange={e => setGoal(e.target.value)}
            />
          </div>
        </div>
        <button
          onClick={handleGenerate}
          disabled={loading || !niche.trim()}
          className="mt-4 flex items-center gap-2 px-6 py-2.5 bg-violet-600 text-white rounded-lg text-sm font-semibold hover:bg-violet-700 disabled:opacity-40 transition-colors"
        >
          {loading ? <Loader2 size={14} className="animate-spin" /> : <Map size={14} />}
          {loading ? 'AI is building your strategy...' : 'Generate Strategy'}
        </button>
      </div>

      {/* Loading state */}
      {loading && (
        <div className="flex flex-col items-center justify-center py-16 gap-4">
          <Loader2 className="w-8 h-8 animate-spin text-violet-500" />
          <p className="text-sm text-gray-500">AI is crafting your Twitter growth strategy...</p>
          <p className="text-xs text-gray-400">This may take 30-60 seconds</p>
        </div>
      )}

      {/* Error */}
      {strategy?.error && (
        <div className="flex items-center gap-3 p-4 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">
          <Zap size={14} /> {strategy.error}
        </div>
      )}

      {/* Strategy Results */}
      {strategy && !strategy.error && (
        <div className="space-y-5">

          {/* Account Setup */}
          {strategy.account_setup && (
            <div className="card p-5">
              <h3 className="text-sm font-semibold text-gray-900 flex items-center gap-2 mb-4">
                <Twitter size={14} /> Account Setup
              </h3>
              <div className="space-y-3">
                <div className="bg-gray-50 rounded-lg p-4">
                  <p className="text-[10px] font-medium text-gray-500 uppercase mb-1">Bio</p>
                  <p className="text-sm text-gray-800">{strategy.account_setup.bio}</p>
                </div>
                <div className="bg-gray-50 rounded-lg p-4">
                  <p className="text-[10px] font-medium text-gray-500 uppercase mb-1">Pinned Tweet</p>
                  <p className="text-sm text-gray-800 italic">&ldquo;{strategy.account_setup.pinned_tweet}&rdquo;</p>
                </div>
                {strategy.account_setup.profile_keywords && (
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-[10px] text-gray-500 font-medium">Keywords:</span>
                    {strategy.account_setup.profile_keywords.map((kw, i) => (
                      <span key={i} className="text-[10px] px-2 py-0.5 rounded-full bg-blue-50 text-blue-600">{kw}</span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Content Pillars */}
          {strategy.content_pillars && strategy.content_pillars.length > 0 && (
            <div className="card p-5">
              <h3 className="text-sm font-semibold text-gray-900 flex items-center gap-2 mb-4">
                <Target size={14} className="text-emerald-500" /> Content Pillars
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {strategy.content_pillars.map((p, i) => (
                  <div key={i} className={`rounded-lg border p-4 ${PILLAR_COLORS[i % PILLAR_COLORS.length]}`}>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-bold capitalize">{p.pillar}</span>
                      <span className="text-xs font-bold">{p.percentage}%</span>
                    </div>
                    <p className="text-xs opacity-90 mb-2">{p.description}</p>
                    <p className="text-[10px] italic opacity-75">Example: &ldquo;{p.example}&rdquo;</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Posting Schedule */}
          {strategy.posting_schedule && (
            <div className="card p-5">
              <h3 className="text-sm font-semibold text-gray-900 flex items-center gap-2 mb-4">
                <Clock size={14} className="text-blue-500" /> Posting Schedule
              </h3>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="bg-blue-50 rounded-lg p-3 text-center">
                  <p className="text-xl font-bold text-blue-700">{strategy.posting_schedule.tweets_per_day}</p>
                  <p className="text-[10px] text-blue-600">tweets/day</p>
                </div>
                <div className="bg-blue-50 rounded-lg p-3 text-center">
                  <p className="text-xs font-semibold text-blue-700">
                    {strategy.posting_schedule.best_times?.join(', ')}
                  </p>
                  <p className="text-[10px] text-blue-600">best times</p>
                </div>
                <div className="bg-blue-50 rounded-lg p-3 text-center">
                  <p className="text-xs font-semibold text-blue-700">{strategy.posting_schedule.thread_frequency}</p>
                  <p className="text-[10px] text-blue-600">threads</p>
                </div>
                <div className="bg-blue-50 rounded-lg p-3 text-center">
                  <p className="text-xs font-semibold text-blue-700">
                    {strategy.posting_schedule.days?.join(', ')}
                  </p>
                  <p className="text-[10px] text-blue-600">active days</p>
                </div>
              </div>
            </div>
          )}

          {/* Growth Tactics */}
          {strategy.growth_tactics && strategy.growth_tactics.length > 0 && (
            <div className="card p-5">
              <h3 className="text-sm font-semibold text-gray-900 flex items-center gap-2 mb-4">
                <TrendingUp size={14} className="text-emerald-500" /> Growth Tactics
              </h3>
              <div className="space-y-2">
                {strategy.growth_tactics.map((t, i) => (
                  <div key={i} className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                    <span className="w-6 h-6 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center text-[10px] font-bold flex-shrink-0">
                      {i + 1}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-semibold text-gray-800">{t.tactic}</p>
                    </div>
                    <span className="text-[10px] text-gray-500 whitespace-nowrap">{t.time_per_day}</span>
                    <span className="text-[10px] font-semibold text-emerald-600 whitespace-nowrap">+{t.expected_followers_month1}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Hashtag Strategy */}
          {strategy.hashtag_strategy && (
            <div className="card p-4 flex items-start gap-3">
              <Hash size={16} className="text-gray-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-xs font-semibold text-gray-800">
                  Hashtags: {strategy.hashtag_strategy.use_hashtags ? 'Yes' : 'No'}
                </p>
                <p className="text-[11px] text-gray-500 mt-0.5">{strategy.hashtag_strategy.reason}</p>
                {strategy.hashtag_strategy.exception && (
                  <p className="text-[10px] text-gray-400 mt-0.5 italic">Exception: {strategy.hashtag_strategy.exception}</p>
                )}
              </div>
            </div>
          )}

          {/* Projections */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {strategy.month_1_milestones && (
              <div className="card p-4">
                <h4 className="text-xs font-semibold text-gray-900 flex items-center gap-2 mb-3">
                  <Calendar size={12} className="text-blue-500" /> Month 1 Milestones
                </h4>
                <ul className="space-y-1.5">
                  {strategy.month_1_milestones.map((m, i) => (
                    <li key={i} className="flex items-start gap-2 text-xs text-gray-600">
                      <CheckCircle2 size={11} className="text-emerald-400 mt-0.5 flex-shrink-0" />
                      {m}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {strategy.month_3_projection && (
              <div className="card p-4 flex flex-col items-center justify-center text-center">
                <Users size={16} className="text-violet-400 mb-2" />
                <p className="text-[10px] text-gray-500 uppercase font-medium">Month 3</p>
                <p className="text-lg font-bold text-violet-700">{strategy.month_3_projection}</p>
                <p className="text-[10px] text-gray-400">projected followers</p>
              </div>
            )}
            {strategy.month_6_projection && (
              <div className="card p-4 flex flex-col items-center justify-center text-center">
                <TrendingUp size={16} className="text-emerald-400 mb-2" />
                <p className="text-[10px] text-gray-500 uppercase font-medium">Month 6</p>
                <p className="text-lg font-bold text-emerald-700">{strategy.month_6_projection}</p>
                <p className="text-[10px] text-gray-400">projected followers</p>
              </div>
            )}
          </div>

          {/* Viral Formula */}
          {strategy.viral_content_formula && (
            <div className="card p-5 bg-gradient-to-r from-violet-50 to-blue-50 border-violet-200">
              <h3 className="text-sm font-semibold text-violet-800 flex items-center gap-2 mb-2">
                <Lightbulb size={14} className="text-amber-500" /> Viral Content Formula
              </h3>
              <p className="text-sm text-violet-700 leading-relaxed">{strategy.viral_content_formula}</p>
            </div>
          )}

          {/* Apply Strategy Button */}
          <div className="flex items-center gap-3 flex-wrap">
            <button
              onClick={handleApplyStrategy}
              disabled={applying}
              className="flex items-center gap-2 px-5 py-2.5 bg-violet-600 text-white rounded-lg text-sm font-semibold hover:bg-violet-700 disabled:opacity-50 transition-colors"
            >
              {applying ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle2 size={14} />}
              {applying ? 'Applying...' : 'Apply Strategy'}
            </button>
            {applyMsg ? (
              <span className="text-xs text-emerald-600 font-medium">{applyMsg}</span>
            ) : (
              <span className="text-xs text-gray-400">Saves niche & audience to your X account settings</span>
            )}
          </div>

        </div>
      )}

    </div>
  )
}

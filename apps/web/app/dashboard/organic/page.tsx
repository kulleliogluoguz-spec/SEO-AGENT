'use client'

import { useState } from 'react'
import { Sprout, TrendingUp, Target, Zap, ChevronRight, Loader2, AlertCircle } from 'lucide-react'

const API = 'http://localhost:8000/api/v1/organic'

interface GrowthScore {
  overall_score: number
  channel_scores: Record<string, number>
  quick_wins: string[]
  thirty_day_plan: string[]
  channel_priority: string[]
  biggest_opportunity: string
  risk_factors: string[]
}

const DEFAULT_PROFILE = {
  business_name: '',
  industry: '',
  target_audience: '',
  current_monthly_revenue: '',
  main_product_service: '',
  geographic_focus: '',
  current_channels: [] as string[],
  monthly_budget: '0',
  team_size: '1',
  biggest_challenge: '',
}

export default function GrowthHubPage() {
  const [profile, setProfile] = useState(DEFAULT_PROFILE)
  const [score, setScore] = useState<GrowthScore | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const CHANNELS = ['Twitter/X', 'Instagram', 'LinkedIn', 'TikTok', 'YouTube', 'Blog/SEO', 'Email', 'Podcast']

  function toggleChannel(ch: string) {
    setProfile(p => ({
      ...p,
      current_channels: p.current_channels.includes(ch)
        ? p.current_channels.filter(c => c !== ch)
        : [...p.current_channels, ch],
    }))
  }

  async function analyze() {
    if (!profile.business_name || !profile.industry || !profile.target_audience) {
      setError('Please fill in Business Name, Industry, and Target Audience.')
      return
    }
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`${API}/growth-score`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(profile),
      })
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      setScore(data)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to analyze')
    } finally {
      setLoading(false)
    }
  }

  const scoreColor = (s: number) =>
    s >= 75 ? 'text-emerald-400' : s >= 50 ? 'text-amber-400' : 'text-red-400'

  const scoreBar = (s: number) =>
    s >= 75 ? 'bg-emerald-500' : s >= 50 ? 'bg-amber-500' : 'bg-red-500'

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-emerald-500/10 flex items-center justify-center">
          <Sprout size={20} className="text-emerald-400" />
        </div>
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Organic Growth Hub</h1>
          <p className="text-sm text-slate-500">Zero-budget growth intelligence powered by proven marketing skills</p>
        </div>
      </div>

      {/* Profile Form */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-5">
        <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">Business Profile</h2>

        <div className="grid grid-cols-2 gap-4">
          {[
            { key: 'business_name', label: 'Business Name', placeholder: 'Acme Corp' },
            { key: 'industry', label: 'Industry', placeholder: 'SaaS, E-commerce, Agency...' },
            { key: 'target_audience', label: 'Target Audience', placeholder: 'e.g. early-stage founders' },
            { key: 'main_product_service', label: 'Main Product / Service', placeholder: 'What do you sell?' },
            { key: 'geographic_focus', label: 'Geographic Focus', placeholder: 'US, Global, EU...' },
            { key: 'current_monthly_revenue', label: 'Monthly Revenue (optional)', placeholder: '$5k, $50k...' },
          ].map(f => (
            <div key={f.key}>
              <label className="block text-xs font-medium text-slate-600 mb-1">{f.label}</label>
              <input
                className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-400"
                placeholder={f.placeholder}
                value={(profile as Record<string, string>)[f.key]}
                onChange={e => setProfile(p => ({ ...p, [f.key]: e.target.value }))}
              />
            </div>
          ))}
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-600 mb-2">Biggest Challenge</label>
          <textarea
            rows={2}
            className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-400"
            placeholder="What is holding your growth back right now?"
            value={profile.biggest_challenge}
            onChange={e => setProfile(p => ({ ...p, biggest_challenge: e.target.value }))}
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-600 mb-2">Active Channels</label>
          <div className="flex flex-wrap gap-2">
            {CHANNELS.map(ch => (
              <button
                key={ch}
                onClick={() => toggleChannel(ch)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                  profile.current_channels.includes(ch)
                    ? 'bg-emerald-500 border-emerald-500 text-white'
                    : 'bg-white border-slate-200 text-slate-600 hover:border-emerald-300'
                }`}
              >
                {ch}
              </button>
            ))}
          </div>
        </div>

        {error && (
          <div className="flex items-center gap-2 text-sm text-red-600 bg-red-50 rounded-lg px-4 py-2.5">
            <AlertCircle size={14} />
            {error}
          </div>
        )}

        <button
          onClick={analyze}
          disabled={loading}
          className="flex items-center gap-2 px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-semibold rounded-lg transition-colors disabled:opacity-50"
        >
          {loading ? <Loader2 size={14} className="animate-spin" /> : <TrendingUp size={14} />}
          {loading ? 'Analyzing...' : 'Analyze Growth Potential'}
        </button>
      </div>

      {/* Results */}
      {score && (
        <div className="space-y-5">
          {/* Overall Score */}
          <div className="bg-white rounded-xl border border-slate-200 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-slate-700">Growth Score</h2>
              <span className={`text-3xl font-bold ${scoreColor(score.overall_score)}`}>
                {score.overall_score}<span className="text-base font-normal text-slate-400">/100</span>
              </span>
            </div>
            <div className="w-full h-2.5 bg-slate-100 rounded-full overflow-hidden mb-6">
              <div
                className={`h-full rounded-full transition-all duration-700 ${scoreBar(score.overall_score)}`}
                style={{ width: `${score.overall_score}%` }}
              />
            </div>

            {/* Channel scores */}
            {Object.keys(score.channel_scores || {}).length > 0 && (
              <div className="space-y-2">
                <p className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-3">Channel Breakdown</p>
                {Object.entries(score.channel_scores || {}).map(([ch, s]) => (
                  <div key={ch} className="flex items-center gap-3">
                    <span className="text-xs text-slate-600 w-24 truncate">{ch}</span>
                    <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                      <div className={`h-full rounded-full ${scoreBar(s as number)}`} style={{ width: `${s}%` }} />
                    </div>
                    <span className={`text-xs font-semibold w-8 text-right ${scoreColor(s as number)}`}>{s}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Biggest Opportunity */}
          {score.biggest_opportunity && (
            <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-5">
              <div className="flex items-start gap-3">
                <Target size={16} className="text-emerald-600 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-xs font-semibold text-emerald-700 uppercase tracking-wide mb-1">Biggest Opportunity</p>
                  <p className="text-sm text-emerald-800">{score.biggest_opportunity}</p>
                </div>
              </div>
            </div>
          )}

          {/* Quick Wins + 30-Day Plan */}
          <div className="grid grid-cols-2 gap-5">
            <div className="bg-white rounded-xl border border-slate-200 p-5">
              <div className="flex items-center gap-2 mb-4">
                <Zap size={14} className="text-amber-500" />
                <h3 className="text-sm font-semibold text-slate-700">Quick Wins</h3>
              </div>
              <ul className="space-y-2">
                {(score.quick_wins ?? []).map((w, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-slate-600">
                    <ChevronRight size={12} className="text-amber-400 mt-1 flex-shrink-0" />
                    {w}
                  </li>
                ))}
              </ul>
            </div>

            <div className="bg-white rounded-xl border border-slate-200 p-5">
              <div className="flex items-center gap-2 mb-4">
                <TrendingUp size={14} className="text-emerald-500" />
                <h3 className="text-sm font-semibold text-slate-700">30-Day Plan</h3>
              </div>
              <ul className="space-y-2">
                {(score.thirty_day_plan ?? []).map((step, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-slate-600">
                    <span className="text-[10px] font-bold text-emerald-500 mt-1 w-4 flex-shrink-0">{i + 1}.</span>
                    {step}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Channel Priority */}
          {(score.channel_priority ?? []).length > 0 && (
            <div className="bg-white rounded-xl border border-slate-200 p-5">
              <h3 className="text-sm font-semibold text-slate-700 mb-3">Channel Priority Order</h3>
              <div className="flex flex-wrap gap-2">
                {(score.channel_priority ?? []).map((ch, i) => (
                  <div key={i} className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg">
                    <span className="text-[10px] font-bold text-slate-400">#{i + 1}</span>
                    <span className="text-xs text-slate-700">{ch}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

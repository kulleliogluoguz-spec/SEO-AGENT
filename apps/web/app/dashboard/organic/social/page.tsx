'use client'

import { useState } from 'react'
import { Share2, Twitter, Instagram, Loader2, AlertCircle, TrendingUp } from 'lucide-react'

const API = 'http://localhost:8000/api/v1/organic'

interface SocialStrategy {
  twitter_strategy: {
    content_pillars: string[]
    posting_frequency: string
    best_times: string[]
    thread_topics: string[]
    engagement_tactics: string[]
    growth_hacks: string[]
  }
  instagram_strategy: {
    content_mix: Record<string, string>
    posting_frequency: string
    hashtag_strategy: string[]
    reel_ideas: string[]
    story_tactics: string[]
    growth_hacks: string[]
  }
  follower_growth_projection: Array<{ month: number; followers: number; milestone: string }>
  cross_platform_synergies: string[]
  content_repurposing: string[]
}

export default function SocialStrategyPage() {
  const [platform, setPlatform] = useState<'both' | 'twitter' | 'instagram'>('both')
  const [audience, setAudience] = useState('')
  const [niche, setNiche] = useState('')
  const [currentFollowers, setCurrentFollowers] = useState('0')

  const [strategy, setStrategy] = useState<SocialStrategy | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function generate() {
    if (!audience || !niche) { setError('Audience and niche are required.'); return }
    setLoading(true); setError('')
    try {
      const res = await fetch(`${API}/social/strategy`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          target_audience: audience,
          niche,
          platform_focus: platform,
          current_followers: parseInt(currentFollowers) || 0,
        }),
      })
      if (!res.ok) throw new Error(await res.text())
      setStrategy(await res.json())
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed')
    } finally { setLoading(false) }
  }

  const projections = strategy?.follower_growth_projection ?? []
  const maxFollowers = projections.length
    ? Math.max(...projections.map(p => p.followers))
    : 1

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-purple-500/10 flex items-center justify-center">
          <Share2 size={20} className="text-purple-500" />
        </div>
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Social Strategy</h1>
          <p className="text-sm text-slate-500">AI-generated Twitter & Instagram growth playbooks</p>
        </div>
      </div>

      {/* Input */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Target Audience *</label>
            <input className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-purple-500/30 focus:border-purple-400"
              placeholder="e.g. indie hackers, B2B founders" value={audience} onChange={e => setAudience(e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Niche *</label>
            <input className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-purple-500/30 focus:border-purple-400"
              placeholder="e.g. SaaS, personal finance, fitness" value={niche} onChange={e => setNiche(e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Current Followers (combined)</label>
            <input type="number" className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-purple-500/30 focus:border-purple-400"
              placeholder="0" value={currentFollowers} onChange={e => setCurrentFollowers(e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Platform Focus</label>
            <div className="flex gap-2">
              {(['both', 'twitter', 'instagram'] as const).map(p => (
                <button key={p} onClick={() => setPlatform(p)}
                  className={`flex-1 py-2 text-xs font-medium rounded-lg border transition-all capitalize ${
                    platform === p ? 'bg-purple-600 border-purple-600 text-white' : 'bg-white border-slate-200 text-slate-600 hover:border-purple-300'
                  }`}>
                  {p}
                </button>
              ))}
            </div>
          </div>
        </div>
        {error && (
          <div className="flex items-center gap-2 text-sm text-red-600 bg-red-50 rounded-lg px-4 py-2.5">
            <AlertCircle size={14} />{error}
          </div>
        )}
        <button onClick={generate} disabled={loading}
          className="flex items-center gap-2 px-5 py-2.5 bg-purple-600 hover:bg-purple-700 text-white text-sm font-semibold rounded-lg transition-colors disabled:opacity-50">
          {loading ? <Loader2 size={14} className="animate-spin" /> : <Share2 size={14} />}
          {loading ? 'Generating...' : 'Generate Strategy'}
        </button>
      </div>

      {strategy && (
        <div className="space-y-5">
          {/* Follower Projection Chart */}
          <div className="bg-white rounded-xl border border-slate-200 p-5">
            <div className="flex items-center gap-2 mb-5">
              <TrendingUp size={14} className="text-emerald-500" />
              <h3 className="text-sm font-semibold text-slate-700">6-Month Follower Projection</h3>
            </div>
            <div className="flex items-end gap-3 h-32">
              {projections.map((p, i) => (
                <div key={i} className="flex-1 flex flex-col items-center gap-1">
                  <span className="text-[10px] text-slate-500">{p.followers.toLocaleString()}</span>
                  <div
                    className="w-full rounded-t-md bg-purple-500 transition-all duration-500"
                    style={{ height: `${Math.max(4, (p.followers / maxFollowers) * 100)}px` }}
                  />
                  <span className="text-[10px] text-slate-400">M{p.month}</span>
                </div>
              ))}
            </div>
            <div className="mt-3 space-y-1">
              {projections.filter(p => p.milestone).map((p, i) => (
                <p key={i} className="text-[11px] text-slate-500">
                  <span className="font-medium text-purple-600">Month {p.month}:</span> {p.milestone}
                </p>
              ))}
            </div>
          </div>

          {/* Twitter + Instagram side by side */}
          <div className="grid grid-cols-2 gap-5">
            {/* Twitter */}
            {(platform === 'both' || platform === 'twitter') && (
              <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-4">
                <div className="flex items-center gap-2">
                  <Twitter size={14} className="text-sky-500" />
                  <h3 className="text-sm font-semibold text-slate-700">Twitter / X Strategy</h3>
                </div>
                <div>
                  <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Content Pillars</p>
                  <div className="flex flex-wrap gap-1.5">
                    {(strategy.twitter_strategy?.content_pillars ?? []).map((p, i) => (
                      <span key={i} className="px-2.5 py-1 bg-sky-50 text-sky-700 text-xs rounded-lg border border-sky-200">{p}</span>
                    ))}
                  </div>
                </div>
                <div>
                  <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Thread Topics</p>
                  <ul className="space-y-1">
                    {(strategy.twitter_strategy?.thread_topics ?? []).map((t, i) => (
                      <li key={i} className="text-xs text-slate-600 flex gap-2"><span className="text-sky-400">→</span>{t}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Growth Hacks</p>
                  <ul className="space-y-1">
                    {(strategy.twitter_strategy?.growth_hacks ?? []).map((h, i) => (
                      <li key={i} className="text-xs text-slate-600 flex gap-2"><span className="text-emerald-400">✓</span>{h}</li>
                    ))}
                  </ul>
                </div>
                <p className="text-xs text-slate-500">
                  <span className="font-medium">Post:</span> {strategy.twitter_strategy?.posting_frequency} ·{' '}
                  <span className="font-medium">Best times:</span> {(strategy.twitter_strategy?.best_times ?? []).join(', ')}
                </p>
              </div>
            )}

            {/* Instagram */}
            {(platform === 'both' || platform === 'instagram') && (
              <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-4">
                <div className="flex items-center gap-2">
                  <Instagram size={14} className="text-pink-500" />
                  <h3 className="text-sm font-semibold text-slate-700">Instagram Strategy</h3>
                </div>
                <div>
                  <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Content Mix</p>
                  <div className="space-y-1">
                    {Object.entries(strategy.instagram_strategy?.content_mix ?? {}).map(([type, pct]) => (
                      <div key={type} className="flex items-center gap-2 text-xs">
                        <span className="text-slate-600 w-24">{type}</span>
                        <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                          <div className="h-full bg-pink-500 rounded-full" style={{ width: String(pct) }} />
                        </div>
                        <span className="text-slate-400 w-8 text-right">{String(pct)}</span>
                      </div>
                    ))}
                  </div>
                </div>
                <div>
                  <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Reel Ideas</p>
                  <ul className="space-y-1">
                    {(strategy.instagram_strategy?.reel_ideas ?? []).map((r, i) => (
                      <li key={i} className="text-xs text-slate-600 flex gap-2"><span className="text-pink-400">▶</span>{r}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Growth Hacks</p>
                  <ul className="space-y-1">
                    {(strategy.instagram_strategy?.growth_hacks ?? []).map((h, i) => (
                      <li key={i} className="text-xs text-slate-600 flex gap-2"><span className="text-emerald-400">✓</span>{h}</li>
                    ))}
                  </ul>
                </div>
              </div>
            )}
          </div>

          {/* Cross-platform */}
          {(strategy.cross_platform_synergies ?? []).length > 0 && (
            <div className="bg-white rounded-xl border border-slate-200 p-5">
              <h3 className="text-sm font-semibold text-slate-700 mb-3">Cross-Platform Synergies & Repurposing</h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wide mb-2">Synergies</p>
                  <ul className="space-y-1">
                    {(strategy.cross_platform_synergies ?? []).map((s, i) => (
                      <li key={i} className="text-xs text-slate-600 flex gap-2"><span className="text-purple-400">◆</span>{s}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wide mb-2">Content Repurposing</p>
                  <ul className="space-y-1">
                    {(strategy.content_repurposing ?? []).map((r, i) => (
                      <li key={i} className="text-xs text-slate-600 flex gap-2"><span className="text-amber-400">→</span>{r}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

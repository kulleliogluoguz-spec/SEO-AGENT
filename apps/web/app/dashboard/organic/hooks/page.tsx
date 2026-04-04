'use client'

import { useState } from 'react'
import { Flame, Copy, Check, Loader2, AlertCircle, RefreshCw } from 'lucide-react'

const API = 'http://localhost:8000/api/v1/organic'

interface HookResult {
  hooks: Array<{
    framework: string
    hook: string
    explanation: string
    engagement_score: number
    variations: string[]
  }>
  best_performing_type: string
  usage_tips: string[]
  a_b_test_suggestions: string[]
}

const FRAMEWORKS = [
  { id: 'curiosity_gap', label: 'Curiosity Gap' },
  { id: 'contrarian', label: 'Contrarian' },
  { id: 'social_proof', label: 'Social Proof' },
  { id: 'pain_point', label: 'Pain Point' },
  { id: 'story', label: 'Story' },
  { id: 'data_driven', label: 'Data-Driven' },
  { id: 'how_to', label: 'How-To' },
  { id: 'list', label: 'List / Listicle' },
]

export default function ViralHooksPage() {
  const [topic, setTopic] = useState('')
  const [audience, setAudience] = useState('')
  const [platform, setPlatform] = useState('twitter')
  const [selectedFrameworks, setSelectedFrameworks] = useState<string[]>([])
  const [result, setResult] = useState<HookResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [copied, setCopied] = useState('')

  function toggleFramework(id: string) {
    setSelectedFrameworks(prev =>
      prev.includes(id) ? prev.filter(f => f !== id) : [...prev, id]
    )
  }

  async function generate() {
    if (!topic || !audience) { setError('Topic and audience are required.'); return }
    setLoading(true); setError('')
    try {
      const res = await fetch(`${API}/hooks/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          topic,
          target_audience: audience,
          platform,
          frameworks: selectedFrameworks.length > 0 ? selectedFrameworks : undefined,
        }),
      })
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      if (data.error) throw new Error(data.error)
      setResult(data)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed')
    } finally { setLoading(false) }
  }

  function copy(text: string, key: string) {
    navigator.clipboard.writeText(text)
    setCopied(key)
    setTimeout(() => setCopied(''), 2000)
  }

  const scoreColor = (s: number) =>
    s >= 8 ? 'text-emerald-600 bg-emerald-50 border-emerald-200'
    : s >= 6 ? 'text-amber-600 bg-amber-50 border-amber-200'
    : 'text-slate-600 bg-slate-50 border-slate-200'

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-orange-500/10 flex items-center justify-center">
          <Flame size={20} className="text-orange-500" />
        </div>
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Viral Hook Generator</h1>
          <p className="text-sm text-slate-500">Generate scroll-stopping hooks using proven copywriting frameworks</p>
        </div>
      </div>

      {/* Input */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Topic / Content Idea *</label>
            <input className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-orange-500/30 focus:border-orange-400"
              placeholder="e.g. how I grew to 10k followers in 3 months" value={topic} onChange={e => setTopic(e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Target Audience *</label>
            <input className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-orange-500/30 focus:border-orange-400"
              placeholder="e.g. aspiring entrepreneurs" value={audience} onChange={e => setAudience(e.target.value)} />
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-600 mb-2">Platform</label>
          <div className="flex gap-2">
            {['twitter', 'instagram', 'linkedin', 'tiktok', 'email'].map(p => (
              <button key={p} onClick={() => setPlatform(p)}
                className={`px-3 py-1.5 text-xs font-medium rounded-lg border capitalize transition-all ${
                  platform === p ? 'bg-orange-500 border-orange-500 text-white' : 'bg-white border-slate-200 text-slate-600 hover:border-orange-300'
                }`}>
                {p}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-600 mb-2">Hook Frameworks (optional — leave blank for all)</label>
          <div className="flex flex-wrap gap-2">
            {FRAMEWORKS.map(f => (
              <button key={f.id} onClick={() => toggleFramework(f.id)}
                className={`px-3 py-1.5 text-xs font-medium rounded-lg border transition-all ${
                  selectedFrameworks.includes(f.id)
                    ? 'bg-orange-500 border-orange-500 text-white'
                    : 'bg-white border-slate-200 text-slate-600 hover:border-orange-300'
                }`}>
                {f.label}
              </button>
            ))}
          </div>
        </div>

        {error && (
          <div className="flex items-center gap-2 text-sm text-red-600 bg-red-50 rounded-lg px-4 py-2.5">
            <AlertCircle size={14} />{error}
          </div>
        )}
        <div className="flex gap-3">
          <button onClick={generate} disabled={loading}
            className="flex items-center gap-2 px-5 py-2.5 bg-orange-500 hover:bg-orange-600 text-white text-sm font-semibold rounded-lg transition-colors disabled:opacity-50">
            {loading ? <Loader2 size={14} className="animate-spin" /> : <Flame size={14} />}
            {loading ? 'Generating...' : 'Generate Hooks'}
          </button>
          {result && (
            <button onClick={generate} disabled={loading}
              className="flex items-center gap-2 px-4 py-2.5 border border-slate-200 text-slate-600 text-sm font-medium rounded-lg hover:bg-slate-50 transition-colors disabled:opacity-50">
              <RefreshCw size={13} />Regenerate
            </button>
          )}
        </div>
      </div>

      {/* Results */}
      {result && (
        <div className="space-y-4">
          {result.best_performing_type && (
            <div className="bg-orange-50 border border-orange-200 rounded-xl px-5 py-3">
              <p className="text-sm text-orange-800">
                <span className="font-semibold">Best performing type for your audience:</span>{' '}
                {result.best_performing_type}
              </p>
            </div>
          )}

          {(result.hooks ?? []).map((hook, i) => (
            <div key={i} className="bg-white rounded-xl border border-slate-200 p-5 space-y-3">
              <div className="flex items-center justify-between">
                <span className="px-2.5 py-1 bg-slate-100 text-slate-600 text-xs font-medium rounded-lg">
                  {hook.framework}
                </span>
                <div className="flex items-center gap-3">
                  <span className={`px-2.5 py-1 text-xs font-semibold rounded-lg border ${scoreColor(hook.engagement_score)}`}>
                    Score: {hook.engagement_score}/10
                  </span>
                  <button onClick={() => copy(hook.hook, `hook-${i}`)}
                    className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-700 transition-colors">
                    {copied === `hook-${i}` ? <Check size={12} className="text-emerald-500" /> : <Copy size={12} />}
                    {copied === `hook-${i}` ? 'Copied' : 'Copy'}
                  </button>
                </div>
              </div>

              <p className="text-sm font-medium text-slate-800 leading-relaxed">{hook.hook}</p>

              <p className="text-xs text-slate-500">{hook.explanation}</p>

              {hook.variations.length > 0 && (
                <div>
                  <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wide mb-2">Variations</p>
                  <div className="space-y-1.5">
                    {hook.variations.map((v, j) => (
                      <div key={j} className="flex items-start justify-between gap-3 p-2.5 bg-slate-50 rounded-lg">
                        <p className="text-xs text-slate-700 flex-1">{v}</p>
                        <button onClick={() => copy(v, `var-${i}-${j}`)}
                          className="text-slate-400 hover:text-slate-600 flex-shrink-0">
                          {copied === `var-${i}-${j}` ? <Check size={11} className="text-emerald-500" /> : <Copy size={11} />}
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}

          {(result.usage_tips ?? []).length > 0 && (
            <div className="bg-white rounded-xl border border-slate-200 p-5">
              <h3 className="text-sm font-semibold text-slate-700 mb-3">Usage Tips</h3>
              <ul className="space-y-2">
                {(result.usage_tips ?? []).map((tip, i) => (
                  <li key={i} className="text-sm text-slate-600 flex gap-2">
                    <span className="text-orange-400 flex-shrink-0">•</span>{tip}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {(result.a_b_test_suggestions ?? []).length > 0 && (
            <div className="bg-white rounded-xl border border-slate-200 p-5">
              <h3 className="text-sm font-semibold text-slate-700 mb-3">A/B Test These</h3>
              <ul className="space-y-2">
                {(result.a_b_test_suggestions ?? []).map((s, i) => (
                  <li key={i} className="text-sm text-slate-600 flex gap-2">
                    <span className="text-purple-400 flex-shrink-0">↔</span>{s}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

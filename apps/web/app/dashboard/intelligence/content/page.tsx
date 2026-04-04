'use client'

import { useState } from 'react'
import { Star, Loader2, Copy, CheckCircle2, AlertCircle, XCircle, ChevronDown, ChevronUp } from 'lucide-react'

const API = '/api/v1/intelligence'

const CONTENT_TYPES = ['blog', 'tweet', 'instagram_caption', 'email', 'landing_page', 'ad_copy']
const GOALS = ['awareness', 'engagement', 'conversion', 'retention']
const BUSINESS_TYPES = ['saas', 'ecommerce', 'local', 'personal_brand', 'agency', 'coaching']

interface ExpertPanel {
  expert: string
  score: number
  grade: string
  strengths: string[]
  weaknesses: string[]
  improvements: { issue: string; fix: string; impact: string }[]
  rewritten_headline?: string
}

interface ScoreResult {
  content_type: string
  overall_score: number
  grade: string
  verdict: string
  expert_panels: ExpertPanel[]
  top_3_improvements: string[]
  improved_version: string
  projected_performance: string
}

function ScoreCircle({ score, grade }: { score: number; grade: string }) {
  const color = score >= 80 ? 'text-emerald-600' : score >= 60 ? 'text-amber-600' : 'text-red-500'
  const ring = score >= 80 ? 'stroke-emerald-500' : score >= 60 ? 'stroke-amber-500' : 'stroke-red-500'
  const circumference = 2 * Math.PI * 36
  const dash = (score / 100) * circumference
  return (
    <div className="relative w-24 h-24 flex items-center justify-center">
      <svg className="absolute inset-0 -rotate-90" viewBox="0 0 80 80">
        <circle cx="40" cy="40" r="36" fill="none" stroke="#e2e8f0" strokeWidth="6" />
        <circle cx="40" cy="40" r="36" fill="none" className={ring} strokeWidth="6"
          strokeDasharray={`${dash} ${circumference}`} strokeLinecap="round" />
      </svg>
      <div className="text-center">
        <div className={`text-2xl font-bold ${color}`}>{score}</div>
        <div className={`text-sm font-semibold ${color}`}>{grade}</div>
      </div>
    </div>
  )
}

function VerdictBadge({ verdict }: { verdict: string }) {
  const map: Record<string, { label: string; cls: string; icon: React.ElementType }> = {
    publish: { label: 'PUBLISH', cls: 'bg-emerald-100 text-emerald-800 border-emerald-200', icon: CheckCircle2 },
    revise: { label: 'REVISE', cls: 'bg-amber-100 text-amber-800 border-amber-200', icon: AlertCircle },
    reject: { label: 'REJECT', cls: 'bg-red-100 text-red-800 border-red-200', icon: XCircle },
  }
  const v = map[verdict?.toLowerCase()] ?? map.revise
  const Icon = v.icon
  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold border ${v.cls}`}>
      <Icon size={12} /> {v.label}
    </span>
  )
}

function ExpertCard({ panel }: { panel: ExpertPanel }) {
  const [open, setOpen] = useState(false)
  const color = panel.score >= 80 ? 'text-emerald-600' : panel.score >= 60 ? 'text-amber-600' : 'text-red-500'
  return (
    <div className="border border-slate-200 rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-slate-50 transition-colors">
        <div className="flex items-center gap-3">
          <span className={`text-lg font-bold ${color}`}>{panel.score}</span>
          <span className="text-sm font-medium text-slate-700">{panel.expert}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-xs font-semibold ${color}`}>{panel.grade}</span>
          {open ? <ChevronUp size={14} className="text-slate-400" /> : <ChevronDown size={14} className="text-slate-400" />}
        </div>
      </button>
      {open && (
        <div className="px-4 pb-4 space-y-3 border-t border-slate-100 pt-3">
          {panel.strengths?.length > 0 && (
            <div>
              <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wide mb-1">Strengths</p>
              {panel.strengths.map((s, i) => (
                <p key={i} className="text-xs text-slate-600 flex items-start gap-1.5"><CheckCircle2 size={10} className="text-emerald-500 mt-0.5 flex-shrink-0" />{s}</p>
              ))}
            </div>
          )}
          {panel.weaknesses?.length > 0 && (
            <div>
              <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wide mb-1">Weaknesses</p>
              {panel.weaknesses.map((w, i) => (
                <p key={i} className="text-xs text-slate-600 flex items-start gap-1.5"><XCircle size={10} className="text-red-400 mt-0.5 flex-shrink-0" />{w}</p>
              ))}
            </div>
          )}
          {panel.improvements?.length > 0 && (
            <div>
              <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wide mb-1">Improvements</p>
              {panel.improvements.map((imp, i) => (
                <div key={i} className="bg-slate-50 rounded-lg p-2.5 mb-1.5">
                  <p className="text-xs text-slate-600 font-medium">{imp.issue}</p>
                  <p className="text-xs text-blue-700 mt-0.5">→ {imp.fix}</p>
                  <span className={`text-[10px] font-semibold ${imp.impact === 'high' ? 'text-red-600' : imp.impact === 'medium' ? 'text-amber-600' : 'text-slate-500'}`}>
                    {imp.impact} impact
                  </span>
                </div>
              ))}
            </div>
          )}
          {panel.rewritten_headline && (
            <div className="bg-blue-50 rounded-lg p-2.5">
              <p className="text-[10px] font-semibold text-blue-600 uppercase tracking-wide mb-1">Rewritten Headline</p>
              <p className="text-xs text-blue-800">{panel.rewritten_headline}</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  const copy = () => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }
  return (
    <button onClick={copy} className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors">
      {copied ? <CheckCircle2 size={12} className="text-emerald-500" /> : <Copy size={12} />}
      {copied ? 'Copied!' : 'Copy'}
    </button>
  )
}

export default function ContentScorePage() {
  const [content, setContent] = useState('')
  const [contentType, setContentType] = useState('landing_page')
  const [audience, setAudience] = useState('')
  const [goal, setGoal] = useState('conversion')
  const [businessType, setBusinessType] = useState('saas')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<ScoreResult | null>(null)
  const [error, setError] = useState('')

  async function score() {
    if (!content.trim()) return
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const res = await fetch(`${API}/content/score`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content, content_type: contentType, target_audience: audience, goal, business_type: businessType }),
      })
      const data = await res.json()
      if (data.error) { setError(data.error); return }
      setResult(data)
    } catch {
      setError('Network error — is the backend running?')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">

      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-amber-500/10 flex items-center justify-center">
          <Star size={20} className="text-amber-500" />
        </div>
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Content Scorer</h1>
          <p className="text-sm text-slate-500">3-expert panel: Copywriter · CRO Specialist · Marketing Psychologist</p>
        </div>
      </div>

      {/* Form */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-4">
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1.5">Your Content</label>
          <textarea
            className="w-full px-3 py-2.5 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-amber-500/30 focus:border-amber-400 resize-none"
            rows={8}
            placeholder="Paste your landing page copy, tweet, email, ad copy, or any marketing content here..."
            value={content}
            onChange={e => setContent(e.target.value)}
          />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Content Type</label>
            <select className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-amber-500/30 bg-white"
              value={contentType} onChange={e => setContentType(e.target.value)}>
              {CONTENT_TYPES.map(t => <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Goal</label>
            <select className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-amber-500/30 bg-white"
              value={goal} onChange={e => setGoal(e.target.value)}>
              {GOALS.map(g => <option key={g} value={g}>{g}</option>)}
            </select>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Target Audience</label>
            <input className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-amber-500/30"
              placeholder="e.g. startup founders" value={audience} onChange={e => setAudience(e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Business Type</label>
            <select className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-amber-500/30 bg-white"
              value={businessType} onChange={e => setBusinessType(e.target.value)}>
              {BUSINESS_TYPES.map(b => <option key={b} value={b}>{b}</option>)}
            </select>
          </div>
        </div>
        <button onClick={score} disabled={loading || !content.trim()}
          className="w-full flex items-center justify-center gap-2 py-3 bg-amber-500 hover:bg-amber-600 text-white text-sm font-bold rounded-xl transition-colors disabled:opacity-50">
          {loading ? <Loader2 size={16} className="animate-spin" /> : <Star size={16} />}
          {loading ? '3 experts are reviewing your content…' : 'Score My Content'}
        </button>
        {loading && (
          <div className="text-center py-2">
            <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
              <div className="h-full bg-amber-500 animate-pulse rounded-full w-2/3" />
            </div>
            <p className="text-xs text-slate-400 mt-2">3 experts reviewing — takes 1–3 minutes with local AI</p>
          </div>
        )}
      </div>

      {error && (
        <div className="flex items-center gap-3 p-4 bg-red-50 border border-red-200 rounded-xl">
          <AlertCircle size={15} className="text-red-500 flex-shrink-0" />
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="space-y-4">
          {/* Score summary */}
          <div className="bg-white border border-slate-200 rounded-xl p-6 flex items-center gap-6">
            <ScoreCircle score={result.overall_score} grade={result.grade} />
            <div className="flex-1 space-y-2">
              <div className="flex items-center gap-3">
                <h2 className="text-base font-semibold text-slate-800 capitalize">{result.content_type.replace(/_/g, ' ')} Score</h2>
                <VerdictBadge verdict={result.verdict} />
              </div>
              {result.projected_performance && (
                <p className="text-sm text-slate-500">{result.projected_performance}</p>
              )}
            </div>
          </div>

          {/* Top 3 improvements */}
          {result.top_3_improvements?.length > 0 && (
            <div className="bg-white border border-slate-200 rounded-xl p-5">
              <h3 className="text-sm font-semibold text-slate-700 mb-3">Top 3 Improvements</h3>
              <div className="space-y-2">
                {result.top_3_improvements.map((imp, i) => (
                  <div key={i} className="flex items-start gap-3">
                    <span className="w-5 h-5 rounded-full bg-amber-100 text-amber-700 text-xs font-bold flex items-center justify-center flex-shrink-0 mt-0.5">{i + 1}</span>
                    <p className="text-sm text-slate-700">{imp}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Expert panels */}
          {result.expert_panels?.length > 0 && (
            <div className="bg-white border border-slate-200 rounded-xl p-5">
              <h3 className="text-sm font-semibold text-slate-700 mb-3">Expert Panel Reviews</h3>
              <div className="space-y-2">
                {result.expert_panels.map((panel, i) => (
                  <ExpertCard key={i} panel={panel} />
                ))}
              </div>
            </div>
          )}

          {/* Improved version */}
          {result.improved_version && (
            <div className="bg-white border border-slate-200 rounded-xl p-5">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-slate-700">Improved Version</h3>
                <CopyButton text={result.improved_version} />
              </div>
              <div className="bg-slate-50 rounded-lg p-4 text-sm text-slate-700 whitespace-pre-wrap font-mono text-xs leading-relaxed">
                {result.improved_version}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

'use client'

import { useState } from 'react'
import { BarChart3, Loader2, AlertCircle, CheckCircle2, XCircle, TrendingUp, TrendingDown, Minus } from 'lucide-react'

const API = '/api/v1/intelligence'
const BUSINESS_TYPES = ['saas', 'ecommerce', 'local', 'personal_brand', 'agency', 'coaching']

const DEFAULT_METRICS = [
  { key: 'website_visitors', label: 'Website Visitors', placeholder: '1200' },
  { key: 'new_followers_twitter', label: 'New Followers (X/Twitter)', placeholder: '45' },
  { key: 'new_followers_instagram', label: 'New Followers (Instagram)', placeholder: '82' },
  { key: 'email_opens', label: 'Email Opens', placeholder: '320' },
  { key: 'conversions', label: 'Conversions / Sales', placeholder: '12' },
  { key: 'revenue', label: 'Revenue ($)', placeholder: '4200' },
]

interface MetricAnalysis {
  metric: string; value: number; trend: string; vs_benchmark: string; score: number; insight: string
}
interface ExperimentSuggestion { experiment: string; expected_impact: string; effort: string }
interface ChannelPerf { channel: string; score: number; trend: string; action: string }
interface ScorecardResult {
  week_ending: string
  overall_score: number
  grade: string
  metrics_analysis: MetricAnalysis[]
  wins: string[]
  losses: string[]
  top_priority_next_week: string
  experiments_to_run: ExperimentSuggestion[]
  channels_performance: ChannelPerf[]
  '30_day_projection': string
}

function TrendIcon({ trend }: { trend: string }) {
  if (trend === 'up') return <TrendingUp size={12} className="text-emerald-500" />
  if (trend === 'down') return <TrendingDown size={12} className="text-red-500" />
  return <Minus size={12} className="text-slate-400" />
}

function GradeCircle({ score, grade }: { score: number; grade: string }) {
  const color = score >= 80 ? 'text-emerald-600' : score >= 60 ? 'text-amber-600' : 'text-red-500'
  const ring = score >= 80 ? 'stroke-emerald-500' : score >= 60 ? 'stroke-amber-500' : 'stroke-red-500'
  const circumference = 2 * Math.PI * 40
  const dash = (score / 100) * circumference
  return (
    <div className="relative w-28 h-28 flex items-center justify-center">
      <svg className="absolute inset-0 -rotate-90" viewBox="0 0 88 88">
        <circle cx="44" cy="44" r="40" fill="none" stroke="#e2e8f0" strokeWidth="6" />
        <circle cx="44" cy="44" r="40" fill="none" className={ring} strokeWidth="6"
          strokeDasharray={`${dash} ${circumference}`} strokeLinecap="round" />
      </svg>
      <div className="text-center">
        <div className={`text-3xl font-bold ${color}`}>{score}</div>
        <div className={`text-sm font-bold ${color}`}>{grade}</div>
      </div>
    </div>
  )
}

export default function ScorecardPage() {
  const [businessType, setBusinessType] = useState('saas')
  const [niche, setNiche] = useState('')
  const [metrics, setMetrics] = useState<Record<string, string>>(
    Object.fromEntries(DEFAULT_METRICS.map(m => [m.key, '']))
  )
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<ScorecardResult | null>(null)
  const [error, setError] = useState('')

  async function generate() {
    setLoading(true); setError(''); setResult(null)
    const numericMetrics = Object.fromEntries(
      Object.entries(metrics).filter(([, v]) => v !== '').map(([k, v]) => [k, parseFloat(v) || 0])
    )
    try {
      const res = await fetch(`${API}/scorecard/weekly`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ business_type: businessType, niche, metrics: numericMetrics }),
      })
      const data = await res.json()
      if (data.error) { setError(data.error); return }
      setResult(data)
    } catch { setError('Network error') } finally { setLoading(false) }
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-slate-800/10 flex items-center justify-center">
          <BarChart3 size={20} className="text-slate-700" />
        </div>
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Weekly Scorecard</h1>
          <p className="text-sm text-slate-500">Growth analysis + next-week priorities</p>
        </div>
      </div>

      {/* Form */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-5">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Business Type</label>
            <select className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-slate-500/20 bg-white"
              value={businessType} onChange={e => setBusinessType(e.target.value)}>
              {BUSINESS_TYPES.map(b => <option key={b} value={b}>{b}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Niche</label>
            <input className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-slate-500/20"
              placeholder="e.g. marketing automation" value={niche} onChange={e => setNiche(e.target.value)} />
          </div>
        </div>

        <div>
          <p className="text-xs font-semibold text-slate-600 mb-3">This Week's Metrics <span className="text-slate-400 font-normal">(fill in what you have)</span></p>
          <div className="grid grid-cols-2 gap-3">
            {DEFAULT_METRICS.map(({ key, label, placeholder }) => (
              <div key={key}>
                <label className="block text-[11px] text-slate-500 mb-1">{label}</label>
                <input type="number" className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-slate-500/20"
                  placeholder={placeholder}
                  value={metrics[key]} onChange={e => setMetrics(m => ({ ...m, [key]: e.target.value }))} />
              </div>
            ))}
          </div>
        </div>

        <button onClick={generate} disabled={loading}
          className="w-full flex items-center justify-center gap-2 py-3 bg-slate-800 hover:bg-slate-900 text-white text-sm font-bold rounded-xl transition-colors disabled:opacity-50">
          {loading ? <Loader2 size={16} className="animate-spin" /> : <BarChart3 size={16} />}
          {loading ? 'Generating scorecard…' : 'Generate Weekly Scorecard'}
        </button>
        {loading && (
          <div className="text-center">
            <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
              <div className="h-full bg-slate-600 animate-pulse rounded-full w-2/3" />
            </div>
            <p className="text-xs text-slate-400 mt-2">Takes 30–60 seconds</p>
          </div>
        )}
      </div>

      {error && (
        <div className="flex items-center gap-3 p-4 bg-red-50 border border-red-200 rounded-xl">
          <AlertCircle size={15} className="text-red-500 flex-shrink-0" />
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {result && (
        <div className="space-y-4">
          {/* Score summary */}
          <div className="bg-white border border-slate-200 rounded-xl p-6 flex items-center gap-6">
            <GradeCircle score={result.overall_score} grade={result.grade} />
            <div className="flex-1">
              <p className="text-sm text-slate-500 mb-1">Week ending {result.week_ending}</p>
              <h2 className="text-lg font-bold text-slate-800">Overall Growth Score</h2>
              {result['30_day_projection'] && (
                <p className="text-sm text-slate-600 mt-2">{result['30_day_projection']}</p>
              )}
            </div>
          </div>

          {/* Wins & Losses */}
          <div className="grid grid-cols-2 gap-4">
            {result.wins?.length > 0 && (
              <div className="bg-white border border-slate-200 rounded-xl p-5">
                <h3 className="text-sm font-semibold text-emerald-700 mb-3 flex items-center gap-2">
                  <CheckCircle2 size={14} /> Wins This Week
                </h3>
                <div className="space-y-2">
                  {result.wins.map((w, i) => (
                    <div key={i} className="flex items-start gap-2">
                      <CheckCircle2 size={12} className="text-emerald-500 mt-0.5 flex-shrink-0" />
                      <p className="text-sm text-slate-700">{w}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {result.losses?.length > 0 && (
              <div className="bg-white border border-slate-200 rounded-xl p-5">
                <h3 className="text-sm font-semibold text-red-700 mb-3 flex items-center gap-2">
                  <XCircle size={14} /> What Didn't Work
                </h3>
                <div className="space-y-2">
                  {result.losses.map((l, i) => (
                    <div key={i} className="flex items-start gap-2">
                      <XCircle size={12} className="text-red-400 mt-0.5 flex-shrink-0" />
                      <p className="text-sm text-slate-700">{l}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Top priority */}
          {result.top_priority_next_week && (
            <div className="bg-slate-900 text-white rounded-xl p-5">
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">Top Priority Next Week</p>
              <p className="text-base font-semibold">{result.top_priority_next_week}</p>
            </div>
          )}

          {/* Metrics analysis */}
          {result.metrics_analysis?.length > 0 && (
            <div className="bg-white border border-slate-200 rounded-xl p-5">
              <h3 className="text-sm font-semibold text-slate-700 mb-3">Metrics Breakdown</h3>
              <div className="space-y-3">
                {result.metrics_analysis.map((m, i) => (
                  <div key={i} className="flex items-start gap-3">
                    <div className="w-10 h-10 bg-slate-50 rounded-lg flex items-center justify-center flex-shrink-0">
                      <TrendIcon trend={m.trend} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-medium text-slate-800">{m.metric}</p>
                        <span className="text-xs text-slate-500">{m.vs_benchmark}</span>
                      </div>
                      <p className="text-xs text-slate-500">{m.insight}</p>
                    </div>
                    <div className="text-right flex-shrink-0">
                      <p className="text-sm font-bold text-slate-800">{m.score}/100</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Experiments to run */}
          {result.experiments_to_run?.length > 0 && (
            <div className="bg-white border border-slate-200 rounded-xl p-5">
              <h3 className="text-sm font-semibold text-slate-700 mb-3">Experiments to Run Next Week</h3>
              <div className="space-y-2">
                {result.experiments_to_run.map((exp, i) => (
                  <div key={i} className="flex items-start gap-3 bg-slate-50 rounded-lg p-3">
                    <span className="w-5 h-5 rounded bg-violet-100 text-violet-700 text-xs font-bold flex items-center justify-center flex-shrink-0">{i + 1}</span>
                    <div className="flex-1">
                      <p className="text-sm text-slate-800">{exp.experiment}</p>
                      <p className="text-xs text-slate-500">{exp.expected_impact}</p>
                    </div>
                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium flex-shrink-0 ${
                      exp.effort === 'low' ? 'bg-emerald-100 text-emerald-700' :
                      exp.effort === 'medium' ? 'bg-amber-100 text-amber-700' : 'bg-red-100 text-red-700'
                    }`}>{exp.effort}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Channel performance */}
          {result.channels_performance?.length > 0 && (
            <div className="bg-white border border-slate-200 rounded-xl p-5">
              <h3 className="text-sm font-semibold text-slate-700 mb-3">Channel Performance</h3>
              <div className="space-y-3">
                {result.channels_performance.map((ch, i) => (
                  <div key={i} className="flex items-center gap-4">
                    <div className="w-20 text-xs font-medium text-slate-600 flex-shrink-0">{ch.channel}</div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <div className="flex-1 bg-slate-100 rounded-full h-1.5">
                          <div className="h-full bg-blue-500 rounded-full" style={{ width: `${ch.score}%` }} />
                        </div>
                        <span className="text-xs text-slate-600 w-8 text-right">{ch.score}</span>
                        <TrendIcon trend={ch.trend} />
                      </div>
                      <p className="text-xs text-slate-500">{ch.action}</p>
                    </div>
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

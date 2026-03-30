'use client'

import { useState, useEffect, useCallback } from 'react'
import { apiFetch } from '@/lib/apiFetch'
import {
  Brain,
  TrendingUp,
  TrendingDown,
  ArrowUpRight,
  CheckCircle,
  XCircle,
  AlertCircle,
  RefreshCw,
  ChevronRight,
  Zap,
  BarChart2,
} from 'lucide-react'

interface LearningSummary {
  total_strategies_recorded: number
  total_measured: number
  total_successes: number
  total_failures: number
  success_rate: number | null
  total_hypotheses: number
  confirmed_hypotheses: number
  rejected_hypotheses: number
  suppressed_patterns: number
  promoted_patterns: number
  suppressed: Array<{ strategy_type: string; niche: string; failure_rate: number; note: string }>
  promoted: Array<{ strategy_type: string; niche: string; success_rate: number; note: string }>
  recent_successes: Array<{ title: string; channel: string; niche: string }>
  recent_failures: Array<{ title: string; channel: string; niche: string }>
}

interface Strategy {
  id: string
  strategy_title: string
  strategy_type: string
  channel: string
  niche: string
  outcome: string | null
  confidence_before: number
  confidence_after: number | null
  created_at: string
}

interface Hypothesis {
  id: string
  hypothesis: string
  channel: string
  niche: string
  result: string | null
  created_at: string
}

export default function LearningPage() {
  const [summary, setSummary] = useState<LearningSummary | null>(null)
  const [strategies, setStrategies] = useState<Strategy[]>([])
  const [hypotheses, setHypotheses] = useState<Hypothesis[]>([])
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<'overview' | 'strategies' | 'hypotheses' | 'patterns'>('overview')

  const load = useCallback(async () => {
    try {
      const [summaryRes, strategiesData, hypothesesData] = await Promise.all([
        apiFetch<{ summary: LearningSummary }>('/api/v1/learning/summary'),
        apiFetch<{ items: Strategy[] }>('/api/v1/learning/strategies'),
        apiFetch<{ items: Hypothesis[] }>('/api/v1/learning/hypotheses'),
      ])
      setSummary(summaryRes.summary ?? null)
      setStrategies(strategiesData.items ?? [])
      setHypotheses(hypothesesData.items ?? [])
    } catch {
      // keep state
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const TABS = [
    { key: 'overview', label: 'Overview' },
    { key: 'strategies', label: `Strategies (${strategies.length})` },
    { key: 'hypotheses', label: `Hypotheses (${hypotheses.length})` },
    { key: 'patterns', label: 'Patterns' },
  ] as const

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-black rounded-lg">
            <Brain className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-semibold">Learning Loop</h1>
            <p className="text-sm text-gray-500">What the system knows, what it's learning, and why it's changing strategy</p>
          </div>
        </div>
        <button
          onClick={() => { setLoading(true); load() }}
          className="flex items-center gap-2 px-3 py-1.5 border border-gray-200 rounded-lg text-sm hover:bg-gray-50"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Refresh
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-200">
        {TABS.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === t.key
                ? 'border-black text-gray-900'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-32">
          <div className="w-6 h-6 border-2 border-black border-t-transparent rounded-full animate-spin" />
        </div>
      ) : (
        <>
          {/* Overview Tab */}
          {tab === 'overview' && summary && (
            <div className="space-y-6">
              {/* KPI Row */}
              <div className="grid grid-cols-4 gap-4">
                {[
                  { label: 'Strategies Tested', value: summary.total_measured, sub: `of ${summary.total_strategies_recorded} recorded`, icon: BarChart2, color: 'text-blue-600' },
                  { label: 'Success Rate', value: summary.success_rate !== null ? `${Math.round(summary.success_rate * 100)}%` : '—', sub: `${summary.total_successes} successes`, icon: TrendingUp, color: 'text-green-600' },
                  { label: 'Suppressed', value: summary.suppressed_patterns, sub: 'failing patterns avoided', icon: TrendingDown, color: 'text-red-500' },
                  { label: 'Promoted', value: summary.promoted_patterns, sub: 'winning patterns amplified', icon: ArrowUpRight, color: 'text-green-600' },
                ].map(({ label, value, sub, icon: Icon, color }) => (
                  <div key={label} className="bg-white border border-gray-200 rounded-xl p-4">
                    <div className={`${color} mb-2`}><Icon className="w-4 h-4" /></div>
                    <div className="text-2xl font-bold">{value}</div>
                    <div className="text-xs text-gray-500 mt-1">{label}</div>
                    <div className="text-xs text-gray-400">{sub}</div>
                  </div>
                ))}
              </div>

              {/* What Changed */}
              <div className="grid grid-cols-2 gap-4">
                {/* Recent Wins */}
                <div className="bg-white border border-gray-200 rounded-xl p-5">
                  <h2 className="font-medium text-sm mb-3 flex items-center gap-2">
                    <TrendingUp className="w-4 h-4 text-green-600" />
                    What&apos;s Working
                  </h2>
                  {summary.recent_successes.length === 0 ? (
                    <p className="text-xs text-gray-400">No confirmed successes yet — keep testing</p>
                  ) : (
                    <ul className="space-y-2">
                      {summary.recent_successes.map((s, i) => (
                        <li key={i} className="flex items-center gap-2 text-sm">
                          <CheckCircle className="w-4 h-4 text-green-500 flex-shrink-0" />
                          <span className="text-gray-700 truncate">{s.title}</span>
                          <span className="text-xs text-gray-400 ml-auto flex-shrink-0">{s.channel}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>

                {/* Recent Losses */}
                <div className="bg-white border border-gray-200 rounded-xl p-5">
                  <h2 className="font-medium text-sm mb-3 flex items-center gap-2">
                    <TrendingDown className="w-4 h-4 text-red-500" />
                    What&apos;s Not Working
                  </h2>
                  {summary.recent_failures.length === 0 ? (
                    <p className="text-xs text-gray-400">No failures recorded yet</p>
                  ) : (
                    <ul className="space-y-2">
                      {summary.recent_failures.map((f, i) => (
                        <li key={i} className="flex items-center gap-2 text-sm">
                          <XCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
                          <span className="text-gray-700 truncate">{f.title}</span>
                          <span className="text-xs text-gray-400 ml-auto flex-shrink-0">{f.channel}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>

              {/* Hypotheses Summary */}
              <div className="bg-white border border-gray-200 rounded-xl p-5">
                <h2 className="font-medium text-sm mb-3 flex items-center gap-2">
                  <Zap className="w-4 h-4 text-blue-600" />
                  Active Hypotheses
                </h2>
                <div className="grid grid-cols-3 gap-4 text-sm">
                  <div className="text-center">
                    <div className="text-2xl font-bold">{summary.total_hypotheses}</div>
                    <div className="text-xs text-gray-500">Total proposed</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-green-600">{summary.confirmed_hypotheses}</div>
                    <div className="text-xs text-gray-500">Confirmed</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-red-500">{summary.rejected_hypotheses}</div>
                    <div className="text-xs text-gray-500">Rejected</div>
                  </div>
                </div>
              </div>

              {/* No data yet */}
              {summary.total_strategies_recorded === 0 && (
                <div className="flex items-start gap-3 p-4 bg-blue-50 border border-blue-200 rounded-xl text-sm text-blue-800">
                  <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                  <div>
                    The learning loop activates once your strategies are measured against real outcomes.
                    Publish content, run campaigns, and record results to start building the learning model.
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Strategies Tab */}
          {tab === 'strategies' && (
            <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
              {strategies.length === 0 ? (
                <div className="text-center py-12 text-gray-400">
                  <Brain className="w-8 h-8 mx-auto mb-3 opacity-30" />
                  <p className="text-sm">No strategies recorded yet</p>
                </div>
              ) : (
                <div className="divide-y divide-gray-100">
                  {strategies.map(s => (
                    <div key={s.id} className="flex items-center gap-4 p-4 hover:bg-gray-50">
                      <div className={`w-2 h-2 rounded-full flex-shrink-0 ${
                        s.outcome === 'success' ? 'bg-green-500'
                        : s.outcome === 'failure' ? 'bg-red-400'
                        : 'bg-gray-300'
                      }`} />
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-gray-800 truncate">{s.strategy_title}</div>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className="text-xs text-gray-400">{s.strategy_type}</span>
                          <span className="text-gray-200">·</span>
                          <span className="text-xs text-gray-400">{s.channel}</span>
                          <span className="text-gray-200">·</span>
                          <span className="text-xs text-gray-400">{s.niche}</span>
                        </div>
                      </div>
                      <div className="text-right flex-shrink-0">
                        <div className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                          s.outcome === 'success' ? 'bg-green-50 text-green-700'
                          : s.outcome === 'failure' ? 'bg-red-50 text-red-600'
                          : 'bg-gray-100 text-gray-500'
                        }`}>
                          {s.outcome ?? 'pending'}
                        </div>
                        {s.confidence_after !== null && (
                          <div className={`text-xs mt-1 ${
                            (s.confidence_after ?? 0) > s.confidence_before ? 'text-green-600' : 'text-red-500'
                          }`}>
                            {s.confidence_before.toFixed(2)} → {s.confidence_after.toFixed(2)}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Hypotheses Tab */}
          {tab === 'hypotheses' && (
            <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
              {hypotheses.length === 0 ? (
                <div className="text-center py-12 text-gray-400">
                  <Zap className="w-8 h-8 mx-auto mb-3 opacity-30" />
                  <p className="text-sm">No hypotheses proposed yet</p>
                  <p className="text-xs mt-1">The system proposes hypotheses as it tests strategy variations</p>
                </div>
              ) : (
                <div className="divide-y divide-gray-100">
                  {hypotheses.map(h => (
                    <div key={h.id} className="flex items-start gap-4 p-4 hover:bg-gray-50">
                      <div className={`mt-1 flex-shrink-0 ${
                        h.result === 'confirmed' ? 'text-green-500'
                        : h.result === 'rejected' ? 'text-red-400'
                        : 'text-gray-300'
                      }`}>
                        {h.result === 'confirmed' ? <CheckCircle className="w-4 h-4" />
                        : h.result === 'rejected' ? <XCircle className="w-4 h-4" />
                        : <AlertCircle className="w-4 h-4" />}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-gray-800">{h.hypothesis}</p>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="text-xs text-gray-400">{h.channel}</span>
                          <span className="text-gray-200">·</span>
                          <span className="text-xs text-gray-400">{h.niche}</span>
                        </div>
                      </div>
                      <span className={`text-xs px-2 py-0.5 rounded-full flex-shrink-0 ${
                        h.result === 'confirmed' ? 'bg-green-50 text-green-700'
                        : h.result === 'rejected' ? 'bg-red-50 text-red-600'
                        : 'bg-gray-100 text-gray-500'
                      }`}>
                        {h.result ?? 'running'}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Patterns Tab */}
          {tab === 'patterns' && summary && (
            <div className="space-y-4">
              {/* Promoted */}
              <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
                <div className="flex items-center gap-2 p-4 border-b border-gray-100 bg-green-50">
                  <ArrowUpRight className="w-4 h-4 text-green-600" />
                  <h2 className="font-medium text-sm text-green-800">Promoted Patterns (amplified by system)</h2>
                </div>
                {summary.promoted.length === 0 ? (
                  <div className="p-6 text-center text-sm text-gray-400">No promoted patterns yet — need ≥ 70% success rate across 3+ tests</div>
                ) : (
                  <div className="divide-y divide-gray-100">
                    {summary.promoted.map((p, i) => (
                      <div key={i} className="flex items-center gap-4 p-4">
                        <ChevronRight className="w-4 h-4 text-green-500" />
                        <div className="flex-1">
                          <span className="text-sm text-gray-800">{p.strategy_type}</span>
                          <span className="text-xs text-gray-400 ml-2">· {p.niche}</span>
                        </div>
                        <span className="text-xs text-green-700 font-medium">{Math.round(p.success_rate * 100)}% success</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Suppressed */}
              <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
                <div className="flex items-center gap-2 p-4 border-b border-gray-100 bg-red-50">
                  <TrendingDown className="w-4 h-4 text-red-500" />
                  <h2 className="font-medium text-sm text-red-800">Suppressed Patterns (avoided by system)</h2>
                </div>
                {summary.suppressed.length === 0 ? (
                  <div className="p-6 text-center text-sm text-gray-400">No suppressed patterns yet — need ≥ 60% failure rate across 3+ tests</div>
                ) : (
                  <div className="divide-y divide-gray-100">
                    {summary.suppressed.map((s, i) => (
                      <div key={i} className="flex items-center gap-4 p-4">
                        <XCircle className="w-4 h-4 text-red-400" />
                        <div className="flex-1">
                          <span className="text-sm text-gray-800">{s.strategy_type}</span>
                          <span className="text-xs text-gray-400 ml-2">· {s.niche}</span>
                        </div>
                        <span className="text-xs text-red-600 font-medium">{Math.round(s.failure_rate * 100)}% failure</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}

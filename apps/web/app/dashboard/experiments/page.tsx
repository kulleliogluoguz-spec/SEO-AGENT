'use client'

import { useState, useEffect } from 'react'
import {
  FlaskConical, TrendingUp, TrendingDown, Minus,
  CheckCircle, XCircle, AlertCircle, Clock, Plus,
  BarChart2, Loader2, ChevronDown, ChevronUp,
  Target, Lightbulb, ShieldOff, Zap
} from 'lucide-react'
import { apiFetch } from '@/lib/apiFetch'

// ── Types ─────────────────────────────────────────────────────────────────────

interface LearningConfig {
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
  suppressed: PatternRecord[]
  promoted: PatternRecord[]
  recent_successes: { title: string; channel: string | null; niche: string }[]
  recent_failures: { title: string; channel: string | null; niche: string }[]
}

interface PatternRecord {
  id: string
  pattern_key: string
  niche: string
  strategy_type: string
  failure_rate?: number
  success_rate?: number
  sample_size: number
  note: string
}

interface StrategyRecord {
  id: string
  strategy_type: string
  strategy_title: string
  niche: string
  channel: string | null
  outcome: 'success' | 'failure' | 'partial' | null
  status: string
  created_at: string
  measured_at: string | null
}

interface HypothesisRecord {
  id: string
  hypothesis: string
  rationale: string
  channel: string | null
  niche: string
  test_type: string
  metric_to_track: string
  expected_lift_pct: number
  actual_lift_pct: number | null
  result: 'confirmed' | 'rejected' | 'inconclusive' | null
  status: string
  created_at: string
  completed_at: string | null
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

const OUTCOME_META: Record<string, { icon: React.ReactNode; label: string; cls: string }> = {
  success:    { icon: <CheckCircle size={12} />, label: 'Success',    cls: 'text-emerald-600 bg-emerald-50 border-emerald-100' },
  failure:    { icon: <XCircle     size={12} />, label: 'Failure',    cls: 'text-red-600     bg-red-50     border-red-100'     },
  partial:    { icon: <Minus       size={12} />, label: 'Partial',    cls: 'text-amber-600   bg-amber-50   border-amber-100'   },
  pending:    { icon: <Clock       size={12} />, label: 'Pending',    cls: 'text-gray-400    bg-gray-50    border-gray-100'    },
}

const RESULT_META: Record<string, { icon: React.ReactNode; label: string; cls: string }> = {
  confirmed:   { icon: <CheckCircle size={12} />, label: 'Confirmed',   cls: 'text-emerald-600 bg-emerald-50 border-emerald-100' },
  rejected:    { icon: <XCircle     size={12} />, label: 'Rejected',    cls: 'text-red-600     bg-red-50     border-red-100'     },
  inconclusive:{ icon: <Minus       size={12} />, label: 'Inconclusive',cls: 'text-amber-600   bg-amber-50   border-amber-100'   },
  proposed:    { icon: <Clock       size={12} />, label: 'Proposed',    cls: 'text-blue-600    bg-blue-50    border-blue-100'    },
}

// ── Sub-components ────────────────────────────────────────────────────────────

function StatCard({ label, value, sub, accent }: { label: string; value: string | number; sub?: string; accent?: string }) {
  return (
    <div className="card p-5">
      <p className="text-xs text-gray-400 font-medium mb-1">{label}</p>
      <p className={`text-2xl font-bold ${accent ?? 'text-gray-900'}`}>{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </div>
  )
}

function StrategyRow({ record }: { record: StrategyRecord }) {
  const meta = record.outcome ? OUTCOME_META[record.outcome] : OUTCOME_META.pending
  return (
    <div className="flex items-center gap-4 py-3 border-b border-gray-50 last:border-0">
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-800 truncate">{record.strategy_title}</p>
        <p className="text-xs text-gray-400 mt-0.5">
          {record.strategy_type.replace(/_/g, ' ')} · {record.niche}
          {record.channel && ` · ${record.channel}`}
        </p>
      </div>
      <div className="flex items-center gap-2 flex-shrink-0">
        <span className={`badge text-[10px] border flex items-center gap-0.5 ${meta.cls}`}>
          {meta.icon}<span className="ml-0.5">{meta.label}</span>
        </span>
        <span className="text-[10px] text-gray-300">{fmtDate(record.created_at)}</span>
      </div>
    </div>
  )
}

function HypothesisRow({ record }: { record: HypothesisRecord }) {
  const [open, setOpen] = useState(false)
  const meta = record.result ? RESULT_META[record.result] : RESULT_META[record.status] ?? RESULT_META.proposed

  return (
    <div className="card overflow-hidden">
      <button onClick={() => setOpen(o => !o)}
        className="w-full flex items-center gap-4 p-4 hover:bg-gray-50/50 transition-colors text-left">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-800 leading-snug">{record.hypothesis}</p>
          <p className="text-xs text-gray-400 mt-0.5">
            {record.niche} · {record.test_type.replace(/_/g, ' ')} · tracking {record.metric_to_track.replace(/_/g, ' ')}
          </p>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {record.actual_lift_pct !== null && (
            <span className={`text-xs font-semibold ${record.actual_lift_pct >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
              {record.actual_lift_pct >= 0 ? '+' : ''}{record.actual_lift_pct.toFixed(1)}%
            </span>
          )}
          <span className={`badge text-[10px] border flex items-center gap-0.5 ${meta.cls}`}>
            {meta.icon}<span className="ml-0.5">{meta.label}</span>
          </span>
          {open ? <ChevronUp size={13} className="text-gray-300" /> : <ChevronDown size={13} className="text-gray-300" />}
        </div>
      </button>

      {open && (
        <div className="px-4 pb-4 pt-0 border-t border-gray-50 space-y-3">
          <div className="mt-3 p-3 bg-gray-50 rounded-lg">
            <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-1">Rationale</p>
            <p className="text-xs text-gray-600">{record.rationale}</p>
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-1">Expected Lift</p>
              <p className="text-sm font-semibold text-gray-800">+{record.expected_lift_pct}%</p>
            </div>
            <div>
              <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-1">Actual Lift</p>
              <p className={`text-sm font-semibold ${record.actual_lift_pct === null ? 'text-gray-300' : record.actual_lift_pct >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                {record.actual_lift_pct === null ? '—' : `${record.actual_lift_pct >= 0 ? '+' : ''}${record.actual_lift_pct.toFixed(1)}%`}
              </p>
            </div>
            <div>
              <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-1">Duration</p>
              <p className="text-sm font-semibold text-gray-800">
                {(record as any).test_duration_days ?? '—'} days
              </p>
            </div>
          </div>
          <p className="text-[10px] text-gray-300">
            Created {fmtDate(record.created_at)}
            {record.completed_at && ` · Completed ${fmtDate(record.completed_at)}`}
          </p>
        </div>
      )}
    </div>
  )
}

function PatternPill({ pattern, type }: { pattern: PatternRecord; type: 'suppressed' | 'promoted' }) {
  const [niche, stratType] = pattern.pattern_key.split(':')
  return (
    <div className={`flex items-center gap-3 px-3 py-2.5 rounded-lg border ${type === 'suppressed' ? 'bg-red-50 border-red-100' : 'bg-emerald-50 border-emerald-100'}`}>
      <div className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 ${type === 'suppressed' ? 'bg-red-100' : 'bg-emerald-100'}`}>
        {type === 'suppressed'
          ? <ShieldOff size={11} className="text-red-500" />
          : <Zap size={11} className="text-emerald-600" />}
      </div>
      <div className="flex-1 min-w-0">
        <p className={`text-xs font-medium ${type === 'suppressed' ? 'text-red-800' : 'text-emerald-800'}`}>
          {stratType?.replace(/_/g, ' ')} in <span className="capitalize">{niche}</span>
        </p>
        <p className={`text-[10px] ${type === 'suppressed' ? 'text-red-500' : 'text-emerald-600'}`}>
          {type === 'suppressed'
            ? `${Math.round((pattern.failure_rate ?? 0) * 100)}% failure rate · ${pattern.sample_size} samples`
            : `${Math.round((pattern.success_rate ?? 0) * 100)}% success rate · ${pattern.sample_size} samples`}
        </p>
      </div>
    </div>
  )
}

// ── New Hypothesis Form ────────────────────────────────────────────────────────

function NewHypothesisModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [form, setForm] = useState({
    hypothesis: '', rationale: '', niche: '', channel: '',
    test_type: 'ab_test', metric_to_track: 'ctr',
    expected_lift_pct: '10', test_duration_days: '14',
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true); setError('')
    try {
      await apiFetch('/api/v1/learning/hypotheses', {
        method: 'POST',
        body: JSON.stringify({
          ...form,
          expected_lift_pct: parseFloat(form.expected_lift_pct),
          test_duration_days: parseInt(form.test_duration_days),
          channel: form.channel || null,
        }),
      })
      onCreated()
      onClose()
    } catch {
      setError('Failed to save. Check backend connection.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg">
        <div className="p-6 border-b border-gray-100">
          <h2 className="text-base font-semibold text-gray-900">New Hypothesis</h2>
          <p className="text-xs text-gray-400 mt-0.5">Define a testable assumption to validate with data</p>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="input-label">Hypothesis *</label>
            <textarea className="input text-sm resize-none" rows={2}
              placeholder='e.g. "Adding video to Instagram posts increases CTR by 15%"'
              value={form.hypothesis} onChange={e => setForm(f => ({ ...f, hypothesis: e.target.value }))} required />
          </div>
          <div>
            <label className="input-label">Rationale *</label>
            <textarea className="input text-sm resize-none" rows={2}
              placeholder="Why do you believe this? What evidence or insight led to this hypothesis?"
              value={form.rationale} onChange={e => setForm(f => ({ ...f, rationale: e.target.value }))} required />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="input-label">Niche *</label>
              <input className="input text-sm" placeholder="e.g. ecommerce, saas"
                value={form.niche} onChange={e => setForm(f => ({ ...f, niche: e.target.value }))} required />
            </div>
            <div>
              <label className="input-label">Channel (optional)</label>
              <input className="input text-sm" placeholder="instagram, google, email"
                value={form.channel} onChange={e => setForm(f => ({ ...f, channel: e.target.value }))} />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="input-label">Test Type</label>
              <select className="input text-sm" value={form.test_type} onChange={e => setForm(f => ({ ...f, test_type: e.target.value }))}>
                <option value="ab_test">A/B Test</option>
                <option value="before_after">Before / After</option>
                <option value="holdout">Holdout</option>
                <option value="multivariate">Multivariate</option>
              </select>
            </div>
            <div>
              <label className="input-label">Metric to Track</label>
              <select className="input text-sm" value={form.metric_to_track} onChange={e => setForm(f => ({ ...f, metric_to_track: e.target.value }))}>
                <option value="ctr">CTR</option>
                <option value="cpa">CPA</option>
                <option value="roas">ROAS</option>
                <option value="engagement_rate">Engagement Rate</option>
                <option value="follower_growth">Follower Growth</option>
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="input-label">Expected Lift %</label>
              <input className="input text-sm" type="number" min="0" max="500" step="0.5"
                value={form.expected_lift_pct} onChange={e => setForm(f => ({ ...f, expected_lift_pct: e.target.value }))} />
            </div>
            <div>
              <label className="input-label">Test Duration (days)</label>
              <input className="input text-sm" type="number" min="1" max="90"
                value={form.test_duration_days} onChange={e => setForm(f => ({ ...f, test_duration_days: e.target.value }))} />
            </div>
          </div>

          {error && <p className="text-xs text-red-500">{error}</p>}

          <div className="flex items-center gap-2 pt-1">
            <button type="submit" disabled={saving} className="btn-primary text-sm">
              {saving && <Loader2 size={13} className="animate-spin" />}
              {saving ? 'Saving…' : 'Create Hypothesis'}
            </button>
            <button type="button" onClick={onClose} className="btn-ghost text-sm">Cancel</button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ExperimentsPage() {
  const [summary, setSummary] = useState<LearningConfig | null>(null)
  const [strategies, setStrategies] = useState<StrategyRecord[]>([])
  const [hypotheses, setHypotheses] = useState<HypothesisRecord[]>([])
  const [suppressed, setSuppressed] = useState<PatternRecord[]>([])
  const [promoted, setPromoted] = useState<PatternRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<'overview' | 'strategies' | 'hypotheses' | 'patterns'>('overview')
  const [showNewHypothesis, setShowNewHypothesis] = useState(false)

  async function load() {
    try {
      const [sumData, stratData, hypData, supData, proData] = await Promise.all([
        apiFetch<LearningConfig>('/api/v1/learning/summary').catch(() => null),
        apiFetch<unknown>('/api/v1/learning/strategies?limit=100').catch(() => null),
        apiFetch<unknown>('/api/v1/learning/hypotheses?limit=100').catch(() => null),
        apiFetch<unknown>('/api/v1/learning/suppressed').catch(() => null),
        apiFetch<unknown>('/api/v1/learning/promoted').catch(() => null),
      ])
      if (sumData)  setSummary(sumData)
      if (stratData) setStrategies((stratData as any).records ?? (stratData as any).items ?? (Array.isArray(stratData) ? stratData : []))
      if (hypData)   setHypotheses((hypData as any).hypotheses ?? (hypData as any).items ?? (Array.isArray(hypData) ? hypData : []))
      if (supData)   setSuppressed((supData as any).patterns ?? (Array.isArray(supData) ? supData : []))
      if (proData)   setPromoted((proData as any).patterns ?? (Array.isArray(proData) ? proData : []))
    } catch {}
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  const successRate = summary?.success_rate != null
    ? `${Math.round(summary.success_rate * 100)}%` : '—'

  return (
    <div className="space-y-6">

      {showNewHypothesis && (
        <NewHypothesisModal onClose={() => setShowNewHypothesis(false)} onCreated={load} />
      )}

      <div className="page-header">
        <div>
          <h1 className="page-title">Experiments</h1>
          <p className="page-subtitle">Learning loop — track strategy outcomes, run hypothesis tests, amplify winners</p>
        </div>
        <button className="btn-primary" onClick={() => setShowNewHypothesis(true)}>
          <Plus size={14} /> New Hypothesis
        </button>
      </div>

      {loading ? (
        <div className="flex items-center gap-2 text-sm text-gray-400 py-8">
          <Loader2 size={14} className="animate-spin" /> Loading learning data…
        </div>
      ) : (
        <>
          {/* Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard label="Strategies Recorded" value={summary?.total_strategies_recorded ?? 0} sub={`${summary?.total_measured ?? 0} measured`} />
            <StatCard
              label="Success Rate"
              value={successRate}
              sub={`${summary?.total_successes ?? 0} wins · ${summary?.total_failures ?? 0} losses`}
              accent={summary?.success_rate != null && summary.success_rate >= 0.6 ? 'text-emerald-600' : summary?.success_rate != null ? 'text-red-500' : undefined}
            />
            <StatCard label="Hypotheses" value={summary?.total_hypotheses ?? 0} sub={`${summary?.confirmed_hypotheses ?? 0} confirmed`} />
            <StatCard label="Patterns Learned" value={(summary?.promoted_patterns ?? 0) + (summary?.suppressed_patterns ?? 0)} sub={`${summary?.promoted_patterns ?? 0} promoted · ${summary?.suppressed_patterns ?? 0} suppressed`} />
          </div>

          {/* Empty state */}
          {(summary?.total_strategies_recorded ?? 0) === 0 && (
            <div className="card p-10 text-center">
              <FlaskConical size={36} className="mx-auto text-gray-200 mb-3" />
              <h3 className="font-medium text-gray-700 mb-1">No learning data yet</h3>
              <p className="text-sm text-gray-400 max-w-sm mx-auto">
                The learning loop activates as soon as strategies are approved and their outcomes recorded.
                Start by using the Content or Media Plan pages to generate recommendations.
              </p>
            </div>
          )}

          {/* Tabs */}
          {(summary?.total_strategies_recorded ?? 0) > 0 && (
            <>
              <div className="flex items-center gap-1 border-b border-gray-100">
                {(['overview', 'strategies', 'hypotheses', 'patterns'] as const).map(t => (
                  <button key={t} onClick={() => setTab(t)}
                    className={`px-4 py-2 text-sm font-medium capitalize border-b-2 transition-colors ${tab === t ? 'border-brand-600 text-brand-600' : 'border-transparent text-gray-400 hover:text-gray-600'}`}>
                    {t}
                  </button>
                ))}
              </div>

              {/* Overview tab */}
              {tab === 'overview' && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="card p-5">
                    <div className="flex items-center gap-2 mb-3">
                      <TrendingUp size={14} className="text-emerald-500" />
                      <h3 className="text-sm font-semibold text-gray-800">Recent Successes</h3>
                    </div>
                    {summary?.recent_successes?.length ? (
                      <div className="space-y-2">
                        {summary.recent_successes.map((s, i) => (
                          <div key={i} className="flex items-center gap-2">
                            <CheckCircle size={12} className="text-emerald-500 flex-shrink-0" />
                            <span className="text-xs text-gray-700 truncate">{s.title}</span>
                            <span className="text-[10px] text-gray-400 flex-shrink-0 capitalize">{s.channel ?? s.niche}</span>
                          </div>
                        ))}
                      </div>
                    ) : <p className="text-xs text-gray-300">No successes recorded yet</p>}
                  </div>
                  <div className="card p-5">
                    <div className="flex items-center gap-2 mb-3">
                      <TrendingDown size={14} className="text-red-400" />
                      <h3 className="text-sm font-semibold text-gray-800">Recent Failures</h3>
                    </div>
                    {summary?.recent_failures?.length ? (
                      <div className="space-y-2">
                        {summary.recent_failures.map((f, i) => (
                          <div key={i} className="flex items-center gap-2">
                            <XCircle size={12} className="text-red-400 flex-shrink-0" />
                            <span className="text-xs text-gray-700 truncate">{f.title}</span>
                            <span className="text-[10px] text-gray-400 flex-shrink-0 capitalize">{f.channel ?? f.niche}</span>
                          </div>
                        ))}
                      </div>
                    ) : <p className="text-xs text-gray-300">No failures recorded yet</p>}
                  </div>
                  <div className="card p-5 md:col-span-2">
                    <div className="flex items-center gap-2 mb-3">
                      <Lightbulb size={14} className="text-amber-500" />
                      <h3 className="text-sm font-semibold text-gray-800">How the Learning Loop Works</h3>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                      {[
                        { step: '1', title: 'Recommend', desc: 'System recommends a strategy (channel, content, budget)' },
                        { step: '2', title: 'Execute', desc: 'You approve, execute the campaign or content piece' },
                        { step: '3', title: 'Measure', desc: 'Record the actual outcome — success, failure, or partial' },
                        { step: '4', title: 'Adapt', desc: 'System suppresses failures and amplifies winning patterns' },
                      ].map(({ step, title, desc }) => (
                        <div key={step} className="flex items-start gap-2.5 p-3 bg-gray-50 rounded-lg">
                          <div className="w-5 h-5 rounded-full bg-brand-600 flex items-center justify-center flex-shrink-0 mt-0.5">
                            <span className="text-white text-[10px] font-bold">{step}</span>
                          </div>
                          <div>
                            <p className="text-xs font-semibold text-gray-800">{title}</p>
                            <p className="text-[10px] text-gray-500 mt-0.5">{desc}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Strategies tab */}
              {tab === 'strategies' && (
                <div className="card p-0 overflow-hidden">
                  <div className="px-5 py-4 border-b border-gray-50 flex items-center justify-between">
                    <h3 className="text-sm font-semibold text-gray-800">Strategy Records</h3>
                    <span className="text-xs text-gray-400">{strategies.length} total</span>
                  </div>
                  <div className="divide-y divide-gray-50 px-5">
                    {strategies.length === 0
                      ? <p className="py-8 text-center text-sm text-gray-300">No strategies recorded yet</p>
                      : strategies.map(r => <StrategyRow key={r.id} record={r} />)
                    }
                  </div>
                </div>
              )}

              {/* Hypotheses tab */}
              {tab === 'hypotheses' && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-semibold text-gray-800">{hypotheses.length} Hypotheses</h3>
                    <button className="btn-secondary text-xs py-1.5" onClick={() => setShowNewHypothesis(true)}>
                      <Plus size={12} /> New
                    </button>
                  </div>
                  {hypotheses.length === 0
                    ? (
                      <div className="card p-10 text-center">
                        <FlaskConical size={28} className="mx-auto text-gray-200 mb-2" />
                        <p className="text-sm text-gray-400">No hypotheses yet. Propose one to start running structured experiments.</p>
                      </div>
                    )
                    : hypotheses.map(h => <HypothesisRow key={h.id} record={h} />)
                  }
                </div>
              )}

              {/* Patterns tab */}
              {tab === 'patterns' && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <div className="flex items-center gap-2 mb-3">
                      <Zap size={13} className="text-emerald-500" />
                      <h3 className="text-sm font-semibold text-gray-800">Promoted Patterns</h3>
                      <span className="text-xs text-gray-400 ml-auto">{promoted.length}</span>
                    </div>
                    {promoted.length === 0
                      ? <p className="text-sm text-gray-300 py-4">None yet — patterns promote after 70%+ success rate over ≥3 samples</p>
                      : <div className="space-y-2">{promoted.map(p => <PatternPill key={p.id} pattern={p} type="promoted" />)}</div>
                    }
                  </div>
                  <div>
                    <div className="flex items-center gap-2 mb-3">
                      <ShieldOff size={13} className="text-red-400" />
                      <h3 className="text-sm font-semibold text-gray-800">Suppressed Patterns</h3>
                      <span className="text-xs text-gray-400 ml-auto">{suppressed.length}</span>
                    </div>
                    {suppressed.length === 0
                      ? <p className="text-sm text-gray-300 py-4">None yet — patterns suppress after 60%+ failure rate over ≥3 samples</p>
                      : <div className="space-y-2">{suppressed.map(p => <PatternPill key={p.id} pattern={p} type="suppressed" />)}</div>
                    }
                  </div>
                </div>
              )}
            </>
          )}
        </>
      )}
    </div>
  )
}

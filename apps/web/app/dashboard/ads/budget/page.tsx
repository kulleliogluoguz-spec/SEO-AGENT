'use client'

import { useState } from 'react'
import { DollarSign, Loader2, Zap, ArrowRight, AlertCircle, CheckCircle2 } from 'lucide-react'
import { apiFetch } from '@/lib/apiFetch'

interface OptimizationResult {
  optimization_id: string
  total_budget: number
  current_allocation: Record<string, number>
  optimal_allocation: Record<string, number>
  expected_uplift_pct: number
  ai_explanation: string
}

export default function BudgetOptimizerPage() {
  const [budget, setBudget] = useState<string>('10000')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<OptimizationResult | null>(null)
  const [applying, setApplying] = useState(false)
  const [applied, setApplied] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function optimize() {
    const total = parseFloat(budget)
    if (!total || total <= 0) { setError('Enter a valid budget'); return }
    setLoading(true); setError(null); setApplied(false)
    try {
      const data = await apiFetch<OptimizationResult>(`/api/v1/ads/portfolio/budget-optimization?total_budget=${total}`, {
        timeoutMs: 60_000,
      })
      setResult(data)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Optimization failed')
    } finally {
      setLoading(false)
    }
  }

  async function apply() {
    if (!result) return
    setApplying(true)
    try {
      await apiFetch(`/api/v1/ads/portfolio/budget-optimization/apply?optimization_id=${result.optimization_id}`, {
        method: 'POST',
      })
      setApplied(true)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Apply failed')
    } finally {
      setApplying(false)
    }
  }

  return (
    <div className="space-y-6 max-w-5xl">
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 bg-emerald-100 rounded-xl flex items-center justify-center">
          <DollarSign size={16} className="text-emerald-600" />
        </div>
        <div>
          <h1 className="text-lg font-bold text-gray-900">Budget Optimizer</h1>
          <p className="text-xs text-gray-500">AI-powered budget reallocation across your campaigns</p>
        </div>
      </div>

      {/* Input */}
      <div className="card p-5">
        <label className="block text-xs font-semibold text-gray-700 mb-2">Total monthly budget (USD)</label>
        <div className="flex items-center gap-3">
          <div className="relative flex-1 max-w-xs">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">$</span>
            <input
              type="number"
              value={budget}
              onChange={e => setBudget(e.target.value)}
              className="w-full pl-7 pr-3 py-2 text-sm rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-emerald-500/30"
              placeholder="10000"
            />
          </div>
          <button
            onClick={optimize}
            disabled={loading}
            className="flex items-center gap-2 px-5 py-2 bg-emerald-600 text-white rounded-lg text-sm font-semibold hover:bg-emerald-700 disabled:opacity-40"
          >
            {loading ? <Loader2 size={14} className="animate-spin" /> : <Zap size={14} />}
            {loading ? 'Optimizing...' : 'Optimize with AI'}
          </button>
        </div>
        {error && (
          <div className="mt-3 flex items-center gap-2 text-xs text-red-600 bg-red-50 px-3 py-2 rounded-lg">
            <AlertCircle size={12} /> {error}
          </div>
        )}
      </div>

      {/* Results */}
      {result && (
        <>
          {/* Uplift summary */}
          <div className="card p-5 bg-gradient-to-r from-emerald-50 to-blue-50 border-emerald-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold text-gray-600 uppercase tracking-wider">Expected ROAS Uplift</p>
                <p className="text-3xl font-bold text-emerald-700 mt-1">
                  {result.expected_uplift_pct >= 0 ? '+' : ''}{(result.expected_uplift_pct * 100).toFixed(1)}%
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Total budget</p>
                <p className="text-xl font-bold text-gray-900">${result.total_budget.toLocaleString()}</p>
              </div>
            </div>
          </div>

          {/* AI explanation */}
          <div className="card p-5">
            <h3 className="text-sm font-semibold text-gray-900 flex items-center gap-2 mb-3">
              <Zap size={14} className="text-amber-500" /> AI Explanation
            </h3>
            <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">{result.ai_explanation}</p>
          </div>

          {/* Allocation comparison table */}
          <div className="card overflow-hidden">
            <div className="px-5 py-3 border-b border-gray-100">
              <h3 className="text-sm font-semibold text-gray-900">Allocation Changes</h3>
            </div>
            <table className="w-full text-xs">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left px-5 py-2 font-semibold text-gray-700">Campaign</th>
                  <th className="text-right px-5 py-2 font-semibold text-gray-700">Current</th>
                  <th className="text-right px-5 py-2 font-semibold text-gray-700">Recommended</th>
                  <th className="text-right px-5 py-2 font-semibold text-gray-700">Change</th>
                </tr>
              </thead>
              <tbody>
                {Object.keys(result.optimal_allocation).map(cid => {
                  const current = result.current_allocation[cid] || 0
                  const optimal = result.optimal_allocation[cid] || 0
                  const change = optimal - current
                  const pct = current > 0 ? (change / current) * 100 : 100
                  return (
                    <tr key={cid} className="border-b border-gray-100">
                      <td className="px-5 py-2 font-mono text-[10px] text-gray-600">{cid.slice(0, 8)}…</td>
                      <td className="px-5 py-2 text-right">${current.toFixed(0)}</td>
                      <td className="px-5 py-2 text-right font-bold">${optimal.toFixed(0)}</td>
                      <td className={`px-5 py-2 text-right font-semibold ${change >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                        {change >= 0 ? '+' : ''}{pct.toFixed(0)}%
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          {/* Apply button */}
          <div className="card p-5">
            {applied ? (
              <div className="flex items-center gap-2 text-sm text-emerald-700">
                <CheckCircle2 size={16} /> Optimization marked as applied
              </div>
            ) : (
              <>
                <button
                  onClick={apply}
                  disabled={applying}
                  className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-semibold hover:bg-blue-700 disabled:opacity-40"
                >
                  {applying ? <Loader2 size={14} className="animate-spin" /> : <ArrowRight size={14} />}
                  {applying ? 'Applying...' : 'Mark as Applied'}
                </button>
                <p className="text-[11px] text-gray-500 mt-2">
                  Per safety policy, the platform never auto-mutates live ad budgets. Apply the changes manually in Google/Meta Ads UI.
                </p>
              </>
            )}
          </div>
        </>
      )}
    </div>
  )
}

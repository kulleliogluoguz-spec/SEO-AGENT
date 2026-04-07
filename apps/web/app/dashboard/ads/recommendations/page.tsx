'use client'

import { useEffect, useState, useCallback } from 'react'
import { Lightbulb, Loader2, CheckCircle2, XCircle, ChevronDown, ChevronUp, AlertCircle } from 'lucide-react'
import { apiFetch } from '@/lib/apiFetch'

interface Recommendation {
  id: string
  recommendation_type: string
  priority: string
  title: string
  description: string
  expected_impact: string
  ai_reasoning: string
  confidence_score: number
  status: string
  campaign_id: string | null
  campaign_name: string | null
  created_at: string
}

const PRIORITY_STYLES: Record<string, { bg: string; text: string; border: string }> = {
  critical: { bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-300' },
  high:     { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-300' },
  medium:   { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200' },
  low:      { bg: 'bg-gray-50', text: 'text-gray-600', border: 'border-gray-200' },
}

export default function RecommendationsPage() {
  const [recs, setRecs] = useState<Recommendation[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [priorityFilter, setPriorityFilter] = useState<string>('all')
  const [typeFilter, setTypeFilter] = useState<string>('all')
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true); setError(null)
    try {
      const params = new URLSearchParams({ status: 'pending' })
      if (priorityFilter !== 'all') params.set('priority', priorityFilter)
      const data = await apiFetch<{ recommendations: Recommendation[] }>(`/api/v1/ads/recommendations?${params}`)
      setRecs(data.recommendations ?? [])
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed')
    } finally {
      setLoading(false)
    }
  }, [priorityFilter])

  useEffect(() => { load() }, [load])

  async function applyRec(id: string) {
    setActionLoading(id)
    try {
      await apiFetch(`/api/v1/ads/recommendations/${id}/apply`, { method: 'POST' })
      setRecs(rs => rs.filter(r => r.id !== id))
    } catch { /* ignore */ }
    finally { setActionLoading(null) }
  }

  async function dismissRec(id: string) {
    setActionLoading(id)
    try {
      await apiFetch(`/api/v1/ads/recommendations/${id}/dismiss`, { method: 'POST' })
      setRecs(rs => rs.filter(r => r.id !== id))
    } catch { /* ignore */ }
    finally { setActionLoading(null) }
  }

  const filtered = recs.filter(r => typeFilter === 'all' || r.recommendation_type === typeFilter)

  return (
    <div className="space-y-5 max-w-5xl">
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 bg-amber-100 rounded-xl flex items-center justify-center">
          <Lightbulb size={16} className="text-amber-600" />
        </div>
        <div>
          <h1 className="text-lg font-bold text-gray-900">AI Recommendations</h1>
          <p className="text-xs text-gray-500">{filtered.length} pending recommendations</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-2 flex-wrap">
        <select value={priorityFilter} onChange={e => setPriorityFilter(e.target.value)}
          className="px-3 py-1.5 text-xs rounded-lg border border-gray-200 bg-white">
          <option value="all">All priorities</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
        <select value={typeFilter} onChange={e => setTypeFilter(e.target.value)}
          className="px-3 py-1.5 text-xs rounded-lg border border-gray-200 bg-white">
          <option value="all">All types</option>
          <option value="scale_budget">Scale</option>
          <option value="reduce_budget">Reduce budget</option>
          <option value="increase_budget">Increase budget</option>
          <option value="pause_campaign">Pause</option>
          <option value="creative_refresh">Creative refresh</option>
          <option value="monitor">Monitor</option>
        </select>
      </div>

      {error && (
        <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          <AlertCircle size={14} /> {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-40">
          <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="card p-8 text-center">
          <Lightbulb size={28} className="text-gray-200 mx-auto mb-3" />
          <p className="text-sm text-gray-500">No pending recommendations</p>
          <p className="text-xs text-gray-400 mt-1">The decision engine runs every 6 hours.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map(r => {
            const isExpanded = expanded.has(r.id)
            const style = PRIORITY_STYLES[r.priority] || PRIORITY_STYLES.medium
            return (
              <div key={r.id} className={`card border-l-4 ${style.border} p-4`}>
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-start gap-2 flex-1 min-w-0">
                    <span className={`text-[9px] font-bold px-2 py-1 rounded ${style.bg} ${style.text} flex-shrink-0`}>
                      {r.priority.toUpperCase()}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold text-gray-900">{r.title}</p>
                      {r.campaign_name && (
                        <p className="text-[10px] text-gray-400 mt-0.5">{r.campaign_name}</p>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={() => setExpanded(s => {
                      const ns = new Set(s)
                      if (ns.has(r.id)) ns.delete(r.id); else ns.add(r.id)
                      return ns
                    })}
                    className="p-1 text-gray-400 hover:text-gray-700"
                  >
                    {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                  </button>
                </div>
                <p className="text-xs text-gray-600 leading-relaxed">{r.description}</p>
                <p className="text-xs font-semibold text-emerald-700 mt-2">📈 {r.expected_impact}</p>

                {isExpanded && (
                  <div className="mt-3 pt-3 border-t border-gray-100">
                    <p className="text-[10px] font-bold text-gray-500 uppercase tracking-wider mb-1">AI Reasoning</p>
                    <p className="text-xs text-gray-600 leading-relaxed">{r.ai_reasoning}</p>
                    <p className="text-[10px] text-gray-400 mt-2">Confidence: {(r.confidence_score * 100).toFixed(0)}%</p>
                  </div>
                )}

                <div className="flex items-center gap-2 mt-3">
                  <button
                    onClick={() => applyRec(r.id)}
                    disabled={actionLoading === r.id}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 text-white text-xs font-semibold rounded-lg hover:bg-emerald-700 disabled:opacity-40"
                  >
                    {actionLoading === r.id ? <Loader2 size={11} className="animate-spin" /> : <CheckCircle2 size={11} />}
                    Apply
                  </button>
                  <button
                    onClick={() => dismissRec(r.id)}
                    disabled={actionLoading === r.id}
                    className="flex items-center gap-1.5 px-3 py-1.5 border border-gray-200 text-xs font-medium text-gray-600 rounded-lg hover:bg-gray-50"
                  >
                    <XCircle size={11} /> Dismiss
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

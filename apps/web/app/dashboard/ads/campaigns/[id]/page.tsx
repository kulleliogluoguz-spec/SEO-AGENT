'use client'

import { useEffect, useState, useCallback } from 'react'
import { useParams } from 'next/navigation'
import {
  Target, Loader2, AlertCircle, ArrowLeft, ArrowUp, ArrowDown,
  CheckCircle2, XCircle, Lightbulb,
} from 'lucide-react'
import Link from 'next/link'
import { apiFetch } from '@/lib/apiFetch'

interface CampaignAnalysis {
  campaign_id: string
  name: string
  platform: string
  metrics: {
    roas_7d: number
    roas_30d: number
    roas_trend: number
    spend_7d: number
    spend_30d: number
    cpa_7d: number | null
    ctr_7d: number
    frequency: number
    budget_utilization: number
    days_active: number
  }
  ai_status: string
  recommendations: Array<{
    type: string
    priority: string
    title: string
    description: string
    expected_impact: string
    confidence: number
    reasoning: string
  }>
  ai_insight: string
}

interface PerformancePoint {
  date: string
  roas: number | null
  spend: number
  conversions: number
}

export default function CampaignDetailPage() {
  const params = useParams<{ id: string }>()
  const id = params?.id
  const [analysis, setAnalysis] = useState<CampaignAnalysis | null>(null)
  const [series, setSeries] = useState<PerformancePoint[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!id) return
    setLoading(true); setError(null)
    try {
      const [a, p] = await Promise.all([
        apiFetch<CampaignAnalysis>(`/api/v1/ads/campaigns/${id}/analysis`, { timeoutMs: 180_000 }),
        apiFetch<{ series: PerformancePoint[] }>(`/api/v1/ads/campaigns/${id}/performance?days=30`),
      ])
      setAnalysis(a)
      setSeries(p.series ?? [])
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => { load() }, [load])

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <Loader2 className="w-7 h-7 animate-spin text-gray-400" />
    </div>
  )

  if (error || !analysis) return (
    <div className="flex flex-col items-center justify-center h-64 gap-4">
      <AlertCircle className="w-8 h-8 text-red-400" />
      <p className="text-sm text-gray-700">{error || 'Campaign not found'}</p>
      <Link href="/dashboard/ads/campaigns" className="text-xs text-blue-600 hover:underline">
        ← Back to campaigns
      </Link>
    </div>
  )

  // Build a simple ROAS sparkline
  const roasPoints = series.filter(p => p.roas !== null).map(p => p.roas as number)
  const maxR = Math.max(...roasPoints, 1)
  const minR = Math.min(...roasPoints, 0)
  const range = maxR - minR || 1
  const w = roasPoints.length > 1 ? 100 / (roasPoints.length - 1) : 0
  const linePath = roasPoints.map((v, i) => {
    const x = i * w
    const y = 100 - ((v - minR) / range) * 80 - 10
    return `${i === 0 ? 'M' : 'L'} ${x.toFixed(2)} ${y.toFixed(2)}`
  }).join(' ')

  const m = analysis.metrics

  return (
    <div className="space-y-6 max-w-5xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href="/dashboard/ads/campaigns" className="p-2 rounded-lg hover:bg-gray-100 text-gray-400">
            <ArrowLeft size={14} />
          </Link>
          <div className="w-9 h-9 bg-blue-100 rounded-xl flex items-center justify-center">
            <Target size={16} className="text-blue-600" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-gray-900">{analysis.name}</h1>
            <p className="text-xs text-gray-500">{analysis.platform.replace('_', ' ')} · {m.days_active} days active</p>
          </div>
        </div>
        <span className={`text-xs font-bold px-3 py-1.5 rounded-full ${
          analysis.ai_status === 'critical' ? 'bg-red-100 text-red-700' :
          analysis.ai_status === 'poor' ? 'bg-amber-100 text-amber-700' :
          analysis.ai_status === 'excellent' ? 'bg-blue-100 text-blue-700' :
          analysis.ai_status === 'good' ? 'bg-emerald-100 text-emerald-700' :
          'bg-gray-100 text-gray-600'
        }`}>{analysis.ai_status.toUpperCase()}</span>
      </div>

      {/* AI insight */}
      <div className="card p-5 bg-gradient-to-r from-blue-50 to-violet-50 border-blue-200">
        <h3 className="text-sm font-semibold text-blue-900 flex items-center gap-2 mb-2">
          <Lightbulb size={14} /> AI Insight
        </h3>
        <p className="text-sm text-blue-900 leading-relaxed">{analysis.ai_insight}</p>
      </div>

      {/* Metrics grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <MetricCard label="ROAS 7d" value={`${m.roas_7d.toFixed(2)}x`} trend={m.roas_trend} />
        <MetricCard label="ROAS 30d" value={`${m.roas_30d.toFixed(2)}x`} />
        <MetricCard label="Spend 7d" value={`$${m.spend_7d.toFixed(0)}`} />
        <MetricCard label="CPA 7d" value={m.cpa_7d ? `$${m.cpa_7d.toFixed(2)}` : '—'} />
        <MetricCard label="CTR 7d" value={`${(m.ctr_7d * 100).toFixed(2)}%`} />
        <MetricCard label="Frequency" value={m.frequency.toFixed(2)} />
        <MetricCard label="Budget util." value={`${(m.budget_utilization * 100).toFixed(0)}%`} />
        <MetricCard label="Days active" value={m.days_active} />
      </div>

      {/* ROAS chart */}
      <div className="card p-5">
        <h3 className="text-sm font-semibold text-gray-900 mb-3">ROAS — Last 30 Days</h3>
        {roasPoints.length < 2 ? (
          <p className="text-xs text-gray-400 py-12 text-center">Not enough data for chart</p>
        ) : (
          <svg viewBox="0 0 100 100" className="w-full h-32" preserveAspectRatio="none">
            <path d={linePath} fill="none" stroke="#3b82f6" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
        )}
      </div>

      {/* Recommendations */}
      {analysis.recommendations.length > 0 && (
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2">
            <Lightbulb size={14} className="text-amber-500" />
            Recommendations ({analysis.recommendations.length})
          </h3>
          <div className="space-y-3">
            {analysis.recommendations.map((r, i) => (
              <div key={i} className={`p-3 border-l-4 rounded-lg ${
                r.priority === 'critical' ? 'border-red-400 bg-red-50' :
                r.priority === 'high' ? 'border-amber-400 bg-amber-50' :
                'border-blue-300 bg-blue-50'
              }`}>
                <p className="text-sm font-semibold text-gray-900">{r.title}</p>
                <p className="text-xs text-gray-600 mt-1">{r.description}</p>
                <p className="text-[11px] text-emerald-700 mt-2 font-medium">📈 {r.expected_impact}</p>
                <p className="text-[10px] text-gray-500 mt-1 italic">{r.reasoning}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function MetricCard({ label, value, trend }: { label: string; value: string | number; trend?: number }) {
  return (
    <div className="card p-3">
      <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">{label}</p>
      <div className="flex items-center gap-1 mt-1">
        <p className="text-lg font-bold text-gray-900">{value}</p>
        {trend !== undefined && trend !== 0 && (
          <span className={`text-[10px] ${trend > 0 ? 'text-emerald-600' : 'text-red-500'}`}>
            {trend > 0 ? <ArrowUp size={10} /> : <ArrowDown size={10} />}
            {Math.abs(trend * 100).toFixed(0)}%
          </span>
        )}
      </div>
    </div>
  )
}

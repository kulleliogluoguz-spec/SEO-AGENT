'use client'

import { useEffect, useState, useCallback } from 'react'
import {
  LayoutDashboard, Target, DollarSign, Lightbulb, TrendingUp, TrendingDown,
  AlertCircle, CheckCircle2, Loader2, RefreshCw, ArrowRight, Zap,
} from 'lucide-react'
import Link from 'next/link'
import { apiFetch } from '@/lib/apiFetch'

interface PortfolioSummary {
  period_days: number
  total_spend: number
  total_revenue: number
  total_conversions: number
  total_impressions: number
  total_clicks: number
  overall_roas: number
  overall_cpa: number | null
  active_campaigns: number
  pending_recommendations: number
  critical_recommendations: number
}

interface CampaignRow {
  id: string
  name: string
  platform: string
  status: string
  roas_7d: number | null
  spend_7d: number
  ai_status: string
  top_recommendation: { type: string; priority: string; title: string } | null
  recommendation_count: number
}

interface Recommendation {
  id: string
  title: string
  description: string
  priority: string
  expected_impact: string
  campaign_name: string | null
}

const STATUS_STYLES: Record<string, { border: string; bg: string; label: string }> = {
  excellent: { border: 'border-blue-300', bg: 'bg-blue-50', label: 'Excellent' },
  good:      { border: 'border-emerald-300', bg: 'bg-emerald-50', label: 'Good' },
  average:   { border: 'border-gray-200', bg: 'bg-white', label: 'Average' },
  poor:      { border: 'border-amber-300', bg: 'bg-amber-50', label: 'Warning' },
  critical:  { border: 'border-red-400', bg: 'bg-red-50', label: 'Critical' },
  fatigued:  { border: 'border-amber-400', bg: 'bg-amber-50', label: 'Fatigued' },
  no_data:   { border: 'border-gray-100', bg: 'bg-gray-50', label: 'No data' },
}

export default function AdsCommandCenter() {
  const [summary, setSummary] = useState<PortfolioSummary | null>(null)
  const [campaigns, setCampaigns] = useState<CampaignRow[]>([])
  const [recs, setRecs] = useState<Recommendation[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true); setError(null)
    try {
      const [s, c, r] = await Promise.all([
        apiFetch<PortfolioSummary>('/api/v1/ads/portfolio/summary?days=7'),
        apiFetch<{ campaigns: CampaignRow[] }>('/api/v1/ads/campaigns'),
        apiFetch<{ recommendations: Recommendation[] }>('/api/v1/ads/recommendations?status=pending'),
      ])
      setSummary(s)
      setCampaigns(c.campaigns ?? [])
      setRecs(r.recommendations ?? [])
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <Loader2 className="w-7 h-7 animate-spin text-gray-400" />
    </div>
  )

  if (error) return (
    <div className="flex flex-col items-center justify-center h-64 gap-4">
      <AlertCircle className="w-8 h-8 text-red-400" />
      <p className="text-sm text-gray-700">{error}</p>
      <button onClick={load} className="text-xs text-blue-600 hover:underline">Retry</button>
    </div>
  )

  const topRecs = recs.slice(0, 3)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center">
            <LayoutDashboard size={18} className="text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-gray-900">Ads Command Center</h1>
            <p className="text-xs text-gray-500">Portfolio overview, AI insights, and recommendations</p>
          </div>
        </div>
        <button onClick={load} className="p-2 rounded-lg hover:bg-gray-100 text-gray-400">
          <RefreshCw size={14} />
        </button>
      </div>

      {/* Critical alert banner */}
      {summary && summary.critical_recommendations > 0 && (
        <div className="flex items-center gap-3 p-4 bg-red-50 border border-red-200 rounded-xl">
          <AlertCircle size={18} className="text-red-500 flex-shrink-0" />
          <div className="flex-1">
            <p className="text-sm font-semibold text-red-900">
              {summary.critical_recommendations} critical issue{summary.critical_recommendations !== 1 ? 's' : ''} require immediate attention
            </p>
            <p className="text-xs text-red-700">Campaigns are losing money or have severe issues</p>
          </div>
          <Link href="/dashboard/ads/recommendations?priority=critical" className="text-xs font-semibold text-red-700 hover:text-red-900">
            View →
          </Link>
        </div>
      )}

      {/* KPI cards */}
      {summary && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: 'Total Spend', value: `$${summary.total_spend.toLocaleString(undefined, { maximumFractionDigits: 0 })}`, color: 'text-gray-900' },
            { label: 'Overall ROAS', value: `${summary.overall_roas.toFixed(2)}x`, color: summary.overall_roas >= 3 ? 'text-emerald-600' : summary.overall_roas >= 1.5 ? 'text-blue-600' : 'text-red-500' },
            { label: 'Conversions', value: summary.total_conversions.toLocaleString(undefined, { maximumFractionDigits: 0 }), color: 'text-gray-900' },
            { label: 'Active Campaigns', value: summary.active_campaigns, color: 'text-gray-900' },
          ].map(k => (
            <div key={k.label} className="card p-4">
              <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">{k.label}</p>
              <p className={`text-2xl font-bold mt-1 ${k.color}`}>{k.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Top recommendations */}
      {topRecs.length > 0 && (
        <div className="card p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-gray-900 flex items-center gap-2">
              <Lightbulb size={14} className="text-amber-500" /> Top AI Recommendations
            </h3>
            <Link href="/dashboard/ads/recommendations" className="text-xs text-blue-600 hover:underline">
              View all ({recs.length})
            </Link>
          </div>
          <div className="space-y-2">
            {topRecs.map(r => (
              <div key={r.id} className="flex items-start gap-3 p-3 border border-gray-100 rounded-lg hover:bg-gray-50">
                <span className={`text-[9px] font-bold px-2 py-1 rounded ${
                  r.priority === 'critical' ? 'bg-red-100 text-red-700' :
                  r.priority === 'high' ? 'bg-amber-100 text-amber-700' :
                  r.priority === 'medium' ? 'bg-blue-100 text-blue-700' :
                  'bg-gray-100 text-gray-600'
                }`}>{r.priority.toUpperCase()}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-gray-900 truncate">{r.title}</p>
                  <p className="text-xs text-gray-500 mt-0.5">{r.expected_impact}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Campaign health grid */}
      <div className="card p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-gray-900 flex items-center gap-2">
            <Target size={14} className="text-blue-500" /> Campaign Health
          </h3>
          <Link href="/dashboard/ads/campaigns" className="text-xs text-blue-600 hover:underline">
            View all campaigns
          </Link>
        </div>
        {campaigns.length === 0 ? (
          <div className="text-center py-12">
            <Target size={28} className="text-gray-200 mx-auto mb-3" />
            <p className="text-sm text-gray-500">No campaigns yet</p>
            <p className="text-xs text-gray-400 mt-1">Connect a Google Ads or Meta Ads account to get started.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {campaigns.slice(0, 9).map(c => {
              const style = STATUS_STYLES[c.ai_status] || STATUS_STYLES.no_data
              return (
                <Link
                  key={c.id}
                  href={`/dashboard/ads/campaigns/${c.id}`}
                  className={`p-3 rounded-lg border-2 ${style.border} ${style.bg} hover:shadow-sm transition`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[9px] font-bold uppercase text-gray-500">{c.platform}</span>
                    <span className="text-[9px] font-semibold text-gray-600">{style.label}</span>
                  </div>
                  <p className="text-xs font-semibold text-gray-900 truncate">{c.name}</p>
                  <div className="flex items-center justify-between mt-2 text-[10px] text-gray-500">
                    <span>ROAS: <span className="font-bold text-gray-800">{c.roas_7d?.toFixed(2) ?? '—'}x</span></span>
                    <span>${c.spend_7d.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                  </div>
                </Link>
              )
            })}
          </div>
        )}
      </div>

      {/* Quick links */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { href: '/dashboard/ads/budget', icon: DollarSign, label: 'Budget Optimizer', color: 'text-emerald-500' },
          { href: '/dashboard/ads/mmm', icon: Target, label: 'Attribution (MMM)', color: 'text-violet-500' },
          { href: '/dashboard/ads/forecasting', icon: TrendingUp, label: 'Forecasting', color: 'text-blue-500' },
          { href: '/dashboard/ads/reports', icon: Zap, label: 'Weekly Report', color: 'text-amber-500' },
        ].map(l => (
          <Link key={l.href} href={l.href} className="card p-4 hover:bg-gray-50 group text-center">
            <l.icon size={20} className={`${l.color} mx-auto mb-2 group-hover:scale-110 transition-transform`} />
            <p className="text-xs font-semibold text-gray-800">{l.label}</p>
          </Link>
        ))}
      </div>
    </div>
  )
}

'use client'

import { useEffect, useState, useCallback } from 'react'
import { Target, Loader2, ArrowUp, ArrowDown, Filter, RefreshCw, AlertCircle } from 'lucide-react'
import Link from 'next/link'
import { apiFetch } from '@/lib/apiFetch'

interface Campaign {
  id: string
  name: string
  platform: string
  status: string
  campaign_type: string | null
  daily_budget: number
  roas_7d: number | null
  roas_30d: number | null
  roas_trend: number | null
  spend_7d: number
  cpa_7d: number | null
  ctr_7d: number | null
  frequency: number | null
  ai_status: string
  top_recommendation: { type: string; priority: string; title: string } | null
  recommendation_count: number
}

const STATUS_BADGE: Record<string, string> = {
  excellent: 'bg-blue-100 text-blue-700',
  good:      'bg-emerald-100 text-emerald-700',
  average:   'bg-gray-100 text-gray-600',
  poor:      'bg-amber-100 text-amber-700',
  critical:  'bg-red-100 text-red-700',
  fatigued:  'bg-amber-100 text-amber-700',
  no_data:   'bg-gray-50 text-gray-400',
}

type SortKey = 'name' | 'roas_7d' | 'spend_7d' | 'ai_status'

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [platformFilter, setPlatformFilter] = useState<string>('all')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [sortKey, setSortKey] = useState<SortKey>('roas_7d')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')

  const load = useCallback(async () => {
    setLoading(true); setError(null)
    try {
      const data = await apiFetch<{ campaigns: Campaign[] }>('/api/v1/ads/campaigns')
      setCampaigns(data.campaigns ?? [])
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const filtered = campaigns
    .filter(c => platformFilter === 'all' || c.platform === platformFilter)
    .filter(c => statusFilter === 'all' || c.ai_status === statusFilter)
    .sort((a, b) => {
      const av = a[sortKey] ?? (typeof a[sortKey] === 'number' ? -Infinity : '')
      const bv = b[sortKey] ?? (typeof b[sortKey] === 'number' ? -Infinity : '')
      if (av < bv) return sortDir === 'asc' ? -1 : 1
      if (av > bv) return sortDir === 'asc' ? 1 : -1
      return 0
    })

  function toggleSort(key: SortKey) {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortKey(key); setSortDir('desc') }
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-blue-100 rounded-xl flex items-center justify-center">
            <Target size={16} className="text-blue-600" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-gray-900">Campaigns</h1>
            <p className="text-xs text-gray-500">{filtered.length} of {campaigns.length} campaigns</p>
          </div>
        </div>
        <button onClick={load} className="p-2 rounded-lg hover:bg-gray-100 text-gray-400">
          <RefreshCw size={14} />
        </button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-2 flex-wrap">
        <Filter size={12} className="text-gray-400" />
        <select value={platformFilter} onChange={e => setPlatformFilter(e.target.value)}
          className="px-3 py-1.5 text-xs rounded-lg border border-gray-200 bg-white">
          <option value="all">All platforms</option>
          <option value="google_ads">Google Ads</option>
          <option value="meta_ads">Meta Ads</option>
        </select>
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
          className="px-3 py-1.5 text-xs rounded-lg border border-gray-200 bg-white">
          <option value="all">All statuses</option>
          <option value="excellent">Excellent</option>
          <option value="good">Good</option>
          <option value="average">Average</option>
          <option value="poor">Poor</option>
          <option value="critical">Critical</option>
          <option value="fatigued">Fatigued</option>
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
          <Target size={28} className="text-gray-200 mx-auto mb-3" />
          <p className="text-sm text-gray-500">No campaigns match the current filters</p>
        </div>
      ) : (
        <div className="card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="text-left px-4 py-3 font-semibold text-gray-700 cursor-pointer" onClick={() => toggleSort('name')}>
                    Campaign {sortKey === 'name' && (sortDir === 'asc' ? '↑' : '↓')}
                  </th>
                  <th className="text-left px-4 py-3 font-semibold text-gray-700">Platform</th>
                  <th className="text-left px-4 py-3 font-semibold text-gray-700 cursor-pointer" onClick={() => toggleSort('ai_status')}>
                    Health {sortKey === 'ai_status' && (sortDir === 'asc' ? '↑' : '↓')}
                  </th>
                  <th className="text-right px-4 py-3 font-semibold text-gray-700 cursor-pointer" onClick={() => toggleSort('roas_7d')}>
                    ROAS 7d {sortKey === 'roas_7d' && (sortDir === 'asc' ? '↑' : '↓')}
                  </th>
                  <th className="text-right px-4 py-3 font-semibold text-gray-700">Trend</th>
                  <th className="text-right px-4 py-3 font-semibold text-gray-700 cursor-pointer" onClick={() => toggleSort('spend_7d')}>
                    Spend 7d
                  </th>
                  <th className="text-right px-4 py-3 font-semibold text-gray-700">CPA</th>
                  <th className="text-left px-4 py-3 font-semibold text-gray-700">Top Issue</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(c => (
                  <tr key={c.id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <Link href={`/dashboard/ads/campaigns/${c.id}`} className="font-semibold text-gray-900 hover:text-blue-600">
                        {c.name}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-gray-600">{c.platform.replace('_', ' ')}</td>
                    <td className="px-4 py-3">
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${STATUS_BADGE[c.ai_status] || STATUS_BADGE.no_data}`}>
                        {c.ai_status.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right font-bold text-gray-900">
                      {c.roas_7d !== null ? `${c.roas_7d.toFixed(2)}x` : '—'}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {c.roas_trend !== null && c.roas_trend !== 0 ? (
                        <span className={`inline-flex items-center gap-0.5 ${c.roas_trend > 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                          {c.roas_trend > 0 ? <ArrowUp size={10} /> : <ArrowDown size={10} />}
                          {Math.abs(c.roas_trend * 100).toFixed(0)}%
                        </span>
                      ) : <span className="text-gray-300">—</span>}
                    </td>
                    <td className="px-4 py-3 text-right text-gray-600">
                      ${c.spend_7d.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                    </td>
                    <td className="px-4 py-3 text-right text-gray-600">
                      {c.cpa_7d !== null ? `$${c.cpa_7d.toFixed(2)}` : '—'}
                    </td>
                    <td className="px-4 py-3">
                      {c.top_recommendation ? (
                        <span className="text-[10px] text-gray-700 truncate block max-w-[200px]">
                          {c.top_recommendation.title}
                        </span>
                      ) : <span className="text-gray-300">—</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

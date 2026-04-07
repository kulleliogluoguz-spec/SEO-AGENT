'use client'

import { useEffect, useState, useCallback } from 'react'
import { TrendingUp, Loader2, AlertCircle } from 'lucide-react'
import { apiFetch } from '@/lib/apiFetch'

interface DailyForecast {
  date: string
  predicted_roas: number
  lower_bound: number
  upper_bound: number
}

interface Forecast {
  campaign: string
  forecast_days: number
  start_date: string
  end_date: string
  daily_forecasts: DailyForecast[]
  avg_predicted_roas: number
  trend: string
  model: string
}

interface Campaign { id: string; name: string }

export default function ForecastingPage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [selectedId, setSelectedId] = useState<string>('')
  const [forecast, setForecast] = useState<Forecast | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Load available campaigns
  useEffect(() => {
    apiFetch<{ campaigns: Campaign[] }>('/api/v1/ads/campaigns')
      .then(d => {
        setCampaigns(d.campaigns ?? [])
        if (d.campaigns?.[0]) setSelectedId(d.campaigns[0].id)
      })
      .catch(() => {})
  }, [])

  const loadForecast = useCallback(async (id: string) => {
    if (!id) return
    setLoading(true); setError(null)
    try {
      const data = await apiFetch<{ forecast: Forecast }>(`/api/v1/ads/campaigns/${id}/forecast?days=30&metric=roas`)
      setForecast(data.forecast)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (selectedId) loadForecast(selectedId)
  }, [selectedId, loadForecast])

  // Build SVG sparkline
  const points = forecast?.daily_forecasts || []
  const maxV = Math.max(...points.map(p => p.upper_bound), 1)
  const minV = Math.min(...points.map(p => p.lower_bound), 0)
  const range = maxV - minV || 1
  const w = points.length > 1 ? 100 / (points.length - 1) : 0

  const linePath = points.map((p, i) => {
    const x = i * w
    const y = 100 - ((p.predicted_roas - minV) / range) * 80 - 10
    return `${i === 0 ? 'M' : 'L'} ${x.toFixed(2)} ${y.toFixed(2)}`
  }).join(' ')

  const upperPath = points.map((p, i) => {
    const x = i * w
    const y = 100 - ((p.upper_bound - minV) / range) * 80 - 10
    return `${i === 0 ? 'M' : 'L'} ${x.toFixed(2)} ${y.toFixed(2)}`
  }).join(' ')

  const lowerPath = points.map((p, i) => {
    const x = i * w
    const y = 100 - ((p.lower_bound - minV) / range) * 80 - 10
    return `${i === 0 ? 'M' : 'L'} ${x.toFixed(2)} ${y.toFixed(2)}`
  }).join(' ')

  const bandPath = upperPath + ' ' + points.slice().reverse().map((p, i) => {
    const idx = points.length - 1 - i
    const x = idx * w
    const y = 100 - ((p.lower_bound - minV) / range) * 80 - 10
    return `L ${x.toFixed(2)} ${y.toFixed(2)}`
  }).join(' ') + ' Z'

  return (
    <div className="space-y-5 max-w-5xl">
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 bg-blue-100 rounded-xl flex items-center justify-center">
          <TrendingUp size={16} className="text-blue-600" />
        </div>
        <div>
          <h1 className="text-lg font-bold text-gray-900">Forecasting</h1>
          <p className="text-xs text-gray-500">Prophet-based 30-day ROAS forecasts</p>
        </div>
      </div>

      <div className="card p-4">
        <label className="block text-xs font-semibold text-gray-700 mb-2">Campaign</label>
        <select
          value={selectedId}
          onChange={e => setSelectedId(e.target.value)}
          className="w-full max-w-md px-3 py-2 text-sm rounded-lg border border-gray-200 bg-white"
        >
          {campaigns.length === 0 && <option>No campaigns available</option>}
          {campaigns.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
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
      ) : forecast ? (
        <>
          {/* Headline metrics */}
          <div className="grid grid-cols-3 gap-3">
            <div className="card p-4">
              <p className="text-[10px] text-gray-500 uppercase">Avg ROAS forecast</p>
              <p className="text-2xl font-bold text-gray-900">{forecast.avg_predicted_roas.toFixed(2)}x</p>
            </div>
            <div className="card p-4">
              <p className="text-[10px] text-gray-500 uppercase">Trend</p>
              <p className={`text-xl font-bold ${
                forecast.trend === 'improving' ? 'text-emerald-600' :
                forecast.trend === 'declining' ? 'text-red-500' : 'text-gray-700'
              }`}>{forecast.trend}</p>
            </div>
            <div className="card p-4">
              <p className="text-[10px] text-gray-500 uppercase">Model</p>
              <p className="text-base font-semibold text-gray-700">{forecast.model}</p>
            </div>
          </div>

          {/* Chart */}
          <div className="card p-5">
            <h3 className="text-sm font-semibold text-gray-900 mb-3">
              ROAS Forecast — {forecast.start_date} to {forecast.end_date}
            </h3>
            {points.length < 2 ? (
              <p className="text-xs text-gray-400">Not enough data points for chart</p>
            ) : (
              <svg viewBox="0 0 100 100" className="w-full h-48" preserveAspectRatio="none">
                {/* Confidence band */}
                <path d={bandPath} fill="#3b82f6" fillOpacity="0.1" />
                {/* Upper bound */}
                <path d={upperPath} fill="none" stroke="#93c5fd" strokeWidth="0.5" strokeDasharray="0.5,0.5" />
                {/* Lower bound */}
                <path d={lowerPath} fill="none" stroke="#93c5fd" strokeWidth="0.5" strokeDasharray="0.5,0.5" />
                {/* Mean line */}
                <path d={linePath} fill="none" stroke="#3b82f6" strokeWidth="1.5" strokeLinecap="round" />
              </svg>
            )}
            <div className="flex items-center justify-between mt-2 text-[10px] text-gray-400">
              <span>{forecast.start_date}</span>
              <span>{forecast.end_date}</span>
            </div>
          </div>
        </>
      ) : (
        <div className="card p-8 text-center">
          <TrendingUp size={28} className="text-gray-200 mx-auto mb-3" />
          <p className="text-sm text-gray-500">Select a campaign to see its forecast</p>
        </div>
      )}
    </div>
  )
}

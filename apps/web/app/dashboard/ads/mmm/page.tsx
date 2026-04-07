'use client'

import { useEffect, useState, useCallback } from 'react'
import { PieChart as PieChartIcon, Loader2, Zap, AlertCircle, CheckCircle2 } from 'lucide-react'
import { apiFetch } from '@/lib/apiFetch'

interface MMMResult {
  has_model: boolean
  message?: string
  model?: {
    id: string
    model_version: string
    training_start_date: string | null
    training_end_date: string | null
    channels: string[] | null
    channel_contributions: Record<string, number> | null
    model_metrics: Record<string, number> | null
    trained_at: string | null
  }
}

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6']

export default function MMMPage() {
  const [accountId, setAccountId] = useState<string>('default')
  const [data, setData] = useState<MMMResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [training, setTraining] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true); setError(null)
    try {
      const result = await apiFetch<MMMResult>(`/api/v1/ads/mmm/results/${accountId}`)
      setData(result)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed')
    } finally {
      setLoading(false)
    }
  }, [accountId])

  useEffect(() => { load() }, [load])

  async function trainModel() {
    setTraining(true); setError(null)
    try {
      await apiFetch(`/api/v1/ads/mmm/train?account_id=${accountId}`, { method: 'POST' })
      // Show "queued" message; the actual training happens in background
      setError(null)
      setTimeout(load, 2000)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Training failed')
    } finally {
      setTraining(false)
    }
  }

  // Compute donut chart data
  const contributions = data?.model?.channel_contributions || {}
  const total = Object.values(contributions).reduce((s, v) => s + v, 0)
  const segments = Object.entries(contributions).map(([ch, v], i) => ({
    channel: ch,
    value: v,
    pct: total > 0 ? v / total : 0,
    color: COLORS[i % COLORS.length],
  }))

  return (
    <div className="space-y-6 max-w-5xl">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-violet-100 rounded-xl flex items-center justify-center">
            <PieChartIcon size={16} className="text-violet-600" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-gray-900">Marketing Mix Model</h1>
            <p className="text-xs text-gray-500">Bayesian channel attribution and budget optimization</p>
          </div>
        </div>
        <button
          onClick={trainModel}
          disabled={training}
          className="flex items-center gap-2 px-4 py-2 bg-violet-600 text-white rounded-lg text-sm font-semibold hover:bg-violet-700 disabled:opacity-40"
        >
          {training ? <Loader2 size={14} className="animate-spin" /> : <Zap size={14} />}
          {training ? 'Queueing...' : 'Train New Model'}
        </button>
      </div>

      {error && (
        <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          <AlertCircle size={14} /> {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-7 h-7 animate-spin text-gray-400" />
        </div>
      ) : !data?.has_model ? (
        <div className="card p-12 text-center">
          <PieChartIcon size={32} className="text-gray-200 mx-auto mb-4" />
          <p className="text-sm font-semibold text-gray-700 mb-1">No MMM model trained yet</p>
          <p className="text-xs text-gray-400 mb-4">{data?.message || 'Train one to see channel attribution'}</p>
          <button
            onClick={trainModel}
            disabled={training}
            className="flex items-center gap-2 px-4 py-2 bg-violet-600 text-white rounded-lg text-sm font-semibold hover:bg-violet-700 disabled:opacity-40 mx-auto"
          >
            {training ? <Loader2 size={14} className="animate-spin" /> : <Zap size={14} />}
            Train First Model
          </button>
        </div>
      ) : (
        <>
          {/* Model info */}
          <div className="card p-5">
            <div className="flex items-center gap-2 mb-3">
              <CheckCircle2 size={14} className="text-emerald-500" />
              <span className="text-sm font-semibold text-gray-900">Model {data.model?.model_version}</span>
              <span className="text-[10px] text-gray-400">
                Trained: {data.model?.trained_at?.slice(0, 10) || 'pending'}
              </span>
            </div>
            <p className="text-xs text-gray-500">
              Training period: {data.model?.training_start_date} → {data.model?.training_end_date}
            </p>
          </div>

          {/* Channel contributions */}
          <div className="card p-5">
            <h3 className="text-sm font-semibold text-gray-900 mb-4">Channel Contributions to Revenue</h3>
            {segments.length === 0 ? (
              <p className="text-xs text-gray-400">No contribution data available</p>
            ) : (
              <div className="space-y-2">
                {segments.map(s => (
                  <div key={s.channel} className="flex items-center gap-3">
                    <div className="w-24 text-xs font-medium text-gray-700 truncate">{s.channel}</div>
                    <div className="flex-1 h-6 bg-gray-100 rounded overflow-hidden">
                      <div
                        className="h-full transition-all duration-500 flex items-center justify-end pr-2 text-[10px] font-bold text-white"
                        style={{ width: `${s.pct * 100}%`, backgroundColor: s.color }}
                      >
                        {(s.pct * 100).toFixed(0)}%
                      </div>
                    </div>
                    <div className="w-20 text-right text-xs text-gray-600">
                      ${s.value.toFixed(0)}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Model metrics */}
          {data.model?.model_metrics && Object.keys(data.model.model_metrics).length > 0 && (
            <div className="card p-5">
              <h3 className="text-sm font-semibold text-gray-900 mb-3">Model Quality</h3>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {Object.entries(data.model.model_metrics).map(([k, v]) => (
                  <div key={k} className="p-3 bg-gray-50 rounded-lg">
                    <p className="text-[10px] text-gray-500 uppercase">{k}</p>
                    <p className="text-lg font-bold text-gray-900">{typeof v === 'number' ? v.toFixed(3) : String(v)}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}

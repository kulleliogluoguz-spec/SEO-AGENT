'use client'

import { useEffect, useState, useCallback } from 'react'
import { CheckCircle, XCircle, AlertCircle, RefreshCw, Activity } from 'lucide-react'
import { apiFetch } from '@/lib/apiFetch'

type ComponentStatus = {
  status?: 'ok' | 'offline' | 'degraded' | 'error'
  models?: string[]
  detail?: string
}

type HealthResponse = {
  overall: 'ok' | 'degraded' | 'error' | 'unknown'
  components: Record<string, ComponentStatus>
  events_last_hour: number
}

const STATUS_ICON: Record<string, React.ReactNode> = {
  ok: <CheckCircle className="w-5 h-5 text-emerald-500" />,
  offline: <XCircle className="w-5 h-5 text-red-500" />,
  degraded: <AlertCircle className="w-5 h-5 text-amber-500" />,
  error: <XCircle className="w-5 h-5 text-red-500" />,
}

const STATUS_TEXT_COLOR: Record<string, string> = {
  ok: 'text-emerald-600',
  offline: 'text-red-600',
  degraded: 'text-amber-600',
  error: 'text-red-600',
}

export default function SystemHealthPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const d = await apiFetch<HealthResponse>('/api/v1/system/health')
      setHealth(d)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const overall = health?.overall ?? 'unknown'
  const components = health?.components ?? {}

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-brand-100 flex items-center justify-center">
            <Activity className="text-brand-600" size={20} />
          </div>
          <div>
            <h1 className="text-2xl font-semibold text-slate-900">System Health</h1>
            <p className="text-sm text-slate-500 mt-1">
              Platform component status across database, Ollama, n8n, Mautic.
            </p>
          </div>
        </div>
        <button
          onClick={load}
          className="inline-flex items-center gap-2 px-3 py-2 border border-slate-300 rounded-lg text-sm hover:bg-slate-50"
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      <div
        className={`rounded-xl p-5 border-2 ${
          overall === 'ok'
            ? 'bg-emerald-50 border-emerald-200'
            : overall === 'degraded'
              ? 'bg-amber-50 border-amber-200'
              : 'bg-red-50 border-red-200'
        }`}
      >
        <div className="flex items-center gap-3">
          {STATUS_ICON[overall] ?? <AlertCircle className="w-5 h-5 text-slate-400" />}
          <div>
            <div className="font-semibold capitalize text-slate-900">System {overall}</div>
            <div className="text-sm text-slate-600">
              {health?.events_last_hour ?? 0} events in the last hour
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {Object.entries(components).map(([name, info]) => (
          <div
            key={name}
            className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="font-medium text-slate-800 capitalize">{name}</span>
              {STATUS_ICON[info?.status ?? 'unknown'] ?? (
                <AlertCircle className="w-4 h-4 text-slate-400" />
              )}
            </div>
            <div
              className={`text-sm font-semibold ${
                STATUS_TEXT_COLOR[info?.status ?? ''] ?? 'text-slate-600'
              }`}
            >
              {(info?.status ?? 'unknown').toUpperCase()}
            </div>
            {info?.models && info.models.length > 0 && (
              <div className="text-xs text-slate-400 mt-2">
                {info.models.slice(0, 3).join(', ')}
              </div>
            )}
            {info?.detail && (
              <div className="text-xs text-red-500 mt-2 truncate">{info.detail}</div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

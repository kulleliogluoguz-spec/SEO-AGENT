'use client'

import { useEffect, useState, useCallback } from 'react'
import {
  AlertCircle,
  DollarSign,
  RefreshCw,
  Settings,
  TrendingDown,
  TrendingUp,
  Zap,
} from 'lucide-react'
import { apiFetch } from '@/lib/apiFetch'

type Analysis = {
  campaign_id: string
  campaign_name: string
  platform?: string
  reported_roas: number
  true_roas: number
  break_even_roas: number
  contribution_margin_pct: number
  gross_profit: number
  kill_signal: boolean
  scale_signal: boolean
  signal_reason: string
  confidence: number
}

type Summary = {
  kill_campaigns: number
  scale_campaigns: number
  estimated_weekly_waste: number
  product_cost_configured: boolean
}

type AnalysisResponse = {
  analyses: Analysis[]
  summary?: Summary
  note?: string
  message?: string
}

type SettingsResponse = {
  settings: {
    cogs?: number
    shipping_cost?: number
    return_rate?: number
    currency?: string
  }
}

export default function ProfitabilityPage() {
  const [analyses, setAnalyses] = useState<Analysis[]>([])
  const [summary, setSummary] = useState<Summary | null>(null)
  const [settings, setSettings] = useState({
    cogs: 0,
    shipping_cost: 0,
    return_rate: 5,
    avg_order_value: 50,
  })
  const [showSettings, setShowSettings] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  const loadAll = useCallback(async () => {
    setLoading(true)
    try {
      const [ar, sr] = await Promise.all([
        apiFetch<AnalysisResponse>(
          `/api/v1/ads/profitability/analysis?avg_order_value=${settings.avg_order_value}`,
        ),
        apiFetch<SettingsResponse>('/api/v1/ads/profitability/settings'),
      ])
      setAnalyses(ar.analyses ?? [])
      setSummary(ar.summary ?? null)
      if (sr.settings) {
        setSettings((prev) => ({
          ...prev,
          cogs: Number(sr.settings.cogs ?? 0),
          shipping_cost: Number(sr.settings.shipping_cost ?? 0),
          return_rate: Number(sr.settings.return_rate ?? 0.05) * 100,
        }))
      }
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
    // settings.avg_order_value intentionally omitted — user presses
    // "Save & Recalculate" to refetch with a new value.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    loadAll()
  }, [loadAll])

  async function saveSettings() {
    setSaving(true)
    try {
      await apiFetch('/api/v1/ads/profitability/settings', {
        method: 'POST',
        body: JSON.stringify({
          cogs: settings.cogs,
          shipping_cost: settings.shipping_cost,
          return_rate: settings.return_rate / 100,
          currency: 'USD',
        }),
      })
    } finally {
      setSaving(false)
      setShowSettings(false)
      loadAll()
    }
  }

  const kills = analyses.filter((a) => a.kill_signal)
  const scales = analyses.filter((a) => a.scale_signal)
  const neutral = analyses.filter((a) => !a.kill_signal && !a.scale_signal)

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">
            True Profitability Analysis
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Real ad profit accounting for COGS, shipping, and returns.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowSettings(!showSettings)}
            className="inline-flex items-center gap-2 px-3 py-2 border border-slate-300 rounded-lg text-sm hover:bg-slate-50"
          >
            <Settings size={14} /> Product Costs
          </button>
          <button
            onClick={loadAll}
            className="p-2 border border-slate-300 rounded-lg hover:bg-slate-50"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {showSettings && (
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
          <h3 className="font-semibold text-slate-800">Product Cost Settings</h3>
          <p className="text-sm text-slate-500">
            These values are used to calculate true profitability. Without them only
            ROAS thresholds are used.
          </p>
          <div className="grid grid-cols-4 gap-4">
            {[
              { label: 'Avg Order Value ($)', key: 'avg_order_value' as const, placeholder: '50' },
              { label: 'COGS per unit ($)', key: 'cogs' as const, placeholder: '15' },
              { label: 'Shipping per order ($)', key: 'shipping_cost' as const, placeholder: '5' },
              { label: 'Return rate (%)', key: 'return_rate' as const, placeholder: '5' },
            ].map(({ label, key, placeholder }) => (
              <div key={key}>
                <label className="block text-xs text-slate-600 mb-1">{label}</label>
                <input
                  type="number"
                  step="0.01"
                  value={settings[key]}
                  onChange={(e) =>
                    setSettings((prev) => ({ ...prev, [key]: Number(e.target.value) }))
                  }
                  placeholder={placeholder}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
                />
              </div>
            ))}
          </div>
          <button
            onClick={saveSettings}
            disabled={saving}
            className="bg-brand-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-brand-700 disabled:opacity-50"
          >
            {saving ? 'Saving…' : 'Save & Recalculate'}
          </button>
        </div>
      )}

      {summary && (
        <div className="grid grid-cols-4 gap-4">
          {[
            {
              label: 'Kill Signals',
              val: summary.kill_campaigns,
              color: 'text-red-600',
              bg: 'bg-red-50',
              border: 'border-red-200',
              icon: TrendingDown,
            },
            {
              label: 'Scale Signals',
              val: summary.scale_campaigns,
              color: 'text-emerald-600',
              bg: 'bg-emerald-50',
              border: 'border-emerald-200',
              icon: TrendingUp,
            },
            {
              label: 'Est. Weekly Waste',
              val: `$${summary.estimated_weekly_waste?.toLocaleString()}`,
              color: 'text-red-600',
              bg: 'bg-red-50',
              border: 'border-red-200',
              icon: DollarSign,
            },
            {
              label: 'Total Campaigns',
              val: analyses.length,
              color: 'text-slate-700',
              bg: 'bg-slate-50',
              border: 'border-slate-200',
              icon: Zap,
            },
          ].map((k) => {
            const Icon = k.icon
            return (
              <div key={k.label} className={`${k.bg} ${k.border} rounded-xl border p-4`}>
                <div className={`flex items-center gap-2 text-sm mb-1 ${k.color}`}>
                  <Icon size={14} /> {k.label}
                </div>
                <div className={`text-2xl font-semibold ${k.color}`}>{k.val}</div>
              </div>
            )
          })}
        </div>
      )}

      {summary && !summary.product_cost_configured && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-amber-800">
            <strong>Product costs not configured.</strong> Set COGS and shipping above
            for true profitability analysis. Without it, only ROAS thresholds are
            used.
          </div>
        </div>
      )}

      {kills.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold text-red-700 flex items-center gap-2">
            <TrendingDown size={18} /> Kill Signals ({kills.length})
          </h2>
          {kills.map((a) => (
            <div
              key={a.campaign_id}
              className="bg-red-50 border border-red-200 rounded-xl p-4"
            >
              <div className="flex items-start justify-between">
                <div>
                  <div className="font-semibold text-red-900">{a.campaign_name}</div>
                  <div className="text-sm text-red-600 mt-1">{a.signal_reason}</div>
                  <div className="flex gap-4 mt-2 text-xs">
                    <span className="text-slate-600">
                      Reported:{' '}
                      <strong className="text-slate-900">{a.reported_roas?.toFixed(2)}x</strong>
                    </span>
                    <span className="text-red-700">
                      True: <strong>{a.true_roas?.toFixed(2)}x</strong>
                    </span>
                    <span className="text-slate-600">
                      Break-even:{' '}
                      <strong className="text-slate-900">
                        {a.break_even_roas?.toFixed(2)}x
                      </strong>
                    </span>
                    <span className="text-red-700">
                      Profit: <strong>${a.gross_profit?.toFixed(0)}</strong>
                    </span>
                  </div>
                </div>
                <div className="text-right flex-shrink-0 ml-4">
                  <div className="text-[10px] text-slate-400 uppercase">Confidence</div>
                  <div className="text-sm font-medium text-slate-700">
                    {(a.confidence * 100).toFixed(0)}%
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {scales.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold text-emerald-700 flex items-center gap-2">
            <TrendingUp size={18} /> Scale Signals ({scales.length})
          </h2>
          {scales.map((a) => (
            <div
              key={a.campaign_id}
              className="bg-emerald-50 border border-emerald-200 rounded-xl p-4"
            >
              <div className="flex items-start justify-between">
                <div>
                  <div className="font-semibold text-emerald-900">{a.campaign_name}</div>
                  <div className="text-sm text-emerald-700 mt-1">{a.signal_reason}</div>
                  <div className="flex gap-4 mt-2 text-xs">
                    <span className="text-slate-600">
                      Reported:{' '}
                      <strong className="text-slate-900">{a.reported_roas?.toFixed(2)}x</strong>
                    </span>
                    <span className="text-emerald-700">
                      True: <strong>{a.true_roas?.toFixed(2)}x</strong>
                    </span>
                    <span className="text-slate-600">
                      Margin:{' '}
                      <strong className="text-slate-900">
                        {a.contribution_margin_pct?.toFixed(0)}%
                      </strong>
                    </span>
                    <span className="text-emerald-700">
                      Profit: <strong>${a.gross_profit?.toFixed(0)}</strong>
                    </span>
                  </div>
                </div>
                <div className="text-[10px] text-slate-400 ml-4">
                  {(a.confidence * 100).toFixed(0)}% confident
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {neutral.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
          <div className="p-4 border-b border-slate-100">
            <h2 className="font-semibold text-slate-700">Monitoring ({neutral.length})</h2>
          </div>
          <div className="divide-y divide-slate-100">
            {neutral.map((a) => (
              <div key={a.campaign_id} className="p-4 flex items-center justify-between">
                <div>
                  <div className="font-medium text-slate-800">{a.campaign_name}</div>
                  <div className="text-xs text-slate-500">{a.signal_reason}</div>
                </div>
                <div className="flex gap-6 text-xs text-right">
                  <div>
                    <div className="text-slate-400 uppercase">True ROAS</div>
                    <div className="font-semibold text-slate-700">
                      {a.true_roas?.toFixed(2)}x
                    </div>
                  </div>
                  <div>
                    <div className="text-slate-400 uppercase">Profit/wk</div>
                    <div
                      className={`font-semibold ${
                        a.gross_profit >= 0 ? 'text-emerald-700' : 'text-red-600'
                      }`}
                    >
                      ${a.gross_profit?.toFixed(0)}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

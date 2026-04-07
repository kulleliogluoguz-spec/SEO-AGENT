'use client'

import { useEffect, useState, useCallback } from 'react'
import { FileText, Loader2, RefreshCw, AlertCircle } from 'lucide-react'
import { apiFetch } from '@/lib/apiFetch'

interface Summary {
  total_spend: number
  total_revenue: number
  total_conversions: number
  overall_roas: number
  active_campaigns: number
  pending_recommendations: number
  critical_recommendations: number
}

interface WeeklyReport {
  summary: Summary
  campaigns_count: number
  report_text: string
}

export default function WeeklyReportPage() {
  const [report, setReport] = useState<WeeklyReport | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true); setError(null)
    try {
      const data = await apiFetch<WeeklyReport>('/api/v1/ads/reports/weekly', { timeoutMs: 180_000 })
      setReport(data)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  return (
    <div className="space-y-5 max-w-4xl">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-amber-100 rounded-xl flex items-center justify-center">
            <FileText size={16} className="text-amber-600" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-gray-900">Weekly AI Report</h1>
            <p className="text-xs text-gray-500">Local Ollama-generated executive summary</p>
          </div>
        </div>
        <button
          onClick={load}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-40"
        >
          {loading ? <Loader2 size={12} className="animate-spin" /> : <RefreshCw size={12} />}
          Regenerate
        </button>
      </div>

      {error && (
        <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          <AlertCircle size={14} /> {error}
        </div>
      )}

      {loading ? (
        <div className="card p-12 text-center">
          <Loader2 className="w-7 h-7 animate-spin text-gray-400 mx-auto mb-3" />
          <p className="text-sm text-gray-500">Generating report with local Ollama...</p>
          <p className="text-xs text-gray-400 mt-1">This may take 30-60 seconds</p>
        </div>
      ) : report ? (
        <>
          {/* KPI bar */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="card p-4">
              <p className="text-[10px] text-gray-500 uppercase">Spend</p>
              <p className="text-xl font-bold text-gray-900">${report.summary.total_spend.toLocaleString(undefined, { maximumFractionDigits: 0 })}</p>
            </div>
            <div className="card p-4">
              <p className="text-[10px] text-gray-500 uppercase">Revenue</p>
              <p className="text-xl font-bold text-gray-900">${report.summary.total_revenue.toLocaleString(undefined, { maximumFractionDigits: 0 })}</p>
            </div>
            <div className="card p-4">
              <p className="text-[10px] text-gray-500 uppercase">ROAS</p>
              <p className={`text-xl font-bold ${report.summary.overall_roas >= 3 ? 'text-emerald-600' : report.summary.overall_roas >= 1.5 ? 'text-blue-600' : 'text-red-500'}`}>
                {report.summary.overall_roas.toFixed(2)}x
              </p>
            </div>
            <div className="card p-4">
              <p className="text-[10px] text-gray-500 uppercase">Conversions</p>
              <p className="text-xl font-bold text-gray-900">{report.summary.total_conversions.toLocaleString(undefined, { maximumFractionDigits: 0 })}</p>
            </div>
          </div>

          {/* AI report text */}
          <div className="card p-6">
            <h3 className="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2">
              <FileText size={14} /> Executive Summary
            </h3>
            <div className="prose prose-sm max-w-none">
              <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">
                {report.report_text}
              </p>
            </div>
          </div>
        </>
      ) : null}
    </div>
  )
}

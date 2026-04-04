'use client'

import { useEffect, useState, useCallback } from 'react'
import Link from 'next/link'
import { Phone, Upload, Flame, Zap, Snowflake, XCircle, RefreshCw, Trash2, Clock } from 'lucide-react'

const API = 'http://localhost:8000'

interface CallAnalysis {
  customer_name?: string
  customer_phone?: string
  company_name?: string
  call_summary?: string
  sales_potential?: 'hot' | 'warm' | 'cold' | 'not_interested'
  sales_score?: number
}

interface Call {
  id: string
  type: 'inbound' | 'outbound'
  phone_number?: string
  rep_name?: string
  filename?: string
  status: 'queued' | 'transcribing' | 'analyzing' | 'completed' | 'failed'
  created_at: string
  duration?: number
  analysis?: CallAnalysis
  error?: string
}

interface Stats {
  total_calls: number
  completed: number
  this_week: number
  sales_breakdown: { hot: number; warm: number; cold: number; not_interested: number }
  avg_sales_score: number
}

const POTENTIAL_CONFIG = {
  hot:           { label: '🔥 Hot',           cls: 'bg-red-100 text-red-700' },
  warm:          { label: '⚡ Warm',          cls: 'bg-amber-100 text-amber-700' },
  cold:          { label: '❄️ Cold',           cls: 'bg-blue-100 text-blue-700' },
  not_interested:{ label: '✗ Not Interested', cls: 'bg-gray-100 text-gray-600' },
}

const STATUS_CONFIG = {
  queued:       { label: 'Queued',        cls: 'bg-gray-100 text-gray-500',   spin: false },
  transcribing: { label: 'Transcribing…', cls: 'bg-blue-100 text-blue-600',  spin: true  },
  analyzing:    { label: 'Analyzing…',    cls: 'bg-purple-100 text-purple-600', spin: true },
  completed:    { label: 'Done',          cls: 'bg-green-100 text-green-700', spin: false },
  failed:       { label: 'Failed',        cls: 'bg-red-100 text-red-700',     spin: false },
}

function StatusBadge({ status }: { status: Call['status'] }) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.queued
  return (
    <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-medium ${cfg.cls}`}>
      {cfg.spin && <RefreshCw size={10} className="animate-spin" />}
      {cfg.label}
    </span>
  )
}

function PotentialBadge({ potential }: { potential?: string }) {
  if (!potential) return <span className="text-gray-300 text-xs">—</span>
  const cfg = POTENTIAL_CONFIG[potential as keyof typeof POTENTIAL_CONFIG]
  if (!cfg) return null
  return <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${cfg.cls}`}>{cfg.label}</span>
}

function ScoreBar({ score }: { score?: number }) {
  if (score == null) return <span className="text-gray-300 text-xs">—</span>
  const color = score >= 80 ? 'bg-green-500' : score >= 50 ? 'bg-amber-500' : 'bg-red-400'
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1.5 bg-gray-200 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${score}%` }} />
      </div>
      <span className="text-xs font-medium text-gray-700">{score}</span>
    </div>
  )
}

export default function CallsPage() {
  const [calls, setCalls] = useState<Call[]>([])
  const [stats, setStats] = useState<Stats | null>(null)
  const [loading, setLoading] = useState(true)
  const [apiError, setApiError] = useState(false)

  const hasInProgress = calls.some(c => ['queued', 'transcribing', 'analyzing'].includes(c.status))

  const fetchData = useCallback(async () => {
    try {
      const [callsRes, statsRes] = await Promise.all([
        fetch(`${API}/api/v1/calls`),
        fetch(`${API}/api/v1/calls/stats`),
      ])
      if (callsRes.ok) {
        const data = await callsRes.json()
        setCalls(data.calls)
      }
      if (statsRes.ok) setStats(await statsRes.json())
      setApiError(false)
    } catch {
      setApiError(true)
    }
    setLoading(false)
  }, [])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  // Auto-refresh while calls are in progress
  useEffect(() => {
    if (!hasInProgress) return
    const id = setInterval(fetchData, 5000)
    return () => clearInterval(id)
  }, [hasInProgress, fetchData])

  async function deleteCall(id: string) {
    await fetch(`${API}/api/v1/calls/${id}`, { method: 'DELETE' })
    fetchData()
  }

  function fmt(iso: string) {
    return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
  }

  function fmtDuration(s?: number) {
    if (!s) return '—'
    const m = Math.floor(s / 60), sec = s % 60
    return `${m}:${String(sec).padStart(2, '0')}`
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Call Intelligence</h1>
          <p className="text-sm text-gray-500 mt-0.5">AI-powered sales call analysis</p>
        </div>
        <Link
          href="/dashboard/calls/upload"
          className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
        >
          <Upload size={14} />
          Log Inbound Call
        </Link>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-white rounded-xl border p-4">
            <div className="flex items-center gap-2 mb-1">
              <Phone size={14} className="text-gray-400" />
              <span className="text-xs text-gray-500 font-medium">This Week</span>
            </div>
            <div className="text-2xl font-bold text-gray-900">{stats.this_week}</div>
            <div className="text-xs text-gray-400">{stats.total_calls} total</div>
          </div>
          <div className="bg-white rounded-xl border p-4">
            <div className="flex items-center gap-2 mb-1">
              <Flame size={14} className="text-red-400" />
              <span className="text-xs text-gray-500 font-medium">Hot Leads</span>
            </div>
            <div className="text-2xl font-bold text-red-600">{stats.sales_breakdown.hot}</div>
            <div className="text-xs text-gray-400">strong buying intent</div>
          </div>
          <div className="bg-white rounded-xl border p-4">
            <div className="flex items-center gap-2 mb-1">
              <Zap size={14} className="text-amber-400" />
              <span className="text-xs text-gray-500 font-medium">Warm Leads</span>
            </div>
            <div className="text-2xl font-bold text-amber-600">{stats.sales_breakdown.warm}</div>
            <div className="text-xs text-gray-400">needs follow-up</div>
          </div>
          <div className="bg-white rounded-xl border p-4">
            <div className="flex items-center gap-2 mb-1">
              <Snowflake size={14} className="text-blue-400" />
              <span className="text-xs text-gray-500 font-medium">Cold / No Interest</span>
            </div>
            <div className="text-2xl font-bold text-blue-600">
              {stats.sales_breakdown.cold + stats.sales_breakdown.not_interested}
            </div>
            <div className="text-xs text-gray-400">avg score {Math.round(stats.avg_sales_score)}</div>
          </div>
        </div>
      )}

      {/* Calls Table */}
      <div className="bg-white rounded-xl border overflow-hidden">
        <div className="px-4 py-3 border-b flex items-center justify-between">
          <span className="text-sm font-semibold text-gray-800">Call Log</span>
          {hasInProgress && (
            <span className="text-xs text-blue-500 flex items-center gap-1">
              <RefreshCw size={10} className="animate-spin" /> Processing — auto-refreshing
            </span>
          )}
        </div>

        {apiError ? (
          <div className="p-8 text-center">
            <p className="text-red-500 font-medium text-sm">Cannot reach API</p>
            <p className="text-gray-400 text-xs mt-1">Make sure the backend is running on port 8000</p>
            <button onClick={fetchData} className="mt-3 text-xs text-blue-500 hover:underline">Retry</button>
          </div>
        ) : loading ? (
          <div className="p-8 text-center text-gray-400 text-sm">Loading…</div>
        ) : calls.length === 0 ? (
          <div className="p-12 text-center">
            <Phone size={32} className="text-gray-200 mx-auto mb-3" />
            <p className="text-gray-500 font-medium">No calls yet</p>
            <p className="text-gray-400 text-sm mt-1">Upload a call recording to get started</p>
            <Link href="/dashboard/calls/upload" className="mt-4 inline-block text-blue-600 text-sm font-medium hover:underline">
              Log your first call →
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  {['Date', 'Phone', 'Customer', 'Company', 'Type', 'Duration', 'Potential', 'Score', 'Status', ''].map((h, i) => (
                    <th key={i} className="px-4 py-2.5 text-left text-xs font-semibold text-gray-500 whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {calls.map(call => {
                  const a = call.analysis
                  return (
                    <tr key={call.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3 text-gray-500 text-xs whitespace-nowrap">{fmt(call.created_at)}</td>
                      <td className="px-4 py-3 text-gray-700 font-mono text-xs">{call.phone_number || '—'}</td>
                      <td className="px-4 py-3 text-gray-800 font-medium">{a?.customer_name || '—'}</td>
                      <td className="px-4 py-3 text-gray-600">{a?.company_name || '—'}</td>
                      <td className="px-4 py-3">
                        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                          call.type === 'outbound' ? 'bg-indigo-50 text-indigo-600' : 'bg-teal-50 text-teal-600'
                        }`}>
                          {call.type}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-gray-500 text-xs">
                        <span className="flex items-center gap-1">
                          <Clock size={10} />
                          {fmtDuration(call.duration)}
                        </span>
                      </td>
                      <td className="px-4 py-3"><PotentialBadge potential={a?.sales_potential} /></td>
                      <td className="px-4 py-3"><ScoreBar score={a?.sales_score} /></td>
                      <td className="px-4 py-3"><StatusBadge status={call.status} /></td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          {call.status === 'completed' && (
                            <Link href={`/dashboard/calls/${call.id}`} className="text-blue-500 hover:text-blue-700 text-xs font-medium">
                              View
                            </Link>
                          )}
                          <button
                            onClick={() => deleteCall(call.id)}
                            className="text-gray-300 hover:text-red-400 transition-colors"
                          >
                            <Trash2 size={13} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

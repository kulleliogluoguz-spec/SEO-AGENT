'use client'

import { useEffect, useState } from 'react'
import { Download, Flame, Zap, Snowflake, XCircle, ChevronDown, ChevronUp } from 'lucide-react'

const API = 'http://localhost:8000'

interface Customer {
  customer_name: string
  customer_phone: string
  company: string
  call_date: string
  duration?: number
  sales_potential: string
  sales_score: number
  summary: string
  key_requests: string[]
  follow_up: boolean
  follow_up_actions: string[]
  reasoning: string
}

interface WeeklyReport {
  period: { from: string; to: string }
  total_calls: number
  customers: Customer[]
  hot_leads: Customer[]
  warm_leads: Customer[]
  cold_leads: Customer[]
  not_interested: Customer[]
}

const POTENTIAL_CONFIG = {
  hot:           { label: '🔥 Hot',           cls: 'bg-red-100 text-red-700',    header: 'Hot Leads',          icon: Flame,     iconCls: 'text-red-400' },
  warm:          { label: '⚡ Warm',          cls: 'bg-amber-100 text-amber-700',header: 'Warm Leads',         icon: Zap,       iconCls: 'text-amber-400' },
  cold:          { label: '❄️ Cold',           cls: 'bg-blue-100 text-blue-700',  header: 'Cold',               icon: Snowflake, iconCls: 'text-blue-400' },
  not_interested:{ label: '✗ Not Interested', cls: 'bg-gray-100 text-gray-500',  header: 'Not Interested',     icon: XCircle,   iconCls: 'text-gray-400' },
}

function exportCSV(customers: Customer[]) {
  const headers = ['Customer', 'Phone', 'Company', 'Date', 'Score', 'Potential', 'Summary', 'Key Requests', 'Follow-up Actions']
  const rows = customers.map(c => [
    c.customer_name, c.customer_phone, c.company,
    new Date(c.call_date).toLocaleDateString(),
    c.sales_score, c.sales_potential,
    `"${c.summary.replace(/"/g, '""')}"`,
    `"${c.key_requests.join('; ')}"`,
    `"${c.follow_up_actions.join('; ')}"`,
  ])
  const csv = [headers, ...rows].map(r => r.join(',')).join('\n')
  const blob = new Blob([csv], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `sales-report-${new Date().toISOString().split('T')[0]}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

function CustomerRow({ c }: { c: Customer }) {
  const [expanded, setExpanded] = useState(false)
  const cfg = POTENTIAL_CONFIG[c.sales_potential as keyof typeof POTENTIAL_CONFIG]
  const scoreColor = c.sales_score >= 80 ? 'text-green-600' : c.sales_score >= 50 ? 'text-amber-600' : 'text-red-500'

  return (
    <>
      <tr
        className="hover:bg-gray-50 cursor-pointer transition-colors"
        onClick={() => setExpanded(v => !v)}
      >
        <td className="px-4 py-3 font-medium text-gray-800 text-sm">{c.customer_name}</td>
        <td className="px-4 py-3 text-gray-500 text-xs font-mono">{c.customer_phone}</td>
        <td className="px-4 py-3 text-gray-600 text-sm">{c.company}</td>
        <td className="px-4 py-3 text-gray-500 text-xs">
          {new Date(c.call_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
        </td>
        <td className="px-4 py-3">
          <span className={`text-sm font-bold ${scoreColor}`}>{c.sales_score}</span>
        </td>
        <td className="px-4 py-3">
          {cfg && <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${cfg.cls}`}>{cfg.label}</span>}
        </td>
        <td className="px-4 py-3 text-gray-600 text-xs max-w-xs truncate">{c.summary}</td>
        <td className="px-4 py-3">
          {c.follow_up && <span className="w-1.5 h-1.5 rounded-full bg-amber-400 inline-block" title="Follow-up recommended" />}
        </td>
        <td className="px-4 py-3 text-gray-400">
          {expanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
        </td>
      </tr>
      {expanded && (
        <tr className="bg-gray-50">
          <td colSpan={9} className="px-6 py-4">
            <div className="grid grid-cols-3 gap-4 text-xs">
              <div>
                <p className="font-medium text-gray-500 mb-1">Key Requests</p>
                {c.key_requests.length > 0
                  ? c.key_requests.map((r, i) => <p key={i} className="text-gray-700">• {r}</p>)
                  : <p className="text-gray-400">None recorded</p>}
              </div>
              <div>
                <p className="font-medium text-gray-500 mb-1">Follow-up Actions</p>
                {c.follow_up_actions.length > 0
                  ? c.follow_up_actions.map((a, i) => <p key={i} className="text-gray-700">→ {a}</p>)
                  : <p className="text-gray-400">None</p>}
              </div>
              <div>
                <p className="font-medium text-gray-500 mb-1">Score Reasoning</p>
                <p className="text-gray-700 leading-relaxed">{c.reasoning || '—'}</p>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  )
}

export default function WeeklyReportPage() {
  const [report, setReport] = useState<WeeklyReport | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${API}/api/v1/calls/weekly-report`)
      .then(r => r.json())
      .then(setReport)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="p-8 text-gray-400 text-sm">Loading…</div>
  if (!report) return <div className="p-8 text-red-500 text-sm">Could not load report — is the backend running?</div>

  const from = new Date(report.period.from).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  const to   = new Date(report.period.to).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Weekly Sales Report</h1>
          <p className="text-sm text-gray-500 mt-0.5">{from} — {to} · {report.total_calls} calls analyzed</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => window.print()}
            className="text-xs px-3 py-1.5 border rounded-lg hover:bg-gray-50 text-gray-600"
          >
            Print
          </button>
          <button
            onClick={() => exportCSV(report.customers)}
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            <Download size={12} /> Export CSV
          </button>
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {(Object.entries(POTENTIAL_CONFIG) as [string, typeof POTENTIAL_CONFIG['hot']][]).map(([key, cfg]) => {
          const count = key === 'hot' ? report.hot_leads.length
            : key === 'warm' ? report.warm_leads.length
            : key === 'cold' ? report.cold_leads.length
            : report.not_interested.length
          const Icon = cfg.icon
          return (
            <div key={key} className="bg-white rounded-xl border p-4">
              <div className="flex items-center gap-2 mb-1">
                <Icon size={14} className={cfg.iconCls} />
                <span className="text-xs font-medium text-gray-500">{cfg.header}</span>
              </div>
              <div className="text-3xl font-bold text-gray-900">{count}</div>
              <div className="text-xs text-gray-400 mt-0.5">customers</div>
            </div>
          )
        })}
      </div>

      {/* Table */}
      {report.customers.length === 0 ? (
        <div className="bg-white rounded-xl border p-12 text-center">
          <p className="text-gray-500 font-medium">No completed calls this week</p>
          <p className="text-gray-400 text-sm mt-1">Upload and analyze calls to populate this report</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border overflow-hidden">
          <div className="px-4 py-3 border-b">
            <span className="text-sm font-semibold text-gray-800">Customer Intelligence — sorted by sales score</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  {['Customer', 'Phone', 'Company', 'Date', 'Score', 'Potential', 'Summary', 'Follow-up', ''].map(h => (
                    <th key={h} className="px-4 py-2.5 text-left text-xs font-semibold text-gray-500 whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {report.customers.map((c, i) => <CustomerRow key={i} c={c} />)}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

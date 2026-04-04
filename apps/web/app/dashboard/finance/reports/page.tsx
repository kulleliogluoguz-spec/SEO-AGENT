'use client'

import { useEffect, useState, useCallback } from 'react'
import {
  PieChart, DollarSign, FileText, TrendingUp,
  Download, AlertCircle, RefreshCw, ExternalLink, Calendar,
} from 'lucide-react'

const TAXHACKER_URL = 'http://localhost:7331'

interface TxRow {
  name: string
  merchant: string
  total: number
  currencyCode: string
  issuedAt: string
  categoryCode: string
  extra?: {
    vat?: number
  }
}

interface MonthlySummary {
  totalSpent: number
  totalTax: number
  invoiceCount: number
  topVendor: string
  byCurrency: Record<string, number>
  byCategory: { category: string; total: number; count: number }[]
}

const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
]

function parseCSV(text: string): TxRow[] {
  const lines = text.trim().split('\n').filter(Boolean)
  if (lines.length < 2) return []
  const headers = lines[0].split(',').map(h => h.replace(/^"|"$/g, '').trim())
  return lines.slice(1).map(line => {
    const vals = line.match(/("(?:[^"\\]|\\.)*"|[^,]*)/g)?.map(v => v.replace(/^"|"$/g, '').trim()) ?? []
    const obj: Record<string, string> = {}
    headers.forEach((h, i) => { obj[h] = vals[i] ?? '' })
    return {
      name: obj.name || '',
      merchant: obj.merchant || '',
      total: parseFloat(obj.total || '0') || 0,
      currencyCode: obj.currencyCode || 'EUR',
      issuedAt: obj.issuedAt || '',
      categoryCode: obj.categoryCode || 'other',
      extra: { vat: parseFloat(obj['extra.vat'] || obj.vat || '0') || undefined },
    }
  })
}

function summarize(rows: TxRow[]): MonthlySummary {
  const totalSpent = rows.reduce((s, r) => s + (r.total || 0), 0)
  const totalTax = rows.reduce((s, r) => s + (r.extra?.vat || 0), 0)
  const invoiceCount = rows.length

  // Top vendor by spend
  const vendorTotals: Record<string, number> = {}
  for (const r of rows) {
    const v = r.merchant || r.name || 'Unknown'
    vendorTotals[v] = (vendorTotals[v] || 0) + (r.total || 0)
  }
  const topVendor = Object.entries(vendorTotals).sort((a, b) => b[1] - a[1])[0]?.[0] || '—'

  // By currency
  const byCurrency: Record<string, number> = {}
  for (const r of rows) {
    const c = r.currencyCode || 'EUR'
    byCurrency[c] = (byCurrency[c] || 0) + (r.total || 0)
  }

  // By category
  const catMap: Record<string, { total: number; count: number }> = {}
  for (const r of rows) {
    const cat = r.categoryCode || 'other'
    if (!catMap[cat]) catMap[cat] = { total: 0, count: 0 }
    catMap[cat].total += r.total || 0
    catMap[cat].count++
  }
  const byCategory = Object.entries(catMap)
    .map(([category, { total, count }]) => ({ category, total, count }))
    .sort((a, b) => b.total - a.total)

  return { totalSpent, totalTax, invoiceCount, topVendor, byCurrency, byCategory }
}

function SummaryCard({ icon: Icon, label, value, sub, color }: {
  icon: React.ElementType
  label: string
  value: string
  sub?: string
  color: string
}) {
  return (
    <div className="card p-5">
      <div className="flex items-center gap-3 mb-3">
        <div className={`w-9 h-9 rounded-xl flex items-center justify-center ${color}`}>
          <Icon size={16} className="text-white" />
        </div>
        <p className="text-sm text-gray-500 font-medium">{label}</p>
      </div>
      <p className="text-2xl font-bold text-gray-900">{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
    </div>
  )
}

export default function TaxReportsPage() {
  const now = new Date()
  const [year, setYear] = useState(now.getFullYear())
  const [month, setMonth] = useState(now.getMonth()) // 0-indexed
  const [rows, setRows] = useState<TxRow[]>([])
  const [summary, setSummary] = useState<MonthlySummary | null>(null)
  const [loading, setLoading] = useState(false)
  const [taxhackerAvailable, setTaxhackerAvailable] = useState<boolean | null>(null)
  const [error, setError] = useState<string | null>(null)

  // Check availability
  useEffect(() => {
    fetch(`${TAXHACKER_URL}/api/auth/get-session`, { credentials: 'include' })
      .then(r => setTaxhackerAvailable(r.ok || r.status === 401 || r.status === 200))
      .catch(() => setTaxhackerAvailable(false))
  }, [])

  const loadReport = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const dateFrom = `${year}-${String(month + 1).padStart(2, '0')}-01`
      const lastDay = new Date(year, month + 1, 0).getDate()
      const dateTo = `${year}-${String(month + 1).padStart(2, '0')}-${String(lastDay).padStart(2, '0')}`

      const fields = 'name,merchant,total,currencyCode,issuedAt,categoryCode,extra.vat'
      const url = `${TAXHACKER_URL}/export/transactions?fields=${fields}&dateFrom=${dateFrom}&dateTo=${dateTo}`

      const res = await fetch(url, { credentials: 'include' })
      if (!res.ok) { setError('Failed to load report data'); setLoading(false); return }

      const text = await res.text()
      const parsed = parseCSV(text)
      setRows(parsed)
      setSummary(summarize(parsed))
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load report')
    } finally {
      setLoading(false)
    }
  }, [year, month])

  useEffect(() => {
    if (taxhackerAvailable) loadReport()
  }, [taxhackerAvailable, loadReport])

  function downloadCSV() {
    const dateFrom = `${year}-${String(month + 1).padStart(2, '0')}-01`
    const lastDay = new Date(year, month + 1, 0).getDate()
    const dateTo = `${year}-${String(month + 1).padStart(2, '0')}-${String(lastDay).padStart(2, '0')}`
    const fields = 'name,merchant,total,currencyCode,issuedAt,categoryCode,extra.vat'
    window.open(
      `${TAXHACKER_URL}/export/transactions?fields=${fields}&dateFrom=${dateFrom}&dateTo=${dateTo}`,
      '_blank'
    )
  }

  function printReport() {
    window.print()
  }

  if (taxhackerAvailable === false) {
    return (
      <div className="space-y-4">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Tax Reports</h1>
          <p className="text-sm text-gray-500">Monthly expense and tax summaries</p>
        </div>
        <div className="card p-10 text-center space-y-4">
          <AlertCircle size={32} className="mx-auto text-yellow-400" />
          <p className="text-base font-semibold text-gray-800">Invoice service is not running</p>
          <div className="bg-gray-900 text-green-400 text-sm font-mono px-4 py-3 rounded-lg inline-block">
            cd apps/taxhacker && npm run dev
          </div>
        </div>
      </div>
    )
  }

  const primaryCurrency = summary ? Object.entries(summary.byCurrency).sort((a, b) => b[1] - a[1])[0] : null
  const currencyCode = primaryCurrency?.[0] || 'EUR'
  const fmt = (n: number) => n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

  return (
    <div className="space-y-5 print:space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Tax Reports</h1>
          <p className="text-sm text-gray-500">Monthly expense and tax summary from your invoices</p>
        </div>
        <div className="flex items-center gap-2 print:hidden">
          <button onClick={loadReport} disabled={loading} className="btn-secondary flex items-center gap-1.5">
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} /> Refresh
          </button>
          <button onClick={downloadCSV} className="btn-secondary flex items-center gap-1.5">
            <Download size={13} /> Export CSV
          </button>
          <button onClick={printReport} className="btn-secondary flex items-center gap-1.5">
            <FileText size={13} /> Print
          </button>
          <a
            href={`${TAXHACKER_URL}/transactions`}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-secondary flex items-center gap-1.5"
          >
            <ExternalLink size={13} /> TaxHacker
          </a>
        </div>
      </div>

      {/* Period selector */}
      <div className="flex items-center gap-3 print:hidden">
        <div className="flex items-center gap-2 bg-white border border-gray-200 rounded-lg px-3 py-2 shadow-sm">
          <Calendar size={14} className="text-gray-400" />
          <select
            value={month}
            onChange={e => setMonth(Number(e.target.value))}
            className="text-sm font-medium text-gray-700 bg-transparent outline-none"
          >
            {MONTHS.map((m, i) => <option key={m} value={i}>{m}</option>)}
          </select>
          <select
            value={year}
            onChange={e => setYear(Number(e.target.value))}
            className="text-sm font-medium text-gray-700 bg-transparent outline-none"
          >
            {[2023, 2024, 2025, 2026].map(y => <option key={y} value={y}>{y}</option>)}
          </select>
        </div>
        <p className="text-sm text-gray-500">
          {loading ? 'Loading…' : `${rows.length} invoices found`}
        </p>
      </div>

      {error && (
        <div className="flex items-center gap-2 px-4 py-3 bg-red-50 text-red-700 rounded-lg text-sm border border-red-200">
          <AlertCircle size={14} />
          {error}
        </div>
      )}

      {/* Summary cards */}
      {loading ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map(i => <div key={i} className="h-28 card animate-pulse" />)}
        </div>
      ) : summary ? (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <SummaryCard
              icon={DollarSign}
              label="Total Spent"
              value={`${fmt(summary.totalSpent)} ${currencyCode}`}
              sub={`${summary.invoiceCount} invoice${summary.invoiceCount !== 1 ? 's' : ''}`}
              color="bg-blue-500"
            />
            <SummaryCard
              icon={TrendingUp}
              label="Total Tax"
              value={summary.totalTax > 0 ? `${fmt(summary.totalTax)} ${currencyCode}` : '—'}
              sub={summary.totalTax > 0
                ? `${((summary.totalTax / (summary.totalSpent || 1)) * 100).toFixed(1)}% effective rate`
                : 'No VAT data extracted yet'}
              color="bg-purple-500"
            />
            <SummaryCard
              icon={FileText}
              label="Invoices"
              value={String(summary.invoiceCount)}
              sub={`${MONTHS[month]} ${year}`}
              color="bg-emerald-500"
            />
            <SummaryCard
              icon={PieChart}
              label="Top Vendor"
              value={summary.topVendor}
              sub={summary.byCategory[0]
                ? `Most spend: ${summary.byCategory[0].category.replace('_', ' ')}`
                : undefined}
              color="bg-amber-500"
            />
          </div>

          {/* By-currency breakdown (if multi-currency) */}
          {Object.keys(summary.byCurrency).length > 1 && (
            <div className="card p-5">
              <h3 className="text-sm font-semibold text-gray-700 mb-3">By Currency</h3>
              <div className="flex flex-wrap gap-3">
                {Object.entries(summary.byCurrency).map(([currency, total]) => (
                  <div key={currency} className="flex items-center gap-2 px-3 py-1.5 bg-gray-50 rounded-lg">
                    <span className="text-xs font-bold text-gray-500">{currency}</span>
                    <span className="text-sm font-semibold text-gray-800">{fmt(total)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Category breakdown table */}
          {summary.byCategory.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <div className="px-5 py-3 border-b bg-gray-50">
                <h3 className="text-sm font-semibold text-gray-700">Breakdown by Category</h3>
              </div>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b">
                    <th className="text-left px-5 py-3 font-medium text-gray-500 text-xs uppercase tracking-wider">Category</th>
                    <th className="text-right px-5 py-3 font-medium text-gray-500 text-xs uppercase tracking-wider">Invoices</th>
                    <th className="text-right px-5 py-3 font-medium text-gray-500 text-xs uppercase tracking-wider">Total</th>
                    <th className="text-right px-5 py-3 font-medium text-gray-500 text-xs uppercase tracking-wider">% of Spend</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {summary.byCategory.map(({ category, total, count }) => (
                    <tr key={category} className="hover:bg-gray-50">
                      <td className="px-5 py-3">
                        <span className="px-2 py-0.5 rounded-full text-xs bg-gray-100 text-gray-700 capitalize font-medium">
                          {category.replace(/_/g, ' ')}
                        </span>
                      </td>
                      <td className="px-5 py-3 text-right text-gray-600">{count}</td>
                      <td className="px-5 py-3 text-right font-semibold text-gray-900">
                        {fmt(total)} {currencyCode}
                      </td>
                      <td className="px-5 py-3 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <div className="w-16 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-brand-500 rounded-full"
                              style={{ width: `${Math.min(100, (total / summary.totalSpent) * 100)}%` }}
                            />
                          </div>
                          <span className="text-xs text-gray-500 w-10 text-right">
                            {((total / summary.totalSpent) * 100).toFixed(1)}%
                          </span>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot className="border-t bg-gray-50">
                  <tr>
                    <td className="px-5 py-3 text-sm font-semibold text-gray-700">Total</td>
                    <td className="px-5 py-3 text-right text-sm font-semibold text-gray-700">{summary.invoiceCount}</td>
                    <td className="px-5 py-3 text-right text-sm font-bold text-gray-900">
                      {fmt(summary.totalSpent)} {currencyCode}
                    </td>
                    <td className="px-5 py-3 text-right text-sm font-semibold text-gray-500">100%</td>
                  </tr>
                </tfoot>
              </table>
            </div>
          )}

          {/* Empty state */}
          {summary.invoiceCount === 0 && (
            <div className="card p-10 text-center space-y-3">
              <FileText size={28} className="mx-auto text-gray-200" />
              <p className="text-sm font-medium text-gray-500">
                No invoices for {MONTHS[month]} {year}
              </p>
              <p className="text-xs text-gray-400">
                Upload invoices in the{' '}
                <a href="/dashboard/finance/invoices" className="text-brand-600 hover:underline">
                  Invoices page
                </a>
              </p>
            </div>
          )}
        </>
      ) : null}
    </div>
  )
}

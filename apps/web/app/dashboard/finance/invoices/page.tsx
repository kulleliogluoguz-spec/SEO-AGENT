'use client'

import { useEffect, useState, useCallback } from 'react'
import {
  FileText, Upload, AlertCircle, RefreshCw,
  ExternalLink, Download, Calendar, DollarSign,
  CheckCircle2, Clock,
} from 'lucide-react'

const TAXHACKER_URL = 'http://localhost:7331'

interface Invoice {
  name: string
  merchant: string
  total: number
  currencyCode: string
  issuedAt: string
  categoryCode: string
}

const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
]

function parseCSV(text: string): Invoice[] {
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
    }
  })
}

function fmt(n: number) {
  return n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export default function InvoicesPage() {
  const now = new Date()
  const [year, setYear] = useState(now.getFullYear())
  const [month, setMonth] = useState(now.getMonth())
  const [invoices, setInvoices] = useState<Invoice[]>([])
  const [loading, setLoading] = useState(false)
  const [available, setAvailable] = useState<boolean | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch(`${TAXHACKER_URL}/api/auth/get-session`, { credentials: 'include' })
      .then(r => setAvailable(r.ok || r.status === 401 || r.status === 200))
      .catch(() => setAvailable(false))
  }, [])

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const dateFrom = `${year}-${String(month + 1).padStart(2, '0')}-01`
      const lastDay = new Date(year, month + 1, 0).getDate()
      const dateTo = `${year}-${String(month + 1).padStart(2, '0')}-${String(lastDay).padStart(2, '0')}`
      const fields = 'name,merchant,total,currencyCode,issuedAt,categoryCode'
      const url = `${TAXHACKER_URL}/export/transactions?fields=${fields}&dateFrom=${dateFrom}&dateTo=${dateTo}`
      const res = await fetch(url, { credentials: 'include' })
      if (!res.ok) { setError('Failed to load invoices'); return }
      setInvoices(parseCSV(await res.text()))
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load invoices')
    } finally {
      setLoading(false)
    }
  }, [year, month])

  useEffect(() => {
    if (available) load()
  }, [available, load])

  function downloadCSV() {
    const dateFrom = `${year}-${String(month + 1).padStart(2, '0')}-01`
    const lastDay = new Date(year, month + 1, 0).getDate()
    const dateTo = `${year}-${String(month + 1).padStart(2, '0')}-${String(lastDay).padStart(2, '0')}`
    window.open(
      `${TAXHACKER_URL}/export/transactions?fields=name,merchant,total,currencyCode,issuedAt,categoryCode&dateFrom=${dateFrom}&dateTo=${dateTo}`,
      '_blank'
    )
  }

  if (available === false) {
    return (
      <div className="space-y-4">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Invoices</h1>
          <p className="text-sm text-gray-500">Upload and manage your invoices via TaxHacker</p>
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

  const totalSpent = invoices.reduce((s, r) => s + r.total, 0)
  const currencies = Array.from(new Set(invoices.map(r => r.currencyCode)))
  const primaryCurrency = currencies[0] || 'EUR'

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Invoices</h1>
          <p className="text-sm text-gray-500">Upload and manage your invoices via TaxHacker</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={load} disabled={loading} className="btn-secondary flex items-center gap-1.5 text-xs">
            <RefreshCw size={12} className={loading ? 'animate-spin' : ''} /> Refresh
          </button>
          <button onClick={downloadCSV} className="btn-secondary flex items-center gap-1.5 text-xs">
            <Download size={12} /> Export CSV
          </button>
          <a
            href={`${TAXHACKER_URL}/import`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 px-3 py-1.5 bg-brand-600 hover:bg-brand-700 text-white text-xs font-semibold rounded-lg transition-colors"
          >
            <Upload size={12} /> Upload Invoices
          </a>
          <a
            href={TAXHACKER_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-secondary flex items-center gap-1.5 text-xs"
          >
            <ExternalLink size={12} /> TaxHacker
          </a>
        </div>
      </div>

      {/* Period selector */}
      <div className="flex items-center gap-3">
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
          {loading ? 'Loading…' : `${invoices.length} invoice${invoices.length !== 1 ? 's' : ''} found`}
        </p>
      </div>

      {error && (
        <div className="flex items-center gap-2 px-4 py-3 bg-red-50 text-red-700 rounded-lg text-sm border border-red-200">
          <AlertCircle size={14} /> {error}
        </div>
      )}

      {/* Summary row */}
      {!loading && invoices.length > 0 && (
        <div className="grid grid-cols-3 gap-4">
          <div className="card p-4 flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-blue-500 flex items-center justify-center flex-shrink-0">
              <FileText size={16} className="text-white" />
            </div>
            <div>
              <p className="text-xs text-gray-500">Invoices</p>
              <p className="text-xl font-bold text-gray-900">{invoices.length}</p>
            </div>
          </div>
          <div className="card p-4 flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-emerald-500 flex items-center justify-center flex-shrink-0">
              <DollarSign size={16} className="text-white" />
            </div>
            <div>
              <p className="text-xs text-gray-500">Total Spend</p>
              <p className="text-xl font-bold text-gray-900">{fmt(totalSpent)} <span className="text-sm font-medium text-gray-400">{primaryCurrency}</span></p>
            </div>
          </div>
          <div className="card p-4 flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-amber-500 flex items-center justify-center flex-shrink-0">
              <Clock size={16} className="text-white" />
            </div>
            <div>
              <p className="text-xs text-gray-500">Period</p>
              <p className="text-sm font-bold text-gray-900">{MONTHS[month]} {year}</p>
            </div>
          </div>
        </div>
      )}

      {/* Invoice table */}
      {loading ? (
        <div className="card overflow-hidden">
          {[1, 2, 3, 4, 5].map(i => (
            <div key={i} className="h-14 border-b border-gray-100 animate-pulse bg-gray-50 last:border-0" />
          ))}
        </div>
      ) : invoices.length === 0 ? (
        <div className="card p-12 text-center space-y-4">
          <FileText size={32} className="mx-auto text-gray-200" />
          <div>
            <p className="text-sm font-semibold text-gray-700">No invoices for {MONTHS[month]} {year}</p>
            <p className="text-xs text-gray-400 mt-1">Upload invoices via TaxHacker to track your spending</p>
          </div>
          <a
            href={`${TAXHACKER_URL}/import`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white text-sm font-semibold rounded-xl transition-colors"
          >
            <Upload size={14} /> Upload in TaxHacker
          </a>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50">
                <th className="text-left px-5 py-3 font-medium text-gray-500 text-xs uppercase tracking-wider">Invoice</th>
                <th className="text-left px-5 py-3 font-medium text-gray-500 text-xs uppercase tracking-wider">Vendor</th>
                <th className="text-left px-5 py-3 font-medium text-gray-500 text-xs uppercase tracking-wider">Category</th>
                <th className="text-left px-5 py-3 font-medium text-gray-500 text-xs uppercase tracking-wider">Date</th>
                <th className="text-right px-5 py-3 font-medium text-gray-500 text-xs uppercase tracking-wider">Amount</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {invoices.map((inv, i) => (
                <tr key={i} className="hover:bg-gray-50 transition-colors">
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-2">
                      <CheckCircle2 size={12} className="text-emerald-400 flex-shrink-0" />
                      <span className="text-sm text-gray-800 truncate max-w-48">{inv.name || '—'}</span>
                    </div>
                  </td>
                  <td className="px-5 py-3 text-gray-600 text-sm">{inv.merchant || '—'}</td>
                  <td className="px-5 py-3">
                    <span className="px-2 py-0.5 rounded-full text-xs bg-gray-100 text-gray-600 capitalize font-medium">
                      {inv.categoryCode.replace(/_/g, ' ')}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-gray-500 text-xs">
                    {inv.issuedAt ? new Date(inv.issuedAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : '—'}
                  </td>
                  <td className="px-5 py-3 text-right font-semibold text-gray-900">
                    {fmt(inv.total)} <span className="text-xs font-normal text-gray-400">{inv.currencyCode}</span>
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot className="border-t bg-gray-50">
              <tr>
                <td colSpan={4} className="px-5 py-3 text-sm font-semibold text-gray-700">Total</td>
                <td className="px-5 py-3 text-right text-sm font-bold text-gray-900">
                  {fmt(totalSpent)} <span className="text-xs font-normal text-gray-400">{primaryCurrency}</span>
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      )}
    </div>
  )
}

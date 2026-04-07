'use client'

import { useEffect, useState, useCallback, useRef } from 'react'
import { Upload, FileText, RefreshCw } from 'lucide-react'
import { apiFetch } from '@/lib/apiFetch'

type Dashboard = {
  income: { total: number; vat_collected: number; net: number; invoice_count: number }
  expenses: { total: number; vat_paid: number; net: number; invoice_count: number }
  profit_loss: {
    gross: number
    net_of_vat: number
    estimated_net_vat_payable: number
    estimated_vat_refundable: number
  }
  categories: Array<{ category: string; direction: string; total: number; cnt: number }>
  disclaimer: string
}

type Invoice = {
  id: string
  vendor_name?: string | null
  file_name?: string | null
  invoice_date?: string | null
  category?: string | null
  direction?: string | null
  total_amount?: number | null
  vat_amount?: number | null
  extraction_status?: string | null
  ai_notes?: string | null
  estimated_tax_impact?: string | null
}

function fmt(n?: number | null) {
  if (n == null) return '—'
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n)
}

export default function FinanceHubPage() {
  const [dash, setDash] = useState<Dashboard | null>(null)
  const [invoices, setInvoices] = useState<Invoice[]>([])
  const [months, setMonths] = useState(3)
  const [loading, setLoading] = useState(true)
  const [uploadMsg, setUploadMsg] = useState<string | null>(null)
  const [selected, setSelected] = useState<Invoice | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [d, i] = await Promise.all([
        apiFetch<Dashboard>(`/api/v1/finance/dashboard?months=${months}`),
        apiFetch<{ invoices: Invoice[] }>('/api/v1/finance/invoices'),
      ])
      setDash(d)
      setInvoices(i.invoices ?? [])
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [months])

  useEffect(() => {
    load()
  }, [load])

  async function handleUpload(file: File) {
    setUploadMsg('Uploading…')
    try {
      const form = new FormData()
      form.append('file', file)
      const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/finance/invoices/upload`,
        {
          method: 'POST',
          headers: token ? { Authorization: `Bearer ${token}` } : {},
          body: form,
        },
      )
      if (!res.ok) throw new Error(`Upload failed (${res.status})`)
      setUploadMsg('Processing — AI extracting fields…')
      setTimeout(() => {
        load()
        setUploadMsg(null)
      }, 5000)
    } catch (e) {
      console.error(e)
      setUploadMsg('Upload failed')
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Finance Intelligence</h1>
          <p className="text-sm text-slate-500 mt-1">
            Upload invoices — local AI extracts fields and estimates Turkish tax impact.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={months}
            onChange={(e) => setMonths(Number(e.target.value))}
            className="px-2 py-2 text-sm border border-slate-300 rounded-lg"
          >
            <option value={1}>1 month</option>
            <option value={3}>3 months</option>
            <option value={6}>6 months</option>
            <option value={12}>12 months</option>
          </select>
          <input
            ref={fileRef}
            type="file"
            accept=".pdf,.png,.jpg,.jpeg"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0]
              if (f) handleUpload(f)
            }}
          />
          <button
            onClick={() => fileRef.current?.click()}
            className="inline-flex items-center gap-2 px-4 py-2 bg-brand-600 text-white text-sm font-medium rounded-lg hover:bg-brand-700"
          >
            <Upload size={14} /> Upload Invoice
          </button>
          <button
            onClick={load}
            className="px-3 py-2 border border-slate-300 rounded-lg hover:bg-slate-50"
            title="Refresh"
          >
            <RefreshCw size={14} />
          </button>
        </div>
      </div>

      <div className="px-4 py-3 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-800">
        ⚠️ {dash?.disclaimer ?? 'Estimates only. Consult your accountant for official tax filing.'}
      </div>

      {uploadMsg && (
        <div className="px-4 py-3 bg-blue-50 border border-blue-200 rounded-lg text-sm text-blue-800">
          {uploadMsg}
        </div>
      )}

      {loading ? (
        <div className="text-sm text-slate-500">Loading…</div>
      ) : (
        <>
          <div className="grid grid-cols-3 gap-4">
            {dash && (
              <>
                <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-5">
                  <div className="text-xs uppercase tracking-wide text-emerald-700">Income</div>
                  <div className="text-2xl font-semibold text-emerald-900 mt-2">
                    {fmt(dash.income.total)}
                  </div>
                  <div className="text-[11px] text-emerald-700 mt-1">
                    VAT: {fmt(dash.income.vat_collected)} · {dash.income.invoice_count} invoices
                  </div>
                </div>
                <div className="bg-red-50 border border-red-200 rounded-xl p-5">
                  <div className="text-xs uppercase tracking-wide text-red-700">Expenses</div>
                  <div className="text-2xl font-semibold text-red-900 mt-2">
                    {fmt(dash.expenses.total)}
                  </div>
                  <div className="text-[11px] text-red-700 mt-1">
                    VAT: {fmt(dash.expenses.vat_paid)} · {dash.expenses.invoice_count} invoices
                  </div>
                </div>
                <div
                  className={`border rounded-xl p-5 ${
                    dash.profit_loss.gross >= 0
                      ? 'bg-emerald-50 border-emerald-200'
                      : 'bg-red-50 border-red-200'
                  }`}
                >
                  <div className="text-xs uppercase tracking-wide text-slate-600">Net Profit</div>
                  <div
                    className={`text-2xl font-semibold mt-2 ${
                      dash.profit_loss.gross >= 0 ? 'text-emerald-900' : 'text-red-900'
                    }`}
                  >
                    {fmt(dash.profit_loss.gross)}
                  </div>
                  <div className="text-[11px] text-slate-600 mt-1">
                    Net of VAT: {fmt(dash.profit_loss.net_of_vat)} · VAT due:{' '}
                    {fmt(dash.profit_loss.estimated_net_vat_payable)}
                  </div>
                </div>
              </>
            )}
          </div>

          {(dash?.categories?.length ?? 0) > 0 && (
            <div className="bg-white border border-slate-200 rounded-xl p-5">
              <h2 className="text-sm font-semibold text-slate-700 mb-3">Category Breakdown</h2>
              <table className="w-full text-sm">
                <thead className="text-xs text-slate-500 uppercase border-b border-slate-200">
                  <tr>
                    <th className="text-left py-2">Category</th>
                    <th className="text-left">Direction</th>
                    <th className="text-right">Total</th>
                    <th className="text-right">Invoices</th>
                  </tr>
                </thead>
                <tbody>
                  {dash!.categories.map((c, i) => (
                    <tr key={i} className="border-b border-slate-100 last:border-0">
                      <td className="py-2 font-medium text-slate-800">{c.category ?? '—'}</td>
                      <td className="text-slate-600">{c.direction}</td>
                      <td className="text-right font-mono text-slate-700">{fmt(c.total)}</td>
                      <td className="text-right text-slate-500">{c.cnt}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div className="bg-white border border-slate-200 rounded-xl p-5">
            <h2 className="text-sm font-semibold text-slate-700 mb-3">Recent Invoices</h2>
            {invoices.length === 0 ? (
              <div className="text-sm text-slate-500 italic">No invoices yet.</div>
            ) : (
              <div className="divide-y divide-slate-100">
                {invoices.map((inv) => (
                  <button
                    key={inv.id}
                    onClick={() => setSelected(inv)}
                    className="w-full flex items-center gap-3 py-3 text-left hover:bg-slate-50 -mx-2 px-2 rounded"
                  >
                    <FileText size={16} className="text-slate-400" />
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium text-slate-800 truncate">
                        {inv.vendor_name ?? inv.file_name ?? 'Unknown'}
                      </div>
                      <div className="text-[11px] text-slate-500">
                        {inv.invoice_date ?? '—'} · {inv.category ?? '—'} ·{' '}
                        {inv.extraction_status}
                      </div>
                    </div>
                    <span
                      className={`text-[11px] px-2 py-0.5 rounded ${
                        inv.direction === 'incoming'
                          ? 'bg-red-50 text-red-700'
                          : 'bg-emerald-50 text-emerald-700'
                      }`}
                    >
                      {inv.direction ?? '—'}
                    </span>
                    <div className="text-right">
                      <div className="text-sm font-mono text-slate-800">
                        {fmt(inv.total_amount)}
                      </div>
                      <div className="text-[10px] text-slate-500">
                        VAT {fmt(inv.vat_amount)}
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </>
      )}

      {selected && (
        <div
          className="fixed inset-0 bg-black/30 flex items-center justify-center z-50 p-4"
          onClick={() => setSelected(null)}
        >
          <div
            className="bg-white rounded-xl max-w-2xl w-full p-6 space-y-4"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between">
              <div>
                <h3 className="text-lg font-semibold text-slate-900">
                  {selected.vendor_name ?? selected.file_name ?? 'Invoice'}
                </h3>
                <div className="text-sm text-slate-500">
                  {selected.invoice_date ?? '—'} · {fmt(selected.total_amount)}
                </div>
              </div>
              <button
                onClick={() => setSelected(null)}
                className="text-slate-400 hover:text-slate-700"
              >
                ✕
              </button>
            </div>
            {selected.estimated_tax_impact && (
              <div className="px-3 py-2 bg-amber-50 border border-amber-200 rounded text-sm text-amber-900">
                {selected.estimated_tax_impact}
              </div>
            )}
            {selected.ai_notes && (
              <div>
                <div className="text-xs uppercase tracking-wide text-slate-500 mb-1">AI Notes</div>
                <pre className="text-sm text-slate-700 whitespace-pre-wrap">
                  {selected.ai_notes}
                </pre>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

'use client'

import { useState, useEffect } from 'react'
import { Handshake, Loader2, AlertCircle, ExternalLink } from 'lucide-react'

const API = '/api/v1/crm'

const STAGE_COLORS: Record<string, string> = {
  NEW: 'bg-blue-100 text-blue-700',
  SCREENING: 'bg-purple-100 text-purple-700',
  MEETING: 'bg-amber-100 text-amber-700',
  PROPOSAL: 'bg-orange-100 text-orange-700',
  CUSTOMER: 'bg-emerald-100 text-emerald-700',
  CLOSING: 'bg-emerald-100 text-emerald-700',
}

interface Deal {
  id: string
  name: string
  amount: number
  currency: string
  stage: string
  close_date: string
  created: string
}

export default function CRMDealsPage() {
  const [deals, setDeals] = useState<Deal[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    fetch(`${API}/opportunities?limit=50`)
      .then(r => r.json())
      .then(d => { setDeals(d.opportunities || []); setTotal(d.total || 0) })
      .catch(() => setError('Could not load deals'))
      .finally(() => setLoading(false))
  }, [])

  const totalValue = deals.reduce((sum, d) => sum + (d.amount || 0), 0)
  const stageBreakdown = deals.reduce<Record<string, number>>((acc, d) => {
    const s = d.stage || 'Unknown'
    acc[s] = (acc[s] || 0) + 1
    return acc
  }, {})

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-emerald-500/10 flex items-center justify-center">
            <Handshake size={20} className="text-emerald-500" />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-slate-900">Deals</h1>
            <p className="text-sm text-slate-500">{total} opportunities in pipeline</p>
          </div>
        </div>
        <a href="http://localhost:3333/objects/opportunities" target="_blank" rel="noopener noreferrer"
          className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition-colors">
          Manage in Twenty <ExternalLink size={11} />
        </a>
      </div>

      {/* Pipeline Summary */}
      {!loading && deals.length > 0 && (
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-white border border-slate-200 rounded-xl p-5">
            <p className="text-xs font-medium text-slate-500 mb-1">Total Pipeline Value</p>
            <p className="text-2xl font-bold text-emerald-600">
              ${totalValue.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
            </p>
          </div>
          <div className="bg-white border border-slate-200 rounded-xl p-5">
            <p className="text-xs font-medium text-slate-500 mb-2">By Stage</p>
            <div className="flex flex-wrap gap-1.5">
              {Object.entries(stageBreakdown).map(([stage, count]) => (
                <span key={stage} className={`text-[10px] px-2 py-0.5 rounded-full font-semibold ${STAGE_COLORS[stage] || 'bg-slate-100 text-slate-600'}`}>
                  {stage} ({count})
                </span>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Deals Table */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
        <div className="px-5 py-3 border-b border-slate-100">
          <h2 className="text-sm font-semibold text-slate-700">Pipeline ({total})</h2>
        </div>
        {loading ? (
          <div className="flex items-center justify-center py-12 text-slate-400"><Loader2 size={18} className="animate-spin" /></div>
        ) : error ? (
          <div className="flex items-center gap-2 p-4 text-red-600 text-sm"><AlertCircle size={14} /> {error}</div>
        ) : deals.length === 0 ? (
          <div className="py-12 text-center space-y-2">
            <p className="text-slate-400 text-sm">No deals yet</p>
            <a href="http://localhost:3333/objects/opportunities" target="_blank" rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-xs text-emerald-600 hover:underline">
              Add deals in Twenty CRM <ExternalLink size={10} />
            </a>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-slate-50">
              <tr>
                {['Deal', 'Amount', 'Stage', 'Close Date', ''].map(h => (
                  <th key={h} className="px-4 py-2.5 text-left text-[11px] font-semibold text-slate-500 uppercase tracking-wide">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {deals.map(d => (
                <tr key={d.id} className="hover:bg-slate-50 transition-colors">
                  <td className="px-4 py-3 font-medium text-slate-800">{d.name}</td>
                  <td className="px-4 py-3 text-slate-700 font-medium">
                    {d.amount ? `$${d.amount.toLocaleString()}` : '—'}
                  </td>
                  <td className="px-4 py-3">
                    {d.stage ? (
                      <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold ${STAGE_COLORS[d.stage] || 'bg-slate-100 text-slate-600'}`}>
                        {d.stage}
                      </span>
                    ) : '—'}
                  </td>
                  <td className="px-4 py-3 text-slate-400 text-xs">
                    {d.close_date ? new Date(d.close_date).toLocaleDateString() : '—'}
                  </td>
                  <td className="px-4 py-3">
                    <a href={`http://localhost:3333/objects/opportunities/${d.id}`} target="_blank" rel="noopener noreferrer"
                      className="flex items-center gap-1 text-xs text-emerald-600 hover:text-emerald-700">
                      View <ExternalLink size={10} />
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

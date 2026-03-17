'use client'
import { useEffect, useState } from 'react'
import { recommendations as recApi } from '@/lib/api'
import type { Recommendation } from '@/lib/api'
import { AlertTriangle, CheckCircle, Info, TrendingUp, Filter } from 'lucide-react'

const DEMO_SITE = '00000000-0000-0000-0003-000000000001'

const SEVERITY_ICON: Record<string, React.ReactNode> = {
  critical: <AlertTriangle size={14} className="text-red-500" />,
  high: <AlertTriangle size={14} className="text-orange-500" />,
  medium: <Info size={14} className="text-yellow-500" />,
  low: <Info size={14} className="text-blue-400" />,
}

const CATEGORY_LABELS: Record<string, string> = {
  technical_seo: 'Technical SEO',
  on_page_seo: 'On-Page SEO',
  content_gap: 'Content Gaps',
  internal_linking: 'Internal Links',
  geo_aeo: 'AI Visibility',
}

function PriorityBar({ score }: { score: number }) {
  const pct = Math.round(score * 100)
  const color = pct >= 80 ? 'bg-red-400' : pct >= 60 ? 'bg-orange-400' : pct >= 40 ? 'bg-yellow-400' : 'bg-blue-400'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-gray-500 w-6 text-right">{pct}</span>
    </div>
  )
}

export default function SEOAuditPage() {
  const [recs, setRecs] = useState<Recommendation[]>([])
  const [loading, setLoading] = useState(true)
  const [category, setCategory] = useState<string>('')
  const [selected, setSelected] = useState<Recommendation | null>(null)

  useEffect(() => {
    recApi.list(DEMO_SITE, { category: category || undefined })
      .then(r => setRecs(r.items))
      .finally(() => setLoading(false))
  }, [category])

  const criticalCount = recs.filter(r => r.impact_score >= 0.8).length
  const highCount = recs.filter(r => r.impact_score >= 0.6 && r.impact_score < 0.8).length

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-bold text-gray-900">SEO Audit</h1>
        <p className="text-sm text-gray-500">Acme SaaS · example-saas.com</p>
      </div>

      {/* Summary bar */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: 'Critical', value: criticalCount, color: 'text-red-600', bg: 'bg-red-50' },
          { label: 'High', value: highCount, color: 'text-orange-600', bg: 'bg-orange-50' },
          { label: 'Total Issues', value: recs.length, color: 'text-gray-700', bg: 'bg-gray-50' },
          { label: 'Health Score', value: '72', suffix: '/100', color: 'text-green-600', bg: 'bg-green-50' },
        ].map(item => (
          <div key={item.label} className={`card p-4 ${item.bg}`}>
            <p className="text-xs text-gray-500 mb-1">{item.label}</p>
            <p className={`text-2xl font-bold ${item.color}`}>
              {item.value}<span className="text-sm font-normal">{(item as any).suffix || ''}</span>
            </p>
          </div>
        ))}
      </div>

      <div className="flex gap-6">
        {/* Left: list */}
        <div className="flex-1 min-w-0">
          {/* Filters */}
          <div className="flex items-center gap-2 mb-4">
            <Filter size={14} className="text-gray-400" />
            <select value={category} onChange={e => { setCategory(e.target.value); setLoading(true) }}
              className="text-sm border border-gray-200 rounded-lg px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-brand-500">
              <option value="">All categories</option>
              {Object.entries(CATEGORY_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </div>

          {loading ? (
            <div className="space-y-3">{[1,2,3,4].map(i => <div key={i} className="h-16 card animate-pulse" />)}</div>
          ) : recs.length === 0 ? (
            <div className="card p-10 text-center">
              <CheckCircle size={32} className="mx-auto text-green-300 mb-2" />
              <p className="text-gray-400 text-sm">No issues found in this category</p>
            </div>
          ) : (
            <div className="space-y-2">
              {recs.map(rec => (
                <button key={rec.id} onClick={() => setSelected(rec)}
                  className={`w-full text-left card p-4 hover:border-brand-300 transition-colors ${selected?.id === rec.id ? 'border-brand-400 bg-brand-50' : ''}`}>
                  <div className="flex items-start gap-3">
                    <div className="mt-0.5">{SEVERITY_ICON[rec.impact_score >= 0.8 ? 'critical' : rec.impact_score >= 0.6 ? 'high' : 'medium']}</div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900">{rec.title}</p>
                      <p className="text-xs text-gray-400 mt-0.5 line-clamp-1">{rec.summary}</p>
                      <div className="mt-2 flex items-center gap-3">
                        <span className="text-xs text-gray-400">Priority:</span>
                        <div className="flex-1"><PriorityBar score={rec.priority_score} /></div>
                      </div>
                    </div>
                    <span className="text-xs badge-gray flex-shrink-0">{CATEGORY_LABELS[rec.category] || rec.category}</span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Right: detail */}
        {selected && (
          <div className="w-80 flex-shrink-0">
            <div className="card p-5 sticky top-20">
              <h3 className="font-semibold text-gray-900 mb-3">{selected.title}</h3>
              <div className="space-y-3 text-sm">
                <div>
                  <p className="text-xs font-medium text-gray-500 uppercase mb-1">Summary</p>
                  <p className="text-gray-700">{selected.summary}</p>
                </div>
                <div>
                  <p className="text-xs font-medium text-gray-500 uppercase mb-1">Rationale</p>
                  <p className="text-gray-600 text-xs">{selected.rationale}</p>
                </div>
                {selected.proposed_action && (
                  <div>
                    <p className="text-xs font-medium text-gray-500 uppercase mb-1">Proposed Action</p>
                    <p className="text-gray-700 text-xs bg-gray-50 p-2 rounded font-mono">{selected.proposed_action}</p>
                  </div>
                )}
                <div className="grid grid-cols-3 gap-2 pt-2 border-t border-gray-100">
                  {[
                    { label: 'Impact', value: selected.impact_score },
                    { label: 'Effort', value: selected.effort_score },
                    { label: 'Confidence', value: selected.confidence_score },
                  ].map(m => (
                    <div key={m.label} className="text-center">
                      <div className="text-lg font-bold text-gray-900">{Math.round(m.value * 10)}</div>
                      <div className="text-xs text-gray-400">{m.label}</div>
                    </div>
                  ))}
                </div>
                {selected.risk_flags.length > 0 && (
                  <div className="bg-yellow-50 border border-yellow-200 rounded p-2">
                    {selected.risk_flags.map((f, i) => (
                      <p key={i} className="text-xs text-yellow-700">{f}</p>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

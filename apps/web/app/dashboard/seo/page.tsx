'use client'

import { useEffect, useState } from 'react'
import { AlertTriangle, CheckCircle, Info, Filter, Loader2 } from 'lucide-react'
import { apiFetch } from '@/lib/apiFetch'

const DEMO_SITE = '00000000-0000-0000-0003-000000000001'

interface Rec {
  id: string
  title: string
  category: string
  summary: string
  rationale: string
  proposed_action: string | null
  impact_score: number
  effort_score: number
  confidence_score: number
  priority_score: number
  risk_flags: string[]
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

function severityIcon(impact: number) {
  if (impact >= 0.8) return <AlertTriangle size={14} className="text-red-500" />
  if (impact >= 0.6) return <AlertTriangle size={14} className="text-orange-500" />
  return <Info size={14} className="text-yellow-500" />
}

export default function SEOAuditPage() {
  const [recs, setRecs] = useState<Rec[]>([])
  const [loading, setLoading] = useState(true)
  const [category, setCategory] = useState('')
  const [selected, setSelected] = useState<Rec | null>(null)
  const [brandName, setBrandName] = useState('')

  useEffect(() => {
    async function load() {
      setLoading(true)
      try {
        const [profileData, recsData] = await Promise.allSettled([
          apiFetch<{ profile?: { brand_name?: string } }>('/api/v1/brand/profile'),
          apiFetch<{ items: Rec[] }>(`/api/v1/recommendations?site_id=${DEMO_SITE}${category ? `&category=${category}` : ''}`),
        ])
        if (profileData.status === 'fulfilled') {
          setBrandName(profileData.value.profile?.brand_name ?? '')
        }
        if (recsData.status === 'fulfilled') {
          setRecs(recsData.value.items ?? [])
        } else {
          setRecs([])
        }
      } catch {
        setRecs([])
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [category])

  const criticalCount = recs.filter(r => r.impact_score >= 0.8).length
  const highCount = recs.filter(r => r.impact_score >= 0.6 && r.impact_score < 0.8).length
  const healthScore = recs.length === 0 ? 100 : Math.max(30, 100 - Math.round(criticalCount * 12 + highCount * 6))

  return (
    <div className="space-y-5">
      <div className="page-header">
        <div>
          <h1 className="page-title">SEO Audit</h1>
          <p className="page-subtitle">
            {brandName ? `${brandName} · ` : ''}Website health and search visibility recommendations
          </p>
        </div>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: 'Critical', value: criticalCount, color: 'text-red-600', bg: 'bg-red-50' },
          { label: 'High Priority', value: highCount, color: 'text-orange-600', bg: 'bg-orange-50' },
          { label: 'Total Issues', value: recs.length, color: 'text-gray-700', bg: 'bg-gray-50' },
          { label: 'Health Score', value: healthScore, suffix: '/100', color: healthScore >= 80 ? 'text-green-600' : 'text-amber-600', bg: healthScore >= 80 ? 'bg-green-50' : 'bg-amber-50' },
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
        {/* List */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-4">
            <Filter size={14} className="text-gray-400" />
            <select value={category} onChange={e => setCategory(e.target.value)}
              className="text-sm border border-gray-200 rounded-lg px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-brand-500">
              <option value="">All categories</option>
              {Object.entries(CATEGORY_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </div>

          {loading ? (
            <div className="flex items-center justify-center h-32">
              <Loader2 size={20} className="animate-spin text-brand-500" />
            </div>
          ) : recs.length === 0 ? (
            <div className="card p-10 text-center">
              <CheckCircle size={32} className="mx-auto text-green-300 mb-2" />
              <p className="text-gray-400 text-sm">No issues found in this category</p>
              <p className="text-gray-300 text-xs mt-1">Add a website in Brand Sites to run a full audit</p>
            </div>
          ) : (
            <div className="space-y-2">
              {recs.map(rec => (
                <button key={rec.id} onClick={() => setSelected(selected?.id === rec.id ? null : rec)}
                  className={`w-full text-left card p-4 hover:border-brand-300 transition-colors ${selected?.id === rec.id ? 'border-brand-400 bg-brand-50' : ''}`}>
                  <div className="flex items-start gap-3">
                    <div className="mt-0.5">{severityIcon(rec.impact_score)}</div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900">{rec.title}</p>
                      <p className="text-xs text-gray-400 mt-0.5 line-clamp-1">{rec.summary}</p>
                      <div className="mt-2 flex items-center gap-3">
                        <span className="text-xs text-gray-400">Priority:</span>
                        <div className="flex-1"><PriorityBar score={rec.priority_score} /></div>
                      </div>
                    </div>
                    <span className="text-xs badge-gray flex-shrink-0">
                      {CATEGORY_LABELS[rec.category] || rec.category}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Detail panel */}
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

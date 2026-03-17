'use client'
import { useEffect, useState } from 'react'
import { content as api } from '@/lib/api'
import type { ContentAsset } from '@/lib/api'
import { FileText, Plus, AlertTriangle, CheckCircle, Clock, Eye } from 'lucide-react'
import Link from 'next/link'

const DEMO_WS = '00000000-0000-0000-0002-000000000001'

const STATUS_CONFIG: Record<string, { label: string; badge: string; icon: React.ReactNode }> = {
  draft: { label: 'Draft', badge: 'badge-gray', icon: <FileText size={12} /> },
  review: { label: 'In Review', badge: 'badge-yellow', icon: <Clock size={12} /> },
  approved: { label: 'Approved', badge: 'badge-green', icon: <CheckCircle size={12} /> },
  published: { label: 'Published', badge: 'badge-blue', icon: <CheckCircle size={12} /> },
}

export default function ContentPage() {
  const [items, setItems] = useState<ContentAsset[]>([])
  const [loading, setLoading] = useState(true)
  const [typeFilter, setTypeFilter] = useState('')

  useEffect(() => {
    api.list(DEMO_WS, { asset_type: typeFilter || undefined })
      .then(r => setItems(r.items))
      .finally(() => setLoading(false))
  }, [typeFilter])

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Content</h1>
          <p className="text-sm text-gray-500">Briefs, drafts, and approved assets</p>
        </div>
        <Link href="/dashboard/content/new" className="btn-primary flex items-center gap-2">
          <Plus size={14} /> New Brief
        </Link>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-2">
        {[
          { label: 'All', value: '' },
          { label: 'Blog', value: 'blog' },
          { label: 'Landing Page', value: 'landing_page' },
          { label: 'Comparison', value: 'comparison_page' },
          { label: 'Social', value: 'social_post' },
        ].map(tab => (
          <button key={tab.value} onClick={() => { setTypeFilter(tab.value); setLoading(true) }}
            className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${typeFilter === tab.value ? 'bg-brand-600 text-white' : 'text-gray-600 hover:bg-gray-100'}`}>
            {tab.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="space-y-3">{[1,2,3].map(i => <div key={i} className="h-20 card animate-pulse" />)}</div>
      ) : items.length === 0 ? (
        <div className="card p-12 text-center">
          <FileText size={36} className="mx-auto text-gray-200 mb-3" />
          <h3 className="font-medium text-gray-900 mb-1">No content yet</h3>
          <p className="text-sm text-gray-400 mb-4">Create a brief to start generating content</p>
          <Link href="/dashboard/content/new" className="btn-primary inline-flex items-center gap-2">
            <Plus size={14} /> Create Brief
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {items.map(item => {
            const statusCfg = STATUS_CONFIG[item.status] || STATUS_CONFIG.draft
            return (
              <div key={item.id} className="card p-5">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={statusCfg.badge + ' flex items-center gap-1'}>
                        {statusCfg.icon}{statusCfg.label}
                      </span>
                      <span className="badge-gray">{item.asset_type.replace('_', ' ')}</span>
                      {item.risk_score > 0.2 && (
                        <span className="badge-yellow flex items-center gap-1">
                          <AlertTriangle size={10} /> Review needed
                        </span>
                      )}
                    </div>
                    <h3 className="font-medium text-gray-900">{item.title}</h3>
                    {item.compliance_flags.length > 0 && (
                      <p className="text-xs text-yellow-700 mt-1">
                        ⚠ {item.compliance_flags[0]}
                        {item.compliance_flags.length > 1 && ` (+${item.compliance_flags.length - 1} more)`}
                      </p>
                    )}
                  </div>
                  <div className="flex gap-2">
                    <button className="btn-secondary text-xs py-1 flex items-center gap-1">
                      <Eye size={12} /> View
                    </button>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

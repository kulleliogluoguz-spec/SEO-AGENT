'use client'
import { useEffect, useState } from 'react'
import { approvals as api } from '@/lib/api'
import type { Approval } from '@/lib/api'
import { CheckCircle, XCircle, Clock, ShieldCheck } from 'lucide-react'

const DEMO_WS = '00000000-0000-0000-0002-000000000001'

const RISK_COLORS: Record<string, string> = {
  low: 'badge-green',
  medium: 'badge-yellow',
  high: 'badge-red',
}

export default function ApprovalsPage() {
  const [items, setItems] = useState<Approval[]>([])
  const [loading, setLoading] = useState(true)
  const [actioning, setActioning] = useState<string | null>(null)

  useEffect(() => {
    api.list(DEMO_WS).then(r => setItems(r.items)).finally(() => setLoading(false))
  }, [])

  async function handleAction(id: string, action: 'approve' | 'reject') {
    setActioning(id)
    try {
      const updated = await api.action(id, action)
      setItems(prev => prev.map(i => i.id === id ? updated : i))
    } catch (e) {
      console.error(e)
    } finally {
      setActioning(null)
    }
  }

  const pending = items.filter(i => i.status === 'pending')
  const actioned = items.filter(i => i.status !== 'pending')

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-bold text-gray-900">Approval Queue</h1>
        <p className="text-sm text-gray-500">Review and approve AI-generated content and actions before execution</p>
      </div>

      {/* Policy note */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-start gap-3">
        <ShieldCheck size={18} className="text-blue-600 flex-shrink-0 mt-0.5" />
        <div className="text-sm text-blue-800">
          <strong>Autonomy Level 1 — Draft Only.</strong> All AI-generated content and actions require explicit
          human approval before any publishing or execution. This ensures quality and policy compliance.
        </div>
      </div>

      {loading ? (
        <div className="space-y-3">{[1,2].map(i => <div key={i} className="h-20 card animate-pulse" />)}</div>
      ) : (
        <>
          {/* Pending */}
          <div>
            <h2 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
              <Clock size={14} className="text-yellow-500" />
              Pending ({pending.length})
            </h2>
            {pending.length === 0 ? (
              <div className="card p-8 text-center">
                <CheckCircle size={28} className="mx-auto text-green-300 mb-2" />
                <p className="text-sm text-gray-400">All caught up! No pending approvals.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {pending.map(item => (
                  <div key={item.id} className="card p-5">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className={RISK_COLORS[item.risk_level] || 'badge-gray'}>
                            {item.risk_level} risk
                          </span>
                          <span className="badge-gray">{item.entity_type.replace('_', ' ')}</span>
                        </div>
                        <h3 className="font-medium text-gray-900">{item.title}</h3>
                        {item.description && (
                          <p className="text-sm text-gray-500 mt-1">{item.description}</p>
                        )}
                        {item.policy_flags.length > 0 && (
                          <div className="mt-2 space-y-1">
                            {item.policy_flags.map((f: unknown, i: number) => (
                              <p key={i} className="text-xs text-yellow-700 bg-yellow-50 px-2 py-1 rounded">{String(f)}</p>
                            ))}
                          </div>
                        )}
                      </div>
                      <div className="flex gap-2 flex-shrink-0">
                        <button
                          onClick={() => handleAction(item.id, 'reject')}
                          disabled={actioning === item.id}
                          className="btn-secondary flex items-center gap-1 text-red-600 border-red-200 hover:bg-red-50"
                        >
                          <XCircle size={14} /> Reject
                        </button>
                        <button
                          onClick={() => handleAction(item.id, 'approve')}
                          disabled={actioning === item.id}
                          className="btn-primary flex items-center gap-1"
                        >
                          <CheckCircle size={14} /> Approve
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Recently actioned */}
          {actioned.length > 0 && (
            <div>
              <h2 className="text-sm font-semibold text-gray-700 mb-3">Recently Actioned</h2>
              <div className="space-y-2">
                {actioned.slice(0, 5).map(item => (
                  <div key={item.id} className="card p-4 opacity-70">
                    <div className="flex items-center gap-3">
                      {item.status === 'approved'
                        ? <CheckCircle size={14} className="text-green-500" />
                        : <XCircle size={14} className="text-red-400" />
                      }
                      <p className="text-sm text-gray-700">{item.title}</p>
                      <span className={`ml-auto text-xs ${item.status === 'approved' ? 'text-green-600' : 'text-red-500'}`}>
                        {item.status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}

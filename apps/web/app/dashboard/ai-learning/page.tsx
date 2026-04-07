'use client'

import { useEffect, useState } from 'react'
import { Brain, RefreshCw } from 'lucide-react'
import { apiFetch } from '@/lib/apiFetch'

type Summary = {
  total_feedback: number
  feedback_by_module: Array<{ module: string; feedback_type: string; cnt: number }>
  learned_preferences: number
  status: 'active' | 'gathering_data'
}

export default function AILearningPage() {
  const [data, setData] = useState<Summary | null>(null)
  const [loading, setLoading] = useState(true)

  async function load() {
    setLoading(true)
    try {
      const d = await apiFetch<Summary>('/api/v1/ai-learning/summary')
      setData(d)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  // Aggregate accept/reject by module
  const moduleStats: Record<string, { accepted: number; rejected: number; modified: number }> = {}
  for (const f of data?.feedback_by_module ?? []) {
    moduleStats[f.module] ??= { accepted: 0, rejected: 0, modified: 0 }
    if (f.feedback_type === 'accepted') moduleStats[f.module].accepted += f.cnt
    else if (f.feedback_type === 'rejected') moduleStats[f.module].rejected += f.cnt
    else moduleStats[f.module].modified += f.cnt
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-brand-100 flex items-center justify-center">
            <Brain className="text-brand-600" size={20} />
          </div>
          <div>
            <h1 className="text-2xl font-semibold text-slate-900">AI Learning System</h1>
            <p className="text-sm text-slate-500 mt-1">
              Tracks how you respond to AI recommendations and improves over time.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`px-2 py-1 text-xs font-semibold rounded ${
              data?.status === 'active'
                ? 'bg-emerald-100 text-emerald-700'
                : 'bg-amber-100 text-amber-700'
            }`}
          >
            {data?.status === 'active' ? 'Active' : 'Gathering Data'}
          </span>
          <button
            onClick={load}
            className="px-3 py-2 border border-slate-300 rounded-lg hover:bg-slate-50"
          >
            <RefreshCw size={14} />
          </button>
        </div>
      </div>

      {loading ? (
        <div className="text-sm text-slate-500">Loading…</div>
      ) : (
        <>
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-white border border-slate-200 rounded-xl p-5">
              <div className="text-xs uppercase tracking-wide text-slate-500">
                Total Feedback Events
              </div>
              <div className="text-2xl font-semibold text-slate-900 mt-2">
                {data?.total_feedback ?? 0}
              </div>
            </div>
            <div className="bg-white border border-slate-200 rounded-xl p-5">
              <div className="text-xs uppercase tracking-wide text-slate-500">
                Learned Preferences
              </div>
              <div className="text-2xl font-semibold text-slate-900 mt-2">
                {data?.learned_preferences ?? 0}
              </div>
            </div>
            <div className="bg-white border border-slate-200 rounded-xl p-5">
              <div className="text-xs uppercase tracking-wide text-slate-500">
                Learning Status
              </div>
              <div className="text-2xl font-semibold text-slate-900 mt-2">
                {data?.status === 'active' ? 'Active' : 'Gathering'}
              </div>
            </div>
          </div>

          <div className="bg-white border border-slate-200 rounded-xl p-5">
            <h2 className="text-sm font-semibold text-slate-700 mb-3">
              Module Breakdown
            </h2>
            {Object.keys(moduleStats).length === 0 ? (
              <div className="text-sm text-slate-500 italic">
                No feedback yet. Accept or reject AI recommendations to start training the system.
              </div>
            ) : (
              <table className="w-full text-sm">
                <thead className="text-xs text-slate-500 uppercase border-b border-slate-200">
                  <tr>
                    <th className="text-left py-2">Module</th>
                    <th className="text-right">Accepted</th>
                    <th className="text-right">Rejected</th>
                    <th className="text-right">Modified</th>
                    <th className="text-left pl-6">Accept Rate</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(moduleStats).map(([mod, s]) => {
                    const total = s.accepted + s.rejected
                    const rate = total > 0 ? Math.round((s.accepted / total) * 100) : 0
                    return (
                      <tr key={mod} className="border-b border-slate-100 last:border-0">
                        <td className="py-3 font-medium text-slate-800">{mod}</td>
                        <td className="text-right text-emerald-700">{s.accepted}</td>
                        <td className="text-right text-red-700">{s.rejected}</td>
                        <td className="text-right text-amber-700">{s.modified}</td>
                        <td className="pl-6 w-48">
                          <div className="flex items-center gap-2">
                            <div className="flex-1 h-2 bg-slate-200 rounded-full overflow-hidden">
                              <div
                                className="h-full bg-emerald-500"
                                style={{ width: `${rate}%` }}
                              />
                            </div>
                            <span className="text-xs text-slate-600 w-10 text-right">
                              {rate}%
                            </span>
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}
    </div>
  )
}

'use client'
import { useEffect, useState } from 'react'
import { reports as api } from '@/lib/api'
import type { Report } from '@/lib/api'
import { BarChart2, Download, Calendar, TrendingUp, TrendingDown } from 'lucide-react'

const DEMO_WS = '00000000-0000-0000-0002-000000000001'

function KPIChip({ label, value, delta }: { label: string; value: unknown; delta?: number }) {
  return (
    <div className="bg-gray-50 rounded-lg p-3">
      <p className="text-xs text-gray-400">{label}</p>
      <p className="text-lg font-bold text-gray-900 mt-0.5">
        {typeof value === 'object' && value !== null ? (value as any).value ?? '-' : String(value ?? '-')}
      </p>
      {delta !== undefined && (
        <p className={`text-xs flex items-center gap-1 mt-0.5 ${delta >= 0 ? 'text-green-600' : 'text-red-500'}`}>
          {delta >= 0 ? <TrendingUp size={10} /> : <TrendingDown size={10} />}
          {delta >= 0 ? '+' : ''}{delta}%
        </p>
      )}
    </div>
  )
}

export default function ReportsPage() {
  const [reportList, setReportList] = useState<Report[]>([])
  const [selected, setSelected] = useState<Report | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.list(DEMO_WS).then(r => {
      setReportList(r.items)
      if (r.items.length > 0) setSelected(r.items[0])
    }).finally(() => setLoading(false))
  }, [])

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Reports</h1>
          <p className="text-sm text-gray-500">Growth summaries, opportunities, and risks</p>
        </div>
      </div>

      <div className="flex gap-6">
        {/* List */}
        <div className="w-72 flex-shrink-0 space-y-2">
          {loading ? (
            <div className="space-y-2">{[1,2].map(i => <div key={i} className="h-16 card animate-pulse" />)}</div>
          ) : reportList.map(report => (
            <button key={report.id} onClick={() => setSelected(report)}
              className={`w-full text-left card p-4 hover:border-brand-300 transition-colors ${selected?.id === report.id ? 'border-brand-400 bg-brand-50' : ''}`}>
              <div className="flex items-center gap-2 mb-1">
                <span className="badge-blue text-xs">{report.report_type}</span>
              </div>
              <p className="text-sm font-medium text-gray-900 truncate">{report.title}</p>
              <p className="text-xs text-gray-400 mt-0.5 flex items-center gap-1">
                <Calendar size={10} />
                {report.period_end ? new Date(report.period_end).toLocaleDateString() : new Date(report.created_at).toLocaleDateString()}
              </p>
            </button>
          ))}
        </div>

        {/* Detail */}
        {selected ? (
          <div className="flex-1 card p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold text-gray-900">{selected.title}</h2>
              <button className="btn-secondary flex items-center gap-1 text-xs">
                <Download size={12} /> Export MD
              </button>
            </div>

            {selected.summary && (
              <div className="bg-gray-50 rounded-lg p-4 mb-5">
                <p className="text-sm text-gray-700">{selected.summary}</p>
              </div>
            )}

            {/* KPIs */}
            {Object.keys(selected.kpis).length > 0 && (
              <div className="mb-5">
                <h3 className="text-sm font-medium text-gray-700 mb-3">KPIs</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {Object.entries(selected.kpis).map(([k, v]) => (
                    <KPIChip key={k} label={k.replace(/_/g, ' ')} value={v}
                      delta={typeof v === 'object' && v !== null ? (v as any).delta : undefined} />
                  ))}
                </div>
              </div>
            )}

            {/* Sections */}
            {(selected as any).sections?.length > 0 && (
              <div className="space-y-4">
                {(selected as any).sections.map((s: any, i: number) => (
                  <div key={i}>
                    <h3 className="text-sm font-semibold text-gray-800 mb-1">{s.title}</h3>
                    <p className="text-sm text-gray-600">{s.content}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : (
          <div className="flex-1 card p-12 text-center">
            <BarChart2 size={36} className="mx-auto text-gray-200 mb-3" />
            <p className="text-gray-400 text-sm">Select a report to view details</p>
          </div>
        )}
      </div>
    </div>
  )
}

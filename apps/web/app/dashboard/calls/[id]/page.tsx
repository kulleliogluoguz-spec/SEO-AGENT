'use client'

import { useEffect, useState, useCallback } from 'react'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import { ArrowLeft, RefreshCw } from 'lucide-react'
import { apiFetch } from '@/lib/apiFetch'

type Segment = {
  id: string
  speaker?: string | null
  text: string
  start_time?: number | null
  end_time?: number | null
  confidence?: number | null
}

type Analysis = {
  qualification_score?: number
  qualification_category?: string
  intent?: string
  urgency?: string
  objections?: string[]
  buying_signals?: string[]
  key_points?: string[]
  summary?: string
  next_action?: string
  overall_sentiment?: string
}

const CAT_COLORS: Record<string, string> = {
  hot: 'bg-red-100 text-red-700',
  warm: 'bg-orange-100 text-orange-700',
  cold: 'bg-blue-100 text-blue-700',
  nurture: 'bg-gray-100 text-gray-600',
  disqualified: 'bg-slate-100 text-slate-500',
}

function formatTime(s?: number | null) {
  if (s == null) return '00:00'
  const m = Math.floor(s / 60)
  const r = Math.floor(s % 60)
  return `${m.toString().padStart(2, '0')}:${r.toString().padStart(2, '0')}`
}

export default function TranscriptViewerPage() {
  const params = useParams<{ id: string }>()
  const callId = params?.id
  const [segments, setSegments] = useState<Segment[]>([])
  const [analysis, setAnalysis] = useState<Analysis>({})
  const [loading, setLoading] = useState(true)
  const [reanalyzing, setReanalyzing] = useState(false)

  const load = useCallback(async () => {
    if (!callId) return
    setLoading(true)
    try {
      const data = await apiFetch<{ segments: Segment[]; analysis: Analysis }>(
        `/api/v1/calling/${callId}/transcript`,
      )
      setSegments(data.segments ?? [])
      setAnalysis(data.analysis ?? {})
    } finally {
      setLoading(false)
    }
  }, [callId])

  useEffect(() => {
    load()
  }, [load])

  async function reanalyze() {
    if (!callId) return
    setReanalyzing(true)
    try {
      await apiFetch(`/api/v1/calling/${callId}/reanalyze`, { method: 'POST' })
      await load()
    } finally {
      setReanalyzing(false)
    }
  }

  const score = analysis.qualification_score ?? 0
  const cat = (analysis.qualification_category ?? 'nurture').toLowerCase()

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <Link
          href="/dashboard/calling"
          className="inline-flex items-center gap-2 text-sm text-slate-500 hover:text-slate-800"
        >
          <ArrowLeft size={14} /> Back to Call Hub
        </Link>
        <button
          onClick={reanalyze}
          disabled={reanalyzing}
          className="inline-flex items-center gap-2 px-3 py-1.5 text-xs border border-slate-300 rounded-lg hover:bg-slate-50 disabled:opacity-50"
        >
          <RefreshCw size={12} className={reanalyzing ? 'animate-spin' : ''} />
          Re-analyze
        </button>
      </div>

      {loading ? (
        <div className="text-sm text-slate-500">Loading transcript…</div>
      ) : segments.length === 0 ? (
        <div className="px-4 py-6 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-800">
          Transcript pending — processing in background. Refresh in a moment.
        </div>
      ) : (
        <div className="grid grid-cols-5 gap-6">
          <div className="col-span-3 bg-white border border-slate-200 rounded-xl p-4 max-h-[70vh] overflow-y-auto space-y-3">
            {segments.map((s) => {
              const speakerColor =
                (s.speaker ?? '').includes('1') || (s.speaker ?? '').includes('B')
                  ? 'bg-emerald-100 text-emerald-700'
                  : 'bg-blue-100 text-blue-700'
              return (
                <div key={s.id} className="flex gap-3">
                  <div className="flex-shrink-0 text-[10px] font-mono text-slate-400 w-12 mt-1">
                    [{formatTime(s.start_time)}]
                  </div>
                  <div className="flex-1">
                    <span className={`text-[10px] px-1.5 py-0.5 rounded font-semibold ${speakerColor}`}>
                      {s.speaker ?? 'SPK'}
                    </span>
                    <p className="text-sm text-slate-800 mt-1 leading-relaxed">{s.text}</p>
                  </div>
                </div>
              )
            })}
          </div>

          <div className="col-span-2 bg-white border border-slate-200 rounded-xl p-4 space-y-4">
            <div>
              <div className="text-xs uppercase tracking-wide text-slate-500">AI Analysis</div>
              <div className="flex items-center gap-3 mt-2">
                <div className="w-16 h-16 rounded-full border-4 border-brand-500 flex items-center justify-center">
                  <span className="text-xl font-semibold text-slate-900">{score}</span>
                </div>
                <div>
                  <div
                    className={`px-2 py-0.5 text-[11px] font-semibold rounded inline-block ${
                      CAT_COLORS[cat] ?? CAT_COLORS.nurture
                    }`}
                  >
                    {cat}
                  </div>
                  <div className="text-xs text-slate-500 mt-1">
                    {analysis.intent ?? '—'} · {analysis.urgency ?? '—'}
                  </div>
                </div>
              </div>
            </div>

            {analysis.summary && (
              <div>
                <div className="text-xs font-semibold text-slate-700 mb-1">Summary</div>
                <p className="text-sm text-slate-700">{analysis.summary}</p>
              </div>
            )}

            {analysis.next_action && (
              <div className="px-3 py-2 bg-emerald-50 border border-emerald-200 rounded-lg">
                <div className="text-[11px] font-semibold text-emerald-700 uppercase tracking-wide">
                  Next Action
                </div>
                <div className="text-sm text-emerald-900 mt-0.5">{analysis.next_action}</div>
              </div>
            )}

            {(analysis.objections?.length ?? 0) > 0 && (
              <div>
                <div className="text-xs font-semibold text-slate-700 mb-1">Objections</div>
                <div className="flex flex-wrap gap-1">
                  {analysis.objections!.map((o, i) => (
                    <span key={i} className="text-[11px] px-2 py-0.5 rounded bg-red-50 text-red-700">
                      {o}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {(analysis.buying_signals?.length ?? 0) > 0 && (
              <div>
                <div className="text-xs font-semibold text-slate-700 mb-1">Buying Signals</div>
                <div className="flex flex-wrap gap-1">
                  {analysis.buying_signals!.map((b, i) => (
                    <span
                      key={i}
                      className="text-[11px] px-2 py-0.5 rounded bg-emerald-50 text-emerald-700"
                    >
                      {b}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {(analysis.key_points?.length ?? 0) > 0 && (
              <div>
                <div className="text-xs font-semibold text-slate-700 mb-1">Key Points</div>
                <ul className="text-sm text-slate-700 list-disc list-inside space-y-0.5">
                  {analysis.key_points!.map((k, i) => (
                    <li key={i}>{k}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

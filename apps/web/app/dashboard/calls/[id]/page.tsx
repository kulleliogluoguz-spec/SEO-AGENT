'use client'

import { useEffect, useState, useCallback } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import {
  ArrowLeft, RefreshCw, Phone, Building2, Calendar,
  Clock, TrendingUp, MessageSquare, AlertCircle,
  CheckSquare, Star, ThumbsUp, ChevronUp, ChevronDown
} from 'lucide-react'

const API = 'http://localhost:8000'

interface Analysis {
  customer_name?: string
  customer_phone?: string
  company_name?: string
  call_summary?: string
  customer_intent?: string
  key_requests?: string[]
  objections?: string[]
  sentiment?: string
  sales_potential?: string
  sales_score?: number
  sales_reasoning?: string
  follow_up_recommended?: boolean
  follow_up_actions?: string[]
  rep_score?: number
  rep_strengths?: string[]
  rep_improvements?: string[]
  keywords?: string[]
}

interface Call {
  id: string
  type: string
  phone_number?: string
  rep_name?: string
  status: string
  created_at: string
  completed_at?: string
  duration?: number
  transcript?: string
  analysis?: Analysis
  error?: string
}

const POTENTIAL_COLOR: Record<string, string> = {
  hot:           'text-red-600 bg-red-50 border-red-200',
  warm:          'text-amber-600 bg-amber-50 border-amber-200',
  cold:          'text-blue-600 bg-blue-50 border-blue-200',
  not_interested:'text-gray-600 bg-gray-50 border-gray-200',
}
const POTENTIAL_LABEL: Record<string, string> = {
  hot: '🔥 Hot Lead', warm: '⚡ Warm Lead', cold: '❄️ Cold Lead', not_interested: '✗ Not Interested'
}

function ScoreGauge({ score, label }: { score: number; label: string }) {
  const color = score >= 80 ? '#22c55e' : score >= 50 ? '#f59e0b' : '#ef4444'
  return (
    <div className="text-center">
      <div className="relative w-24 h-24 mx-auto">
        <svg viewBox="0 0 36 36" className="w-24 h-24 -rotate-90">
          <circle cx="18" cy="18" r="15.9" fill="none" stroke="#e5e7eb" strokeWidth="3" />
          <circle
            cx="18" cy="18" r="15.9" fill="none" stroke={color} strokeWidth="3"
            strokeDasharray={`${score} 100`} strokeLinecap="round"
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center flex-col">
          <span className="text-xl font-bold text-gray-900">{score}</span>
          <span className="text-[10px] text-gray-400">/100</span>
        </div>
      </div>
      <p className="text-xs text-gray-500 mt-1">{label}</p>
    </div>
  )
}

export default function CallDetailPage() {
  const params = useParams()
  const id = params.id as string
  const [call, setCall] = useState<Call | null>(null)
  const [loading, setLoading] = useState(true)
  const [reanalyzing, setReanalyzing] = useState(false)
  const [showTranscript, setShowTranscript] = useState(false)

  const load = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/v1/calls/${id}`)
      if (r.ok) setCall(await r.json())
      else setCall(null)
    } catch {}
    setLoading(false)
  }, [id])

  useEffect(() => { load() }, [load])

  // Auto-poll while call is being processed
  useEffect(() => {
    if (!call) return
    const inProgress = ['queued', 'transcribing', 'analyzing'].includes(call.status)
    if (!inProgress) return
    const t = setInterval(load, 4000)
    return () => clearInterval(t)
  }, [call?.status, load])

  async function reanalyze() {
    setReanalyzing(true)
    // Optimistically show queued status immediately
    setCall(prev => prev ? { ...prev, status: 'queued' } : prev)
    try {
      await fetch(`${API}/api/v1/calls/${id}/reanalyze`, { method: 'POST' })
      await load()
    } catch {}
    setReanalyzing(false)
  }

  function fmt(iso: string) {
    return new Date(iso).toLocaleString('en-US', {
      month: 'short', day: 'numeric', year: 'numeric',
      hour: '2-digit', minute: '2-digit'
    })
  }

  if (loading) return <div className="p-8 text-gray-400 text-sm">Loading…</div>
  if (!call) return <div className="p-8 text-red-500 text-sm">Call not found.</div>

  const a = call.analysis

  return (
    <div className="max-w-3xl space-y-5">
      {/* Back + header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <Link href="/dashboard/calls" className="text-gray-400 hover:text-gray-600">
            <ArrowLeft size={18} />
          </Link>
          <div>
            <h1 className="text-xl font-bold text-gray-900">
              {a?.customer_name || 'Unknown Customer'}
            </h1>
            <div className="flex items-center gap-3 mt-0.5 text-xs text-gray-500">
              {call.phone_number && <span className="flex items-center gap-1"><Phone size={11} />{call.phone_number}</span>}
              {a?.company_name && a.company_name !== 'Unknown' && <span className="flex items-center gap-1"><Building2 size={11} />{a.company_name}</span>}
              <span className="flex items-center gap-1"><Calendar size={11} />{fmt(call.created_at)}</span>
              {call.duration && <span className="flex items-center gap-1"><Clock size={11} />{Math.floor(call.duration / 60)}:{String(call.duration % 60).padStart(2, '0')}</span>}
            </div>
          </div>
        </div>
        <button
          onClick={reanalyze}
          disabled={reanalyzing}
          className="flex items-center gap-1.5 text-xs px-3 py-1.5 border rounded-lg hover:bg-gray-50 text-gray-600 disabled:opacity-50"
        >
          <RefreshCw size={12} className={reanalyzing ? 'animate-spin' : ''} />
          Re-analyze
        </button>
      </div>

      {call.status !== 'completed' && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-sm text-amber-700">
          Status: <strong>{call.status}</strong>
          {call.error && <span className="ml-2 text-red-600">— {call.error}</span>}
        </div>
      )}

      {a && (
        <>
          {/* Sales assessment */}
          <div className="bg-white rounded-xl border p-5">
            <h2 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
              <TrendingUp size={14} className="text-gray-400" /> Sales Assessment
            </h2>
            <div className="flex items-center gap-8">
              <ScoreGauge score={a.sales_score ?? 0} label="Sales Score" />
              {a.rep_score != null && <ScoreGauge score={a.rep_score} label="Rep Score" />}
              <div className="flex-1 space-y-3">
                {a.sales_potential && (
                  <div className={`inline-flex items-center text-sm font-semibold px-3 py-1.5 rounded-lg border ${POTENTIAL_COLOR[a.sales_potential] ?? ''}`}>
                    {POTENTIAL_LABEL[a.sales_potential] ?? a.sales_potential}
                  </div>
                )}
                {a.sales_reasoning && (
                  <p className="text-xs text-gray-600 leading-relaxed">{a.sales_reasoning}</p>
                )}
                {a.sentiment && (
                  <div className="text-xs text-gray-500">
                    Sentiment: <span className="font-medium capitalize text-gray-700">{a.sentiment}</span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* AI Analysis */}
          <div className="bg-white rounded-xl border p-5">
            <h2 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
              <MessageSquare size={14} className="text-gray-400" /> AI Analysis
            </h2>
            <div className="space-y-4">
              {a.call_summary && (
                <div>
                  <p className="text-xs font-medium text-gray-500 mb-1">Summary</p>
                  <p className="text-sm text-gray-700 leading-relaxed">{a.call_summary}</p>
                </div>
              )}
              {a.customer_intent && (
                <div>
                  <p className="text-xs font-medium text-gray-500 mb-1">Customer Intent</p>
                  <p className="text-sm text-gray-700">{a.customer_intent}</p>
                </div>
              )}
              {(a.key_requests?.length ?? 0) > 0 && (
                <div>
                  <p className="text-xs font-medium text-gray-500 mb-1">Key Requests</p>
                  <ul className="space-y-0.5">
                    {a.key_requests!.map((r, i) => (
                      <li key={i} className="text-sm text-gray-700 flex items-start gap-1.5">
                        <span className="text-blue-400 mt-0.5">•</span>{r}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {(a.objections?.length ?? 0) > 0 && (
                <div>
                  <p className="text-xs font-medium text-gray-500 mb-1 flex items-center gap-1">
                    <AlertCircle size={11} className="text-amber-400" /> Objections
                  </p>
                  <ul className="space-y-0.5">
                    {a.objections!.map((o, i) => (
                      <li key={i} className="text-sm text-gray-700 flex items-start gap-1.5">
                        <span className="text-amber-400 mt-0.5">•</span>{o}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {(a.keywords?.length ?? 0) > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {a.keywords!.map(k => (
                    <span key={k} className="text-xs px-2 py-0.5 bg-gray-100 text-gray-600 rounded-full">{k}</span>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Follow-up actions */}
          {(a.follow_up_actions?.length ?? 0) > 0 && (
            <div className="bg-white rounded-xl border p-5">
              <h2 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
                <CheckSquare size={14} className="text-gray-400" /> Recommended Follow-up
              </h2>
              <ul className="space-y-2">
                {a.follow_up_actions!.map((action, i) => (
                  <li key={i} className="flex items-start gap-2.5">
                    <div className="w-4 h-4 rounded border border-gray-300 flex-shrink-0 mt-0.5" />
                    <span className="text-sm text-gray-700">{action}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Rep performance */}
          {((a.rep_strengths?.length ?? 0) > 0 || (a.rep_improvements?.length ?? 0) > 0) && (
            <div className="bg-white rounded-xl border p-5">
              <h2 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
                <Star size={14} className="text-gray-400" /> Rep Performance
              </h2>
              <div className="grid grid-cols-2 gap-4">
                {(a.rep_strengths?.length ?? 0) > 0 && (
                  <div>
                    <p className="text-xs font-medium text-green-600 mb-2 flex items-center gap-1">
                      <ThumbsUp size={11} /> Strengths
                    </p>
                    <ul className="space-y-1">
                      {a.rep_strengths!.map((s, i) => (
                        <li key={i} className="text-xs text-gray-600 flex items-start gap-1.5">
                          <span className="text-green-400">+</span>{s}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {(a.rep_improvements?.length ?? 0) > 0 && (
                  <div>
                    <p className="text-xs font-medium text-amber-600 mb-2 flex items-center gap-1">
                      <TrendingUp size={11} /> Areas to Improve
                    </p>
                    <ul className="space-y-1">
                      {a.rep_improvements!.map((s, i) => (
                        <li key={i} className="text-xs text-gray-600 flex items-start gap-1.5">
                          <span className="text-amber-400">→</span>{s}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          )}
        </>
      )}

      {/* Transcript */}
      {call.transcript && (
        <div className="bg-white rounded-xl border overflow-hidden">
          <button
            onClick={() => setShowTranscript(v => !v)}
            className="w-full px-5 py-3.5 flex items-center justify-between text-sm font-semibold text-gray-700 hover:bg-gray-50 transition-colors"
          >
            <span className="flex items-center gap-2"><MessageSquare size={14} className="text-gray-400" /> Full Transcript</span>
            {showTranscript ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
          {showTranscript && (
            <div className="border-t px-5 py-4">
              <pre className="text-xs text-gray-600 leading-relaxed whitespace-pre-wrap font-sans max-h-80 overflow-y-auto">
                {call.transcript}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

'use client'

import { useEffect, useState, useCallback, useRef } from 'react'
import Link from 'next/link'
import { Phone, Upload, Flame, Snowflake, UserPlus, RefreshCw, CheckCircle2, XCircle } from 'lucide-react'
import { apiFetch } from '@/lib/apiFetch'

type Lead = {
  id: string
  full_name?: string | null
  company_name?: string | null
  email?: string | null
  phone?: string | null
  qualification_score?: number | null
  category?: string | null
  ai_next_action?: string | null
  status?: string | null
  total_calls?: number | null
}

type Call = {
  id: string
  full_name?: string | null
  company_name?: string | null
  status?: string | null
  started_at?: string | null
  duration_seconds?: number | null
  qualification_score?: number | null
  qualification_category?: string | null
  transcription_status?: string | null
  intent?: string | null
}

const CATEGORY_STYLE: Record<string, string> = {
  hot: 'bg-red-100 text-red-700 border border-red-200',
  warm: 'bg-orange-100 text-orange-700 border border-orange-200',
  cold: 'bg-blue-100 text-blue-700 border border-blue-200',
  nurture: 'bg-gray-100 text-gray-600 border border-gray-200',
  disqualified: 'bg-slate-100 text-slate-500 border border-slate-200',
}

function formatDuration(s?: number | null) {
  if (!s) return '—'
  const m = Math.floor(s / 60)
  const r = s % 60
  return `${m}:${r.toString().padStart(2, '0')}`
}

export default function CallingHubPage() {
  const [leads, setLeads] = useState<Lead[]>([])
  const [calls, setCalls] = useState<Call[]>([])
  const [tab, setTab] = useState<'leads' | 'calls'>('leads')
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [uploadMsg, setUploadMsg] = useState<string | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [l, c] = await Promise.all([
        apiFetch<{ leads: Lead[] }>('/api/v1/calling/leads'),
        apiFetch<{ calls: Call[] }>('/api/v1/calling'),
      ])
      setLeads(l.leads ?? [])
      setCalls(c.calls ?? [])
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  async function handleUpload(file: File) {
    setUploading(true)
    setUploadMsg('Uploading recording…')
    try {
      const form = new FormData()
      form.append('file', file)
      const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/calling/upload`,
        {
          method: 'POST',
          headers: token ? { Authorization: `Bearer ${token}` } : {},
          body: form,
        },
      )
      if (!res.ok) throw new Error(`Upload failed (${res.status})`)
      setUploadMsg('AI analyzing…')
      setTimeout(() => {
        load()
        setUploading(false)
        setUploadMsg(null)
      }, 3000)
    } catch (e) {
      console.error(e)
      setUploadMsg('Upload failed')
      setUploading(false)
    }
  }

  const stats = {
    totalLeads: leads.length,
    hotLeads: leads.filter((l) => l.category === 'hot').length,
    totalCalls: calls.length,
    avgScore:
      leads.length > 0
        ? Math.round(
            leads.reduce((s, l) => s + (l.qualification_score ?? 0), 0) / leads.length,
          )
        : 0,
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Call Hub</h1>
          <p className="text-sm text-slate-500 mt-1">
            Phase 2 calling engine — upload recordings to auto-transcribe and qualify leads.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <input
            ref={fileRef}
            type="file"
            accept=".wav,.mp3,.m4a,.ogg,.webm"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0]
              if (f) handleUpload(f)
            }}
          />
          <button
            onClick={() => fileRef.current?.click()}
            disabled={uploading}
            className="inline-flex items-center gap-2 px-4 py-2 bg-brand-600 text-white text-sm font-medium rounded-lg hover:bg-brand-700 disabled:opacity-50"
          >
            <Upload size={14} /> Upload Recording
          </button>
          <Link
            href="/dashboard/calling/new-contact"
            className="inline-flex items-center gap-2 px-4 py-2 border border-slate-300 text-sm font-medium rounded-lg hover:bg-slate-50"
          >
            <UserPlus size={14} /> Add Contact
          </Link>
        </div>
      </div>

      {uploadMsg && (
        <div className="px-4 py-3 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-800">
          {uploadMsg}
        </div>
      )}

      {/* Stat cards */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: 'Total Leads', value: stats.totalLeads, icon: Phone, color: 'text-slate-600' },
          { label: 'Hot Leads', value: stats.hotLeads, icon: Flame, color: 'text-red-500' },
          { label: 'Total Calls', value: stats.totalCalls, icon: Phone, color: 'text-blue-500' },
          { label: 'Avg Score', value: stats.avgScore, icon: CheckCircle2, color: 'text-emerald-500' },
        ].map((s) => {
          const Icon = s.icon
          return (
            <div
              key={s.label}
              className="bg-white border border-slate-200 rounded-xl p-4 flex items-center justify-between"
            >
              <div>
                <div className="text-xs uppercase tracking-wide text-slate-500">{s.label}</div>
                <div className="text-2xl font-semibold text-slate-900 mt-1">{s.value}</div>
              </div>
              <Icon className={s.color} size={22} />
            </div>
          )
        })}
      </div>

      {/* Tab switcher */}
      <div className="flex gap-2 border-b border-slate-200">
        {(['leads', 'calls'] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
              tab === t
                ? 'border-brand-600 text-brand-700'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            {t === 'leads' ? 'Lead Inbox' : 'Call History'}
          </button>
        ))}
        <button
          onClick={load}
          className="ml-auto px-3 py-2 text-xs text-slate-500 hover:text-slate-800 inline-flex items-center gap-1"
        >
          <RefreshCw size={12} /> Refresh
        </button>
      </div>

      {loading ? (
        <div className="text-sm text-slate-500">Loading…</div>
      ) : tab === 'leads' ? (
        <div className="space-y-2">
          {leads.length === 0 && (
            <div className="text-sm text-slate-500 italic px-4 py-6 bg-slate-50 rounded-lg border border-dashed border-slate-300">
              No leads yet. Upload a call recording or add a contact to get started.
            </div>
          )}
          {leads.map((l) => {
            const cat = (l.category ?? 'nurture').toLowerCase()
            return (
              <Link
                key={l.id}
                href={`/dashboard/calling/leads/${l.id}`}
                className="flex items-center gap-4 p-4 bg-white border border-slate-200 rounded-xl hover:border-brand-300 transition-colors"
              >
                <div className="w-10 h-10 rounded-full bg-brand-100 flex items-center justify-center text-brand-700 font-semibold">
                  {(l.full_name ?? '?').slice(0, 1).toUpperCase()}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-semibold text-slate-900 truncate">
                    {l.full_name ?? 'Unnamed'}
                  </div>
                  <div className="text-xs text-slate-500 truncate">
                    {l.company_name ?? '—'} · {l.email ?? l.phone ?? '—'}
                  </div>
                  {l.ai_next_action && (
                    <div className="text-[11px] text-slate-600 mt-1 truncate">
                      Next: {l.ai_next_action}
                    </div>
                  )}
                </div>
                <span
                  className={`px-2 py-0.5 text-[11px] font-semibold rounded ${
                    CATEGORY_STYLE[cat] ?? CATEGORY_STYLE.nurture
                  }`}
                >
                  {cat}
                </span>
                <div className="text-right">
                  <div className="text-lg font-semibold text-slate-900">
                    {l.qualification_score ?? 0}
                  </div>
                  <div className="text-[10px] text-slate-400 uppercase tracking-wide">score</div>
                </div>
              </Link>
            )
          })}
        </div>
      ) : (
        <div className="space-y-2">
          {calls.length === 0 && (
            <div className="text-sm text-slate-500 italic px-4 py-6 bg-slate-50 rounded-lg border border-dashed border-slate-300">
              No calls yet.
            </div>
          )}
          {calls.map((c) => {
            const ok = c.status === 'completed'
            return (
              <Link
                key={c.id}
                href={`/dashboard/calling/${c.id}`}
                className="flex items-center gap-4 p-4 bg-white border border-slate-200 rounded-xl hover:border-brand-300"
              >
                {ok ? (
                  <CheckCircle2 size={18} className="text-emerald-500" />
                ) : (
                  <XCircle size={18} className="text-slate-400" />
                )}
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-semibold text-slate-900 truncate">
                    {c.full_name ?? 'Unknown caller'} · {c.company_name ?? ''}
                  </div>
                  <div className="text-xs text-slate-500">
                    {c.started_at ? new Date(c.started_at).toLocaleString() : '—'} ·{' '}
                    {formatDuration(c.duration_seconds)}
                  </div>
                </div>
                <span className="text-[11px] text-slate-500 px-2 py-0.5 rounded bg-slate-100">
                  {c.transcription_status ?? 'pending'}
                </span>
                <div className="w-12 text-right">
                  <div className="text-base font-semibold text-slate-900">
                    {c.qualification_score ?? '—'}
                  </div>
                </div>
              </Link>
            )
          })}
        </div>
      )}
    </div>
  )
}

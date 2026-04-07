'use client'

import { useEffect, useState, useCallback } from 'react'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import { ArrowLeft, Mail } from 'lucide-react'
import { apiFetch } from '@/lib/apiFetch'

type TimelineItem = {
  id: string
  event_type?: string | null
  title?: string | null
  description?: string | null
  created_at?: string | null
}

type LeadProfile = {
  id: string
  full_name?: string | null
  company_name?: string | null
  email?: string | null
  phone?: string | null
  industry?: string | null
  status?: string | null
  category?: string | null
  qualification_score?: number | null
  ai_summary?: string | null
  ai_intent?: string | null
  ai_urgency?: string | null
  ai_next_action?: string | null
  ai_objections?: string[] | null
  notes?: string | null
  timeline?: TimelineItem[]
  call_stats?: { cnt?: number; avg_dur?: number; last?: string | null }
}

const STATUSES = ['new', 'contacted', 'qualified', 'warm', 'hot', 'cold', 'disqualified']

const CAT_COLORS: Record<string, string> = {
  hot: 'bg-red-100 text-red-700',
  warm: 'bg-orange-100 text-orange-700',
  cold: 'bg-blue-100 text-blue-700',
  nurture: 'bg-gray-100 text-gray-600',
  disqualified: 'bg-slate-100 text-slate-500',
}

export default function LeadProfilePage() {
  const params = useParams<{ id: string }>()
  const id = params?.id
  const [lead, setLead] = useState<LeadProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const [draft, setDraft] = useState<{ subject: string; body: string } | null>(null)
  const [draftLoading, setDraftLoading] = useState(false)

  const load = useCallback(async () => {
    if (!id) return
    setLoading(true)
    try {
      const data = await apiFetch<{ lead: LeadProfile }>(`/api/v1/calling/leads/${id}`)
      setLead(data.lead)
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    load()
  }, [load])

  async function updateStatus(status: string) {
    if (!id) return
    await apiFetch(`/api/v1/calling/leads/${id}`, {
      method: 'PUT',
      body: JSON.stringify({ status }),
    })
    load()
  }

  async function generateDraft() {
    if (!id) return
    setDraftLoading(true)
    try {
      const d = await apiFetch<{ subject: string; body: string }>(
        `/api/v1/email-bridge/draft/${id}`,
        { method: 'POST', body: JSON.stringify({ purpose: 'follow_up' }), timeoutMs: 120000 },
      )
      setDraft(d)
    } catch (e) {
      console.error(e)
    } finally {
      setDraftLoading(false)
    }
  }

  if (loading) return <div className="text-sm text-slate-500">Loading lead…</div>
  if (!lead) return <div className="text-sm text-slate-500">Lead not found.</div>

  const cat = (lead.category ?? 'nurture').toLowerCase()

  return (
    <div className="space-y-6">
      <Link
        href="/dashboard/calling"
        className="inline-flex items-center gap-2 text-sm text-slate-500 hover:text-slate-800"
      >
        <ArrowLeft size={14} /> Back to Call Hub
      </Link>

      <div className="bg-white border border-slate-200 rounded-xl p-6 flex items-center gap-6">
        <div className="w-20 h-20 rounded-full bg-brand-100 flex items-center justify-center text-brand-700 text-3xl font-semibold">
          {(lead.full_name ?? '?').slice(0, 1).toUpperCase()}
        </div>
        <div className="flex-1">
          <h1 className="text-2xl font-semibold text-slate-900">{lead.full_name ?? 'Unnamed'}</h1>
          <div className="text-sm text-slate-500">{lead.company_name ?? '—'}</div>
          <div className="text-xs text-slate-500 mt-1">
            {lead.email ?? '—'} · {lead.phone ?? '—'} · {lead.industry ?? '—'}
          </div>
        </div>
        <div className="text-right">
          <div className="w-20 h-20 rounded-full border-4 border-brand-500 flex items-center justify-center">
            <span className="text-2xl font-semibold text-slate-900">
              {lead.qualification_score ?? 0}
            </span>
          </div>
          <div
            className={`mt-2 px-2 py-0.5 text-[11px] font-semibold rounded inline-block ${
              CAT_COLORS[cat] ?? CAT_COLORS.nurture
            }`}
          >
            {cat}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="col-span-2 bg-white border border-slate-200 rounded-xl p-5 space-y-4">
          <div>
            <div className="text-xs uppercase tracking-wide text-slate-500">Qualification</div>
            <div className="flex flex-wrap gap-2 mt-2 text-xs">
              {lead.ai_intent && (
                <span className="px-2 py-0.5 rounded bg-blue-50 text-blue-700">
                  intent: {lead.ai_intent}
                </span>
              )}
              {lead.ai_urgency && (
                <span className="px-2 py-0.5 rounded bg-amber-50 text-amber-700">
                  urgency: {lead.ai_urgency}
                </span>
              )}
              {(lead.ai_objections ?? []).map((o, i) => (
                <span key={i} className="px-2 py-0.5 rounded bg-red-50 text-red-700">
                  {o}
                </span>
              ))}
            </div>
          </div>

          {lead.ai_summary && (
            <div>
              <div className="text-xs uppercase tracking-wide text-slate-500">AI Assessment</div>
              <p className="text-sm text-slate-700 mt-1">{lead.ai_summary}</p>
            </div>
          )}

          {lead.ai_next_action && (
            <div className="px-3 py-2 bg-emerald-50 border border-emerald-200 rounded-lg">
              <div className="text-[11px] font-semibold text-emerald-700 uppercase tracking-wide">
                Recommended Next Action
              </div>
              <div className="text-sm text-emerald-900 mt-0.5">{lead.ai_next_action}</div>
            </div>
          )}

          <div>
            <div className="text-xs uppercase tracking-wide text-slate-500 mb-2">Timeline</div>
            <ul className="space-y-2">
              {(lead.timeline ?? []).length === 0 && (
                <li className="text-sm text-slate-500 italic">No events yet.</li>
              )}
              {(lead.timeline ?? []).map((t) => (
                <li
                  key={t.id}
                  className="flex items-start gap-3 text-sm border-l-2 border-slate-200 pl-3"
                >
                  <span className="text-[10px] text-slate-400 mt-1">
                    {t.created_at ? new Date(t.created_at).toLocaleDateString() : ''}
                  </span>
                  <div className="flex-1">
                    <div className="font-medium text-slate-800">{t.title ?? t.event_type}</div>
                    {t.description && (
                      <div className="text-xs text-slate-500">{t.description}</div>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-4">
          <div>
            <label className="text-xs font-semibold text-slate-600">Status</label>
            <select
              value={lead.status ?? 'new'}
              onChange={(e) => updateStatus(e.target.value)}
              className="mt-1 w-full px-2 py-1.5 text-sm border border-slate-300 rounded-lg"
            >
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={generateDraft}
            disabled={draftLoading || !lead.email}
            className="w-full inline-flex items-center justify-center gap-2 px-3 py-2 bg-brand-600 text-white text-sm rounded-lg hover:bg-brand-700 disabled:opacity-50"
          >
            <Mail size={14} /> {draftLoading ? 'Generating…' : 'Generate Email Draft'}
          </button>

          {draft && (
            <div className="border border-slate-200 rounded-lg p-3 bg-slate-50 space-y-1">
              <div className="text-[10px] uppercase tracking-wide text-slate-500">Subject</div>
              <div className="text-sm font-semibold text-slate-800">{draft.subject}</div>
              <div className="text-[10px] uppercase tracking-wide text-slate-500 pt-2">Body</div>
              <pre className="text-xs text-slate-700 whitespace-pre-wrap">{draft.body}</pre>
              <p className="text-[10px] text-amber-700 pt-1">
                AI draft — review before sending. Email is NOT auto-sent.
              </p>
            </div>
          )}

          <div className="text-xs text-slate-500">
            Total calls:{' '}
            <span className="font-semibold text-slate-800">{lead.call_stats?.cnt ?? 0}</span>
          </div>
        </div>
      </div>
    </div>
  )
}

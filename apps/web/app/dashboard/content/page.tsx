'use client'

import { useEffect, useState, useCallback } from 'react'
import {
  FileText, Zap, Twitter, Instagram, Loader2, AlertCircle,
  CheckCircle2, Clock, XCircle, RefreshCw, Send, Calendar,
  Archive, Edit3, ChevronDown, ChevronUp, ArrowRight, Plus,
  Brain, TrendingUp, Play, Eye, Copy
} from 'lucide-react'
import Link from 'next/link'
import { apiFetch, ApiError } from '@/lib/apiFetch'

// ── Types ─────────────────────────────────────────────────────────────────────

interface Draft {
  id: string
  title?: string
  content_type: string
  topic?: string
  generated_text: string
  status: string
  channels: string[]
  trend_keyword?: string
  niche?: string
  created_at: string
  approved_at?: string
  rejection_reason?: string
  platform_post_id?: string
}

interface ActiveExperiment {
  id: string
  niche: string
  channel: string
}

interface Experiments {
  x?: ActiveExperiment
  instagram?: ActiveExperiment
}

// ── Constants ─────────────────────────────────────────────────────────────────

const CONTENT_TYPES = [
  { id: 'educational',    label: 'Educational',    desc: 'Teach something valuable' },
  { id: 'opinion',        label: 'Opinion',         desc: 'Bold take or perspective' },
  { id: 'how_to',         label: 'How-to',          desc: 'Step-by-step guide' },
  { id: 'thread',         label: 'Thread',          desc: 'Multi-post deep dive' },
  { id: 'carousel',       label: 'Carousel',        desc: 'Slides-style content (IG)' },
  { id: 'engagement',     label: 'Engagement',      desc: 'Question or poll prompt' },
  { id: 'storytelling',   label: 'Story',           desc: 'Personal narrative' },
  { id: 'trend_response', label: 'Trend Response',  desc: 'React to trending topic' },
]

const STATUS_CONFIG: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  draft:       { label: 'Draft',     color: 'bg-gray-100 text-gray-600',     icon: <FileText size={10} /> },
  approved:    { label: 'Approved',  color: 'bg-emerald-50 text-emerald-700', icon: <CheckCircle2 size={10} /> },
  scheduled:   { label: 'Scheduled', color: 'bg-blue-50 text-blue-700',       icon: <Clock size={10} /> },
  published:   { label: 'Published', color: 'bg-violet-50 text-violet-700',   icon: <Send size={10} /> },
  failed:      { label: 'Failed',    color: 'bg-red-50 text-red-600',         icon: <XCircle size={10} /> },
  rejected:    { label: 'Rejected',  color: 'bg-red-50 text-red-600',         icon: <XCircle size={10} /> },
}

// ── Draft card ────────────────────────────────────────────────────────────────

function DraftCard({ draft, onAction }: {
  draft: Draft
  onAction: (id: string, action: 'approve' | 'reject' | 'queue') => void
}) {
  const [expanded, setExpanded] = useState(false)
  const [copying, setCopying] = useState(false)
  const status = STATUS_CONFIG[draft.status] ?? STATUS_CONFIG.draft
  const channel = draft.channels?.[0] ?? 'x'

  async function copyText() {
    await navigator.clipboard.writeText(draft.generated_text)
    setCopying(true)
    setTimeout(() => setCopying(false), 1500)
  }

  return (
    <div className={`card overflow-hidden transition-all ${draft.status === 'draft' ? 'border-gray-200' : draft.status === 'approved' ? 'border-emerald-200' : 'border-gray-200'}`}>
      <div className="p-4">
        {/* Header row */}
        <div className="flex items-start gap-3 mb-3">
          <div className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 ${channel === 'instagram' ? 'bg-gradient-to-br from-pink-500 to-purple-500' : 'bg-black'}`}>
            {channel === 'instagram'
              ? <Instagram size={13} className="text-white" />
              : <Twitter size={13} className="text-white" />}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs font-semibold text-gray-700 capitalize">{draft.content_type.replace(/_/g, ' ')}</span>
              {draft.trend_keyword && (
                <span className="text-[10px] font-medium text-brand-600 bg-brand-50 px-1.5 py-0.5 rounded-full">
                  #{draft.trend_keyword}
                </span>
              )}
              <span className={`flex items-center gap-0.5 text-[10px] font-semibold px-2 py-0.5 rounded-full ${status.color}`}>
                {status.icon} {status.label}
              </span>
            </div>
            {draft.topic && <p className="text-[10px] text-gray-400 mt-0.5 truncate">{draft.topic}</p>}
          </div>
          <button onClick={() => setExpanded(e => !e)} className="p-1 rounded-md hover:bg-gray-100 text-gray-400 flex-shrink-0">
            {expanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
          </button>
        </div>

        {/* Preview */}
        <p className={`text-sm text-gray-700 leading-relaxed ${expanded ? '' : 'line-clamp-3'}`}>
          {draft.generated_text}
        </p>

        {/* Char count */}
        <p className="text-[10px] text-gray-400 mt-1.5">
          {draft.generated_text.length} chars
          {draft.channels?.includes('x') && draft.generated_text.length > 280 && (
            <span className="text-amber-500 ml-1">· exceeds X limit</span>
          )}
        </p>
      </div>

      {/* Actions */}
      {(draft.status === 'draft' || draft.status === 'rejected') && (
        <div className="px-4 pb-4 flex items-center gap-2">
          <button
            onClick={() => onAction(draft.id, 'approve')}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 text-white rounded-lg text-xs font-semibold hover:bg-emerald-700 transition-colors"
          >
            <CheckCircle2 size={11} /> Approve
          </button>
          <button
            onClick={() => onAction(draft.id, 'queue')}
            className="flex items-center gap-1.5 px-3 py-1.5 border border-gray-200 rounded-lg text-xs font-medium text-gray-600 hover:bg-gray-50 transition-colors"
          >
            <Calendar size={11} /> Schedule
          </button>
          <button
            onClick={copyText}
            className="flex items-center gap-1.5 px-3 py-1.5 border border-gray-200 rounded-lg text-xs font-medium text-gray-600 hover:bg-gray-50 transition-colors"
          >
            <Copy size={11} /> {copying ? 'Copied!' : 'Copy'}
          </button>
          <button
            onClick={() => onAction(draft.id, 'reject')}
            className="ml-auto flex items-center gap-1 px-2.5 py-1.5 text-xs text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
          >
            <XCircle size={11} /> Reject
          </button>
        </div>
      )}

      {draft.status === 'approved' && (
        <div className="px-4 pb-4 flex items-center gap-2">
          <Link
            href="/dashboard/content/queue"
            className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 text-white rounded-lg text-xs font-semibold hover:bg-blue-700 transition-colors"
          >
            <Calendar size={11} /> Schedule
          </Link>
          <button
            onClick={copyText}
            className="flex items-center gap-1.5 px-3 py-1.5 border border-gray-200 rounded-lg text-xs font-medium text-gray-600 hover:bg-gray-50 transition-colors"
          >
            <Copy size={11} /> {copying ? 'Copied!' : 'Copy'}
          </button>
        </div>
      )}

      {draft.rejection_reason && (
        <div className="px-4 pb-4">
          <p className="text-xs text-red-600 bg-red-50 px-3 py-2 rounded-lg">{draft.rejection_reason}</p>
        </div>
      )}
    </div>
  )
}

// ── Generate form ─────────────────────────────────────────────────────────────

function GenerateForm({
  experiments,
  onGenerated,
}: {
  experiments: Experiments
  onGenerated: () => void
}) {
  const [channel, setChannel] = useState<'x' | 'instagram'>('x')
  const [topic, setTopic] = useState('')
  const [count, setCount] = useState(5)
  const [loading, setLoading] = useState(false)
  const [msg, setMsg] = useState<{ type: 'ok' | 'err'; text: string } | null>(null)

  const exp = channel === 'x' ? experiments.x : experiments.instagram

  async function generate() {
    if (!exp) {
      setMsg({ type: 'err', text: `No active ${channel === 'x' ? 'X' : 'Instagram'} experiment. Set up your niche in Brand Setup first.` })
      return
    }
    setLoading(true); setMsg(null)
    try {
      await apiFetch(`/api/v1/growth/experiments/${exp.id}/generate-posts`, {
        method: 'POST',
        body: JSON.stringify({ count, topic_override: topic.trim() || undefined }),
      })
      setMsg({ type: 'ok', text: `${count} drafts generated for ${channel === 'x' ? 'X' : 'Instagram'}. Review below.` })
      setTopic('')
      onGenerated()
    } catch (e) {
      setMsg({ type: 'err', text: e instanceof ApiError ? e.message : 'Generation failed' })
    } finally { setLoading(false) }
  }

  return (
    <div className="card p-5">
      <h3 className="text-sm font-bold text-gray-900 flex items-center gap-2 mb-4">
        <Zap size={14} className="text-brand-500" /> Generate New Posts
      </h3>

      {/* Channel selector */}
      <div className="flex rounded-xl border border-gray-200 overflow-hidden mb-4">
        {([
          { id: 'x', label: 'X / Twitter', Icon: Twitter, active: channel === 'x', hasExp: !!experiments.x },
          { id: 'instagram', label: 'Instagram', Icon: Instagram, active: channel === 'instagram', hasExp: !!experiments.instagram },
        ] as const).map(c => (
          <button
            key={c.id}
            onClick={() => setChannel(c.id)}
            className={`flex-1 flex items-center justify-center gap-2 py-2.5 text-sm font-medium transition-colors ${
              c.active
                ? c.id === 'instagram'
                  ? 'text-white'
                  : 'bg-black text-white'
                : 'bg-white text-gray-500 hover:bg-gray-50'
            }`}
            style={c.active && c.id === 'instagram' ? { background: 'linear-gradient(135deg, #ec4899, #a855f7)' } : undefined}
          >
            <c.Icon size={14} />
            {c.label}
            {!c.hasExp && <span className="text-[9px] font-bold bg-amber-100 text-amber-600 px-1.5 py-0.5 rounded-full">Setup needed</span>}
          </button>
        ))}
      </div>

      <div className="space-y-3">
        <div>
          <label className="input-label">Topic <span className="font-normal text-gray-400">(optional — uses live trends by default)</span></label>
          <input
            className="input"
            placeholder="e.g. AI tools, productivity systems, SaaS growth"
            value={topic}
            onChange={e => setTopic(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && generate()}
          />
        </div>
        <div className="flex items-center gap-3">
          <select
            className="input w-36 flex-shrink-0"
            value={count}
            onChange={e => setCount(Number(e.target.value))}
          >
            {[3, 5, 10, 15].map(n => <option key={n} value={n}>{n} posts</option>)}
          </select>
          <button
            onClick={generate}
            disabled={loading}
            className="btn-primary flex-1 justify-center"
          >
            {loading ? <Loader2 size={14} className="animate-spin" /> : <Zap size={14} />}
            {loading ? 'Generating…' : `Generate ${count} Posts`}
          </button>
        </div>
      </div>

      {msg && (
        <div className={`mt-3 flex items-center gap-2 text-xs px-3 py-2 rounded-lg ${msg.type === 'ok' ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'}`}>
          {msg.type === 'ok' ? <CheckCircle2 size={12} /> : <AlertCircle size={12} />}
          <span className="flex-1">{msg.text}</span>
        </div>
      )}

      {!exp && (
        <div className="mt-3 flex items-center gap-2 p-3 bg-amber-50 border border-amber-100 rounded-lg">
          <AlertCircle size={13} className="text-amber-500 flex-shrink-0" />
          <p className="text-xs text-amber-700">
            No active {channel === 'x' ? 'X' : 'Instagram'} experiment.{' '}
            <Link href="/dashboard/growth/x-test" className="font-semibold underline">
              Set up your growth campaign →
            </Link>
          </p>
        </div>
      )}
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

type FilterStatus = 'all' | 'draft' | 'approved' | 'scheduled' | 'published' | 'failed'

export default function ContentPage() {
  const [drafts, setDrafts] = useState<Draft[]>([])
  const [experiments, setExperiments] = useState<Experiments>({})
  const [loading, setLoading] = useState(true)
  const [filterStatus, setFilterStatus] = useState<FilterStatus>('draft')
  const [filterChannel, setFilterChannel] = useState<'all' | 'x' | 'instagram'>('all')
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [actionMsg, setActionMsg] = useState<string | null>(null)

  const loadDrafts = useCallback(async () => {
    try {
      const data = await apiFetch<{ posts: Draft[] }>('/api/v1/content-queue/drafts?limit=50')
      setDrafts(data.posts ?? [])
    } catch { /* best effort */ }
  }, [])

  const load = useCallback(async () => {
    setLoading(true)
    await Promise.allSettled([
      loadDrafts(),
      apiFetch<{ has_active: boolean; experiment: ActiveExperiment }>('/api/v1/growth/experiments/active')
        .then(d => { if (d.has_active) setExperiments(e => ({ ...e, x: { ...d.experiment, channel: 'x' } })) })
        .catch(() => {}),
      apiFetch<{ has_active: boolean; experiment: ActiveExperiment }>('/api/v1/growth/experiments/instagram/active')
        .then(d => { if (d.has_active) setExperiments(e => ({ ...e, instagram: { ...d.experiment, channel: 'instagram' } })) })
        .catch(() => {}),
    ])
    setLoading(false)
  }, [loadDrafts])

  useEffect(() => { load() }, [load])

  async function handleAction(draftId: string, action: 'approve' | 'reject' | 'queue') {
    setActionLoading(draftId)
    try {
      if (action === 'approve') {
        await apiFetch(`/api/v1/content-queue/drafts/${draftId}/approve`, { method: 'POST' })
        setActionMsg('Post approved!')
      } else if (action === 'reject') {
        await apiFetch(`/api/v1/content-queue/drafts/${draftId}/reject`, {
          method: 'POST',
          body: JSON.stringify({ reason: 'Rejected via content page' }),
        })
        setActionMsg('Post rejected.')
      } else {
        await apiFetch(`/api/v1/content-queue/drafts/${draftId}/approve`, { method: 'POST' })
        setActionMsg('Post approved and ready for scheduling!')
      }
      await loadDrafts()
    } catch (e) {
      setActionMsg(e instanceof ApiError ? e.message : 'Action failed')
    } finally {
      setActionLoading(null)
      setTimeout(() => setActionMsg(null), 3000)
    }
  }

  // Filter drafts
  const filtered = drafts.filter(d => {
    const statusMatch = filterStatus === 'all' || d.status === filterStatus
    const channelMatch = filterChannel === 'all' || d.channels?.includes(filterChannel)
    return statusMatch && channelMatch
  })

  // Counts
  const counts: Record<FilterStatus, number> = {
    all: drafts.length,
    draft: drafts.filter(d => d.status === 'draft').length,
    approved: drafts.filter(d => d.status === 'approved').length,
    scheduled: drafts.filter(d => d.status === 'scheduled').length,
    published: drafts.filter(d => d.status === 'published').length,
    failed: drafts.filter(d => d.status === 'failed' || d.status === 'rejected').length,
  }

  const tabs: { id: FilterStatus; label: string; color?: string }[] = [
    { id: 'draft', label: 'Drafts' },
    { id: 'approved', label: 'Approved' },
    { id: 'scheduled', label: 'Scheduled' },
    { id: 'published', label: 'Published' },
    { id: 'failed', label: 'Failed / Rejected', color: 'text-red-600' },
    { id: 'all', label: 'All' },
  ]

  return (
    <div className="space-y-6">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">Content</h1>
          <p className="page-subtitle">Generate, review, and schedule posts for X and Instagram</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={load} className="p-2 rounded-lg hover:bg-gray-100 text-gray-400 transition-colors" title="Refresh">
            <RefreshCw size={14} />
          </button>
          <Link href="/dashboard/content/queue" className="btn-secondary text-xs">
            <Calendar size={12} /> View queue
          </Link>
        </div>
      </div>

      {/* Action message */}
      {actionMsg && (
        <div className="flex items-center gap-2 p-3 bg-brand-50 border border-brand-200 rounded-xl text-sm text-brand-700">
          <CheckCircle2 size={14} />
          {actionMsg}
        </div>
      )}

      {/* Generate form */}
      <GenerateForm experiments={experiments} onGenerated={loadDrafts} />

      {/* Filter strip */}
      <div className="flex items-center gap-2 flex-wrap">
        {/* Status tabs */}
        <div className="flex items-center gap-1 p-1 bg-gray-100 rounded-xl">
          {tabs.map(t => (
            <button
              key={t.id}
              onClick={() => setFilterStatus(t.id)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                filterStatus === t.id ? 'bg-white text-gray-900 shadow-sm' : `text-gray-500 hover:text-gray-700 ${t.color ?? ''}`
              }`}
            >
              {t.label}
              {counts[t.id] > 0 && (
                <span className={`min-w-[18px] h-[18px] flex items-center justify-center text-[10px] rounded-full font-bold ${
                  filterStatus === t.id ? 'bg-brand-100 text-brand-700' : 'bg-gray-200 text-gray-600'
                }`}>{counts[t.id]}</span>
              )}
            </button>
          ))}
        </div>

        {/* Channel filter */}
        <div className="flex items-center gap-1 p-1 bg-gray-100 rounded-xl ml-auto">
          {([
            { id: 'all', label: 'All channels' },
            { id: 'x', label: 'X' },
            { id: 'instagram', label: 'Instagram' },
          ] as const).map(c => (
            <button
              key={c.id}
              onClick={() => setFilterChannel(c.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                filterChannel === c.id ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              {c.label}
            </button>
          ))}
        </div>
      </div>

      {/* Draft list */}
      {loading ? (
        <div className="flex items-center gap-2 text-sm text-gray-400 py-8 justify-center">
          <Loader2 size={16} className="animate-spin" /> Loading posts…
        </div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 gap-4 text-center">
          <div className="w-16 h-16 bg-gray-50 rounded-2xl flex items-center justify-center">
            <FileText size={28} className="text-gray-200" />
          </div>
          <div>
            <p className="text-sm font-semibold text-gray-700">
              {filterStatus === 'draft' ? 'No drafts yet' : `No ${filterStatus} posts`}
            </p>
            <p className="text-xs text-gray-400 mt-1">
              {filterStatus === 'draft'
                ? 'Use the Generate form above to create your first batch of posts.'
                : 'Switch to Drafts to generate and approve content.'}
            </p>
          </div>
          {filterStatus !== 'draft' && (
            <button
              onClick={() => setFilterStatus('draft')}
              className="btn-secondary text-xs"
            >
              View drafts
            </button>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map(draft => (
            <DraftCard
              key={draft.id}
              draft={draft}
              onAction={handleAction}
            />
          ))}
        </div>
      )}

      {/* Footer navigation */}
      <div className="flex items-center gap-3 flex-wrap border-t border-gray-100 pt-4">
        <Link href="/dashboard/content/queue" className="btn-secondary text-xs">
          <Calendar size={12} /> Scheduled queue
        </Link>
        <Link href="/dashboard/approvals" className="btn-secondary text-xs">
          <CheckCircle2 size={12} /> Approval queue
        </Link>
        <Link href="/dashboard/trends" className="btn-secondary text-xs">
          <TrendingUp size={12} /> Browse trends
        </Link>
      </div>

    </div>
  )
}

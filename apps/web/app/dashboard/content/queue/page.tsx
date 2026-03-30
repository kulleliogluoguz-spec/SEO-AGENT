'use client'

import { useEffect, useState, useCallback } from 'react'
import {
  FileText, CheckCircle2, XCircle, Clock, Calendar,
  Archive, Loader2, ArrowRight, ChevronRight, Play,
  AlertCircle, Radio, RefreshCw, Zap, Plus
} from 'lucide-react'
import Link from 'next/link'
import { apiFetch } from '@/lib/apiFetch'

// ── Types ─────────────────────────────────────────────────────────────────────

interface ContentDraft {
  id: string
  title: string
  content_type: string
  topic: string
  generated_text: string
  status: string
  niche?: string
  trend_keyword?: string
  objective?: string
  channels: string[]
  created_at: string
  approved_at?: string
  rejection_reason?: string
  lifecycle_log?: Array<{ from: string; to: string; at: string; reason?: string }>
}

interface PublishNowResult {
  success: boolean
  channel: string
  post_id?: string
  post_url?: string
  error?: string
  rate_limited?: boolean
}

interface ScheduledPost {
  id: string
  draft_id: string
  channel: string
  scheduled_at: string
  status: string
  published_at?: string
  error?: string
  publish_attempt_count: number
}

interface QueueSummary {
  draft_counts: Record<string, number>
  total_drafts: number
  scheduled_upcoming: number
  next_scheduled_at: string | null
  needs_action: number
}


const STATUS_CONFIG: Record<string, { label: string; color: string; dot: string }> = {
  generated:    { label: 'Generated',    color: 'badge-gray',   dot: 'bg-gray-400' },
  needs_review: { label: 'Needs Review', color: 'badge-yellow', dot: 'bg-amber-400' },
  approved:     { label: 'Approved',     color: 'badge-green',  dot: 'bg-emerald-500' },
  scheduled:    { label: 'Scheduled',    color: 'badge-blue',   dot: 'bg-blue-500' },
  publishing:   { label: 'Publishing',   color: 'badge-blue',   dot: 'bg-blue-500 animate-pulse' },
  published:    { label: 'Published',    color: 'badge-green',  dot: 'bg-emerald-600' },
  failed:       { label: 'Failed',       color: 'badge-red',    dot: 'bg-red-400' },
  archived:     { label: 'Archived',     color: 'badge-gray',   dot: 'bg-gray-300' },
}

const CONTENT_TYPE_LABELS: Record<string, string> = {
  reel_script: 'Reel', carousel: 'Carousel', caption: 'Caption',
  story: 'Story', ad_copy: 'Ad Copy', blog: 'Blog', landing_page: 'Landing Page',
}

const STATUS_TABS = [
  { id: '', label: 'All' },
  { id: 'needs_review', label: 'Needs Review' },
  { id: 'approved', label: 'Approved' },
  { id: 'scheduled', label: 'Scheduled' },
  { id: 'published', label: 'Published' },
  { id: 'failed', label: 'Failed' },
]

function ScheduleModal({
  draft,
  onClose,
  onScheduled,
}: {
  draft: ContentDraft
  onClose: () => void
  onScheduled: () => void
}) {
  const [channel, setChannel] = useState('instagram')
  const [scheduledAt, setScheduledAt] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  async function handleSchedule() {
    if (!scheduledAt) { setError('Please select a date/time'); return }
    setSaving(true)
    setError('')
    try {
      await apiFetch(`/api/v1/content-queue/drafts/${draft.id}/schedule`, {
        method: 'POST',
        body: JSON.stringify({ channel, scheduled_at: new Date(scheduledAt).toISOString() }),
      })
      onScheduled()
      onClose()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to schedule')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-2xl shadow-2xl p-6 w-full max-w-sm mx-4">
        <h3 className="text-base font-bold text-gray-900 mb-1">Schedule Post</h3>
        <p className="text-xs text-gray-500 mb-4 truncate">{draft.title}</p>

        <div className="space-y-3">
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">Channel</label>
            <select
              value={channel}
              onChange={e => setChannel(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/30"
            >
              {['instagram', 'x', 'tiktok', 'linkedin', 'youtube'].map(c => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">Scheduled At</label>
            <input
              type="datetime-local"
              value={scheduledAt}
              onChange={e => setScheduledAt(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/30"
            />
          </div>
          {error && (
            <p className="text-xs text-red-600 flex items-center gap-1">
              <AlertCircle size={11} /> {error}
            </p>
          )}
        </div>

        <div className="flex gap-2 mt-5">
          <button onClick={onClose} className="flex-1 btn-secondary text-sm">Cancel</button>
          <button
            onClick={handleSchedule}
            disabled={saving}
            className="flex-1 btn-primary text-sm flex items-center justify-center gap-1"
          >
            {saving ? <Loader2 size={12} className="animate-spin" /> : <Calendar size={12} />}
            Schedule
          </button>
        </div>
      </div>
    </div>
  )
}

function PublishNowModal({
  draft,
  onClose,
  onPublished,
}: {
  draft: ContentDraft
  onClose: () => void
  onPublished: () => void
}) {
  const [channel, setChannel] = useState(draft.channels[0] ?? 'x')
  const [publishing, setPublishing] = useState(false)
  const [result, setResult] = useState<PublishNowResult | null>(null)
  const [error, setError] = useState('')

  async function handlePublish() {
    setPublishing(true)
    setError('')
    setResult(null)
    try {
      const data = await apiFetch<PublishNowResult>(`/api/v1/publishing/publish-now/${draft.id}`, {
        method: 'POST',
        body: JSON.stringify({ channel }),
      })
      setResult(data)
      if (data.success) {
        setTimeout(() => { onPublished(); onClose() }, 2000)
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Publish failed')
    } finally {
      setPublishing(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-2xl shadow-2xl p-6 w-full max-w-sm mx-4">
        <h3 className="text-base font-bold text-gray-900 mb-1">Publish Now</h3>
        <p className="text-xs text-gray-500 mb-4 truncate">{draft.title}</p>

        {result ? (
          <div className={`p-4 rounded-xl ${result.success ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
            {result.success ? (
              <>
                <p className="text-sm font-semibold text-green-700 mb-1">Published!</p>
                {result.post_url && (
                  <a href={result.post_url} target="_blank" rel="noopener noreferrer"
                    className="text-xs text-green-600 underline break-all">
                    View post →
                  </a>
                )}
                {!result.post_url && result.post_id && (
                  <p className="text-xs text-green-600">Post ID: {result.post_id}</p>
                )}
              </>
            ) : (
              <>
                <p className="text-sm font-semibold text-red-700 mb-1">Publish failed</p>
                <p className="text-xs text-red-600">{result.error}</p>
                {result.rate_limited && <p className="text-xs text-orange-600 mt-1">Rate limited — try again later</p>}
              </>
            )}
          </div>
        ) : (
          <div className="space-y-3">
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">Channel</label>
              <select
                value={channel}
                onChange={e => setChannel(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/30"
              >
                {['x', 'instagram', 'tiktok', 'linkedin'].map(c => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
              <p className="text-xs text-amber-700">
                This will immediately publish to <strong>{channel}</strong> — no scheduling.
              </p>
            </div>
            {error && (
              <p className="text-xs text-red-600 flex items-center gap-1">
                <AlertCircle size={11} /> {error}
              </p>
            )}
          </div>
        )}

        <div className="flex gap-2 mt-5">
          <button onClick={onClose} className="flex-1 btn-secondary text-sm">
            {result?.success ? 'Close' : 'Cancel'}
          </button>
          {!result && (
            <button
              onClick={handlePublish}
              disabled={publishing}
              className="flex-1 btn-primary text-sm flex items-center justify-center gap-1"
            >
              {publishing ? <Loader2 size={12} className="animate-spin" /> : <Play size={12} />}
              {publishing ? 'Publishing…' : 'Publish Now'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function ContentQueuePage() {
  const [drafts, setDrafts] = useState<ContentDraft[]>([])
  const [summary, setSummary] = useState<QueueSummary | null>(null)
  const [activeTab, setActiveTab] = useState('')
  const [loading, setLoading] = useState(true)
  const [actioning, setActioning] = useState<string | null>(null)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [schedulingDraft, setSchedulingDraft] = useState<ContentDraft | null>(null)
  const [publishingDraft, setPublishingDraft] = useState<ContentDraft | null>(null)

  const loadQueue = useCallback(async () => {
    setLoading(true)
    try {
      const [draftsRes, summaryRes] = await Promise.allSettled([
        apiFetch<{ drafts: ContentDraft[] }>(`/api/v1/content-queue/drafts${activeTab ? `?status=${activeTab}` : ''}`),
        apiFetch<QueueSummary>('/api/v1/content-queue/summary'),
      ])
      if (draftsRes.status === 'fulfilled') setDrafts(draftsRes.value.drafts ?? [])
      if (summaryRes.status === 'fulfilled') setSummary(summaryRes.value)
    } catch { /* ignore */ } finally {
      setLoading(false)
    }
  }, [activeTab])

  useEffect(() => { loadQueue() }, [loadQueue])

  async function handleAction(draftId: string, action: 'approve' | 'reject' | 'archive') {
    setActioning(draftId)
    try {
      await apiFetch(`/api/v1/content-queue/drafts/${draftId}/${action}`, { method: 'POST' })
      await loadQueue()
    } catch (e) {
      console.error(e)
    } finally {
      setActioning(null)
    }
  }

  const busy = (id: string) => actioning === id

  return (
    <div className="space-y-5">

      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Content Queue</h1>
          <p className="page-subtitle">Lifecycle view: generated → review → approved → scheduled → published</p>
        </div>
        <div className="flex gap-2">
          <button onClick={loadQueue} disabled={loading} className="btn-secondary flex items-center gap-1.5 text-xs">
            <RefreshCw size={11} className={loading ? 'animate-spin' : ''} /> Refresh
          </button>
          <Link href="/dashboard/content/new" className="btn-primary flex items-center gap-1.5 text-xs">
            <Plus size={11} /> New Content
          </Link>
        </div>
      </div>

      {/* Summary cards */}
      {summary && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {[
            { label: 'Needs Action', value: summary.needs_action, color: 'text-amber-600 bg-amber-50', icon: AlertCircle },
            { label: 'Approved', value: summary.draft_counts.approved ?? 0, color: 'text-emerald-600 bg-emerald-50', icon: CheckCircle2 },
            { label: 'Scheduled', value: summary.scheduled_upcoming, color: 'text-blue-600 bg-blue-50', icon: Calendar },
            { label: 'Published', value: summary.draft_counts.published ?? 0, color: 'text-violet-600 bg-violet-50', icon: Radio },
          ].map(card => (
            <div key={card.label} className={`card-stat ${card.color.includes('bg') ? '' : ''}`}>
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs font-medium text-gray-500 uppercase tracking-widest">{card.label}</p>
                  <p className="text-2xl font-bold text-gray-900 mt-1.5">{card.value}</p>
                </div>
                <div className={`w-9 h-9 rounded-xl flex items-center justify-center ${card.color}`}>
                  <card.icon size={16} />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Status tabs */}
      <div className="flex gap-1 overflow-x-auto">
        {STATUS_TABS.map(tab => {
          const count = tab.id && summary ? (summary.draft_counts[tab.id] ?? 0) : (summary?.total_drafts ?? 0)
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-all ${
                activeTab === tab.id
                  ? 'bg-brand-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {tab.label}
              {count > 0 && (
                <span className={`min-w-[16px] h-4 flex items-center justify-center text-[9px] rounded-full px-1 font-bold ${
                  activeTab === tab.id ? 'bg-white/20' : 'bg-gray-300 text-gray-600'
                }`}>
                  {count}
                </span>
              )}
            </button>
          )
        })}
      </div>

      {/* Draft list */}
      {loading ? (
        <div className="space-y-2">
          {[1, 2, 3].map(i => <div key={i} className="h-16 card animate-pulse" />)}
        </div>
      ) : drafts.length === 0 ? (
        <div className="card p-12 text-center">
          <FileText size={28} className="mx-auto mb-3 text-gray-200" />
          <p className="text-sm text-gray-400 mb-3">
            {activeTab ? `No drafts with status "${activeTab}"` : 'No content drafts yet'}
          </p>
          <Link href="/dashboard/growth" className="btn-secondary text-xs inline-flex items-center gap-1.5">
            <Zap size={11} /> Generate from trends
          </Link>
        </div>
      ) : (
        <div className="space-y-2">
          {drafts.map(draft => {
            const cfg = STATUS_CONFIG[draft.status] ?? STATUS_CONFIG.generated
            const isExpanded = expandedId === draft.id
            return (
              <div key={draft.id} className="card overflow-hidden">
                {/* Row */}
                <div
                  className="flex items-center gap-3 p-4 cursor-pointer hover:bg-gray-50 transition-colors"
                  onClick={() => setExpandedId(isExpanded ? null : draft.id)}
                >
                  <div className={`w-2 h-2 rounded-full flex-shrink-0 ${cfg.dot}`} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className={`${cfg.color} text-[10px]`}>{cfg.label}</span>
                      <span className="badge-gray text-[10px]">
                        {CONTENT_TYPE_LABELS[draft.content_type] ?? draft.content_type}
                      </span>
                      {draft.trend_keyword && (
                        <span className="text-[10px] text-orange-600 bg-orange-50 px-1.5 py-0.5 rounded">
                          trend: {draft.trend_keyword}
                        </span>
                      )}
                    </div>
                    <p className="text-sm font-medium text-gray-900 truncate">{draft.title}</p>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    {/* Action buttons */}
                    {(draft.status === 'generated' || draft.status === 'needs_review') && (
                      <>
                        <button
                          onClick={e => { e.stopPropagation(); handleAction(draft.id, 'reject') }}
                          disabled={busy(draft.id)}
                          className="p-1.5 rounded-lg border border-red-200 text-red-500 hover:bg-red-50 disabled:opacity-40 transition-colors"
                          title="Send back for review"
                        >
                          <XCircle size={13} />
                        </button>
                        <button
                          onClick={e => { e.stopPropagation(); handleAction(draft.id, 'approve') }}
                          disabled={busy(draft.id)}
                          className="p-1.5 rounded-lg border border-emerald-200 text-emerald-600 hover:bg-emerald-50 disabled:opacity-40 transition-colors"
                          title="Approve"
                        >
                          {busy(draft.id) ? <Loader2 size={13} className="animate-spin" /> : <CheckCircle2 size={13} />}
                        </button>
                      </>
                    )}
                    {draft.status === 'approved' && (
                      <>
                        <button
                          onClick={e => { e.stopPropagation(); setPublishingDraft(draft) }}
                          className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-emerald-200 text-emerald-700 hover:bg-emerald-50 text-xs font-medium transition-colors"
                        >
                          <Play size={11} /> Publish
                        </button>
                        <button
                          onClick={e => { e.stopPropagation(); setSchedulingDraft(draft) }}
                          className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-blue-200 text-blue-600 hover:bg-blue-50 text-xs font-medium transition-colors"
                        >
                          <Calendar size={11} /> Schedule
                        </button>
                      </>
                    )}
                    {!['published', 'archived'].includes(draft.status) && (
                      <button
                        onClick={e => { e.stopPropagation(); handleAction(draft.id, 'archive') }}
                        disabled={busy(draft.id)}
                        className="p-1.5 rounded-lg text-gray-400 hover:bg-gray-100 disabled:opacity-40 transition-colors"
                        title="Archive"
                      >
                        <Archive size={13} />
                      </button>
                    )}
                    <ChevronRight
                      size={13}
                      className={`text-gray-400 transition-transform ${isExpanded ? 'rotate-90' : ''}`}
                    />
                  </div>
                </div>

                {/* Expanded: content text */}
                {isExpanded && (
                  <div className="border-t border-gray-100 p-4 bg-gray-50">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-xs font-semibold text-gray-600">Generated Content</span>
                    </div>
                    <pre className="text-xs text-gray-700 whitespace-pre-wrap font-sans leading-relaxed max-h-56 overflow-y-auto">
                      {draft.generated_text}
                    </pre>
                    {draft.rejection_reason && (
                      <div className="mt-3 p-2 bg-amber-50 border border-amber-200 rounded-lg">
                        <p className="text-xs text-amber-700">
                          <AlertCircle size={10} className="inline mr-1" />
                          Review note: {draft.rejection_reason}
                        </p>
                      </div>
                    )}
                    {draft.lifecycle_log && draft.lifecycle_log.length > 0 && (
                      <div className="mt-3">
                        <p className="text-[10px] text-gray-500 mb-1 font-semibold uppercase tracking-wider">History</p>
                        <div className="space-y-1">
                          {draft.lifecycle_log.slice(-3).map((entry, i) => (
                            <p key={i} className="text-[10px] text-gray-400">
                              {entry.from} → {entry.to} · {new Date(entry.at).toLocaleString()}
                            </p>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* Schedule modal */}
      {schedulingDraft && (
        <ScheduleModal
          draft={schedulingDraft}
          onClose={() => setSchedulingDraft(null)}
          onScheduled={loadQueue}
        />
      )}

      {/* Publish Now modal */}
      {publishingDraft && (
        <PublishNowModal
          draft={publishingDraft}
          onClose={() => setPublishingDraft(null)}
          onPublished={loadQueue}
        />
      )}
    </div>
  )
}

'use client'

import { useEffect, useState, useCallback } from 'react'
import {
  Twitter, Loader2, AlertCircle, CheckCircle2,
  RefreshCw, XCircle, Send, Edit3, ChevronDown,
  ChevronUp, Trash2, RotateCcw, Zap,
} from 'lucide-react'
import Link from 'next/link'
import { apiFetch } from '@/lib/apiFetch'

interface QueueItem {
  id: number
  content: string
  tweet_type: string
  thread_tweets?: string[]
  status: string
  niche: string
  hook_type: string
  pillar: string
  ai_score: number
  best_time: string
  error_message?: string
  created_at: string
}

interface QueueResponse {
  status: string
  count: number
  items: QueueItem[]
}

// ── Tweet Card ───────────────────────────────────────────────────────────────

function TweetCard({
  item,
  onAction,
}: {
  item: QueueItem
  onAction: () => void
}) {
  const [expanded, setExpanded] = useState(false)
  const [editing, setEditing] = useState(false)
  const [editText, setEditText] = useState(item.content)
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  const isThread = item.tweet_type === 'thread'
  const threadTweets = item.thread_tweets || []

  async function doAction(action: string, method: string = 'POST', url?: string) {
    setActionLoading(action)
    try {
      const endpoint = url || `/api/v1/twitter/queue/${item.id}/${action}`
      await apiFetch(endpoint, { method })
      onAction()
    } catch { /* ignore */ }
    finally { setActionLoading(null) }
  }

  async function handleSaveEdit() {
    setActionLoading('edit')
    try {
      await apiFetch(`/api/v1/twitter/queue/${item.id}/edit`, {
        method: 'PUT',
        body: JSON.stringify({ content: editText }),
      })
      setEditing(false)
      onAction()
    } catch { /* ignore */ }
    finally { setActionLoading(null) }
  }

  const scoreColor = item.ai_score >= 85 ? 'text-emerald-600 bg-emerald-50' :
    item.ai_score >= 70 ? 'text-blue-600 bg-blue-50' : 'text-gray-600 bg-gray-50'

  return (
    <div className="card p-4 hover:shadow-md transition-shadow">
      {/* Header row */}
      <div className="flex items-center gap-2 mb-2 flex-wrap">
        <span className={`text-[9px] font-bold uppercase px-2 py-0.5 rounded-full ${
          isThread ? 'bg-violet-100 text-violet-700' : 'bg-gray-100 text-gray-600'
        }`}>
          {isThread ? `Thread - ${threadTweets.length} tweets` : 'Single Tweet'}
        </span>
        {item.hook_type && item.hook_type !== 'manual' && (
          <span className="text-[9px] px-2 py-0.5 rounded-full bg-blue-50 text-blue-600 font-medium">
            {item.hook_type.replace(/_/g, ' ')}
          </span>
        )}
        {item.pillar && (
          <span className="text-[9px] px-2 py-0.5 rounded-full bg-amber-50 text-amber-600 font-medium">
            {item.pillar}
          </span>
        )}
        <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full ${scoreColor}`}>
          Score: {item.ai_score}
        </span>
        {item.best_time && (
          <span className="text-[9px] text-gray-400 ml-auto">Best: {item.best_time}</span>
        )}
      </div>

      {/* Content */}
      {editing ? (
        <div className="mb-3">
          <textarea
            rows={3}
            maxLength={280}
            className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/30 resize-none"
            value={editText}
            onChange={e => setEditText(e.target.value)}
          />
          <div className="flex items-center justify-between mt-1">
            <span className={`text-xs ${editText.length > 260 ? 'text-red-500' : 'text-gray-400'}`}>
              {editText.length}/280
            </span>
            <div className="flex gap-2">
              <button onClick={() => { setEditing(false); setEditText(item.content) }} className="text-xs text-gray-500 hover:text-gray-700">Cancel</button>
              <button
                onClick={handleSaveEdit}
                disabled={actionLoading === 'edit' || !editText.trim() || editText.length > 280}
                className="text-xs font-semibold text-brand-600 hover:text-brand-700 disabled:opacity-40"
              >
                {actionLoading === 'edit' ? 'Saving...' : 'Save'}
              </button>
            </div>
          </div>
        </div>
      ) : (
        <p className="text-sm text-gray-800 leading-relaxed mb-2 whitespace-pre-wrap">{item.content}</p>
      )}

      {/* Thread expansion */}
      {isThread && threadTweets.length > 0 && (
        <div className="mb-3">
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1 text-xs text-violet-600 hover:text-violet-800 font-medium"
          >
            {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            {expanded ? 'Hide thread' : `Show all ${threadTweets.length} tweets`}
          </button>
          {expanded && (
            <div className="mt-2 space-y-2 pl-3 border-l-2 border-violet-100">
              {threadTweets.map((t, i) => (
                <p key={i} className="text-xs text-gray-600 leading-relaxed">{t}</p>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Character count for singles */}
      {!isThread && !editing && (
        <p className="text-[10px] text-gray-400 mb-3">{item.content.length}/280 chars</p>
      )}

      {/* Error message */}
      {item.error_message && (
        <div className="flex items-center gap-2 text-xs text-red-600 bg-red-50 px-3 py-2 rounded-lg mb-3">
          <AlertCircle size={12} /> {item.error_message}
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-2 flex-wrap">
        {item.status === 'pending' && (
          <>
            <button
              onClick={() => setEditing(true)}
              disabled={!!actionLoading}
              className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 disabled:opacity-40"
            >
              <Edit3 size={11} /> Edit
            </button>
            <button
              onClick={() => doAction('reject')}
              disabled={!!actionLoading}
              className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium bg-red-50 text-red-600 rounded-lg hover:bg-red-100 disabled:opacity-40"
            >
              {actionLoading === 'reject' ? <Loader2 size={11} className="animate-spin" /> : <XCircle size={11} />}
              Reject
            </button>
            <button
              onClick={() => doAction('approve')}
              disabled={!!actionLoading}
              className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium bg-emerald-50 text-emerald-700 rounded-lg hover:bg-emerald-100 disabled:opacity-40"
            >
              {actionLoading === 'approve' ? <Loader2 size={11} className="animate-spin" /> : <CheckCircle2 size={11} />}
              Approve
            </button>
            <button
              onClick={() => apiFetch(`/api/v1/twitter/queue/${item.id}/approve?post_now=true`, { method: 'POST' }).then(onAction)}
              disabled={!!actionLoading}
              className="flex items-center gap-1 px-4 py-1.5 text-xs font-bold bg-black text-white rounded-lg hover:bg-gray-800 disabled:opacity-40 ml-auto"
            >
              <Send size={11} /> Post Now
            </button>
          </>
        )}
        {item.status === 'approved' && (
          <>
            <button
              onClick={() => doAction('post')}
              disabled={!!actionLoading}
              className="flex items-center gap-1 px-4 py-1.5 text-xs font-bold bg-black text-white rounded-lg hover:bg-gray-800 disabled:opacity-40"
            >
              {actionLoading === 'post' ? <Loader2 size={11} className="animate-spin" /> : <Send size={11} />}
              Post Now
            </button>
            <button
              onClick={() => doAction('reject')}
              disabled={!!actionLoading}
              className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-gray-500 hover:text-red-600"
            >
              <XCircle size={11} /> Revoke
            </button>
          </>
        )}
        {item.status === 'rejected' && (
          <button
            onClick={() => doAction('restore')}
            disabled={!!actionLoading}
            className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-100 disabled:opacity-40"
          >
            <RotateCcw size={11} /> Re-approve
          </button>
        )}
        {item.status === 'error' && (
          <button
            onClick={() => doAction('post')}
            disabled={!!actionLoading}
            className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium bg-amber-50 text-amber-700 rounded-lg hover:bg-amber-100 disabled:opacity-40"
          >
            <RotateCcw size={11} /> Retry
          </button>
        )}
        {/* Always show delete */}
        <button
          onClick={() => doAction('', 'DELETE', `/api/v1/twitter/queue/${item.id}`)}
          disabled={!!actionLoading}
          className="flex items-center gap-1 px-2 py-1.5 text-xs text-gray-400 hover:text-red-500 ml-auto"
        >
          <Trash2 size={11} />
        </button>
      </div>
    </div>
  )
}

// ── Main Page ────────────────────────────────────────────────────────────────

export default function QueuePage() {
  const [tab, setTab] = useState<string>('pending')
  const [queue, setQueue] = useState<QueueResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [approveAllLoading, setApproveAllLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await apiFetch<QueueResponse>(`/api/v1/twitter/queue?status=${tab}&limit=50`)
      setQueue(data)
    } catch { setQueue(null) }
    finally { setLoading(false) }
  }, [tab])

  useEffect(() => { load() }, [load])

  async function handleApproveAll(postNow: boolean) {
    setApproveAllLoading(true)
    try {
      await apiFetch(`/api/v1/twitter/queue/approve-all?post_now=${postNow}`, { method: 'POST' })
      load()
    } catch { /* ignore */ }
    finally { setApproveAllLoading(false) }
  }

  const tabs = [
    { key: 'pending', label: 'Pending', count: null },
    { key: 'approved', label: 'Approved', count: null },
    { key: 'posted', label: 'Posted', count: null },
    { key: 'rejected', label: 'Rejected', count: null },
    { key: 'error', label: 'Errors', count: null },
  ]

  return (
    <div className="space-y-5">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-black rounded-xl flex items-center justify-center">
            <Twitter size={16} className="text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-gray-900">Content Queue</h1>
            <p className="text-xs text-gray-500">Review, approve, and post AI-generated tweets</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Link href="/dashboard/twitter-engine" className="text-xs text-gray-500 hover:text-gray-700">
            ← Back to Hub
          </Link>
          <button onClick={load} className="p-2 rounded-lg hover:bg-gray-100 text-gray-400">
            <RefreshCw size={14} />
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 border-b border-gray-100 pb-px">
        {tabs.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2 text-xs font-medium rounded-t-lg transition-colors ${
              tab === t.key
                ? 'bg-white border border-b-white border-gray-200 text-gray-900 -mb-px'
                : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
            }`}
          >
            {t.label}
            {queue && tab === t.key && queue.count > 0 && (
              <span className="ml-1.5 text-[10px] bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded-full font-semibold">
                {queue.count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Approve All button for pending tab */}
      {tab === 'pending' && queue && queue.count > 0 && (
        <div className="flex items-center gap-2">
          <button
            onClick={() => handleApproveAll(false)}
            disabled={approveAllLoading}
            className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold bg-emerald-50 text-emerald-700 rounded-lg hover:bg-emerald-100 disabled:opacity-40"
          >
            {approveAllLoading ? <Loader2 size={12} className="animate-spin" /> : <CheckCircle2 size={12} />}
            Approve All ({queue.count})
          </button>
          <button
            onClick={() => handleApproveAll(true)}
            disabled={approveAllLoading}
            className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold bg-black text-white rounded-lg hover:bg-gray-800 disabled:opacity-40"
          >
            <Zap size={12} /> Approve & Post All
          </button>
        </div>
      )}

      {/* Queue Items */}
      {loading ? (
        <div className="flex items-center justify-center h-40">
          <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
        </div>
      ) : queue && queue.items.length > 0 ? (
        <div className="space-y-3">
          {queue.items.map(item => (
            <TweetCard key={item.id} item={item} onAction={load} />
          ))}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center h-40 gap-3 text-center">
          <Twitter size={24} className="text-gray-200" />
          <p className="text-sm text-gray-400">No {tab} tweets</p>
          {tab === 'pending' && (
            <Link href="/dashboard/twitter-engine" className="text-xs text-brand-600 font-semibold hover:underline">
              Generate content →
            </Link>
          )}
        </div>
      )}

    </div>
  )
}

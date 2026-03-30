'use client'

import { useState, useEffect, useCallback } from 'react'
import { apiFetch } from '@/lib/apiFetch'
import {
  Activity,
  CheckCircle,
  XCircle,
  AlertTriangle,
  RefreshCw,
  Filter,
  Clock,
  Zap,
  Shield,
  TrendingUp,
} from 'lucide-react'

interface AuditEvent {
  id: string
  action: string
  channel?: string
  success: boolean
  post_id?: string
  content_id?: string
  campaign_id?: string
  error?: string
  timestamp: string
}

function getActionIcon(action: string) {
  if (action.startsWith('publish.')) return Zap
  if (action.startsWith('kill_switch')) return Shield
  if (action.startsWith('reallocation')) return TrendingUp
  if (action.startsWith('campaign')) return TrendingUp
  return Activity
}

function getActionColor(action: string, success: boolean) {
  if (!success) return 'bg-red-50 text-red-600 border border-red-100'
  if (action.startsWith('publish.')) return 'bg-green-50 text-green-700'
  if (action.startsWith('kill_switch')) return 'bg-red-50 text-red-700'
  if (action.startsWith('reallocation')) return 'bg-blue-50 text-blue-700'
  return 'bg-gray-100 text-gray-600'
}

function formatRelTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

const CHANNEL_FILTERS = ['all', 'x', 'instagram', 'tiktok']
const ACTION_PREFIX_FILTERS = [
  { label: 'All', value: '' },
  { label: 'Publish', value: 'publish.' },
  { label: 'Campaign', value: 'campaign.' },
  { label: 'Policy', value: 'kill_switch.' },
]

export default function ActivityPage() {
  const [events, setEvents] = useState<AuditEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [channelFilter, setChannelFilter] = useState('all')
  const [actionPrefix, setActionPrefix] = useState('')
  const [summary, setSummary] = useState<{
    total_published: number
    total_failed: number
    by_channel: Record<string, { published: number; failed: number; last_at: string | null }>
    last_action_at: string | null
  } | null>(null)

  const load = useCallback(async (showRefresh = false) => {
    if (showRefresh) setRefreshing(true)
    try {
      const params = new URLSearchParams({ limit: '100' })
      if (channelFilter !== 'all') params.set('channel', channelFilter)
      if (actionPrefix) params.set('action_prefix', actionPrefix)

      const [auditData, summaryData] = await Promise.all([
        apiFetch<{ events: AuditEvent[] }>(`/api/v1/publishing/audit?${params}`),
        apiFetch<typeof summary>('/api/v1/publishing/summary').catch(() => null),
      ])
      setEvents(auditData.events ?? [])
      if (summaryData) setSummary(summaryData)
    } catch {
      // keep existing state
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [channelFilter, actionPrefix])

  useEffect(() => { load() }, [load])

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-black rounded-lg">
            <Activity className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-semibold">Audit Log</h1>
            <p className="text-sm text-gray-500">Every autonomous action the platform took on your behalf — immutable record</p>
          </div>
        </div>
        <button
          onClick={() => load(true)}
          disabled={refreshing}
          className="flex items-center gap-2 px-3 py-1.5 border border-gray-200 rounded-lg text-sm hover:bg-gray-50 disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-4 gap-4">
          <div className="bg-white border border-gray-200 rounded-xl p-4">
            <div className="text-2xl font-bold text-green-600">{summary.total_published}</div>
            <div className="text-xs text-gray-500 mt-1">Posts Published</div>
          </div>
          <div className="bg-white border border-gray-200 rounded-xl p-4">
            <div className="text-2xl font-bold text-red-500">{summary.total_failed}</div>
            <div className="text-xs text-gray-500 mt-1">Failed Attempts</div>
          </div>
          {Object.entries(summary.by_channel).slice(0, 2).map(([ch, stats]) => (
            <div key={ch} className="bg-white border border-gray-200 rounded-xl p-4">
              <div className="text-2xl font-bold">{stats.published}</div>
              <div className="text-xs text-gray-500 mt-1">{ch.charAt(0).toUpperCase() + ch.slice(1)} published</div>
              {stats.last_at && (
                <div className="text-xs text-gray-400 mt-0.5">Last: {formatRelTime(stats.last_at)}</div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Filters */}
      <div className="flex items-center gap-4 bg-white border border-gray-200 rounded-xl p-4 flex-wrap">
        <Filter className="w-4 h-4 text-gray-400 flex-shrink-0" />
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs text-gray-500">Channel:</span>
          {CHANNEL_FILTERS.map(ch => (
            <button
              key={ch}
              onClick={() => setChannelFilter(ch)}
              className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-colors ${channelFilter === ch ? 'bg-black text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
            >
              {ch === 'all' ? 'All' : ch.charAt(0).toUpperCase() + ch.slice(1)}
            </button>
          ))}
        </div>
        <div className="h-4 w-px bg-gray-200" />
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs text-gray-500">Type:</span>
          {ACTION_PREFIX_FILTERS.map(f => (
            <button
              key={f.value}
              onClick={() => setActionPrefix(f.value)}
              className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-colors ${actionPrefix === f.value ? 'bg-black text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {/* Event List */}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-32">
            <div className="w-6 h-6 border-2 border-black border-t-transparent rounded-full animate-spin" />
          </div>
        ) : events.length === 0 ? (
          <div className="text-center py-16 text-gray-400">
            <Activity className="w-8 h-8 mx-auto mb-3 opacity-30" />
            <p className="text-sm font-medium">No activity recorded yet</p>
            <p className="text-xs mt-1">Platform actions appear here as they happen</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {events.map(event => {
              const Icon = getActionIcon(event.action)
              const colorClass = getActionColor(event.action, event.success)
              return (
                <div key={event.id} className="flex items-start gap-4 p-4 hover:bg-gray-50">
                  <div className={`p-1.5 rounded-lg flex-shrink-0 ${colorClass}`}>
                    <Icon className="w-3.5 h-3.5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-mono font-medium text-gray-800">{event.action}</span>
                      {event.channel && (
                        <span className="text-xs bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">{event.channel}</span>
                      )}
                      {event.post_id && (
                        <span className="text-xs text-gray-300 truncate max-w-[100px]">#{event.post_id.slice(0, 8)}</span>
                      )}
                    </div>
                    {event.error && (
                      <p className="text-xs text-red-600 mt-0.5 truncate">{event.error}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    {event.success
                      ? <CheckCircle className="w-4 h-4 text-green-500" />
                      : <XCircle className="w-4 h-4 text-red-400" />
                    }
                    <span className="flex items-center gap-1 text-xs text-gray-400">
                      <Clock className="w-3 h-3" />
                      {formatRelTime(event.timestamp)}
                    </span>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {events.length === 0 && !loading && (
        <div className="flex items-center gap-2 p-4 bg-amber-50 border border-amber-200 rounded-xl text-sm text-amber-800">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          Events are recorded when the platform auto-publishes, launches campaigns, reallocates budget, or enforces policy.
          Connect a channel and enable auto-publish to start generating events.
        </div>
      )}
    </div>
  )
}

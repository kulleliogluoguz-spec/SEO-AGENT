'use client'

import { useEffect, useState, useCallback } from 'react'
import {
  Twitter, Loader2, RefreshCw, ExternalLink,
  Heart, MessageCircle, Repeat2, Eye, Calendar,
} from 'lucide-react'
import Link from 'next/link'
import { apiFetch } from '@/lib/apiFetch'

interface PostedItem {
  id: number
  content: string
  tweet_type: string
  thread_tweets?: string[]
  tweet_id: string
  post_url: string
  posted_at: string
  likes: number
  retweets: number
  replies: number
  impressions: number
  niche: string
  ai_score: number
}

interface PostedResponse {
  posted: number
  items: PostedItem[]
}

export default function PostedPage() {
  const [data, setData] = useState<PostedResponse | null>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const result = await apiFetch<PostedResponse>('/api/v1/twitter/posted?limit=50')
      setData(result)
    } catch { setData(null) }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  // Compute summary
  const totalLikes = data?.items.reduce((s, i) => s + i.likes, 0) ?? 0
  const totalRetweets = data?.items.reduce((s, i) => s + i.retweets, 0) ?? 0
  const totalImpressions = data?.items.reduce((s, i) => s + i.impressions, 0) ?? 0
  const threads = data?.items.filter(i => i.tweet_type === 'thread').length ?? 0
  const singles = (data?.posted ?? 0) - threads

  return (
    <div className="space-y-5">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-black rounded-xl flex items-center justify-center">
            <Twitter size={16} className="text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-gray-900">Posted Tweets</h1>
            <p className="text-xs text-gray-500">History of all tweets posted to X</p>
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

      {/* Summary */}
      {data && data.posted > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
          {[
            { label: 'Total Posted', value: data.posted, color: 'text-gray-900' },
            { label: 'Singles', value: singles, color: 'text-blue-600' },
            { label: 'Threads', value: threads, color: 'text-violet-600' },
            { label: 'Total Likes', value: totalLikes, color: 'text-red-500' },
            { label: 'Impressions', value: totalImpressions, color: 'text-emerald-600' },
          ].map(s => (
            <div key={s.label} className="card p-3 text-center">
              <p className="text-[10px] font-medium text-gray-500 uppercase tracking-wider">{s.label}</p>
              <p className={`text-xl font-bold ${s.color} mt-0.5`}>{s.value.toLocaleString()}</p>
            </div>
          ))}
        </div>
      )}

      {/* Posted Items */}
      {loading ? (
        <div className="flex items-center justify-center h-40">
          <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
        </div>
      ) : data && data.items.length > 0 ? (
        <div className="space-y-3">
          {data.items.map(item => (
            <div key={item.id} className="card p-4 hover:shadow-md transition-shadow">
              {/* Date & type */}
              <div className="flex items-center gap-2 mb-2">
                <Calendar size={11} className="text-gray-400" />
                <span className="text-[10px] text-gray-400">
                  {new Date(item.posted_at).toLocaleDateString('en-US', {
                    month: 'short', day: 'numeric', year: 'numeric',
                    hour: '2-digit', minute: '2-digit',
                  })}
                </span>
                <span className={`text-[9px] font-bold uppercase px-2 py-0.5 rounded-full ${
                  item.tweet_type === 'thread' ? 'bg-violet-100 text-violet-700' : 'bg-gray-100 text-gray-600'
                }`}>
                  {item.tweet_type}
                </span>
                {item.niche && item.niche !== 'manual' && (
                  <span className="text-[9px] px-2 py-0.5 rounded-full bg-blue-50 text-blue-600">
                    {item.niche}
                  </span>
                )}
              </div>

              {/* Content */}
              <p className="text-sm text-gray-800 leading-relaxed mb-3 whitespace-pre-wrap">{item.content}</p>

              {/* Metrics */}
              <div className="flex items-center gap-4 text-[11px] text-gray-500">
                <span className="flex items-center gap-1"><Eye size={11} /> {item.impressions.toLocaleString()}</span>
                <span className="flex items-center gap-1"><Heart size={11} className="text-red-400" /> {item.likes}</span>
                <span className="flex items-center gap-1"><MessageCircle size={11} /> {item.replies}</span>
                <span className="flex items-center gap-1"><Repeat2 size={11} className="text-emerald-500" /> {item.retweets}</span>

                {item.post_url && (
                  <a
                    href={item.post_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="ml-auto flex items-center gap-1 text-xs text-brand-600 hover:text-brand-700 font-medium"
                  >
                    View on X <ExternalLink size={10} />
                  </a>
                )}
                {!item.post_url && item.tweet_id && (
                  <a
                    href={`https://x.com/i/web/status/${item.tweet_id}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="ml-auto flex items-center gap-1 text-xs text-brand-600 hover:text-brand-700 font-medium"
                  >
                    View on X <ExternalLink size={10} />
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center h-48 gap-3 text-center">
          <Twitter size={28} className="text-gray-200" />
          <p className="text-sm text-gray-400">No posted tweets yet</p>
          <p className="text-xs text-gray-300">Generate and approve content to start posting</p>
          <Link href="/dashboard/twitter-engine" className="text-xs text-brand-600 font-semibold hover:underline">
            Go to Twitter Hub →
          </Link>
        </div>
      )}

    </div>
  )
}

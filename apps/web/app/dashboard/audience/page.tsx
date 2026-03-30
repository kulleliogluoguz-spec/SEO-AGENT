'use client'

import { useEffect, useState } from 'react'
import { Users, Target, Heart, Loader2, AlertCircle, Instagram, TrendingUp } from 'lucide-react'
import { apiFetch } from '@/lib/apiFetch'

interface AudienceSegment {
  segment_name: string
  size_estimate: string
  fit_score: number
  intent_score: number
  interests: string[]
  pain_points: string[]
  platforms: string[]
  content_angle: string
}

function ScoreBar({ value, color }: { value: number; color: string }) {
  const pct = Math.round(value * 100)
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-mono text-gray-500 w-7 text-right">{pct}%</span>
    </div>
  )
}

function SegmentCard({ seg, index }: { seg: AudienceSegment; index: number }) {
  const colors = [
    'from-violet-500/10 to-purple-500/10 border-violet-200',
    'from-blue-500/10 to-cyan-500/10 border-blue-200',
    'from-emerald-500/10 to-teal-500/10 border-emerald-200',
    'from-orange-500/10 to-amber-500/10 border-orange-200',
  ]
  const dotColors = ['bg-violet-500', 'bg-blue-500', 'bg-emerald-500', 'bg-orange-500']
  const color = colors[index % colors.length]
  const dot = dotColors[index % dotColors.length]

  return (
    <div className={`card p-5 bg-gradient-to-br ${color}`}>
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className={`w-2.5 h-2.5 rounded-full ${dot}`} />
          <h3 className="font-semibold text-gray-900 text-sm">{seg.segment_name}</h3>
        </div>
        {seg.size_estimate && (
          <span className="badge-gray text-[10px]">{seg.size_estimate}</span>
        )}
      </div>

      {/* Scores */}
      <div className="space-y-2 mb-4">
        <div>
          <div className="flex justify-between text-[10px] text-gray-400 mb-1">
            <span>Audience fit</span>
          </div>
          <ScoreBar value={seg.fit_score} color="bg-violet-500" />
        </div>
        <div>
          <div className="flex justify-between text-[10px] text-gray-400 mb-1">
            <span>Purchase intent</span>
          </div>
          <ScoreBar value={seg.intent_score} color="bg-emerald-500" />
        </div>
      </div>

      {/* Content angle */}
      <div className="bg-white/60 rounded-lg px-3 py-2 mb-3">
        <p className="text-[10px] text-gray-400 uppercase tracking-widest mb-0.5">Content angle</p>
        <p className="text-xs text-gray-700 font-medium leading-relaxed">{seg.content_angle}</p>
      </div>

      {/* Interests */}
      {seg.interests?.length > 0 && (
        <div className="mb-3">
          <p className="text-[10px] text-gray-400 uppercase tracking-widest mb-1.5">Interests</p>
          <div className="flex flex-wrap gap-1">
            {seg.interests.map((i) => (
              <span key={i} className="text-[10px] bg-white/70 border border-gray-200 px-2 py-0.5 rounded-full text-gray-600">
                {i}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Pain points */}
      {seg.pain_points?.length > 0 && (
        <div className="mb-3">
          <p className="text-[10px] text-gray-400 uppercase tracking-widest mb-1.5">Pain points</p>
          <div className="space-y-1">
            {seg.pain_points.slice(0, 3).map((p) => (
              <div key={p} className="flex items-start gap-1.5">
                <div className="w-1 h-1 rounded-full bg-red-400 mt-1.5 flex-shrink-0" />
                <span className="text-[11px] text-gray-600">{p}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Platforms */}
      {seg.platforms?.length > 0 && (
        <div className="flex items-center gap-1 flex-wrap">
          {seg.platforms.map((p) => (
            <span key={p} className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${
              p.toLowerCase().includes('instagram') ? 'bg-gradient-to-r from-pink-100 to-purple-100 text-purple-700' :
              p.toLowerCase().includes('tiktok') ? 'bg-black/5 text-gray-700' :
              'bg-blue-50 text-blue-700'
            }`}>
              {p}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

export default function AudiencePage() {
  const [segments, setSegments] = useState<AudienceSegment[]>([])
  const [niche, setNiche] = useState('')
  const [brandName, setBrandName] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    async function load() {
      try {
        const data = await apiFetch<{ segments: AudienceSegment[]; niche: string; brand_name: string }>('/api/v1/brand/audience')
        setSegments(data.segments ?? [])
        setNiche(data.niche ?? '')
        setBrandName(data.brand_name ?? '')
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : 'Failed to load audience data')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin text-brand-500" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-3">
        <AlertCircle className="w-8 h-8 text-red-400" />
        <p className="text-sm text-gray-500">{error}</p>
        <button onClick={() => window.location.reload()} className="btn-secondary text-xs">Retry</button>
      </div>
    )
  }

  const avgFit = segments.length > 0
    ? segments.reduce((s, seg) => s + seg.fit_score, 0) / segments.length
    : 0

  const topSegment = [...segments].sort((a, b) => b.fit_score - a.fit_score)[0]

  return (
    <div className="space-y-6">

      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Audience Intelligence</h1>
          <p className="page-subtitle">
            {brandName ? `${brandName} · ` : ''}{niche || 'Niche'} — Segment profiles
          </p>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-gray-500 bg-violet-50 border border-violet-100 px-3 py-1.5 rounded-lg">
          <Instagram size={12} className="text-violet-500" />
          Instagram-first targeting
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-4">
        <div className="card-stat">
          <p className="text-xs font-medium text-gray-400 uppercase tracking-widest">Segments</p>
          <p className="text-2xl font-bold text-gray-900 mt-1.5">{segments.length}</p>
          <p className="text-xs text-gray-400 mt-1">identified profiles</p>
        </div>
        <div className="card-stat">
          <p className="text-xs font-medium text-gray-400 uppercase tracking-widest">Avg Fit Score</p>
          <p className="text-2xl font-bold text-gray-900 mt-1.5">{Math.round(avgFit * 100)}%</p>
          <p className="text-xs text-emerald-600 mt-1 font-medium flex items-center gap-1">
            <TrendingUp size={10} /> Strong alignment
          </p>
        </div>
        <div className="card-stat">
          <p className="text-xs font-medium text-gray-400 uppercase tracking-widest">Best Segment</p>
          <p className="text-sm font-bold text-gray-900 mt-1.5 truncate">{topSegment?.segment_name ?? '—'}</p>
          <p className="text-xs text-gray-400 mt-1">
            {topSegment ? `${Math.round(topSegment.fit_score * 100)}% fit` : ''}
          </p>
        </div>
      </div>

      {/* Segments grid */}
      {segments.length === 0 ? (
        <div className="card flex flex-col items-center justify-center py-20 gap-4">
          <Users size={32} className="text-gray-200" />
          <div className="text-center">
            <p className="text-sm font-medium text-gray-500">No audience data yet</p>
            <p className="text-xs text-gray-400 mt-1">Complete onboarding to generate audience segments.</p>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {segments.map((seg, i) => (
            <SegmentCard key={i} seg={seg} index={i} />
          ))}
        </div>
      )}

    </div>
  )
}

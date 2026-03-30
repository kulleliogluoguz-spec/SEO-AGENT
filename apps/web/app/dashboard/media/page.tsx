'use client'

import { useEffect, useState } from 'react'
import {
  Radio, TrendingUp, DollarSign, Target, Zap,
  BarChart2, FlaskConical, Loader2, ChevronDown, ChevronUp
} from 'lucide-react'
import { apiFetch } from '@/lib/apiFetch'

interface Channel {
  channel: string
  priority: number
  budget_pct: number
  goal: string
  formats: string[]
  cpm_range: string
  audience_note: string
}

interface TestItem {
  test: string
  hypothesis: string
  duration: string
}

interface MediaPlan {
  primary_channels: Channel[]
  content_mix: { organic: number; paid: number }
  test_plan: TestItem[]
  monthly_budget_guide: Record<string, string>
  kpi_targets: Record<string, string>
  niche: string
  brand_name: string
}

const CHANNEL_COLORS: Record<string, string> = {
  Instagram: 'bg-pink-500',
  'Meta (Instagram + Facebook)': 'bg-pink-500',
  'Meta (Facebook)': 'bg-blue-600',
  'Meta (Retargeting)': 'bg-blue-500',
  LinkedIn: 'bg-blue-700',
  TikTok: 'bg-slate-900',
  YouTube: 'bg-red-600',
  Pinterest: 'bg-red-500',
  'Google Search': 'bg-blue-500',
  'Google (Search + Display)': 'bg-blue-500',
  'Google (Search + Maps)': 'bg-blue-500',
  'Google Shopping': 'bg-blue-500',
  'Content / SEO': 'bg-emerald-600',
  'Email / SMS': 'bg-violet-600',
  'Newsletter / Email': 'bg-violet-600',
}

function channelColor(name: string): string {
  for (const [key, cls] of Object.entries(CHANNEL_COLORS)) {
    if (name.toLowerCase().includes(key.toLowerCase()) || key.toLowerCase().includes(name.toLowerCase())) return cls
  }
  return 'bg-gray-500'
}

function DonutChart({ organic, paid }: { organic: number; paid: number }) {
  const r = 52
  const c = 2 * Math.PI * r
  const paidOffset = c - (paid / 100) * c

  return (
    <svg width="120" height="120" viewBox="0 0 120 120">
      <circle cx="60" cy="60" r={r} fill="none" stroke="#e2e8f0" strokeWidth="16" />
      <circle
        cx="60" cy="60" r={r}
        fill="none"
        stroke="#7c3aed"
        strokeWidth="16"
        strokeDasharray={c}
        strokeDashoffset={paidOffset}
        strokeLinecap="round"
        transform="rotate(-90 60 60)"
      />
      <text x="60" y="56" textAnchor="middle" fontSize="13" fontWeight="700" fill="#1e293b">{paid}%</text>
      <text x="60" y="70" textAnchor="middle" fontSize="9" fill="#94a3b8">paid</text>
    </svg>
  )
}

function ChannelCard({ ch }: { ch: Channel }) {
  const [open, setOpen] = useState(false)
  const color = channelColor(ch.channel)

  return (
    <div className="border border-gray-100 rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center gap-4 p-4 hover:bg-gray-50/60 transition-colors text-left"
      >
        <div className={`w-8 h-8 rounded-lg ${color} flex items-center justify-center flex-shrink-0`}>
          <Radio size={12} className="text-white" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm font-semibold text-gray-900">{ch.channel}</span>
            <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-gray-100 text-gray-500 font-medium">
              #{ch.priority}
            </span>
          </div>
          <p className="text-xs text-gray-500 truncate">{ch.goal}</p>
        </div>
        <div className="text-right flex-shrink-0">
          <p className="text-lg font-bold text-gray-900">{ch.budget_pct}%</p>
          <p className="text-[10px] text-gray-400">of budget</p>
        </div>
        <div className="text-gray-300">
          {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </div>
      </button>

      {open && (
        <div className="px-4 pb-4 pt-0 border-t border-gray-50 bg-gray-50/30">
          <div className="grid grid-cols-2 gap-4 mt-3">
            <div>
              <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-1.5">Ad Formats</p>
              <div className="flex flex-wrap gap-1">
                {ch.formats.map(f => (
                  <span key={f} className="text-[10px] bg-white border border-gray-200 text-gray-600 px-2 py-0.5 rounded-full">{f}</span>
                ))}
              </div>
            </div>
            <div>
              <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-1.5">CPM / CPC Range</p>
              <p className="text-sm font-semibold text-gray-800">{ch.cpm_range}</p>
            </div>
          </div>
          <div className="mt-3">
            <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-1">Audience Targeting</p>
            <p className="text-xs text-gray-600">{ch.audience_note}</p>
          </div>
        </div>
      )}
    </div>
  )
}

export default function MediaPlanPage() {
  const [plan, setPlan] = useState<MediaPlan | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    async function load() {
      try {
        const data = await apiFetch<{ media_plan: any }>('/api/v1/brand/media-plan')
        setPlan(data.media_plan)
      } catch {
        setError('No brand profile found. Complete onboarding first.')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-48 gap-2 text-gray-400">
        <Loader2 size={18} className="animate-spin" />
        <span className="text-sm">Loading media plan…</span>
      </div>
    )
  }

  if (error || !plan) {
    return (
      <div className="card p-10 text-center">
        <BarChart2 size={32} className="mx-auto text-gray-200 mb-3" />
        <p className="text-gray-500 text-sm">{error || 'No media plan available.'}</p>
      </div>
    )
  }

  const totalBudgetCheck = plan.primary_channels.reduce((s, c) => s + c.budget_pct, 0)

  return (
    <div className="space-y-6 max-w-4xl">

      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title flex items-center gap-2">
            <BarChart2 size={18} className="text-violet-500" />
            Media Planning
          </h1>
          <p className="page-subtitle">
            {plan.brand_name} · {plan.niche} — niche-calibrated channel strategy and budget guidance
          </p>
        </div>
      </div>

      {/* KPI + Budget row */}
      <div className="grid grid-cols-2 gap-4">
        {/* Budget guide */}
        <div className="card p-5">
          <div className="flex items-center gap-2 mb-4">
            <DollarSign size={14} className="text-emerald-500" />
            <h2 className="section-title">Monthly Budget Guide</h2>
          </div>
          <div className="space-y-2">
            {Object.entries(plan.monthly_budget_guide).map(([tier, range]) => (
              <div key={tier} className="flex items-center justify-between py-1.5 border-b border-gray-50 last:border-0">
                <span className="text-sm font-medium text-gray-600 capitalize">{tier}</span>
                <span className="text-sm font-bold text-gray-900">{range}</span>
              </div>
            ))}
          </div>
        </div>

        {/* KPI targets */}
        <div className="card p-5">
          <div className="flex items-center gap-2 mb-4">
            <Target size={14} className="text-brand-500" />
            <h2 className="section-title">Target KPIs</h2>
          </div>
          <div className="space-y-2">
            {Object.entries(plan.kpi_targets).map(([key, val]) => (
              <div key={key} className="flex items-center justify-between py-1.5 border-b border-gray-50 last:border-0">
                <span className="text-sm font-medium text-gray-600 uppercase text-xs tracking-wide">{key.toUpperCase()}</span>
                <span className="text-sm font-bold text-gray-900">{val}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Content mix + Budget allocation */}
      <div className="grid grid-cols-3 gap-4">
        {/* Donut */}
        <div className="card p-5 flex flex-col items-center justify-center text-center">
          <DonutChart organic={plan.content_mix.organic} paid={plan.content_mix.paid} />
          <p className="text-sm font-semibold text-gray-900 mt-2">Content Mix</p>
          <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-violet-500 inline-block" />{plan.content_mix.paid}% Paid</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-slate-200 inline-block" />{plan.content_mix.organic}% Organic</span>
          </div>
        </div>

        {/* Budget bars */}
        <div className="col-span-2 card p-5">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp size={14} className="text-violet-500" />
            <h2 className="section-title">Budget Allocation</h2>
          </div>
          <div className="space-y-3">
            {plan.primary_channels.map(ch => {
              const color = channelColor(ch.channel)
              return (
                <div key={ch.channel}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-medium text-gray-700">{ch.channel}</span>
                    <span className="text-xs font-semibold text-gray-900">{ch.budget_pct}%</span>
                  </div>
                  <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full ${color} rounded-full`}
                      style={{ width: `${ch.budget_pct}%` }}
                    />
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {/* Channel breakdown */}
      <div className="card p-5">
        <div className="flex items-center gap-2 mb-4">
          <Radio size={14} className="text-violet-500" />
          <h2 className="section-title">Channel Playbook</h2>
          <span className="badge-purple text-[10px]">{plan.primary_channels.length} channels</span>
        </div>
        <div className="space-y-2">
          {plan.primary_channels.map(ch => (
            <ChannelCard key={ch.channel} ch={ch} />
          ))}
        </div>
      </div>

      {/* Test plan */}
      <div className="card p-5">
        <div className="flex items-center gap-2 mb-4">
          <FlaskConical size={14} className="text-amber-500" />
          <h2 className="section-title">A/B Test Plan</h2>
          <span className="badge-yellow text-[10px]">Run these first</span>
        </div>
        <div className="space-y-3">
          {plan.test_plan.map((t, i) => (
            <div key={i} className="flex items-start gap-4 p-4 bg-amber-50/50 border border-amber-100 rounded-xl">
              <div className="w-6 h-6 rounded-full bg-amber-500 text-white text-[10px] font-bold flex items-center justify-center flex-shrink-0 mt-0.5">
                {i + 1}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-gray-900 mb-0.5">{t.test}</p>
                <p className="text-xs text-gray-500 italic mb-1.5">"{t.hypothesis}"</p>
                <div className="flex items-center gap-1">
                  <Zap size={10} className="text-amber-500" />
                  <span className="text-[10px] text-amber-700 font-medium">Run for {t.duration}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

    </div>
  )
}

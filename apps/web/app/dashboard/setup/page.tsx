'use client'

import { useState, useCallback } from 'react'
import {
  Instagram, Globe, ArrowRight, ArrowLeft, CheckCircle2,
  Loader2, Zap, Flame, FileText, MonitorPlay, ShieldCheck,
  Play, TrendingUp, Target, Cpu, Sparkles, AlertCircle,
  ChevronRight, Twitter, ExternalLink, DollarSign, Users
} from 'lucide-react'
import Link from 'next/link'
import { apiFetch } from '@/lib/apiFetch'

// ── Types ─────────────────────────────────────────────────────────────────────

interface BrandInputs {
  brand_name: string
  website_url: string
  instagram_handle: string
  x_handle: string
  tiktok_handle: string
  primary_goal: string
  monthly_budget_usd: string
  category: string
  target_audience: string
}

interface ActivationResult {
  brand_profile: Record<string, unknown>
  niche: string
  niche_confidence: number
  growth_stage: {
    stage: string
    description: string
    next_milestone: string
    cold_start_content_mix: Record<string, number> | null
    posting_cadence_per_week: number
  }
  live_trends: Array<{ keyword: string; momentum_score: number; source: string }>
  content_ideas: Array<{
    topic: string
    content_type: string
    objective: string
    action_hint: string
    momentum_score: number
  }>
  campaign_angles: Array<{
    headline: string
    objective: string
    suggested_budget_usd: number
    platform: string
  }>
  channels_connected: string[]
  recommended_autonomy_mode: string
  growth_plan_summary: {
    goal: string
    stage: string
    posting_cadence_per_week: number
    paid_enabled: boolean
    monthly_budget_usd: number | null
    top_opportunity: string
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

const GOALS = [
  { id: 'grow_followers', label: 'Grow Followers', icon: Users, description: 'Build a larger, engaged social audience' },
  { id: 'drive_traffic', label: 'Drive Traffic', icon: Globe, description: 'Bring more visitors to your website' },
  { id: 'increase_sales', label: 'Increase Sales', icon: DollarSign, description: 'Convert attention into revenue' },
  { id: 'build_awareness', label: 'Build Awareness', icon: Zap, description: 'Establish brand presence in your niche' },
]

const NICHE_LABELS: Record<string, string> = {
  tech: 'Technology / SaaS',
  fashion: 'Fashion & Apparel',
  food: 'Food & Beverage',
  fitness: 'Fitness & Health',
  travel: 'Travel & Tourism',
  ecommerce: 'E-Commerce & Retail',
  creator: 'Creator & Media',
  beauty: 'Beauty & Skincare',
  b2b: 'B2B & Professional Services',
  wellness: 'Wellness & Mental Health',
  general: 'General',
}

const STAGE_COLORS: Record<string, string> = {
  cold_start: 'text-amber-600 bg-amber-50 border-amber-200',
  growing: 'text-blue-600 bg-blue-50 border-blue-200',
  optimizing: 'text-emerald-600 bg-emerald-50 border-emerald-200',
}

const CONTENT_TYPE_LABELS: Record<string, string> = {
  reel_script: 'Reel Script', carousel: 'Carousel', caption: 'Caption',
  ad_copy: 'Ad Copy', story: 'Story',
}

const AUTONOMY_MODES = [
  { id: 'manual', label: 'Manual', desc: 'Everything requires your approval', color: 'border-amber-300 text-amber-700 bg-amber-50' },
  { id: 'assisted', label: 'Assisted', desc: 'Drafts auto-created, you approve', color: 'border-blue-300 text-blue-700 bg-blue-50' },
  { id: 'semi_auto', label: 'Semi-Auto', desc: 'Content auto-schedules, ads need approval', color: 'border-violet-300 text-violet-700 bg-violet-50' },
  { id: 'autonomous', label: 'Autonomous', desc: 'Platform acts within your budget limits', color: 'border-emerald-300 text-emerald-700 bg-emerald-50' },
]


// ── Step components ───────────────────────────────────────────────────────────

function StepBrandInputs({
  inputs, onChange, onNext
}: {
  inputs: BrandInputs
  onChange: (k: keyof BrandInputs, v: string) => void
  onNext: () => void
}) {
  const canNext = inputs.brand_name.trim().length >= 2 && inputs.primary_goal

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-gray-900">Tell us about your brand</h2>
        <p className="text-sm text-gray-500 mt-1">Connect your accounts so the Growth Engine can start learning.</p>
      </div>

      <div className="grid grid-cols-1 gap-4">
        <div>
          <label className="block text-xs font-semibold text-gray-700 mb-1.5">Brand Name *</label>
          <input
            type="text"
            value={inputs.brand_name}
            onChange={e => onChange('brand_name', e.target.value)}
            placeholder="Your brand name"
            className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-500"
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1.5">
              <Instagram size={11} className="inline mr-1" />Instagram Handle
            </label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm">@</span>
              <input
                type="text"
                value={inputs.instagram_handle}
                onChange={e => onChange('instagram_handle', e.target.value.replace('@', ''))}
                placeholder="yourbrand"
                className="w-full pl-7 pr-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-500"
              />
            </div>
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1.5">
              <Twitter size={11} className="inline mr-1" />X / Twitter Handle
            </label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm">@</span>
              <input
                type="text"
                value={inputs.x_handle}
                onChange={e => onChange('x_handle', e.target.value.replace('@', ''))}
                placeholder="yourbrand"
                className="w-full pl-7 pr-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-500"
              />
            </div>
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1.5">TikTok Handle</label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm">@</span>
              <input
                type="text"
                value={inputs.tiktok_handle}
                onChange={e => onChange('tiktok_handle', e.target.value.replace('@', ''))}
                placeholder="yourbrand"
                className="w-full pl-7 pr-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-500"
              />
            </div>
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1.5">
              <Globe size={11} className="inline mr-1" />Website URL
            </label>
            <input
              type="url"
              value={inputs.website_url}
              onChange={e => onChange('website_url', e.target.value)}
              placeholder="https://yourbrand.com"
              className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-500"
            />
          </div>
        </div>

        <div>
          <label className="block text-xs font-semibold text-gray-700 mb-1.5">Primary Goal *</label>
          <div className="grid grid-cols-2 gap-2">
            {GOALS.map(g => (
              <button
                key={g.id}
                onClick={() => onChange('primary_goal', g.id)}
                className={`p-3 border rounded-xl text-left transition-all ${
                  inputs.primary_goal === g.id
                    ? 'border-brand-500 bg-brand-50 ring-2 ring-brand-500/20'
                    : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                }`}
              >
                <div className="flex items-center gap-2 mb-1">
                  <g.icon size={13} className={inputs.primary_goal === g.id ? 'text-brand-600' : 'text-gray-500'} />
                  <span className={`text-xs font-semibold ${inputs.primary_goal === g.id ? 'text-brand-700' : 'text-gray-700'}`}>
                    {g.label}
                  </span>
                </div>
                <p className="text-[10px] text-gray-500 leading-snug">{g.description}</p>
              </button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1.5">Monthly Ad Budget (optional)</label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm">$</span>
              <input
                type="number"
                value={inputs.monthly_budget_usd}
                onChange={e => onChange('monthly_budget_usd', e.target.value)}
                placeholder="0"
                min="0"
                className="w-full pl-7 pr-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-500"
              />
            </div>
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1.5">Target Audience (optional)</label>
            <input
              type="text"
              value={inputs.target_audience}
              onChange={e => onChange('target_audience', e.target.value)}
              placeholder="e.g. fitness enthusiasts 25-35"
              className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-500"
            />
          </div>
        </div>
      </div>

      <button
        onClick={onNext}
        disabled={!canNext}
        className="w-full btn-primary flex items-center justify-center gap-2 py-3 disabled:opacity-40"
      >
        Analyze Brand <ArrowRight size={14} />
      </button>
    </div>
  )
}

function StepDiscovery() {
  const steps = [
    { label: 'Saving brand profile', done: true },
    { label: 'Inferring niche and audience', done: true },
    { label: 'Fetching live trend signals', done: false },
    { label: 'Generating content ideas', done: false },
    { label: 'Building growth plan', done: false },
  ]
  return (
    <div className="space-y-6">
      <div className="text-center">
        <div className="w-16 h-16 bg-indigo-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
          <Cpu size={24} className="text-indigo-600 animate-pulse" />
        </div>
        <h2 className="text-xl font-bold text-gray-900">Analyzing your brand…</h2>
        <p className="text-sm text-gray-500 mt-1">Running intelligence layers. This takes ~5 seconds.</p>
      </div>
      <div className="space-y-3 max-w-sm mx-auto">
        {steps.map((step, i) => (
          <div key={i} className="flex items-center gap-3">
            {step.done
              ? <CheckCircle2 size={16} className="text-emerald-500 flex-shrink-0" />
              : <Loader2 size={16} className="text-brand-500 animate-spin flex-shrink-0" />
            }
            <span className={`text-sm ${step.done ? 'text-gray-600' : 'text-gray-800 font-medium'}`}>
              {step.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Main wizard ───────────────────────────────────────────────────────────────

const TOTAL_STEPS = 7

export default function SetupPage() {
  const [step, setStep] = useState(0)
  const [inputs, setInputs] = useState<BrandInputs>({
    brand_name: '', website_url: '', instagram_handle: '',
    x_handle: '', tiktok_handle: '', primary_goal: '',
    monthly_budget_usd: '', category: '', target_audience: '',
  })
  const [activating, setActivating] = useState(false)
  const [result, setResult] = useState<ActivationResult | null>(null)
  const [error, setError] = useState('')
  const [selectedAutonomy, setSelectedAutonomy] = useState('manual')
  const [autonomySaved, setAutonomySaved] = useState(false)

  const handleChange = useCallback((k: keyof BrandInputs, v: string) => {
    setInputs(prev => ({ ...prev, [k]: v }))
  }, [])

  async function handleActivate() {
    setActivating(true)
    setStep(1) // show discovery step
    setError('')
    try {
      const data = await apiFetch<ActivationResult>('/api/v1/brand/activate', {
        method: 'POST',
        body: JSON.stringify({
          brand_name: inputs.brand_name,
          website_url: inputs.website_url || undefined,
          instagram_handle: inputs.instagram_handle || undefined,
          x_handle: inputs.x_handle || undefined,
          tiktok_handle: inputs.tiktok_handle || undefined,
          primary_goal: inputs.primary_goal,
          monthly_budget_usd: inputs.monthly_budget_usd ? parseFloat(inputs.monthly_budget_usd) : undefined,
          category: inputs.category || undefined,
          target_audience: inputs.target_audience || undefined,
        }),
      })
      setResult(data)
      setSelectedAutonomy(data.recommended_autonomy_mode || 'manual')
      setStep(2) // jump to results
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Activation failed')
      setStep(0)
    } finally {
      setActivating(false)
    }
  }

  async function handleSaveAutonomy() {
    if (!result) return
    try {
      const channels = result.channels_connected.filter(c => ['instagram', 'x', 'tiktok'].includes(c))
      if (channels.length === 0) channels.push('instagram')
      for (const ch of channels) {
        await apiFetch(`/api/v1/autonomy/policies/${ch}`, {
          method: 'POST',
          body: JSON.stringify({ autonomy_mode: selectedAutonomy }),
        })
      }
      setAutonomySaved(true)
      setStep(6) // final step
    } catch {
      setStep(6) // proceed anyway
    }
  }

  const stageData = result?.growth_stage
  const stageBadge = stageData ? STAGE_COLORS[stageData.stage] ?? '' : ''

  return (
    <div className="max-w-2xl mx-auto">

      {/* Progress bar */}
      {step > 0 && step < 6 && (
        <div className="mb-8">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-gray-500 font-medium">
              Step {step} of {TOTAL_STEPS - 1}
            </span>
            <span className="text-xs text-gray-400">{Math.round((step / (TOTAL_STEPS - 1)) * 100)}% complete</span>
          </div>
          <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-brand-600 rounded-full transition-all duration-500"
              style={{ width: `${(step / (TOTAL_STEPS - 1)) * 100}%` }}
            />
          </div>
        </div>
      )}

      <div className="card p-8">

        {/* Step 0: Brand Inputs */}
        {step === 0 && (
          <>
            {error && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2">
                <AlertCircle size={14} className="text-red-500" />
                <p className="text-sm text-red-700">{error}</p>
              </div>
            )}
            <StepBrandInputs inputs={inputs} onChange={handleChange} onNext={handleActivate} />
          </>
        )}

        {/* Step 1: Discovery */}
        {step === 1 && <StepDiscovery />}

        {/* Step 2: Brand Understanding */}
        {step === 2 && result && (
          <div className="space-y-5">
            <div>
              <h2 className="text-xl font-bold text-gray-900">Brand Intelligence Ready</h2>
              <p className="text-sm text-gray-500 mt-1">Here's what we know about {result.brand_profile.brand_name as string}.</p>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="p-4 rounded-xl bg-gray-50 border border-gray-200">
                <p className="text-xs text-gray-500 mb-1">Niche Detected</p>
                <p className="text-base font-bold text-gray-900">{NICHE_LABELS[result.niche] ?? result.niche}</p>
                <p className="text-[10px] text-gray-400 mt-1">
                  {Math.round(result.niche_confidence * 100)}% confidence · inferred
                </p>
              </div>
              <div className={`p-4 rounded-xl border ${stageBadge}`}>
                <p className="text-xs font-medium mb-1 opacity-70">Growth Stage</p>
                <p className="text-base font-bold capitalize">{stageData?.stage.replace('_', ' ')}</p>
                <p className="text-[10px] mt-1 opacity-70">{stageData?.description}</p>
              </div>
            </div>

            {stageData?.cold_start_content_mix && (
              <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl">
                <div className="flex items-center gap-2 mb-2">
                  <Zap size={13} className="text-amber-500" />
                  <span className="text-xs font-semibold text-amber-700">Cold-Start Content Mix</span>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  {Object.entries(stageData.cold_start_content_mix).map(([type, pct]) => (
                    <div key={type} className="flex items-center justify-between">
                      <span className="text-xs text-amber-700 capitalize">{type.replace('_', ' ')}</span>
                      <span className="text-xs font-bold text-amber-800">{Math.round(pct * 100)}%</span>
                    </div>
                  ))}
                </div>
                <p className="text-[10px] text-amber-600 mt-2">
                  Recommended posting cadence: {stageData.posting_cadence_per_week}× per week
                </p>
              </div>
            )}

            <div className="flex items-center gap-2">
              <div className="flex gap-2 flex-wrap">
                {result.channels_connected.map(ch => (
                  <span key={ch} className="px-2 py-1 rounded-full bg-gray-100 text-xs text-gray-600 font-medium">
                    {ch}
                  </span>
                ))}
              </div>
            </div>

            <button onClick={() => setStep(3)} className="w-full btn-primary flex items-center justify-center gap-2 py-3">
              View Trend Alignment <ArrowRight size={14} />
            </button>
          </div>
        )}

        {/* Step 3: Trend Alignment */}
        {step === 3 && result && (
          <div className="space-y-5">
            <div>
              <h2 className="text-xl font-bold text-gray-900">Trend Alignment</h2>
              <p className="text-sm text-gray-500 mt-1">
                Live trends in your niche right now.
              </p>
            </div>

            <div className="space-y-2">
              {result.live_trends.slice(0, 6).map((t, i) => (
                <div key={i} className="flex items-center gap-3 p-3 rounded-lg bg-gray-50 border border-gray-100">
                  <span className="text-xs text-gray-300 w-4 font-mono">{i + 1}</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-800 truncate">{t.keyword}</p>
                    <p className="text-[10px] text-gray-400">{t.source}</p>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <div className="w-16 h-1.5 rounded-full bg-gray-200 overflow-hidden">
                      <div
                        className="h-full bg-orange-400 rounded-full"
                        style={{ width: `${Math.round(t.momentum_score * 100)}%` }}
                      />
                    </div>
                    <span className="text-[10px] font-semibold text-orange-600 w-7 text-right">
                      {Math.round(t.momentum_score * 100)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>

            <div className="flex gap-3">
              <button onClick={() => setStep(2)} className="btn-secondary flex items-center gap-1">
                <ArrowLeft size={13} /> Back
              </button>
              <button onClick={() => setStep(4)} className="flex-1 btn-primary flex items-center justify-center gap-2">
                See Growth Plan <ArrowRight size={14} />
              </button>
            </div>
          </div>
        )}

        {/* Step 4: Growth Plan + Content Preview */}
        {step === 4 && result && (
          <div className="space-y-5">
            <div>
              <h2 className="text-xl font-bold text-gray-900">Your Growth Plan</h2>
              <p className="text-sm text-gray-500 mt-1">AI-generated execution plan based on your brand and trends.</p>
            </div>

            {/* Plan summary */}
            <div className="p-4 bg-slate-900 rounded-xl text-white space-y-2">
              <div className="flex items-center gap-2 mb-3">
                <Cpu size={13} className="text-indigo-400" />
                <span className="text-xs font-semibold text-indigo-300 uppercase tracking-wider">Growth Plan</span>
              </div>
              {[
                { label: 'Goal', value: result.growth_plan_summary.goal.replace(/_/g, ' ') },
                { label: 'Stage', value: result.growth_plan_summary.stage.replace(/_/g, ' ') },
                { label: 'Posting cadence', value: `${result.growth_plan_summary.posting_cadence_per_week}× / week` },
                { label: 'Paid campaigns', value: result.growth_plan_summary.paid_enabled ? `$${result.growth_plan_summary.monthly_budget_usd}/mo` : 'Not configured' },
                { label: 'Top opportunity', value: result.growth_plan_summary.top_opportunity || 'See recommendations' },
              ].map(row => (
                <div key={row.label} className="flex items-start justify-between gap-2">
                  <span className="text-xs text-slate-400">{row.label}</span>
                  <span className="text-xs text-white font-medium text-right capitalize">{row.value}</span>
                </div>
              ))}
            </div>

            {/* Content ideas */}
            <div>
              <p className="text-xs font-semibold text-gray-700 mb-2">Content ideas from trends</p>
              <div className="space-y-2">
                {result.content_ideas.slice(0, 4).map((idea, i) => (
                  <div key={i} className="flex items-start gap-2 p-3 rounded-lg border border-gray-200 bg-gray-50">
                    <FileText size={13} className="text-violet-500 mt-0.5 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-800 truncate">{idea.topic}</p>
                      <div className="flex gap-1.5 mt-0.5">
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-violet-100 text-violet-600">
                          {CONTENT_TYPE_LABELS[idea.content_type] ?? idea.content_type}
                        </span>
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-200 text-gray-500">
                          {idea.objective}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex gap-3">
              <button onClick={() => setStep(3)} className="btn-secondary flex items-center gap-1">
                <ArrowLeft size={13} /> Back
              </button>
              <button onClick={() => setStep(5)} className="flex-1 btn-primary flex items-center justify-center gap-2">
                Set Autonomy <ArrowRight size={14} />
              </button>
            </div>
          </div>
        )}

        {/* Step 5: Autonomy Settings */}
        {step === 5 && result && (
          <div className="space-y-5">
            <div>
              <h2 className="text-xl font-bold text-gray-900">Autonomy Settings</h2>
              <p className="text-sm text-gray-500 mt-1">
                Choose how much the platform should act on your behalf.
                {result.recommended_autonomy_mode !== 'manual' && (
                  <span className="text-brand-600 font-medium"> Recommended: {result.recommended_autonomy_mode.replace('_', ' ')}.</span>
                )}
              </p>
            </div>

            <div className="space-y-2.5">
              {AUTONOMY_MODES.map(mode => (
                <button
                  key={mode.id}
                  onClick={() => setSelectedAutonomy(mode.id)}
                  className={`w-full p-4 border-2 rounded-xl text-left transition-all ${
                    selectedAutonomy === mode.id
                      ? `${mode.color} ring-2 ring-offset-1 ring-current/20`
                      : 'border-gray-200 hover:border-gray-300 bg-white'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className={`text-sm font-bold ${selectedAutonomy === mode.id ? '' : 'text-gray-800'}`}>
                          {mode.label}
                        </span>
                        {mode.id === result.recommended_autonomy_mode && (
                          <span className="text-[9px] px-1.5 py-0.5 rounded font-bold bg-brand-100 text-brand-700 uppercase tracking-wide">
                            Recommended
                          </span>
                        )}
                      </div>
                      <p className={`text-xs mt-0.5 ${selectedAutonomy === mode.id ? 'opacity-80' : 'text-gray-500'}`}>
                        {mode.desc}
                      </p>
                    </div>
                    {selectedAutonomy === mode.id && <CheckCircle2 size={16} className="flex-shrink-0" />}
                  </div>
                </button>
              ))}
            </div>

            <div className="p-3 bg-gray-50 border border-gray-200 rounded-lg">
              <p className="text-xs text-gray-500">
                <ShieldCheck size={11} className="inline mr-1 text-gray-400" />
                You can change this anytime in Settings. Budget caps and approval thresholds are always configurable.
              </p>
            </div>

            <div className="flex gap-3">
              <button onClick={() => setStep(4)} className="btn-secondary flex items-center gap-1">
                <ArrowLeft size={13} /> Back
              </button>
              <button
                onClick={handleSaveAutonomy}
                className="flex-1 btn-primary flex items-center justify-center gap-2 py-3"
              >
                <Play size={14} />
                Activate Growth Engine
              </button>
            </div>
          </div>
        )}

        {/* Step 6: Activation Complete */}
        {step === 6 && result && (
          <div className="text-center space-y-6">
            <div className="w-16 h-16 bg-emerald-100 rounded-2xl flex items-center justify-center mx-auto">
              <CheckCircle2 size={28} className="text-emerald-600" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-gray-900">Growth Engine Active</h2>
              <p className="text-sm text-gray-500 mt-2">
                {result.brand_profile.brand_name as string} is set up in{' '}
                <span className="font-semibold">{NICHE_LABELS[result.niche] ?? result.niche}</span> niche,{' '}
                mode: <span className="font-semibold capitalize">{selectedAutonomy.replace('_', ' ')}</span>.
              </p>
            </div>

            <div className="grid grid-cols-3 gap-3 text-left">
              <div className="p-3 bg-gray-50 rounded-xl border">
                <p className="text-[10px] text-gray-400 mb-1">Trends tracked</p>
                <p className="text-lg font-bold text-gray-900">{result.live_trends.length}</p>
              </div>
              <div className="p-3 bg-gray-50 rounded-xl border">
                <p className="text-[10px] text-gray-400 mb-1">Content ideas</p>
                <p className="text-lg font-bold text-gray-900">{result.content_ideas.length}</p>
              </div>
              <div className="p-3 bg-gray-50 rounded-xl border">
                <p className="text-[10px] text-gray-400 mb-1">Channels</p>
                <p className="text-lg font-bold text-gray-900">{result.channels_connected.length}</p>
              </div>
            </div>

            <div className="space-y-2">
              <Link
                href="/dashboard/growth"
                className="w-full btn-primary flex items-center justify-center gap-2 py-3 text-sm"
              >
                <Cpu size={14} />
                Open Growth Engine
              </Link>
              <Link
                href="/dashboard"
                className="w-full btn-secondary flex items-center justify-center gap-2 py-2.5 text-sm"
              >
                <ArrowRight size={13} />
                Go to Command Center
              </Link>
            </div>
          </div>
        )}

      </div>
    </div>
  )
}

'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  Instagram,
  Globe,
  Target,
  Sparkles,
  ChevronRight,
  ChevronLeft,
  Check,
  Loader2,
} from 'lucide-react'

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

const CATEGORIES = [
  'Fashion & Style',
  'Beauty & Skincare',
  'Food & Beverage',
  'Health & Fitness',
  'Travel & Lifestyle',
  'Technology & SaaS',
  'Home & Interior',
  'Education & Coaching',
  'Finance & Investing',
  'Arts & Entertainment',
  'E-commerce & Retail',
  'Professional Services',
]

const GOALS = [
  'Grow Instagram followers',
  'Drive website traffic',
  'Increase product sales',
  'Build email list',
  'Generate brand awareness',
  'Establish thought leadership',
]

const GEOS = [
  'Global',
  'United States',
  'United Kingdom',
  'Europe',
  'APAC',
  'Latin America',
  'Middle East & Africa',
]

interface FormData {
  instagram_handle: string
  brand_name: string
  website_url: string
  description: string
  category: string
  target_audience: string
  geography: string
  business_goal: string
}

const EMPTY: FormData = {
  instagram_handle: '',
  brand_name: '',
  website_url: '',
  description: '',
  category: '',
  target_audience: '',
  geography: '',
  business_goal: '',
}

export default function OnboardingPage() {
  const router = useRouter()
  const [step, setStep] = useState(1)
  const [form, setForm] = useState<FormData>(EMPTY)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const set = (key: keyof FormData, value: string) =>
    setForm((f) => ({ ...f, [key]: value }))

  const canNext = () => {
    if (step === 1) return form.brand_name.trim().length > 0
    if (step === 2) return form.category.length > 0
    return true
  }

  const handleSubmit = async () => {
    setSaving(true)
    setError('')
    try {
      const token = localStorage.getItem('access_token')
      const res = await fetch(`${API}/api/v1/brand/profile`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          instagram_handle: form.instagram_handle || null,
          brand_name: form.brand_name,
          website_url: form.website_url || null,
          description: form.description || null,
          category: form.category || null,
          target_audience: form.target_audience || null,
          geography: form.geography || null,
          business_goal: form.business_goal || null,
        }),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.detail ?? 'Failed to save profile')
      }
      setStep(4)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
      <div className="w-full max-w-xl">
        {/* Progress */}
        {step < 4 && (
          <div className="mb-8">
            <div className="flex items-center gap-2 mb-3">
              {[1, 2, 3].map((s) => (
                <div key={s} className="flex items-center gap-2">
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold transition-all ${
                      s < step
                        ? 'bg-violet-600 text-white'
                        : s === step
                        ? 'bg-violet-500 text-white ring-2 ring-violet-400 ring-offset-2 ring-offset-slate-950'
                        : 'bg-slate-800 text-slate-500'
                    }`}
                  >
                    {s < step ? <Check className="w-4 h-4" /> : s}
                  </div>
                  {s < 3 && (
                    <div
                      className={`h-0.5 w-16 transition-all ${
                        s < step ? 'bg-violet-600' : 'bg-slate-800'
                      }`}
                    />
                  )}
                </div>
              ))}
            </div>
            <p className="text-xs text-slate-500">
              {step === 1 && 'Identity — who are you?'}
              {step === 2 && 'Business context — what do you do?'}
              {step === 3 && 'Goals — what matters most?'}
            </p>
          </div>
        )}

        {/* Card */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 shadow-2xl">
          {/* ── Step 1: Identity ─────────────────────────────────────────── */}
          {step === 1 && (
            <div className="space-y-6">
              <div>
                <div className="w-10 h-10 bg-gradient-to-br from-violet-600 to-pink-600 rounded-xl flex items-center justify-center mb-4">
                  <Instagram className="w-5 h-5 text-white" />
                </div>
                <h1 className="text-2xl font-bold text-white mb-1">Set up your brand</h1>
                <p className="text-slate-400 text-sm">
                  Your Instagram account becomes the central hub for all growth intelligence.
                </p>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1.5">
                    Brand name <span className="text-red-400">*</span>
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Acme Coffee"
                    value={form.brand_name}
                    onChange={(e) => set('brand_name', e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2.5 text-white placeholder-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1.5">
                    Instagram handle
                  </label>
                  <div className="relative">
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 text-sm">@</span>
                    <input
                      type="text"
                      placeholder="yourbrand"
                      value={form.instagram_handle}
                      onChange={(e) =>
                        set('instagram_handle', e.target.value.replace(/^@/, ''))
                      }
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-7 pr-3 py-2.5 text-white placeholder-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1.5">
                    Website <span className="text-slate-500">(optional)</span>
                  </label>
                  <div className="relative">
                    <Globe className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                    <input
                      type="url"
                      placeholder="https://yourbrand.com"
                      value={form.website_url}
                      onChange={(e) => set('website_url', e.target.value)}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-9 pr-3 py-2.5 text-white placeholder-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1.5">
                    Short description <span className="text-slate-500">(optional)</span>
                  </label>
                  <textarea
                    placeholder="What does your brand do?"
                    value={form.description}
                    onChange={(e) => set('description', e.target.value)}
                    rows={3}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2.5 text-white placeholder-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent resize-none"
                  />
                </div>
              </div>
            </div>
          )}

          {/* ── Step 2: Business Context ──────────────────────────────────── */}
          {step === 2 && (
            <div className="space-y-6">
              <div>
                <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-cyan-600 rounded-xl flex items-center justify-center mb-4">
                  <Target className="w-5 h-5 text-white" />
                </div>
                <h1 className="text-2xl font-bold text-white mb-1">Business context</h1>
                <p className="text-slate-400 text-sm">
                  This helps us generate niche-specific intelligence for{' '}
                  <span className="text-white font-medium">{form.brand_name}</span>.
                </p>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Category <span className="text-red-400">*</span>
                  </label>
                  <div className="grid grid-cols-2 gap-2">
                    {CATEGORIES.map((c) => (
                      <button
                        key={c}
                        onClick={() => set('category', c)}
                        className={`text-left px-3 py-2 rounded-lg text-sm border transition-all ${
                          form.category === c
                            ? 'bg-violet-600/20 border-violet-500 text-violet-300'
                            : 'bg-slate-800 border-slate-700 text-slate-400 hover:border-slate-600 hover:text-slate-300'
                        }`}
                      >
                        {c}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1.5">
                    Target audience <span className="text-slate-500">(optional)</span>
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Women 25-40 interested in wellness"
                    value={form.target_audience}
                    onChange={(e) => set('target_audience', e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2.5 text-white placeholder-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent"
                  />
                </div>
              </div>
            </div>
          )}

          {/* ── Step 3: Goals ────────────────────────────────────────────── */}
          {step === 3 && (
            <div className="space-y-6">
              <div>
                <div className="w-10 h-10 bg-gradient-to-br from-emerald-600 to-teal-600 rounded-xl flex items-center justify-center mb-4">
                  <Sparkles className="w-5 h-5 text-white" />
                </div>
                <h1 className="text-2xl font-bold text-white mb-1">Platform activation</h1>
                <p className="text-slate-400 text-sm">
                  Set your primary growth goal and geographic focus.
                </p>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Primary goal
                  </label>
                  <div className="space-y-2">
                    {GOALS.map((g) => (
                      <button
                        key={g}
                        onClick={() => set('business_goal', g)}
                        className={`w-full text-left px-4 py-2.5 rounded-lg text-sm border flex items-center gap-3 transition-all ${
                          form.business_goal === g
                            ? 'bg-emerald-600/20 border-emerald-500 text-emerald-300'
                            : 'bg-slate-800 border-slate-700 text-slate-400 hover:border-slate-600 hover:text-slate-300'
                        }`}
                      >
                        <div
                          className={`w-4 h-4 rounded-full border-2 flex items-center justify-center flex-shrink-0 ${
                            form.business_goal === g
                              ? 'border-emerald-500 bg-emerald-500'
                              : 'border-slate-600'
                          }`}
                        >
                          {form.business_goal === g && (
                            <div className="w-1.5 h-1.5 rounded-full bg-white" />
                          )}
                        </div>
                        {g}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Geography
                  </label>
                  <div className="flex flex-wrap gap-2">
                    {GEOS.map((g) => (
                      <button
                        key={g}
                        onClick={() => set('geography', g)}
                        className={`px-3 py-1.5 rounded-lg text-sm border transition-all ${
                          form.geography === g
                            ? 'bg-blue-600/20 border-blue-500 text-blue-300'
                            : 'bg-slate-800 border-slate-700 text-slate-400 hover:border-slate-600 hover:text-slate-300'
                        }`}
                      >
                        {g}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {error && (
                <p className="text-red-400 text-sm bg-red-900/20 border border-red-800 rounded-lg px-3 py-2">
                  {error}
                </p>
              )}
            </div>
          )}

          {/* ── Step 4: Confirmation ─────────────────────────────────────── */}
          {step === 4 && (
            <div className="text-center space-y-6">
              <div className="w-16 h-16 bg-gradient-to-br from-violet-600 to-pink-600 rounded-2xl flex items-center justify-center mx-auto">
                <Check className="w-8 h-8 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-white mb-2">
                  {form.brand_name} is ready
                </h1>
                <p className="text-slate-400 text-sm leading-relaxed">
                  Your brand profile has been created. The intelligence engine has loaded
                  niche-specific trends, audience segments, and growth recommendations for your
                  account.
                </p>
              </div>

              <div className="bg-slate-800 rounded-xl p-4 text-left space-y-2">
                {[
                  'Trend feed calibrated to your niche',
                  'Audience segment profiles generated',
                  'Top 6 growth recommendations ready',
                  'GEO/SEO signals analyzed',
                  'Content opportunity themes identified',
                ].map((item) => (
                  <div key={item} className="flex items-center gap-2 text-sm text-slate-300">
                    <Check className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                    {item}
                  </div>
                ))}
              </div>

              <button
                onClick={() => router.push('/dashboard')}
                className="w-full bg-violet-600 hover:bg-violet-500 text-white font-semibold py-3 rounded-xl transition-colors"
              >
                Enter dashboard
              </button>
            </div>
          )}

          {/* ── Navigation ───────────────────────────────────────────────── */}
          {step < 4 && (
            <div className="flex items-center justify-between mt-8 pt-6 border-t border-slate-800">
              <button
                onClick={() => setStep((s) => s - 1)}
                disabled={step === 1}
                className="flex items-center gap-1.5 text-sm text-slate-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronLeft className="w-4 h-4" />
                Back
              </button>

              {step < 3 ? (
                <button
                  onClick={() => setStep((s) => s + 1)}
                  disabled={!canNext()}
                  className="flex items-center gap-1.5 bg-violet-600 hover:bg-violet-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-semibold px-5 py-2 rounded-lg transition-colors"
                >
                  Continue
                  <ChevronRight className="w-4 h-4" />
                </button>
              ) : (
                <button
                  onClick={handleSubmit}
                  disabled={saving}
                  className="flex items-center gap-1.5 bg-violet-600 hover:bg-violet-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-semibold px-5 py-2 rounded-lg transition-colors"
                >
                  {saving ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Saving…
                    </>
                  ) : (
                    <>
                      Launch platform
                      <Sparkles className="w-4 h-4" />
                    </>
                  )}
                </button>
              )}
            </div>
          )}
        </div>

        {/* Footer hint */}
        {step < 4 && (
          <p className="text-center text-xs text-slate-600 mt-4">
            You can update your brand profile at any time from the dashboard.
          </p>
        )}
      </div>
    </div>
  )
}

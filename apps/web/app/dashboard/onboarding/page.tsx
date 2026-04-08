'use client'

import { useEffect, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import {
  ArrowRight,
  Building2,
  CheckCircle,
  DollarSign,
  Link2,
} from 'lucide-react'
import { apiFetch } from '@/lib/apiFetch'

type Connection = { id: string; platform: 'meta' | 'google' }

const STEPS = [
  { num: 1, title: 'Company Info', icon: Building2 },
  { num: 2, title: 'Ad Accounts', icon: Link2 },
  { num: 3, title: 'Cost Settings', icon: DollarSign },
  { num: 4, title: 'Ready!', icon: CheckCircle },
]

export default function OnboardingWizard() {
  const router = useRouter()
  const [step, setStep] = useState(1)
  const [saving, setSaving] = useState(false)
  const [connections, setConnections] = useState<Connection[]>([])
  const [form, setForm] = useState({
    company_name: '',
    industry: '',
    monthly_ad_budget: '',
    default_currency: 'USD',
    cogs_per_unit: '',
    shipping_cost: '',
    return_rate: '5',
    avg_order_value: '',
  })

  const loadStatus = useCallback(async () => {
    try {
      const status = await apiFetch<{
        setup_step?: number
        setup_completed?: boolean
      }>('/api/v1/workspace/setup-status')
      if (status.setup_completed) {
        router.push('/dashboard')
        return
      }
      if (status.setup_step) setStep(status.setup_step)
    } catch (e) {
      console.error(e)
    }

    try {
      const c = await apiFetch<{ connections: Connection[] }>(
        '/api/v1/integrations/connections',
      )
      setConnections(c.connections ?? [])
    } catch (e) {
      console.error(e)
    }
  }, [router])

  useEffect(() => {
    loadStatus()
  }, [loadStatus])

  const update = (k: string, v: string) =>
    setForm((f) => ({ ...f, [k]: v }))

  async function saveStep1() {
    setSaving(true)
    try {
      await apiFetch('/api/v1/workspace/settings', {
        method: 'PUT',
        body: JSON.stringify({
          company_name: form.company_name,
          industry: form.industry || null,
          monthly_ad_budget: parseFloat(form.monthly_ad_budget) || null,
          default_currency: form.default_currency,
          setup_step: 2,
        }),
      })
      setStep(2)
    } finally {
      setSaving(false)
    }
  }

  async function saveStep3() {
    setSaving(true)
    try {
      await apiFetch('/api/v1/workspace/settings', {
        method: 'PUT',
        body: JSON.stringify({
          cogs_per_unit: parseFloat(form.cogs_per_unit) || 0,
          shipping_cost: parseFloat(form.shipping_cost) || 0,
          return_rate: (parseFloat(form.return_rate) || 0) / 100,
          avg_order_value: parseFloat(form.avg_order_value) || null,
          setup_step: 4,
          setup_completed: true,
        }),
      })
      setStep(4)
    } finally {
      setSaving(false)
    }
  }

  const metaCount = connections.filter((c) => c.platform === 'meta').length
  const googleCount = connections.filter((c) => c.platform === 'google').length

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6">
      <div className="w-full max-w-2xl">
        <div className="flex items-center justify-between mb-8">
          {STEPS.map((s, i) => (
            <div key={s.num} className="flex items-center flex-1">
              <div className="flex flex-col items-center flex-1">
                <div
                  className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold ${
                    step > s.num
                      ? 'bg-emerald-500 text-white'
                      : step === s.num
                        ? 'bg-brand-600 text-white'
                        : 'bg-slate-200 text-slate-400'
                  }`}
                >
                  {step > s.num ? (
                    <CheckCircle className="w-5 h-5" />
                  ) : (
                    s.num
                  )}
                </div>
                <div className="text-xs text-slate-500 mt-1 text-center w-20">
                  {s.title}
                </div>
              </div>
              {i < STEPS.length - 1 && (
                <div
                  className={`flex-1 h-0.5 mx-2 mb-4 ${
                    step > s.num ? 'bg-emerald-400' : 'bg-slate-200'
                  }`}
                />
              )}
            </div>
          ))}
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8">
          {step === 1 && (
            <div className="space-y-5">
              <div>
                <h2 className="text-xl font-semibold text-slate-900">
                  Tell us about your company
                </h2>
                <p className="text-sm text-slate-500 mt-1">
                  This personalises every recommendation the platform makes.
                </p>
              </div>
              {(
                [
                  { label: 'Company Name *', key: 'company_name', placeholder: 'Acme Corp' },
                  { label: 'Industry', key: 'industry', placeholder: 'E-commerce, SaaS, Agency…' },
                  {
                    label: 'Monthly Ad Budget ($)',
                    key: 'monthly_ad_budget',
                    placeholder: '10000',
                    type: 'number' as const,
                  },
                ] as const
              ).map((f) => (
                <div key={f.key}>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    {f.label}
                  </label>
                  <input
                    type={(f as { type?: string }).type ?? 'text'}
                    value={form[f.key]}
                    onChange={(e) => update(f.key, e.target.value)}
                    placeholder={f.placeholder}
                    className="w-full border border-slate-300 rounded-xl px-4 py-3 text-sm"
                  />
                </div>
              ))}
              <button
                onClick={saveStep1}
                disabled={saving || !form.company_name}
                className="w-full bg-brand-600 text-white py-3 rounded-xl font-medium hover:bg-brand-700 disabled:opacity-50 inline-flex items-center justify-center gap-2"
              >
                {saving ? 'Saving…' : 'Continue'}{' '}
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-5">
              <div>
                <h2 className="text-xl font-semibold text-slate-900">
                  Connect your ad accounts
                </h2>
                <p className="text-sm text-slate-500 mt-1">
                  Connect Meta and/or Google Ads to analyse real campaign data.
                </p>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div
                  className={`border-2 rounded-xl p-4 ${
                    metaCount > 0
                      ? 'border-emerald-400 bg-emerald-50'
                      : 'border-dashed border-slate-300'
                  }`}
                >
                  <div className="font-medium text-slate-800 mb-1">Meta Ads</div>
                  {metaCount > 0 ? (
                    <div className="text-sm text-emerald-700 inline-flex items-center gap-1">
                      <CheckCircle className="w-4 h-4" /> Connected ({metaCount})
                    </div>
                  ) : (
                    <button
                      onClick={() =>
                        router.push('/dashboard/integrations?tab=meta')
                      }
                      className="text-sm text-blue-600 hover:underline"
                    >
                      Connect →
                    </button>
                  )}
                </div>
                <div
                  className={`border-2 rounded-xl p-4 ${
                    googleCount > 0
                      ? 'border-emerald-400 bg-emerald-50'
                      : 'border-dashed border-slate-300'
                  }`}
                >
                  <div className="font-medium text-slate-800 mb-1">
                    Google Ads
                  </div>
                  {googleCount > 0 ? (
                    <div className="text-sm text-emerald-700 inline-flex items-center gap-1">
                      <CheckCircle className="w-4 h-4" /> Connected ({googleCount})
                    </div>
                  ) : (
                    <button
                      onClick={() =>
                        router.push('/dashboard/integrations?tab=google')
                      }
                      className="text-sm text-red-600 hover:underline"
                    >
                      Connect →
                    </button>
                  )}
                </div>
              </div>
              <div className="flex gap-3">
                <button
                  onClick={() => setStep(3)}
                  className="flex-1 border border-slate-300 text-slate-600 py-3 rounded-xl text-sm hover:bg-slate-50"
                >
                  Skip for now
                </button>
                <button
                  onClick={() => setStep(3)}
                  className="flex-1 bg-brand-600 text-white py-3 rounded-xl font-medium hover:bg-brand-700 inline-flex items-center justify-center gap-2"
                >
                  Continue <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="space-y-5">
              <div>
                <h2 className="text-xl font-semibold text-slate-900">
                  Product cost settings
                </h2>
                <p className="text-sm text-slate-500 mt-1">
                  Used to calculate true profitability beyond reported ROAS.
                  Skip if you don&rsquo;t know yet.
                </p>
              </div>
              {(
                [
                  { label: 'Avg Order Value ($)', key: 'avg_order_value', placeholder: '65' },
                  { label: 'Cost of Goods (COGS) per unit ($)', key: 'cogs_per_unit', placeholder: '15' },
                  { label: 'Shipping cost per order ($)', key: 'shipping_cost', placeholder: '5' },
                  { label: 'Return rate (%)', key: 'return_rate', placeholder: '5' },
                ] as const
              ).map((f) => (
                <div key={f.key}>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    {f.label}
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    value={form[f.key]}
                    onChange={(e) => update(f.key, e.target.value)}
                    placeholder={f.placeholder}
                    className="w-full border border-slate-300 rounded-xl px-4 py-3 text-sm"
                  />
                </div>
              ))}
              <div className="flex gap-3">
                <button
                  onClick={saveStep3}
                  className="flex-1 border border-slate-300 text-slate-600 py-3 rounded-xl text-sm hover:bg-slate-50"
                >
                  Skip
                </button>
                <button
                  onClick={saveStep3}
                  disabled={saving}
                  className="flex-1 bg-brand-600 text-white py-3 rounded-xl font-medium hover:bg-brand-700 disabled:opacity-50 inline-flex items-center justify-center gap-2"
                >
                  {saving ? 'Saving…' : 'Finish Setup'}{' '}
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {step === 4 && (
            <div className="text-center space-y-4 py-4">
              <div className="w-16 h-16 bg-emerald-100 rounded-full flex items-center justify-center mx-auto">
                <CheckCircle className="w-10 h-10 text-emerald-600" />
              </div>
              <h2 className="text-2xl font-semibold text-slate-900">
                Platform Ready
              </h2>
              <p className="text-slate-500">
                Your platform is configured. Data will start syncing from
                connected accounts.
              </p>
              {connections.length > 0 && (
                <div className="bg-blue-50 rounded-xl p-3 text-sm text-blue-700">
                  {connections.length} account(s) connected — first sync may
                  take 1-2 minutes
                </div>
              )}
              <button
                onClick={() => router.push('/dashboard')}
                className="bg-brand-600 text-white px-8 py-3 rounded-xl font-medium hover:bg-brand-700"
              >
                Go to Dashboard →
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

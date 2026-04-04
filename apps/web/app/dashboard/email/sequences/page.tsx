'use client'

import { useState, useEffect } from 'react'
import { useSearchParams } from 'next/navigation'
import { Suspense } from 'react'
import {
  Layers, Zap, Loader2, CheckCircle2, AlertCircle,
  ExternalLink, ChevronRight,
} from 'lucide-react'

const API = 'http://localhost:8000/api/v1/email'

const SEQUENCE_TYPES = [
  { value: 'welcome', label: 'Welcome Series', desc: '5 emails over 14 days — onboard new subscribers' },
  { value: 'abandoned_cart', label: 'Cart Recovery', desc: '3 emails — recover lost e-commerce sales' },
  { value: 're_engagement', label: 'Re-engagement', desc: '4 emails — win back inactive contacts' },
  { value: 'nurture', label: 'Lead Nurture', desc: '6 emails — educate and convert prospects' },
  { value: 'onboarding', label: 'Onboarding', desc: '5 emails — activate new SaaS users' },
]

const BUSINESS_TYPES = [
  { value: 'ecommerce', label: 'E-commerce' },
  { value: 'saas', label: 'SaaS' },
  { value: 'local', label: 'Local Business' },
  { value: 'personal_brand', label: 'Personal Brand' },
  { value: 'agency', label: 'Agency' },
  { value: 'coaching', label: 'Coaching / Consulting' },
]

interface GeneratedEmail {
  position: number
  mautic_id: number | null
  subject: string
  delay: string
  goal: string
  mautic_url: string | null
}

interface GenerateResult {
  success?: boolean
  error?: string
  hint?: string
  sequence_name?: string
  sequence_type?: string
  emails_created?: number
  emails?: GeneratedEmail[]
  next_steps?: string[]
  mautic_emails_url?: string
}

function SequenceGeneratorInner() {
  const searchParams = useSearchParams()
  const defaultType = searchParams.get('type') || 'welcome'

  const [sequenceType, setSequenceType] = useState(defaultType)
  const [businessType, setBusinessType] = useState('saas')
  const [niche, setNiche] = useState('')
  const [name, setName] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<GenerateResult | null>(null)

  // Auto-fill name when sequence type changes
  useEffect(() => {
    const found = SEQUENCE_TYPES.find(t => t.value === sequenceType)
    if (found) setName(found.label)
  }, [sequenceType])

  async function generate() {
    if (!businessType || !sequenceType) return
    setLoading(true)
    setResult(null)
    try {
      const res = await fetch(`${API}/sequences/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name || SEQUENCE_TYPES.find(t => t.value === sequenceType)?.label || sequenceType,
          business_type: businessType,
          sequence_type: sequenceType,
          niche: niche.trim(),
        }),
      })
      setResult(await res.json())
    } catch {
      setResult({ error: 'Network error — is the backend running on port 8000?' })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">

      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-blue-500/10 flex items-center justify-center">
          <Layers size={20} className="text-blue-500" />
        </div>
        <div>
          <h1 className="text-xl font-semibold text-slate-900">AI Email Sequences</h1>
          <p className="text-sm text-slate-500">Generate complete email sequences with AI, saved directly to Mautic</p>
        </div>
      </div>

      {/* Generator form */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-5">
        <h2 className="text-sm font-semibold text-slate-700">Configure Your Sequence</h2>

        {/* Sequence type cards */}
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-2">Sequence Type</label>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {SEQUENCE_TYPES.map(t => (
              <button
                key={t.value}
                onClick={() => setSequenceType(t.value)}
                className={`text-left px-4 py-3 rounded-xl border transition-all ${
                  sequenceType === t.value
                    ? 'border-blue-500 bg-blue-50 ring-1 ring-blue-500'
                    : 'border-slate-200 hover:border-slate-300 bg-white'
                }`}
              >
                <p className={`text-xs font-semibold ${sequenceType === t.value ? 'text-blue-700' : 'text-slate-700'}`}>{t.label}</p>
                <p className="text-[11px] text-slate-400 mt-0.5">{t.desc}</p>
              </button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Business Type</label>
            <select
              className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-400 bg-white"
              value={businessType}
              onChange={e => setBusinessType(e.target.value)}
            >
              {BUSINESS_TYPES.map(b => (
                <option key={b.value} value={b.value}>{b.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Niche <span className="text-slate-400 font-normal">(optional)</span></label>
            <input
              className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-400"
              placeholder="e.g. project management, fitness"
              value={niche}
              onChange={e => setNiche(e.target.value)}
            />
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">Sequence Name</label>
          <input
            className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-400"
            placeholder="Name for this sequence"
            value={name}
            onChange={e => setName(e.target.value)}
          />
        </div>

        <button
          onClick={generate}
          disabled={loading || !businessType}
          className="w-full flex items-center justify-center gap-2 py-3 bg-blue-600 hover:bg-blue-700 text-white text-sm font-bold rounded-xl transition-colors disabled:opacity-50"
        >
          {loading ? <Loader2 size={16} className="animate-spin" /> : <Zap size={16} />}
          {loading ? 'AI is writing your email sequence…' : 'Generate Email Sequence with AI'}
        </button>

        {loading && (
          <div className="flex flex-col items-center gap-2 py-4 text-center">
            <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
              <div className="h-full bg-blue-500 animate-pulse rounded-full w-2/3" />
            </div>
            <p className="text-xs text-slate-400">This takes 30–60 seconds using local AI</p>
          </div>
        )}
      </div>

      {/* Results */}
      {result && (
        <div className="space-y-4">
          {result.error ? (
            <div className="flex items-start gap-3 p-4 bg-red-50 border border-red-200 rounded-xl">
              <AlertCircle size={15} className="text-red-500 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-red-800">{result.error}</p>
                {result.hint && <p className="text-xs text-red-600 mt-1">{result.hint}</p>}
              </div>
            </div>
          ) : (
            <>
              {/* Success banner */}
              <div className="flex items-center justify-between p-4 bg-emerald-50 border border-emerald-200 rounded-xl">
                <div className="flex items-center gap-2.5">
                  <CheckCircle2 size={16} className="text-emerald-600" />
                  <span className="text-sm font-semibold text-emerald-800">
                    {result.emails_created} emails created in Mautic — {result.sequence_name}
                  </span>
                </div>
                <a href={result.mautic_emails_url} target="_blank" rel="noreferrer"
                  className="flex items-center gap-1 text-xs font-semibold text-emerald-700 hover:text-emerald-900">
                  View in Mautic <ExternalLink size={11} />
                </a>
              </div>

              {/* Email cards */}
              <div className="space-y-2">
                {(result.emails ?? []).map(email => (
                  <div key={email.position} className="flex items-center gap-4 p-4 bg-white border border-slate-200 rounded-xl hover:border-blue-200 transition-colors">
                    <div className="w-7 h-7 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0">
                      <span className="text-xs font-bold text-blue-600">{email.position}</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-slate-800 truncate">{email.subject}</p>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-[11px] text-slate-400">Send: {email.delay}</span>
                        {email.goal && (
                          <>
                            <span className="text-slate-200">·</span>
                            <span className="text-[11px] text-slate-400 capitalize">{email.goal.replace(/_/g, ' ')}</span>
                          </>
                        )}
                      </div>
                    </div>
                    {email.mautic_url && (
                      <a href={email.mautic_url} target="_blank" rel="noreferrer"
                        className="flex items-center gap-1 text-xs text-blue-500 hover:text-blue-700 flex-shrink-0">
                        Edit <ExternalLink size={10} />
                      </a>
                    )}
                  </div>
                ))}
              </div>

              {/* Next steps */}
              {(result.next_steps ?? []).length > 0 && (
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-5">
                  <h3 className="text-sm font-semibold text-slate-700 mb-3">Next Steps — Set Up the Campaign</h3>
                  <ul className="space-y-1.5">
                    {result.next_steps!.map((step, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-slate-600">
                        <ChevronRight size={12} className="text-blue-400 mt-1 flex-shrink-0" />
                        {step.includes('http') ? (
                          <a href={step.split(': ')[1]} target="_blank" rel="noreferrer"
                            className="text-blue-600 hover:underline">{step}</a>
                        ) : step}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}

export default function SequencesPage() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center h-32"><Loader2 className="w-6 h-6 animate-spin text-gray-400" /></div>}>
      <SequenceGeneratorInner />
    </Suspense>
  )
}

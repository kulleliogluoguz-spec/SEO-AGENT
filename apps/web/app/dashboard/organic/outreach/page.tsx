'use client'

import { useState } from 'react'
import { Mail, Send, Copy, Check, Loader2, AlertCircle, ArrowRight, RefreshCw } from 'lucide-react'

const API = 'http://localhost:8000/api/v1/organic'

interface OutreachStrategy {
  acquisition_channels: Array<{
    channel: string
    effort: string
    time_to_results: string
    tactics: string[]
    free_tools: string[]
  }>
  cold_email_sequences: Array<{
    sequence_name: string
    emails: Array<{
      subject: string
      body: string
      send_day: number
      purpose: string
    }>
  }>
  growth_loop: {
    description: string
    steps: string[]
    viral_coefficient_tip: string
  }
  partnership_opportunities: string[]
  referral_program_ideas: string[]
}

interface GrowthLoop {
  loop_name: string
  trigger: string
  steps: string[]
  viral_mechanism: string
  metrics_to_track: string[]
  implementation_steps: string[]
  expected_k_factor: string
}

export default function OutreachPage() {
  const [business, setBusiness] = useState('')
  const [audience, setAudience] = useState('')
  const [industry, setIndustry] = useState('')
  const [budget, setBudget] = useState('0')

  const [strategy, setStrategy] = useState<OutreachStrategy | null>(null)
  const [growthLoop, setGrowthLoop] = useState<GrowthLoop | null>(null)
  const [loadingStrategy, setLoadingStrategy] = useState(false)
  const [loadingLoop, setLoadingLoop] = useState(false)
  const [error, setError] = useState('')
  const [copied, setCopied] = useState('')
  const [activeSeq, setActiveSeq] = useState(0)
  const [activeEmail, setActiveEmail] = useState(0)

  async function buildStrategy() {
    if (!business || !audience) { setError('Business and audience are required.'); return }
    setLoadingStrategy(true); setError('')
    try {
      const res = await fetch(`${API}/outreach/strategy`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          business_type: business,
          target_audience: audience,
          industry,
          monthly_budget: parseInt(budget) || 0,
        }),
      })
      if (!res.ok) throw new Error(await res.text())
      setStrategy(await res.json())
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed')
    } finally { setLoadingStrategy(false) }
  }

  async function buildGrowthLoop() {
    if (!business || !audience) { setError('Fill in Business and Audience first.'); return }
    setLoadingLoop(true); setError('')
    try {
      const res = await fetch(`${API}/growth-loop`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          business_model: business,
          target_audience: audience,
          current_channels: [],
        }),
      })
      if (!res.ok) throw new Error(await res.text())
      setGrowthLoop(await res.json())
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed')
    } finally { setLoadingLoop(false) }
  }

  function copy(text: string, key: string) {
    navigator.clipboard.writeText(text)
    setCopied(key)
    setTimeout(() => setCopied(''), 2000)
  }

  const effortColor = (effort: string) => {
    const e = effort.toLowerCase()
    return e.includes('low') ? 'text-emerald-600 bg-emerald-50 border-emerald-200'
      : e.includes('medium') ? 'text-amber-600 bg-amber-50 border-amber-200'
      : 'text-red-600 bg-red-50 border-red-200'
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-teal-500/10 flex items-center justify-center">
          <Mail size={20} className="text-teal-500" />
        </div>
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Free Outreach Engine</h1>
          <p className="text-sm text-slate-500">Zero-budget acquisition channels, cold email sequences & growth loops</p>
        </div>
      </div>

      {/* Input */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Business Type *</label>
            <input className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-400"
              placeholder="e.g. B2B SaaS, agency, e-commerce" value={business} onChange={e => setBusiness(e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Target Audience *</label>
            <input className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-400"
              placeholder="e.g. startup CTOs" value={audience} onChange={e => setAudience(e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Industry</label>
            <input className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-400"
              placeholder="e.g. fintech" value={industry} onChange={e => setIndustry(e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Monthly Budget ($)</label>
            <input type="number" className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-teal-500/30 focus:border-teal-400"
              placeholder="0" value={budget} onChange={e => setBudget(e.target.value)} />
          </div>
        </div>
        {error && (
          <div className="flex items-center gap-2 text-sm text-red-600 bg-red-50 rounded-lg px-4 py-2.5">
            <AlertCircle size={14} />{error}
          </div>
        )}
        <div className="flex gap-3">
          <button onClick={buildStrategy} disabled={loadingStrategy}
            className="flex items-center gap-2 px-5 py-2.5 bg-teal-600 hover:bg-teal-700 text-white text-sm font-semibold rounded-lg transition-colors disabled:opacity-50">
            {loadingStrategy ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
            {loadingStrategy ? 'Building...' : 'Build Outreach Strategy'}
          </button>
          <button onClick={buildGrowthLoop} disabled={loadingLoop}
            className="flex items-center gap-2 px-5 py-2.5 border border-teal-200 text-teal-700 text-sm font-medium rounded-lg hover:bg-teal-50 transition-colors disabled:opacity-50">
            {loadingLoop ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
            {loadingLoop ? 'Building Loop...' : 'Design Growth Loop'}
          </button>
        </div>
      </div>

      {strategy && (
        <div className="space-y-5">
          {/* Acquisition Channels */}
          <div className="space-y-3">
            <h2 className="text-sm font-semibold text-slate-700">Acquisition Channels</h2>
            <div className="grid grid-cols-1 gap-3">
              {strategy.acquisition_channels.map((ch, i) => (
                <div key={i} className="bg-white rounded-xl border border-slate-200 p-5">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-sm font-semibold text-slate-800">{ch.channel}</h3>
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-0.5 text-xs font-medium rounded-lg border ${effortColor(ch.effort)}`}>
                        {ch.effort} effort
                      </span>
                      <span className="text-xs text-slate-400">{ch.time_to_results}</span>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Tactics</p>
                      <ul className="space-y-1">
                        {ch.tactics.map((t, j) => (
                          <li key={j} className="text-xs text-slate-600 flex gap-2"><span className="text-teal-400">→</span>{t}</li>
                        ))}
                      </ul>
                    </div>
                    {ch.free_tools.length > 0 && (
                      <div>
                        <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Free Tools</p>
                        <div className="flex flex-wrap gap-1.5">
                          {ch.free_tools.map((tool, j) => (
                            <span key={j} className="px-2 py-0.5 bg-slate-50 text-slate-600 text-xs rounded border border-slate-200">{tool}</span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Cold Email Sequences */}
          {strategy.cold_email_sequences.length > 0 && (
            <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
              <div className="flex border-b border-slate-100">
                {strategy.cold_email_sequences.map((seq, i) => (
                  <button key={i} onClick={() => { setActiveSeq(i); setActiveEmail(0) }}
                    className={`px-4 py-3 text-xs font-medium transition-colors ${
                      activeSeq === i ? 'bg-teal-50 text-teal-700 border-b-2 border-teal-500' : 'text-slate-500 hover:text-slate-700'
                    }`}>
                    {seq.sequence_name}
                  </button>
                ))}
              </div>
              {strategy.cold_email_sequences[activeSeq] && (
                <div className="p-5 space-y-4">
                  {/* Email step tabs */}
                  <div className="flex gap-2">
                    {strategy.cold_email_sequences[activeSeq].emails.map((email, i) => (
                      <button key={i} onClick={() => setActiveEmail(i)}
                        className={`px-3 py-1.5 text-xs font-medium rounded-lg border transition-all ${
                          activeEmail === i ? 'bg-teal-600 border-teal-600 text-white' : 'border-slate-200 text-slate-600 hover:border-teal-300'
                        }`}>
                        Day {email.send_day}
                      </button>
                    ))}
                  </div>
                  {strategy.cold_email_sequences[activeSeq].emails[activeEmail] && (() => {
                    const email = strategy.cold_email_sequences[activeSeq].emails[activeEmail]
                    return (
                      <div className="space-y-3">
                        <div className="flex items-start justify-between">
                          <div>
                            <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wide mb-1">Subject Line</p>
                            <p className="text-sm font-medium text-slate-800">{email.subject}</p>
                          </div>
                          <button onClick={() => copy(`Subject: ${email.subject}\n\n${email.body}`, `email-${activeSeq}-${activeEmail}`)}
                            className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-700">
                            {copied === `email-${activeSeq}-${activeEmail}` ? <Check size={12} className="text-emerald-500" /> : <Copy size={12} />}
                            Copy
                          </button>
                        </div>
                        <div>
                          <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wide mb-1">Purpose</p>
                          <p className="text-xs text-slate-500">{email.purpose}</p>
                        </div>
                        <pre className="text-sm text-slate-700 whitespace-pre-wrap font-sans leading-relaxed bg-slate-50 rounded-xl p-4">{email.body}</pre>
                      </div>
                    )
                  })()}
                </div>
              )}
            </div>
          )}

          {/* Referral & Partnership */}
          <div className="grid grid-cols-2 gap-5">
            {strategy.referral_program_ideas.length > 0 && (
              <div className="bg-white rounded-xl border border-slate-200 p-5">
                <h3 className="text-sm font-semibold text-slate-700 mb-3">Referral Program Ideas</h3>
                <ul className="space-y-2">
                  {strategy.referral_program_ideas.map((idea, i) => (
                    <li key={i} className="text-xs text-slate-600 flex gap-2 items-start">
                      <span className="text-teal-400 mt-0.5">◆</span>{idea}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {strategy.partnership_opportunities.length > 0 && (
              <div className="bg-white rounded-xl border border-slate-200 p-5">
                <h3 className="text-sm font-semibold text-slate-700 mb-3">Partnership Opportunities</h3>
                <ul className="space-y-2">
                  {strategy.partnership_opportunities.map((p, i) => (
                    <li key={i} className="text-xs text-slate-600 flex gap-2 items-start">
                      <span className="text-amber-400 mt-0.5">↔</span>{p}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Growth Loop */}
      {growthLoop && (
        <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-4">
          <div className="flex items-center gap-2">
            <RefreshCw size={14} className="text-teal-500" />
            <h2 className="text-sm font-semibold text-slate-700">{growthLoop.loop_name}</h2>
          </div>
          <p className="text-sm text-slate-600">Trigger: <span className="font-medium">{growthLoop.trigger}</span></p>
          <div className="flex items-center gap-2 flex-wrap">
            {growthLoop.steps.map((step, i) => (
              <div key={i} className="flex items-center gap-2">
                <div className="px-3 py-2 bg-teal-50 border border-teal-200 rounded-lg text-xs text-teal-800 max-w-[160px]">
                  {step}
                </div>
                {i < growthLoop.steps.length - 1 && <ArrowRight size={12} className="text-slate-400 flex-shrink-0" />}
              </div>
            ))}
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs font-medium text-slate-500 mb-1">Viral Mechanism</p>
              <p className="text-sm text-slate-700">{growthLoop.viral_mechanism}</p>
            </div>
            <div>
              <p className="text-xs font-medium text-slate-500 mb-1">Expected K-Factor</p>
              <p className="text-sm font-semibold text-teal-600">{growthLoop.expected_k_factor}</p>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wide mb-2">Metrics to Track</p>
              <ul className="space-y-1">
                {growthLoop.metrics_to_track.map((m, i) => (
                  <li key={i} className="text-xs text-slate-600 flex gap-2"><span className="text-teal-400">•</span>{m}</li>
                ))}
              </ul>
            </div>
            <div>
              <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wide mb-2">Implementation Steps</p>
              <ol className="space-y-1">
                {growthLoop.implementation_steps.map((s, i) => (
                  <li key={i} className="text-xs text-slate-600 flex gap-2">
                    <span className="text-slate-400 w-3 flex-shrink-0">{i + 1}.</span>{s}
                  </li>
                ))}
              </ol>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

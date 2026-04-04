'use client'

import { useState } from 'react'
import { Users, Target, Mail, Copy, Check, Loader2, AlertCircle } from 'lucide-react'

const API = 'http://localhost:8000/api/v1/organic'

interface AudienceIntelligence {
  icp_profiles: Array<{
    persona_name: string
    demographics: string
    psychographics: string[]
    pain_points: string[]
    goals: string[]
    where_they_hang_out: string[]
    buying_triggers: string[]
  }>
  free_targeting_methods: string[]
  communities_to_join: string[]
  influencers_to_engage: string[]
  outreach_templates: Array<{
    channel: string
    template: string
    personalization_tips: string[]
  }>
  audience_segments: string[]
  content_themes_by_segment: Record<string, string[]>
}

export default function AudienceMapPage() {
  const [product, setProduct] = useState('')
  const [audience, setAudience] = useState('')
  const [industry, setIndustry] = useState('')

  const [intel, setIntel] = useState<AudienceIntelligence | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [copied, setCopied] = useState('')
  const [activePersona, setActivePersona] = useState(0)

  async function analyze() {
    if (!product || !audience) { setError('Product and audience are required.'); return }
    setLoading(true); setError('')
    try {
      const res = await fetch(`${API}/audience/intelligence`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ product_service: product, target_audience: audience, industry }),
      })
      if (!res.ok) throw new Error(await res.text())
      setIntel(await res.json())
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed')
    } finally { setLoading(false) }
  }

  function copy(text: string, key: string) {
    navigator.clipboard.writeText(text)
    setCopied(key)
    setTimeout(() => setCopied(''), 2000)
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-indigo-500/10 flex items-center justify-center">
          <Users size={20} className="text-indigo-500" />
        </div>
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Audience Map</h1>
          <p className="text-sm text-slate-500">ICP profiles, free targeting methods & outreach templates</p>
        </div>
      </div>

      {/* Input */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-4">
        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Product / Service *</label>
            <input className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-400"
              placeholder="What do you offer?" value={product} onChange={e => setProduct(e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Target Audience *</label>
            <input className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-400"
              placeholder="Who do you serve?" value={audience} onChange={e => setAudience(e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Industry</label>
            <input className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-400"
              placeholder="e.g. SaaS" value={industry} onChange={e => setIndustry(e.target.value)} />
          </div>
        </div>
        {error && (
          <div className="flex items-center gap-2 text-sm text-red-600 bg-red-50 rounded-lg px-4 py-2.5">
            <AlertCircle size={14} />{error}
          </div>
        )}
        <button onClick={analyze} disabled={loading}
          className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold rounded-lg transition-colors disabled:opacity-50">
          {loading ? <Loader2 size={14} className="animate-spin" /> : <Target size={14} />}
          {loading ? 'Mapping Audience...' : 'Map Audience'}
        </button>
      </div>

      {intel && (
        <div className="space-y-5">
          {/* ICP Profiles */}
          {intel.icp_profiles.length > 0 && (
            <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
              <div className="flex border-b border-slate-100">
                {intel.icp_profiles.map((p, i) => (
                  <button key={i} onClick={() => setActivePersona(i)}
                    className={`px-4 py-3 text-xs font-medium transition-colors ${
                      activePersona === i
                        ? 'bg-indigo-50 text-indigo-700 border-b-2 border-indigo-500'
                        : 'text-slate-500 hover:text-slate-700'
                    }`}>
                    {p.persona_name}
                  </button>
                ))}
              </div>
              {intel.icp_profiles[activePersona] && (() => {
                const p = intel.icp_profiles[activePersona]
                return (
                  <div className="p-5 grid grid-cols-2 gap-5">
                    <div className="space-y-4">
                      <div>
                        <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Demographics</p>
                        <p className="text-sm text-slate-700">{p.demographics}</p>
                      </div>
                      <div>
                        <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Psychographics</p>
                        <ul className="space-y-1">
                          {p.psychographics.map((item, i) => (
                            <li key={i} className="text-xs text-slate-600 flex gap-2"><span className="text-indigo-400">•</span>{item}</li>
                          ))}
                        </ul>
                      </div>
                      <div>
                        <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Pain Points</p>
                        <ul className="space-y-1">
                          {p.pain_points.map((item, i) => (
                            <li key={i} className="text-xs text-slate-600 flex gap-2"><span className="text-red-400">!</span>{item}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                    <div className="space-y-4">
                      <div>
                        <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Goals</p>
                        <ul className="space-y-1">
                          {p.goals.map((item, i) => (
                            <li key={i} className="text-xs text-slate-600 flex gap-2"><span className="text-emerald-400">→</span>{item}</li>
                          ))}
                        </ul>
                      </div>
                      <div>
                        <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Where They Hang Out</p>
                        <div className="flex flex-wrap gap-1.5">
                          {p.where_they_hang_out.map((place, i) => (
                            <span key={i} className="px-2.5 py-1 bg-indigo-50 text-indigo-700 text-xs rounded-lg border border-indigo-200">{place}</span>
                          ))}
                        </div>
                      </div>
                      <div>
                        <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Buying Triggers</p>
                        <ul className="space-y-1">
                          {p.buying_triggers.map((item, i) => (
                            <li key={i} className="text-xs text-slate-600 flex gap-2"><span className="text-amber-400">⚡</span>{item}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  </div>
                )
              })()}
            </div>
          )}

          {/* Free targeting + communities */}
          <div className="grid grid-cols-2 gap-5">
            <div className="bg-white rounded-xl border border-slate-200 p-5">
              <h3 className="text-sm font-semibold text-slate-700 mb-3">Free Targeting Methods</h3>
              <ul className="space-y-2">
                {intel.free_targeting_methods.map((m, i) => (
                  <li key={i} className="text-xs text-slate-600 flex gap-2 items-start">
                    <span className="text-emerald-500 mt-0.5">✓</span>{m}
                  </li>
                ))}
              </ul>
            </div>
            <div className="bg-white rounded-xl border border-slate-200 p-5">
              <h3 className="text-sm font-semibold text-slate-700 mb-3">Communities to Join</h3>
              <ul className="space-y-2">
                {intel.communities_to_join.map((c, i) => (
                  <li key={i} className="text-xs text-slate-600 flex gap-2 items-start">
                    <span className="text-indigo-400">→</span>{c}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Outreach Templates */}
          {intel.outreach_templates.length > 0 && (
            <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-4">
              <div className="flex items-center gap-2">
                <Mail size={14} className="text-slate-500" />
                <h3 className="text-sm font-semibold text-slate-700">Outreach Templates</h3>
              </div>
              {intel.outreach_templates.map((tmpl, i) => (
                <div key={i} className="border border-slate-100 rounded-xl p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="px-2.5 py-1 bg-slate-100 text-slate-600 text-xs font-medium rounded-lg capitalize">{tmpl.channel}</span>
                    <button onClick={() => copy(tmpl.template, `tmpl-${i}`)}
                      className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-700">
                      {copied === `tmpl-${i}` ? <Check size={12} className="text-emerald-500" /> : <Copy size={12} />}
                      {copied === `tmpl-${i}` ? 'Copied' : 'Copy'}
                    </button>
                  </div>
                  <pre className="text-xs text-slate-700 whitespace-pre-wrap font-sans leading-relaxed bg-slate-50 rounded-lg p-3">{tmpl.template}</pre>
                  {tmpl.personalization_tips.length > 0 && (
                    <div>
                      <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wide mb-1">Personalization Tips</p>
                      <ul className="space-y-0.5">
                        {tmpl.personalization_tips.map((tip, j) => (
                          <li key={j} className="text-xs text-slate-500 flex gap-1.5"><span className="text-amber-400">•</span>{tip}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

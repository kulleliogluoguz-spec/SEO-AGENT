'use client'

import { useState } from 'react'
import { Target, Loader2, AlertCircle, CheckCircle2, XCircle, Plus, X } from 'lucide-react'

const API = '/api/v1/intelligence'

const BUSINESS_TYPES = ['saas', 'ecommerce', 'local', 'personal_brand', 'agency', 'coaching']

interface ScoringCriterion { criterion: string; weight: number; how_to_identify: string }
interface WhereToFind { platform: string; search_strategy: string; estimated_pool: string }
interface ICPResult {
  icp_definition: {
    company_size: string
    industry: string[]
    roles: string[]
    pain_points: string[]
    buying_triggers: string[]
    disqualifiers: string[]
  }
  scoring_criteria: ScoringCriterion[]
  where_to_find_them: WhereToFind[]
  qualification_questions: string[]
  red_flags: string[]
}

interface ProspectResult {
  fit_score: number
  fit_grade: string
  verdict: string
  matching_criteria: string[]
  missing_criteria: string[]
  recommended_action: string
  outreach_timing: string
  personalization_angles: string[]
}

export default function PipelinePage() {
  const [tab, setTab] = useState<'icp' | 'prospect'>('icp')

  // ICP form
  const [businessType, setBusinessType] = useState('saas')
  const [product, setProduct] = useState('')
  const [targetMarket, setTargetMarket] = useState('')
  const [dealSize, setDealSize] = useState('')
  const [loading, setLoading] = useState(false)
  const [icpResult, setIcpResult] = useState<ICPResult | null>(null)
  const [error, setError] = useState('')

  // Prospect score form
  const [company, setCompany] = useState('')
  const [role, setRole] = useState('')
  const [signals, setSignals] = useState<string[]>([''])
  const [scoring, setScoring] = useState(false)
  const [prospectResult, setProspectResult] = useState<ProspectResult | null>(null)

  async function buildICP() {
    if (!product || !targetMarket) return
    setLoading(true); setError(''); setIcpResult(null)
    try {
      const res = await fetch(`${API}/pipeline/icp-score`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ business_type: businessType, product_description: product, target_market: targetMarket, average_deal_size: dealSize }),
      })
      const data = await res.json()
      if (data.error) { setError(data.error); return }
      setIcpResult(data)
    } catch { setError('Network error') } finally { setLoading(false) }
  }

  async function scoreProspect() {
    if (!company || !role) return
    setScoring(true); setProspectResult(null)
    try {
      const cleanSignals = signals.filter(s => s.trim())
      const params = new URLSearchParams({ company, role, business_type: businessType })
      cleanSignals.forEach(s => params.append('signals', s))
      const res = await fetch(`${API}/pipeline/prospect-score?${params}`, { method: 'POST' })
      const data = await res.json()
      setProspectResult(data)
    } catch { } finally { setScoring(false) }
  }

  const verdictColor = (v: string) =>
    v === 'hot' ? 'bg-red-100 text-red-800 border-red-200' :
    v === 'warm' ? 'bg-amber-100 text-amber-800 border-amber-200' :
    v === 'cold' ? 'bg-blue-100 text-blue-800 border-blue-200' :
    'bg-slate-100 text-slate-800 border-slate-200'

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-blue-500/10 flex items-center justify-center">
          <Target size={20} className="text-blue-500" />
        </div>
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Sales Pipeline</h1>
          <p className="text-sm text-slate-500">ICP scoring + prospect qualification — customer-research skill</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-slate-100 rounded-xl p-1">
        {([['icp', '🎯 Build ICP'], ['prospect', '👤 Score Prospect']] as const).map(([t, label]) => (
          <button key={t} onClick={() => setTab(t)}
            className={`flex-1 py-2 text-sm font-medium rounded-lg transition-colors ${tab === t ? 'bg-white text-slate-800 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}>
            {label}
          </button>
        ))}
      </div>

      {tab === 'icp' && (
        <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Business Type</label>
              <select className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/30 bg-white"
                value={businessType} onChange={e => setBusinessType(e.target.value)}>
                {BUSINESS_TYPES.map(b => <option key={b} value={b}>{b}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Avg Deal Size <span className="text-slate-400 font-normal">(optional)</span></label>
              <input className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/30"
                placeholder="e.g. $500/month" value={dealSize} onChange={e => setDealSize(e.target.value)} />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Product Description</label>
            <textarea className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/30 resize-none"
              rows={3} placeholder="What does your product do? What problem does it solve?"
              value={product} onChange={e => setProduct(e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Target Market</label>
            <input className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/30"
              placeholder="e.g. marketing teams at B2B SaaS companies with 10-100 employees"
              value={targetMarket} onChange={e => setTargetMarket(e.target.value)} />
          </div>
          <button onClick={buildICP} disabled={loading || !product || !targetMarket}
            className="w-full flex items-center justify-center gap-2 py-3 bg-blue-600 hover:bg-blue-700 text-white text-sm font-bold rounded-xl transition-colors disabled:opacity-50">
            {loading ? <Loader2 size={16} className="animate-spin" /> : <Target size={16} />}
            {loading ? 'Building ICP profile…' : 'Build ICP Profile'}
          </button>
          {loading && (
            <div className="text-center">
              <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                <div className="h-full bg-blue-500 animate-pulse rounded-full w-1/2" />
              </div>
              <p className="text-xs text-slate-400 mt-2">Takes 30–60 seconds</p>
            </div>
          )}
        </div>
      )}

      {tab === 'prospect' && (
        <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Company</label>
              <input className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/30"
                placeholder="e.g. Acme Corp" value={company} onChange={e => setCompany(e.target.value)} />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Role</label>
              <input className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/30"
                placeholder="e.g. Head of Marketing" value={role} onChange={e => setRole(e.target.value)} />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Signals Observed</label>
            <div className="space-y-2">
              {signals.map((s, i) => (
                <div key={i} className="flex gap-2">
                  <input className="flex-1 px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/30"
                    placeholder={`e.g. ${i === 0 ? 'recently hired a new CMO' : i === 1 ? 'just raised Series A' : 'posting about growth challenges'}`}
                    value={s} onChange={e => { const ns = [...signals]; ns[i] = e.target.value; setSignals(ns) }} />
                  {signals.length > 1 && (
                    <button onClick={() => setSignals(signals.filter((_, j) => j !== i))} className="p-2 text-slate-400 hover:text-red-500">
                      <X size={14} />
                    </button>
                  )}
                </div>
              ))}
              <button onClick={() => setSignals([...signals, ''])} className="flex items-center gap-1.5 text-xs text-blue-600 hover:text-blue-800">
                <Plus size={12} /> Add signal
              </button>
            </div>
          </div>
          <button onClick={scoreProspect} disabled={scoring || !company || !role}
            className="w-full flex items-center justify-center gap-2 py-3 bg-blue-600 hover:bg-blue-700 text-white text-sm font-bold rounded-xl transition-colors disabled:opacity-50">
            {scoring ? <Loader2 size={16} className="animate-spin" /> : <Target size={16} />}
            {scoring ? 'Scoring prospect…' : 'Score This Prospect'}
          </button>

          {prospectResult && (
            <div className="space-y-3 pt-2">
              <div className="flex items-center gap-3">
                <div className="text-3xl font-bold text-slate-800">{prospectResult.fit_score}</div>
                <div>
                  <div className="text-sm font-semibold text-slate-700">{prospectResult.fit_grade} fit</div>
                  <span className={`text-xs px-2 py-0.5 rounded-full font-semibold border ${verdictColor(prospectResult.verdict)}`}>
                    {prospectResult.verdict?.toUpperCase()}
                  </span>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                {prospectResult.matching_criteria?.length > 0 && (
                  <div className="bg-emerald-50 rounded-lg p-3">
                    <p className="text-[10px] font-semibold text-emerald-700 mb-1">MATCHING</p>
                    {prospectResult.matching_criteria.map((c, i) => (
                      <p key={i} className="text-xs text-emerald-800 flex items-start gap-1"><CheckCircle2 size={9} className="mt-0.5 flex-shrink-0" />{c}</p>
                    ))}
                  </div>
                )}
                {prospectResult.missing_criteria?.length > 0 && (
                  <div className="bg-red-50 rounded-lg p-3">
                    <p className="text-[10px] font-semibold text-red-700 mb-1">MISSING</p>
                    {prospectResult.missing_criteria.map((c, i) => (
                      <p key={i} className="text-xs text-red-800 flex items-start gap-1"><XCircle size={9} className="mt-0.5 flex-shrink-0" />{c}</p>
                    ))}
                  </div>
                )}
              </div>
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                <p className="text-[10px] font-semibold text-blue-700 mb-1">RECOMMENDED ACTION</p>
                <p className="text-sm text-blue-800">{prospectResult.recommended_action}</p>
                <p className="text-xs text-blue-600 mt-1">{prospectResult.outreach_timing}</p>
              </div>
              {prospectResult.personalization_angles?.length > 0 && (
                <div className="bg-slate-50 rounded-lg p-3">
                  <p className="text-[10px] font-semibold text-slate-500 mb-1">PERSONALIZATION ANGLES</p>
                  {prospectResult.personalization_angles.map((a, i) => (
                    <p key={i} className="text-xs text-slate-700 mb-0.5">• {a}</p>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {error && (
        <div className="flex items-center gap-3 p-4 bg-red-50 border border-red-200 rounded-xl">
          <AlertCircle size={15} className="text-red-500 flex-shrink-0" />
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* ICP Result */}
      {icpResult && tab === 'icp' && (
        <div className="space-y-4">
          {/* Definition */}
          <div className="bg-white border border-slate-200 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-slate-700 mb-3">ICP Definition</h3>
            <div className="grid grid-cols-2 gap-3">
              {[
                { label: 'Company Size', value: icpResult.icp_definition?.company_size },
                { label: 'Industries', value: icpResult.icp_definition?.industry?.join(', ') },
              ].map(({ label, value }) => (
                <div key={label} className="bg-slate-50 rounded-lg p-3">
                  <p className="text-[10px] font-semibold text-slate-500 mb-1">{label.toUpperCase()}</p>
                  <p className="text-sm text-slate-700">{value}</p>
                </div>
              ))}
            </div>
            <div className="mt-3 grid grid-cols-1 gap-3">
              {[
                { label: 'Pain Points', items: icpResult.icp_definition?.pain_points, color: 'text-red-600', dot: 'bg-red-400' },
                { label: 'Buying Triggers', items: icpResult.icp_definition?.buying_triggers, color: 'text-emerald-700', dot: 'bg-emerald-400' },
                { label: 'Disqualifiers', items: icpResult.icp_definition?.disqualifiers, color: 'text-amber-700', dot: 'bg-amber-400' },
              ].map(({ label, items, color, dot }) => items?.length > 0 && (
                <div key={label}>
                  <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wide mb-1.5">{label}</p>
                  <div className="flex flex-wrap gap-2">
                    {items.map((item, i) => (
                      <span key={i} className={`flex items-center gap-1.5 text-xs font-medium ${color} bg-white border border-slate-200 px-2 py-1 rounded-full`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${dot}`} />{item}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Scoring criteria */}
          {icpResult.scoring_criteria?.length > 0 && (
            <div className="bg-white border border-slate-200 rounded-xl p-5">
              <h3 className="text-sm font-semibold text-slate-700 mb-3">Scoring Criteria</h3>
              <div className="space-y-2">
                {icpResult.scoring_criteria.map((c, i) => (
                  <div key={i} className="flex items-start gap-3">
                    <span className="w-8 h-6 bg-blue-100 text-blue-700 text-xs font-bold rounded flex items-center justify-center flex-shrink-0">{c.weight}%</span>
                    <div>
                      <p className="text-sm font-medium text-slate-700">{c.criterion}</p>
                      <p className="text-xs text-slate-500">{c.how_to_identify}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Where to find + qualification questions */}
          <div className="grid grid-cols-1 gap-4">
            {icpResult.where_to_find_them?.length > 0 && (
              <div className="bg-white border border-slate-200 rounded-xl p-5">
                <h3 className="text-sm font-semibold text-slate-700 mb-3">Where to Find Them</h3>
                {icpResult.where_to_find_them.map((w, i) => (
                  <div key={i} className="bg-slate-50 rounded-lg p-3 mb-2">
                    <div className="flex items-center justify-between mb-1">
                      <p className="text-xs font-semibold text-slate-700">{w.platform}</p>
                      <span className="text-[10px] text-slate-500">{w.estimated_pool}</span>
                    </div>
                    <p className="text-xs text-slate-600 font-mono">{w.search_strategy}</p>
                  </div>
                ))}
              </div>
            )}
            {icpResult.qualification_questions?.length > 0 && (
              <div className="bg-white border border-slate-200 rounded-xl p-5">
                <h3 className="text-sm font-semibold text-slate-700 mb-3">Qualification Questions</h3>
                <div className="space-y-2">
                  {icpResult.qualification_questions.map((q, i) => (
                    <div key={i} className="flex items-start gap-2">
                      <span className="text-xs font-bold text-blue-600 flex-shrink-0 mt-0.5">{i + 1}.</span>
                      <p className="text-sm text-slate-700">{q}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

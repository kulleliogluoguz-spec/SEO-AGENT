'use client'

import { useState } from 'react'
import { Send, Loader2, AlertCircle, Copy, CheckCircle2, UserPlus } from 'lucide-react'

const API = '/api/v1/intelligence'
const CRM_API = '/api/v1/crm'
const CHANNELS = ['email', 'linkedin', 'twitter']
const BUSINESS_TYPES = ['saas', 'ecommerce', 'local', 'personal_brand', 'agency', 'coaching']

interface OutboundResult {
  subject: string
  message: string
  follow_up_1: string
  follow_up_2: string
  personalization_used: string
  predicted_open_rate: string
  predicted_reply_rate: string
  best_send_time: string
}

interface Touch { touch: number; day: number; type: string; subject?: string; message: string; goal: string }
interface SequenceResult {
  sequence_name: string
  target_profile: string
  touches: Touch[]
  expected_reply_rate: string
  best_performing_touch: number
  tips: string[]
}

function CopyBlock({ label, text }: { label: string; text: string }) {
  const [copied, setCopied] = useState(false)
  if (!text) return null
  const copy = () => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }
  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4">
      <div className="flex items-center justify-between mb-2">
        <p className="text-xs font-semibold text-slate-600 uppercase tracking-wide">{label}</p>
        <button onClick={copy} className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors">
          {copied ? <CheckCircle2 size={11} className="text-emerald-500" /> : <Copy size={11} />}
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </div>
      <p className="text-sm text-slate-700 whitespace-pre-wrap">{text}</p>
    </div>
  )
}

export default function OutboundPage() {
  const [tab, setTab] = useState<'single' | 'sequence'>('single')

  // Single outreach
  const [name, setName] = useState('')
  const [company, setCompany] = useState('')
  const [role, setRole] = useState('')
  const [product, setProduct] = useState('')
  const [painPoint, setPainPoint] = useState('')
  const [channel, setChannel] = useState('email')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<OutboundResult | null>(null)
  const [error, setError] = useState('')

  // Sequence
  const [seqRole, setSeqRole] = useState('')
  const [seqPain, setSeqPain] = useState('')
  const [seqProduct, setSeqProduct] = useState('')
  const [seqChannel, setSeqChannel] = useState('email')
  const [seqBiz, setSeqBiz] = useState('saas')
  const [seqLoading, setSeqLoading] = useState(false)
  const [sequence, setSequence] = useState<SequenceResult | null>(null)
  const [crmSyncing, setCrmSyncing] = useState(false)
  const [crmResult, setCrmResult] = useState<string>('')

  async function syncToCRM() {
    if (!name || !result) return
    setCrmSyncing(true)
    setCrmResult('')
    try {
      const params = new URLSearchParams({
        prospect_name: name,
        prospect_email: '',
        prospect_company: company || 'Unknown',
        outreach_channel: channel,
        source: 'outreach',
      })
      const res = await fetch(`${CRM_API}/sync/from-outreach?${params}`, { method: 'POST' })
      const data = await res.json()
      setCrmResult(data.success ? '✓ Added to CRM' : `✗ ${data.error?.[0]?.message || 'CRM sync failed'}`)
    } catch {
      setCrmResult('✗ Network error')
    } finally {
      setCrmSyncing(false)
    }
  }

  async function generate() {
    if (!name || !product || !painPoint) return
    setLoading(true); setError(''); setResult(null)
    try {
      const res = await fetch(`${API}/outbound/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prospect_name: name, prospect_company: company, prospect_role: role, your_product: product, pain_point: painPoint, channel }),
      })
      const data = await res.json()
      if (data.error) { setError(data.error); return }
      setResult(data)
    } catch { setError('Network error') } finally { setLoading(false) }
  }

  async function generateSeq() {
    if (!seqRole || !seqPain || !seqProduct) return
    setSeqLoading(true); setSequence(null)
    try {
      const params = new URLSearchParams({ prospect_role: seqRole, pain_point: seqPain, your_product: seqProduct, channel: seqChannel, business_type: seqBiz })
      const res = await fetch(`${API}/outbound/sequence?${params}`, { method: 'POST' })
      const data = await res.json()
      setSequence(data)
    } catch { } finally { setSeqLoading(false) }
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-emerald-500/10 flex items-center justify-center">
          <Send size={20} className="text-emerald-500" />
        </div>
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Outbound Engine</h1>
          <p className="text-sm text-slate-500">Personalized cold outreach — cold-email skill</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-slate-100 rounded-xl p-1">
        {([['single', '✉️ Single Message'], ['sequence', '📋 Full Sequence']] as const).map(([t, label]) => (
          <button key={t} onClick={() => setTab(t)}
            className={`flex-1 py-2 text-sm font-medium rounded-lg transition-colors ${tab === t ? 'bg-white text-slate-800 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}>
            {label}
          </button>
        ))}
      </div>

      {tab === 'single' && (
        <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-4">
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Prospect Name</label>
              <input className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-emerald-500/30"
                placeholder="John" value={name} onChange={e => setName(e.target.value)} />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Company</label>
              <input className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-emerald-500/30"
                placeholder="Acme Corp" value={company} onChange={e => setCompany(e.target.value)} />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Role</label>
              <input className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-emerald-500/30"
                placeholder="Head of Marketing" value={role} onChange={e => setRole(e.target.value)} />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Your Product</label>
            <input className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-emerald-500/30"
              placeholder="e.g. AI-powered marketing automation platform"
              value={product} onChange={e => setProduct(e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Their Pain Point</label>
            <input className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-emerald-500/30"
              placeholder="e.g. spending too much on paid ads with declining ROI"
              value={painPoint} onChange={e => setPainPoint(e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Channel</label>
            <div className="flex gap-2">
              {CHANNELS.map(c => (
                <button key={c} onClick={() => setChannel(c)}
                  className={`px-4 py-2 text-sm font-medium rounded-lg border transition-colors capitalize ${channel === c ? 'border-emerald-500 bg-emerald-50 text-emerald-700' : 'border-slate-200 text-slate-600 hover:border-slate-300'}`}>
                  {c}
                </button>
              ))}
            </div>
          </div>
          <button onClick={generate} disabled={loading || !name || !product || !painPoint}
            className="w-full flex items-center justify-center gap-2 py-3 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-bold rounded-xl transition-colors disabled:opacity-50">
            {loading ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
            {loading ? 'Writing your outreach…' : 'Generate Outreach'}
          </button>
          {loading && (
            <div className="text-center">
              <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                <div className="h-full bg-emerald-500 animate-pulse rounded-full w-2/3" />
              </div>
              <p className="text-xs text-slate-400 mt-2">Takes 15–30 seconds</p>
            </div>
          )}
        </div>
      )}

      {tab === 'sequence' && (
        <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Prospect Role</label>
              <input className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-emerald-500/30"
                placeholder="e.g. Marketing Directors" value={seqRole} onChange={e => setSeqRole(e.target.value)} />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Business Type</label>
              <select className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-emerald-500/30 bg-white"
                value={seqBiz} onChange={e => setSeqBiz(e.target.value)}>
                {BUSINESS_TYPES.map(b => <option key={b} value={b}>{b}</option>)}
              </select>
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Their Pain Point</label>
            <input className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-emerald-500/30"
              placeholder="e.g. scaling content production without growing team"
              value={seqPain} onChange={e => setSeqPain(e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Your Product</label>
            <input className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-emerald-500/30"
              placeholder="e.g. AI content platform" value={seqProduct} onChange={e => setSeqProduct(e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Channel</label>
            <div className="flex gap-2">
              {CHANNELS.map(c => (
                <button key={c} onClick={() => setSeqChannel(c)}
                  className={`px-4 py-2 text-sm font-medium rounded-lg border transition-colors capitalize ${seqChannel === c ? 'border-emerald-500 bg-emerald-50 text-emerald-700' : 'border-slate-200 text-slate-600 hover:border-slate-300'}`}>
                  {c}
                </button>
              ))}
            </div>
          </div>
          <button onClick={generateSeq} disabled={seqLoading || !seqRole || !seqPain || !seqProduct}
            className="w-full flex items-center justify-center gap-2 py-3 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-bold rounded-xl transition-colors disabled:opacity-50">
            {seqLoading ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
            {seqLoading ? 'Building sequence…' : 'Generate 5-Touch Sequence'}
          </button>
          {seqLoading && (
            <div className="text-center">
              <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                <div className="h-full bg-emerald-500 animate-pulse rounded-full w-1/2" />
              </div>
              <p className="text-xs text-slate-400 mt-2">Writing 5 messages — takes 30–60 seconds</p>
            </div>
          )}

          {sequence && (
            <div className="space-y-3 pt-2">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-slate-700">{sequence.sequence_name}</h3>
                <span className="text-xs text-slate-500">{sequence.expected_reply_rate} expected reply rate</span>
              </div>
              <div className="space-y-2">
                {sequence.touches?.map((touch) => (
                  <div key={touch.touch}
                    className={`border rounded-xl p-4 ${touch.touch === sequence.best_performing_touch ? 'border-emerald-300 bg-emerald-50' : 'border-slate-200 bg-white'}`}>
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className={`w-6 h-6 rounded-full text-xs font-bold flex items-center justify-center ${touch.touch === sequence.best_performing_touch ? 'bg-emerald-500 text-white' : 'bg-slate-200 text-slate-600'}`}>
                          {touch.touch}
                        </span>
                        <span className="text-xs font-semibold text-slate-600 capitalize">{touch.type}</span>
                        {touch.touch === sequence.best_performing_touch && (
                          <span className="text-[10px] bg-emerald-500 text-white px-1.5 py-0.5 rounded font-semibold">BEST</span>
                        )}
                      </div>
                      <span className="text-xs text-slate-400">Day {touch.day}</span>
                    </div>
                    {touch.subject && (
                      <p className="text-xs font-semibold text-slate-700 mb-1">Subject: {touch.subject}</p>
                    )}
                    <p className="text-sm text-slate-700 whitespace-pre-wrap">{touch.message}</p>
                    <p className="text-[10px] text-slate-400 mt-1 italic">Goal: {touch.goal}</p>
                  </div>
                ))}
              </div>
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

      {/* Single outreach results */}
      {result && tab === 'single' && (
        <div className="space-y-3">
          {/* Stats row */}
          <div className="grid grid-cols-3 gap-3">
            {[
              { label: 'Open Rate', value: result.predicted_open_rate },
              { label: 'Reply Rate', value: result.predicted_reply_rate },
              { label: 'Best Send Time', value: result.best_send_time },
            ].map(({ label, value }) => (
              <div key={label} className="bg-white border border-slate-200 rounded-xl p-3 text-center">
                <p className="text-xs text-slate-500 mb-0.5">{label}</p>
                <p className="text-sm font-semibold text-slate-800">{value || '—'}</p>
              </div>
            ))}
          </div>

          {result.subject && <CopyBlock label="Subject Line" text={result.subject} />}
          <CopyBlock label="Main Message" text={result.message} />
          {result.follow_up_1 && <CopyBlock label="Follow-up #1 (Day 3)" text={result.follow_up_1} />}
          {result.follow_up_2 && <CopyBlock label="Follow-up #2 (Day 7)" text={result.follow_up_2} />}
          {result.personalization_used && (
            <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4">
              <p className="text-[10px] font-semibold text-emerald-700 uppercase tracking-wide mb-1">Personalization Used</p>
              <p className="text-sm text-emerald-800">{result.personalization_used}</p>
            </div>
          )}
          {/* Add to CRM */}
          <div className="flex items-center gap-3 p-4 bg-white border border-slate-200 rounded-xl">
            <button
              onClick={syncToCRM}
              disabled={crmSyncing}
              className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-bold rounded-lg transition-colors disabled:opacity-50"
            >
              {crmSyncing ? <Loader2 size={13} className="animate-spin" /> : <UserPlus size={13} />}
              {crmSyncing ? 'Adding…' : 'Add Prospect to CRM'}
            </button>
            {crmResult && (
              <span className={`text-sm font-medium ${crmResult.startsWith('✓') ? 'text-emerald-600' : 'text-red-500'}`}>
                {crmResult}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

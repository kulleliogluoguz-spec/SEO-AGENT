'use client'

import { useState } from 'react'
import { FlaskConical, Loader2, AlertCircle, CheckCircle2, BarChart3 } from 'lucide-react'

const API = '/api/v1/intelligence'

const METRICS = ['clicks', 'conversions', 'engagement', 'revenue', 'sign_ups', 'bounce_rate']
const BUSINESS_TYPES = ['saas', 'ecommerce', 'local', 'personal_brand', 'agency', 'coaching']

interface Variant { id: string; name: string; description: string; implementation: string }
interface ExperimentResult {
  experiment_name: string
  structured_hypothesis: string
  null_hypothesis: string
  primary_metric: string
  secondary_metrics: string[]
  variants: Variant[]
  sample_size_needed: string
  test_duration_days: number
  success_criteria: string
  how_to_measure: string
  free_tools: string[]
  expected_outcome: string
  risk_level: string
  priority_score: number
  estimated_impact: string
  what_to_test_next: string
}

interface AnalysisResult {
  result: string
  uplift_percentage: number
  statistical_significance: string
  recommendation: string
  reasoning: string
  next_experiment: string
  projected_annual_impact: string
}

export default function ExperimentsPage() {
  const [tab, setTab] = useState<'create' | 'analyze'>('create')

  // Create form
  const [hypothesis, setHypothesis] = useState('')
  const [metric, setMetric] = useState('conversions')
  const [variantA, setVariantA] = useState('')
  const [variantB, setVariantB] = useState('')
  const [businessType, setBusinessType] = useState('saas')
  const [niche, setNiche] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<ExperimentResult | null>(null)
  const [error, setError] = useState('')

  // Analyze form
  const [expName, setExpName] = useState('')
  const [controlVal, setControlVal] = useState('')
  const [variantVal, setVariantVal] = useState('')
  const [sampleSize, setSampleSize] = useState('')
  const [analyzing, setAnalyzing] = useState(false)
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null)

  async function createExperiment() {
    if (!hypothesis || !variantA) return
    setLoading(true); setError(''); setResult(null)
    try {
      const res = await fetch(`${API}/experiments/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          hypothesis, metric,
          variants: [variantA, variantB || 'Control (unchanged)'],
          business_type: businessType, niche,
        }),
      })
      const data = await res.json()
      if (data.error) { setError(data.error); return }
      setResult(data)
    } catch { setError('Network error') } finally { setLoading(false) }
  }

  async function analyzeResults() {
    if (!expName || !controlVal || !variantVal || !sampleSize) return
    setAnalyzing(true); setAnalysis(null)
    try {
      const params = new URLSearchParams({
        experiment_name: expName,
        control_metric: controlVal,
        variant_metric: variantVal,
        sample_size: sampleSize,
        metric_name: metric,
      })
      const res = await fetch(`${API}/experiments/analyze?${params}`, { method: 'POST' })
      const data = await res.json()
      setAnalysis(data)
    } catch { setAnalysis(null) } finally { setAnalyzing(false) }
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-violet-500/10 flex items-center justify-center">
          <FlaskConical size={20} className="text-violet-500" />
        </div>
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Experiments</h1>
          <p className="text-sm text-slate-500">Design A/B tests with structured hypotheses — ab-test-setup skill</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-slate-100 rounded-xl p-1">
        {(['create', 'analyze'] as const).map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`flex-1 py-2 text-sm font-medium rounded-lg transition-colors ${tab === t ? 'bg-white text-slate-800 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}>
            {t === 'create' ? '🧪 Design Experiment' : '📊 Analyze Results'}
          </button>
        ))}
      </div>

      {tab === 'create' && (
        <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Hypothesis</label>
            <input className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-violet-500/30 focus:border-violet-400"
              placeholder='We believe that adding testimonials will increase sign-ups...'
              value={hypothesis} onChange={e => setHypothesis(e.target.value)} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Metric to Measure</label>
              <select className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-violet-500/30 bg-white"
                value={metric} onChange={e => setMetric(e.target.value)}>
                {METRICS.map(m => <option key={m} value={m}>{m.replace(/_/g, ' ')}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Business Type</label>
              <select className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-violet-500/30 bg-white"
                value={businessType} onChange={e => setBusinessType(e.target.value)}>
                {BUSINESS_TYPES.map(b => <option key={b} value={b}>{b}</option>)}
              </select>
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Control / Variant A <span className="text-slate-400 font-normal">(current version)</span></label>
            <input className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-violet-500/30"
              placeholder="e.g. Original landing page without testimonials"
              value={variantA} onChange={e => setVariantA(e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Variant B <span className="text-slate-400 font-normal">(new version to test)</span></label>
            <input className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-violet-500/30"
              placeholder="e.g. Landing page with customer testimonial section added"
              value={variantB} onChange={e => setVariantB(e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Niche <span className="text-slate-400 font-normal">(optional)</span></label>
            <input className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-violet-500/30"
              placeholder="e.g. project management tools"
              value={niche} onChange={e => setNiche(e.target.value)} />
          </div>
          <button onClick={createExperiment} disabled={loading || !hypothesis || !variantA}
            className="w-full flex items-center justify-center gap-2 py-3 bg-violet-600 hover:bg-violet-700 text-white text-sm font-bold rounded-xl transition-colors disabled:opacity-50">
            {loading ? <Loader2 size={16} className="animate-spin" /> : <FlaskConical size={16} />}
            {loading ? 'Designing experiment…' : 'Design Experiment'}
          </button>
          {loading && (
            <div className="text-center">
              <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                <div className="h-full bg-violet-500 animate-pulse rounded-full w-1/2" />
              </div>
              <p className="text-xs text-slate-400 mt-2">Takes 15–30 seconds</p>
            </div>
          )}
        </div>
      )}

      {tab === 'analyze' && (
        <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-4">
          <p className="text-sm text-slate-600">Enter your experiment results to get a statistical interpretation and recommendation.</p>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Experiment Name</label>
            <input className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-violet-500/30"
              placeholder="e.g. Homepage CTA color test" value={expName} onChange={e => setExpName(e.target.value)} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Control Value</label>
              <input type="number" step="0.01" className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-violet-500/30"
                placeholder="e.g. 0.032 or 124" value={controlVal} onChange={e => setControlVal(e.target.value)} />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Variant Value</label>
              <input type="number" step="0.01" className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-violet-500/30"
                placeholder="e.g. 0.041 or 156" value={variantVal} onChange={e => setVariantVal(e.target.value)} />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Sample Size (per variant)</label>
              <input type="number" className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-violet-500/30"
                placeholder="e.g. 1200" value={sampleSize} onChange={e => setSampleSize(e.target.value)} />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Metric</label>
              <select className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-violet-500/30 bg-white"
                value={metric} onChange={e => setMetric(e.target.value)}>
                {METRICS.map(m => <option key={m} value={m}>{m.replace(/_/g, ' ')}</option>)}
              </select>
            </div>
          </div>
          <button onClick={analyzeResults} disabled={analyzing || !expName || !controlVal || !variantVal || !sampleSize}
            className="w-full flex items-center justify-center gap-2 py-3 bg-violet-600 hover:bg-violet-700 text-white text-sm font-bold rounded-xl transition-colors disabled:opacity-50">
            {analyzing ? <Loader2 size={16} className="animate-spin" /> : <BarChart3 size={16} />}
            {analyzing ? 'Analyzing…' : 'Analyze Results'}
          </button>

          {analysis && (
            <div className="space-y-3 pt-2">
              <div className={`p-4 rounded-xl border ${
                analysis.result === 'winner' ? 'bg-emerald-50 border-emerald-200' :
                analysis.result === 'loser' ? 'bg-red-50 border-red-200' : 'bg-amber-50 border-amber-200'
              }`}>
                <div className="flex items-center gap-2 mb-2">
                  {analysis.result === 'winner'
                    ? <CheckCircle2 size={16} className="text-emerald-600" />
                    : <AlertCircle size={16} className="text-amber-600" />}
                  <span className="text-sm font-bold capitalize">{analysis.result} — {analysis.uplift_percentage}% uplift</span>
                </div>
                <p className="text-sm text-slate-700">{analysis.reasoning}</p>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-slate-50 rounded-lg p-3">
                  <p className="text-xs text-slate-500 mb-1">Recommendation</p>
                  <p className="text-sm font-semibold text-slate-800 capitalize">{analysis.recommendation}</p>
                </div>
                <div className="bg-slate-50 rounded-lg p-3">
                  <p className="text-xs text-slate-500 mb-1">Significance</p>
                  <p className="text-sm font-semibold text-slate-800">{analysis.statistical_significance}</p>
                </div>
              </div>
              {analysis.next_experiment && (
                <div className="bg-violet-50 border border-violet-200 rounded-lg p-3">
                  <p className="text-xs font-semibold text-violet-700 mb-1">Next Experiment</p>
                  <p className="text-sm text-violet-800">{analysis.next_experiment}</p>
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

      {/* Experiment result */}
      {result && tab === 'create' && (
        <div className="space-y-4">
          <div className="bg-white border border-slate-200 rounded-xl p-5">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-base font-semibold text-slate-800">{result.experiment_name}</h2>
              <div className="flex items-center gap-2">
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                  result.risk_level === 'low' ? 'bg-emerald-50 text-emerald-700' :
                  result.risk_level === 'medium' ? 'bg-amber-50 text-amber-700' : 'bg-red-50 text-red-700'
                }`}>{result.risk_level} risk</span>
                <span className="text-xs text-slate-500">Priority: {result.priority_score}/100</span>
              </div>
            </div>
            {/* Priority bar */}
            <div className="w-full bg-slate-100 rounded-full h-1.5 mb-4">
              <div className="h-full bg-violet-500 rounded-full" style={{ width: `${result.priority_score}%` }} />
            </div>

            <div className="space-y-3">
              <div className="bg-violet-50 rounded-lg p-3">
                <p className="text-[10px] font-semibold text-violet-600 uppercase tracking-wide mb-1">Structured Hypothesis</p>
                <p className="text-sm text-violet-800">{result.structured_hypothesis}</p>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-slate-50 rounded-lg p-3">
                  <p className="text-[10px] text-slate-500 mb-0.5">Sample Size Needed</p>
                  <p className="text-sm font-medium text-slate-800">{result.sample_size_needed}</p>
                </div>
                <div className="bg-slate-50 rounded-lg p-3">
                  <p className="text-[10px] text-slate-500 mb-0.5">Test Duration</p>
                  <p className="text-sm font-medium text-slate-800">{result.test_duration_days} days</p>
                </div>
                <div className="bg-slate-50 rounded-lg p-3">
                  <p className="text-[10px] text-slate-500 mb-0.5">Estimated Impact</p>
                  <p className="text-sm font-medium text-slate-800">{result.estimated_impact}</p>
                </div>
                <div className="bg-slate-50 rounded-lg p-3">
                  <p className="text-[10px] text-slate-500 mb-0.5">Free Tools</p>
                  <p className="text-sm font-medium text-slate-800">{result.free_tools?.join(', ')}</p>
                </div>
              </div>
            </div>
          </div>

          {/* Variants */}
          {result.variants?.length > 0 && (
            <div className="bg-white border border-slate-200 rounded-xl p-5">
              <h3 className="text-sm font-semibold text-slate-700 mb-3">Variants</h3>
              <div className="space-y-3">
                {result.variants.map((v, i) => (
                  <div key={i} className={`rounded-lg p-4 border ${i === 0 ? 'bg-slate-50 border-slate-200' : 'bg-violet-50 border-violet-200'}`}>
                    <p className="text-xs font-semibold text-slate-600 mb-1">{v.name}</p>
                    <p className="text-sm text-slate-700 mb-2">{v.description}</p>
                    {v.implementation && (
                      <div className="bg-white rounded p-2 border border-slate-100">
                        <p className="text-[10px] font-semibold text-slate-500 mb-1">HOW TO SET UP</p>
                        <p className="text-xs text-slate-600">{v.implementation}</p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Success criteria + measurement */}
          <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-3">
            <h3 className="text-sm font-semibold text-slate-700">Success Criteria</h3>
            <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3">
              <p className="text-sm text-emerald-800">{result.success_criteria}</p>
            </div>
            {result.how_to_measure && (
              <div>
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">How to Measure</p>
                <p className="text-sm text-slate-700">{result.how_to_measure}</p>
              </div>
            )}
            {result.what_to_test_next && (
              <div className="bg-slate-50 rounded-lg p-3">
                <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wide mb-1">If This Wins → Test Next</p>
                <p className="text-sm text-slate-700">{result.what_to_test_next}</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

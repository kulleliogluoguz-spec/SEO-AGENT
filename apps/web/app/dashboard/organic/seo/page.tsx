'use client'

import { useState } from 'react'
import { Search, FileText, CheckSquare, Loader2, AlertCircle, Copy, Check } from 'lucide-react'

const API = 'http://localhost:8000/api/v1/organic'

interface SEOAnalysis {
  primary_keywords: string[]
  long_tail_keywords: string[]
  content_calendar: Array<{ week: number; topic: string; keyword: string; format: string }>
  technical_checklist: string[]
  competitor_gaps: string[]
  estimated_traffic_potential: string
  time_to_rank: string
}

interface ContentBrief {
  title: string
  meta_description: string
  outline: string[]
  word_count_target: number
  internal_links: string[]
  call_to_action: string
  seo_tips: string[]
}

export default function SEOIntelligencePage() {
  const [topic, setTopic] = useState('')
  const [audience, setAudience] = useState('')
  const [industry, setIndustry] = useState('')
  const [briefKeyword, setBriefKeyword] = useState('')

  const [analysis, setAnalysis] = useState<SEOAnalysis | null>(null)
  const [brief, setBrief] = useState<ContentBrief | null>(null)
  const [loadingAnalysis, setLoadingAnalysis] = useState(false)
  const [loadingBrief, setLoadingBrief] = useState(false)
  const [error, setError] = useState('')
  const [copied, setCopied] = useState('')

  async function runAnalysis() {
    if (!topic || !audience) { setError('Topic and audience are required.'); return }
    setLoadingAnalysis(true); setError('')
    try {
      const res = await fetch(`${API}/seo/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic, target_audience: audience, industry }),
      })
      if (!res.ok) throw new Error(await res.text())
      setAnalysis(await res.json())
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed')
    } finally { setLoadingAnalysis(false) }
  }

  async function runBrief() {
    if (!briefKeyword) { setError('Enter a keyword for the brief.'); return }
    setLoadingBrief(true); setError('')
    try {
      const res = await fetch(`${API}/seo/content-brief`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ keyword: briefKeyword, target_audience: audience || 'general audience', industry }),
      })
      if (!res.ok) throw new Error(await res.text())
      setBrief(await res.json())
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed')
    } finally { setLoadingBrief(false) }
  }

  function copyText(text: string, key: string) {
    navigator.clipboard.writeText(text)
    setCopied(key)
    setTimeout(() => setCopied(''), 2000)
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-blue-500/10 flex items-center justify-center">
          <Search size={20} className="text-blue-500" />
        </div>
        <div>
          <h1 className="text-xl font-semibold text-slate-900">SEO Intelligence</h1>
          <p className="text-sm text-slate-500">Keyword research, content calendar & technical SEO checklist</p>
        </div>
      </div>

      {/* Input */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-4">
        <h2 className="text-sm font-semibold text-slate-700">Analyze SEO Opportunity</h2>
        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Topic / Niche *</label>
            <input className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-400"
              placeholder="e.g. project management" value={topic} onChange={e => setTopic(e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Target Audience *</label>
            <input className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-400"
              placeholder="e.g. startup founders" value={audience} onChange={e => setAudience(e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Industry</label>
            <input className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-400"
              placeholder="e.g. SaaS" value={industry} onChange={e => setIndustry(e.target.value)} />
          </div>
        </div>
        {error && (
          <div className="flex items-center gap-2 text-sm text-red-600 bg-red-50 rounded-lg px-4 py-2.5">
            <AlertCircle size={14} />{error}
          </div>
        )}
        <button onClick={runAnalysis} disabled={loadingAnalysis}
          className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-lg transition-colors disabled:opacity-50">
          {loadingAnalysis ? <Loader2 size={14} className="animate-spin" /> : <Search size={14} />}
          {loadingAnalysis ? 'Analyzing...' : 'Analyze SEO'}
        </button>
      </div>

      {/* SEO Analysis Results */}
      {analysis && (
        <div className="space-y-5">
          {/* Stats row */}
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-white rounded-xl border border-slate-200 p-4">
              <p className="text-xs text-slate-500 mb-1">Traffic Potential</p>
              <p className="text-base font-semibold text-slate-800">{analysis.estimated_traffic_potential}</p>
            </div>
            <div className="bg-white rounded-xl border border-slate-200 p-4">
              <p className="text-xs text-slate-500 mb-1">Time to Rank</p>
              <p className="text-base font-semibold text-slate-800">{analysis.time_to_rank}</p>
            </div>
          </div>

          {/* Keywords */}
          <div className="grid grid-cols-2 gap-5">
            <div className="bg-white rounded-xl border border-slate-200 p-5">
              <h3 className="text-sm font-semibold text-slate-700 mb-3">Primary Keywords</h3>
              <div className="flex flex-wrap gap-1.5">
                {analysis.primary_keywords.map((kw, i) => (
                  <button key={i} onClick={() => setBriefKeyword(kw)}
                    className="px-2.5 py-1 bg-blue-50 hover:bg-blue-100 text-blue-700 text-xs rounded-lg border border-blue-200 transition-colors">
                    {kw}
                  </button>
                ))}
              </div>
            </div>
            <div className="bg-white rounded-xl border border-slate-200 p-5">
              <h3 className="text-sm font-semibold text-slate-700 mb-3">Long-tail Keywords</h3>
              <div className="flex flex-wrap gap-1.5">
                {analysis.long_tail_keywords.map((kw, i) => (
                  <button key={i} onClick={() => setBriefKeyword(kw)}
                    className="px-2.5 py-1 bg-slate-50 hover:bg-slate-100 text-slate-600 text-xs rounded-lg border border-slate-200 transition-colors">
                    {kw}
                  </button>
                ))}
              </div>
              <p className="text-[10px] text-slate-400 mt-2">Click any keyword to generate a content brief</p>
            </div>
          </div>

          {/* Content Calendar */}
          <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
            <div className="px-5 py-3 border-b border-slate-100">
              <h3 className="text-sm font-semibold text-slate-700">4-Week Content Calendar</h3>
            </div>
            <table className="w-full">
              <thead className="bg-slate-50">
                <tr>
                  {['Week', 'Topic', 'Target Keyword', 'Format'].map((h, i) => (
                    <th key={i} className="px-4 py-2.5 text-left text-[11px] font-semibold text-slate-500 uppercase tracking-wide">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {analysis.content_calendar.map((row, i) => (
                  <tr key={i} className="hover:bg-slate-50">
                    <td className="px-4 py-3 text-sm font-medium text-slate-600">Week {row.week}</td>
                    <td className="px-4 py-3 text-sm text-slate-700">{row.topic}</td>
                    <td className="px-4 py-3">
                      <button onClick={() => setBriefKeyword(row.keyword)}
                        className="text-xs text-blue-600 hover:text-blue-800 underline underline-offset-2">
                        {row.keyword}
                      </button>
                    </td>
                    <td className="px-4 py-3">
                      <span className="px-2 py-0.5 bg-slate-100 text-slate-600 text-xs rounded-md">{row.format}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Technical Checklist */}
          <div className="grid grid-cols-2 gap-5">
            <div className="bg-white rounded-xl border border-slate-200 p-5">
              <div className="flex items-center gap-2 mb-3">
                <CheckSquare size={14} className="text-emerald-500" />
                <h3 className="text-sm font-semibold text-slate-700">Technical SEO Checklist</h3>
              </div>
              <ul className="space-y-2">
                {analysis.technical_checklist.map((item, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-slate-600">
                    <div className="w-4 h-4 rounded border border-slate-300 flex-shrink-0 mt-0.5" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
            <div className="bg-white rounded-xl border border-slate-200 p-5">
              <h3 className="text-sm font-semibold text-slate-700 mb-3">Competitor Gaps</h3>
              <ul className="space-y-2">
                {analysis.competitor_gaps.map((gap, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-slate-600">
                    <span className="text-emerald-500 mt-1">→</span>{gap}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Content Brief Generator */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-4">
        <div className="flex items-center gap-2">
          <FileText size={14} className="text-slate-500" />
          <h2 className="text-sm font-semibold text-slate-700">Content Brief Generator</h2>
        </div>
        <div className="flex gap-3">
          <input className="flex-1 px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-400"
            placeholder="Enter keyword or click one above..." value={briefKeyword} onChange={e => setBriefKeyword(e.target.value)} />
          <button onClick={runBrief} disabled={loadingBrief}
            className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-900 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50">
            {loadingBrief ? <Loader2 size={13} className="animate-spin" /> : <FileText size={13} />}
            Generate Brief
          </button>
        </div>
      </div>

      {brief && (
        <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-700">Content Brief</h3>
            <button onClick={() => copyText(JSON.stringify(brief, null, 2), 'brief')}
              className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-700">
              {copied === 'brief' ? <Check size={12} className="text-emerald-500" /> : <Copy size={12} />}
              {copied === 'brief' ? 'Copied' : 'Copy All'}
            </button>
          </div>

          <div>
            <p className="text-xs font-medium text-slate-500 mb-1">Title</p>
            <p className="text-sm font-semibold text-slate-800">{brief.title}</p>
          </div>
          <div>
            <p className="text-xs font-medium text-slate-500 mb-1">Meta Description</p>
            <p className="text-sm text-slate-700">{brief.meta_description}</p>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs font-medium text-slate-500 mb-2">Outline</p>
              <ol className="space-y-1">
                {brief.outline.map((section, i) => (
                  <li key={i} className="text-sm text-slate-700 flex gap-2">
                    <span className="text-slate-400">{i + 1}.</span>{section}
                  </li>
                ))}
              </ol>
            </div>
            <div className="space-y-3">
              <div>
                <p className="text-xs font-medium text-slate-500 mb-1">Word Count Target</p>
                <p className="text-sm font-semibold text-slate-800">{brief.word_count_target.toLocaleString()} words</p>
              </div>
              <div>
                <p className="text-xs font-medium text-slate-500 mb-1">Call to Action</p>
                <p className="text-sm text-slate-700">{brief.call_to_action}</p>
              </div>
            </div>
          </div>
          <div>
            <p className="text-xs font-medium text-slate-500 mb-2">SEO Tips</p>
            <ul className="space-y-1">
              {brief.seo_tips.map((tip, i) => (
                <li key={i} className="text-sm text-slate-600 flex gap-2">
                  <span className="text-blue-400">•</span>{tip}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  )
}

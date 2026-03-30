'use client'

import React, { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import {
  Globe, Loader2, Zap, FileText, TrendingUp,
  Users, BarChart2, Share2, ExternalLink, AlertCircle
} from 'lucide-react'
import { apiFetch } from '@/lib/apiFetch'

interface AnalysisResult {
  success:    boolean
  raw_content?: string
  error?:     string
  model_used?: string
  latency_ms?: number
  cost_usd?:  number
}

interface SiteData {
  id:              string
  name:            string
  url?:            string
  domain?:         string
  status:          string
  product_summary?: string
}

const ANALYSIS_BUTTONS = [
  { label: 'SEO Audit',         engine: 'reasoning',            icon: TrendingUp,   color: 'bg-blue-600   hover:bg-blue-700'   },
  { label: 'Content Strategy',  engine: 'content_strategy',     icon: FileText,     color: 'bg-violet-600 hover:bg-violet-700' },
  { label: 'Competitor Analysis',engine: 'competitor_reasoning',icon: BarChart2,    color: 'bg-orange-600 hover:bg-orange-700' },
  { label: 'AI Visibility',     engine: 'visibility_reasoning', icon: Zap,          color: 'bg-teal-600   hover:bg-teal-700'   },
  { label: 'Recommendations',   engine: 'recommendation',       icon: Globe,        color: 'bg-emerald-600 hover:bg-emerald-700'},
  { label: 'Social Content',    engine: 'social_adaptation',    icon: Share2,       color: 'bg-pink-600   hover:bg-pink-700'   },
]

function buildPrompt(engine: string, url: string): string {
  const map: Record<string, string> = {
    reasoning:            `Perform a technical SEO audit for ${url}. Give 5 prioritized recommendations.`,
    content_strategy:     `Create a content strategy for ${url}. Include topic clusters and keywords.`,
    competitor_reasoning: `Identify top 3 competitors for ${url} and compare SEO strategies.`,
    visibility_reasoning: `Analyze AI visibility for ${url}. Give improvement tips.`,
    recommendation:       `Generate 5 growth recommendations for ${url}.`,
    social_adaptation:    `Create a social media plan for ${url} for LinkedIn, Twitter, Instagram.`,
  }
  return map[engine] || `Analyze ${url}.`
}

function AnalysisRenderer({ content }: { content: string }) {
  const lines = content.split('\n')
  const elements: React.ReactNode[] = []
  let bulletBuffer: string[] = []
  let numberedBuffer: { n: string; text: string }[] = []

  function flushBullets() {
    if (bulletBuffer.length === 0) return
    elements.push(
      <ul key={`ul-${elements.length}`} className="space-y-1.5 mb-3">
        {bulletBuffer.map((b, i) => (
          <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
            <span className="w-1.5 h-1.5 rounded-full bg-brand-400 mt-[7px] flex-shrink-0" />
            <span>{b}</span>
          </li>
        ))}
      </ul>
    )
    bulletBuffer = []
  }

  function flushNumbered() {
    if (numberedBuffer.length === 0) return
    elements.push(
      <ol key={`ol-${elements.length}`} className="space-y-2 mb-3">
        {numberedBuffer.map((item, i) => (
          <li key={i} className="flex items-start gap-3 text-sm text-gray-700">
            <span className="w-5 h-5 rounded-full bg-brand-600 text-white text-[10px] font-bold flex items-center justify-center flex-shrink-0 mt-0.5">
              {item.n}
            </span>
            <span>{item.text}</span>
          </li>
        ))}
      </ol>
    )
    numberedBuffer = []
  }

  lines.forEach((line, idx) => {
    const trimmed = line.trim()
    if (!trimmed) {
      flushBullets()
      flushNumbered()
      return
    }

    // H1 / H2 / H3
    const h1 = trimmed.match(/^#{1}\s+(.+)/)
    const h2 = trimmed.match(/^#{2}\s+(.+)/)
    const h3 = trimmed.match(/^#{3,}\s+(.+)/)
    if (h1 && !h2) {
      flushBullets(); flushNumbered()
      elements.push(<h2 key={idx} className="text-base font-semibold text-gray-900 mt-4 mb-2 border-b border-gray-100 pb-1">{h1[1]}</h2>)
      return
    }
    if (h2 && !h3) {
      flushBullets(); flushNumbered()
      elements.push(<h3 key={idx} className="text-sm font-semibold text-gray-800 mt-3 mb-1.5">{h2[1]}</h3>)
      return
    }
    if (h3) {
      flushBullets(); flushNumbered()
      elements.push(<h4 key={idx} className="text-sm font-medium text-brand-700 mt-2 mb-1">{h3[1]}</h4>)
      return
    }

    // Bullet
    const bullet = trimmed.match(/^[-*•]\s+(.+)/)
    if (bullet) {
      flushNumbered()
      bulletBuffer.push(bullet[1])
      return
    }

    // Numbered list
    const numbered = trimmed.match(/^(\d+)[.)]\s+(.+)/)
    if (numbered) {
      flushBullets()
      numberedBuffer.push({ n: numbered[1], text: numbered[2] })
      return
    }

    // Bold line (likely a label)
    const bold = trimmed.match(/^\*\*(.+?)\*\*:?\s*(.*)/)
    if (bold) {
      flushBullets(); flushNumbered()
      elements.push(
        <p key={idx} className="text-sm text-gray-700 mb-1.5">
          <strong className="font-semibold text-gray-900">{bold[1]}</strong>
          {bold[2] ? `: ${bold[2]}` : ''}
        </p>
      )
      return
    }

    // Plain paragraph
    flushBullets(); flushNumbered()
    elements.push(<p key={idx} className="text-sm text-gray-700 mb-2 leading-relaxed">{trimmed}</p>)
  })

  flushBullets()
  flushNumbered()

  return <div className="space-y-0.5">{elements}</div>
}

export default function SiteDetailPage() {
  const params  = useParams()
  const id      = params.id as string

  const [site,      setSite]      = useState<SiteData | null>(null)
  const [analysis,  setAnalysis]  = useState<AnalysisResult | null>(null)
  const [activeLabel, setActiveLabel] = useState<string | null>(null)
  const [analyzing, setAnalyzing] = useState(false)
  const [error,     setError]     = useState('')

  useEffect(() => {
    if (!id) return
    apiFetch<SiteData>(`/api/v1/sites/${id}`)
      .then(setSite)
      .catch(e => setError(e instanceof Error ? e.message : 'Failed to load site'))
  }, [id])

  async function runAnalysis(label: string, engine: string) {
    if (!site) return
    const url = site.url || site.domain || ''
    setAnalyzing(true)
    setAnalysis(null)
    setActiveLabel(label)
    try {
      const result = await apiFetch<AnalysisResult>('/api/v1/ai/complete', {
        method: 'POST',
        body: JSON.stringify({ message: buildPrompt(engine, url), engine, max_tokens: 2048 }),
      })
      setAnalysis(result)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Analysis failed')
    } finally {
      setAnalyzing(false)
    }
  }

  if (error && !site) {
    return (
      <div className="flex items-center gap-3 p-6 bg-red-50 rounded-xl border border-red-100 text-red-600">
        <AlertCircle size={18} />
        <span className="text-sm font-medium">Error: {error}</span>
      </div>
    )
  }

  if (!site) {
    return (
      <div className="flex items-center justify-center h-48 text-gray-400 gap-2">
        <Loader2 size={18} className="animate-spin" />
        <span className="text-sm">Loading site…</span>
      </div>
    )
  }

  const displayUrl = site.url || (site.domain ? `https://${site.domain}` : '')

  return (
    <div className="space-y-6 max-w-4xl">

      {/* Site header */}
      <div className="card p-6">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-brand-50 rounded-xl flex items-center justify-center flex-shrink-0">
              <Globe size={18} className="text-brand-600" />
            </div>
            <div>
              <h1 className="text-lg font-semibold text-gray-900">{site.name}</h1>
              {displayUrl && (
                <a
                  href={displayUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-brand-600 hover:text-brand-700 flex items-center gap-1 mt-0.5"
                >
                  {displayUrl}
                  <ExternalLink size={11} />
                </a>
              )}
            </div>
          </div>
          <span className={`badge ${site.status === 'active' ? 'badge-green' : 'badge-yellow'}`}>
            {site.status}
          </span>
        </div>
        {site.product_summary && (
          <p className="mt-4 text-sm text-gray-500 leading-relaxed border-t border-gray-50 pt-4">
            {site.product_summary}
          </p>
        )}
      </div>

      {/* AI Analysis buttons */}
      <div className="card p-5">
        <div className="mb-4">
          <h2 className="section-title">AI Analysis</h2>
          <p className="text-xs text-gray-400 mt-0.5">Powered by local Qwen3 — private, free, offline-capable</p>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-2.5">
          {ANALYSIS_BUTTONS.map(btn => {
            const Icon = btn.icon
            const isActive = activeLabel === btn.label && analyzing
            return (
              <button
                key={btn.label}
                onClick={() => runAnalysis(btn.label, btn.engine)}
                disabled={analyzing}
                className={`flex items-center gap-2 px-4 py-3 rounded-xl text-sm font-medium text-white transition-all duration-150
                  ${btn.color}
                  ${analyzing ? 'opacity-50 cursor-not-allowed' : 'shadow-sm hover:shadow-md active:scale-[0.98]'}
                `}
              >
                {isActive
                  ? <Loader2 size={14} className="animate-spin flex-shrink-0" />
                  : <Icon size={14} className="flex-shrink-0" />
                }
                <span className="truncate">{isActive ? 'Analyzing…' : btn.label}</span>
              </button>
            )
          })}
        </div>
      </div>

      {/* Analyzing state */}
      {analyzing && (
        <div className="card p-8 text-center">
          <Loader2 size={24} className="animate-spin text-brand-500 mx-auto mb-3" />
          <p className="text-sm font-medium text-gray-700">Running {activeLabel}…</p>
          <p className="text-xs text-gray-400 mt-1">Local Qwen3 model · may take 1–2 minutes</p>
        </div>
      )}

      {/* Results */}
      {analysis && (
        <div className="card p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="section-title">{activeLabel} Results</h2>
            {analysis.model_used && (
              <div className="flex items-center gap-2 text-xs text-gray-400 font-mono">
                <span>{analysis.model_used}</span>
                <span className="text-gray-200">·</span>
                <span>{((analysis.latency_ms || 0) / 1000).toFixed(1)}s</span>
                {analysis.cost_usd !== undefined && (
                  <>
                    <span className="text-gray-200">·</span>
                    <span>${analysis.cost_usd}</span>
                  </>
                )}
              </div>
            )}
          </div>
          {analysis.success ? (
            <AnalysisRenderer content={analysis.raw_content || ''} />
          ) : (
            <div className="flex items-start gap-3 p-4 bg-red-50 rounded-xl border border-red-100 text-red-600">
              <AlertCircle size={16} className="flex-shrink-0 mt-0.5" />
              <span className="text-sm">{analysis.error}</span>
            </div>
          )}
        </div>
      )}

    </div>
  )
}

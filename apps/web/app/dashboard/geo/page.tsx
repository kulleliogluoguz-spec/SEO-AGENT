'use client'

import { useState } from 'react'
import {
  Zap, Info, CheckCircle, AlertCircle, Clock,
  Globe, RefreshCw, ExternalLink, ChevronDown, ChevronUp
} from 'lucide-react'

const GEO_SIGNALS = [
  {
    label:   'Content Citability',
    key:     'citability',
    score:   45,
    weight:  0.30,
    status:  'needs_work',
    notes:   'Add structured FAQ content and clear attributable claims with author attribution.',
    actions: ['Add FAQ sections with question/answer format', 'Include author bylines and credentials', 'Add "TL;DR" summaries to key pages'],
  },
  {
    label:   'AI Crawler Access',
    key:     'ai_crawler',
    score:   80,
    weight:  0.20,
    status:  'good',
    notes:   'robots.txt permits major AI crawlers (GPTBot, ClaudeBot, PerplexityBot).',
    actions: ['Add llms.txt for structured model access', 'Consider AI-specific sitemap'],
  },
  {
    label:   'Structured Markup',
    key:     'schema',
    score:   62,
    weight:  0.20,
    status:  'needs_work',
    notes:   'JSON-LD schema found on homepage. Missing on product and FAQ pages.',
    actions: ['Add FAQPage schema to FAQ content', 'Add Product schema to product pages', 'Add Organization schema sitewide'],
  },
  {
    label:   'Entity Consistency',
    key:     'entity',
    score:   70,
    weight:  0.15,
    status:  'good',
    notes:   'Brand name and description are consistent across main pages.',
    actions: ['Add Wikidata/Crunchbase entity references', 'Ensure consistent NAP across all pages'],
  },
  {
    label:   'llms.txt Present',
    key:     'llms_txt',
    score:   0,
    weight:  0.10,
    status:  'poor',
    notes:   'No llms.txt found. This file allows LLMs to understand your site structure.',
    actions: ['Create /llms.txt with brand description and key pages', 'Include product summaries and use cases'],
  },
  {
    label:   'Canonical Clarity',
    key:     'clarity',
    score:   55,
    weight:  0.05,
    status:  'needs_work',
    notes:   'Canonical tags present on most pages. Some pagination issues detected.',
    actions: ['Audit canonical tags on all paginated URLs', 'Resolve conflicting canonical signals'],
  },
]

const WEIGHTED_SCORE = Math.round(
  GEO_SIGNALS.reduce((sum, s) => sum + s.score * s.weight, 0)
)

const STATUS_META: Record<string, { icon: React.ReactNode; label: string; cls: string }> = {
  good:       { icon: <CheckCircle size={13} />, label: 'Good',       cls: 'text-emerald-500' },
  needs_work: { icon: <Clock       size={13} />, label: 'Needs work', cls: 'text-amber-500'   },
  poor:       { icon: <AlertCircle size={13} />, label: 'Poor',       cls: 'text-red-400'     },
}

function ScoreRing({ score }: { score: number }) {
  const r = 36
  const c = 2 * Math.PI * r
  const offset = c - (score / 100) * c
  const color = score >= 70 ? '#10b981' : score >= 50 ? '#f59e0b' : '#ef4444'

  return (
    <svg width="96" height="96" viewBox="0 0 96 96" className="flex-shrink-0">
      <circle cx="48" cy="48" r={r} fill="none" stroke="#f1f5f9" strokeWidth="8" />
      <circle
        cx="48" cy="48" r={r}
        fill="none"
        stroke={color}
        strokeWidth="8"
        strokeDasharray={c}
        strokeDashoffset={offset}
        strokeLinecap="round"
        transform="rotate(-90 48 48)"
        className="transition-all duration-500"
      />
      <text x="48" y="46" textAnchor="middle" dominantBaseline="middle" fontSize="18" fontWeight="700" fill={color}>
        {score}
      </text>
      <text x="48" y="62" textAnchor="middle" fontSize="9" fill="#94a3b8">/ 100</text>
    </svg>
  )
}

function ScoreBar({ score }: { score: number }) {
  const color = score >= 70 ? 'bg-emerald-400' : score >= 50 ? 'bg-amber-400' : 'bg-red-400'
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all duration-500`} style={{ width: `${score}%` }} />
      </div>
      <span className="text-sm font-semibold text-gray-700 w-7 text-right tabular-nums">{score}</span>
    </div>
  )
}

function SignalCard({ signal }: { signal: typeof GEO_SIGNALS[0] }) {
  const [open, setOpen] = useState(false)
  const meta = STATUS_META[signal.status]

  return (
    <div className="border border-gray-100 rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center gap-4 p-4 hover:bg-gray-50/60 transition-colors text-left"
      >
        <div className={`${meta.cls} flex-shrink-0`}>{meta.icon}</div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1.5">
            <span className="text-sm font-medium text-gray-900">{signal.label}</span>
            <span className={`text-[10px] font-medium ${meta.cls}`}>{meta.label}</span>
          </div>
          <ScoreBar score={signal.score} />
        </div>
        <div className="text-gray-300 flex-shrink-0">
          {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </div>
      </button>

      {open && (
        <div className="px-4 pb-4 pt-0 border-t border-gray-50">
          <p className="text-xs text-gray-500 mb-3 mt-3">{signal.notes}</p>
          <div className="space-y-1.5">
            {signal.actions.map((a, i) => (
              <div key={i} className="flex items-start gap-2 text-xs text-gray-600">
                <span className="w-1 h-1 rounded-full bg-brand-400 mt-1.5 flex-shrink-0" />
                {a}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default function GEOPage() {
  const [running, setRunning] = useState(false)
  const [siteUrl, setSiteUrl] = useState('https://acmegrowth.com')

  async function handleAudit() {
    setRunning(true)
    // POST /api/v1/geo/audit { site_url: siteUrl }
    await new Promise(r => setTimeout(r, 1500))
    setRunning(false)
  }

  return (
    <div className="space-y-6">

      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title flex items-center gap-2.5">
            <Zap size={18} className="text-indigo-500" />
            GEO Audit
          </h1>
          <p className="page-subtitle">AI-engine discoverability for your brand</p>
        </div>
        <div className="flex items-center gap-2">
          <input
            className="input text-sm h-9 w-60"
            value={siteUrl}
            onChange={e => setSiteUrl(e.target.value)}
            placeholder="https://yourdomain.com"
          />
          <button onClick={handleAudit} disabled={running} className="btn-primary">
            <RefreshCw size={13} className={running ? 'animate-spin' : ''} />
            {running ? 'Auditing…' : 'Run Audit'}
          </button>
        </div>
      </div>

      {/* Info banner */}
      <div className="flex items-start gap-3 px-4 py-3 bg-indigo-50 border border-indigo-100 rounded-xl">
        <Info size={14} className="text-indigo-500 flex-shrink-0 mt-0.5" />
        <p className="text-xs text-indigo-700 leading-relaxed">
          <strong>Generative Engine Optimization (GEO)</strong> measures how well AI assistants can
          discover, understand, and cite your brand. Signals are inferred from site structure and
          content — treat as directional guidance while the space matures.
        </p>
      </div>

      {/* Score + summary */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="card p-6 flex items-center gap-6">
          <ScoreRing score={WEIGHTED_SCORE} />
          <div>
            <p className="text-sm font-semibold text-gray-900">AI Visibility Score</p>
            <p className="text-xs text-gray-400 mt-0.5">Weighted across 6 signals</p>
            <div className="mt-3 space-y-1">
              {[
                { label: 'Good (70+)',   count: GEO_SIGNALS.filter(s => s.score >= 70).length, cls: 'bg-emerald-400' },
                { label: 'Needs work',  count: GEO_SIGNALS.filter(s => s.score >= 50 && s.score < 70).length, cls: 'bg-amber-400' },
                { label: 'Poor (<50)',  count: GEO_SIGNALS.filter(s => s.score < 50).length, cls: 'bg-red-400' },
              ].map(row => (
                <div key={row.label} className="flex items-center gap-2 text-xs text-gray-500">
                  <span className={`w-2 h-2 rounded-full ${row.cls}`} />
                  {row.count} {row.label}
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="lg:col-span-2 card p-6">
          <h2 className="section-title mb-3">Priority Actions</h2>
          <div className="space-y-2">
            {[
              { priority: 1, action: 'Create /llms.txt with brand and product descriptions', effort: 'Low', impact: 'High' },
              { priority: 2, action: 'Add FAQPage JSON-LD schema to FAQ content pages',      effort: 'Low', impact: 'High' },
              { priority: 3, action: 'Build structured FAQ content for product queries',      effort: 'Med', impact: 'High' },
              { priority: 4, action: 'Add author attribution and expert credentials',         effort: 'Low', impact: 'Med'  },
            ].map(item => (
              <div key={item.priority} className="flex items-center gap-3 py-2 border-b border-gray-50 last:border-0">
                <span className="w-5 h-5 rounded-full bg-brand-600 text-white text-[10px] font-bold flex items-center justify-center flex-shrink-0">
                  {item.priority}
                </span>
                <span className="text-sm text-gray-700 flex-1">{item.action}</span>
                <span className={`badge text-[10px] ${item.effort === 'Low' ? 'badge-green' : 'badge-yellow'}`}>
                  {item.effort} effort
                </span>
                <span className={`badge text-[10px] ${item.impact === 'High' ? 'badge-purple' : 'badge-blue'}`}>
                  {item.impact} impact
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Signal breakdown */}
      <div className="card p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="section-title">Signal Breakdown</h2>
          <a
            href={`${siteUrl}/robots.txt`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-brand-600 hover:text-brand-700 flex items-center gap-1"
          >
            View robots.txt <ExternalLink size={11} />
          </a>
        </div>
        <div className="space-y-3">
          {GEO_SIGNALS.map(signal => (
            <SignalCard key={signal.key} signal={signal} />
          ))}
        </div>
      </div>

    </div>
  )
}

'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import {
  ArrowLeft, Sparkles, Loader2, CheckCircle,
  Target, Users, TrendingUp, FileText, Zap, Hash,
  Copy, CheckCheck
} from 'lucide-react'
import { apiFetch } from '@/lib/apiFetch'

const OBJECTIVES = [
  { id: 'engagement', label: 'Drive Engagement', icon: Heart, desc: 'Comments, shares, saves' },
  { id: 'awareness', label: 'Build Awareness', icon: Zap, desc: 'Reach new audiences' },
  { id: 'traffic', label: 'Drive Traffic', icon: TrendingUp, desc: 'Clicks to website' },
  { id: 'conversion', label: 'Convert Audience', icon: Target, desc: 'Leads, sales, sign-ups' },
]

const CONTENT_TYPES = [
  { id: 'reel_script', label: 'Reel Script', icon: '🎬' },
  { id: 'carousel', label: 'Carousel Post', icon: '🎨' },
  { id: 'caption', label: 'Post Caption', icon: '✍️' },
  { id: 'story', label: 'Story Series', icon: '📖' },
  { id: 'blog', label: 'Blog Article', icon: '📝' },
  { id: 'landing_page', label: 'Landing Page', icon: '🎯' },
]

function Heart(props: any) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} {...props}>
      <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
    </svg>
  )
}

interface ContentOpportunity {
  theme: string
  description: string
  hook_ideas: string[]
  cta: string
  format_suggestion: string
}

interface AudienceSegment {
  segment_name?: string
  name?: string
  fit_score: number
}

export default function NewContentPage() {
  const router = useRouter()

  // Brand data
  const [opportunities, setOpportunities] = useState<ContentOpportunity[]>([])
  const [audiences, setAudiences] = useState<AudienceSegment[]>([])
  const [brandName, setBrandName] = useState('')
  const [niche, setNiche] = useState('')
  const [loadingIntel, setLoadingIntel] = useState(true)

  // Form state
  const [selectedObjective, setSelectedObjective] = useState('')
  const [selectedType, setSelectedType] = useState('')
  const [selectedOpportunity, setSelectedOpportunity] = useState<ContentOpportunity | null>(null)
  const [selectedAudience, setSelectedAudience] = useState('')
  const [topic, setTopic] = useState('')
  const [keywords, setKeywords] = useState('')
  const [tone, setTone] = useState('conversational')
  const [notes, setNotes] = useState('')

  // Submit state
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState('')

  // AI generate state
  const [generating, setGenerating] = useState(false)
  const [generated, setGenerated] = useState('')
  const [generateSource, setGenerateSource] = useState('')
  const [generateNote, setGenerateNote] = useState('')
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    async function loadIntel() {
      try {
        const [oppData, audData] = await Promise.allSettled([
          apiFetch<{ opportunities: ContentOpportunity[]; brand_name: string; niche: string }>('/api/v1/brand/content-opportunities'),
          apiFetch<{ segments: AudienceSegment[] }>('/api/v1/brand/audience'),
        ])
        if (oppData.status === 'fulfilled') {
          setOpportunities(oppData.value.opportunities ?? [])
          setBrandName(oppData.value.brand_name ?? '')
          setNiche(oppData.value.niche ?? '')
        }
        if (audData.status === 'fulfilled') {
          setAudiences(audData.value.segments ?? [])
        }
      } finally {
        setLoadingIntel(false)
      }
    }
    loadIntel()
  }, [])

  function selectOpportunity(opp: ContentOpportunity) {
    setSelectedOpportunity(opp)
    setTopic(opp.theme)
    if (opp.hook_ideas?.length) {
      setNotes(`Hook ideas:\n${opp.hook_ideas.slice(0, 3).map((h, i) => `${i + 1}. ${h}`).join('\n')}`)
    }
  }

  async function handleGenerate() {
    if (!topic.trim()) { setError('Topic is required to generate'); return }
    setGenerating(true)
    setError('')
    setGenerated('')
    try {
      const data = await apiFetch<{ generated: string; source: string; note: string }>('/api/v1/content/generate-creative', {
        method: 'POST',
        body: JSON.stringify({
          content_type: selectedType || 'caption',
          objective: selectedObjective || 'engagement',
          topic,
          audience: selectedAudience || null,
          tone: tone || 'conversational',
          keywords: keywords || null,
          brand_name: brandName || null,
          niche: niche || null,
          notes: notes || null,
          variations: 3,
        }),
      })
      setGenerated(data.generated || '')
      setGenerateSource(data.source || '')
      setGenerateNote(data.note || '')
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Generation failed'
      if (msg.includes('timed out') || msg.includes('408')) {
        setError('Ollama is not running. Start it with: ollama serve — then run: ollama pull qwen3:8b')
      } else {
        setError(msg)
      }
    } finally {
      setGenerating(false)
    }
  }

  async function handleCopy() {
    if (!generated) return
    await navigator.clipboard.writeText(generated)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  async function handleSubmit() {
    if (!topic.trim()) { setError('Topic is required'); return }
    setSubmitting(true)
    setError('')
    try {
      await apiFetch('/api/v1/content/briefs', {
        method: 'POST',
        body: JSON.stringify({
          site_id: '00000000-0000-0000-0003-000000000001',
          content_type: selectedType || 'blog',
          topic,
          target_keyword: keywords || null,
          tone: tone || 'conversational',
          word_count_target: selectedType === 'blog' ? 800 : null,
          notes: [
            selectedObjective ? `Objective: ${selectedObjective}` : '',
            selectedAudience ? `Target audience: ${selectedAudience}` : '',
            notes,
          ].filter(Boolean).join('\n') || null,
        }),
      })
      setSubmitted(true)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to create brief')
    } finally {
      setSubmitting(false)
    }
  }

  if (submitted) {
    return (
      <div className="max-w-xl mx-auto text-center py-16 space-y-4">
        <div className="w-16 h-16 bg-emerald-100 rounded-2xl flex items-center justify-center mx-auto">
          <CheckCircle className="w-8 h-8 text-emerald-600" />
        </div>
        <h2 className="text-xl font-bold text-gray-900">Content brief created</h2>
        <p className="text-sm text-gray-500">
          Your brief for "<span className="font-medium text-gray-700">{topic}</span>" has been added to the content queue.
        </p>
        <div className="flex items-center justify-center gap-3 pt-2">
          <Link href="/dashboard/content" className="btn-primary">View Content Queue</Link>
          <button onClick={() => { setSubmitted(false); setTopic(''); setSelectedOpportunity(null); setNotes('') }}
            className="btn-secondary">Create Another</button>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-3xl space-y-6">

      {/* Header */}
      <div>
        <Link href="/dashboard/content" className="flex items-center gap-1 text-sm text-gray-400 hover:text-gray-600 mb-4">
          <ArrowLeft size={14} /> Back to Content
        </Link>
        <div className="page-header">
          <div>
            <h1 className="page-title">New Content Brief</h1>
            <p className="page-subtitle">
              {brandName ? `${brandName} · ` : ''}{niche || 'Brand'} — create a content brief for Instagram and beyond
            </p>
          </div>
        </div>
      </div>

      {/* Intelligence — content opportunities */}
      {!loadingIntel && opportunities.length > 0 && (
        <div className="card p-5">
          <div className="flex items-center gap-2 mb-4">
            <Sparkles size={14} className="text-violet-500" />
            <h2 className="section-title">AI-Suggested Opportunities</h2>
            <span className="badge-purple text-[10px]">for your niche</span>
          </div>
          <div className="grid grid-cols-1 gap-3">
            {opportunities.map((opp, i) => (
              <button
                key={i}
                onClick={() => selectOpportunity(opp)}
                className={`text-left p-4 rounded-xl border transition-all ${
                  selectedOpportunity?.theme === opp.theme
                    ? 'bg-violet-50 border-violet-400 ring-1 ring-violet-300'
                    : 'bg-gray-50 border-gray-200 hover:border-violet-300 hover:bg-violet-50/40'
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1">
                    <p className="font-semibold text-sm text-gray-900">{opp.theme}</p>
                    <p className="text-xs text-gray-500 mt-0.5">{opp.description}</p>
                    {opp.hook_ideas?.length > 0 && (
                      <p className="text-xs text-violet-600 mt-1.5 italic">"{opp.hook_ideas[0]}"</p>
                    )}
                  </div>
                  <span className="text-xs text-gray-400 bg-white border border-gray-200 px-2 py-0.5 rounded-full flex-shrink-0">
                    {opp.format_suggestion}
                  </span>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Form */}
      <div className="card p-6 space-y-5">

        {/* Content type */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Content type</label>
          <div className="grid grid-cols-3 gap-2">
            {CONTENT_TYPES.map(ct => (
              <button
                key={ct.id}
                onClick={() => setSelectedType(ct.id)}
                className={`flex items-center gap-2 px-3 py-2.5 rounded-lg border text-sm transition-all ${
                  selectedType === ct.id
                    ? 'bg-brand-50 border-brand-400 text-brand-700'
                    : 'bg-gray-50 border-gray-200 text-gray-600 hover:border-brand-300'
                }`}
              >
                <span>{ct.icon}</span>
                <span className="font-medium">{ct.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Objective */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Objective</label>
          <div className="grid grid-cols-2 gap-2">
            {OBJECTIVES.map(obj => {
              const Icon = obj.icon
              return (
                <button
                  key={obj.id}
                  onClick={() => setSelectedObjective(obj.id)}
                  className={`flex items-start gap-2 px-3 py-2.5 rounded-lg border text-sm transition-all text-left ${
                    selectedObjective === obj.id
                      ? 'bg-emerald-50 border-emerald-400 text-emerald-800'
                      : 'bg-gray-50 border-gray-200 text-gray-600 hover:border-emerald-300'
                  }`}
                >
                  <Icon size={14} className="mt-0.5 flex-shrink-0" />
                  <div>
                    <div className="font-medium">{obj.label}</div>
                    <div className="text-[11px] opacity-70">{obj.desc}</div>
                  </div>
                </button>
              )
            })}
          </div>
        </div>

        {/* Topic */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">
            Topic / Title <span className="text-red-400">*</span>
          </label>
          <input
            type="text"
            value={topic}
            onChange={e => setTopic(e.target.value)}
            placeholder="e.g. 10-minute morning workout for beginners"
            className="input w-full"
          />
        </div>

        {/* Target audience */}
        {audiences.length > 0 && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Target audience segment</label>
            <div className="flex flex-wrap gap-2">
              {audiences.map((seg, i) => {
                const name = seg.segment_name || seg.name || `Segment ${i + 1}`
                return (
                  <button
                    key={i}
                    onClick={() => setSelectedAudience(selectedAudience === name ? '' : name)}
                    className={`px-3 py-1.5 rounded-full text-sm border transition-all ${
                      selectedAudience === name
                        ? 'bg-blue-100 border-blue-400 text-blue-800'
                        : 'bg-gray-50 border-gray-200 text-gray-600 hover:border-blue-300'
                    }`}
                  >
                    <Users size={10} className="inline mr-1" />
                    {name}
                  </button>
                )
              })}
            </div>
          </div>
        )}

        {/* Keywords */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">
            <Hash size={12} className="inline mr-1" />
            Target keyword(s) <span className="text-gray-400 font-normal">(optional)</span>
          </label>
          <input
            type="text"
            value={keywords}
            onChange={e => setKeywords(e.target.value)}
            placeholder="beginner fitness, morning routine, no-gym workout"
            className="input w-full"
          />
        </div>

        {/* Tone */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">Tone</label>
          <select value={tone} onChange={e => setTone(e.target.value)} className="input w-full">
            <option value="conversational">Conversational</option>
            <option value="motivational">Motivational</option>
            <option value="educational">Educational</option>
            <option value="humorous">Humorous</option>
            <option value="authoritative">Authoritative</option>
            <option value="empathetic">Empathetic</option>
          </select>
        </div>

        {/* Notes / hook ideas */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">
            Additional notes / hook ideas <span className="text-gray-400 font-normal">(optional)</span>
          </label>
          <textarea
            rows={4}
            value={notes}
            onChange={e => setNotes(e.target.value)}
            placeholder="Any specific angles, hooks, or directions for this content..."
            className="input w-full resize-none"
          />
        </div>

        {/* AI Generate */}
        <div className="border-t pt-4 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles size={14} className="text-violet-500" />
              <span className="text-sm font-medium text-gray-700">Generate with AI</span>
              <span className="text-[10px] px-1.5 py-0.5 bg-violet-100 text-violet-600 rounded font-semibold">Ollama</span>
            </div>
            <button
              onClick={handleGenerate}
              disabled={generating || !topic.trim()}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-violet-600 text-white rounded-lg text-xs font-medium hover:bg-violet-700 disabled:opacity-40 transition-colors"
            >
              {generating ? (
                <><Loader2 size={11} className="animate-spin" /> Generating…</>
              ) : (
                <><Sparkles size={11} /> Generate Copy</>
              )}
            </button>
          </div>

          {generated && (
            <div className="relative bg-gray-50 border border-gray-200 rounded-xl p-4">
              <div className="flex items-center justify-between mb-2">
                <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${
                  generateSource === 'ollama' ? 'bg-violet-100 text-violet-600' : 'bg-amber-100 text-amber-600'
                }`}>
                  {generateSource === 'ollama' ? 'AI Generated' : 'Template (Ollama offline)'}
                </span>
                <button
                  onClick={handleCopy}
                  className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700"
                >
                  {copied ? <><CheckCheck size={11} className="text-emerald-500" /> Copied!</> : <><Copy size={11} /> Copy</>}
                </button>
              </div>
              <pre className="text-xs text-gray-700 whitespace-pre-wrap font-sans leading-relaxed">{generated}</pre>
              {generateNote && (
                <p className="text-[10px] text-gray-400 mt-2 italic">{generateNote}</p>
              )}
            </div>
          )}
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-3 py-2 text-sm">{error}</div>
        )}

        <div className="flex items-center justify-between pt-2">
          <Link href="/dashboard/content" className="btn-secondary">Cancel</Link>
          <button
            onClick={handleSubmit}
            disabled={submitting || !topic.trim()}
            className="btn-primary flex items-center gap-2 disabled:opacity-40"
          >
            {submitting ? (
              <><Loader2 size={14} className="animate-spin" /> Creating…</>
            ) : (
              <><FileText size={14} /> Save Brief</>
            )}
          </button>
        </div>
      </div>

    </div>
  )
}

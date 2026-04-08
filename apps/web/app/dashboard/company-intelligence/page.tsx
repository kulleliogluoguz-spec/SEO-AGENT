'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import { Brain, CheckCircle, ChevronRight, RefreshCw } from 'lucide-react'
import { apiFetch } from '@/lib/apiFetch'

type Status = 'not_started' | 'in_progress' | 'completed'

type TranscriptMsg = { role: string; content: string; type?: string }

type Profile = {
  company_name?: string | null
  industry?: string | null
  stage?: string | null
  business_model?: string | null
  primary_goal?: string | null
  biggest_challenge?: string | null
  target_customer?: string | null
  avg_order_value?: number | null
  monthly_ad_spend?: number | null
  current_roas?: number | null
  break_even_roas?: number | null
  active_channels?: string[] | null
  ai_summary?: string | null
  discovery_transcript?: TranscriptMsg[] | null
}

type StatusResponse = {
  status: Status
  profile: Profile | null
  question_count: number
}

type StartResponse = {
  question: string
  question_number: number
}

type AnswerResponse = {
  completed: boolean
  next_question: string | null
  question_number: number
  profile: Profile | null
  summary: string | null
}

export default function CompanyIntelligencePage() {
  const [status, setStatus] = useState<Status>('not_started')
  const [question, setQuestion] = useState('')
  const [questionNumber, setQuestionNumber] = useState(0)
  const [answer, setAnswer] = useState('')
  const [profile, setProfile] = useState<Profile | null>(null)
  const [summary, setSummary] = useState('')
  const [loading, setLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [transcript, setTranscript] = useState<TranscriptMsg[]>([])
  const bottomRef = useRef<HTMLDivElement>(null)

  const loadStatus = useCallback(async () => {
    setLoading(true)
    try {
      const d = await apiFetch<StatusResponse>('/api/v1/discovery/status')
      setStatus(d.status)
      if (d.profile) {
        setProfile(d.profile)
        if (d.profile.ai_summary) setSummary(d.profile.ai_summary)
        const t = (d.profile.discovery_transcript ?? []) as TranscriptMsg[]
        setTranscript(t)
        if (d.status === 'in_progress') {
          const lastQ = t.filter((x) => x.role === 'assistant').slice(-1)[0]
          if (lastQ) setQuestion(lastQ.content)
          setQuestionNumber(d.question_count ?? 0)
        }
      }
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadStatus()
  }, [loadStatus])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [transcript])

  async function startDiscovery() {
    setLoading(true)
    try {
      const d = await apiFetch<StartResponse>('/api/v1/discovery/start', {
        method: 'POST',
        body: JSON.stringify({}),
        timeoutMs: 120000,
      })
      setStatus('in_progress')
      setQuestion(d.question)
      setQuestionNumber(1)
      setTranscript([{ role: 'assistant', content: d.question }])
    } finally {
      setLoading(false)
    }
  }

  async function submitAnswer() {
    if (!answer.trim()) return
    setSubmitting(true)
    const userMsg: TranscriptMsg = { role: 'user', content: answer }
    setTranscript((prev) => [...prev, userMsg])
    const submitted = answer
    setAnswer('')

    try {
      const d = await apiFetch<AnswerResponse>('/api/v1/discovery/answer', {
        method: 'POST',
        body: JSON.stringify({ answer: submitted }),
        timeoutMs: 180000,
      })
      if (d.completed) {
        setStatus('completed')
        setProfile(d.profile)
        setSummary(d.summary ?? '')
      } else if (d.next_question) {
        setQuestion(d.next_question)
        setQuestionNumber(d.question_number)
        setTranscript((prev) => [
          ...prev,
          { role: 'assistant', content: d.next_question ?? '' },
        ])
      }
    } finally {
      setSubmitting(false)
    }
  }

  if (loading && status === 'not_started') {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin w-8 h-8 border-4 border-brand-600 border-t-transparent rounded-full" />
      </div>
    )
  }

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-brand-100 flex items-center justify-center">
            <Brain className="text-brand-600" size={20} />
          </div>
          <div>
            <h1 className="text-2xl font-semibold text-slate-900">
              Company Intelligence
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              AI-powered discovery — personalizes all platform recommendations.
            </p>
          </div>
        </div>
        {status === 'completed' && (
          <button
            onClick={startDiscovery}
            className="inline-flex items-center gap-2 px-3 py-2 border border-slate-300 rounded-lg text-sm hover:bg-slate-50"
          >
            <RefreshCw size={14} /> Redo Discovery
          </button>
        )}
      </div>

      {status === 'not_started' && (
        <div className="bg-white rounded-2xl border border-slate-200 p-8 text-center shadow-sm">
          <Brain className="w-16 h-16 text-brand-400 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-slate-900 mb-2">
            Start Company Discovery
          </h2>
          <p className="text-slate-500 mb-6 max-w-md mx-auto">
            Our AI asks 12-20 adaptive questions to deeply understand your business.
            Takes about 15-30 minutes and personalizes all platform recommendations.
          </p>
          <div className="grid grid-cols-3 gap-4 mb-8 text-sm text-slate-600">
            {[
              'Adaptive questions based on your answers',
              'Builds your complete company profile',
              'Personalizes ads, email & AI recommendations',
            ].map((item) => (
              <div key={item} className="flex items-start gap-2">
                <CheckCircle className="w-4 h-4 text-emerald-500 flex-shrink-0 mt-0.5" />
                <span>{item}</span>
              </div>
            ))}
          </div>
          <button
            onClick={startDiscovery}
            disabled={loading}
            className="inline-flex items-center gap-2 bg-brand-600 text-white px-6 py-3 rounded-xl font-medium hover:bg-brand-700"
          >
            <Brain className="w-5 h-5" /> Begin Discovery
          </button>
        </div>
      )}

      {status === 'in_progress' && (
        <div className="space-y-4">
          <div className="bg-white rounded-xl border border-slate-200 p-3 flex items-center gap-3">
            <div className="text-sm text-slate-500">
              Question {questionNumber} of ~15
            </div>
            <div className="flex-1 bg-slate-100 rounded-full h-2">
              <div
                className="bg-brand-500 h-2 rounded-full transition-all"
                style={{ width: `${Math.min((questionNumber / 15) * 100, 95)}%` }}
              />
            </div>
            <div className="text-sm text-slate-400">
              {Math.round((questionNumber / 15) * 100)}%
            </div>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
            <div className="p-4 border-b border-slate-100 bg-slate-50 rounded-t-xl">
              <div className="flex items-center gap-2">
                <Brain className="w-5 h-5 text-brand-600" />
                <span className="font-medium text-slate-800">AI Consultant</span>
              </div>
            </div>
            <div className="p-4 space-y-4 max-h-96 overflow-y-auto">
              {transcript.map((msg, i) => (
                <div
                  key={i}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[80%] rounded-xl px-4 py-3 ${
                      msg.role === 'user'
                        ? 'bg-brand-600 text-white'
                        : 'bg-slate-100 text-slate-800'
                    }`}
                  >
                    {msg.content}
                  </div>
                </div>
              ))}
              {submitting && (
                <div className="flex justify-start">
                  <div className="bg-slate-100 rounded-xl px-4 py-3">
                    <div className="flex gap-1">
                      {[0, 1, 2].map((i) => (
                        <div
                          key={i}
                          className="w-2 h-2 bg-slate-400 rounded-full animate-bounce"
                          style={{ animationDelay: `${i * 0.1}s` }}
                        />
                      ))}
                    </div>
                  </div>
                </div>
              )}
              <div ref={bottomRef} />
            </div>
            <div className="p-4 border-t border-slate-100">
              <div className="flex gap-3">
                <textarea
                  value={answer}
                  onChange={(e) => setAnswer(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault()
                      submitAnswer()
                    }
                  }}
                  placeholder="Type your answer… (Enter to submit)"
                  rows={3}
                  className="flex-1 border border-slate-300 rounded-xl px-4 py-3 text-sm resize-none"
                />
                <button
                  onClick={submitAnswer}
                  disabled={submitting || !answer.trim()}
                  className="bg-brand-600 text-white px-4 py-3 rounded-xl hover:bg-brand-700 disabled:opacity-50 flex items-center"
                >
                  <ChevronRight className="w-5 h-5" />
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {status === 'completed' && profile && (
        <div className="space-y-4">
          <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 flex items-center gap-3">
            <CheckCircle className="w-5 h-5 text-emerald-600" />
            <p className="text-emerald-800 font-medium">
              Discovery complete! Platform is now personalized for{' '}
              {profile.company_name ?? 'your company'}.
            </p>
          </div>

          {summary && (
            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
              <div className="flex items-center gap-2 mb-3">
                <Brain className="w-5 h-5 text-brand-600" />
                <h3 className="font-semibold text-slate-800">AI Business Summary</h3>
              </div>
              <p className="text-slate-700 leading-relaxed whitespace-pre-line text-sm">
                {summary}
              </p>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            {[
              { label: 'Industry', value: profile.industry },
              { label: 'Stage', value: profile.stage },
              { label: 'Business Model', value: profile.business_model },
              { label: 'Primary Goal', value: profile.primary_goal },
              { label: 'Biggest Challenge', value: profile.biggest_challenge },
              { label: 'Target Customer', value: profile.target_customer },
              {
                label: 'Avg Order Value',
                value: profile.avg_order_value ? `$${profile.avg_order_value}` : null,
              },
              {
                label: 'Monthly Ad Spend',
                value: profile.monthly_ad_spend
                  ? `$${profile.monthly_ad_spend?.toLocaleString()}`
                  : null,
              },
              {
                label: 'Current ROAS',
                value: profile.current_roas ? `${profile.current_roas}x` : null,
              },
              {
                label: 'Break-even ROAS',
                value: profile.break_even_roas ? `${profile.break_even_roas}x` : null,
              },
            ]
              .filter((i) => i.value)
              .map((item) => (
                <div
                  key={item.label}
                  className="bg-white rounded-xl border border-slate-200 p-4"
                >
                  <div className="text-xs text-slate-400 mb-1">{item.label}</div>
                  <div className="text-sm font-medium text-slate-800">{item.value}</div>
                </div>
              ))}
          </div>

          {(profile.active_channels?.length ?? 0) > 0 && (
            <div className="bg-white rounded-xl border border-slate-200 p-4">
              <div className="text-xs text-slate-400 mb-2">Active Channels</div>
              <div className="flex flex-wrap gap-2">
                {(profile.active_channels ?? []).map((ch) => (
                  <span
                    key={ch}
                    className="bg-brand-50 text-brand-700 text-sm px-3 py-1 rounded-full border border-brand-200"
                  >
                    {ch}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

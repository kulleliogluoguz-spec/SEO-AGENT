'use client'

import Link from 'next/link'
import {
  Zap, FlaskConical, Star, Target, Send, BarChart3,
  ArrowRight, Brain,
} from 'lucide-react'

const MODULES = [
  {
    icon: FlaskConical,
    color: 'text-violet-500',
    bg: 'bg-violet-500/10',
    name: 'Experiments',
    description: 'Design rigorous A/B tests with structured hypotheses, sample size calculation, and statistical success criteria.',
    example: '"Adding social proof will increase sign-ups by 15%"',
    href: '/dashboard/intelligence/experiments',
    skill: 'ab-test-setup',
  },
  {
    icon: Star,
    color: 'text-amber-500',
    bg: 'bg-amber-500/10',
    name: 'Content Scorer',
    description: '3-expert panel (Copywriter, CRO Specialist, Marketing Psychologist) reviews your content and rewrites it.',
    example: 'Score a landing page, tweet, email, or ad copy',
    href: '/dashboard/intelligence/content',
    skill: 'copywriting + page-cro',
  },
  {
    icon: Target,
    color: 'text-blue-500',
    bg: 'bg-blue-500/10',
    name: 'Sales Pipeline',
    description: 'Define your ICP with scoring criteria, buying triggers, and where to find ideal prospects.',
    example: 'Build a complete ICP profile with scoring rubric',
    href: '/dashboard/intelligence/pipeline',
    skill: 'customer-research',
  },
  {
    icon: Send,
    color: 'text-emerald-500',
    bg: 'bg-emerald-500/10',
    name: 'Outbound Engine',
    description: 'Generate personalized cold outreach and multi-touch sequences. Lead with their problem, not your product.',
    example: 'Write a 5-touch email sequence for a specific role',
    href: '/dashboard/intelligence/outbound',
    skill: 'cold-email',
  },
]

const QUICK_ACTIONS = [
  { label: 'Weekly Scorecard', href: '/dashboard/intelligence/scorecard', icon: BarChart3, color: 'bg-slate-800 hover:bg-slate-700 text-white' },
  { label: 'Score My Content', href: '/dashboard/intelligence/content', icon: Star, color: 'bg-amber-500 hover:bg-amber-600 text-white' },
  { label: 'Create Experiment', href: '/dashboard/intelligence/experiments', icon: FlaskConical, color: 'bg-violet-600 hover:bg-violet-700 text-white' },
  { label: 'Write Outreach', href: '/dashboard/intelligence/outbound', icon: Send, color: 'bg-emerald-600 hover:bg-emerald-700 text-white' },
]

export default function IntelligenceHub() {
  return (
    <div className="max-w-5xl mx-auto space-y-6">

      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-violet-500/10 flex items-center justify-center">
          <Brain size={20} className="text-violet-500" />
        </div>
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Growth Intelligence</h1>
          <p className="text-sm text-slate-500">Powered by AI Marketing Skills — all local, zero external cost</p>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {QUICK_ACTIONS.map(({ label, href, icon: Icon, color }) => (
          <Link key={label} href={href}
            className={`flex items-center gap-2 px-4 py-3 rounded-xl text-sm font-medium transition-colors ${color}`}>
            <Icon size={14} className="flex-shrink-0" />
            {label}
          </Link>
        ))}
      </div>

      {/* Module cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {MODULES.map(({ icon: Icon, color, bg, name, description, example, href, skill }) => (
          <div key={name} className="bg-white border border-slate-200 rounded-xl p-5 flex flex-col gap-4 hover:border-slate-300 transition-colors">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <div className={`w-9 h-9 rounded-lg ${bg} flex items-center justify-center`}>
                  <Icon size={17} className={color} />
                </div>
                <div>
                  <h2 className="text-sm font-semibold text-slate-800">{name}</h2>
                  <span className="text-[10px] font-mono text-slate-400">{skill}</span>
                </div>
              </div>
            </div>
            <p className="text-sm text-slate-600">{description}</p>
            <p className="text-xs text-slate-400 italic">{example}</p>
            <Link href={href}
              className={`mt-auto flex items-center gap-1.5 text-xs font-semibold ${color} hover:opacity-80 transition-opacity`}>
              Open {name} <ArrowRight size={12} />
            </Link>
          </div>
        ))}
      </div>

      {/* Skills banner */}
      <div className="bg-slate-50 border border-slate-200 rounded-xl p-4">
        <p className="text-xs text-slate-500">
          <strong className="text-slate-700">Skills applied:</strong>{' '}
          ab-test-setup · copywriting · page-cro · copy-editing · marketing-psychology · customer-research · cold-email · content-strategy · marketing-ideas
        </p>
        <p className="text-xs text-slate-400 mt-1">
          All AI runs locally via Ollama — no external API calls, no usage fees.
        </p>
      </div>
    </div>
  )
}

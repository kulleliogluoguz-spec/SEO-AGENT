'use client'

import { useState, useEffect } from 'react'
import {
  GitBranch, Loader2, CheckCircle2, AlertCircle, XCircle,
  ExternalLink, Play, Users, FileText, Calendar, Zap,
  Clock, Activity,
} from 'lucide-react'

const API = '/api/v1/workflows'

interface WorkflowInfo {
  id: string
  name: string
  active: boolean
  created: string
}

interface Overview {
  total_workflows: number
  active_workflows: number
  workflows: WorkflowInfo[]
  n8n_editor: string
  status: string
}

interface Execution {
  id: string
  workflow_name: string
  status: string
  started: string
  finished: string
}

interface InstallResult {
  success: boolean
  workflow_id?: string
  workflow_name?: string
  webhook_url?: string
  n8n_url?: string
  schedule?: string
  error?: string
}

interface SetupAllResult {
  workflows_created: number
  total_attempted: number
  results: {
    contact_automation: InstallResult
    content_auto_score: InstallResult
    weekly_scorecard: InstallResult
  }
  n8n_editor: string
}

const WORKFLOW_CARDS = [
  {
    key: 'contact_automation' as const,
    endpoint: '/setup/contact-automation',
    title: 'New Contact Automation',
    description: 'When a contact is added → adds to Mautic → sends welcome email sequence',
    flow: 'Platform → Mautic → Email',
    icon: Users,
    color: 'blue',
  },
  {
    key: 'content_auto_score' as const,
    endpoint: '/setup/content-auto-score',
    title: 'Content Auto-Score',
    description: 'When content is generated → scores it with 3 AI experts → posts if score > 80',
    flow: 'Content → Scorer → Social',
    icon: FileText,
    color: 'amber',
  },
  {
    key: 'weekly_scorecard' as const,
    endpoint: '/setup/weekly-scorecard',
    title: 'Weekly Scorecard',
    description: 'Every Monday 9am → automatically generates your growth scorecard',
    flow: 'Schedule → Scorecard → Report',
    icon: Calendar,
    color: 'emerald',
  },
]

const COLOR_MAP = {
  blue: { icon: 'bg-blue-500/10 text-blue-500', badge: 'bg-blue-100 text-blue-700', ring: 'ring-blue-200' },
  amber: { icon: 'bg-amber-500/10 text-amber-500', badge: 'bg-amber-100 text-amber-700', ring: 'ring-amber-200' },
  emerald: { icon: 'bg-emerald-500/10 text-emerald-500', badge: 'bg-emerald-100 text-emerald-700', ring: 'ring-emerald-200' },
}

function StatusBadge({ status }: { status: string }) {
  if (status === 'success') return <span className="flex items-center gap-1 text-xs font-medium text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded-full"><CheckCircle2 size={10} /> Success</span>
  if (status === 'error') return <span className="flex items-center gap-1 text-xs font-medium text-red-700 bg-red-100 px-2 py-0.5 rounded-full"><XCircle size={10} /> Failed</span>
  if (status === 'running') return <span className="flex items-center gap-1 text-xs font-medium text-blue-700 bg-blue-100 px-2 py-0.5 rounded-full"><Activity size={10} className="animate-pulse" /> Running</span>
  return <span className="text-xs text-slate-500">{status}</span>
}

export default function WorkflowsPage() {
  const [health, setHealth] = useState<{ status: string; n8n_url?: string; hint?: string } | null>(null)
  const [overview, setOverview] = useState<Overview | null>(null)
  const [executions, setExecutions] = useState<Execution[]>([])
  const [installedIds, setInstalledIds] = useState<Record<string, string>>({})
  const [installing, setInstalling] = useState<Record<string, boolean>>({})
  const [installAll, setInstallAll] = useState(false)
  const [installAllResult, setInstallAllResult] = useState<SetupAllResult | null>(null)
  const [triggerEmail, setTriggerEmail] = useState('')
  const [triggerContent, setTriggerContent] = useState('')
  const [triggerLoading, setTriggerLoading] = useState<Record<string, boolean>>({})
  const [triggerResult, setTriggerResult] = useState<Record<string, string>>({})

  useEffect(() => {
    fetch(`${API}/health`).then(r => r.json()).then(setHealth).catch(() => setHealth({ status: 'offline' }))
    fetch(`${API}/overview`).then(r => r.json()).then(setOverview).catch(() => {})
    fetch(`${API}/executions?limit=10`).then(r => r.json()).then(d => setExecutions(d.executions || [])).catch(() => {})
  }, [])

  async function installWorkflow(key: string, endpoint: string) {
    setInstalling(p => ({ ...p, [key]: true }))
    try {
      const res = await fetch(`${API}${endpoint}`, { method: 'POST' })
      const data: InstallResult = await res.json()
      if (data.success && data.workflow_id) {
        setInstalledIds(p => ({ ...p, [key]: data.workflow_id! }))
        setOverview(prev => prev ? { ...prev, total_workflows: prev.total_workflows + 1, active_workflows: prev.active_workflows + 1 } : prev)
      }
    } finally {
      setInstalling(p => ({ ...p, [key]: false }))
    }
  }

  async function installAll_() {
    setInstallAll(true)
    try {
      const res = await fetch(`${API}/setup/all`, { method: 'POST' })
      const data: SetupAllResult = await res.json()
      setInstallAllResult(data)
      const newIds: Record<string, string> = {}
      for (const [k, v] of Object.entries(data.results)) {
        if (v.success && v.workflow_id) newIds[k] = v.workflow_id
      }
      setInstalledIds(p => ({ ...p, ...newIds }))
      setOverview(prev => prev ? {
        ...prev,
        total_workflows: prev.total_workflows + data.workflows_created,
        active_workflows: prev.active_workflows + data.workflows_created,
      } : prev)
    } finally {
      setInstallAll(false)
    }
  }

  async function triggerContact() {
    if (!triggerEmail) return
    setTriggerLoading(p => ({ ...p, contact: true }))
    try {
      const res = await fetch(`${API}/trigger/new-contact?email=${encodeURIComponent(triggerEmail)}&business_type=saas`, { method: 'POST' })
      const d = await res.json()
      setTriggerResult(p => ({ ...p, contact: d.triggered ? '✓ Triggered!' : `✗ ${d.error || d.status}` }))
    } finally {
      setTriggerLoading(p => ({ ...p, contact: false }))
    }
  }

  async function triggerContentScore() {
    if (!triggerContent) return
    setTriggerLoading(p => ({ ...p, content: true }))
    try {
      const res = await fetch(`${API}/trigger/content-score?content=${encodeURIComponent(triggerContent)}&content_type=tweet&business_type=saas`, { method: 'POST' })
      const d = await res.json()
      setTriggerResult(p => ({ ...p, content: d.triggered ? '✓ Triggered!' : `✗ ${d.error || d.status}` }))
    } finally {
      setTriggerLoading(p => ({ ...p, content: false }))
    }
  }

  const isConnected = health?.status === 'connected'

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-violet-500/10 flex items-center justify-center">
          <GitBranch size={20} className="text-violet-500" />
        </div>
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Workflow Automation</h1>
          <p className="text-sm text-slate-500">Connect all platform features into automated pipelines — powered by n8n</p>
        </div>
      </div>

      {/* n8n Status Banner */}
      {health && (
        <div className={`flex items-center justify-between p-4 rounded-xl border ${
          isConnected
            ? 'bg-emerald-50 border-emerald-200'
            : 'bg-red-50 border-red-200'
        }`}>
          <div className="flex items-center gap-3">
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'}`} />
            {isConnected ? (
              <p className="text-sm font-medium text-emerald-800">n8n Connected</p>
            ) : (
              <div>
                <p className="text-sm font-medium text-red-800">n8n Offline</p>
                {health.hint && <p className="text-xs text-red-600 mt-0.5 font-mono">{health.hint}</p>}
              </div>
            )}
          </div>
          {isConnected && (
            <a
              href="http://localhost:5678"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-emerald-100 hover:bg-emerald-200 text-emerald-800 rounded-lg transition-colors"
            >
              Open n8n Editor <ExternalLink size={11} />
            </a>
          )}
        </div>
      )}

      {/* Stats Row */}
      {overview && (
        <div className="grid grid-cols-3 gap-4">
          {[
            { label: 'Total Workflows', value: overview.total_workflows },
            { label: 'Active Workflows', value: overview.active_workflows },
            { label: 'Recent Executions', value: executions.length },
          ].map(({ label, value }) => (
            <div key={label} className="bg-white border border-slate-200 rounded-xl p-4 text-center">
              <p className="text-2xl font-bold text-slate-800">{value}</p>
              <p className="text-xs text-slate-500 mt-0.5">{label}</p>
            </div>
          ))}
        </div>
      )}

      {/* Install All Button */}
      <div className="bg-gradient-to-r from-violet-600 to-indigo-600 rounded-xl p-5">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold text-white">Install All Workflows</h2>
            <p className="text-sm text-violet-200 mt-0.5">Set up all 3 pre-built automations in one click</p>
          </div>
          <button
            onClick={installAll_}
            disabled={installAll || !isConnected}
            className="flex items-center gap-2 px-5 py-2.5 bg-white text-violet-700 text-sm font-bold rounded-xl hover:bg-violet-50 transition-colors disabled:opacity-50"
          >
            {installAll ? <Loader2 size={15} className="animate-spin" /> : <Zap size={15} />}
            {installAll ? 'Installing…' : 'Install All'}
          </button>
        </div>
        {installAllResult && (
          <div className="mt-4 grid grid-cols-3 gap-2">
            {Object.entries(installAllResult.results).map(([key, r]) => (
              <div key={key} className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium ${r.success ? 'bg-white/20 text-white' : 'bg-red-500/30 text-red-100'}`}>
                {r.success ? <CheckCircle2 size={12} /> : <XCircle size={12} />}
                <span className="truncate">{key.replace(/_/g, ' ')}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Workflow Cards */}
      <div>
        <h2 className="text-sm font-semibold text-slate-700 mb-3">Pre-built Workflows</h2>
        <div className="grid grid-cols-1 gap-4">
          {WORKFLOW_CARDS.map(card => {
            const colors = COLOR_MAP[card.color as keyof typeof COLOR_MAP]
            const installed = !!installedIds[card.key]
            const isInstalling = installing[card.key]
            const Icon = card.icon
            return (
              <div key={card.key} className={`bg-white border border-slate-200 rounded-xl p-5 ${installed ? `ring-1 ${colors.ring}` : ''}`}>
                <div className="flex items-start gap-4">
                  <div className={`w-10 h-10 rounded-xl ${colors.icon} flex items-center justify-center flex-shrink-0`}>
                    <Icon size={18} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="text-sm font-semibold text-slate-800">{card.title}</h3>
                      {installed && (
                        <span className={`text-[10px] px-1.5 py-0.5 rounded font-semibold ${colors.badge}`}>ACTIVE</span>
                      )}
                    </div>
                    <p className="text-xs text-slate-500 mb-2">{card.description}</p>
                    <span className={`inline-block text-[10px] px-2 py-0.5 rounded-full font-medium ${colors.badge}`}>
                      {card.flow}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    {installed && installedIds[card.key] && (
                      <a
                        href={`http://localhost:5678/workflow/${installedIds[card.key]}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
                      >
                        Open <ExternalLink size={10} />
                      </a>
                    )}
                    <button
                      onClick={() => installWorkflow(card.key, card.endpoint)}
                      disabled={isInstalling || installed || !isConnected}
                      className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold rounded-lg transition-colors disabled:opacity-50 ${
                        installed
                          ? 'bg-slate-100 text-slate-400 cursor-default'
                          : 'bg-slate-800 hover:bg-slate-900 text-white'
                      }`}
                    >
                      {isInstalling ? <Loader2 size={11} className="animate-spin" /> : installed ? <CheckCircle2 size={11} /> : <Play size={11} />}
                      {installed ? 'Installed' : isInstalling ? 'Installing…' : 'Install'}
                    </button>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Manual Triggers */}
      <div className="bg-white border border-slate-200 rounded-xl p-5">
        <h2 className="text-sm font-semibold text-slate-700 mb-4">Manual Triggers</h2>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Test Contact Automation</label>
            <div className="flex gap-2">
              <input
                className="flex-1 px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-violet-500/20"
                placeholder="test@example.com"
                value={triggerEmail}
                onChange={e => setTriggerEmail(e.target.value)}
              />
              <button
                onClick={triggerContact}
                disabled={triggerLoading.contact || !triggerEmail || !isConnected}
                className="flex items-center gap-1 px-3 py-2 bg-slate-800 hover:bg-slate-900 text-white text-xs font-bold rounded-lg transition-colors disabled:opacity-50"
              >
                {triggerLoading.contact ? <Loader2 size={12} className="animate-spin" /> : <Play size={12} />}
              </button>
            </div>
            {triggerResult.contact && (
              <p className={`text-xs mt-1.5 font-medium ${triggerResult.contact.startsWith('✓') ? 'text-emerald-600' : 'text-red-500'}`}>
                {triggerResult.contact}
              </p>
            )}
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Test Content Scoring</label>
            <div className="flex gap-2">
              <input
                className="flex-1 px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-violet-500/20"
                placeholder="Enter content to score…"
                value={triggerContent}
                onChange={e => setTriggerContent(e.target.value)}
              />
              <button
                onClick={triggerContentScore}
                disabled={triggerLoading.content || !triggerContent || !isConnected}
                className="flex items-center gap-1 px-3 py-2 bg-slate-800 hover:bg-slate-900 text-white text-xs font-bold rounded-lg transition-colors disabled:opacity-50"
              >
                {triggerLoading.content ? <Loader2 size={12} className="animate-spin" /> : <Play size={12} />}
              </button>
            </div>
            {triggerResult.content && (
              <p className={`text-xs mt-1.5 font-medium ${triggerResult.content.startsWith('✓') ? 'text-emerald-600' : 'text-red-500'}`}>
                {triggerResult.content}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Recent Executions */}
      {executions.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <h2 className="text-sm font-semibold text-slate-700 mb-3">Recent Executions</h2>
          <div className="space-y-2">
            {executions.map(exec => (
              <div key={exec.id} className="flex items-center gap-3 py-2 border-b border-slate-100 last:border-0">
                <StatusBadge status={exec.status} />
                <p className="text-sm text-slate-700 flex-1 truncate">{exec.workflow_name}</p>
                <div className="flex items-center gap-1.5 text-xs text-slate-400 flex-shrink-0">
                  <Clock size={10} />
                  {exec.started ? new Date(exec.started).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—'}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* n8n Editor Launch */}
      <div className="bg-white border border-slate-200 rounded-xl p-6">
        <h2 className="text-sm font-semibold text-slate-700 mb-1">n8n Workflow Editor</h2>
        <p className="text-xs text-slate-500 mb-4">n8n sets strict framing headers — open it in a new tab for the full editor experience.</p>
        {isConnected ? (
          <a
            href="http://localhost:5678"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-violet-600 hover:bg-violet-700 text-white text-sm font-semibold rounded-xl transition-colors"
          >
            <ExternalLink size={14} />
            Open n8n Editor
          </a>
        ) : (
          <div className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg border border-slate-200">
            <AlertCircle size={14} className="text-slate-400 flex-shrink-0" />
            <p className="text-xs text-slate-500">n8n is offline — <code className="bg-slate-100 px-1 rounded">cd apps/n8n &amp;&amp; docker compose up -d</code></p>
          </div>
        )}
      </div>
    </div>
  )
}

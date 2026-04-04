'use client'

import { useState, useEffect, useCallback } from 'react'
import Link from 'next/link'
import {
  Mail, Users, Layers, Megaphone, ExternalLink,
  CheckCircle2, AlertCircle, Loader2, RefreshCw,
  Zap, RotateCcw, Plus, TrendingUp,
} from 'lucide-react'

const API = 'http://localhost:8000/api/v1/email'

interface HealthStatus { status: string; mautic_url: string; details?: string }
interface Overview {
  total_contacts: number
  total_campaigns: number
  total_emails: number
  active_campaigns: number
  mautic_dashboard: string
  status: string
}
interface EmailItem {
  id: number
  name: string
  subject: string
  isPublished: boolean
}

export default function EmailHubPage() {
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [overview, setOverview] = useState<Overview | null>(null)
  const [emails, setEmails] = useState<EmailItem[]>([])
  const [loading, setLoading] = useState(true)
  const [contactEmail, setContactEmail] = useState('')
  const [contactFirst, setContactFirst] = useState('')
  const [addingContact, setAddingContact] = useState(false)
  const [addMsg, setAddMsg] = useState<{ type: 'ok' | 'err'; text: string } | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [h, o, e] = await Promise.all([
        fetch(`${API}/health`).then(r => r.json()).catch(() => ({ status: 'error', mautic_url: 'http://localhost:8181' })),
        fetch(`${API}/stats/overview`).then(r => r.json()).catch(() => null),
        fetch(`${API}/emails`).then(r => r.json()).catch(() => ({ emails: [] })),
      ])
      setHealth(h)
      setOverview(o)
      setEmails((e?.emails ?? []).slice(0, 8))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  async function addContact() {
    if (!contactEmail) return
    setAddingContact(true)
    setAddMsg(null)
    try {
      const res = await fetch(`${API}/contacts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: contactEmail, firstname: contactFirst }),
      })
      const data = await res.json()
      if (data.contact) {
        setAddMsg({ type: 'ok', text: `Contact ${contactEmail} added to Mautic.` })
        setContactEmail(''); setContactFirst('')
        load()
      } else {
        setAddMsg({ type: 'err', text: data.error || 'Failed to add contact' })
      }
    } catch {
      setAddMsg({ type: 'err', text: 'Network error' })
    } finally {
      setAddingContact(false)
    }
  }

  const connected = health?.status === 'connected'

  return (
    <div className="max-w-5xl mx-auto space-y-6">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-blue-500/10 flex items-center justify-center">
            <Mail size={20} className="text-blue-500" />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-slate-900">Email Hub</h1>
            <p className="text-sm text-slate-500">Self-hosted email automation powered by Mautic</p>
          </div>
        </div>
        <button onClick={load} className="p-2 rounded-lg hover:bg-gray-100 text-gray-400 transition-colors" title="Refresh">
          <RefreshCw size={14} />
        </button>
      </div>

      {/* Status banner */}
      {loading ? (
        <div className="flex items-center gap-3 p-4 bg-gray-50 border border-gray-200 rounded-xl">
          <Loader2 size={16} className="animate-spin text-gray-400" />
          <span className="text-sm text-gray-500">Checking Mautic connection…</span>
        </div>
      ) : connected ? (
        <div className="flex items-center justify-between p-4 bg-emerald-50 border border-emerald-200 rounded-xl">
          <div className="flex items-center gap-2.5">
            <CheckCircle2 size={16} className="text-emerald-600 flex-shrink-0" />
            <span className="text-sm font-medium text-emerald-800">Mautic Connected — Email automation is active</span>
          </div>
          <a
            href="http://localhost:8181"
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1.5 text-xs font-semibold text-emerald-700 hover:text-emerald-900 transition-colors"
          >
            Open Mautic <ExternalLink size={11} />
          </a>
        </div>
      ) : (
        <div className="flex items-center justify-between p-4 bg-red-50 border border-red-200 rounded-xl">
          <div className="flex items-center gap-2.5">
            <AlertCircle size={16} className="text-red-500 flex-shrink-0" />
            <div>
              <span className="text-sm font-medium text-red-800">Mautic Offline</span>
              <p className="text-xs text-red-600 mt-0.5">
                Start it: <code className="bg-red-100 px-1 rounded">cd apps/mautic && docker compose up -d</code>
              </p>
            </div>
          </div>
          <button onClick={load} className="flex items-center gap-1.5 text-xs font-semibold text-red-600 hover:text-red-800 transition-colors">
            <RotateCcw size={11} /> Retry
          </button>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: 'Contacts', value: overview?.total_contacts ?? '—', icon: Users, color: 'text-blue-500', bg: 'bg-blue-50' },
          { label: 'Campaigns', value: overview?.total_campaigns ?? '—', icon: Megaphone, color: 'text-violet-500', bg: 'bg-violet-50' },
          { label: 'Email Templates', value: overview?.total_emails ?? '—', icon: Mail, color: 'text-emerald-500', bg: 'bg-emerald-50' },
          { label: 'Active Campaigns', value: overview?.active_campaigns ?? '—', icon: TrendingUp, color: 'text-amber-500', bg: 'bg-amber-50' },
        ].map(({ label, value, icon: Icon, color, bg }) => (
          <div key={label} className="bg-white border border-slate-200 rounded-xl p-4">
            <div className={`w-8 h-8 rounded-lg ${bg} flex items-center justify-center mb-3`}>
              <Icon size={15} className={color} />
            </div>
            <div className="text-2xl font-bold text-slate-900">{value}</div>
            <div className="text-xs text-slate-500 mt-0.5">{label}</div>
          </div>
        ))}
      </div>

      {/* Quick actions */}
      <div className="bg-white border border-slate-200 rounded-xl p-5">
        <h2 className="text-sm font-semibold text-slate-700 mb-4">Quick Actions</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {[
            { label: 'Generate Welcome Sequence', href: '/dashboard/email/sequences?type=welcome', icon: Zap, color: 'bg-blue-500 hover:bg-blue-600 text-white' },
            { label: 'Generate Cart Recovery', href: '/dashboard/email/sequences?type=abandoned_cart', icon: Layers, color: 'bg-violet-500 hover:bg-violet-600 text-white' },
            { label: 'Generate Re-engagement', href: '/dashboard/email/sequences?type=re_engagement', icon: RotateCcw, color: 'bg-amber-500 hover:bg-amber-600 text-white' },
            { label: 'Generate Nurture Series', href: '/dashboard/email/sequences?type=nurture', icon: TrendingUp, color: 'bg-emerald-500 hover:bg-emerald-600 text-white' },
            { label: 'Manage Contacts', href: '/dashboard/email/contacts', icon: Users, color: 'bg-slate-100 hover:bg-slate-200 text-slate-700' },
            { label: 'Open Mautic', href: 'http://localhost:8181', icon: ExternalLink, color: 'bg-slate-100 hover:bg-slate-200 text-slate-700', external: true },
          ].map(({ label, href, icon: Icon, color, external }) => (
            external ? (
              <a key={label} href={href} target="_blank" rel="noreferrer"
                className={`flex items-center gap-2 px-4 py-3 rounded-xl text-sm font-medium transition-colors ${color}`}>
                <Icon size={14} className="flex-shrink-0" />
                {label}
              </a>
            ) : (
              <Link key={label} href={href}
                className={`flex items-center gap-2 px-4 py-3 rounded-xl text-sm font-medium transition-colors ${color}`}>
                <Icon size={14} className="flex-shrink-0" />
                {label}
              </Link>
            )
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Quick add contact */}
        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <h2 className="text-sm font-semibold text-slate-700 mb-4 flex items-center gap-2">
            <Plus size={14} className="text-blue-500" /> Quick Add Contact
          </h2>
          <div className="space-y-3">
            <input
              className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-400"
              placeholder="Email address"
              value={contactEmail}
              onChange={e => setContactEmail(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && addContact()}
            />
            <input
              className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-400"
              placeholder="First name (optional)"
              value={contactFirst}
              onChange={e => setContactFirst(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && addContact()}
            />
            <button
              onClick={addContact}
              disabled={addingContact || !contactEmail}
              className="w-full flex items-center justify-center gap-2 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-lg transition-colors disabled:opacity-50"
            >
              {addingContact ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
              {addingContact ? 'Adding…' : 'Add to Mautic'}
            </button>
            {addMsg && (
              <div className={`flex items-center gap-2 text-xs px-3 py-2 rounded-lg ${addMsg.type === 'ok' ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'}`}>
                {addMsg.type === 'ok' ? <CheckCircle2 size={12} /> : <AlertCircle size={12} />}
                {addMsg.text}
              </div>
            )}
          </div>
        </div>

        {/* Recent emails */}
        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-slate-700">Recent Email Templates</h2>
            <a href="http://localhost:8181/s/emails" target="_blank" rel="noreferrer"
              className="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1">
              All in Mautic <ExternalLink size={10} />
            </a>
          </div>
          {emails.length === 0 ? (
            <div className="text-center py-8">
              <Mail size={24} className="text-slate-200 mx-auto mb-2" />
              <p className="text-xs text-slate-400">No emails yet — generate a sequence to get started</p>
            </div>
          ) : (
            <div className="divide-y divide-slate-100">
              {emails.map(e => (
                <div key={e.id} className="flex items-center gap-3 py-2.5">
                  <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${e.isPublished ? 'bg-emerald-400' : 'bg-slate-300'}`} />
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-slate-700 truncate">{e.name}</p>
                    <p className="text-[11px] text-slate-400 truncate">{e.subject}</p>
                  </div>
                  <a href={`http://localhost:8181/s/emails/${e.id}/edit`} target="_blank" rel="noreferrer"
                    className="text-[11px] text-blue-500 hover:text-blue-700 flex-shrink-0 flex items-center gap-0.5">
                    Edit <ExternalLink size={9} />
                  </a>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Mautic iframe */}
      {connected && (
        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
          <div className="flex items-center justify-between px-5 py-3 border-b border-slate-100">
            <h2 className="text-sm font-semibold text-slate-700">Mautic Dashboard</h2>
            <a href="http://localhost:8181/s/dashboard" target="_blank" rel="noreferrer"
              className="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1">
              Open full screen <ExternalLink size={10} />
            </a>
          </div>
          <iframe
            src="http://localhost:8181/s/dashboard"
            style={{ width: '100%', height: '600px', border: 'none' }}
            title="Mautic Dashboard"
          />
        </div>
      )}
    </div>
  )
}

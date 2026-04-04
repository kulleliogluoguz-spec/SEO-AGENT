'use client'

import { useState, useEffect } from 'react'
import { Building2, ExternalLink, UserCheck, Handshake, PieChart, AlertCircle } from 'lucide-react'
import Link from 'next/link'

const API = '/api/v1/crm'

interface Health {
  status: string
  twenty_url?: string
  action?: string
  hint?: string
  user?: { id: string; email: string }
}

interface Overview {
  total_contacts: number
  total_companies: number
  total_opportunities: number
  status: string
}

export default function CRMHubPage() {
  const [health, setHealth] = useState<Health | null>(null)
  const [overview, setOverview] = useState<Overview | null>(null)

  useEffect(() => {
    fetch(`${API}/health`).then(r => r.json()).then(setHealth).catch(() => setHealth({ status: 'offline' }))
    fetch(`${API}/stats/overview`).then(r => r.json()).then(setOverview).catch(() => {})
  }, [])

  const isConnected = health?.status === 'connected'
  const isNotConfigured = health?.status === 'not_configured'
  const isOffline = health?.status === 'offline'

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-indigo-500/10 flex items-center justify-center">
          <Building2 size={20} className="text-indigo-500" />
        </div>
        <div>
          <h1 className="text-xl font-semibold text-slate-900">CRM</h1>
          <p className="text-sm text-slate-500">Manage leads, contacts, and deals — powered by Twenty CRM</p>
        </div>
      </div>

      {/* Status Banner */}
      {health && (
        <div className={`flex items-center justify-between p-4 rounded-xl border ${
          isConnected ? 'bg-emerald-50 border-emerald-200' :
          isNotConfigured ? 'bg-amber-50 border-amber-200' :
          'bg-red-50 border-red-200'
        }`}>
          <div className="flex items-start gap-3">
            <div className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${
              isConnected ? 'bg-emerald-500 animate-pulse' :
              isNotConfigured ? 'bg-amber-500' : 'bg-red-500'
            }`} />
            <div>
              {isConnected && (
                <p className="text-sm font-medium text-emerald-800">
                  Twenty CRM Connected{health.user ? ` — ${health.user.email}` : ''}
                </p>
              )}
              {isNotConfigured && (
                <>
                  <p className="text-sm font-medium text-amber-800">API Key Required</p>
                  <p className="text-xs text-amber-700 mt-0.5">{health.action}</p>
                </>
              )}
              {isOffline && (
                <>
                  <p className="text-sm font-medium text-red-800">Twenty CRM Offline</p>
                  {health.hint && <p className="text-xs text-red-600 font-mono mt-0.5">{health.hint}</p>}
                </>
              )}
            </div>
          </div>
          <a
            href="http://localhost:3333"
            target="_blank"
            rel="noopener noreferrer"
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg transition-colors flex-shrink-0 ${
              isConnected ? 'bg-emerald-100 hover:bg-emerald-200 text-emerald-800' :
              'bg-slate-100 hover:bg-slate-200 text-slate-600'
            }`}
          >
            Open Twenty <ExternalLink size={11} />
          </a>
        </div>
      )}

      {/* Stats */}
      {overview && (
        <div className="grid grid-cols-3 gap-4">
          {[
            { label: 'Contacts', value: overview.total_contacts, href: '/dashboard/crm/contacts', icon: UserCheck, color: 'text-blue-600' },
            { label: 'Companies', value: overview.total_companies, href: '/dashboard/crm/companies', icon: Building2, color: 'text-indigo-600' },
            { label: 'Deals', value: overview.total_opportunities, href: '/dashboard/crm/deals', icon: Handshake, color: 'text-emerald-600' },
          ].map(({ label, value, href, icon: Icon, color }) => (
            <Link key={label} href={href}
              className="bg-white border border-slate-200 rounded-xl p-5 hover:border-slate-300 hover:shadow-sm transition-all">
              <div className="flex items-center justify-between mb-3">
                <p className="text-xs font-medium text-slate-500">{label}</p>
                <Icon size={14} className={color} />
              </div>
              <p className={`text-3xl font-bold ${color}`}>{value}</p>
            </Link>
          ))}
        </div>
      )}

      {/* Quick Actions */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <h2 className="text-sm font-semibold text-slate-700 mb-3">Quick Actions</h2>
          <div className="space-y-2">
            {[
              { label: 'Add Contact', href: '/dashboard/crm/contacts', icon: UserCheck },
              { label: 'Add Company', href: '/dashboard/crm/companies', icon: Building2 },
              { label: 'View Pipeline', href: '/dashboard/crm/deals', icon: Handshake },
              { label: 'Growth Intelligence', href: '/dashboard/intelligence/outbound', icon: PieChart },
            ].map(({ label, href, icon: Icon }) => (
              <Link key={label} href={href}
                className="flex items-center gap-2.5 px-3 py-2 rounded-lg hover:bg-slate-50 text-sm text-slate-700 transition-colors">
                <Icon size={14} className="text-slate-400" />
                {label}
              </Link>
            ))}
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <h2 className="text-sm font-semibold text-slate-700 mb-3">CRM Setup</h2>
          <div className="space-y-3 text-xs text-slate-600">
            <div className={`flex items-center gap-2 ${isConnected || isNotConfigured || isOffline ? '' : 'text-slate-400'}`}>
              <div className={`w-4 h-4 rounded-full flex items-center justify-center text-white text-[9px] font-bold flex-shrink-0 ${
                isConnected || isNotConfigured || isOffline ? 'bg-emerald-500' : 'bg-slate-300'
              }`}>1</div>
              Twenty CRM running at port 3333
            </div>
            <div className={`flex items-center gap-2 ${isConnected ? '' : 'text-slate-400'}`}>
              <div className={`w-4 h-4 rounded-full flex items-center justify-center text-white text-[9px] font-bold flex-shrink-0 ${
                isNotConfigured ? 'bg-amber-500' : isConnected ? 'bg-emerald-500' : 'bg-slate-300'
              }`}>2</div>
              <span>
                {isNotConfigured
                  ? 'Get API key: Twenty → Settings → API'
                  : 'API key configured in .env'}
              </span>
            </div>
            <div className={`flex items-center gap-2 ${isConnected ? '' : 'text-slate-400'}`}>
              <div className={`w-4 h-4 rounded-full flex items-center justify-center text-white text-[9px] font-bold flex-shrink-0 ${
                isConnected ? 'bg-emerald-500' : 'bg-slate-300'
              }`}>3</div>
              CRM connected to platform
            </div>
          </div>
          {isNotConfigured && (
            <div className="mt-3 p-2.5 bg-amber-50 rounded-lg border border-amber-200">
              <p className="text-[10px] font-mono text-amber-800">TWENTY_API_KEY=&lt;key&gt; in apps/api/.env</p>
            </div>
          )}
        </div>
      </div>

      {/* Twenty CRM launch */}
      <div className="bg-white border border-slate-200 rounded-xl p-6">
        <h2 className="text-sm font-semibold text-slate-700 mb-1">Twenty CRM</h2>
        <p className="text-xs text-slate-500 mb-4">Twenty blocks cross-origin framing — open it in a new tab for the full CRM experience.</p>
        {isConnected ? (
          <a
            href="http://localhost:3333"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold rounded-xl transition-colors"
          >
            <ExternalLink size={14} />
            Open Twenty CRM
          </a>
        ) : (
          <div className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg border border-slate-200">
            <AlertCircle size={14} className="text-slate-400 flex-shrink-0" />
            <p className="text-xs text-slate-500">
              {isOffline ? 'Twenty is offline — start it first' :
               isNotConfigured ? 'Configure TWENTY_API_KEY in apps/api/.env first' :
               'Connecting…'}
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

'use client'

import { useState, useEffect, useCallback } from 'react'
import {
  Megaphone, Loader2, RefreshCw, ExternalLink,
  CheckCircle2, XCircle, AlertCircle,
} from 'lucide-react'

const API = 'http://localhost:8000/api/v1/email'

interface Campaign {
  id: number
  name: string
  isPublished: boolean
  publishDate?: string
  emailCount?: number
  description?: string
}

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`${API}/campaigns`)
      const data = await res.json()
      if (data.error) { setError(data.error); return }
      setCampaigns(data.campaigns ?? [])
      setTotal(data.total ?? 0)
    } catch {
      setError('Could not load campaigns — is the backend and Mautic running?')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  return (
    <div className="max-w-4xl mx-auto space-y-6">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-violet-500/10 flex items-center justify-center">
            <Megaphone size={20} className="text-violet-500" />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-slate-900">Campaigns</h1>
            <p className="text-sm text-slate-500">{total > 0 ? `${total} campaigns in Mautic` : 'Manage email campaigns'}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <a
            href="http://localhost:8181/s/campaigns/new"
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold bg-violet-600 hover:bg-violet-700 text-white rounded-lg transition-colors"
          >
            <Megaphone size={12} /> New Campaign in Mautic
          </a>
          <button onClick={load} className="p-2 rounded-lg hover:bg-gray-100 text-gray-400 transition-colors">
            <RefreshCw size={14} />
          </button>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-3 p-4 bg-red-50 border border-red-200 rounded-xl">
          <AlertCircle size={15} className="text-red-500 flex-shrink-0" />
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* Info banner */}
      <div className="p-4 bg-blue-50 border border-blue-200 rounded-xl">
        <p className="text-sm text-blue-800">
          <strong>Campaigns are managed in Mautic.</strong> Use the AI Sequence Generator to create email templates,
          then build campaigns in Mautic to automate delivery with triggers and conditions.
        </p>
        <a href="http://localhost:8181/s/campaigns" target="_blank" rel="noreferrer"
          className="inline-flex items-center gap-1 mt-2 text-xs font-semibold text-blue-700 hover:text-blue-900">
          Open Mautic Campaign Builder <ExternalLink size={11} />
        </a>
      </div>

      {/* Campaign list */}
      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="w-6 h-6 animate-spin text-slate-300" />
        </div>
      ) : campaigns.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded-xl text-center py-16">
          <Megaphone size={28} className="text-slate-200 mx-auto mb-3" />
          <p className="text-sm text-slate-400">No campaigns yet</p>
          <p className="text-xs text-slate-300 mt-1">Create your first campaign in Mautic</p>
          <a href="http://localhost:8181/s/campaigns/new" target="_blank" rel="noreferrer"
            className="inline-flex items-center gap-1.5 mt-4 px-4 py-2 text-xs font-semibold bg-violet-600 hover:bg-violet-700 text-white rounded-lg transition-colors">
            <Megaphone size={12} /> Create Campaign
          </a>
        </div>
      ) : (
        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
          <div className="grid grid-cols-12 gap-3 px-5 py-2.5 bg-slate-50 border-b border-slate-100">
            <div className="col-span-1 text-[10px] font-semibold text-slate-500 uppercase tracking-wide">Status</div>
            <div className="col-span-7 text-[10px] font-semibold text-slate-500 uppercase tracking-wide">Campaign</div>
            <div className="col-span-2 text-[10px] font-semibold text-slate-500 uppercase tracking-wide">Published</div>
            <div className="col-span-2 text-[10px] font-semibold text-slate-500 uppercase tracking-wide">Actions</div>
          </div>
          {campaigns.map(c => (
            <div key={c.id} className="grid grid-cols-12 gap-3 px-5 py-4 border-b border-slate-100 last:border-0 hover:bg-slate-50 transition-colors items-center">
              <div className="col-span-1">
                {c.isPublished
                  ? <CheckCircle2 size={14} className="text-emerald-500" />
                  : <XCircle size={14} className="text-slate-300" />}
              </div>
              <div className="col-span-7 min-w-0">
                <p className="text-sm font-medium text-slate-800 truncate">{c.name}</p>
                {c.description && <p className="text-xs text-slate-400 truncate mt-0.5">{c.description}</p>}
              </div>
              <div className="col-span-2">
                <span className={`text-[11px] px-2 py-0.5 rounded-full font-medium ${
                  c.isPublished ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-500'
                }`}>
                  {c.isPublished ? 'Active' : 'Draft'}
                </span>
              </div>
              <div className="col-span-2 flex gap-2">
                <a href={`http://localhost:8181/s/campaigns/${c.id}/edit`} target="_blank" rel="noreferrer"
                  className="text-xs text-blue-500 hover:text-blue-700 flex items-center gap-0.5">
                  Edit <ExternalLink size={9} />
                </a>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

'use client'

import { useState, useEffect } from 'react'
import { UserCheck, Loader2, AlertCircle, ExternalLink, Plus, CheckCircle2 } from 'lucide-react'
import Link from 'next/link'

const API = '/api/v1/crm'

const SOURCES = ['organic', 'outreach', 'referral', 'paid']

interface Contact {
  id: string
  name: string
  email: string
  company: string
  created: string
}

export default function CRMContactsPage() {
  const [contacts, setContacts] = useState<Contact[]>([])
  const [total, setTotal] = useState(0)
  const [loadingList, setLoadingList] = useState(true)
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [company, setCompany] = useState('')
  const [source, setSource] = useState('organic')
  const [saving, setSaving] = useState(false)
  const [saveResult, setSaveResult] = useState<{ success: boolean; message: string } | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    fetch(`${API}/contacts?limit=50`)
      .then(r => r.json())
      .then(d => { setContacts(d.contacts || []); setTotal(d.total || 0) })
      .catch(() => setError('Could not load contacts'))
      .finally(() => setLoadingList(false))
  }, [])

  async function addContact() {
    if (!name) return
    setSaving(true)
    setSaveResult(null)
    try {
      const res = await fetch(`${API}/contacts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, email, company, source }),
      })
      const data = await res.json()
      if (data.success) {
        setSaveResult({ success: true, message: `${name} added to CRM` })
        setContacts(prev => [{ id: data.id, name, email, company, created: new Date().toISOString() }, ...prev])
        setTotal(t => t + 1)
        setName(''); setEmail(''); setCompany('')
      } else {
        setSaveResult({ success: false, message: data.error?.[0]?.message || 'Failed to add contact' })
      }
    } catch {
      setSaveResult({ success: false, message: 'Network error' })
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-blue-500/10 flex items-center justify-center">
          <UserCheck size={20} className="text-blue-500" />
        </div>
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Contacts</h1>
          <p className="text-sm text-slate-500">{total} contacts in CRM</p>
        </div>
      </div>

      {/* Add Contact Form */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-4">
        <h2 className="text-sm font-semibold text-slate-700">Add Contact</h2>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Name *</label>
            <input className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
              placeholder="John Doe" value={name} onChange={e => setName(e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Email</label>
            <input type="email" className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
              placeholder="john@example.com" value={email} onChange={e => setEmail(e.target.value)} />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Company</label>
            <input className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
              placeholder="Acme Corp" value={company} onChange={e => setCompany(e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Source</label>
            <div className="flex gap-2 flex-wrap">
              {SOURCES.map(s => (
                <button key={s} onClick={() => setSource(s)}
                  className={`px-3 py-1.5 text-xs font-medium rounded-lg border capitalize transition-colors ${
                    source === s ? 'border-blue-500 bg-blue-50 text-blue-700' : 'border-slate-200 text-slate-600 hover:border-slate-300'
                  }`}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        </div>
        <button onClick={addContact} disabled={saving || !name}
          className="flex items-center gap-2 px-4 py-2.5 bg-slate-800 hover:bg-slate-900 text-white text-sm font-bold rounded-xl transition-colors disabled:opacity-50">
          {saving ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
          {saving ? 'Adding…' : 'Add to CRM'}
        </button>
        {saveResult && (
          <div className={`flex items-center gap-2 text-sm ${saveResult.success ? 'text-emerald-600' : 'text-red-600'}`}>
            {saveResult.success ? <CheckCircle2 size={14} /> : <AlertCircle size={14} />}
            {saveResult.message}
            {saveResult.success && (
              <Link href="/dashboard/intelligence/outbound" className="text-xs text-blue-600 hover:underline ml-1">
                → Generate outreach
              </Link>
            )}
          </div>
        )}
      </div>

      {/* Sync hint */}
      <div className="flex items-center gap-3 p-4 bg-blue-50 border border-blue-200 rounded-xl">
        <AlertCircle size={14} className="text-blue-500 flex-shrink-0" />
        <p className="text-xs text-blue-700">
          Contacts auto-sync when you use the <Link href="/dashboard/intelligence/outbound" className="font-semibold underline">Outbound Engine</Link> — click "Add to CRM" after generating outreach.
        </p>
      </div>

      {/* Contacts Table */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
        <div className="px-5 py-3 border-b border-slate-100 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-700">All Contacts ({total})</h2>
        </div>
        {loadingList ? (
          <div className="flex items-center justify-center py-12 text-slate-400">
            <Loader2 size={18} className="animate-spin" />
          </div>
        ) : error ? (
          <div className="flex items-center gap-2 p-4 text-red-600 text-sm">
            <AlertCircle size={14} /> {error}
          </div>
        ) : contacts.length === 0 ? (
          <div className="py-12 text-center text-slate-400 text-sm">No contacts yet — add your first one above</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-slate-50">
              <tr>
                {['Name', 'Email', 'Company', 'Created', ''].map(h => (
                  <th key={h} className="px-4 py-2.5 text-left text-[11px] font-semibold text-slate-500 uppercase tracking-wide">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {contacts.map(c => (
                <tr key={c.id} className="hover:bg-slate-50 transition-colors">
                  <td className="px-4 py-3 font-medium text-slate-800">{c.name || '—'}</td>
                  <td className="px-4 py-3 text-slate-500">{c.email || '—'}</td>
                  <td className="px-4 py-3 text-slate-500">{c.company || '—'}</td>
                  <td className="px-4 py-3 text-slate-400 text-xs">{c.created ? new Date(c.created).toLocaleDateString() : '—'}</td>
                  <td className="px-4 py-3">
                    <a href={`http://localhost:3333/objects/people/${c.id}`} target="_blank" rel="noopener noreferrer"
                      className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-700">
                      View <ExternalLink size={10} />
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

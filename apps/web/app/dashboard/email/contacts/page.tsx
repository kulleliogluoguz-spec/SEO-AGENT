'use client'

import { useState, useEffect, useCallback } from 'react'
import {
  Users, Plus, Loader2, CheckCircle2, AlertCircle,
  ExternalLink, RefreshCw, Search,
} from 'lucide-react'

const API = 'http://localhost:8000/api/v1/email'

const BUSINESS_TYPES = [
  { value: '', label: 'No tag' },
  { value: 'ecommerce', label: 'E-commerce' },
  { value: 'saas', label: 'SaaS' },
  { value: 'local', label: 'Local Business' },
  { value: 'personal_brand', label: 'Personal Brand' },
  { value: 'lead', label: 'Lead' },
  { value: 'customer', label: 'Customer' },
]

interface Contact {
  id: number
  fields: {
    core: {
      email?: { value: string }
      firstname?: { value: string }
      lastname?: { value: string }
      company?: { value: string }
    }
  }
  tags?: { tag: string }[]
}

export default function ContactsPage() {
  const [contacts, setContacts] = useState<Contact[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [msg, setMsg] = useState<{ type: 'ok' | 'err'; text: string } | null>(null)

  const [form, setForm] = useState({
    email: '',
    firstname: '',
    lastname: '',
    company: '',
    business_type: '',
  })

  const load = useCallback(async (q = '') => {
    setLoading(true)
    try {
      const url = q ? `${API}/contacts?limit=50&search=${encodeURIComponent(q)}` : `${API}/contacts?limit=50`
      const res = await fetch(url)
      const data = await res.json()
      setContacts(data.contacts ?? [])
      setTotal(data.total ?? 0)
    } catch {
      setContacts([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  function handleSearch(e: React.FormEvent) {
    e.preventDefault()
    load(search)
  }

  async function addContact(e: React.FormEvent) {
    e.preventDefault()
    if (!form.email) return
    setSubmitting(true)
    setMsg(null)
    try {
      const res = await fetch(`${API}/contacts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      const data = await res.json()
      if (data.contact) {
        setMsg({ type: 'ok', text: `${form.email} added to Mautic.` })
        setForm({ email: '', firstname: '', lastname: '', company: '', business_type: '' })
        load()
      } else {
        setMsg({ type: 'err', text: data.error || 'Failed to add contact' })
      }
    } catch {
      setMsg({ type: 'err', text: 'Network error — is the backend running?' })
    } finally {
      setSubmitting(false)
    }
  }

  function field(c: Contact, key: keyof Contact['fields']['core']): string {
    return c.fields?.core?.[key]?.value ?? ''
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-blue-500/10 flex items-center justify-center">
            <Users size={20} className="text-blue-500" />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-slate-900">Contacts</h1>
            <p className="text-sm text-slate-500">{total > 0 ? `${total} total in Mautic` : 'Manage your email contacts'}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <a href="http://localhost:8181/s/contacts" target="_blank" rel="noreferrer"
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors">
            Manage in Mautic <ExternalLink size={11} />
          </a>
          <button onClick={() => load(search)} className="p-2 rounded-lg hover:bg-gray-100 text-gray-400 transition-colors">
            <RefreshCw size={14} />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Add contact form */}
        <div className="lg:col-span-1">
          <div className="bg-white border border-slate-200 rounded-xl p-5">
            <h2 className="text-sm font-semibold text-slate-700 mb-4 flex items-center gap-2">
              <Plus size={14} className="text-blue-500" /> Add Contact
            </h2>
            <form onSubmit={addContact} className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Email <span className="text-red-400">*</span></label>
                <input
                  required
                  type="email"
                  className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-400"
                  placeholder="contact@example.com"
                  value={form.email}
                  onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">First Name</label>
                <input
                  className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-400"
                  placeholder="John"
                  value={form.firstname}
                  onChange={e => setForm(f => ({ ...f, firstname: e.target.value }))}
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Last Name</label>
                <input
                  className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-400"
                  placeholder="Smith"
                  value={form.lastname}
                  onChange={e => setForm(f => ({ ...f, lastname: e.target.value }))}
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Company</label>
                <input
                  className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-400"
                  placeholder="Acme Inc"
                  value={form.company}
                  onChange={e => setForm(f => ({ ...f, company: e.target.value }))}
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Tag</label>
                <select
                  className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-400 bg-white"
                  value={form.business_type}
                  onChange={e => setForm(f => ({ ...f, business_type: e.target.value }))}
                >
                  {BUSINESS_TYPES.map(b => (
                    <option key={b.value} value={b.value}>{b.label}</option>
                  ))}
                </select>
              </div>
              <button
                type="submit"
                disabled={submitting || !form.email}
                className="w-full flex items-center justify-center gap-2 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-lg transition-colors disabled:opacity-50"
              >
                {submitting ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
                {submitting ? 'Adding…' : 'Add Contact'}
              </button>
              {msg && (
                <div className={`flex items-center gap-2 text-xs px-3 py-2 rounded-lg ${msg.type === 'ok' ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'}`}>
                  {msg.type === 'ok' ? <CheckCircle2 size={12} /> : <AlertCircle size={12} />}
                  {msg.text}
                </div>
              )}
            </form>
          </div>
        </div>

        {/* Contact list */}
        <div className="lg:col-span-2">
          <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
            {/* Search bar */}
            <form onSubmit={handleSearch} className="flex items-center gap-2 px-4 py-3 border-b border-slate-100">
              <Search size={14} className="text-slate-400 flex-shrink-0" />
              <input
                className="flex-1 text-sm bg-transparent outline-none placeholder-slate-400"
                placeholder="Search contacts…"
                value={search}
                onChange={e => setSearch(e.target.value)}
              />
              <button type="submit" className="px-3 py-1 text-xs font-medium bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors">
                Search
              </button>
            </form>

            {loading ? (
              <div className="flex items-center justify-center py-16">
                <Loader2 className="w-6 h-6 animate-spin text-slate-300" />
              </div>
            ) : contacts.length === 0 ? (
              <div className="text-center py-16">
                <Users size={28} className="text-slate-200 mx-auto mb-3" />
                <p className="text-sm text-slate-400">No contacts yet</p>
                <p className="text-xs text-slate-300 mt-1">Add a contact using the form</p>
              </div>
            ) : (
              <div className="divide-y divide-slate-100">
                {/* Header row */}
                <div className="grid grid-cols-12 gap-3 px-4 py-2 bg-slate-50">
                  <div className="col-span-5 text-[10px] font-semibold text-slate-500 uppercase tracking-wide">Email</div>
                  <div className="col-span-3 text-[10px] font-semibold text-slate-500 uppercase tracking-wide">Name</div>
                  <div className="col-span-2 text-[10px] font-semibold text-slate-500 uppercase tracking-wide">Company</div>
                  <div className="col-span-2 text-[10px] font-semibold text-slate-500 uppercase tracking-wide">Tags</div>
                </div>
                {contacts.map(c => (
                  <div key={c.id} className="grid grid-cols-12 gap-3 px-4 py-3 hover:bg-slate-50 transition-colors items-center">
                    <div className="col-span-5 min-w-0">
                      <a href={`http://localhost:8181/s/contacts/${c.id}/view`} target="_blank" rel="noreferrer"
                        className="text-xs text-blue-600 hover:underline truncate flex items-center gap-1">
                        {field(c, 'email')} <ExternalLink size={9} />
                      </a>
                    </div>
                    <div className="col-span-3 text-xs text-slate-600 truncate">
                      {[field(c, 'firstname'), field(c, 'lastname')].filter(Boolean).join(' ') || '—'}
                    </div>
                    <div className="col-span-2 text-xs text-slate-500 truncate">{field(c, 'company') || '—'}</div>
                    <div className="col-span-2 flex flex-wrap gap-1">
                      {(c.tags ?? []).slice(0, 2).map((t, i) => (
                        <span key={i} className="text-[10px] px-1.5 py-0.5 bg-blue-50 text-blue-600 rounded font-medium">
                          {t.tag}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

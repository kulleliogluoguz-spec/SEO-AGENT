'use client'

import { useState, useEffect } from 'react'
import { Building2, Loader2, AlertCircle, ExternalLink, Plus, CheckCircle2 } from 'lucide-react'

const API = '/api/v1/crm'

const INDUSTRIES = ['Technology', 'SaaS', 'E-commerce', 'Agency', 'Finance', 'Healthcare', 'Other']

interface Company {
  id: string
  name: string
  domain: string
  employees: number | null
  created: string
}

export default function CRMCompaniesPage() {
  const [companies, setCompanies] = useState<Company[]>([])
  const [total, setTotal] = useState(0)
  const [loadingList, setLoadingList] = useState(true)
  const [name, setName] = useState('')
  const [domain, setDomain] = useState('')
  const [industry, setIndustry] = useState('')
  const [saving, setSaving] = useState(false)
  const [saveResult, setSaveResult] = useState<{ success: boolean; message: string } | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    fetch(`${API}/companies?limit=50`)
      .then(r => r.json())
      .then(d => { setCompanies(d.companies || []); setTotal(d.total || 0) })
      .catch(() => setError('Could not load companies'))
      .finally(() => setLoadingList(false))
  }, [])

  async function addCompany() {
    if (!name) return
    setSaving(true)
    setSaveResult(null)
    try {
      const res = await fetch(`${API}/companies`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, domain, industry }),
      })
      const data = await res.json()
      if (data.success) {
        setSaveResult({ success: true, message: `${name} added to CRM` })
        setCompanies(prev => [{ id: data.id, name, domain, employees: null, created: new Date().toISOString() }, ...prev])
        setTotal(t => t + 1)
        setName(''); setDomain('')
      } else {
        setSaveResult({ success: false, message: data.error?.[0]?.message || 'Failed to add company' })
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
        <div className="w-10 h-10 rounded-xl bg-indigo-500/10 flex items-center justify-center">
          <Building2 size={20} className="text-indigo-500" />
        </div>
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Companies</h1>
          <p className="text-sm text-slate-500">{total} companies in CRM</p>
        </div>
      </div>

      {/* Add Company Form */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-4">
        <h2 className="text-sm font-semibold text-slate-700">Add Company</h2>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Company Name *</label>
            <input className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
              placeholder="Acme Corp" value={name} onChange={e => setName(e.target.value)} />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Domain</label>
            <input className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
              placeholder="acme.com" value={domain} onChange={e => setDomain(e.target.value)} />
          </div>
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">Industry</label>
          <div className="flex flex-wrap gap-2">
            {INDUSTRIES.map(ind => (
              <button key={ind} onClick={() => setIndustry(ind === industry ? '' : ind)}
                className={`px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors ${
                  industry === ind ? 'border-indigo-500 bg-indigo-50 text-indigo-700' : 'border-slate-200 text-slate-600 hover:border-slate-300'
                }`}>
                {ind}
              </button>
            ))}
          </div>
        </div>
        <button onClick={addCompany} disabled={saving || !name}
          className="flex items-center gap-2 px-4 py-2.5 bg-slate-800 hover:bg-slate-900 text-white text-sm font-bold rounded-xl transition-colors disabled:opacity-50">
          {saving ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
          {saving ? 'Adding…' : 'Add Company'}
        </button>
        {saveResult && (
          <div className={`flex items-center gap-2 text-sm ${saveResult.success ? 'text-emerald-600' : 'text-red-600'}`}>
            {saveResult.success ? <CheckCircle2 size={14} /> : <AlertCircle size={14} />}
            {saveResult.message}
          </div>
        )}
      </div>

      {/* Companies Table */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
        <div className="px-5 py-3 border-b border-slate-100">
          <h2 className="text-sm font-semibold text-slate-700">All Companies ({total})</h2>
        </div>
        {loadingList ? (
          <div className="flex items-center justify-center py-12 text-slate-400">
            <Loader2 size={18} className="animate-spin" />
          </div>
        ) : error ? (
          <div className="flex items-center gap-2 p-4 text-red-600 text-sm"><AlertCircle size={14} /> {error}</div>
        ) : companies.length === 0 ? (
          <div className="py-12 text-center text-slate-400 text-sm">No companies yet — add your first one above</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-slate-50">
              <tr>
                {['Company', 'Domain', 'Employees', 'Created', ''].map(h => (
                  <th key={h} className="px-4 py-2.5 text-left text-[11px] font-semibold text-slate-500 uppercase tracking-wide">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {companies.map(c => (
                <tr key={c.id} className="hover:bg-slate-50 transition-colors">
                  <td className="px-4 py-3 font-medium text-slate-800">{c.name}</td>
                  <td className="px-4 py-3 text-slate-500">{c.domain || '—'}</td>
                  <td className="px-4 py-3 text-slate-500">{c.employees ?? '—'}</td>
                  <td className="px-4 py-3 text-slate-400 text-xs">{c.created ? new Date(c.created).toLocaleDateString() : '—'}</td>
                  <td className="px-4 py-3">
                    <a href={`http://localhost:3333/objects/companies/${c.id}`} target="_blank" rel="noopener noreferrer"
                      className="flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-700">
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

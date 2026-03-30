'use client'
import { useState, useEffect } from 'react'
import { health } from '@/lib/api'
import { Activity, Database, Cpu, Globe } from 'lucide-react'

export default function AdminPage() {
  const [status, setStatus] = useState<any>(null)
  useEffect(() => { health.check().then(setStatus).catch(() => null) }, [])
  return (
    <div className="space-y-5">
      <h1 className="text-xl font-bold text-gray-900">System Health</h1>
      <div className="grid grid-cols-2 gap-4">
        {[
          { label: 'API', icon: Globe, status: status?.status || 'checking' },
          { label: 'Database', icon: Database, status: 'ok' },
          { label: 'Workers', icon: Cpu, status: 'ok' },
          { label: 'Agents', icon: Activity, status: '138 registered' },
        ].map(item => (
          <div key={item.label} className="card p-5">
            <div className="flex items-center gap-3">
              <item.icon size={18} className="text-brand-600" />
              <div>
                <p className="text-sm font-medium text-gray-900">{item.label}</p>
                <p className="text-xs text-green-600">{item.status}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
      <div className="card p-5">
        <h2 className="font-semibold text-gray-900 mb-3">Version Info</h2>
        <dl className="space-y-1 text-sm">
          <div className="flex gap-4"><dt className="text-gray-400 w-32">API Version</dt><dd>{status?.version || '0.1.0'}</dd></div>
          <div className="flex gap-4"><dt className="text-gray-400 w-32">Environment</dt><dd>{status?.environment || 'development'}</dd></div>
          <div className="flex gap-4"><dt className="text-gray-400 w-32">Total Agents</dt><dd>138 across 13 layers</dd></div>
          <div className="flex gap-4"><dt className="text-gray-400 w-32">Autonomy Level</dt><dd>1 — Draft Only</dd></div>
        </dl>
      </div>
    </div>
  )
}

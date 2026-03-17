'use client'
import { Plug, CheckCircle, AlertCircle, Info } from 'lucide-react'

const CONNECTORS = [
  { name: 'Google Analytics 4', key: 'ga4', status: 'mock', description: 'Traffic, conversions, and user behavior data' },
  { name: 'Google Search Console', key: 'gsc', status: 'mock', description: 'Search queries, impressions, and click data' },
  { name: 'Slack', key: 'slack', status: 'mock', description: 'Approval notifications and report delivery' },
  { name: 'CMS Publishing', key: 'cms', status: 'not_configured', description: 'Publish content to WordPress, Webflow, etc.' },
  { name: 'Social Scheduler', key: 'social', status: 'not_configured', description: 'Schedule posts to LinkedIn, X, and more' },
]

export default function ConnectorsPage() {
  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-bold text-gray-900">Connectors</h1>
        <p className="text-sm text-gray-500">Connect data sources and publishing channels</p>
      </div>
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex gap-3">
        <Info size={16} className="text-blue-600 flex-shrink-0 mt-0.5" />
        <p className="text-sm text-blue-800">
          Connectors in <strong>mock mode</strong> return realistic demo data. Configure real credentials in
          <code className="bg-blue-100 px-1 rounded">.env</code> to connect live systems.
        </p>
      </div>
      <div className="grid gap-4">
        {CONNECTORS.map(c => (
          <div key={c.key} className="card p-5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center">
                  <Plug size={18} className="text-gray-400" />
                </div>
                <div>
                  <h3 className="font-medium text-gray-900">{c.name}</h3>
                  <p className="text-xs text-gray-400">{c.description}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span className={`flex items-center gap-1 text-xs ${c.status === 'mock' ? 'text-yellow-600' : 'text-gray-400'}`}>
                  {c.status === 'mock' ? <CheckCircle size={12} /> : <AlertCircle size={12} />}
                  {c.status === 'mock' ? 'Mock mode' : 'Not configured'}
                </span>
                <button className="btn-secondary text-xs py-1">Configure</button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Globe, Plus, ExternalLink, Clock } from 'lucide-react'
import { sites } from '@/lib/api'
import type { Site } from '@/lib/api'

const DEMO_WS = '00000000-0000-0000-0002-000000000001'

export default function SitesPage() {
  const [siteList, setSiteList] = useState<Site[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    sites.list(DEMO_WS).then(r => setSiteList(r.items)).finally(() => setLoading(false))
  }, [])

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Sites</h1>
          <p className="text-sm text-gray-500">Manage your onboarded websites</p>
        </div>
        <Link href="/dashboard/sites/onboard" className="btn-primary flex items-center gap-2">
          <Plus size={14} /> Add Site
        </Link>
      </div>

      {loading ? (
        <div className="grid gap-4">{[1,2].map(i => <div key={i} className="h-24 card animate-pulse" />)}</div>
      ) : siteList.length === 0 ? (
        <div className="card p-12 text-center">
          <Globe size={40} className="mx-auto text-gray-300 mb-3" />
          <h3 className="font-medium text-gray-900 mb-1">No sites yet</h3>
          <p className="text-sm text-gray-400 mb-4">Add your first website to get started</p>
          <Link href="/dashboard/sites/onboard" className="btn-primary inline-flex items-center gap-2">
            <Plus size={14} /> Add Site
          </Link>
        </div>
      ) : (
        <div className="grid gap-4">
          {siteList.map(site => (
            <Link key={site.id} href={`/dashboard/sites/${site.id}`}
              className="card p-5 hover:border-brand-300 transition-colors block">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className={`w-3 h-3 rounded-full mt-0.5 ${site.status === 'active' ? 'bg-green-400' : 'bg-yellow-400'}`} />
                  <div>
                    <h3 className="font-semibold text-gray-900">{site.name || site.domain}</h3>
                    <p className="text-xs text-gray-400 flex items-center gap-1 mt-0.5">
                      <ExternalLink size={10} />{site.url}
                    </p>
                  </div>
                </div>
                <span className={`text-xs px-2 py-1 rounded-full ${site.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'}`}>
                  {site.status}
                </span>
              </div>
              {site.product_summary && (
                <p className="text-sm text-gray-600 mt-3 ml-6 line-clamp-2">{site.product_summary}</p>
              )}
              {site.last_crawled_at && (
                <p className="text-xs text-gray-400 mt-2 ml-6 flex items-center gap-1">
                  <Clock size={10} /> Last crawled {new Date(site.last_crawled_at).toLocaleDateString()}
                </p>
              )}
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}

'use client'

import { useEffect, useState } from 'react'
import {
  TrendingUp, TrendingDown, Globe, FileText,
  CheckSquare, AlertTriangle, ArrowRight, Zap
} from 'lucide-react'
import Link from 'next/link'
import { sites, approvals, recommendations, reports } from '@/lib/api'
import type { Site, Approval, Recommendation, Report } from '@/lib/api'

const DEMO_WS = '00000000-0000-0000-0002-000000000001'
const DEMO_SITE = '00000000-0000-0000-0003-000000000001'

function KPICard({
  label, value, delta, suffix = '', icon: Icon, color = 'blue'
}: {
  label: string; value: string | number; delta?: number
  suffix?: string; icon: React.ElementType; color?: string
}) {
  const colors: Record<string, string> = {
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-green-50 text-green-600',
    yellow: 'bg-yellow-50 text-yellow-600',
    purple: 'bg-purple-50 text-purple-600',
  }

  return (
    <div className="card p-5">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">{label}</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">
            {value}{suffix}
          </p>
          {delta !== undefined && (
            <div className={`flex items-center gap-1 mt-1 text-xs ${delta >= 0 ? 'text-green-600' : 'text-red-500'}`}>
              {delta >= 0 ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
              <span>{delta >= 0 ? '+' : ''}{delta}% vs last week</span>
            </div>
          )}
        </div>
        <div className={`p-2 rounded-lg ${colors[color]}`}>
          <Icon size={18} />
        </div>
      </div>
    </div>
  )
}

function RecommendationRow({ rec }: { rec: Recommendation }) {
  const severityColors: Record<string, string> = {
    technical_seo: 'badge-red',
    on_page_seo: 'badge-yellow',
    content_gap: 'badge-blue',
    geo_aeo: 'badge-purple',
  }

  return (
    <div className="flex items-center gap-3 py-3 border-b border-gray-100 last:border-0">
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-900 truncate">{rec.title}</p>
        <p className="text-xs text-gray-400 mt-0.5">{rec.summary.slice(0, 80)}…</p>
      </div>
      <div className="flex items-center gap-2 flex-shrink-0">
        <span className={`badge-gray text-xs`}>
          {(rec.priority_score * 100).toFixed(0)} pts
        </span>
        <span className={`${severityColors[rec.category] || 'badge-gray'}`}>
          {rec.category.replace('_', ' ')}
        </span>
      </div>
    </div>
  )
}

export default function DashboardPage() {
  const [siteList, setSiteList] = useState<Site[]>([])
  const [pendingApprovals, setPendingApprovals] = useState<Approval[]>([])
  const [topRecs, setTopRecs] = useState<Recommendation[]>([])
  const [reportList, setReportList] = useState<Report[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      try {
        const [s, a, r, rp] = await Promise.allSettled([
          sites.list(DEMO_WS),
          approvals.list(DEMO_WS, 'pending'),
          recommendations.list(DEMO_SITE, { page: 1 }),
          reports.list(DEMO_WS),
        ])
        if (s.status === 'fulfilled') setSiteList(s.value.items)
        if (a.status === 'fulfilled') setPendingApprovals(a.value.items)
        if (r.status === 'fulfilled') setTopRecs(r.value.items.slice(0, 5))
        if (rp.status === 'fulfilled') setReportList(rp.value.items)
      } catch (e) {
        console.error(e)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Growth Overview</h1>
          <p className="text-sm text-gray-500 mt-0.5">Acme Growth · Last 7 days</p>
        </div>
        <Link href="/dashboard/sites/onboard" className="btn-primary flex items-center gap-2">
          <Globe size={14} />
          Add Site
        </Link>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard label="Organic Sessions" value="1,240" delta={8.3} icon={TrendingUp} color="green" />
        <KPICard label="Organic Leads" value="23" delta={-4.2} icon={TrendingDown} color="yellow" />
        <KPICard label="Avg. Position" value="18.4" icon={Globe} color="blue" />
        <KPICard label="Content in Pipeline" value="2" icon={FileText} color="purple" />
      </div>

      {/* Main grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recommendations */}
        <div className="lg:col-span-2 card p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-gray-900">Top Recommendations</h2>
            <Link href="/dashboard/seo" className="text-xs text-brand-600 hover:text-brand-700 flex items-center gap-1">
              View all <ArrowRight size={12} />
            </Link>
          </div>
          {loading ? (
            <div className="space-y-3">
              {[1,2,3].map(i => (
                <div key={i} className="h-12 bg-gray-100 rounded animate-pulse" />
              ))}
            </div>
          ) : topRecs.length > 0 ? (
            <div>
              {topRecs.map(rec => <RecommendationRow key={rec.id} rec={rec} />)}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-400 text-sm">
              <Globe size={32} className="mx-auto mb-2 opacity-30" />
              No recommendations yet — add and crawl a site to get started
            </div>
          )}
        </div>

        {/* Right panel */}
        <div className="space-y-4">
          {/* Pending approvals */}
          <div className="card p-5">
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-semibold text-gray-900 flex items-center gap-2">
                <CheckSquare size={16} className="text-yellow-500" />
                Pending Approvals
              </h2>
              <span className="badge-yellow text-xs">{pendingApprovals.length}</span>
            </div>
            {loading ? (
              <div className="h-16 bg-gray-100 rounded animate-pulse" />
            ) : pendingApprovals.length > 0 ? (
              <div className="space-y-2">
                {pendingApprovals.slice(0, 3).map(a => (
                  <div key={a.id} className="text-sm">
                    <p className="text-gray-700 truncate">{a.title}</p>
                    <p className="text-xs text-gray-400">{a.risk_level} risk</p>
                  </div>
                ))}
                <Link href="/dashboard/approvals" className="text-xs text-brand-600 flex items-center gap-1 mt-2">
                  Review approvals <ArrowRight size={12} />
                </Link>
              </div>
            ) : (
              <p className="text-sm text-gray-400">No pending approvals</p>
            )}
          </div>

          {/* Sites */}
          <div className="card p-5">
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-semibold text-gray-900">Sites</h2>
              <span className="text-xs text-gray-400">{siteList.length} active</span>
            </div>
            {siteList.slice(0, 3).map(site => (
              <Link
                key={site.id}
                href={`/dashboard/sites/${site.id}`}
                className="flex items-center gap-2 py-2 hover:text-brand-600 transition-colors"
              >
                <div className={`w-2 h-2 rounded-full ${site.status === 'active' ? 'bg-green-400' : 'bg-yellow-400'}`} />
                <span className="text-sm font-medium truncate">{site.domain}</span>
                <span className={`ml-auto text-xs ${site.status === 'active' ? 'text-green-600' : 'text-yellow-600'}`}>
                  {site.status}
                </span>
              </Link>
            ))}
          </div>

          {/* AI Visibility teaser */}
          <div className="card p-5 bg-gradient-to-br from-purple-50 to-blue-50 border-purple-200">
            <div className="flex items-center gap-2 mb-2">
              <Zap size={16} className="text-purple-600" />
              <h2 className="font-semibold text-gray-900 text-sm">AI Visibility</h2>
              <span className="badge-blue text-xs">Experimental</span>
            </div>
            <p className="text-xs text-gray-600 mb-3">
              See how discoverable your brand is to AI assistants like ChatGPT and Claude.
            </p>
            <Link href="/dashboard/geo" className="btn-secondary text-xs py-1.5">
              View Analysis
            </Link>
          </div>
        </div>
      </div>

      {/* Recent Reports */}
      {reportList.length > 0 && (
        <div className="card p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-gray-900">Recent Reports</h2>
            <Link href="/dashboard/reports" className="text-xs text-brand-600 flex items-center gap-1">
              All reports <ArrowRight size={12} />
            </Link>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {reportList.slice(0, 3).map(report => (
              <Link
                key={report.id}
                href={`/dashboard/reports/${report.id}`}
                className="p-3 rounded-lg border border-gray-200 hover:border-brand-300 hover:bg-brand-50 transition-colors"
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className="badge-blue">{report.report_type}</span>
                </div>
                <p className="text-sm font-medium text-gray-900 truncate">{report.title}</p>
                {report.summary && (
                  <p className="text-xs text-gray-400 mt-1 line-clamp-2">{report.summary}</p>
                )}
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

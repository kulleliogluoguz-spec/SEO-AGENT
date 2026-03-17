'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Globe, ArrowLeft, Loader2 } from 'lucide-react'
import Link from 'next/link'
import { sites } from '@/lib/api'

const DEMO_WS = '00000000-0000-0000-0002-000000000001'

export default function OnboardPage() {
  const router = useRouter()
  const [url, setUrl] = useState('https://')
  const [name, setName] = useState('')
  const [maxPages, setMaxPages] = useState(100)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const site = await sites.create(DEMO_WS, url, name || undefined, maxPages)
      router.push(`/dashboard/sites/${site.id}`)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to onboard site')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-lg">
      <Link href="/dashboard/sites" className="flex items-center gap-1 text-sm text-gray-400 hover:text-gray-600 mb-5">
        <ArrowLeft size={14} /> Back to Sites
      </Link>
      <h1 className="text-xl font-bold text-gray-900 mb-1">Add a Website</h1>
      <p className="text-sm text-gray-500 mb-6">
        Enter your website URL to begin the onboarding analysis. We will crawl the site, extract product intelligence,
        run SEO audits, and generate prioritized recommendations.
      </p>
      <div className="card p-6">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Website URL *</label>
            <input type="url" value={url} onChange={e => setUrl(e.target.value)} required
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              placeholder="https://yoursite.com" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Site Name (optional)</label>
            <input type="text" value={name} onChange={e => setName(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              placeholder="My Product" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Max pages to crawl</label>
            <select value={maxPages} onChange={e => setMaxPages(Number(e.target.value))}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500">
              <option value={25}>25 pages (quick)</option>
              <option value={100}>100 pages (standard)</option>
              <option value={250}>250 pages (thorough)</option>
              <option value={500}>500 pages (deep)</option>
            </select>
          </div>
          {error && <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-3 text-sm">{error}</div>}
          <button type="submit" disabled={loading} className="btn-primary w-full flex items-center justify-center gap-2">
            {loading ? <><Loader2 size={14} className="animate-spin" /> Onboarding…</> : <><Globe size={14} /> Start Onboarding</>}
          </button>
        </form>
      </div>
      <div className="mt-4 p-4 bg-blue-50 rounded-lg text-xs text-blue-700">
        <strong>What happens next:</strong> We will validate the domain, check robots.txt, crawl up to {maxPages} pages,
        run SEO and AI visibility audits, and generate prioritized recommendations. This may take a few minutes.
      </div>
    </div>
  )
}

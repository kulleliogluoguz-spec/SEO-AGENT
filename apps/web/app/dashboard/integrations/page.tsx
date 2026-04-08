'use client'

import { useEffect, useState, useCallback } from 'react'
import {
  AlertCircle,
  CheckCircle,
  ExternalLink,
  Link2,
  RefreshCw,
  Trash2,
  XCircle,
} from 'lucide-react'
import { apiFetch } from '@/lib/apiFetch'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

type Connection = {
  id: string
  platform: 'meta' | 'google'
  account_id: string
  account_name?: string | null
  currency?: string | null
  is_active: boolean
  last_sync_status?: string | null
  last_sync_error?: string | null
  connected_at?: string | null
  last_synced_at?: string | null
}

type Message = { type: 'success' | 'error' | 'info'; text: string } | null

const PLATFORM_COLORS: Record<string, string> = {
  meta: 'bg-blue-100 text-blue-700 border-blue-300',
  google: 'bg-red-100 text-red-700 border-red-300',
}

export default function IntegrationsPage() {
  const [connections, setConnections] = useState<Connection[]>([])
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState<string | null>(null)
  const [metaToken, setMetaToken] = useState('')
  const [metaAccountId, setMetaAccountId] = useState('')
  const [googleRefreshToken, setGoogleRefreshToken] = useState('')
  const [googleCustomerId, setGoogleCustomerId] = useState('')
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<Message>(null)
  const [activeTab, setActiveTab] = useState<'connected' | 'meta' | 'google'>(
    'connected',
  )

  const loadConnections = useCallback(async () => {
    setLoading(true)
    try {
      const d = await apiFetch<{ connections: Connection[] }>(
        '/api/v1/integrations/connections',
      )
      setConnections(d.connections ?? [])
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadConnections()
    if (typeof window === 'undefined') return
    const params = new URLSearchParams(window.location.search)
    const status = params.get('status')
    const platform = params.get('platform')
    if (status === 'success') {
      setMessage({
        type: 'success',
        text: `${(platform ?? '').toUpperCase()} Ads connected successfully!`,
      })
      window.history.replaceState({}, '', window.location.pathname)
      loadConnections()
    } else if (status === 'error') {
      setMessage({
        type: 'error',
        text: `Connection failed: ${params.get('msg') ?? 'unknown error'}`,
      })
    }
  }, [loadConnections])

  async function connectMetaOAuth() {
    try {
      const d = await apiFetch<{ auth_url: string }>(
        '/api/v1/integrations/meta/authorize',
      )
      window.location.href = d.auth_url
    } catch (e) {
      setMessage({
        type: 'error',
        text: e instanceof Error ? e.message : 'Failed to start Meta OAuth',
      })
    }
  }

  async function connectGoogleOAuth() {
    try {
      const d = await apiFetch<{ auth_url: string }>(
        '/api/v1/integrations/google/authorize',
      )
      window.location.href = d.auth_url
    } catch (e) {
      setMessage({
        type: 'error',
        text: e instanceof Error ? e.message : 'Failed to start Google OAuth',
      })
    }
  }

  async function connectMetaToken() {
    if (!metaToken) return
    setSaving(true)
    setMessage(null)
    try {
      await apiFetch('/api/v1/integrations/meta/connect-token', {
        method: 'POST',
        body: JSON.stringify({
          access_token: metaToken,
          account_id: metaAccountId || undefined,
        }),
      })
      setMessage({
        type: 'success',
        text: 'Meta Ads connected — loading accounts…',
      })
      setMetaToken('')
      setMetaAccountId('')
      loadConnections()
      setActiveTab('connected')
    } catch (e) {
      setMessage({
        type: 'error',
        text: e instanceof Error ? e.message : 'Connection failed',
      })
    } finally {
      setSaving(false)
    }
  }

  async function connectGoogleToken() {
    if (!googleRefreshToken || !googleCustomerId) return
    setSaving(true)
    setMessage(null)
    try {
      await apiFetch('/api/v1/integrations/google/connect-token', {
        method: 'POST',
        body: JSON.stringify({
          refresh_token: googleRefreshToken,
          customer_id: googleCustomerId.replace(/-/g, ''),
        }),
      })
      setMessage({ type: 'success', text: 'Google Ads connected!' })
      setGoogleRefreshToken('')
      setGoogleCustomerId('')
      loadConnections()
      setActiveTab('connected')
    } catch (e) {
      setMessage({
        type: 'error',
        text: e instanceof Error ? e.message : 'Connection failed',
      })
    } finally {
      setSaving(false)
    }
  }

  async function syncAccount(id: string) {
    setSyncing(id)
    try {
      const conn = connections.find((c) => c.id === id)
      if (!conn) return
      const path =
        conn.platform === 'meta'
          ? `/api/v1/integrations/meta/sync/${id}`
          : `/api/v1/integrations/google/sync/${id}`
      const d = await apiFetch<{
        synced_campaigns?: number
        campaigns_synced?: number
      }>(path, { timeoutMs: 120000 })
      setMessage({
        type: 'success',
        text: `Synced ${d.synced_campaigns ?? d.campaigns_synced ?? 0} campaigns`,
      })
      loadConnections()
    } catch (e) {
      setMessage({
        type: 'error',
        text: e instanceof Error ? e.message : 'Sync failed',
      })
    } finally {
      setSyncing(null)
    }
  }

  async function disconnectAccount(id: string) {
    if (!confirm('Disconnect this account? Ad data will remain in the system.')) {
      return
    }
    try {
      await apiFetch(`/api/v1/integrations/connections/${id}`, {
        method: 'DELETE',
      })
      loadConnections()
    } catch (e) {
      setMessage({
        type: 'error',
        text: e instanceof Error ? e.message : 'Disconnect failed',
      })
    }
  }

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">
          Ad Account Integrations
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          Connect your Meta Ads and Google Ads accounts to analyze real campaign data.
        </p>
      </div>

      {message && (
        <div
          className={`flex items-center gap-3 p-4 rounded-xl border ${
            message.type === 'success'
              ? 'bg-emerald-50 border-emerald-200'
              : message.type === 'info'
                ? 'bg-blue-50 border-blue-200'
                : 'bg-red-50 border-red-200'
          }`}
        >
          {message.type === 'success' ? (
            <CheckCircle className="w-5 h-5 text-emerald-600 flex-shrink-0" />
          ) : message.type === 'info' ? (
            <AlertCircle className="w-5 h-5 text-blue-600 flex-shrink-0" />
          ) : (
            <XCircle className="w-5 h-5 text-red-600 flex-shrink-0" />
          )}
          <p
            className={`text-sm flex-1 ${
              message.type === 'success'
                ? 'text-emerald-800'
                : message.type === 'info'
                  ? 'text-blue-800'
                  : 'text-red-800'
            }`}
          >
            {message.text}
          </p>
          <button
            onClick={() => setMessage(null)}
            className="text-slate-400 hover:text-slate-700"
          >
            ×
          </button>
        </div>
      )}

      <div className="flex gap-1 border-b border-slate-200">
        {([
          { key: 'connected', label: `Connected (${connections.length})` },
          { key: 'meta', label: '+ Meta Ads' },
          { key: 'google', label: '+ Google Ads' },
        ] as const).map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
              activeTab === tab.key
                ? 'border-brand-600 text-brand-700'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === 'connected' && (
        <div className="space-y-3">
          {loading ? (
            <div className="text-sm text-slate-500">Loading…</div>
          ) : connections.length === 0 ? (
            <div className="bg-white rounded-xl border border-slate-200 p-8 text-center">
              <Link2 className="w-12 h-12 text-slate-300 mx-auto mb-3" />
              <p className="text-slate-500 font-medium">
                No accounts connected yet
              </p>
              <p className="text-sm text-slate-400 mt-1">
                Connect Meta Ads or Google Ads using the tabs above.
              </p>
            </div>
          ) : (
            connections.map((conn) => (
              <div
                key={conn.id}
                className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span
                      className={`px-2 py-1 rounded text-xs font-bold uppercase border ${
                        PLATFORM_COLORS[conn.platform] ??
                        'bg-slate-100 text-slate-600 border-slate-200'
                      }`}
                    >
                      {conn.platform}
                    </span>
                    <div>
                      <div className="font-medium text-slate-800">
                        {conn.account_name ?? conn.account_id}
                      </div>
                      <div className="text-xs text-slate-400">
                        {conn.account_id}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span
                      className={`text-xs px-2 py-1 rounded-full ${
                        conn.last_sync_status === 'success'
                          ? 'bg-emerald-100 text-emerald-700'
                          : conn.last_sync_status === 'error'
                            ? 'bg-red-100 text-red-600'
                            : 'bg-slate-100 text-slate-500'
                      }`}
                    >
                      {conn.last_sync_status === 'success'
                        ? '✓ Synced'
                        : conn.last_sync_status === 'error'
                          ? '✗ Error'
                          : '○ Pending'}
                    </span>
                    <button
                      onClick={() => syncAccount(conn.id)}
                      disabled={syncing === conn.id}
                      className="p-2 hover:bg-slate-100 rounded-lg"
                      title="Sync now"
                    >
                      <RefreshCw
                        className={`w-4 h-4 text-slate-500 ${
                          syncing === conn.id ? 'animate-spin' : ''
                        }`}
                      />
                    </button>
                    <button
                      onClick={() => disconnectAccount(conn.id)}
                      className="p-2 hover:bg-red-50 rounded-lg"
                      title="Disconnect"
                    >
                      <Trash2 className="w-4 h-4 text-red-400" />
                    </button>
                  </div>
                </div>
                {conn.last_synced_at && (
                  <div className="text-xs text-slate-400 mt-2">
                    Last synced: {new Date(conn.last_synced_at).toLocaleString()}
                  </div>
                )}
                {conn.last_sync_error && (
                  <div className="text-xs text-red-500 mt-1 flex items-center gap-1">
                    <AlertCircle className="w-3 h-3" />
                    {conn.last_sync_error}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      )}

      {activeTab === 'meta' && (
        <div className="space-y-4">
          <div className="bg-blue-50 border border-blue-200 rounded-xl p-5">
            <h3 className="font-semibold text-blue-900 mb-2">
              Option A — OAuth (Recommended)
            </h3>
            <p className="text-sm text-blue-800 mb-4">
              Click below to authorize via Facebook. You&rsquo;ll be redirected
              to Meta and back automatically. Requires a Meta App with
              Marketing API access.
            </p>
            <button
              onClick={connectMetaOAuth}
              className="bg-blue-600 text-white px-5 py-2.5 rounded-lg text-sm font-medium hover:bg-blue-700 inline-flex items-center gap-2"
            >
              <ExternalLink className="w-4 h-4" /> Connect with Meta OAuth
            </button>
          </div>

          <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-4">
            <h3 className="font-semibold text-slate-800">
              Option B — System User Token (Quick Setup)
            </h3>
            <p className="text-sm text-slate-500">
              Get a token from Meta Business Manager → Settings → Users → System
              Users → Generate Token. Grant{' '}
              <code className="bg-slate-100 px-1 rounded text-xs">
                ads_management, ads_read
              </code>
              .
            </p>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Access Token *
              </label>
              <textarea
                value={metaToken}
                onChange={(e) => setMetaToken(e.target.value)}
                rows={3}
                placeholder="EAAxxxxxxx..."
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm font-mono resize-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Ad Account ID (optional — auto-discovered if blank)
              </label>
              <input
                value={metaAccountId}
                onChange={(e) => setMetaAccountId(e.target.value)}
                placeholder="act_1234567890"
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
              />
            </div>
            <button
              onClick={connectMetaToken}
              disabled={saving || !metaToken}
              className="bg-blue-600 text-white px-5 py-2.5 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              {saving ? 'Connecting…' : 'Connect Meta Ads'}
            </button>
          </div>
        </div>
      )}

      {activeTab === 'google' && (
        <div className="space-y-4">
          <div className="bg-red-50 border border-red-200 rounded-xl p-5">
            <h3 className="font-semibold text-red-900 mb-2">
              Option A — OAuth (Recommended)
            </h3>
            <p className="text-sm text-red-800 mb-4">
              Requires a Google Cloud project with Google Ads API enabled +
              Developer Token.
            </p>
            <button
              onClick={connectGoogleOAuth}
              className="bg-red-600 text-white px-5 py-2.5 rounded-lg text-sm font-medium hover:bg-red-700 inline-flex items-center gap-2"
            >
              <ExternalLink className="w-4 h-4" /> Connect with Google OAuth
            </button>
          </div>

          <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-4">
            <h3 className="font-semibold text-slate-800">
              Option B — Refresh Token (Quick Setup)
            </h3>
            <p className="text-sm text-slate-500">
              Generate a refresh token using the Google Ads Python helper:{' '}
              <code className="bg-slate-100 px-1 rounded text-xs">
                python3 -m google.ads.googleads.examples.authentication.generate_user_credentials
              </code>
            </p>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Google Customer ID *
              </label>
              <input
                value={googleCustomerId}
                onChange={(e) => setGoogleCustomerId(e.target.value)}
                placeholder="123-456-7890"
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
              />
              <p className="text-xs text-slate-400 mt-1">
                Found in the top-right corner of the Google Ads UI.
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Refresh Token *
              </label>
              <textarea
                value={googleRefreshToken}
                onChange={(e) => setGoogleRefreshToken(e.target.value)}
                rows={3}
                placeholder="1//0gxxxxxx..."
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm font-mono resize-none"
              />
            </div>
            <button
              onClick={connectGoogleToken}
              disabled={saving || !googleRefreshToken || !googleCustomerId}
              className="bg-red-600 text-white px-5 py-2.5 rounded-lg text-sm font-medium hover:bg-red-700 disabled:opacity-50"
            >
              {saving ? 'Connecting…' : 'Connect Google Ads'}
            </button>
          </div>
        </div>
      )}

      <div className="text-xs text-slate-400 pt-4 border-t border-slate-100">
        API base: {API}
      </div>
    </div>
  )
}

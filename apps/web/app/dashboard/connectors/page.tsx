'use client'

import { useState, useEffect, useCallback } from 'react'
import {
  Twitter, Instagram, Megaphone, BarChart2, Search,
  CheckCircle2, AlertCircle, XCircle, Loader2,
  RefreshCw, Zap, ChevronDown, ChevronUp,
  Key, Globe, Shield
} from 'lucide-react'
import Link from 'next/link'
import { apiFetch, ApiError } from '@/lib/apiFetch'

// ── Types ─────────────────────────────────────────────────────────────────────

interface SocialHealth {
  channel: string
  label: string
  status: string
  ready: boolean
  message: string
  publish_enabled: boolean
  capabilities: { text_posts: boolean; media_posts: boolean; threads: boolean }
  post_limit_note?: string
  note?: string
}

// ── Status helpers ─────────────────────────────────────────────────────────────

function StatusBadge({ ready, status }: { ready: boolean; status: string }) {
  if (ready) return (
    <span className="flex items-center gap-1.5 text-xs font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2.5 py-1 rounded-full">
      <CheckCircle2 size={11} /> Connected
    </span>
  )
  if (status === 'invalid_credentials') return (
    <span className="flex items-center gap-1.5 text-xs font-semibold text-red-600 bg-red-50 border border-red-200 px-2.5 py-1 rounded-full">
      <XCircle size={11} /> Token expired
    </span>
  )
  if (status === 'missing_scopes') return (
    <span className="flex items-center gap-1.5 text-xs font-semibold text-amber-600 bg-amber-50 border border-amber-200 px-2.5 py-1 rounded-full">
      <Shield size={11} /> Missing permissions
    </span>
  )
  return (
    <span className="flex items-center gap-1.5 text-xs font-semibold text-gray-500 bg-gray-50 border border-gray-200 px-2.5 py-1 rounded-full">
      <AlertCircle size={11} /> Not connected
    </span>
  )
}

// ── What this unlocks ─────────────────────────────────────────────────────────

const UNLOCKS: Record<string, string[]> = {
  x:         ['Generate trend-aware posts', 'Auto-publish to X', 'Track follower growth', 'Measure post engagement'],
  instagram: ['Generate carousels and captions', 'Schedule Instagram posts', 'Track follower and reach metrics', 'Measure saves and engagement'],
  meta_ads:  ['Launch Meta/Facebook ad campaigns', 'Target by interest and demographics', 'Track conversions and ROAS', 'AI-optimized ad copy generation'],
  google_ads:['Launch Google Search campaigns', 'Capture high-intent traffic', 'Track clicks, CPC, and conversions', 'AI keyword and copy generation'],
  ga4:       ['Import site traffic data', 'Connect ad spend to conversions', 'Track goal completions'],
  gsc:       ['Import search query data', 'See keywords driving traffic', 'Track ranking trends'],
}

// ── Social card ───────────────────────────────────────────────────────────────

function SocialCard({
  channel,
  onRefresh,
}: {
  channel: SocialHealth
  onRefresh: () => void
}) {
  const [showSetup, setShowSetup] = useState(false)
  const [token, setToken] = useState('')
  const [saving, setSaving] = useState(false)
  const [saveMsg, setSaveMsg] = useState<{ type: 'ok' | 'err'; text: string } | null>(null)
  const [validating, setValidating] = useState(false)
  const [validateMsg, setValidateMsg] = useState('')
  const [oauthLoading, setOauthLoading] = useState(false)
  const [oauthError, setOauthError] = useState<string | null>(null)

  const isX = channel.channel === 'x'
  const isIG = channel.channel === 'instagram'

  const Icon = isX ? Twitter : Instagram
  const iconStyle = isX
    ? 'bg-black'
    : 'bg-gradient-to-br from-pink-500 to-purple-600'

  async function handleOAuth() {
    setOauthLoading(true)
    setOauthError(null)
    try {
      const endpoint = isIG ? '/api/v1/auth/meta/authorize?scope=all' : '/api/v1/auth/x/authorize'
      const data = await apiFetch<{ authorization_url: string }>(endpoint)
      if (data.authorization_url) window.location.href = data.authorization_url
    } catch (e) {
      setOauthError(e instanceof Error ? e.message : 'OAuth not configured — check server .env')
      setOauthLoading(false)
    }
  }

  async function handleSave() {
    if (!token.trim()) return
    setSaving(true); setSaveMsg(null)
    try {
      await apiFetch('/api/v1/connectors/credentials', {
        method: 'POST',
        body: JSON.stringify({
          connector_key: channel.channel,
          fields: { [isIG ? 'access_token' : 'bearer_token']: token.trim() },
        }),
      })
      setSaveMsg({ type: 'ok', text: 'Token saved!' })
      setToken('')
    } catch (e) {
      setSaveMsg({ type: 'err', text: e instanceof ApiError ? e.message : 'Save failed' })
    } finally { setSaving(false) }
  }

  async function handleValidate() {
    setValidating(true); setValidateMsg('')
    try {
      const data = await apiFetch<{ ready: boolean; message: string }>(
        `/api/v1/publishing/validate-connection/${channel.channel}`,
        { method: 'POST' }
      )
      setValidateMsg(data.ready ? '✓ Connection validated!' : `⚠ ${data.message}`)
      if (data.ready) onRefresh()
    } catch { setValidateMsg('Validation failed — check credentials') }
    finally { setValidating(false) }
  }

  const unlocks = UNLOCKS[channel.channel] ?? []

  return (
    <div className={`card overflow-hidden ${channel.ready ? 'border-emerald-200' : 'border-gray-200'}`}>
      <div className="p-5">
        {/* Header */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${iconStyle}`}>
              <Icon size={18} className="text-white" />
            </div>
            <div>
              <div className="text-sm font-bold text-gray-900">{channel.label}</div>
              {channel.post_limit_note && (
                <div className="text-xs text-gray-400 mt-0.5">{channel.post_limit_note}</div>
              )}
            </div>
          </div>
          <StatusBadge ready={channel.ready} status={channel.status} />
        </div>

        {/* Status message */}
        <p className="text-xs text-gray-500 mb-3 leading-relaxed">{channel.message}</p>

        {/* Note (if any) */}
        {channel.note && (
          <div className="flex items-start gap-2 p-2.5 bg-blue-50 border border-blue-100 rounded-lg mb-3">
            <AlertCircle size={11} className="text-blue-400 flex-shrink-0 mt-0.5" />
            <p className="text-xs text-blue-700">{channel.note}</p>
          </div>
        )}

        {/* What this unlocks */}
        <div className="mb-4">
          <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-widest mb-2">What this unlocks</p>
          <ul className="space-y-1">
            {unlocks.map((u, i) => (
              <li key={i} className="flex items-center gap-2 text-xs text-gray-600">
                <CheckCircle2 size={10} className={channel.ready ? 'text-emerald-500' : 'text-gray-200'} />
                {u}
              </li>
            ))}
          </ul>
        </div>

        {/* OAuth error */}
        {oauthError && (
          <div className="flex items-start gap-2 p-2.5 bg-red-50 border border-red-100 rounded-lg mb-3">
            <XCircle size={11} className="text-red-500 flex-shrink-0 mt-0.5" />
            <p className="text-xs text-red-700">{oauthError}</p>
          </div>
        )}

        {/* Connect CTA */}
        {!channel.ready && (isX || isIG) && (
          <button
            onClick={handleOAuth}
            disabled={oauthLoading}
            className={`w-full flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-bold text-white transition-all mb-3 disabled:opacity-50 ${
              isX ? 'bg-black hover:bg-gray-800' : ''
            }`}
            style={isIG && !oauthLoading ? { background: 'linear-gradient(135deg, #ec4899, #a855f7)' } : undefined}
          >
            {oauthLoading ? <Loader2 size={14} className="animate-spin" /> : <Zap size={14} />}
            {oauthLoading ? 'Redirecting…' : isX ? 'Connect X Account' : 'Connect Instagram'}
          </button>
        )}

        {/* Re-connect if expired */}
        {channel.ready && channel.status !== 'ready' && (isX || isIG) && (
          <button
            onClick={handleOAuth}
            disabled={oauthLoading}
            className="w-full flex items-center justify-center gap-2 py-2 rounded-xl text-xs font-semibold text-amber-700 bg-amber-50 border border-amber-200 hover:bg-amber-100 transition-colors mb-3"
          >
            <RefreshCw size={12} /> Reconnect to refresh token
          </button>
        )}

        {/* Manual token toggle */}
        <button
          onClick={() => setShowSetup(s => !s)}
          className="w-full flex items-center justify-between px-3 py-2 bg-gray-50 rounded-lg text-xs font-medium text-gray-600 hover:bg-gray-100 transition-colors"
        >
          <span className="flex items-center gap-1.5">
            <Key size={11} />
            {channel.ready ? 'View / update token' : 'Manual token setup (advanced)'}
          </span>
          {showSetup ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
        </button>
      </div>

      {/* Manual setup panel */}
      {showSetup && (
        <div className="border-t border-gray-100 p-5 bg-gray-50 space-y-3">
          {isX && (
            <div className="p-2.5 bg-blue-50 border border-blue-100 rounded-lg">
              <p className="text-xs text-blue-700">
                <strong>Requires X Basic plan ($100/mo)</strong> for posting. Free tier is read-only.
                <a href="https://developer.twitter.com/en/portal/dashboard" target="_blank" rel="noopener noreferrer" className="underline ml-1">Get tokens →</a>
              </p>
            </div>
          )}
          {isIG && (
            <div className="p-2.5 bg-blue-50 border border-blue-100 rounded-lg">
              <p className="text-xs text-blue-700">
                <strong>Requires a Business or Creator account.</strong> Personal accounts cannot publish via API.
                <a href="https://developers.facebook.com/apps" target="_blank" rel="noopener noreferrer" className="underline ml-1">Get token →</a>
              </p>
            </div>
          )}
          <div>
            <label className="input-label text-xs">{isIG ? 'Instagram Graph API Token' : 'Bearer Token'}</label>
            <div className="flex gap-2">
              <input
                type="password"
                value={token}
                onChange={e => setToken(e.target.value)}
                placeholder={isIG ? 'EAAxxxxxxx…' : 'AAAAAAAAAAAAAxx…'}
                className="flex-1 px-3 py-2 border border-gray-200 rounded-lg text-xs font-mono focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-500 bg-white"
              />
              <button
                onClick={handleSave}
                disabled={saving || !token.trim()}
                className="px-3 py-2 bg-gray-900 text-white rounded-lg text-xs font-semibold disabled:opacity-40 hover:bg-gray-700 transition-colors"
              >
                {saving ? '…' : 'Save'}
              </button>
            </div>
            {saveMsg && (
              <p className={`text-xs mt-1 ${saveMsg.type === 'ok' ? 'text-emerald-600' : 'text-red-500'}`}>{saveMsg.text}</p>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleValidate}
              disabled={validating}
              className="flex items-center gap-1.5 px-3 py-1.5 border border-gray-200 bg-white rounded-lg text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 transition-colors"
            >
              {validating ? <Loader2 size={11} className="animate-spin" /> : <Zap size={11} />}
              {validating ? 'Validating…' : 'Test connection'}
            </button>
            {validateMsg && (
              <span className={`text-xs font-medium ${validateMsg.startsWith('✓') ? 'text-emerald-600' : 'text-amber-600'}`}>
                {validateMsg}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Ad account card ────────────────────────────────────────────────────────────

function AdAccountCard({
  platform,
  label,
  description,
  icon,
  iconBg,
  connected,
}: {
  platform: string
  label: string
  description: string
  icon: string
  iconBg: string
  connected: boolean
}) {
  const [loading, setLoading] = useState(false)
  const [connectError, setConnectError] = useState<string | null>(null)
  const unlocks = UNLOCKS[platform] ?? []

  async function handleConnect() {
    setLoading(true)
    setConnectError(null)
    try {
      const endpoint = platform === 'google_ads' ? '/api/v1/auth/google/authorize' : '/api/v1/auth/meta/authorize?scope=ads'
      const data = await apiFetch<{ authorization_url: string }>(endpoint)
      if (data.authorization_url) window.location.href = data.authorization_url
    } catch (e) {
      setConnectError(e instanceof Error ? e.message : 'Connection failed — check server .env credentials')
      setLoading(false)
    }
  }

  return (
    <div className={`card overflow-hidden ${connected ? 'border-emerald-200' : 'border-gray-200'}`}>
      <div className="p-5">
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 text-white font-bold text-sm ${iconBg}`}>
              {icon}
            </div>
            <div>
              <div className="text-sm font-bold text-gray-900">{label}</div>
              <div className="text-xs text-gray-400 mt-0.5">{description}</div>
            </div>
          </div>
          <StatusBadge ready={connected} status={connected ? 'ready' : 'no_credentials'} />
        </div>

        <div className="mb-4">
          <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-widest mb-2">What this unlocks</p>
          <ul className="space-y-1">
            {unlocks.map((u, i) => (
              <li key={i} className="flex items-center gap-2 text-xs text-gray-600">
                <CheckCircle2 size={10} className={connected ? 'text-emerald-500' : 'text-gray-200'} />
                {u}
              </li>
            ))}
          </ul>
        </div>

        {connectError && (
          <div className="flex items-start gap-2 p-2.5 bg-red-50 border border-red-100 rounded-lg mb-3">
            <XCircle size={11} className="text-red-500 flex-shrink-0 mt-0.5" />
            <p className="text-xs text-red-700">{connectError}</p>
          </div>
        )}

        {!connected ? (
          <button
            onClick={handleConnect}
            disabled={loading}
            className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-bold text-white bg-gray-900 hover:bg-gray-700 transition-colors disabled:opacity-50"
          >
            {loading ? <Loader2 size={14} className="animate-spin" /> : <Zap size={14} />}
            {loading ? 'Redirecting…' : `Connect ${label}`}
          </button>
        ) : (
          <div className="flex items-center gap-2">
            <Link href="/dashboard/promote" className="flex-1 flex items-center justify-center gap-2 py-2 rounded-xl text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 hover:bg-emerald-100 transition-colors">
              <Megaphone size={11} /> Launch Ads
            </Link>
            <button
              onClick={handleConnect}
              disabled={loading}
              className="flex items-center gap-1.5 px-3 py-2 border border-gray-200 rounded-xl text-xs font-medium text-gray-600 hover:bg-gray-50 transition-colors"
            >
              <RefreshCw size={11} /> Reconnect
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

// ── Analytics card ─────────────────────────────────────────────────────────────

function AnalyticsCard({
  name,
  description,
  icon: Icon,
  iconBg,
  configured,
  fields,
  onSave,
}: {
  name: string
  description: string
  icon: React.ElementType
  iconBg: string
  configured: boolean
  fields: { id: string; label: string; placeholder: string; type?: string }[]
  onSave: (values: Record<string, string>) => Promise<void>
}) {
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState<Record<string, string>>({})
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState('')

  async function handleSave() {
    setSaving(true)
    try {
      await onSave(form)
      setMsg('Saved!')
      setOpen(false)
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : 'Save failed')
    } finally { setSaving(false) }
  }

  return (
    <div className="card overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center gap-4 p-4 hover:bg-gray-50/50 transition-colors text-left"
      >
        <div className={`w-9 h-9 ${iconBg} rounded-xl flex items-center justify-center flex-shrink-0`}>
          <Icon size={16} className="text-white" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-gray-800">{name}</span>
            {configured
              ? <span className="flex items-center gap-1 text-[10px] font-semibold text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded-full"><CheckCircle2 size={9} /> Configured</span>
              : <span className="text-[10px] font-medium text-gray-400 bg-gray-50 px-1.5 py-0.5 rounded-full">Not configured</span>
            }
          </div>
          <p className="text-xs text-gray-400 truncate mt-0.5">{description}</p>
        </div>
        {open ? <ChevronUp size={13} className="text-gray-300 flex-shrink-0" /> : <ChevronDown size={13} className="text-gray-300 flex-shrink-0" />}
      </button>

      {open && (
        <div className="border-t border-gray-100 p-4 bg-gray-50 space-y-3">
          {fields.map(f => (
            <div key={f.id}>
              <label className="input-label text-xs">{f.label}</label>
              {f.type === 'textarea' ? (
                <textarea
                  className="input text-xs font-mono resize-none"
                  rows={3}
                  placeholder={f.placeholder}
                  value={form[f.id] ?? ''}
                  onChange={e => setForm(v => ({ ...v, [f.id]: e.target.value }))}
                />
              ) : (
                <input
                  className="input text-sm"
                  type={f.type === 'password' ? 'password' : 'text'}
                  placeholder={f.placeholder}
                  value={form[f.id] ?? ''}
                  onChange={e => setForm(v => ({ ...v, [f.id]: e.target.value }))}
                />
              )}
            </div>
          ))}
          <div className="flex items-center gap-2">
            <button onClick={handleSave} disabled={saving} className="btn-primary text-xs py-1.5">
              {saving ? <Loader2 size={11} className="animate-spin" /> : null}
              {saving ? 'Saving…' : 'Save & Connect'}
            </button>
            <button onClick={() => setOpen(false)} className="btn-ghost text-xs">Cancel</button>
            {msg && <span className={`text-xs ${msg === 'Saved!' ? 'text-emerald-600' : 'text-red-500'}`}>{msg}</span>}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function ConnectionsPage() {
  const [socialChannels, setSocialChannels] = useState<SocialHealth[]>([])
  const [socialLoading, setSocialLoading] = useState(true)
  const [socialError, setSocialError] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)
  const [connectedPlatforms, setConnectedPlatforms] = useState<Set<string>>(new Set())

  const loadSocial = useCallback(async (showRefresh = false) => {
    if (showRefresh) setRefreshing(true)
    setSocialError(null)
    try {
      const [healthData, connectionsData] = await Promise.all([
        apiFetch<{ channels: SocialHealth[] }>('/api/v1/connectors/social/health', { timeoutMs: 8000 }),
        apiFetch<{ connections: { platform: string }[] }>('/api/v1/auth/connections').catch(() => ({ connections: [] })),
      ])
      setSocialChannels(healthData.channels ?? [])
      setConnectedPlatforms(new Set(connectionsData.connections.map(c => c.platform)))
    } catch (e) {
      setSocialError(e instanceof Error ? e.message : 'Could not reach service')
    } finally {
      setSocialLoading(false)
      setRefreshing(false)
    }
  }, [])

  useEffect(() => { loadSocial() }, [loadSocial])

  const xChannel = socialChannels.find(c => c.channel === 'x')
  const igChannel = socialChannels.find(c => c.channel === 'instagram')

  async function saveAnalytics(key: string, values: Record<string, string>) {
    await apiFetch('/api/v1/connectors/credentials', {
      method: 'POST',
      body: JSON.stringify({ connector_key: key, fields: values }),
    })
  }

  return (
    <div className="space-y-8">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">Connections</h1>
          <p className="page-subtitle">Connect the accounts that power your growth</p>
        </div>
        <button
          onClick={() => loadSocial(true)}
          disabled={refreshing}
          className="btn-secondary text-xs"
        >
          <RefreshCw size={12} className={refreshing ? 'animate-spin' : ''} />
          {refreshing ? 'Checking…' : 'Check health'}
        </button>
      </div>

      {/* ── Social Accounts ── */}
      <div>
        <div className="flex items-center gap-3 mb-4">
          <h2 className="text-sm font-bold text-gray-900">Social Accounts</h2>
          <div className="flex-1 h-px bg-gray-100" />
          {!socialLoading && (
            <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
              socialChannels.filter(c => c.ready).length > 0
                ? 'bg-emerald-50 text-emerald-700'
                : 'bg-gray-100 text-gray-500'
            }`}>
              {socialChannels.filter(c => c.ready).length}/{socialChannels.length} connected
            </span>
          )}
        </div>

        {socialLoading ? (
          <div className="flex items-center gap-2 text-sm text-gray-400 py-8">
            <Loader2 size={14} className="animate-spin" /> Checking connection health…
          </div>
        ) : socialError ? (
          <div className="flex items-center gap-3 p-4 bg-amber-50 border border-amber-200 rounded-xl">
            <AlertCircle size={15} className="text-amber-500 flex-shrink-0" />
            <div>
              <p className="text-sm font-medium text-amber-800">Could not reach service</p>
              <p className="text-xs text-amber-600 mt-0.5">{socialError}</p>
            </div>
            <button onClick={() => loadSocial(true)} className="ml-auto text-xs font-medium text-amber-700 hover:text-amber-900 underline">Retry</button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {xChannel
              ? <SocialCard channel={xChannel} onRefresh={() => loadSocial(true)} />
              : <SocialCard
                  channel={{ channel: 'x', label: 'X / Twitter', status: 'no_credentials', ready: false, message: 'Connect your X account to start publishing and tracking growth.', publish_enabled: false, capabilities: { text_posts: false, media_posts: false, threads: false } }}
                  onRefresh={() => loadSocial(true)}
                />
            }
            {igChannel
              ? <SocialCard channel={igChannel} onRefresh={() => loadSocial(true)} />
              : <SocialCard
                  channel={{ channel: 'instagram', label: 'Instagram', status: 'no_credentials', ready: false, message: 'Connect your Instagram Business or Creator account to start publishing.', publish_enabled: false, capabilities: { text_posts: false, media_posts: false, threads: false } }}
                  onRefresh={() => loadSocial(true)}
                />
            }
          </div>
        )}
      </div>

      {/* ── Ad Accounts ── */}
      <div>
        <div className="flex items-center gap-3 mb-4">
          <h2 className="text-sm font-bold text-gray-900">Ad Accounts</h2>
          <div className="flex-1 h-px bg-gray-100" />
          <Link href="/dashboard/promote" className="text-xs text-brand-600 font-medium hover:text-brand-700">
            Launch ads →
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <AdAccountCard
            platform="meta_ads"
            label="Meta Ads"
            description="Facebook & Instagram advertising"
            icon="M"
            iconBg="bg-blue-600"
            connected={connectedPlatforms.has('meta') || connectedPlatforms.has('meta_ads')}
          />
          <AdAccountCard
            platform="google_ads"
            label="Google Ads"
            description="Search & Display advertising"
            icon="G"
            iconBg="bg-red-500"
            connected={connectedPlatforms.has('google_ads')}
          />
        </div>
      </div>

      {/* ── Website & Analytics ── */}
      <div>
        <div className="flex items-center gap-3 mb-4">
          <h2 className="text-sm font-bold text-gray-900">Website & Analytics</h2>
          <div className="flex-1 h-px bg-gray-100" />
          <span className="text-xs text-gray-400">Optional — enhances recommendations</span>
        </div>

        <div className="space-y-3">
          <AnalyticsCard
            name="Google Analytics 4"
            description="Import traffic, conversions, and user behavior data"
            icon={BarChart2}
            iconBg="bg-yellow-500"
            configured={false}
            fields={[
              { id: 'property_id', label: 'GA4 Property ID', placeholder: '123456789' },
              { id: 'credentials', label: 'Service Account JSON', placeholder: 'Paste JSON content', type: 'textarea' },
            ]}
            onSave={v => saveAnalytics('ga4', v)}
          />
          <AnalyticsCard
            name="Google Search Console"
            description="Import search queries, impressions, and ranking data"
            icon={Search}
            iconBg="bg-blue-500"
            configured={false}
            fields={[
              { id: 'site_url', label: 'Site URL', placeholder: 'https://yourdomain.com' },
              { id: 'credentials', label: 'Service Account JSON', placeholder: 'Paste JSON content', type: 'textarea' },
            ]}
            onSave={v => saveAnalytics('gsc', v)}
          />
          <AnalyticsCard
            name="RSS / Blog Feed"
            description="Ingest industry news to inform content generation"
            icon={Globe}
            iconBg="bg-orange-500"
            configured={false}
            fields={[
              { id: 'feed_urls', label: 'Feed URLs (one per line)', placeholder: 'https://techcrunch.com/feed/', type: 'textarea' },
              { id: 'keywords', label: 'Filter keywords (optional)', placeholder: 'ai, saas, growth' },
            ]}
            onSave={v => saveAnalytics('rss', v)}
          />
        </div>
      </div>

    </div>
  )
}

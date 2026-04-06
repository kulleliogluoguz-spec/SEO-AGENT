'use client'

import { useEffect, useState, useCallback } from 'react'
import {
  Twitter, Loader2, AlertCircle, CheckCircle2,
  RefreshCw, Zap, Send, ListOrdered,
  Map, TrendingUp, XCircle, Plus, Trash2,
  Users, Key, ShieldCheck,
} from 'lucide-react'
import Link from 'next/link'
import { apiFetch } from '@/lib/apiFetch'

// ── Types ────────────────────────────────────────────────────────────────────

interface AccountInfo {
  id: number | null
  username: string
  display_name?: string
  followers: number
  valid: boolean
  source?: string
  connected_at?: string
}

interface HealthData {
  status: string
  message?: string
  instructions?: string[]
  accounts?: AccountInfo[]
}

interface AccountsResponse {
  accounts: Array<{
    id: number
    username: string
    display_name: string
    followers: number
    connected_at: string
    is_active: number
    niche?: string
    target_audience?: string
    auto_generate?: number
  }>
  count: number
}

interface StatsData {
  queue: {
    pending: number
    approved: number
    posted: number
    rejected: number
    errored: number
  }
  this_month_posts: number
  monthly_limit: number
  remaining_this_month: number
  daily_safe_limit: number
  totals: { likes: number; retweets: number; impressions: number }
}

interface GenerateResult {
  generated: number
  items: Array<{ id: number; type: string; content: string; ai_score: number }>
  message?: string
  error?: string
  hint?: string
}

// ── Main Page ────────────────────────────────────────────────────────────────

export default function TwitterHubPage() {
  const [health, setHealth] = useState<HealthData | null>(null)
  const [accounts, setAccounts] = useState<AccountsResponse | null>(null)
  const [stats, setStats] = useState<StatsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Generate form state
  const [niche, setNiche] = useState('')
  const [audience, setAudience] = useState('')
  const [count, setCount] = useState(5)
  const [includeThreads, setIncludeThreads] = useState(true)
  const [selectedAccountId, setSelectedAccountId] = useState<number | null>(null)
  const [generating, setGenerating] = useState(false)
  const [genResult, setGenResult] = useState<GenerateResult | null>(null)

  // Manual tweet state
  const [showManual, setShowManual] = useState(false)
  const [manualText, setManualText] = useState('')
  const [posting, setPosting] = useState(false)

  // Account setup
  const [editNiche, setEditNiche] = useState('')
  const [editAudience, setEditAudience] = useState('')
  const [editAutoGen, setEditAutoGen] = useState(true)
  const [savingSetup, setSavingSetup] = useState(false)

  // OAuth connect
  const [oauthLoading, setOauthLoading] = useState(false)

  // Manual token connect form
  const [showConnect, setShowConnect] = useState(false)
  const [connectToken, setConnectToken] = useState('')
  const [connectSecret, setConnectSecret] = useState('')
  const [connecting, setConnecting] = useState(false)
  const [connectError, setConnectError] = useState<string | null>(null)
  const [connectSuccess, setConnectSuccess] = useState<string | null>(null)

  const load = useCallback(async (showSpinner = true) => {
    if (showSpinner) setLoading(true)
    setError(null)
    try {
      const [h, a, s] = await Promise.all([
        apiFetch<HealthData>('/api/v1/twitter/health').catch(() => ({ status: 'error', message: 'Backend unreachable', accounts: [] })),
        apiFetch<AccountsResponse>('/api/v1/twitter/accounts').catch(() => ({ accounts: [], count: 0 })),
        apiFetch<StatsData>('/api/v1/twitter/stats').catch(() => null),
      ])
      setHealth(h)
      setAccounts(a)
      setStats(s)
      // Auto-select first account if none selected
      if (!selectedAccountId && a.accounts.length > 0) {
        setSelectedAccountId(a.accounts[0].id)
      }
    } catch {
      if (showSpinner) setError('Failed to load Twitter Hub')
    } finally {
      setLoading(false)
    }
  }, [selectedAccountId])

  useEffect(() => { load() }, [load])

  // Sync setup fields when selected account changes
  useEffect(() => {
    const acct = accounts?.accounts.find(a => a.id === selectedAccountId)
    if (acct) {
      setEditNiche(acct.niche || 'general')
      setEditAudience(acct.target_audience || 'general audience')
      setEditAutoGen(acct.auto_generate !== 0)
      // Also populate generate form
      if (acct.niche && acct.niche !== 'general') setNiche(acct.niche)
      if (acct.target_audience && acct.target_audience !== 'general audience') setAudience(acct.target_audience)
    }
  }, [selectedAccountId, accounts])

  // Load saved niche/audience from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('twitter_strategy')
    if (saved) {
      try {
        const data = JSON.parse(saved)
        if (data.niche) setNiche(data.niche)
        if (data.audience) setAudience(data.audience)
      } catch { /* ignore */ }
    }
  }, [])

  function handleOAuthConnect() {
    setOauthLoading(true)
    setConnectError(null)
    const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    const jwt = localStorage.getItem('access_token') || ''
    if (!jwt) { setConnectError('Not logged in. Please log in first.'); setOauthLoading(false); return }
    window.location.replace(`${apiBase}/api/v1/auth/x/authorize?token=${encodeURIComponent(jwt)}`)
  }

  const [setupSaved, setSetupSaved] = useState(false)

  async function handleSaveSetup() {
    if (!selectedAccountId) return
    setSavingSetup(true)
    setSetupSaved(false)
    try {
      await apiFetch(`/api/v1/twitter/accounts/${selectedAccountId}`, {
        method: 'PUT',
        body: JSON.stringify({
          niche: editNiche.trim() || 'general',
          target_audience: editAudience.trim() || 'general audience',
          auto_generate: editAutoGen,
        }),
      })
      // Update generate form
      setNiche(editNiche.trim())
      setAudience(editAudience.trim())
      setSetupSaved(true)
      setTimeout(() => setSetupSaved(false), 3000)
      load(false)
    } catch { /* ignore */ }
    finally { setSavingSetup(false) }
  }

  async function handleConnect() {
    if (!connectToken.trim() || !connectSecret.trim()) return
    setConnecting(true)
    setConnectError(null)
    setConnectSuccess(null)
    try {
      const result = await apiFetch<{ connected: boolean; account: { username: string; followers: number } }>(
        '/api/v1/twitter/accounts/connect',
        {
          method: 'POST',
          body: JSON.stringify({
            access_token: connectToken.trim(),
            access_token_secret: connectSecret.trim(),
          }),
        },
      )
      setConnectSuccess(`@${result.account.username} connected (${result.account.followers.toLocaleString()} followers)`)
      setConnectToken('')
      setConnectSecret('')
      load(false) // refetch without full spinner
      // Auto-close form after 2 seconds
      setTimeout(() => { setShowConnect(false); setConnectSuccess(null) }, 2000)
    } catch (e) {
      setConnectError(e instanceof Error ? e.message : 'Connection failed')
    } finally {
      setConnecting(false)
    }
  }

  async function handleDisconnect(accountId: number) {
    try {
      await apiFetch(`/api/v1/twitter/accounts/${accountId}`, { method: 'DELETE' })
      if (selectedAccountId === accountId) setSelectedAccountId(null)
      load(false)
    } catch { /* ignore */ }
  }

  async function handleGenerate() {
    if (!niche.trim()) return
    setGenerating(true)
    setGenResult(null)
    try {
      const result = await apiFetch<GenerateResult>('/api/v1/twitter/generate', {
        method: 'POST',
        body: JSON.stringify({
          niche: niche.trim(),
          target_audience: audience.trim() || 'general audience',
          count,
          include_threads: includeThreads,
          account_id: selectedAccountId,
        }),
        timeoutMs: 180_000,
      })
      setGenResult(result)
      load(false)
    } catch (e) {
      setGenResult({ generated: 0, items: [], error: e instanceof Error ? e.message : 'Generation failed' })
    } finally {
      setGenerating(false)
    }
  }

  async function handleManualTweet(postNow: boolean) {
    if (!manualText.trim()) return
    setPosting(true)
    try {
      await apiFetch('/api/v1/twitter/tweet/manual', {
        method: 'POST',
        body: JSON.stringify({
          content: manualText.trim(),
          post_now: postNow,
          account_id: selectedAccountId,
        }),
      })
      setManualText('')
      setShowManual(false)
      load(false)
    } catch { /* ignore */ }
    finally { setPosting(false) }
  }

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="text-center">
        <Loader2 className="w-7 h-7 animate-spin text-gray-400 mx-auto mb-3" />
        <p className="text-sm text-gray-400">Loading Twitter Hub...</p>
      </div>
    </div>
  )

  if (error) return (
    <div className="flex flex-col items-center justify-center h-64 gap-4 text-center">
      <XCircle className="w-8 h-8 text-red-400" />
      <p className="text-sm text-gray-800">{error}</p>
      <button onClick={() => load()} className="flex items-center gap-1.5 px-4 py-2 text-xs font-medium bg-gray-100 rounded-lg hover:bg-gray-200">
        <RefreshCw className="w-3.5 h-3.5" /> Try again
      </button>
    </div>
  )

  // Derive connected status from accounts list (primary) + health (fallback)
  const connectedAccounts = accounts?.accounts ?? []
  const isConnected = connectedAccounts.length > 0 || health?.status === 'connected'
  const primaryAccount = connectedAccounts[0] ?? null
  const statusText = isConnected
    ? (primaryAccount ? `@${primaryAccount.username} connected (${primaryAccount.followers.toLocaleString()} followers)` : (health?.message ?? 'Connected'))
    : 'No accounts connected'
  const q = stats?.queue

  return (
    <div className="space-y-6">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-black rounded-xl flex items-center justify-center shadow-sm">
            <Twitter size={18} className="text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-gray-900">Twitter Growth Engine</h1>
            <p className="text-xs text-gray-500 flex items-center gap-1.5">
              {isConnected ? (
                <><CheckCircle2 size={10} className="text-emerald-500" /> {statusText}</>
              ) : (
                <><AlertCircle size={10} className="text-amber-500" /> {statusText}</>
              )}
            </p>
          </div>
        </div>
        <button onClick={() => load()} className="p-2 rounded-lg hover:bg-gray-100 text-gray-400">
          <RefreshCw size={14} />
        </button>
      </div>

      {/* ── Connected Accounts ── */}
      <div className="card p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-gray-900 flex items-center gap-2">
            <Users size={14} className="text-blue-500" /> Connected Accounts
          </h3>
          <button
            onClick={() => { setShowConnect(!showConnect); setConnectError(null); setConnectSuccess(null) }}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold bg-black text-white rounded-lg hover:bg-gray-800 transition-colors"
          >
            <Plus size={12} /> Connect Account
          </button>
        </div>

        {/* Account cards */}
        {connectedAccounts.length > 0 ? (
          <div className="space-y-2">
            {connectedAccounts.map(acct => {
              const isSelected = selectedAccountId === acct.id
              return (
                <div
                  key={acct.id}
                  className={`flex items-center gap-3 p-3 rounded-lg border transition-colors cursor-pointer ${
                    isSelected ? 'border-brand-400 bg-brand-50' : 'border-gray-100 hover:border-gray-200 hover:bg-gray-50'
                  }`}
                  onClick={() => setSelectedAccountId(acct.id)}
                >
                  <div className="w-8 h-8 bg-black rounded-full flex items-center justify-center flex-shrink-0">
                    <Twitter size={12} className="text-white" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-gray-900">@{acct.username}</span>
                      {acct.display_name && <span className="text-xs text-gray-400">{acct.display_name}</span>}
                    </div>
                    <div className="flex items-center gap-3 mt-0.5">
                      <span className="text-[10px] text-gray-500">{acct.followers.toLocaleString()} followers</span>
                      <span className="text-[10px] text-gray-400">Connected {new Date(acct.connected_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                  {isSelected && (
                    <span className="text-[9px] font-bold text-brand-600 bg-brand-100 px-2 py-0.5 rounded-full">ACTIVE</span>
                  )}
                  <button
                    onClick={e => { e.stopPropagation(); handleDisconnect(acct.id) }}
                    className="p-1.5 rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50 transition-colors"
                    title="Disconnect"
                  >
                    <Trash2 size={12} />
                  </button>
                </div>
              )
            })}
          </div>
        ) : health?.accounts && health.accounts.length > 0 ? (
          /* .env fallback accounts */
          <div className="space-y-2">
            {health.accounts.filter(a => a.valid).map((acct, i) => (
              <div key={i} className="flex items-center gap-3 p-3 rounded-lg border border-gray-100 bg-gray-50">
                <div className="w-8 h-8 bg-black rounded-full flex items-center justify-center flex-shrink-0">
                  <Twitter size={12} className="text-white" />
                </div>
                <div className="flex-1 min-w-0">
                  <span className="text-sm font-semibold text-gray-900">@{acct.username}</span>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-[10px] text-gray-500">{acct.followers.toLocaleString()} followers</span>
                    <span className="text-[9px] bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded-full font-medium">via .env</span>
                  </div>
                </div>
                <ShieldCheck size={14} className="text-emerald-500" />
              </div>
            ))}
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3 py-6">
            <Twitter size={24} className="text-gray-300" />
            <p className="text-xs text-gray-400">No accounts connected yet</p>
            <div className="flex items-center gap-2">
              <button
                onClick={handleOAuthConnect}
                disabled={oauthLoading}
                className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold bg-black text-white rounded-lg hover:bg-gray-800 disabled:opacity-40 transition-colors"
              >
                {oauthLoading ? <Loader2 size={12} className="animate-spin" /> : <Twitter size={12} />}
                {oauthLoading ? 'Redirecting to X...' : 'Connect with OAuth'}
              </button>
              <span className="text-[10px] text-gray-300">or</span>
              <button
                onClick={() => setShowConnect(true)}
                className="text-xs text-gray-500 hover:text-gray-700 underline"
              >
                Enter tokens manually
              </button>
            </div>
            {connectError && !showConnect && (
              <p className="text-xs text-red-500">{connectError}</p>
            )}
          </div>
        )}

        {/* Account Setup — niche, audience, auto-generate */}
        {selectedAccountId && connectedAccounts.length > 0 && (
          <div className="mt-4 p-4 bg-blue-50 rounded-lg border border-blue-200">
            <h4 className="text-xs font-semibold text-gray-800 flex items-center gap-2 mb-3">
              <Zap size={12} className="text-blue-500" /> Account Growth Settings
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <label className="block text-[10px] font-medium text-slate-600 mb-1">Niche</label>
                <input
                  className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/30"
                  placeholder="e.g. AI tools, SaaS, crypto trading"
                  value={editNiche}
                  onChange={e => setEditNiche(e.target.value)}
                />
              </div>
              <div>
                <label className="block text-[10px] font-medium text-slate-600 mb-1">Target Audience</label>
                <input
                  className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/30"
                  placeholder="e.g. startup founders, indie hackers"
                  value={editAudience}
                  onChange={e => setEditAudience(e.target.value)}
                />
              </div>
            </div>
            <div className="flex items-center justify-between mt-3">
              <label className="flex items-center gap-2 text-xs text-gray-700 cursor-pointer">
                <input
                  type="checkbox"
                  checked={editAutoGen}
                  onChange={e => setEditAutoGen(e.target.checked)}
                  className="rounded border-gray-300"
                />
                Auto-generate daily tweets using trends
              </label>
              <button
                onClick={handleSaveSetup}
                disabled={savingSetup}
                className="flex items-center gap-1.5 px-4 py-1.5 text-xs font-semibold bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-40 transition-colors"
              >
                {savingSetup ? <Loader2 size={11} className="animate-spin" /> : <CheckCircle2 size={11} />}
                {savingSetup ? 'Saving...' : setupSaved ? 'Saved!' : 'Save Settings'}
              </button>
              {setupSaved && <span className="text-xs text-emerald-600 font-medium">Settings saved</span>}
            </div>
          </div>
        )}

        {/* Connect form */}
        {showConnect && (
          <div className="mt-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
            <h4 className="text-xs font-semibold text-gray-800 flex items-center gap-2 mb-3">
              <Key size={12} className="text-amber-500" /> Add X Access Tokens
            </h4>
            <p className="text-[10px] text-gray-500 mb-3 leading-relaxed">
              Go to <span className="font-semibold">developer.twitter.com</span> → Your App → Keys and Tokens → Generate Access Token &amp; Secret.
              Make sure app permissions are set to <span className="font-semibold">Read and Write</span>.
            </p>
            <div className="space-y-2">
              <input
                className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/30 font-mono"
                placeholder="Access Token"
                value={connectToken}
                onChange={e => setConnectToken(e.target.value)}
              />
              <input
                className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/30 font-mono"
                placeholder="Access Token Secret"
                type="password"
                value={connectSecret}
                onChange={e => setConnectSecret(e.target.value)}
              />
            </div>
            <div className="flex items-center gap-2 mt-3">
              <button
                onClick={handleConnect}
                disabled={connecting || !connectToken.trim() || !connectSecret.trim()}
                className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold bg-black text-white rounded-lg hover:bg-gray-800 disabled:opacity-40 transition-colors"
              >
                {connecting ? <Loader2 size={12} className="animate-spin" /> : <CheckCircle2 size={12} />}
                {connecting ? 'Verifying...' : 'Connect Account'}
              </button>
              <button onClick={() => setShowConnect(false)} className="px-3 py-2 text-xs text-gray-500 hover:text-gray-700">
                Cancel
              </button>
            </div>
            {connectError && (
              <div className="mt-2 flex items-center gap-2 text-xs text-red-600 bg-red-50 px-3 py-2 rounded-lg">
                <AlertCircle size={12} /> {connectError}
              </div>
            )}
            {connectSuccess && (
              <div className="mt-2 flex items-center gap-2 text-xs text-emerald-600 bg-emerald-50 px-3 py-2 rounded-lg">
                <CheckCircle2 size={12} /> {connectSuccess}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Stats Row */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
          {[
            { label: 'Pending', value: q?.pending ?? 0, color: 'text-amber-600', bg: 'bg-amber-50' },
            { label: 'Approved', value: q?.approved ?? 0, color: 'text-blue-600', bg: 'bg-blue-50' },
            { label: 'Posted', value: q?.posted ?? 0, color: 'text-emerald-600', bg: 'bg-emerald-50' },
            { label: 'Rejected', value: q?.rejected ?? 0, color: 'text-red-500', bg: 'bg-red-50' },
            { label: 'This Month', value: stats.this_month_posts, color: 'text-gray-800', bg: 'bg-gray-50' },
          ].map(s => (
            <div key={s.label} className={`${s.bg} rounded-xl p-4 text-center`}>
              <p className="text-[10px] font-medium text-gray-500 uppercase tracking-wider">{s.label}</p>
              <p className={`text-2xl font-bold ${s.color} mt-1`}>{s.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Monthly Usage Bar */}
      {stats && (
        <div className="card p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-gray-600">Monthly Usage</span>
            <span className="text-xs text-gray-400">{stats.this_month_posts} / {stats.monthly_limit} tweets</span>
          </div>
          <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-brand-500 rounded-full transition-all duration-500"
              style={{ width: `${Math.min(100, (stats.this_month_posts / stats.monthly_limit) * 100)}%` }}
            />
          </div>
          <p className="text-[10px] text-gray-400 mt-1">{stats.remaining_this_month} remaining this month</p>
        </div>
      )}

      {/* Generate Content Card */}
      <div className="card p-5">
        <h3 className="text-sm font-semibold text-gray-900 flex items-center gap-2 mb-4">
          <Zap size={14} className="text-brand-500" /> Generate Today&apos;s Content
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Niche *</label>
            <input
              className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-400"
              placeholder="e.g. AI tools for marketers"
              value={niche}
              onChange={e => setNiche(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Target Audience</label>
            <input
              className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-400"
              placeholder="e.g. startup founders, indie hackers"
              value={audience}
              onChange={e => setAudience(e.target.value)}
            />
          </div>
        </div>
        <div className="flex items-center gap-3 mt-3 flex-wrap">
          <select
            className="px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/30"
            value={count}
            onChange={e => setCount(Number(e.target.value))}
          >
            {[3, 5, 7, 10].map(n => <option key={n} value={n}>{n} tweets</option>)}
          </select>
          <label className="flex items-center gap-1.5 text-xs text-gray-600 cursor-pointer">
            <input
              type="checkbox"
              checked={includeThreads}
              onChange={e => setIncludeThreads(e.target.checked)}
              className="rounded border-gray-300"
            />
            Include thread
          </label>
          {connectedAccounts.length > 1 && (
            <select
              className="px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/30"
              value={selectedAccountId ?? ''}
              onChange={e => setSelectedAccountId(e.target.value ? Number(e.target.value) : null)}
            >
              <option value="">Default account</option>
              {connectedAccounts.map(a => (
                <option key={a.id} value={a.id}>@{a.username}</option>
              ))}
            </select>
          )}
          <button
            onClick={handleGenerate}
            disabled={generating || !niche.trim()}
            className="ml-auto flex items-center gap-2 px-5 py-2.5 bg-black text-white rounded-lg text-sm font-semibold hover:bg-gray-800 disabled:opacity-40 transition-colors"
          >
            {generating ? <Loader2 size={14} className="animate-spin" /> : <Zap size={14} />}
            {generating ? 'Generating (up to 60s)...' : 'Generate with AI'}
          </button>
        </div>

        {genResult && (
          <div className={`mt-4 flex items-center gap-2 text-xs px-4 py-3 rounded-lg ${
            genResult.error ? 'bg-red-50 text-red-700' : 'bg-emerald-50 text-emerald-700'
          }`}>
            {genResult.error ? <AlertCircle size={12} /> : <CheckCircle2 size={12} />}
            {genResult.error || genResult.message}
            {!genResult.error && (
              <Link href="/dashboard/twitter-engine/queue" className="ml-auto font-semibold underline whitespace-nowrap">
                Review Queue →
              </Link>
            )}
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Link href="/dashboard/twitter-engine/queue" className="card p-4 hover:bg-gray-50 transition-colors group text-center">
          <ListOrdered size={20} className="text-amber-500 mx-auto mb-2 group-hover:scale-110 transition-transform" />
          <p className="text-xs font-semibold text-gray-800">Review Queue</p>
          {q?.pending ? <p className="text-[10px] text-amber-600 font-medium mt-0.5">{q.pending} pending</p> : null}
        </Link>
        <Link href="/dashboard/twitter-engine/posted" className="card p-4 hover:bg-gray-50 transition-colors group text-center">
          <CheckCircle2 size={20} className="text-emerald-500 mx-auto mb-2 group-hover:scale-110 transition-transform" />
          <p className="text-xs font-semibold text-gray-800">Posted Tweets</p>
          {q?.posted ? <p className="text-[10px] text-emerald-600 font-medium mt-0.5">{q.posted} total</p> : null}
        </Link>
        <Link href="/dashboard/twitter-engine/strategy" className="card p-4 hover:bg-gray-50 transition-colors group text-center">
          <Map size={20} className="text-violet-500 mx-auto mb-2 group-hover:scale-110 transition-transform" />
          <p className="text-xs font-semibold text-gray-800">Growth Strategy</p>
          <p className="text-[10px] text-gray-400 mt-0.5">AI-powered plan</p>
        </Link>
        <button onClick={() => setShowManual(!showManual)} className="card p-4 hover:bg-gray-50 transition-colors group text-center">
          <Send size={20} className="text-blue-500 mx-auto mb-2 group-hover:scale-110 transition-transform" />
          <p className="text-xs font-semibold text-gray-800">Manual Tweet</p>
          <p className="text-[10px] text-gray-400 mt-0.5">Write & post</p>
        </button>
      </div>

      {/* Manual Tweet Modal */}
      {showManual && (
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-gray-900 flex items-center gap-2 mb-3">
            <Send size={14} className="text-blue-500" /> Manual Tweet
          </h3>
          <textarea
            rows={3}
            maxLength={280}
            className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/30 resize-none"
            placeholder="Write your tweet..."
            value={manualText}
            onChange={e => setManualText(e.target.value)}
          />
          <div className="flex items-center justify-between mt-2">
            <span className={`text-xs ${manualText.length > 260 ? 'text-red-500 font-semibold' : 'text-gray-400'}`}>
              {manualText.length}/280
            </span>
            <div className="flex gap-2">
              <button onClick={() => setShowManual(false)} className="px-3 py-1.5 text-xs text-gray-500 hover:text-gray-700">Cancel</button>
              <button
                onClick={() => handleManualTweet(false)}
                disabled={posting || !manualText.trim()}
                className="px-3 py-1.5 text-xs font-medium bg-gray-100 rounded-lg hover:bg-gray-200 disabled:opacity-40"
              >
                Save to Queue
              </button>
              <button
                onClick={() => handleManualTweet(true)}
                disabled={posting || !manualText.trim() || !isConnected}
                className="flex items-center gap-1.5 px-4 py-1.5 text-xs font-semibold bg-black text-white rounded-lg hover:bg-gray-800 disabled:opacity-40"
              >
                {posting ? <Loader2 size={12} className="animate-spin" /> : <Send size={12} />}
                Post Now
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Totals if any posted */}
      {stats && stats.totals.impressions > 0 && (
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-gray-900 flex items-center gap-2 mb-3">
            <TrendingUp size={14} className="text-emerald-500" /> Performance Totals
          </h3>
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center">
              <p className="text-2xl font-bold text-gray-900">{stats.totals.impressions.toLocaleString()}</p>
              <p className="text-[10px] text-gray-500">Impressions</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-gray-900">{stats.totals.likes.toLocaleString()}</p>
              <p className="text-[10px] text-gray-500">Likes</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-gray-900">{stats.totals.retweets.toLocaleString()}</p>
              <p className="text-[10px] text-gray-500">Retweets</p>
            </div>
          </div>
        </div>
      )}

    </div>
  )
}

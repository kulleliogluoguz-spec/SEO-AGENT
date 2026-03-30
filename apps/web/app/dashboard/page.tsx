'use client'

import { useEffect, useState, useCallback } from 'react'
import {
  Twitter, Instagram, FileText, Megaphone,
  CheckCircle2, AlertCircle, Loader2, ArrowRight,
  Clock, Activity, TrendingUp, Flame, Play, XCircle,
  RefreshCw, Zap, Calendar, Radio, ShieldCheck
} from 'lucide-react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { apiFetch } from '@/lib/apiFetch'

// ── Types ─────────────────────────────────────────────────────────────────────

interface ConnStatus { x: boolean; instagram: boolean; meta_ads: boolean; google_ads: boolean }
interface QueueStats { drafts: number; approved: number; scheduled_upcoming: number; published_total: number; needs_action: number; failed: number }
interface AutonState { any_auto_content: boolean; highest_mode: string; any_kill_switch_active: boolean }
interface AuditEvent { action: string; channel?: string; success: boolean; timestamp: string }
interface Trend { keyword: string; momentum_score: number }

// ── Big hero card ─────────────────────────────────────────────────────────────

function HeroBigCard({
  gradient,
  icon: Icon,
  iconInvertColor,
  title,
  subtitle,
  connected,
  primaryHref,
  primaryLabel,
  secondaryHref,
  secondaryLabel,
  connectHref,
  connectLabel,
  connLoading,
  extraContent,
}: {
  gradient: string
  icon: React.ElementType
  iconInvertColor?: boolean
  title: string
  subtitle: string
  connected: boolean | null
  primaryHref: string
  primaryLabel: string
  secondaryHref?: string
  secondaryLabel?: string
  connectHref: string
  connectLabel: string
  connLoading: boolean
  extraContent?: React.ReactNode
}) {
  return (
    <div className={`relative flex flex-col rounded-2xl overflow-hidden ${gradient} p-6 min-h-[280px]`}>
      {/* Icon + status */}
      <div className="flex items-start justify-between mb-4">
        <div className="w-12 h-12 rounded-xl bg-white/15 backdrop-blur-sm flex items-center justify-center flex-shrink-0">
          <Icon size={24} className={iconInvertColor ? 'text-gray-900' : 'text-white'} />
        </div>
        {connLoading ? (
          <span className="flex items-center gap-1.5 text-[11px] font-semibold px-3 py-1.5 rounded-full bg-white/20 text-white/70">
            <Loader2 size={10} className="animate-spin" /> Checking…
          </span>
        ) : connected === true ? (
          <span className="flex items-center gap-1.5 text-[11px] font-semibold px-3 py-1.5 rounded-full bg-white/25 text-white">
            <CheckCircle2 size={11} /> Connected
          </span>
        ) : connected === false ? (
          <span className="flex items-center gap-1.5 text-[11px] font-semibold px-3 py-1.5 rounded-full bg-black/20 text-white/80">
            <AlertCircle size={11} /> Not connected
          </span>
        ) : null}
      </div>

      {/* Title */}
      <div className="flex-1">
        <h2 className="text-xl font-bold text-white leading-tight mb-2">{title}</h2>
        <p className="text-sm text-white/70 leading-relaxed">{subtitle}</p>
        {extraContent && <div className="mt-3">{extraContent}</div>}
      </div>

      {/* CTAs */}
      <div className="mt-5 space-y-2">
        {connected === false ? (
          <Link
            href={connectHref}
            className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-white text-gray-900 text-sm font-bold hover:bg-gray-100 transition-colors shadow-sm"
          >
            <Zap size={14} /> {connectLabel}
          </Link>
        ) : (
          <>
            <Link
              href={primaryHref}
              className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-white/20 backdrop-blur-sm border border-white/30 text-white text-sm font-bold hover:bg-white/30 transition-colors"
            >
              {primaryLabel} <ArrowRight size={14} />
            </Link>
            {secondaryHref && secondaryLabel && (
              <Link
                href={secondaryHref}
                className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl bg-white/10 border border-white/20 text-white/80 text-xs font-semibold hover:bg-white/20 transition-colors"
              >
                {secondaryLabel}
              </Link>
            )}
          </>
        )}
      </div>
    </div>
  )
}

// ── Connection pill ────────────────────────────────────────────────────────────

function ConnPill({ label, ok, loading, href }: { label: string; ok: boolean; loading: boolean; href: string }) {
  return (
    <Link href={href} className={`flex items-center gap-1.5 px-3 py-2 rounded-xl border text-xs font-semibold transition-all ${
      loading ? 'border-gray-200 text-gray-400 bg-gray-50' :
      ok ? 'border-emerald-200 text-emerald-700 bg-emerald-50 hover:bg-emerald-100' :
      'border-amber-200 text-amber-700 bg-amber-50 hover:bg-amber-100'
    }`}>
      {loading
        ? <Loader2 size={9} className="animate-spin" />
        : <span className={`w-2 h-2 rounded-full flex-shrink-0 ${ok ? 'bg-emerald-500' : 'bg-amber-400'}`} />
      }
      {label}
      {!loading && !ok && <span className="text-[9px] opacity-70">→ Connect</span>}
    </Link>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function OverviewPage() {
  const router = useRouter()

  // Connection state — null = unknown/loading
  const [conn, setConn] = useState<ConnStatus | null>(null)
  const [connLoading, setConnLoading] = useState(true)

  // Secondary data — loaded async, never blocks main UI
  const [queue, setQueue] = useState<QueueStats | null>(null)
  const [auton, setAuton] = useState<AutonState | null>(null)
  const [activity, setActivity] = useState<AuditEvent[]>([])
  const [trends, setTrends] = useState<Trend[]>([])
  const [brandName, setBrandName] = useState<string | null>(null)

  // ── Load connection status first (fastest, most critical) ──
  const loadConn = useCallback(async () => {
    setConnLoading(true)
    try {
      const data = await apiFetch<{ channels: Array<{ channel: string; ready: boolean }> }>('/api/v1/connectors/social/health')
      const channels = data.channels ?? []
      const ready = (ch: string) => channels.find(c => c.channel === ch)?.ready ?? false

      // Also try to get ad account status from connectors summary
      let metaReady = false, googleReady = false
      try {
        const sum = await apiFetch<{ ready_channels: string[] }>('/api/v1/connectors/summary')
        metaReady = (sum.ready_channels ?? []).includes('meta_ads')
        googleReady = (sum.ready_channels ?? []).includes('google_ads')
      } catch { /* ignore */ }

      setConn({ x: ready('x'), instagram: ready('instagram'), meta_ads: metaReady, google_ads: googleReady })
    } catch {
      // If endpoint fails, show disconnected for all
      setConn({ x: false, instagram: false, meta_ads: false, google_ads: false })
    } finally {
      setConnLoading(false)
    }
  }, [])

  // ── Load everything else in background ──
  useEffect(() => {
    loadConn()

    // Auth check first
    const token = localStorage.getItem('access_token')
    if (!token) { router.replace('/auth'); return }

    // Brand name + trends (single call)
    apiFetch<{ brand_name: string; top_trends: Trend[] }>('/api/v1/brand/overview')
      .then(d => { setBrandName(d.brand_name); setTrends(d.top_trends ?? []) })
      .catch(() => {})

    // Queue stats
    apiFetch<QueueStats>('/api/v1/content-queue/summary')
      .then(d => setQueue(d))
      .catch(() => {})

    // Autonomy
    apiFetch<AutonState>('/api/v1/autonomy/summary')
      .then(d => setAuton(d))
      .catch(() => {})

    // Activity
    apiFetch<{ events: AuditEvent[] }>('/api/v1/publishing/audit?limit=5')
      .then(d => setActivity(d.events ?? []))
      .catch(() => {})
  }, [loadConn, router])

  const xOk = conn?.x ?? false
  const igOk = conn?.instagram ?? false
  const adsOk = (conn?.meta_ads ?? false) || (conn?.google_ads ?? false)

  return (
    <div className="space-y-8">

      {/* ── PAGE HEADER ── */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Radio size={10} className="text-emerald-500 animate-pulse" />
            <span className="text-[11px] font-semibold text-emerald-600 uppercase tracking-widest">Live</span>
          </div>
          <h1 className="text-3xl font-black text-gray-900 leading-tight">
            {brandName ? brandName : 'What do you want to grow today?'}
          </h1>
          {brandName && (
            <p className="text-base text-gray-500 mt-1 font-medium">What do you want to grow today?</p>
          )}
        </div>
        <button onClick={loadConn} className="p-2 rounded-lg hover:bg-gray-100 text-gray-400 transition-colors mt-1" title="Refresh">
          <RefreshCw size={15} />
        </button>
      </div>

      {/* ── 4 GIANT HERO CARDS — ALWAYS VISIBLE ── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">

        {/* X */}
        <HeroBigCard
          gradient="bg-gradient-to-br from-gray-900 via-gray-800 to-black"
          icon={Twitter}
          title="Grow My X Account"
          subtitle="Generate trend-aware posts, auto-publish, and track follower growth with AI-powered insights."
          connected={connLoading ? null : xOk}
          connLoading={connLoading}
          primaryHref="/dashboard/growth/x-test"
          primaryLabel="Open X Console"
          secondaryHref="/dashboard/content/queue"
          secondaryLabel="View content queue"
          connectHref="/dashboard/connectors"
          connectLabel="Connect X Account"
          extraContent={xOk ? (
            <div className="flex gap-2 flex-wrap">
              <span className="text-[10px] bg-white/10 text-white/60 px-2 py-1 rounded-full">Auto-publish</span>
              <span className="text-[10px] bg-white/10 text-white/60 px-2 py-1 rounded-full">Trend-aware</span>
              <span className="text-[10px] bg-white/10 text-white/60 px-2 py-1 rounded-full">AI learning</span>
            </div>
          ) : (
            <p className="text-xs text-white/50">Connect your X account to start generating and publishing posts automatically</p>
          )}
        />

        {/* Instagram */}
        <HeroBigCard
          gradient="bg-gradient-to-br from-pink-600 via-rose-500 to-purple-700"
          icon={Instagram}
          title="Grow My Instagram"
          subtitle="Create carousels, Reel scripts, and captions. Grow your following with visual content that performs."
          connected={connLoading ? null : igOk}
          connLoading={connLoading}
          primaryHref="/dashboard/growth/instagram"
          primaryLabel="Open Instagram Console"
          secondaryHref="/dashboard/content/queue"
          secondaryLabel="View content queue"
          connectHref="/dashboard/connectors"
          connectLabel="Connect Instagram"
          extraContent={igOk ? (
            <div className="flex gap-2 flex-wrap">
              <span className="text-[10px] bg-white/10 text-white/60 px-2 py-1 rounded-full">Carousels</span>
              <span className="text-[10px] bg-white/10 text-white/60 px-2 py-1 rounded-full">Reels</span>
              <span className="text-[10px] bg-white/10 text-white/60 px-2 py-1 rounded-full">Captions</span>
            </div>
          ) : (
            <p className="text-xs text-white/60">Connect a Business or Creator Instagram account to start publishing</p>
          )}
        />

        {/* Create Posts */}
        <HeroBigCard
          gradient="bg-gradient-to-br from-blue-600 via-blue-500 to-indigo-700"
          icon={FileText}
          title="Create Posts"
          subtitle="Batch-generate posts for X and Instagram. Review, approve, and schedule your content in one place."
          connected={true}
          connLoading={false}
          primaryHref="/dashboard/content"
          primaryLabel="Create Post Batch"
          secondaryHref="/dashboard/content/queue"
          secondaryLabel="Review & schedule"
          connectHref="/dashboard/content"
          connectLabel="Create Posts"
          extraContent={queue ? (
            <div className="flex items-center gap-4">
              {[
                { label: 'Drafts', value: queue.drafts },
                { label: 'Approved', value: queue.approved },
                { label: 'Scheduled', value: queue.scheduled_upcoming },
              ].map(s => (
                <div key={s.label}>
                  <div className="text-xl font-black text-white">{s.value}</div>
                  <div className="text-[10px] text-white/60">{s.label}</div>
                </div>
              ))}
              {queue.needs_action > 0 && (
                <div className="ml-auto flex items-center gap-1.5 px-2.5 py-1 bg-amber-400/20 border border-amber-300/30 rounded-lg">
                  <Clock size={10} className="text-amber-200" />
                  <span className="text-[10px] font-bold text-amber-200">{queue.needs_action} need review</span>
                </div>
              )}
            </div>
          ) : (
            <p className="text-xs text-white/60">Generate, review, approve, and schedule posts for all your channels</p>
          )}
        />

        {/* Promote My Site */}
        <HeroBigCard
          gradient="bg-gradient-to-br from-violet-700 via-purple-600 to-indigo-800"
          icon={Megaphone}
          title="Promote My Site"
          subtitle="Launch paid ad campaigns on Meta and Google. AI-generated copy, audience targeting, and budget optimization."
          connected={connLoading ? null : adsOk}
          connLoading={connLoading}
          primaryHref="/dashboard/promote"
          primaryLabel="Launch Ad Campaign"
          secondaryHref="/dashboard/campaigns"
          secondaryLabel="View live campaigns"
          connectHref="/dashboard/connectors"
          connectLabel="Connect Ad Account"
          extraContent={adsOk ? (
            <div className="flex gap-2 flex-wrap">
              {conn?.meta_ads && <span className="text-[10px] bg-white/10 text-white/60 px-2 py-1 rounded-full">Meta Ads ✓</span>}
              {conn?.google_ads && <span className="text-[10px] bg-white/10 text-white/60 px-2 py-1 rounded-full">Google Ads ✓</span>}
            </div>
          ) : (
            <p className="text-xs text-white/60">Connect Meta or Google Ads to launch and optimize paid campaigns</p>
          )}
        />
      </div>

      {/* ── CONNECTION STRIP ── */}
      <div className="flex flex-col gap-3 p-4 bg-white border border-gray-200 rounded-2xl shadow-card">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold text-gray-500 uppercase tracking-widest">Account connections</span>
          <Link href="/dashboard/connectors" className="text-xs text-brand-600 hover:text-brand-700 font-semibold">
            Manage all →
          </Link>
        </div>
        <div className="flex flex-wrap gap-2">
          <ConnPill label="X / Twitter" ok={xOk} loading={connLoading} href="/dashboard/connectors" />
          <ConnPill label="Instagram" ok={igOk} loading={connLoading} href="/dashboard/connectors" />
          <ConnPill label="Meta Ads" ok={conn?.meta_ads ?? false} loading={connLoading} href="/dashboard/connectors" />
          <ConnPill label="Google Ads" ok={conn?.google_ads ?? false} loading={connLoading} href="/dashboard/connectors" />
          <div className="ml-auto flex items-center">
            {auton ? (
              <span className={`flex items-center gap-1.5 text-[11px] font-semibold px-3 py-1.5 rounded-xl border ${
                auton.any_kill_switch_active ? 'bg-red-50 text-red-700 border-red-200' :
                auton.any_auto_content ? 'bg-emerald-50 text-emerald-700 border-emerald-200' :
                'bg-amber-50 text-amber-700 border-amber-200'
              }`}>
                <ShieldCheck size={11} />
                {auton.any_kill_switch_active ? 'Kill switch ON' :
                 auton.any_auto_content ? `Auto-publish (${auton.highest_mode})` : 'Manual approval mode'}
              </span>
            ) : (
              <Link href="/dashboard/settings" className="text-xs text-gray-400 hover:text-gray-600">
                Autonomy settings →
              </Link>
            )}
          </div>
        </div>
      </div>

      {/* ── QUICK OPERATIONS ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">

        {/* Operations panel */}
        <div className="lg:col-span-1 card p-5">
          <h3 className="text-sm font-bold text-gray-900 mb-4 flex items-center gap-2">
            <Zap size={14} className="text-brand-500" /> Quick Actions
          </h3>
          <div className="space-y-1.5">
            {[
              { label: 'Generate X posts', href: '/dashboard/growth/x-test', enabled: xOk, note: xOk ? undefined : 'Connect X first' },
              { label: 'Generate Instagram content', href: '/dashboard/growth/instagram', enabled: igOk, note: igOk ? undefined : 'Connect Instagram first' },
              { label: `Review ${queue?.needs_action ?? 0} pending approvals`, href: '/dashboard/approvals', enabled: true, badge: queue?.needs_action ?? 0 },
              { label: 'Schedule approved posts', href: '/dashboard/content/queue', enabled: true },
              { label: 'Launch ad campaign', href: '/dashboard/promote', enabled: adsOk, note: adsOk ? undefined : 'Connect ad account first' },
              { label: 'Browse trending topics', href: '/dashboard/trends', enabled: true },
            ].map((a, i) => (
              <Link
                key={i}
                href={a.href}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-all ${
                  a.enabled ? 'text-gray-700 hover:bg-gray-50 hover:text-gray-900' : 'text-gray-300 pointer-events-none'
                }`}
              >
                <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${a.enabled ? 'bg-brand-500' : 'bg-gray-200'}`} />
                <span className="flex-1 text-xs font-medium">{a.label}</span>
                {a.badge !== undefined && a.badge > 0 && (
                  <span className="text-[10px] font-bold bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded-full">{a.badge}</span>
                )}
                {a.note && <span className="text-[9px] text-amber-500 font-semibold">{a.note}</span>}
              </Link>
            ))}
          </div>
        </div>

        {/* Post queue summary */}
        <div className="card p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold text-gray-900 flex items-center gap-2">
              <FileText size={14} className="text-blue-500" /> Post Queue
            </h3>
            <Link href="/dashboard/content" className="text-xs text-brand-600 hover:text-brand-700 font-semibold">Manage →</Link>
          </div>
          {queue === null ? (
            <div className="py-6 text-center">
              <Loader2 size={16} className="animate-spin text-gray-300 mx-auto mb-2" />
              <p className="text-xs text-gray-400">Loading…</p>
            </div>
          ) : (
            <>
              <div className="grid grid-cols-2 gap-2 mb-3">
                {[
                  { label: 'Drafts', value: queue.drafts, bg: 'bg-gray-50 border-gray-200', text: 'text-gray-800' },
                  { label: 'Approved', value: queue.approved, bg: 'bg-emerald-50 border-emerald-100', text: 'text-emerald-800' },
                  { label: 'Scheduled', value: queue.scheduled_upcoming, bg: 'bg-blue-50 border-blue-100', text: 'text-blue-800' },
                  { label: 'Published', value: queue.published_total, bg: 'bg-violet-50 border-violet-100', text: 'text-violet-800' },
                ].map(s => (
                  <div key={s.label} className={`${s.bg} border rounded-xl p-3 text-center`}>
                    <div className={`text-2xl font-black ${s.text}`}>{s.value}</div>
                    <div className={`text-[10px] font-semibold ${s.text} opacity-70 mt-0.5`}>{s.label}</div>
                  </div>
                ))}
              </div>
              {queue.needs_action > 0 && (
                <Link href="/dashboard/approvals" className="flex items-center gap-2 px-3 py-2 bg-amber-50 border border-amber-200 rounded-xl text-xs font-semibold text-amber-700 hover:bg-amber-100 transition-colors">
                  <Clock size={11} /> {queue.needs_action} post{queue.needs_action > 1 ? 's' : ''} waiting for approval
                  <ArrowRight size={10} className="ml-auto" />
                </Link>
              )}
              <Link href="/dashboard/content" className="mt-2 w-full flex items-center justify-center gap-2 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-bold transition-colors">
                <FileText size={11} /> Create new posts
              </Link>
            </>
          )}
        </div>

        {/* Activity feed */}
        <div className="card p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold text-gray-900 flex items-center gap-2">
              <Activity size={14} className="text-blue-500" /> Recent Activity
            </h3>
            <Link href="/dashboard/activity" className="text-xs text-brand-600 hover:text-brand-700 font-semibold">All →</Link>
          </div>
          {activity.length === 0 ? (
            <div className="flex flex-col items-center py-6 gap-2 text-center">
              <Play size={20} className="text-gray-200" />
              <p className="text-xs text-gray-400">No activity yet</p>
              <p className="text-[10px] text-gray-300">Connect accounts and publish posts to see activity</p>
            </div>
          ) : (
            <div className="space-y-2">
              {activity.map((e, i) => (
                <div key={i} className="flex items-start gap-2.5">
                  <div className={`w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 ${e.success ? 'bg-emerald-50' : 'bg-red-50'}`}>
                    {e.success ? <CheckCircle2 size={10} className="text-emerald-500" /> : <XCircle size={10} className="text-red-400" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-gray-700 truncate">{e.action.replace(/\./g, ' › ')}</p>
                    {e.channel && <p className="text-[10px] text-gray-400 capitalize">{e.channel}</p>}
                  </div>
                  <span className="text-[10px] text-gray-300 flex-shrink-0">
                    {new Date(e.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* ── TRENDS (secondary, bottom) ── */}
      {trends.length > 0 && (
        <div className="card p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold text-gray-900 flex items-center gap-2">
              <Flame size={14} className="text-orange-500" /> Hot Trends Right Now
            </h3>
            <Link href="/dashboard/trends" className="text-xs text-brand-600 hover:text-brand-700 font-semibold">See all →</Link>
          </div>
          <div className="flex flex-wrap gap-2">
            {trends.slice(0, 8).map((t, i) => (
              <Link
                key={i}
                href="/dashboard/content"
                className="flex items-center gap-1.5 px-3 py-1.5 bg-orange-50 border border-orange-100 rounded-full text-xs font-semibold text-orange-700 hover:bg-orange-100 transition-colors"
              >
                <TrendingUp size={9} />
                {t.keyword}
                <span className="text-[9px] font-normal opacity-60">{Math.round(t.momentum_score * 100)}</span>
              </Link>
            ))}
          </div>
        </div>
      )}

    </div>
  )
}

'use client'

import { useEffect, useState } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import Link from 'next/link'
import { isAuthenticated, clearTokens } from '@/lib/auth'
import {
  LayoutDashboard, FileText, CheckSquare, BarChart2,
  Plug, Settings, Activity, LogOut, TrendingUp,
  ChevronDown, Bell, ShieldCheck, Sparkles, Radio,
  Megaphone, Twitter, Instagram, Brain, ListOrdered,
  LineChart, Zap, Shield,
} from 'lucide-react'

const NAV_SECTIONS = [
  {
    label: '',
    items: [
      { href: '/dashboard', label: 'Overview', icon: LayoutDashboard, exact: true },
    ],
  },
  {
    label: 'Grow',
    items: [
      { href: '/dashboard/growth/x-test',    label: 'Grow X Account',   icon: Twitter },
      { href: '/dashboard/growth/instagram', label: 'Grow Instagram',    icon: Instagram },
      { href: '/dashboard/promote',          label: 'Promote My Site',   icon: Megaphone },
    ],
  },
  {
    label: 'Content',
    items: [
      { href: '/dashboard/content',        label: 'Create Posts',     icon: FileText, exact: true },
      { href: '/dashboard/content/queue',  label: 'Schedule Queue',   icon: ListOrdered },
      { href: '/dashboard/approvals',      label: 'Approvals',        icon: CheckSquare },
    ],
  },
  {
    label: 'Insights',
    items: [
      { href: '/dashboard/trends',   label: 'Trend Feed',     icon: TrendingUp },
      { href: '/dashboard/learning', label: 'Learning',       icon: Brain },
      { href: '/dashboard/reports',  label: 'Growth Metrics', icon: LineChart },
    ],
  },
  {
    label: 'Workspace',
    items: [
      { href: '/dashboard/connectors', label: 'Connections', icon: Plug },
      { href: '/dashboard/setup',      label: 'Brand Setup',  icon: Sparkles },
      { href: '/dashboard/settings',   label: 'Autonomy',     icon: Shield },
      { href: '/dashboard/activity',   label: 'Activity',     icon: Activity },
    ],
  },
]

interface NavItemProps {
  href: string
  label: string
  icon: React.ElementType
  badge?: string
  exact?: boolean
  active: boolean
}

function NavItem({ href, label, icon: Icon, badge, active }: NavItemProps) {
  return (
    <Link
      href={href}
      className={`group flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] font-medium transition-all duration-150 ${
        active
          ? 'bg-brand-600 text-white shadow-sm'
          : 'text-slate-400 hover:bg-slate-800 hover:text-slate-100'
      }`}
    >
      <Icon size={14} className="flex-shrink-0 opacity-80" />
      <span className="flex-1 truncate">{label}</span>
      {badge === 'NEW' && (
        <span className="text-[9px] px-1.5 py-0.5 rounded font-bold bg-brand-500/20 text-brand-300 tracking-wide">
          NEW
        </span>
      )}
      {badge && badge !== 'NEW' && (
        <span className={`min-w-[18px] h-[18px] flex items-center justify-center text-[10px] rounded-full font-semibold ${
          active ? 'bg-white/20 text-white' : 'bg-amber-500/20 text-amber-300'
        }`}>{badge}</span>
      )}
    </Link>
  )
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const router = useRouter()
  const [currentTime, setCurrentTime] = useState('')

  useEffect(() => {
    if (!isAuthenticated()) router.replace('/auth')
  }, [router])

  useEffect(() => {
    const tick = () => setCurrentTime(new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }))
    tick()
    const id = setInterval(tick, 60000)
    return () => clearInterval(id)
  }, [])

  function handleLogout() {
    clearTokens()
    router.push('/auth')
  }

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden">
      {/* ── Sidebar ── */}
      <aside className="w-[220px] bg-sidebar-bg flex flex-col flex-shrink-0 select-none">

        {/* Logo */}
        <div className="h-14 flex items-center gap-3 px-4 border-b border-slate-800">
          <div className="w-8 h-8 bg-brand-600 rounded-lg flex items-center justify-center flex-shrink-0 shadow-sm">
            <Sparkles size={14} className="text-white" />
          </div>
          <div>
            <div className="text-[13px] font-semibold text-slate-100 leading-tight tracking-tight">AI Growth OS</div>
            <div className="text-[10px] text-slate-500 leading-tight">Growth Intelligence</div>
          </div>
        </div>

        {/* Workspace */}
        <div className="px-3 py-2 border-b border-slate-800">
          <button className="w-full flex items-center justify-between px-2.5 py-2 rounded-lg hover:bg-slate-800 transition-colors">
            <div className="flex items-center gap-2 min-w-0">
              <div className="w-5 h-5 rounded bg-brand-600/20 flex items-center justify-center flex-shrink-0">
                <span className="text-brand-300 text-[10px] font-bold">A</span>
              </div>
              <span className="text-[13px] text-slate-300 font-medium truncate">Acme Growth</span>
            </div>
            <ChevronDown size={12} className="text-slate-500 flex-shrink-0" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto p-2 space-y-4">
          {NAV_SECTIONS.map(section => (
            <div key={section.label || '__top'}>
              {section.label && (
                <p className="px-3 mb-1 text-[10px] font-semibold text-slate-600 uppercase tracking-widest">
                  {section.label}
                </p>
              )}
              <div className="space-y-0.5">
                {section.items.map(item => (
                  <NavItem
                    key={item.href}
                    {...item}
                    active={
                      (item as { exact?: boolean }).exact
                        ? pathname === item.href
                        : pathname.startsWith(item.href)
                    }
                  />
                ))}
              </div>
            </div>
          ))}
        </nav>

        {/* Autonomy badge */}
        <div className="px-3 py-2 border-t border-slate-800">
          <div className="flex items-center gap-2 px-2.5 py-1.5 bg-amber-500/10 rounded-lg border border-amber-500/20">
            <ShieldCheck size={11} className="text-amber-400 flex-shrink-0" />
            <span className="text-[11px] text-amber-300 font-medium">Level 1 — Draft Only</span>
          </div>
        </div>

        {/* User footer */}
        <div className="px-3 py-3 border-t border-slate-800">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-full bg-brand-600/20 flex items-center justify-center flex-shrink-0 ring-1 ring-brand-500/30">
              <span className="text-brand-300 text-[11px] font-semibold">D</span>
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-[12px] font-medium text-slate-300 truncate">Demo User</div>
              <div className="text-[10px] text-slate-500 truncate">demo@aicmo.os</div>
            </div>
            <button
              onClick={handleLogout}
              className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-500 hover:text-slate-300 transition-colors"
              title="Sign out"
            >
              <LogOut size={12} />
            </button>
          </div>
        </div>
      </aside>

      {/* ── Main area ── */}
      <div className="flex-1 flex flex-col overflow-hidden">

        {/* Top header */}
        <header className="h-14 bg-white border-b border-gray-200 flex items-center justify-between px-6 flex-shrink-0">
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <Radio size={12} className="text-emerald-500 animate-pulse" />
            <span className="text-emerald-600 font-medium">Live</span>
            <span className="text-gray-300">·</span>
            <span>Acme Growth Workspace</span>
          </div>

          <div className="flex items-center gap-3">
            <span className="text-xs text-gray-400 font-mono">{currentTime}</span>
            <div className="h-4 w-px bg-gray-200" />
            <button className="relative p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors">
              <Bell size={15} />
              <span className="absolute top-1 right-1 w-1.5 h-1.5 bg-red-500 rounded-full" />
            </button>
            <div className="w-7 h-7 rounded-full bg-brand-100 flex items-center justify-center">
              <span className="text-brand-700 text-xs font-semibold">D</span>
            </div>
          </div>
        </header>

        {/* Scrollable content */}
        <main className="flex-1 overflow-y-auto">
          <div className="p-6 min-h-full animate-fade-in">
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}

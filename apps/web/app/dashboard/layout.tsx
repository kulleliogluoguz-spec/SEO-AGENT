'use client'

import { useEffect } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import Link from 'next/link'
import { isAuthenticated, clearTokens } from '@/lib/auth'
import {
  LayoutDashboard, Globe, Search, Zap, FileText,
  CheckSquare, BarChart2, FlaskConical, Plug, Settings,
  Activity, LogOut, ChevronDown, Bell, ShieldCheck
} from 'lucide-react'

const NAV_ITEMS = [
  { href: '/dashboard', label: 'Overview', icon: LayoutDashboard, exact: true },
  { href: '/dashboard/sites', label: 'Sites', icon: Globe },
  { href: '/dashboard/seo', label: 'SEO Audit', icon: Search },
  { href: '/dashboard/geo', label: 'AI Visibility', icon: Zap, experimental: true },
  { href: '/dashboard/content', label: 'Content', icon: FileText },
  { href: '/dashboard/approvals', label: 'Approvals', icon: CheckSquare, badge: '1' },
  { href: '/dashboard/reports', label: 'Reports', icon: BarChart2 },
  { href: '/dashboard/experiments', label: 'Experiments', icon: FlaskConical },
  { href: '/dashboard/connectors', label: 'Connectors', icon: Plug },
  { href: '/dashboard/activity', label: 'Activity', icon: Activity },
  { href: '/dashboard/admin', label: 'System', icon: Settings },
]

interface NavItemProps {
  href: string
  label: string
  icon: React.ElementType
  badge?: string
  experimental?: boolean
  exact?: boolean
  active: boolean
}

function NavItem({ href, label, icon: Icon, badge, experimental, active }: NavItemProps) {
  return (
    <Link
      href={href}
      className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
        active
          ? 'bg-brand-600 text-white'
          : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
      }`}
    >
      <Icon size={15} className="flex-shrink-0" />
      <span className="flex-1 truncate">{label}</span>
      {experimental && (
        <span className={`text-[10px] px-1 py-0.5 rounded font-medium ${
          active ? 'bg-white/20 text-white' : 'bg-purple-100 text-purple-700'
        }`}>BETA</span>
      )}
      {badge && (
        <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${
          active ? 'bg-white/20 text-white' : 'bg-yellow-100 text-yellow-800'
        }`}>{badge}</span>
      )}
    </Link>
  )
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const router = useRouter()

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace('/auth')
    }
  }, [router])

  function handleLogout() {
    clearTokens()
    router.push('/auth')
  }

  return (
    <div className="flex h-screen bg-gray-50 overflow-hidden">
      {/* Sidebar */}
      <aside className="w-56 bg-white border-r border-gray-200 flex flex-col flex-shrink-0">
        {/* Logo */}
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 bg-brand-600 rounded-lg flex items-center justify-center flex-shrink-0">
              <span className="text-white text-xs font-bold">AI</span>
            </div>
            <div>
              <div className="text-sm font-bold text-gray-900 leading-tight">AI CMO OS</div>
              <div className="text-[10px] text-gray-400 leading-tight">Growth Operating System</div>
            </div>
          </div>
        </div>

        {/* Workspace switcher */}
        <div className="px-3 py-2 border-b border-gray-200">
          <button className="w-full flex items-center justify-between px-2 py-1.5 rounded-lg hover:bg-gray-50 text-sm">
            <span className="text-gray-700 font-medium truncate">Acme Growth</span>
            <ChevronDown size={13} className="text-gray-400 flex-shrink-0" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto p-2 space-y-0.5">
          {NAV_ITEMS.map(item => (
            <NavItem
              key={item.href}
              {...item}
              active={
                item.exact
                  ? pathname === item.href
                  : pathname.startsWith(item.href) && !item.exact
              }
            />
          ))}
        </nav>

        {/* Autonomy level indicator */}
        <div className="px-3 py-2 border-t border-gray-100">
          <div className="flex items-center gap-2 px-2 py-1.5 bg-yellow-50 rounded-lg">
            <ShieldCheck size={12} className="text-yellow-600 flex-shrink-0" />
            <span className="text-[11px] text-yellow-700 font-medium">Level 1 — Draft Only</span>
          </div>
        </div>

        {/* User footer */}
        <div className="p-3 border-t border-gray-200">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 bg-brand-100 rounded-full flex items-center justify-center flex-shrink-0">
              <span className="text-brand-700 text-xs font-semibold">D</span>
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-xs font-medium text-gray-900 truncate">Demo User</div>
              <div className="text-[10px] text-gray-400 truncate">demo@aicmo.os</div>
            </div>
            <button onClick={handleLogout} className="p-1 rounded hover:bg-gray-100 text-gray-400" title="Sign out">
              <LogOut size={13} />
            </button>
          </div>
        </div>
      </aside>

      {/* Main content area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top header */}
        <header className="h-12 bg-white border-b border-gray-200 flex items-center justify-between px-6 flex-shrink-0">
          <div className="text-xs text-gray-400">
            Workspace: <span className="text-gray-600 font-medium">Acme Growth</span>
          </div>
          <button className="relative p-1.5 rounded-lg hover:bg-gray-100 text-gray-500">
            <Bell size={15} />
            <span className="absolute top-1 right-1 w-1.5 h-1.5 bg-red-500 rounded-full" />
          </button>
        </header>

        {/* Scrollable content */}
        <main className="flex-1 overflow-y-auto p-6">
          {children}
        </main>
      </div>
    </div>
  )
}

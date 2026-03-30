'use client'

import { useState, useEffect, useCallback } from 'react'
import { apiFetch } from '@/lib/apiFetch'
import {
  Shield,
  Zap,
  AlertTriangle,
  CheckCircle,
  XCircle,
  ToggleLeft,
  ToggleRight,
  DollarSign,
  Lock,
  Unlock,
} from 'lucide-react'

const AUTONOMY_MODES = [
  { value: 'manual', label: 'Manual', desc: 'You approve every action', color: 'bg-gray-100 text-gray-700' },
  { value: 'assisted', label: 'Assisted', desc: 'AI suggests, you decide', color: 'bg-blue-100 text-blue-700' },
  { value: 'semi_auto', label: 'Semi-Auto', desc: 'Auto below threshold, you approve above', color: 'bg-yellow-100 text-yellow-700' },
  { value: 'autonomous', label: 'Autonomous', desc: 'Full automation within your caps', color: 'bg-green-100 text-green-700' },
]

const CHANNELS = [
  { key: 'x', label: 'X / Twitter', emoji: '𝕏' },
  { key: 'instagram', label: 'Instagram', emoji: '📸' },
  { key: 'tiktok', label: 'TikTok', emoji: '🎵' },
  { key: 'meta_ads', label: 'Meta Ads', emoji: '📣' },
  { key: 'google_ads', label: 'Google Ads', emoji: '🔍' },
  { key: 'tiktok_ads', label: 'TikTok Ads', emoji: '📱' },
]

interface Policy {
  channel: string
  autonomy_mode: string
  content_auto_publish: boolean
  ads_auto_launch: boolean
  max_daily_posts: number
  max_daily_spend_usd: number
  reallocation_cap_pct: number
  approval_threshold_usd: number
  kill_switch: boolean
}

function defaultPolicy(channel: string): Policy {
  return {
    channel,
    autonomy_mode: 'manual',
    content_auto_publish: false,
    ads_auto_launch: false,
    max_daily_posts: 10,
    max_daily_spend_usd: 100,
    reallocation_cap_pct: 20,
    approval_threshold_usd: 50,
    kill_switch: false,
  }
}

export default function SettingsPage() {
  const [policies, setPolicies] = useState<Record<string, Policy>>(() => {
    const map: Record<string, Policy> = {}
    for (const ch of CHANNELS) map[ch.key] = defaultPolicy(ch.key)
    return map
  })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState<string | null>(null)
  const [killAllLoading, setKillAllLoading] = useState(false)
  const [message, setMessage] = useState('')

  const load = useCallback(async () => {
    try {
      const data = await apiFetch<{ policies: Policy[] }>('/api/v1/autonomy/policies')
      const map: Record<string, Policy> = {}
      for (const ch of CHANNELS) map[ch.key] = defaultPolicy(ch.key)
      for (const p of data.policies ?? []) {
        map[p.channel] = { ...defaultPolicy(p.channel), ...p }
      }
      setPolicies(map)
    } catch {
      // API unavailable — defaults already set in initial state, keep them
      setMessage('Could not reach backend — showing defaults')
      setTimeout(() => setMessage(''), 4000)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const updatePolicy = useCallback(async (channel: string, updates: Partial<Policy>) => {
    // Optimistically apply the change immediately so the UI responds on click
    setPolicies(prev => ({
      ...prev,
      [channel]: { ...prev[channel], ...updates },
    }))
    setSaving(channel)
    setMessage('')
    try {
      const updated = await apiFetch<Policy>(`/api/v1/autonomy/policies/${channel}`, {
        method: 'POST',
        body: JSON.stringify(updates),
      })
      // Reconcile with server response (may include fields we didn't send)
      setPolicies(prev => ({ ...prev, [channel]: { ...defaultPolicy(channel), ...updated } }))
      setMessage(`${channel} settings saved`)
      setTimeout(() => setMessage(''), 3000)
    } catch {
      // Revert optimistic update by reloading from server
      load()
      setMessage(`Failed to save ${channel}`)
    } finally {
      setSaving(null)
    }
  }, [load])

  const toggleKillSwitch = useCallback(async (channel: string, current: boolean) => {
    setSaving(channel)
    try {
      const updated = await apiFetch<Policy>(`/api/v1/autonomy/policies/${channel}/kill`, {
        method: 'POST',
        body: JSON.stringify({ enabled: !current }),
      })
      setPolicies(prev => ({ ...prev, [channel]: updated }))
    } catch {
      setMessage(`Failed to toggle kill switch for ${channel}`)
    } finally {
      setSaving(null)
    }
  }, [])

  const killAll = useCallback(async () => {
    setKillAllLoading(true)
    try {
      await apiFetch('/api/v1/autonomy/kill-all', { method: 'POST' })
      await load()
      setMessage('Emergency stop activated — all channels halted')
    } catch {
      setMessage('Failed to activate emergency stop')
    } finally {
      setKillAllLoading(false)
    }
  }, [load])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-6 h-6 border-2 border-black border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  const anyActive = Object.values(policies).some(p => !p.kill_switch && p.content_auto_publish)

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-black rounded-lg">
            <Shield className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-semibold">Autonomy Settings</h1>
            <p className="text-sm text-gray-500">Control what the AI can do on your behalf, per channel</p>
          </div>
        </div>

        {/* Emergency Stop */}
        <button
          onClick={killAll}
          disabled={killAllLoading}
          className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 disabled:opacity-50"
        >
          <AlertTriangle className="w-4 h-4" />
          {killAllLoading ? 'Stopping...' : 'Emergency Stop All'}
        </button>
      </div>

      {/* Message */}
      {message && (
        <div className={`flex items-center gap-2 p-3 rounded-lg text-sm ${
          message.includes('Failed') ? 'bg-red-50 text-red-700 border border-red-200' : 'bg-green-50 text-green-700 border border-green-200'
        }`}>
          {message.includes('Failed') ? <XCircle className="w-4 h-4" /> : <CheckCircle className="w-4 h-4" />}
          {message}
        </div>
      )}

      {/* Status Banner */}
      <div className={`flex items-center gap-3 p-4 rounded-xl border ${
        anyActive ? 'bg-green-50 border-green-200' : 'bg-gray-50 border-gray-200'
      }`}>
        <Zap className={`w-5 h-5 ${anyActive ? 'text-green-600' : 'text-gray-400'}`} />
        <div>
          <div className="text-sm font-medium">
            {anyActive ? 'Autonomous publishing is active' : 'All channels in manual mode'}
          </div>
          <div className="text-xs text-gray-500">
            {Object.values(policies).filter(p => !p.kill_switch && p.content_auto_publish).length} of {CHANNELS.length} channels on auto-publish
          </div>
        </div>
      </div>

      {/* Per-Channel Policies */}
      {CHANNELS.map(ch => {
        const policy = policies[ch.key]
        if (!policy) return null

        return (
          <div key={ch.key} className={`bg-white border rounded-xl overflow-hidden ${policy.kill_switch ? 'border-red-200' : 'border-gray-200'}`}>
            {/* Channel Header */}
            <div className={`flex items-center justify-between p-4 ${policy.kill_switch ? 'bg-red-50' : 'bg-gray-50'} border-b ${policy.kill_switch ? 'border-red-200' : 'border-gray-200'}`}>
              <div className="flex items-center gap-3">
                <span className="text-lg">{ch.emoji}</span>
                <div>
                  <div className="font-medium text-sm">{ch.label}</div>
                  <div className={`text-xs ${
                    policy.kill_switch ? 'text-red-600' : 'text-gray-500'
                  }`}>
                    {policy.kill_switch ? 'KILL SWITCH ACTIVE — no actions will run' : `Mode: ${policy.autonomy_mode}`}
                  </div>
                </div>
              </div>
              <button
                onClick={() => toggleKillSwitch(ch.key, policy.kill_switch)}
                disabled={saving === ch.key}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  policy.kill_switch
                    ? 'bg-red-600 text-white hover:bg-red-700'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                {policy.kill_switch ? <Lock className="w-3 h-3" /> : <Unlock className="w-3 h-3" />}
                {policy.kill_switch ? 'Halted' : 'Active'}
              </button>
            </div>

            {/* Policy Controls */}
            <div className="p-5 space-y-5">
              {/* Autonomy Mode */}
              <div>
                <label className="block text-xs text-gray-500 font-medium mb-2 uppercase tracking-wide">Autonomy Mode</label>
                <div className="grid grid-cols-4 gap-2">
                  {AUTONOMY_MODES.map(m => (
                    <button
                      key={m.value}
                      onClick={() => updatePolicy(ch.key, { autonomy_mode: m.value })}
                      disabled={saving === ch.key}
                      className={`p-2 rounded-lg border text-left transition-colors ${
                        policy.autonomy_mode === m.value
                          ? 'border-black bg-black text-white'
                          : 'border-gray-200 hover:border-gray-400'
                      }`}
                    >
                      <div className="text-xs font-medium">{m.label}</div>
                      <div className={`text-xs mt-0.5 ${policy.autonomy_mode === m.value ? 'text-gray-300' : 'text-gray-400'}`}>{m.desc}</div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Toggles */}
              <div className="flex gap-6">
                <Toggle
                  label="Auto-Publish Content"
                  checked={policy.content_auto_publish}
                  onChange={v => updatePolicy(ch.key, { content_auto_publish: v })}
                  disabled={saving === ch.key || policy.kill_switch}
                />
                <Toggle
                  label="Auto-Launch Ads"
                  checked={policy.ads_auto_launch}
                  onChange={v => updatePolicy(ch.key, { ads_auto_launch: v })}
                  disabled={saving === ch.key || policy.kill_switch}
                />
              </div>

              {/* Numeric Limits */}
              <div className="grid grid-cols-2 gap-4">
                <NumberField
                  label="Max Daily Posts"
                  value={policy.max_daily_posts}
                  min={1}
                  max={50}
                  onChange={v => updatePolicy(ch.key, { max_daily_posts: v })}
                  disabled={saving === ch.key}
                />
                <NumberField
                  label="Max Daily Spend (USD)"
                  value={policy.max_daily_spend_usd}
                  min={0}
                  max={10000}
                  prefix="$"
                  onChange={v => updatePolicy(ch.key, { max_daily_spend_usd: v })}
                  disabled={saving === ch.key}
                />
                <NumberField
                  label="Approval Threshold (USD)"
                  value={policy.approval_threshold_usd}
                  min={0}
                  max={10000}
                  prefix="$"
                  onChange={v => updatePolicy(ch.key, { approval_threshold_usd: v })}
                  disabled={saving === ch.key}
                  hint="Spend above this requires your approval"
                />
                <NumberField
                  label="Reallocation Cap (%)"
                  value={policy.reallocation_cap_pct}
                  min={0}
                  max={100}
                  suffix="%"
                  onChange={v => updatePolicy(ch.key, { reallocation_cap_pct: v })}
                  disabled={saving === ch.key}
                  hint="Max budget shift between ad sets"
                />
              </div>

              {saving === ch.key && (
                <div className="text-xs text-gray-500 flex items-center gap-1">
                  <div className="w-3 h-3 border border-gray-400 border-t-transparent rounded-full animate-spin" />
                  Saving...
                </div>
              )}
            </div>
          </div>
        )
      })}

      {/* Safety Note */}
      <div className="flex items-start gap-3 p-4 bg-amber-50 border border-amber-200 rounded-xl text-sm text-amber-800">
        <DollarSign className="w-4 h-4 flex-shrink-0 mt-0.5" />
        <div>
          <strong>Spend protection:</strong> All ad actions above your approval threshold require manual sign-off regardless of autonomy mode.
          The emergency stop instantly halts all scheduled and background actions across every channel.
        </div>
      </div>
    </div>
  )
}

function Toggle({
  label,
  checked,
  onChange,
  disabled,
}: {
  label: string
  checked: boolean
  onChange: (v: boolean) => void
  disabled?: boolean
}) {
  return (
    <button
      onClick={() => !disabled && onChange(!checked)}
      disabled={disabled}
      className="flex items-center gap-2 text-sm disabled:opacity-50"
    >
      {checked ? (
        <ToggleRight className="w-8 h-5 text-green-600" />
      ) : (
        <ToggleLeft className="w-8 h-5 text-gray-400" />
      )}
      <span className={checked ? 'text-gray-900' : 'text-gray-500'}>{label}</span>
    </button>
  )
}

function NumberField({
  label,
  value,
  min,
  max,
  prefix,
  suffix,
  hint,
  onChange,
  disabled,
}: {
  label: string
  value: number
  min: number
  max: number
  prefix?: string
  suffix?: string
  hint?: string
  onChange: (v: number) => void
  disabled?: boolean
}) {
  const [local, setLocal] = useState(String(value))

  useEffect(() => { setLocal(String(value)) }, [value])

  return (
    <div>
      <label className="block text-xs text-gray-500 mb-1">{label}</label>
      <div className="flex items-center border border-gray-200 rounded-lg overflow-hidden focus-within:ring-2 focus-within:ring-black">
        {prefix && <span className="px-2 text-gray-400 text-sm bg-gray-50">{prefix}</span>}
        <input
          type="number"
          value={local}
          min={min}
          max={max}
          disabled={disabled}
          onChange={e => setLocal(e.target.value)}
          onBlur={() => {
            const n = Number(local)
            if (!isNaN(n) && n >= min && n <= max) onChange(n)
            else setLocal(String(value))
          }}
          className="flex-1 px-3 py-2 text-sm focus:outline-none disabled:bg-gray-50 disabled:text-gray-400"
        />
        {suffix && <span className="px-2 text-gray-400 text-sm bg-gray-50">{suffix}</span>}
      </div>
      {hint && <p className="text-xs text-gray-400 mt-1">{hint}</p>}
    </div>
  )
}

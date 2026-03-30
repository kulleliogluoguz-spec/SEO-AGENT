'use client'

import { useEffect, useState, useCallback } from 'react'
import { apiFetch } from '@/lib/apiFetch'

export type ChannelStatus = 'connected' | 'disconnected' | 'error' | 'loading'

export interface ConnectionHealth {
  x: ChannelStatus
  instagram: ChannelStatus
  meta_ads: ChannelStatus
  google_ads: ChannelStatus
}

export interface ConnectionHealthResult {
  health: ConnectionHealth
  loading: boolean
  refresh: () => void
}

const DEFAULT_HEALTH: ConnectionHealth = {
  x: 'loading',
  instagram: 'loading',
  meta_ads: 'loading',
  google_ads: 'loading',
}

export function useConnectionHealth(): ConnectionHealthResult {
  const [health, setHealth] = useState<ConnectionHealth>(DEFAULT_HEALTH)
  const [loading, setLoading] = useState(true)

  const fetch = useCallback(async () => {
    setLoading(true)
    try {
      const data = await apiFetch<{ channels: Record<string, { connected: boolean }> }>(
        '/api/v1/connectors/status'
      )
      setHealth({
        x: data.channels?.x?.connected ? 'connected' : 'disconnected',
        instagram: data.channels?.instagram?.connected ? 'connected' : 'disconnected',
        meta_ads: data.channels?.meta_ads?.connected ? 'connected' : 'disconnected',
        google_ads: data.channels?.google_ads?.connected ? 'connected' : 'disconnected',
      })
    } catch {
      setHealth({
        x: 'error',
        instagram: 'error',
        meta_ads: 'error',
        google_ads: 'error',
      })
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetch()
  }, [fetch])

  return { health, loading, refresh: fetch }
}

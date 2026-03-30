'use client'

import { useMemo } from 'react'
import { useConnectionHealth, ConnectionHealth } from './useConnectionHealth'

export interface FeatureReadiness {
  canGrowX: boolean
  canGrowInstagram: boolean
  canRunMetaAds: boolean
  canRunGoogleAds: boolean
  canPromoteSite: boolean
  anyConnected: boolean
}

function computeReadiness(health: ConnectionHealth): FeatureReadiness {
  const canGrowX = health.x === 'connected'
  const canGrowInstagram = health.instagram === 'connected'
  const canRunMetaAds = health.meta_ads === 'connected'
  const canRunGoogleAds = health.google_ads === 'connected'
  const canPromoteSite = canRunMetaAds || canRunGoogleAds
  const anyConnected = canGrowX || canGrowInstagram || canRunMetaAds || canRunGoogleAds

  return { canGrowX, canGrowInstagram, canRunMetaAds, canRunGoogleAds, canPromoteSite, anyConnected }
}

export function useFeatureReadiness() {
  const { health, loading, refresh } = useConnectionHealth()
  const readiness = useMemo(() => computeReadiness(health), [health])
  return { readiness, loading, refresh }
}

'use client'

import { useEffect, useRef, useState } from 'react'
import { Mic, MicOff, Phone, PhoneOff } from 'lucide-react'
import { apiFetch } from '@/lib/apiFetch'

type CallStatus = 'idle' | 'connecting' | 'connected' | 'ended'

interface BrowserCallerProps {
  contactId?: string
  contactName?: string
  onCallEnd?: (callId: string) => void
}

type TokenResponse = {
  call_id: string
  room_name: string
  token: string | null
  livekit_url: string
  configured?: boolean
  message?: string
}

export default function BrowserCaller({
  contactId,
  contactName,
  onCallEnd,
}: BrowserCallerProps) {
  const [status, setStatus] = useState<CallStatus>('idle')
  const [muted, setMuted] = useState(false)
  const [callId, setCallId] = useState<string | null>(null)
  const [duration, setDuration] = useState(0)
  const [error, setError] = useState<string | null>(null)
  // roomRef is `unknown` so we can import livekit-client lazily; callers
  // don't need to know the concrete Room type.
  const roomRef = useRef<unknown>(null)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [])

  async function startCall() {
    setError(null)
    setStatus('connecting')
    try {
      const data = await apiFetch<TokenResponse>('/api/v1/calls/livekit/token', {
        method: 'POST',
        body: JSON.stringify({ contact_id: contactId, identity: 'agent' }),
      })
      if (!data.token) {
        setError(data.message ?? 'LiveKit not configured')
        setStatus('idle')
        return
      }
      setCallId(data.call_id)

      // Lazy import — livekit-client is an optional peer dep. The variable
      // module name keeps tsc happy when the package is not installed.
      // At runtime the dynamic import either resolves or throws, and we
      // show a friendly "not installed" message on failure.
      const moduleName = 'livekit-client'
      const livekit = await import(/* webpackIgnore: true */ moduleName).catch(
        () => null,
      )
      if (!livekit) {
        setError('livekit-client is not installed. Run: npm install livekit-client')
        setStatus('idle')
        return
      }

      const { Room, RoomEvent } = livekit as {
        Room: new () => {
          on: (evt: string, cb: () => void) => void
          connect: (url: string, token: string) => Promise<void>
          disconnect: () => Promise<void>
          localParticipant: {
            setMicrophoneEnabled: (on: boolean) => Promise<void>
          }
        }
        RoomEvent: { Connected: string; Disconnected: string }
      }
      const room = new Room()
      roomRef.current = room

      room.on(RoomEvent.Connected, () => {
        setStatus('connected')
        timerRef.current = setInterval(() => setDuration((d) => d + 1), 1000)
      })
      room.on(RoomEvent.Disconnected, () => {
        setStatus('ended')
        if (timerRef.current) clearInterval(timerRef.current)
        if (data.call_id) onCallEnd?.(data.call_id)
      })

      await room.connect(data.livekit_url, data.token)
      await room.localParticipant.setMicrophoneEnabled(true)
    } catch (e) {
      console.error('Call failed:', e)
      setError(e instanceof Error ? e.message : 'Call failed')
      setStatus('idle')
    }
  }

  async function endCall() {
    const room = roomRef.current as {
      disconnect?: () => Promise<void>
    } | null
    if (room?.disconnect) {
      try {
        await room.disconnect()
      } catch {
        /* noop */
      }
    }
    setStatus('ended')
    if (timerRef.current) clearInterval(timerRef.current)
    if (callId) onCallEnd?.(callId)
  }

  function toggleMute() {
    const room = roomRef.current as {
      localParticipant?: {
        setMicrophoneEnabled: (on: boolean) => Promise<void>
      }
    } | null
    if (!room?.localParticipant) return
    const enabled = muted // flipping: currently muted → turn on
    room.localParticipant.setMicrophoneEnabled(enabled).catch(() => {
      /* noop */
    })
    setMuted(!enabled)
  }

  const formatDuration = (s: number) =>
    `${Math.floor(s / 60)
      .toString()
      .padStart(2, '0')}:${(s % 60).toString().padStart(2, '0')}`

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <div>
          <div className="font-medium text-slate-800">
            {contactName || 'Browser Call'}
          </div>
          {status === 'connected' && (
            <div className="text-sm text-emerald-600 font-mono">
              {formatDuration(duration)}
            </div>
          )}
          {status === 'connecting' && (
            <div className="text-sm text-amber-600 animate-pulse">Connecting…</div>
          )}
          {status === 'ended' && (
            <div className="text-sm text-slate-500">
              Call ended. Processing transcript…
            </div>
          )}
        </div>
        <div className="flex gap-2">
          {status === 'connected' && (
            <button
              onClick={toggleMute}
              className={`p-2 rounded-full ${
                muted
                  ? 'bg-red-100 text-red-600'
                  : 'bg-slate-100 text-slate-600'
              }`}
            >
              {muted ? (
                <MicOff className="w-4 h-4" />
              ) : (
                <Mic className="w-4 h-4" />
              )}
            </button>
          )}
          {status === 'idle' && (
            <button
              onClick={startCall}
              className="flex items-center gap-2 bg-emerald-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-emerald-700"
            >
              <Phone className="w-4 h-4" /> Start Call
            </button>
          )}
          {(status === 'connecting' || status === 'connected') && (
            <button
              onClick={endCall}
              className="flex items-center gap-2 bg-red-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-red-700"
            >
              <PhoneOff className="w-4 h-4" /> End Call
            </button>
          )}
        </div>
      </div>
      {status === 'idle' && !error && (
        <p className="text-xs text-slate-400">
          This call will be recorded. The other party will be notified.
        </p>
      )}
      {error && (
        <p className="text-xs text-red-500 mt-1">{error}</p>
      )}
    </div>
  )
}

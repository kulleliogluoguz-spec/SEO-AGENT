'use client'

import { AlertCircle, RefreshCw } from 'lucide-react'

export default function TrendsError({
  error,
  reset,
}: {
  error: Error
  reset: () => void
}) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[400px] gap-5 text-center">
      <div className="w-14 h-14 bg-red-50 rounded-2xl flex items-center justify-center">
        <AlertCircle size={24} className="text-red-500" />
      </div>
      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-1">Trend Feed failed to load</h2>
        <p className="text-sm text-gray-500 max-w-sm">
          {error.message || 'An unexpected error occurred while loading the trend feed.'}
        </p>
      </div>
      <button
        onClick={reset}
        className="flex items-center gap-2 px-4 py-2.5 bg-gray-900 text-white rounded-xl text-sm font-semibold hover:bg-gray-700 transition-colors"
      >
        <RefreshCw size={13} /> Try again
      </button>
    </div>
  )
}

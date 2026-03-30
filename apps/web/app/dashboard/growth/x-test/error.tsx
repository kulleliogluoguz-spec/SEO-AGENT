'use client'

export default function XTestError({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center h-64 gap-4 text-center">
      <p className="text-sm text-red-600 font-medium">Failed to load X dashboard</p>
      <p className="text-xs text-gray-400">{error.message}</p>
      <button
        onClick={reset}
        className="text-xs text-brand-600 underline hover:text-brand-800"
      >
        Try again
      </button>
    </div>
  )
}

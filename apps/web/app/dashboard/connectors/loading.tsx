import { Loader2 } from 'lucide-react'

export default function ConnectionsLoading() {
  return (
    <div className="space-y-8">
      {/* Header skeleton */}
      <div className="flex items-center justify-between">
        <div>
          <div className="h-7 w-40 bg-gray-100 rounded-lg animate-pulse mb-2" />
          <div className="h-4 w-64 bg-gray-100 rounded animate-pulse" />
        </div>
        <div className="h-8 w-28 bg-gray-100 rounded-lg animate-pulse" />
      </div>

      {/* Social accounts skeleton */}
      <div>
        <div className="h-5 w-36 bg-gray-100 rounded animate-pulse mb-4" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[0, 1].map(i => (
            <div key={i} className="card p-5">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-gray-100 animate-pulse" />
                  <div>
                    <div className="h-4 w-24 bg-gray-100 rounded animate-pulse mb-1" />
                    <div className="h-3 w-32 bg-gray-100 rounded animate-pulse" />
                  </div>
                </div>
                <div className="h-6 w-24 bg-gray-100 rounded-full animate-pulse" />
              </div>
              <div className="h-3 w-full bg-gray-100 rounded animate-pulse mb-1" />
              <div className="h-3 w-3/4 bg-gray-100 rounded animate-pulse mb-4" />
              <div className="h-10 w-full bg-gray-100 rounded-xl animate-pulse" />
            </div>
          ))}
        </div>
      </div>

      {/* Ad accounts skeleton */}
      <div>
        <div className="h-5 w-28 bg-gray-100 rounded animate-pulse mb-4" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[0, 1].map(i => (
            <div key={i} className="card p-5">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-xl bg-gray-100 animate-pulse" />
                <div>
                  <div className="h-4 w-20 bg-gray-100 rounded animate-pulse mb-1" />
                  <div className="h-3 w-36 bg-gray-100 rounded animate-pulse" />
                </div>
              </div>
              <div className="h-10 w-full bg-gray-100 rounded-xl animate-pulse" />
            </div>
          ))}
        </div>
      </div>

      {/* Loading indicator */}
      <div className="flex items-center justify-center gap-2 py-4 text-gray-400">
        <Loader2 size={14} className="animate-spin" />
        <span className="text-sm">Loading connections…</span>
      </div>
    </div>
  )
}

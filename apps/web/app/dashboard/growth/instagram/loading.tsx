import { Loader2 } from 'lucide-react'

export default function InstagramLoading() {
  return (
    <div className="flex items-center justify-center h-64">
      <div className="text-center">
        <Loader2 className="w-7 h-7 animate-spin text-gray-400 mx-auto mb-3" />
        <p className="text-sm text-gray-400">Loading Instagram dashboard…</p>
      </div>
    </div>
  )
}

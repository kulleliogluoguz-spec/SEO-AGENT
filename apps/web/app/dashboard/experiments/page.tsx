'use client'
import { FlaskConical } from 'lucide-react'

export default function ExperimentsPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-gray-900">Experiments</h1>
      <p className="text-sm text-gray-500">Design and track A/B experiments for content, headlines, and CTAs.</p>
      <div className="card p-12 text-center">
        <FlaskConical size={36} className="mx-auto text-gray-300 mb-3" />
        <h3 className="font-medium text-gray-700 mb-1">Experiments Coming in v0.2</h3>
        <p className="text-sm text-gray-400 max-w-sm mx-auto">
          Hypothesis generation, variant creation, success metrics, and experiment lifecycle tracking.
          See the roadmap for details.
        </p>
      </div>
    </div>
  )
}

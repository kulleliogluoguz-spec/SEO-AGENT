'use client'
import { Zap, Info, CheckCircle, AlertCircle, Clock } from 'lucide-react'

const GEO_SIGNALS = [
  { label: 'Citation Readiness', score: 45, status: 'needs_work', notes: 'Add more structured FAQ content and clear attributable claims' },
  { label: 'Answer Surface Coverage', score: 30, status: 'poor', notes: 'Missing Q&A pages for key product queries' },
  { label: 'Entity Consistency', score: 70, status: 'good', notes: 'Brand name and description are consistent across main pages' },
  { label: 'Use Case Page Coverage', score: 50, status: 'needs_work', notes: 'Add dedicated use case pages per ICP' },
  { label: 'Comparison Page Coverage', score: 20, status: 'poor', notes: 'No vs-competitor pages found' },
  { label: 'FAQ Completeness', score: 35, status: 'needs_work', notes: 'FAQ content is minimal or absent' },
]

const STATUS_ICON: Record<string, React.ReactNode> = {
  good: <CheckCircle size={14} className="text-green-500" />,
  needs_work: <Clock size={14} className="text-yellow-500" />,
  poor: <AlertCircle size={14} className="text-red-400" />,
}

function ScoreBar({ score }: { score: number }) {
  const color = score >= 70 ? 'bg-green-400' : score >= 50 ? 'bg-yellow-400' : 'bg-red-400'
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all`} style={{ width: `${score}%` }} />
      </div>
      <span className="text-sm font-medium text-gray-700 w-8 text-right">{score}</span>
    </div>
  )
}

export default function GEOPage() {
  const avgScore = Math.round(GEO_SIGNALS.reduce((a, b) => a + b.score, 0) / GEO_SIGNALS.length)
  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
          AI Visibility Analysis
          <span className="badge-blue text-xs">Experimental</span>
        </h1>
        <p className="text-sm text-gray-500">How discoverable is your brand to AI assistants and LLMs?</p>
      </div>

      <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 flex gap-3">
        <Info size={16} className="text-amber-600 flex-shrink-0 mt-0.5" />
        <p className="text-sm text-amber-800">
          <strong>Experimental module.</strong> GEO/AEO measurement surfaces are still emerging. These signals
          are inferred from site content and structure — not from live AI engine measurements. Treat as directional guidance.
        </p>
      </div>

      {/* Overall score */}
      <div className="card p-6">
        <div className="flex items-center gap-6">
          <div className="text-center">
            <div className={`text-5xl font-bold ${avgScore >= 70 ? 'text-green-600' : avgScore >= 50 ? 'text-yellow-500' : 'text-red-500'}`}>
              {avgScore}
            </div>
            <div className="text-xs text-gray-400 mt-1">AI Visibility Score</div>
            <div className="text-xs text-gray-400">out of 100</div>
          </div>
          <div className="flex-1">
            <p className="text-sm text-gray-600">
              Your site has <strong>significant room for improvement</strong> in AI answer surface optimization.
              Focus on structured FAQ content, use-case pages, and comparison pages to improve citation likelihood.
            </p>
          </div>
        </div>
      </div>

      {/* Signal breakdown */}
      <div className="card p-5">
        <h2 className="font-semibold text-gray-900 mb-4">Signal Breakdown</h2>
        <div className="space-y-4">
          {GEO_SIGNALS.map(signal => (
            <div key={signal.label}>
              <div className="flex items-center gap-2 mb-1">
                {STATUS_ICON[signal.status]}
                <span className="text-sm font-medium text-gray-800">{signal.label}</span>
              </div>
              <ScoreBar score={signal.score} />
              <p className="text-xs text-gray-400 mt-1 ml-5">{signal.notes}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

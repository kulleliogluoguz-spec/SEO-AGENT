'use client'
import { Activity, Clock } from 'lucide-react'

const DEMO_EVENTS = [
  { action: 'site.onboarded', entity: 'example-saas.com', time: '2h ago', icon: '🌐' },
  { action: 'crawl.completed', entity: '6 pages crawled', time: '2h ago', icon: '🔍' },
  { action: 'recommendations.generated', entity: '4 recommendations', time: '2h ago', icon: '💡' },
  { action: 'report.generated', entity: 'Weekly report', time: '1h ago', icon: '📊' },
]

export default function ActivityPage() {
  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-bold text-gray-900">Activity Log</h1>
        <p className="text-sm text-gray-500">Audit trail of all agent actions, approvals, and system events.</p>
      </div>
      <div className="card divide-y divide-gray-100">
        {DEMO_EVENTS.map((event, i) => (
          <div key={i} className="flex items-center gap-4 p-4">
            <span className="text-xl">{event.icon}</span>
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-900">{event.action}</p>
              <p className="text-xs text-gray-400">{event.entity}</p>
            </div>
            <div className="flex items-center gap-1 text-xs text-gray-400">
              <Clock size={11} />
              {event.time}
            </div>
          </div>
        ))}
      </div>
      <p className="text-xs text-gray-400 text-center">
        Showing seeded demo events. Live activity log requires database connection.
      </p>
    </div>
  )
}

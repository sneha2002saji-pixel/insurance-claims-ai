import type { ClaimStatus } from '@insurance/shared-types'
import { STATUS_LABELS } from '@insurance/shared-types'

const TERMINAL_STATUSES = new Set<ClaimStatus>([
  'agent_approved',
  'rejected',
  'partial_settlement',
  'settled',
])

interface StatusTimelineProps {
  currentStatus: ClaimStatus
  updatedAt: string
}

export function StatusTimeline({ currentStatus, updatedAt }: StatusTimelineProps) {
  // Build a linear flow: pending → under_review → currentStatus (if not already included)
  const activeFlow: ClaimStatus[] = ['pending', 'under_review']
  if (!activeFlow.includes(currentStatus)) {
    activeFlow.push(currentStatus)
  }

  const formattedTime = new Date(updatedAt).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })

  const currentIndex = activeFlow.indexOf(currentStatus)

  return (
    <div className="space-y-1">
      {activeFlow.map((status, idx) => {
        const isActive = status === currentStatus
        const isPast = idx < currentIndex
        const isTerminal = TERMINAL_STATUSES.has(status)
        const isLast = idx === activeFlow.length - 1

        let dotClasses: string
        if (isActive) {
          if (isTerminal && status === 'rejected') {
            dotClasses = 'border-red-400 bg-red-400'
          } else if (isTerminal) {
            dotClasses = 'border-green-400 bg-green-400'
          } else {
            dotClasses = 'border-blue-400 bg-blue-400'
          }
        } else if (isPast) {
          dotClasses = 'border-slate-500 bg-slate-500'
        } else {
          dotClasses = 'border-slate-600 bg-transparent'
        }

        return (
          <div key={status} className="flex items-center gap-3">
            <div className="flex flex-col items-center">
              <div
                className={`w-3 h-3 rounded-full border-2 transition-colors ${dotClasses}`}
              />
              {!isLast && (
                <div
                  className={`w-0.5 h-4 ${isPast || isActive ? 'bg-slate-600' : 'bg-slate-700'}`}
                />
              )}
            </div>
            <div className="pb-4">
              <span
                className={`text-sm font-medium ${isActive ? 'text-white' : 'text-slate-400'}`}
              >
                {STATUS_LABELS[status]}
              </span>
              {isActive && (
                <p className="text-slate-500 text-xs mt-0.5">{formattedTime}</p>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}

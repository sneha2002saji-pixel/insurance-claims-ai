interface FraudBadgeProps {
  /** Fraud risk score in the range 0.0–1.0 */
  score: number
  showBar?: boolean
}

export function FraudBadge({ score, showBar = true }: FraudBadgeProps) {
  const pct = Math.round(score * 100)

  const color =
    score >= 0.7 ? 'text-red-400' : score >= 0.4 ? 'text-yellow-400' : 'text-green-400'

  const barColor =
    score >= 0.7 ? 'bg-red-500' : score >= 0.4 ? 'bg-yellow-500' : 'bg-green-500'

  const label =
    score >= 0.7 ? 'High Risk' : score >= 0.4 ? 'Medium Risk' : 'Low Risk'

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <span className="text-slate-400 text-sm">Fraud Risk</span>
        <span className={`font-bold text-sm ${color}`}>
          {pct}% &middot; {label}
        </span>
      </div>
      {showBar && (
        <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${barColor}`}
            style={{ width: `${pct}%` }}
          />
        </div>
      )}
    </div>
  )
}

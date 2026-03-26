'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import type { HumanDecision, InsuranceClaim } from '@insurance/shared-types'

interface HitlReviewClientProps {
  claim: InsuranceClaim
}

const DECISION_OPTIONS: { value: HumanDecision; label: string; description: string }[] = [
  {
    value: 'approved',
    label: 'Approve',
    description: 'Approve the claim for full payment',
  },
  {
    value: 'partial_settlement',
    label: 'Partial Settlement',
    description: 'Approve for a reduced settlement amount',
  },
  {
    value: 'rejected',
    label: 'Reject',
    description: 'Deny the claim',
  },
]

interface ApproveResponse {
  claim_id: string
  new_status: string
  decision: string
}

interface ApiErrorBody {
  error?: { message?: string }
  detail?: string
}

export function HitlReviewClient({ claim }: HitlReviewClientProps) {
  const router = useRouter()
  const [decision, setDecision] = useState<HumanDecision | null>(null)
  const [comment, setComment] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const formattedAmount = new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(claim.amount)

  const escalationReason =
    claim.amount > 10000 && 'Claim amount exceeds $10,000 automatic threshold'

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    if (!decision) return
    setLoading(true)
    setError(null)

    try {
      const res = await fetch(`/api/claims/${claim.id}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ decision, comment }),
      })
      // Read body once, then branch on status
      const body: unknown = await res.json()
      if (!res.ok) {
        const errBody = body as ApiErrorBody
        const msg = errBody.error?.message ?? errBody.detail ?? 'Failed to submit decision'
        throw new Error(msg)
      }
      const data = body as ApproveResponse
      router.push(`/claims/${data.claim_id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unexpected error occurred')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Left: Claim summary */}
      <div className="space-y-4">
        <div className="bg-slate-800/50 border border-slate-700 rounded-2xl p-5">
          <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-4">
            Claim Summary
          </h2>
          <dl className="space-y-3">
            <div>
              <dt className="text-xs text-slate-500">Claimant</dt>
              <dd className="text-white font-medium mt-0.5">{claim.claimant_name}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">Policy Number</dt>
              <dd className="text-white font-mono text-sm mt-0.5">{claim.policy_number}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">Type</dt>
              <dd className="text-white mt-0.5">{claim.claim_type}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">Claim Amount</dt>
              <dd className="text-2xl font-bold text-white mt-0.5">{formattedAmount}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">Description</dt>
              <dd className="text-slate-300 text-sm mt-0.5 leading-relaxed">
                {claim.incident_description}
              </dd>
            </div>
          </dl>
        </div>

        {/* Escalation reason */}
        {escalationReason && (
          <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-2xl p-4">
            <p className="text-xs text-yellow-400 font-semibold uppercase tracking-wide mb-1">
              Escalation Reason
            </p>
            <p className="text-slate-200 text-sm">{escalationReason}</p>
          </div>
        )}
      </div>

      {/* Right: Decision form */}
      <div>
        <form onSubmit={e => void handleSubmit(e)} className="space-y-5">
          <div className="bg-slate-800/50 border border-slate-700 rounded-2xl p-5">
            <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-4">
              Adjuster Decision
            </h2>

            {error && (
              <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-3 text-red-400 text-sm mb-4">
                {error}
              </div>
            )}

            {/* Decision options */}
            <div className="space-y-3 mb-5">
              {DECISION_OPTIONS.map(opt => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => setDecision(opt.value)}
                  className={`w-full p-4 rounded-xl border text-left transition-all ${
                    decision === opt.value
                      ? opt.value === 'rejected'
                        ? 'border-red-500 bg-red-500/10'
                        : opt.value === 'approved'
                          ? 'border-green-500 bg-green-500/10'
                          : 'border-purple-500 bg-purple-500/10'
                      : 'border-slate-700 bg-slate-800/50 hover:border-slate-500'
                  }`}
                >
                  <div
                    className={`font-semibold text-sm ${
                      decision === opt.value
                        ? opt.value === 'rejected'
                          ? 'text-red-400'
                          : opt.value === 'approved'
                            ? 'text-green-400'
                            : 'text-purple-400'
                        : 'text-white'
                    }`}
                  >
                    {opt.label}
                  </div>
                  <div className="text-xs text-slate-400 mt-0.5">{opt.description}</div>
                </button>
              ))}
            </div>

            {/* Comment */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1.5">
                Adjuster Comment <span className="text-slate-500">(required)</span>
              </label>
              <textarea
                required
                rows={4}
                value={comment}
                onChange={e => setComment(e.target.value)}
                placeholder="Provide a brief explanation for your decision..."
                className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors resize-none"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading || !decision || comment.trim().length === 0}
            className="w-full bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 disabled:text-slate-500 text-white font-semibold py-3 rounded-xl transition-colors"
          >
            {loading ? 'Submitting\u2026' : 'Submit Decision'}
          </button>
        </form>
      </div>
    </div>
  )
}

'use client'

import Link from 'next/link'
import type { InsuranceClaim, ClaimType, ClaimStatus } from '@insurance/shared-types'
import { STATUS_LABELS } from '@insurance/shared-types'

const TYPE_BADGE_CLASSES: Record<ClaimType, string> = {
  AUTO: 'bg-blue-500/20 text-blue-400 border border-blue-500/30',
  HEALTH: 'bg-green-500/20 text-green-400 border border-green-500/30',
  PROPERTY: 'bg-orange-500/20 text-orange-400 border border-orange-500/30',
}

const STATUS_BADGE_CLASSES: Record<ClaimStatus, string> = {
  pending: 'bg-slate-500/20 text-slate-400',
  under_review: 'bg-blue-500/20 text-blue-400',
  agent_approved: 'bg-green-500/20 text-green-400',
  awaiting_human_approval: 'bg-yellow-500/20 text-yellow-400',
  rejected: 'bg-red-500/20 text-red-400',
  partial_settlement: 'bg-purple-500/20 text-purple-400',
  settled: 'bg-emerald-500/20 text-emerald-400',
}

interface ClaimCardProps {
  claim: InsuranceClaim
}

export function ClaimCard({ claim }: ClaimCardProps) {
  const formattedAmount = new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(claim.amount)

  const formattedDate = new Date(claim.created_at).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })

  return (
    <Link href={`/claims/${claim.id}`}>
      <div className="group bg-slate-800/50 border border-slate-700 rounded-xl p-5 hover:border-slate-500 hover:bg-slate-800 transition-all duration-200 cursor-pointer">
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-2">
            <span
              className={`px-2 py-0.5 rounded-full text-xs font-semibold ${TYPE_BADGE_CLASSES[claim.claim_type]}`}
            >
              {claim.claim_type}
            </span>
            <span className="text-slate-500 text-xs font-mono">
              {claim.id.slice(0, 8)}&hellip;
            </span>
          </div>
          <span
            className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_BADGE_CLASSES[claim.status]}`}
          >
            {STATUS_LABELS[claim.status]}
          </span>
        </div>

        <div className="mb-3">
          <p className="text-white font-semibold text-base group-hover:text-blue-400 transition-colors">
            {claim.claimant_name}
          </p>
          <p className="text-slate-400 text-sm">{claim.policy_number}</p>
        </div>

        <div className="flex items-center justify-between">
          <span className="text-2xl font-bold text-white">{formattedAmount}</span>
          <span className="text-slate-500 text-xs">{formattedDate}</span>
        </div>
      </div>
    </Link>
  )
}

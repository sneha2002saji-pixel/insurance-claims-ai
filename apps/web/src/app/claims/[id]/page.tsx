import { notFound } from 'next/navigation'
import Link from 'next/link'
import type { InsuranceClaim, ClaimStatus } from '@insurance/shared-types'
import { STATUS_LABELS } from '@insurance/shared-types'
import { ClaimDetailClient } from './ClaimDetailClient'

const STATUS_BADGE_CLASSES: Record<ClaimStatus, string> = {
  pending: 'bg-slate-500/20 text-slate-400',
  under_review: 'bg-blue-500/20 text-blue-400',
  agent_approved: 'bg-green-500/20 text-green-400',
  awaiting_human_approval: 'bg-yellow-500/20 text-yellow-400',
  rejected: 'bg-red-500/20 text-red-400',
  partial_settlement: 'bg-purple-500/20 text-purple-400',
  settled: 'bg-emerald-500/20 text-emerald-400',
}

async function getClaim(id: string): Promise<InsuranceClaim | null> {
  const baseUrl =
    process.env.AGENT_SERVICE_URL_INTERNAL ??
    process.env.AGENT_SERVICE_URL ??
    'http://localhost:8000'
  try {
    const res = await fetch(`${baseUrl}/claims/${id}`, { cache: 'no-store' })
    if (!res.ok) return null
    return (await res.json()) as InsuranceClaim
  } catch {
    return null
  }
}

interface PageProps {
  params: Promise<{ id: string }>
}

export default async function ClaimDetailPage({ params }: PageProps) {
  const { id } = await params
  const claim = await getClaim(id)
  if (!claim) notFound()

  return (
    <div className="flex flex-col min-h-screen bg-slate-900">
      {/* Top nav */}
      <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-7 h-7 rounded-lg bg-blue-600 flex items-center justify-center text-white text-xs font-bold">
              AI
            </div>
            <span className="font-semibold text-white text-sm">Insurance Claims AI</span>
          </div>
          <nav className="flex items-center gap-6 text-sm">
            <Link href="/" className="text-slate-400 hover:text-white transition-colors">
              Dashboard
            </Link>
            <Link href="/claims/new" className="text-slate-400 hover:text-white transition-colors">
              New Claim
            </Link>
          </nav>
        </div>
      </header>

      <main className="flex-1 max-w-6xl mx-auto w-full px-6 py-8">
        {/* Breadcrumb + title */}
        <div className="mb-6">
          <div className="flex items-center gap-2 text-sm text-slate-500 mb-2">
            <Link href="/" className="hover:text-slate-300 transition-colors">
              Dashboard
            </Link>
            <span>/</span>
            <span className="text-slate-300">
              {claim.claimant_name} &mdash; {claim.claim_type}
            </span>
          </div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-white">{claim.claimant_name}</h1>
            <span
              className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${STATUS_BADGE_CLASSES[claim.status]}`}
            >
              {STATUS_LABELS[claim.status]}
            </span>
          </div>
          <p className="text-slate-500 text-sm font-mono mt-1">{claim.id}</p>
        </div>

        <ClaimDetailClient claim={claim} />
      </main>
    </div>
  )
}

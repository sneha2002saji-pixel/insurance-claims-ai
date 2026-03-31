import { notFound, redirect } from 'next/navigation'
import Link from 'next/link'
import type { InsuranceClaim } from '@insurance/shared-types'
import { HitlReviewClient } from './HitlReviewClient'
import { getIdentityToken } from '@/lib/gcp-auth'

async function getClaim(id: string): Promise<InsuranceClaim | null> {
  const baseUrl =
    process.env.AGENT_SERVICE_URL_INTERNAL ??
    process.env.AGENT_SERVICE_URL ??
    'http://localhost:8000'
  // Use the public URL as the identity token audience (Cloud Run requires the service URL)
  const audience = process.env.AGENT_SERVICE_URL ?? baseUrl
  const token = await getIdentityToken(audience)
  const headers: Record<string, string> = {}
  if (token) headers['Authorization'] = `Bearer ${token}`
  try {
    const res = await fetch(`${baseUrl}/claims/${id}`, { cache: 'no-store', headers })
    if (!res.ok) return null
    return (await res.json()) as InsuranceClaim
  } catch {
    return null
  }
}

interface PageProps {
  params: Promise<{ id: string }>
}

export default async function HitlReviewPage({ params }: PageProps) {
  const { id } = await params
  const claim = await getClaim(id)
  if (!claim) notFound()

  // If claim is no longer awaiting review, redirect to claim detail
  if (claim.status !== 'awaiting_human_approval') {
    redirect(`/claims/${id}`)
  }

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
            <Link
              href={`/claims/${id}`}
              className="text-slate-400 hover:text-white transition-colors"
            >
              Claim Detail
            </Link>
          </nav>
        </div>
      </header>

      <main className="flex-1 max-w-6xl mx-auto w-full px-6 py-8">
        <div className="mb-8">
          <div className="flex items-center gap-2 text-sm text-slate-500 mb-2">
            <Link href="/" className="hover:text-slate-300 transition-colors">
              Dashboard
            </Link>
            <span>/</span>
            <Link href={`/claims/${id}`} className="hover:text-slate-300 transition-colors">
              {claim.claimant_name}
            </Link>
            <span>/</span>
            <span className="text-yellow-400">Human Review</span>
          </div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-white">Human Review Required</h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-yellow-500/20 text-yellow-400">
              Awaiting Review
            </span>
          </div>
          <p className="text-slate-400 text-sm mt-1">
            This claim was escalated by the AI pipeline and requires adjuster review.
          </p>
        </div>

        <HitlReviewClient claim={claim} />
      </main>
    </div>
  )
}

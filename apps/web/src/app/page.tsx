import Link from 'next/link'
import type { InsuranceClaim, PaginatedResponse } from '@insurance/shared-types'
import { ClaimCard } from '@/components'
import { getIdentityToken } from '@/lib/gcp-auth'

async function getClaims(): Promise<InsuranceClaim[]> {
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
    const res = await fetch(`${baseUrl}/claims`, {
      cache: 'no-store',
      next: { revalidate: 0 },
      headers,
    })
    if (!res.ok) return []
    const body = (await res.json()) as PaginatedResponse<InsuranceClaim>
    return body.data ?? []
  } catch {
    return []
  }
}

export default async function DashboardPage() {
  const claims = await getClaims()

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
            <span className="text-blue-400 font-medium">Dashboard</span>
            <Link href="/claims/new" className="text-slate-400 hover:text-white transition-colors">
              New Claim
            </Link>
          </nav>
        </div>
      </header>

      <main className="flex-1 max-w-6xl mx-auto w-full px-6 py-8">
        {/* Header row */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-white">Claims Dashboard</h1>
            <p className="text-slate-400 text-sm mt-1">
              {claims.length} claim{claims.length !== 1 ? 's' : ''} total
            </p>
          </div>
          <Link
            href="/claims/new"
            className="bg-blue-600 hover:bg-blue-500 text-white text-sm font-semibold px-4 py-2 rounded-xl transition-colors"
          >
            + Submit Claim
          </Link>
        </div>

        {claims.length === 0 ? (
          <div className="text-center py-24 text-slate-500">
            <p className="text-lg font-medium">No claims yet</p>
            <p className="text-sm mt-1">Submit a claim to see it processed by the AI pipeline.</p>
            <Link
              href="/claims/new"
              className="inline-block mt-4 bg-blue-600 hover:bg-blue-500 text-white text-sm font-semibold px-5 py-2.5 rounded-xl transition-colors"
            >
              Submit First Claim
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {claims.map(claim => (
              <ClaimCard key={claim.id} claim={claim} />
            ))}
          </div>
        )}
      </main>
    </div>
  )
}

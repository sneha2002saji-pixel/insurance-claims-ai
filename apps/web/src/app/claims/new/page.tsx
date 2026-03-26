import Link from 'next/link'
import { ClaimForm } from '@/components'

export default function SubmitClaimPage() {
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
            <span className="text-blue-400 font-medium">New Claim</span>
          </nav>
        </div>
      </header>

      <main className="flex-1 max-w-2xl mx-auto w-full px-6 py-8">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-white">Submit a Claim</h1>
          <p className="text-slate-400 text-sm mt-1">
            Your claim will be automatically processed by the AI pipeline.
          </p>
        </div>

        <div className="bg-slate-800/50 border border-slate-700 rounded-2xl p-6">
          <ClaimForm />
        </div>
      </main>
    </div>
  )
}

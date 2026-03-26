'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import type { ClaimType } from '@insurance/shared-types'

const CLAIM_TYPES: ClaimType[] = ['AUTO', 'HEALTH', 'PROPERTY']

const TYPE_DESCRIPTIONS: Record<ClaimType, string> = {
  AUTO: 'Vehicle accidents, damage, theft',
  HEALTH: 'Medical bills, hospitalization, treatment',
  PROPERTY: 'Home damage, flooding, theft',
}

interface FormState {
  claim_type: ClaimType
  claimant_name: string
  policy_number: string
  amount: string
  incident_description: string
}

interface CreateClaimResponse {
  id: string
}

interface ApiErrorResponse {
  error?: {
    message?: string
  }
}

export function ClaimForm() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [form, setForm] = useState<FormState>({
    claim_type: 'AUTO',
    claimant_name: '',
    policy_number: '',
    amount: '',
    incident_description: '',
  })

  const parsedAmount = parseFloat(form.amount)
  const amountIsValid = !Number.isNaN(parsedAmount) && parsedAmount > 0

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      const res = await fetch('/api/claims', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          claim_type: form.claim_type,
          claimant_name: form.claimant_name,
          policy_number: form.policy_number,
          amount: parsedAmount,
          incident_description: form.incident_description,
        }),
      })

      if (!res.ok) {
        const body = (await res.json()) as ApiErrorResponse
        throw new Error(body.error?.message ?? 'Failed to submit claim')
      }

      const data = (await res.json()) as CreateClaimResponse
      router.push(`/claims/${data.id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unexpected error occurred')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Claim Type */}
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-2">Claim Type</label>
        <div className="grid grid-cols-3 gap-3">
          {CLAIM_TYPES.map(type => (
            <button
              key={type}
              type="button"
              onClick={() => setForm(f => ({ ...f, claim_type: type }))}
              className={`p-3 rounded-xl border text-left transition-all ${
                form.claim_type === type
                  ? 'border-blue-500 bg-blue-500/10 text-blue-400'
                  : 'border-slate-700 bg-slate-800/50 text-slate-400 hover:border-slate-500'
              }`}
            >
              <div className="font-semibold text-sm">{type}</div>
              <div className="text-xs mt-0.5 opacity-70">{TYPE_DESCRIPTIONS[type]}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Claimant Name */}
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-1.5">
          Claimant Name
        </label>
        <input
          type="text"
          required
          value={form.claimant_name}
          onChange={e => setForm(f => ({ ...f, claimant_name: e.target.value }))}
          placeholder="Full legal name"
          className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors"
        />
      </div>

      {/* Policy Number */}
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-1.5">
          Policy Number
        </label>
        <input
          type="text"
          required
          value={form.policy_number}
          onChange={e => setForm(f => ({ ...f, policy_number: e.target.value }))}
          placeholder="e.g. AUTO-2024-001"
          className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors"
        />
      </div>

      {/* Claim Amount */}
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-1.5">
          Claim Amount (USD)
        </label>
        <div className="relative">
          <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500">$</span>
          <input
            type="number"
            required
            min="1"
            step="0.01"
            value={form.amount}
            onChange={e => setForm(f => ({ ...f, amount: e.target.value }))}
            placeholder="0.00"
            className="w-full bg-slate-800 border border-slate-700 rounded-xl pl-8 pr-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors"
          />
        </div>
        {amountIsValid && parsedAmount > 10000 && (
          <p className="text-yellow-400 text-xs mt-1.5">
            &#9888; Claims over $10,000 may require human review
          </p>
        )}
      </div>

      {/* Incident Description */}
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-1.5">
          Incident Description
        </label>
        <textarea
          required
          rows={4}
          value={form.incident_description}
          onChange={e => setForm(f => ({ ...f, incident_description: e.target.value }))}
          placeholder="Describe what happened, when, and the extent of the damage or loss..."
          className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors resize-none"
        />
      </div>

      <button
        type="submit"
        disabled={loading}
        className="w-full bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 disabled:text-slate-500 text-white font-semibold py-3 rounded-xl transition-colors"
      >
        {loading ? 'Submitting\u2026' : 'Submit Claim'}
      </button>
    </form>
  )
}

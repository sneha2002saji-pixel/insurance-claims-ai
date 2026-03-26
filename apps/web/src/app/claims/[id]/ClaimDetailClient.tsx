'use client'

import { useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import type { InsuranceClaim, AgentEvent } from '@insurance/shared-types'
import { AgentThinkingFeed, FraudBadge, StatusTimeline } from '@/components'

interface ClaimDetailClientProps {
  claim: InsuranceClaim
}

export function ClaimDetailClient({ claim: initialClaim }: ClaimDetailClientProps) {
  const router = useRouter()
  const [claim, setClaim] = useState<InsuranceClaim>(initialClaim)
  const [events, setEvents] = useState<AgentEvent[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [pipelineStarted, setPipelineStarted] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fraudScore = events
    .filter(e => e.type === 'stage_complete' && e.stage === 'fraud_detection' && e.fraud_score !== undefined)
    .map(e => e.fraud_score!)
    .at(-1)

  const finalStatus = events.find(e => e.type === 'pipeline_complete')?.final_status

  const runPipeline = useCallback(async () => {
    setIsStreaming(true)
    setPipelineStarted(true)
    setError(null)
    setEvents([])

    let reader: ReadableStreamDefaultReader<Uint8Array> | null = null
    let terminated = false

    try {
      const res = await fetch(`/api/claims/${claim.id}/run`, { method: 'POST' })
      if (!res.ok || !res.body) {
        throw new Error('Failed to start pipeline')
      }

      reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const evt = JSON.parse(line.slice(6)) as AgentEvent
              setEvents(prev => [...prev, evt])

              if (
                evt.type === 'pipeline_complete' ||
                evt.type === 'hitl_required' ||
                evt.type === 'error'
              ) {
                terminated = true
                // Refresh server component to get the updated claim status
                router.refresh()
                return
              }
            } catch {
              // skip malformed SSE lines
            }
          }
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      // Cancel the reader if we exited before natural stream end (terminal event or error)
      if (reader && terminated) {
        reader.cancel().catch(() => undefined)
      }
      setIsStreaming(false)
    }
  }, [claim.id, router])

  const canRunPipeline = claim.status === 'pending' && !pipelineStarted

  const formattedAmount = new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(claim.amount)

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Left: Claim details + actions */}
      <div className="lg:col-span-1 space-y-4">
        {/* Claim info card */}
        <div className="bg-slate-800/50 border border-slate-700 rounded-2xl p-5">
          <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-4">
            Claim Details
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
              <dt className="text-xs text-slate-500">Claim Type</dt>
              <dd className="text-white mt-0.5">{claim.claim_type}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">Amount</dt>
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

        {/* Fraud score (only once available) */}
        {fraudScore !== undefined && (
          <div className="bg-slate-800/50 border border-slate-700 rounded-2xl p-5">
            <FraudBadge score={fraudScore} />
          </div>
        )}

        {/* Status timeline */}
        <div className="bg-slate-800/50 border border-slate-700 rounded-2xl p-5">
          <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-4">
            Status
          </h2>
          <StatusTimeline
            currentStatus={finalStatus ?? claim.status}
            updatedAt={claim.updated_at}
          />
        </div>

        {/* Run pipeline button */}
        {canRunPipeline && (
          <button
            onClick={() => void runPipeline()}
            className="w-full bg-blue-600 hover:bg-blue-500 text-white font-semibold py-3 rounded-xl transition-colors"
          >
            Run AI Pipeline
          </button>
        )}

        {/* HITL banner */}
        {claim.status === 'awaiting_human_approval' && (
          <a
            href={`/review/${claim.id}`}
            className="block w-full bg-yellow-500/10 border border-yellow-500/30 hover:bg-yellow-500/20 text-yellow-400 font-semibold py-3 rounded-xl transition-colors text-center text-sm"
          >
            Review &amp; Approve &rarr;
          </a>
        )}

        {error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-red-400 text-sm">
            {error}
          </div>
        )}
      </div>

      {/* Right: Agent thinking feed */}
      <div className="lg:col-span-2">
        <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-4">
          AI Processing
        </h2>
        <AgentThinkingFeed events={events} isStreaming={isStreaming} />
      </div>
    </div>
  )
}

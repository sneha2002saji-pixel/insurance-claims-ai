'use client'

import { useState } from 'react'
import type { AgentEvent, AgentStage } from '@insurance/shared-types'
import { STAGE_LABELS } from '@insurance/shared-types'

interface AgentThinkingFeedProps {
  events: AgentEvent[]
  isStreaming: boolean
}

interface StageGroup {
  stage: AgentStage
  thoughts: AgentEvent[]
  startEvent?: AgentEvent
  completeEvent?: AgentEvent
}

function groupEventsByStage(events: AgentEvent[]): StageGroup[] {
  const stageMap = new Map<AgentStage, StageGroup>()
  const stageOrder: AgentStage[] = []

  for (const event of events) {
    if (!event.stage) continue
    if (!stageMap.has(event.stage)) {
      stageMap.set(event.stage, { stage: event.stage, thoughts: [] })
      stageOrder.push(event.stage)
    }
    const group = stageMap.get(event.stage)!
    if (event.type === 'thought') {
      group.thoughts.push(event)
    } else if (event.type === 'stage_start') {
      group.startEvent = event
    } else if (event.type === 'stage_complete') {
      group.completeEvent = event
    }
  }

  return stageOrder.map(s => stageMap.get(s)!)
}

interface ThinkingSectionProps {
  thoughts: AgentEvent[]
}

function ThinkingSection({ thoughts }: ThinkingSectionProps) {
  const [open, setOpen] = useState(false)

  if (thoughts.length === 0) return null

  return (
    <div className="mt-2">
      <button
        onClick={() => setOpen(o => !o)}
        className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300 transition-colors"
      >
        <span>{open ? '▾' : '▸'}</span>
        <span>
          Agent thinking ({thoughts.length} thought{thoughts.length !== 1 ? 's' : ''})
        </span>
      </button>
      {open && (
        <div className="mt-2 pl-3 border-l border-slate-700 space-y-2">
          {thoughts.map((t, i) => (
            <p
              key={`${t.timestamp}-${i}`}
              className="text-xs text-slate-500 font-mono leading-relaxed whitespace-pre-wrap"
            >
              {t.content}
            </p>
          ))}
        </div>
      )}
    </div>
  )
}

export function AgentThinkingFeed({ events, isStreaming }: AgentThinkingFeedProps) {
  const stageGroups = groupEventsByStage(events)
  const hitlEvent = events.find(e => e.type === 'hitl_required')
  const completeEvent = events.find(e => e.type === 'pipeline_complete')
  const errorEvent = events.find(e => e.type === 'error')

  if (events.length === 0 && !isStreaming) {
    return (
      <div className="text-center py-8 text-slate-500">
        <p>Pipeline has not started yet.</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Stage groups */}
      {stageGroups.map(({ stage, thoughts, startEvent, completeEvent: stageComplete }) => (
        <div key={stage} className="bg-slate-800/50 border border-slate-700 rounded-xl p-4">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <div
                className={`w-2 h-2 rounded-full ${
                  stageComplete ? 'bg-green-400' : 'bg-blue-400 animate-pulse'
                }`}
              />
              <h4 className="text-sm font-semibold text-white">{STAGE_LABELS[stage]}</h4>
              {startEvent && (
                <span className="text-xs text-slate-500">
                  {new Date(startEvent.timestamp).toLocaleTimeString('en-US', {
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit',
                  })}
                </span>
              )}
            </div>
            {stageComplete && (
              <span className="text-xs text-green-400">&#10003; Complete</span>
            )}
          </div>
          <ThinkingSection thoughts={thoughts} />
          {stageComplete && (
            <div className="mt-3 pt-3 border-t border-slate-700">
              <p className="text-xs text-slate-400 leading-relaxed line-clamp-4">
                {stageComplete.content}
              </p>
            </div>
          )}
        </div>
      ))}

      {/* Streaming indicator */}
      {isStreaming && (
        <div className="flex items-center gap-2 text-slate-400 text-sm py-2">
          <div className="flex gap-1">
            <div
              className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce"
              style={{ animationDelay: '0ms' }}
            />
            <div
              className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce"
              style={{ animationDelay: '150ms' }}
            />
            <div
              className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce"
              style={{ animationDelay: '300ms' }}
            />
          </div>
          <span>Agent processing&hellip;</span>
        </div>
      )}

      {/* HITL pause */}
      {hitlEvent && (
        <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-yellow-400 text-lg">&#9888;</span>
            <h4 className="text-yellow-400 font-semibold text-sm">Human Review Required</h4>
          </div>
          <p className="text-slate-300 text-sm">{hitlEvent.content}</p>
        </div>
      )}

      {/* Pipeline complete */}
      {completeEvent && (
        <div className="bg-green-500/10 border border-green-500/30 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-green-400 text-lg">&#10003;</span>
            <h4 className="text-green-400 font-semibold text-sm">Pipeline Complete</h4>
          </div>
          <p className="text-slate-300 text-sm">{completeEvent.content}</p>
        </div>
      )}

      {/* Error */}
      {errorEvent && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-red-400 text-lg">&#10005;</span>
            <h4 className="text-red-400 font-semibold text-sm">Processing Error</h4>
          </div>
          <p className="text-slate-300 text-sm">{errorEvent.content}</p>
        </div>
      )}
    </div>
  )
}

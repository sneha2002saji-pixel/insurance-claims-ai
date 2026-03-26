// ─── Claim Types ───────────────────────────────────────────────────────────

export type ClaimType = 'AUTO' | 'HEALTH' | 'PROPERTY'

export type ClaimStatus =
  | 'pending'
  | 'under_review'
  | 'agent_approved'
  | 'awaiting_human_approval'
  | 'rejected'
  | 'partial_settlement'
  | 'settled'

export interface InsuranceClaim {
  id: string
  claim_type: ClaimType
  claimant_name: string
  policy_number: string
  amount: number
  incident_description: string
  document_refs: string[]
  status: ClaimStatus
  created_at: string   // ISO 8601
  updated_at: string   // ISO 8601
}

export interface CreateClaimRequest {
  claim_type: ClaimType
  claimant_name: string
  policy_number: string
  amount: number
  incident_description: string
  document_refs?: string[]
}

// ─── Agent Pipeline Types ──────────────────────────────────────────────────

export type AgentStage =
  | 'document_verification'
  | 'fraud_detection'
  | 'claim_validation'
  | 'decision'

export type AgentEventType =
  | 'thought'
  | 'stage_start'
  | 'stage_complete'
  | 'hitl_required'
  | 'pipeline_complete'
  | 'error'

export interface AgentEvent {
  type: AgentEventType
  stage?: AgentStage    // optional: pipeline_complete and error events are not stage-specific
  content: string
  fraud_score?: number          // 0.0–1.0, present when type is stage_complete for fraud_detection
  final_status?: ClaimStatus    // present when type is pipeline_complete
  timestamp: string             // ISO 8601
}

export interface AgentAnalysis {
  id: string
  claim_id: string
  stage: AgentStage
  agent_name: string
  output_json: Record<string, unknown>
  confidence_score: number
  fraud_score?: number
  duration_ms: number
  created_at: string
}

// ─── HITL Types ────────────────────────────────────────────────────────────

export type HumanDecision = 'approved' | 'rejected' | 'partial_settlement'

export type HitlTriggerReason = 'high_amount' | 'high_fraud_risk' | 'both'

export interface HumanApprovalRequest {
  id: string
  claim_id: string
  trigger_reason: HitlTriggerReason
  fraud_score: number
  amount: number
  assigned_to?: string
  decision?: HumanDecision
  adjuster_comment?: string
  created_at: string
  decided_at?: string
}

export interface HumanApprovalPayload {
  decision: HumanDecision
  comment: string
}

// ─── Audit Log Types ───────────────────────────────────────────────────────

export type AuditEventType =
  | 'claim_created'
  | 'pipeline_started'
  | 'stage_completed'
  | 'hitl_triggered'
  | 'human_decision'
  | 'claim_settled'
  | 'claim_rejected'

export interface AuditLogEntry {
  id: string
  claim_id: string
  event_type: AuditEventType
  previous_status?: ClaimStatus
  new_status?: ClaimStatus
  actor: string
  details_json: Record<string, unknown>
  created_at: string
}

// ─── API Response Types ────────────────────────────────────────────────────

export interface ApiError {
  error: {
    code: string
    message: string
    details?: unknown[]
    traceId?: string
  }
}

export interface PaginatedResponse<T> {
  data: T[]
  pagination: {
    nextCursor?: string
    hasMore: boolean
    total: number
  }
}

// ─── UI Helper Types ───────────────────────────────────────────────────────

export const CLAIM_TYPE_COLORS: Record<ClaimType, string> = {
  AUTO: 'blue',
  HEALTH: 'green',
  PROPERTY: 'orange',
}

export const STATUS_LABELS: Record<ClaimStatus, string> = {
  pending: 'Pending',
  under_review: 'Under Review',
  agent_approved: 'Agent Approved',
  awaiting_human_approval: 'Awaiting Review',
  rejected: 'Rejected',
  partial_settlement: 'Partial Settlement',
  settled: 'Settled',
}

export const STAGE_LABELS: Record<AgentStage, string> = {
  document_verification: 'Document Verification',
  fraud_detection: 'Fraud Detection',
  claim_validation: 'Claim Validation',
  decision: 'Decision',
}

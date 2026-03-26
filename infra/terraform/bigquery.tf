# BigQuery dataset
resource "google_bigquery_dataset" "insurance" {
  project     = var.project_id
  dataset_id  = var.bq_dataset_id
  location    = "US"
  description = "Insurance Claims AI — claims, agent analyses, audit log, and human approval requests"
  labels      = local.common_labels

  depends_on = [google_project_service.bigquery]
}

# Table: insurance_claims — master claims record
resource "google_bigquery_table" "insurance_claims" {
  project    = var.project_id
  dataset_id = google_bigquery_dataset.insurance.dataset_id
  table_id   = "insurance_claims"
  labels     = local.common_labels

  deletion_protection = true

  schema = jsonencode([
    {
      name = "id"
      type = "STRING"
      mode = "REQUIRED"
      description = "Unique claim identifier (UUID)"
    },
    {
      name = "claim_type"
      type = "STRING"
      mode = "REQUIRED"
      description = "Type of insurance claim: AUTO, HEALTH, or PROPERTY"
    },
    {
      name = "claimant_name"
      type = "STRING"
      mode = "REQUIRED"
      description = "Full name of the policy holder submitting the claim"
    },
    {
      name = "policy_number"
      type = "STRING"
      mode = "REQUIRED"
      description = "Insurance policy number associated with this claim"
    },
    {
      name = "amount"
      type = "FLOAT64"
      mode = "REQUIRED"
      description = "Claimed amount in USD"
    },
    {
      name = "incident_description"
      type = "STRING"
      mode = "NULLABLE"
      description = "Free-text description of the incident"
    },
    {
      name = "document_refs"
      type = "JSON"
      mode = "NULLABLE"
      description = "JSON array of GCS document references (photos, reports, invoices)"
    },
    {
      name = "status"
      type = "STRING"
      mode = "REQUIRED"
      description = "Claim lifecycle status: pending | under_review | agent_approved | awaiting_human_approval | rejected | partial_settlement | settled"
    },
    {
      name = "created_at"
      type = "TIMESTAMP"
      mode = "REQUIRED"
      description = "UTC timestamp when the claim was submitted"
    },
    {
      name = "updated_at"
      type = "TIMESTAMP"
      mode = "REQUIRED"
      description = "UTC timestamp of the most recent status update"
    }
  ])
}

# Table: agent_analyses — per-stage agent pipeline outputs
resource "google_bigquery_table" "agent_analyses" {
  project    = var.project_id
  dataset_id = google_bigquery_dataset.insurance.dataset_id
  table_id   = "agent_analyses"
  labels     = local.common_labels

  deletion_protection = true

  schema = jsonencode([
    {
      name = "id"
      type = "STRING"
      mode = "REQUIRED"
      description = "Unique analysis record identifier (UUID)"
    },
    {
      name = "claim_id"
      type = "STRING"
      mode = "REQUIRED"
      description = "Foreign key to insurance_claims.id"
    },
    {
      name = "stage"
      type = "STRING"
      mode = "REQUIRED"
      description = "Pipeline stage: document_verification | policy_validation | fraud_detection | settlement_calculation | decision"
    },
    {
      name = "agent_name"
      type = "STRING"
      mode = "REQUIRED"
      description = "Name of the ADK agent that produced this analysis"
    },
    {
      name = "output_json"
      type = "JSON"
      mode = "NULLABLE"
      description = "Full structured output from the agent stage"
    },
    {
      name = "confidence_score"
      type = "FLOAT64"
      mode = "NULLABLE"
      description = "Agent confidence in its decision (0.0–1.0)"
    },
    {
      name = "fraud_score"
      type = "FLOAT64"
      mode = "NULLABLE"
      description = "Fraud risk score (0.0–1.0); higher = more suspicious"
    },
    {
      name = "duration_ms"
      type = "INT64"
      mode = "NULLABLE"
      description = "Time taken by this agent stage in milliseconds"
    },
    {
      name = "created_at"
      type = "TIMESTAMP"
      mode = "REQUIRED"
      description = "UTC timestamp when this analysis was recorded"
    }
  ])
}

# Table: audit_log — insert-only event log (never UPDATE or DELETE)
# Clustered by (claim_id, created_at) for efficient per-claim audit queries
resource "google_bigquery_table" "audit_log" {
  project    = var.project_id
  dataset_id = google_bigquery_dataset.insurance.dataset_id
  table_id   = "audit_log"
  labels     = local.common_labels
  clustering = ["claim_id", "created_at"]

  deletion_protection = true

  schema = jsonencode([
    {
      name = "id"
      type = "STRING"
      mode = "REQUIRED"
      description = "Unique audit event identifier (UUID)"
    },
    {
      name = "claim_id"
      type = "STRING"
      mode = "REQUIRED"
      description = "Foreign key to insurance_claims.id"
    },
    {
      name = "event_type"
      type = "STRING"
      mode = "REQUIRED"
      description = "Type of audit event: CLAIM_CREATED | STATUS_CHANGED | AGENT_STAGE_COMPLETE | HUMAN_DECISION | DOCUMENT_UPLOADED"
    },
    {
      name = "previous_status"
      type = "STRING"
      mode = "NULLABLE"
      description = "Claim status before this event (null for CLAIM_CREATED events)"
    },
    {
      name = "new_status"
      type = "STRING"
      mode = "NULLABLE"
      description = "Claim status after this event"
    },
    {
      name = "actor"
      type = "STRING"
      mode = "REQUIRED"
      description = "Identity that triggered the event: agent name, adjuster email, or 'system'"
    },
    {
      name = "details_json"
      type = "JSON"
      mode = "NULLABLE"
      description = "Additional event-specific context as JSON"
    },
    {
      name = "created_at"
      type = "TIMESTAMP"
      mode = "REQUIRED"
      description = "UTC timestamp when this audit event was recorded"
    }
  ])
}

# Table: human_approval_requests — HITL pause records
resource "google_bigquery_table" "human_approval_requests" {
  project    = var.project_id
  dataset_id = google_bigquery_dataset.insurance.dataset_id
  table_id   = "human_approval_requests"
  labels     = local.common_labels

  deletion_protection = true

  schema = jsonencode([
    {
      name = "id"
      type = "STRING"
      mode = "REQUIRED"
      description = "Unique approval request identifier (UUID)"
    },
    {
      name = "claim_id"
      type = "STRING"
      mode = "REQUIRED"
      description = "Foreign key to insurance_claims.id"
    },
    {
      name = "trigger_reason"
      type = "STRING"
      mode = "REQUIRED"
      description = "Why human review was triggered: HIGH_FRAUD_SCORE | HIGH_AMOUNT | POLICY_EXCEPTION | MULTI_CLAIM"
    },
    {
      name = "fraud_score"
      type = "FLOAT64"
      mode = "NULLABLE"
      description = "Fraud score at the time of escalation (0.0–1.0)"
    },
    {
      name = "amount"
      type = "FLOAT64"
      mode = "REQUIRED"
      description = "Claimed amount that triggered escalation"
    },
    {
      name = "assigned_to"
      type = "STRING"
      mode = "NULLABLE"
      description = "Email of the claims adjuster assigned for review"
    },
    {
      name = "decision"
      type = "STRING"
      mode = "NULLABLE"
      description = "Adjuster decision: APPROVE | REJECT | PARTIAL_SETTLE | ESCALATE"
    },
    {
      name = "adjuster_comment"
      type = "STRING"
      mode = "NULLABLE"
      description = "Free-text comment from the adjuster explaining their decision"
    },
    {
      name = "created_at"
      type = "TIMESTAMP"
      mode = "REQUIRED"
      description = "UTC timestamp when the approval request was created"
    },
    {
      name = "decided_at"
      type = "TIMESTAMP"
      mode = "NULLABLE"
      description = "UTC timestamp when the adjuster submitted their decision"
    }
  ])
}

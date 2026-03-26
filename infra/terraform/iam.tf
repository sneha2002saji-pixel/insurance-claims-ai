# Service account for the Python ADK agent Cloud Run service
resource "google_service_account" "insurance_agent_sa" {
  project      = var.project_id
  account_id   = "insurance-agent-sa"
  display_name = "Insurance Claims Agent SA"
  description  = "Service account for the insurance claims Python ADK agent running on Cloud Run"
}

# Service account for the Next.js web Cloud Run service
resource "google_service_account" "insurance_web_sa" {
  project      = var.project_id
  account_id   = "insurance-web-sa"
  display_name = "Insurance Claims Web SA"
  description  = "Service account for the insurance claims Next.js web service running on Cloud Run"
}

# --- Agent SA IAM bindings ---

# BigQuery: read/write claim data, insert analyses and audit events
resource "google_project_iam_member" "agent_bq_data_editor" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.insurance_agent_sa.email}"
}

# BigQuery: run jobs (required to execute queries in addition to dataEditor)
resource "google_project_iam_member" "agent_bq_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.insurance_agent_sa.email}"
}

# Redis: read connection metadata (actual auth via Secret Manager)
resource "google_project_iam_member" "agent_redis_viewer" {
  project = var.project_id
  role    = "roles/redis.viewer"
  member  = "serviceAccount:${google_service_account.insurance_agent_sa.email}"
}

# Secret Manager: access secrets at runtime (GOOGLE_API_KEY, REDIS_URL, etc.)
resource "google_project_iam_member" "agent_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.insurance_agent_sa.email}"
}

# Cloud Storage: read mock documents from GCS bucket
resource "google_project_iam_member" "agent_storage_object_viewer" {
  project = var.project_id
  role    = "roles/storage.objectViewer"
  member  = "serviceAccount:${google_service_account.insurance_agent_sa.email}"
}

# --- Web SA IAM bindings ---

# BigQuery: read-only for dashboard and claim status queries
resource "google_project_iam_member" "web_bq_data_viewer" {
  project = var.project_id
  role    = "roles/bigquery.dataViewer"
  member  = "serviceAccount:${google_service_account.insurance_web_sa.email}"
}

# BigQuery: run jobs (required for the web BFF to execute SELECT queries)
resource "google_project_iam_member" "web_bq_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.insurance_web_sa.email}"
}

# Secret Manager: access secrets at runtime (GCP_PROJECT_ID, REDIS_URL)
resource "google_project_iam_member" "web_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.insurance_web_sa.email}"
}

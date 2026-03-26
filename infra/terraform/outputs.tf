output "bq_dataset_id" {
  description = "BigQuery dataset ID containing all insurance claims tables"
  value       = google_bigquery_dataset.insurance.dataset_id
}

output "agent_sa_email" {
  description = "Service account email for the Python ADK agent Cloud Run service"
  value       = google_service_account.insurance_agent_sa.email
}

output "web_sa_email" {
  description = "Service account email for the Next.js web Cloud Run service"
  value       = google_service_account.insurance_web_sa.email
}

output "artifact_registry_url" {
  description = "Artifact Registry base URL for pushing and pulling Docker images"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.insurance_claims.repository_id}"
}

output "mock_documents_bucket" {
  description = "GCS bucket name for mock insurance documents (photos, PDFs, invoices)"
  value       = google_storage_bucket.mock_documents.name
}

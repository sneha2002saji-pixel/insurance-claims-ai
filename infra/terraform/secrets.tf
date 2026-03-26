# Secret Manager secrets — created here as empty shells.
# Values must be populated manually via CLI or Secret Manager console:
#   gcloud secrets versions add GOOGLE_API_KEY --data-file=<(echo -n "your-key")
# Never store secret values in Terraform state or code.

resource "google_secret_manager_secret" "google_api_key" {
  project   = var.project_id
  secret_id = "GOOGLE_API_KEY"

  labels = {
    project     = "insurance-claims-ai"
    environment = var.environment
    managed_by  = "terraform"
  }

  replication {
    auto {}
  }

  depends_on = [google_project_service.secretmanager]
}

resource "google_secret_manager_secret" "gcp_project_id" {
  project   = var.project_id
  secret_id = "GCP_PROJECT_ID"

  labels = {
    project     = "insurance-claims-ai"
    environment = var.environment
    managed_by  = "terraform"
  }

  replication {
    auto {}
  }

  depends_on = [google_project_service.secretmanager]
}

resource "google_secret_manager_secret" "redis_url" {
  project   = var.project_id
  secret_id = "REDIS_URL"

  labels = {
    project     = "insurance-claims-ai"
    environment = var.environment
    managed_by  = "terraform"
  }

  replication {
    auto {}
  }

  depends_on = [google_project_service.secretmanager]
}

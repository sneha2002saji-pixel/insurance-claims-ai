locals {
  common_labels = {
    project     = "insurance-claims-ai"
    environment = var.environment
    managed_by  = "terraform"
    team        = "engineering"
  }
}

# Enable required GCP APIs
resource "google_project_service" "bigquery" {
  project            = var.project_id
  service            = "bigquery.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "redis" {
  project            = var.project_id
  service            = "redis.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "cloudrun" {
  project            = var.project_id
  service            = "run.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "secretmanager" {
  project            = var.project_id
  service            = "secretmanager.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "artifactregistry" {
  project            = var.project_id
  service            = "artifactregistry.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "storage" {
  project            = var.project_id
  service            = "storage.googleapis.com"
  disable_on_destroy = false
}

# Artifact Registry — Docker repository for insurance claims AI images
resource "google_artifact_registry_repository" "insurance_claims" {
  project       = var.project_id
  location      = var.region
  repository_id = "insurance-claims"
  format        = "DOCKER"
  description   = "Insurance Claims AI Docker images"
  labels        = local.common_labels

  depends_on = [google_project_service.artifactregistry]
}

# GCS bucket — mock insurance documents (intake PDFs, photos, etc.)
resource "google_storage_bucket" "mock_documents" {
  project                     = var.project_id
  name                        = "insurance-mock-documents"
  location                    = "US"
  force_destroy               = false
  uniform_bucket_level_access = true
  labels                      = local.common_labels

  versioning {
    enabled = true
  }

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age = 365
    }
  }

  depends_on = [google_project_service.storage]
}

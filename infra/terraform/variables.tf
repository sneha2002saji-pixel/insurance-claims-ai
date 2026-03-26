variable "project_id" {
  description = "GCP project ID where all insurance claims AI resources are deployed"
  type        = string
  default     = "upbeat-repeater-477110-q6"
}

variable "region" {
  description = "GCP region for Cloud Run services and Artifact Registry"
  type        = string
  default     = "us-central1"

  validation {
    condition     = contains(["us-central1", "us-east1", "europe-west1"], var.region)
    error_message = "Region must be one of: us-central1, us-east1, europe-west1."
  }
}

variable "environment" {
  description = "Deployment environment label applied to all resources"
  type        = string
  default     = "prod"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "bq_dataset_id" {
  description = "BigQuery dataset ID for all insurance claims tables"
  type        = string
  default     = "insurance"
}

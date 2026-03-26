terraform {
  required_version = ">= 1.6.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
  backend "gcs" {
    bucket = "upbeat-repeater-477110-q6-tf-state"
    prefix = "insurance-claims-ai/state"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

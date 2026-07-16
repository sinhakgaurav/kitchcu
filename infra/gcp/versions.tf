terraform {
  required_version = ">= 1.7.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.10"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # Uncomment once the GCS state bucket exists (see docs/DEPLOYMENT-GCP.md step 1) —
  # local state is fine for the very first apply that creates the bucket itself.
  # backend "gcs" {
  #   bucket = "REPLACE_WITH_STATE_BUCKET"
  #   prefix = "ckac/terraform/state"
  # }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

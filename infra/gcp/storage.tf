# Kitchen media (dish live-capture photos). Reuses the existing MinioMediaStorage client
# unchanged via GCS's S3-compatible interoperability endpoint — see docs/DEPLOYMENT-GCP.md
# for the one-time HMAC key setup. No application code changes required.
#
# KNOWN GAP (tracked, not a launch blocker): objects are public-read to match current
# MinIO dev/prod behavior. Security standard calls for signed URLs — fast-follow before
# this bucket holds anything beyond publicly-intended dish photos.

resource "google_storage_bucket" "media" {
  name     = "ckac-media-${var.project_id}"
  location = var.region
  project  = var.project_id

  uniform_bucket_level_access = true
  force_destroy               = false

  cors {
    origin          = ["https://${var.domain_root}", "https://customer.${var.domain_root}", "https://kitchen.${var.domain_root}", "https://admin.${var.domain_root}"]
    method          = ["GET", "HEAD"]
    response_header = ["*"]
    max_age_seconds  = 3600
  }

  lifecycle_rule {
    condition {
      age = 365
    }
    action {
      type = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }

  depends_on = [google_project_service.apis]
}

resource "google_storage_bucket_iam_member" "media_public_read" {
  bucket = google_storage_bucket.media.name
  role   = "roles/storage.objectViewer"
  member = "allUsers"
}

# HMAC key lets the existing MinioMediaStorage (S3-compatible) client talk to GCS
# via its S3 interoperability endpoint with zero application code changes.
resource "google_storage_hmac_key" "media" {
  service_account_email = google_service_account.run_sa.email
}

locals {
  # Non-secret media env vars — same on every service that uploads dish/refund media.
  media_env_plain = {
    MEDIA_STORAGE_BACKEND = "minio"
    MINIO_ENDPOINT          = "storage.googleapis.com"
    MINIO_BUCKET             = google_storage_bucket.media.name
    MINIO_PUBLIC_URL         = "https://storage.googleapis.com/${google_storage_bucket.media.name}"
    MINIO_SECURE             = "true"
  }
}

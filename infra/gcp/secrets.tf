# Secret Manager — bootstrap secrets the app needs to boot. Third-party keys
# (Razorpay, Meta WhatsApp, LiveKit, OAuth, Google Maps) are intentionally NOT
# here: they're DB-backed and owner/admin-configurable at runtime via
# Super Admin -> Control -> API Keys (ckac_identity.platform_api_keys, encrypted
# with JWT_SECRET). Populate those through the product UI after go-live, not Terraform.

locals {
  bootstrap_secrets = {
    database-url      = local.database_url_asyncpg
    database-sync-url = local.database_url_sync
    redis-url          = local.redis_url
    jwt-secret         = var.jwt_secret
    internal-api-key   = var.internal_api_key
    minio-access-key   = google_storage_hmac_key.media.access_id
    minio-secret-key   = google_storage_hmac_key.media.secret
  }
}

resource "google_secret_manager_secret" "bootstrap" {
  for_each  = local.bootstrap_secrets
  secret_id = "ckac-${each.key}"

  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }

  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "bootstrap" {
  for_each    = local.bootstrap_secrets
  secret      = google_secret_manager_secret.bootstrap[each.key].id
  secret_data = each.value

  lifecycle {
    # Terraform manages the secret container; rotate values via
    # `gcloud secrets versions add` (see runbook) without forcing an apply diff.
    ignore_changes = [secret_data]
  }
}

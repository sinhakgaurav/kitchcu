# One-shot Alembic migration jobs — run explicitly by CI/CD before deploying a new
# revision of the matching service (see .github/workflows/deploy-gcp.yml). Running
# migrations here (not in the serving container's boot command) avoids N concurrent
# Cloud Run instances racing `alembic upgrade head` on cold start / autoscale-out.

resource "google_cloud_run_v2_job" "migrate" {
  for_each = local.backend_services

  name     = "ckac-${each.key}-migrate"
  location = var.region

  template {
    template {
      service_account = google_service_account.run_sa.email
      max_retries      = 1
      timeout          = "300s"

      vpc_access {
        network_interfaces {
          network    = google_compute_network.vpc.id
          subnetwork = google_compute_subnetwork.run_subnet.id
        }
        egress = "PRIVATE_RANGES_ONLY"
      }

      containers {
        image   = "${local.registry_prefix}/${each.key}:${var.image_tag}"
        command = ["alembic"]
        args    = ["upgrade", "head"]

        env {
          name  = "APP_ENV"
          value = "production"
        }
        env {
          name  = "PYTHONPATH"
          value = "/app/packages/ckac-common"
        }

        dynamic "env" {
          for_each = {
            DATABASE_URL      = "database-url"
            DATABASE_SYNC_URL = "database-sync-url"
          }
          content {
            name = env.key
            value_source {
              secret_key_ref {
                secret  = google_secret_manager_secret.bootstrap[env.value].secret_id
                version = "latest"
              }
            }
          }
        }
      }
    }
  }

  depends_on = [
    google_secret_manager_secret_version.bootstrap,
  ]
}

# NOTE: after the first `terraform apply`, CI/CD (deploy-gcp.yml) updates each
# job's image via `gcloud run jobs update` on every deploy — that's expected to
# drift from whatever `var.image_tag` Terraform last applied. Terraform owns the
# job's existence/config; CI/CD owns which image version it runs. Don't "fix"
# this drift by re-running `terraform apply` with an old image_tag.

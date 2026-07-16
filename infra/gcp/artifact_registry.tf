resource "google_artifact_registry_repository" "ckac" {
  location      = var.region
  repository_id = "ckac"
  description   = "kitchCU service + website container images"
  format        = "DOCKER"

  cleanup_policies {
    id     = "keep-last-20"
    action = "KEEP"
    most_recent_versions {
      keep_count = 20
    }
  }

  depends_on = [google_project_service.apis]
}

locals {
  registry_host   = "${var.region}-docker.pkg.dev"
  registry_prefix = "${local.registry_host}/${var.project_id}/${google_artifact_registry_repository.ckac.repository_id}"
}

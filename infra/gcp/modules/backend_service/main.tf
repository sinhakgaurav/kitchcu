# One internal (never public) domain service. Ingress is INTERNAL_ONLY —
# reachable only from the gateway / other Cloud Run services in this VPC/project.
# See infra/gcp/cloud_run_backend.tf for why this is a module (not a single
# for_each resource): Cloud Run services with cross-service dependencies
# (billing -> identity, growth -> billing + notification, ...) can't reference
# sibling instances of the *same* for_each resource — Terraform's graph builder
# treats that as a self-reference cycle regardless of which key differs. Each
# module call is its own graph node, so tier1/tier2 module calls can safely
# depend on tier0/tier1 module outputs.

resource "google_cloud_run_v2_service" "this" {
  name     = "ckac-${var.service_key}"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_INTERNAL_ONLY"

  template {
    service_account = var.run_sa_email

    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }

    vpc_access {
      network_interfaces {
        network    = var.network_id
        subnetwork = var.subnetwork_id
      }
      egress = "PRIVATE_RANGES_ONLY"
    }

    containers {
      image = "${var.registry_prefix}/${var.service_key}:${var.image_tag}"

      ports {
        container_port = var.port
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }

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
          REDIS_URL         = "redis-url"
          JWT_SECRET        = "jwt-secret"
          INTERNAL_API_KEY  = "internal-api-key"
        }
        content {
          name = env.key
          value_source {
            secret_key_ref {
              secret  = var.secret_ids[env.value]
              version = "latest"
            }
          }
        }
      }

      dynamic "env" {
        for_each = var.is_media_service ? {
          MINIO_ACCESS_KEY = "minio-access-key"
          MINIO_SECRET_KEY = "minio-secret-key"
        } : {}
        content {
          name = env.key
          value_source {
            secret_key_ref {
              secret  = var.secret_ids[env.value]
              version = "latest"
            }
          }
        }
      }

      dynamic "env" {
        for_each = var.is_media_service ? var.media_env_plain : {}
        content {
          name  = env.key
          value = env.value
        }
      }

      dynamic "env" {
        for_each = var.static_env
        content {
          name  = env.key
          value = env.value
        }
      }

      dynamic "env" {
        for_each = var.cross_service_env
        content {
          name  = env.key
          value = env.value
        }
      }

      startup_probe {
        http_get {
          path = "/health/live"
          port = var.port
        }
        initial_delay_seconds = 5
        period_seconds        = 5
        failure_threshold     = 10
      }

      liveness_probe {
        http_get {
          path = "/health/live"
          port = var.port
        }
        period_seconds = 15
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
}

# SECURITY TRADE-OFF (documented, not a silent gap): backend services skip Cloud
# Run's per-call IAM/ID-token check so the gateway's existing plain httpx calls
# work with zero application code changes. The real boundary is
# `ingress = INTERNAL_ONLY` above, which rejects all public-internet traffic at
# the network edge regardless of IAM — only resources inside this GCP project
# (Cloud Run services, VPC-connected workloads) can reach these URLs at all.
# Fast-follow: mint Google-signed ID tokens in the gateway's httpx clients and
# switch this to per-caller-service-account `roles/run.invoker` for
# defense-in-depth (see docs/DEPLOYMENT-GCP.md "Known gaps").
resource "google_cloud_run_v2_service_iam_member" "invoker" {
  name     = google_cloud_run_v2_service.this.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}

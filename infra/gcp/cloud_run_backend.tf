# 12 internal domain services — never public. Only reachable from the gateway /
# other Cloud Run services in this project, or via the load balancer for the
# gateway itself. This mirrors the existing "gateway is the only public edge"
# rule enforced in services/gateway/app/main.py — zero application code changes.

locals {
  media_services = toset(["identity", "catalog", "billing"])

  # for_each SOURCE — must stay free of any reference to
  # google_cloud_run_v2_service.backend itself (that would be a self-reference
  # cycle: Terraform needs this fully resolved before it can even expand the
  # for_each). Cross-service URLs are wired separately below via
  # backend_service_deps, resolved inside the resource body per-instance.
  backend_services = {
    identity     = { port = 8001 }
    catalog      = { port = 8002 }
    order        = { port = 8003 }
    billing      = { port = 8004 }
    notification = { port = 8005 }
    marketing    = { port = 8006 }
    ratings      = { port = 8007 }
    growth       = { port = 8008 }
    delivery     = { port = 8009 }
    learning     = { port = 8010 }
    community    = { port = 8011 }
    streaming    = { port = 8012 }
  }

  # Static (non-cross-service) extra env vars per service.
  backend_static_env = {
    notification = { WHATSAPP_VERIFY_TOKEN = "REPLACE-VIA-SUPER-ADMIN-CONTROL" } # bootstrap only — DB value in Super Admin -> Control takes precedence
    community    = { COMMUNITY_MIN_ORDERS_RANKING = "3" }
  }

  # Cross-service dependency wiring: service_key => { ENV_VAR_NAME = <other backend_services key> }.
  # The `.uri` lookup happens inside the resource body (see dynamic "env" below),
  # not here — that's what keeps this cycle-free.
  backend_service_deps = {
    billing = {
      IDENTITY_SERVICE_URL = "identity"
    }
    notification = {
      ORDER_SERVICE_URL = "order"
    }
    growth = {
      BILLING_SERVICE_URL      = "billing"
      NOTIFICATION_SERVICE_URL = "notification"
    }
    learning = {
      CATALOG_SERVICE_URL      = "catalog"
      NOTIFICATION_SERVICE_URL = "notification"
    }
  }

  # Services with an alembic/ dir — see cloud_run_jobs.tf. Kept as a single
  # source of truth alongside backend_services so job + service definitions
  # can't drift.
  services_with_migrations = keys(local.backend_services)
}

resource "google_cloud_run_v2_service" "backend" {
  for_each = local.backend_services

  name     = "ckac-${each.key}"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_INTERNAL_ONLY"

  template {
    service_account = google_service_account.run_sa.email

    scaling {
      min_instance_count = var.backend_min_instances
      max_instance_count = var.max_instances
    }

    vpc_access {
      network_interfaces {
        network    = google_compute_network.vpc.id
        subnetwork = google_compute_subnetwork.run_subnet.id
      }
      egress = "PRIVATE_RANGES_ONLY"
    }

    containers {
      image = "${local.registry_prefix}/${each.key}:${var.image_tag}"

      ports {
        container_port = each.value.port
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
          REDIS_URL          = "redis-url"
          JWT_SECRET         = "jwt-secret"
          INTERNAL_API_KEY   = "internal-api-key"
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

      dynamic "env" {
        for_each = contains(local.media_services, each.key) ? {
          MINIO_ACCESS_KEY = "minio-access-key"
          MINIO_SECRET_KEY = "minio-secret-key"
        } : {}
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

      dynamic "env" {
        for_each = contains(local.media_services, each.key) ? local.media_env_plain : {}
        content {
          name  = env.key
          value = env.value
        }
      }

      dynamic "env" {
        for_each = lookup(local.backend_static_env, each.key, {})
        content {
          name  = env.key
          value = env.value
        }
      }

      # Cross-service URLs — resolved here (per-instance, inside the resource
      # body) rather than in the for_each source, so referencing a sibling
      # instance of this same resource collection is a normal, non-circular
      # inter-instance dependency.
      dynamic "env" {
        for_each = lookup(local.backend_service_deps, each.key, {})
        content {
          name  = env.key
          value = google_cloud_run_v2_service.backend[env.value].uri
        }
      }

      startup_probe {
        http_get {
          path = "/health/live"
          port = each.value.port
        }
        initial_delay_seconds = 5
        period_seconds         = 5
        failure_threshold      = 10
      }

      liveness_probe {
        http_get {
          path = "/health/live"
          port = each.value.port
        }
        period_seconds = 15
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  depends_on = [
    google_secret_manager_secret_version.bootstrap,
    google_project_iam_member.run_sa_cloudsql,
  ]
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
resource "google_cloud_run_v2_service_iam_member" "backend_invoker" {
  for_each = local.backend_services
  name     = google_cloud_run_v2_service.backend[each.key].name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}

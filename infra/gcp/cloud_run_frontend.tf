# 4 website builds (apps/website/Dockerfile, ARG APP=portal|customer|kitchen|admin).
# Each is a static SPA served by nginx. The load balancer (load_balancer.tf) routes
# every /api/* path straight to the gateway NEG per-host, so these containers never
# need to proxy API calls themselves — nginx's own /api/ location (used only by
# local docker-compose) is simply unreached in production. Zero app code changes.

locals {
  frontend_services = {
    portal-web   = { app = "portal" }
    customer-web = { app = "customer" }
    kitchen-web  = { app = "kitchen" }
    admin-web    = { app = "admin" }
  }
}

resource "google_cloud_run_v2_service" "frontend" {
  for_each = local.frontend_services

  name     = "ckac-${each.key}"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"

  template {
    scaling {
      min_instance_count = var.frontend_min_instances
      max_instance_count = var.max_instances
    }

    containers {
      image = "${local.registry_prefix}/${each.key}:${var.image_tag}"

      ports {
        container_port = 80
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "256Mi"
        }
      }

      startup_probe {
        http_get {
          path = "/"
          port = 80
        }
        initial_delay_seconds = 3
        period_seconds          = 5
        failure_threshold       = 6
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
}

resource "google_cloud_run_v2_service_iam_member" "frontend_public_via_lb" {
  for_each = local.frontend_services
  name     = google_cloud_run_v2_service.frontend[each.key].name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}

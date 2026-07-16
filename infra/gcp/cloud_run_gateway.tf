# The gateway is the ONLY public edge (per services/gateway/app/main.py + the
# platform's "gateway edge only" rule). It's exposed exclusively through the
# global HTTPS load balancer (load_balancer.tf) — direct *.run.app access is
# blocked by ingress = INTERNAL_LOAD_BALANCER.

resource "google_cloud_run_v2_service" "gateway" {
  name     = "ckac-gateway"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"

  template {
    service_account = google_service_account.run_sa.email

    scaling {
      min_instance_count = var.gateway_min_instances
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
      image = "${local.registry_prefix}/gateway:${var.image_tag}"

      ports {
        container_port = 8000
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
      env {
        name = "CORS_ORIGINS"
        value = join(",", [
          "https://${var.domain_root}",
          "https://www.${var.domain_root}",
          "https://customer.${var.domain_root}",
          "https://kitchen.${var.domain_root}",
          "https://admin.${var.domain_root}",
        ])
      }

      env {
        name = "REDIS_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.bootstrap["redis-url"].secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "JWT_SECRET"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.bootstrap["jwt-secret"].secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "INTERNAL_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.bootstrap["internal-api-key"].secret_id
            version = "latest"
          }
        }
      }

      dynamic "env" {
        for_each = {
          IDENTITY_SERVICE_URL     = google_cloud_run_v2_service.backend["identity"].uri
          CATALOG_SERVICE_URL      = google_cloud_run_v2_service.backend["catalog"].uri
          ORDER_SERVICE_URL         = google_cloud_run_v2_service.backend["order"].uri
          BILLING_SERVICE_URL       = google_cloud_run_v2_service.backend["billing"].uri
          NOTIFICATION_SERVICE_URL  = google_cloud_run_v2_service.backend["notification"].uri
          MARKETING_SERVICE_URL     = google_cloud_run_v2_service.backend["marketing"].uri
          RATINGS_SERVICE_URL        = google_cloud_run_v2_service.backend["ratings"].uri
          GROWTH_SERVICE_URL         = google_cloud_run_v2_service.backend["growth"].uri
          DELIVERY_SERVICE_URL       = google_cloud_run_v2_service.backend["delivery"].uri
          LEARNING_SERVICE_URL       = google_cloud_run_v2_service.backend["learning"].uri
          COMMUNITY_SERVICE_URL      = google_cloud_run_v2_service.backend["community"].uri
          STREAMING_SERVICE_URL      = google_cloud_run_v2_service.backend["streaming"].uri
        }
        content {
          name  = env.key
          value = env.value
        }
      }

      startup_probe {
        http_get {
          path = "/health/live"
          port = 8000
        }
        initial_delay_seconds = 5
        period_seconds          = 5
        failure_threshold       = 10
      }

      liveness_probe {
        http_get {
          path = "/health/live"
          port = 8000
        }
        period_seconds = 15
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  depends_on = [google_cloud_run_v2_service.backend]
}

resource "google_cloud_run_v2_service_iam_member" "gateway_public_via_lb" {
  name     = google_cloud_run_v2_service.gateway.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}

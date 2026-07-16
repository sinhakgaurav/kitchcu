# Single global external HTTPS load balancer in front of every public Cloud Run
# service. This is the ONE public network entry point for the whole platform —
# gateway and the 4 websites all set ingress = INTERNAL_LOAD_BALANCER, so nothing
# is reachable except through here. Host-based + path-based routing replaces the
# nginx "/api/ proxy to gateway" used in local docker-compose (unreachable in prod,
# left untouched for local dev parity).

resource "google_compute_global_address" "lb_ip" {
  name = "ckac-lb-ip"
}

locals {
  neg_targets = merge(
    { gateway = google_cloud_run_v2_service.gateway.name },
    { for k, v in google_cloud_run_v2_service.frontend : k => v.name }
  )
}

resource "google_compute_region_network_endpoint_group" "neg" {
  for_each              = local.neg_targets
  name                  = "ckac-neg-${each.key}"
  region                = var.region
  network_endpoint_type = "SERVERLESS"

  cloud_run {
    service = each.value
  }
}

resource "google_compute_backend_service" "backend" {
  for_each              = local.neg_targets
  name                  = "ckac-backend-${each.key}"
  protocol              = "HTTPS"
  port_name             = "http"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  enable_cdn            = each.key == "gateway" ? false : true

  dynamic "cdn_policy" {
    for_each = each.key == "gateway" ? [] : [1]
    content {
      cache_mode  = "CACHE_ALL_STATIC"
      client_ttl  = 3600
      default_ttl = 3600
      max_ttl     = 86400
    }
  }

  backend {
    group = google_compute_region_network_endpoint_group.neg[each.key].id
  }

  log_config {
    enable      = true
    sample_rate = 1.0
  }
}

# --- URL map: host + path routing ---------------------------------------------

resource "google_compute_url_map" "https" {
  name            = "ckac-url-map"
  default_service = google_compute_backend_service.backend["gateway"].id

  host_rule {
    hosts        = ["api.${var.domain_root}"]
    path_matcher = "api-only"
  }
  path_matcher {
    name            = "api-only"
    default_service = google_compute_backend_service.backend["gateway"].id
  }

  host_rule {
    hosts        = [var.domain_root, "www.${var.domain_root}"]
    path_matcher = "portal"
  }
  path_matcher {
    name            = "portal"
    default_service = google_compute_backend_service.backend["portal-web"].id
    path_rule {
      paths   = ["/api/*"]
      service = google_compute_backend_service.backend["gateway"].id
    }
  }

  host_rule {
    hosts        = ["customer.${var.domain_root}"]
    path_matcher = "customer"
  }
  path_matcher {
    name            = "customer"
    default_service = google_compute_backend_service.backend["customer-web"].id
    path_rule {
      paths   = ["/api/*"]
      service = google_compute_backend_service.backend["gateway"].id
    }
  }

  host_rule {
    hosts        = ["kitchen.${var.domain_root}"]
    path_matcher = "kitchen"
  }
  path_matcher {
    name            = "kitchen"
    default_service = google_compute_backend_service.backend["kitchen-web"].id
    path_rule {
      paths   = ["/api/*"]
      service = google_compute_backend_service.backend["gateway"].id
    }
  }

  host_rule {
    hosts        = ["admin.${var.domain_root}"]
    path_matcher = "admin"
  }
  path_matcher {
    name            = "admin"
    default_service = google_compute_backend_service.backend["admin-web"].id
    path_rule {
      paths   = ["/api/*"]
      service = google_compute_backend_service.backend["gateway"].id
    }
  }
}

resource "google_compute_managed_ssl_certificate" "ckac" {
  name = "ckac-cert"

  managed {
    domains = [
      var.domain_root,
      "www.${var.domain_root}",
      "customer.${var.domain_root}",
      "kitchen.${var.domain_root}",
      "admin.${var.domain_root}",
      "api.${var.domain_root}",
    ]
  }
}

resource "google_compute_target_https_proxy" "https" {
  name             = "ckac-https-proxy"
  url_map          = google_compute_url_map.https.id
  ssl_certificates = [google_compute_managed_ssl_certificate.ckac.id]
}

resource "google_compute_global_forwarding_rule" "https" {
  name                  = "ckac-https-forwarding-rule"
  target                = google_compute_target_https_proxy.https.id
  port_range            = "443"
  ip_address            = google_compute_global_address.lb_ip.id
  load_balancing_scheme = "EXTERNAL_MANAGED"
}

# --- HTTP -> HTTPS redirect ----------------------------------------------------

resource "google_compute_url_map" "http_redirect" {
  name = "ckac-http-redirect"

  default_url_redirect {
    https_redirect         = true
    strip_query             = false
    redirect_response_code = "MOVED_PERMANENTLY_DEFAULT"
  }
}

resource "google_compute_target_http_proxy" "http" {
  name    = "ckac-http-proxy"
  url_map = google_compute_url_map.http_redirect.id
}

resource "google_compute_global_forwarding_rule" "http" {
  name                  = "ckac-http-forwarding-rule"
  target                = google_compute_target_http_proxy.http.id
  port_range            = "80"
  ip_address            = google_compute_global_address.lb_ip.id
  load_balancing_scheme = "EXTERNAL_MANAGED"
}

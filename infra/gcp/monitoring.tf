# Baseline observability — Cloud Run auto-ships stdout/stderr to Cloud Logging and
# request metrics to Cloud Monitoring already. This adds the one check that matters
# most on day one: is the public API up.

resource "google_monitoring_notification_channel" "email" {
  count        = var.alert_notification_email == "" ? 0 : 1
  display_name = "kitchCU on-call email"
  type          = "email"

  labels = {
    email_address = var.alert_notification_email
  }
}

resource "google_monitoring_uptime_check_config" "gateway_health" {
  display_name = "ckac-gateway-health-ready"
  timeout       = "10s"
  period        = "60s"

  http_check {
    path         = "/health/ready"
    port         = 443
    use_ssl      = true
    validate_ssl = true
  }

  monitored_resource {
    type = "uptime_url"
    labels = {
      project_id = var.project_id
      host       = "api.${var.domain_root}"
    }
  }
}

resource "google_monitoring_alert_policy" "gateway_down" {
  display_name = "kitchCU gateway /health/ready failing"
  combiner      = "OR"
  notification_channels = var.alert_notification_email == "" ? [] : [google_monitoring_notification_channel.email[0].id]

  conditions {
    display_name = "Uptime check failure"
    condition_threshold {
      filter          = "resource.type=\"uptime_url\" AND metric.type=\"monitoring.googleapis.com/uptime_check/check_passed\" AND metric.label.check_id=\"${google_monitoring_uptime_check_config.gateway_health.uptime_check_id}\""
      comparison       = "COMPARISON_LT"
      threshold_value  = 1
      duration          = "180s"
      aggregations {
        alignment_period     = "60s"
        cross_series_reducer = "REDUCE_COUNT_FALSE"
        per_series_aligner    = "ALIGN_NEXT_OLDER"
      }
    }
  }

  alert_strategy {
    auto_close = "1800s"
  }
}

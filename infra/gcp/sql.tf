# Cloud SQL for PostgreSQL 16 + PostGIS — single source of truth, schema-per-domain (ckac_<domain>).

resource "google_sql_database_instance" "postgres" {
  name             = "ckac-postgres-${var.environment}"
  database_version = "POSTGRES_16"
  region            = var.region

  depends_on = [google_service_networking_connection.private_vpc_connection]

  settings {
    tier              = var.db_tier
    availability_type = var.db_availability_type
    disk_size         = var.db_disk_size_gb
    disk_autoresize   = true
    disk_type         = "PD_SSD"

    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.vpc.id
    }

    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
      transaction_log_retention_days = 7
      backup_retention_settings {
        retained_backups = 14
      }
    }

    database_flags {
      name  = "cloudsql.enable_pgaudit"
      value = "off"
    }

    insights_config {
      query_insights_enabled = true
    }

    maintenance_window {
      day          = 7 # Sunday
      hour         = 3
      update_track = "stable"
    }
  }

  deletion_protection = true
}

# PostGIS/uuid-ossp are on Cloud SQL's allow-listed extension list but are NOT
# enabled by Terraform: the instance is private-IP-only (secure default) and
# is therefore unreachable from a laptop running `terraform apply`. This is a
# deliberate, documented manual step — see docs/DEPLOYMENT-GCP.md step 3b —
# run once via `gcloud sql connect` (which handles the Cloud SQL Auth Proxy
# for you, no network changes needed) right after this apply, before the
# first migration job runs.

resource "google_sql_database" "ckac" {
  name     = "ckac"
  instance = google_sql_database_instance.postgres.name
}

resource "google_sql_user" "ckac" {
  name     = "ckac"
  instance = google_sql_database_instance.postgres.name
  password = var.db_password
}

locals {
  database_url_asyncpg = "postgresql+asyncpg://ckac:${var.db_password}@${google_sql_database_instance.postgres.private_ip_address}:5432/ckac"
  database_url_sync    = "postgresql://ckac:${var.db_password}@${google_sql_database_instance.postgres.private_ip_address}:5432/ckac"
}

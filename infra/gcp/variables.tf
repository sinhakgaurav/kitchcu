variable "project_id" {
  description = "GCP project ID that hosts the kitchCU production stack."
  type        = string
}

variable "region" {
  description = "Primary GCP region. asia-south1 (Mumbai) is closest to kitchCU's India-first user base."
  type        = string
  default     = "asia-south1"
}

variable "environment" {
  description = "Environment label used in resource names/labels (production | staging)."
  type        = string
  default     = "production"
}

variable "domain_root" {
  description = "Root domain for the platform, e.g. kitchcu.in."
  type        = string
  default     = "kitchcu.in"
}

variable "image_tag" {
  description = "Container image tag deployed to Cloud Run. CI/CD overrides this per-deploy with the git SHA."
  type        = string
  default     = "latest"
}

variable "db_tier" {
  description = "Cloud SQL machine tier. db-custom-2-7680 = 2 vCPU / 7.5GB — resize later without app changes."
  type        = string
  default     = "db-custom-2-7680"
}

variable "db_disk_size_gb" {
  description = "Cloud SQL disk size in GB (autoresize is enabled, this is the floor)."
  type        = number
  default     = 20
}

variable "db_availability_type" {
  description = "ZONAL (cheaper, single-zone) or REGIONAL (HA standby, ~2x cost). Start ZONAL, upgrade before scale."
  type        = string
  default     = "ZONAL"
}

variable "redis_memory_gb" {
  description = "Memorystore Redis capacity in GB."
  type        = number
  default     = 1
}

variable "redis_tier" {
  description = "BASIC (single node, cheaper, no failover) or STANDARD_HA (replica + auto-failover)."
  type        = string
  default     = "BASIC"
}

variable "gateway_min_instances" {
  description = "Minimum warm Cloud Run instances for the public gateway (avoids cold start on the hot path)."
  type        = number
  default     = 1
}

variable "backend_min_instances" {
  description = "Minimum warm instances for internal backend services (0 = scale-to-zero, cheapest)."
  type        = number
  default     = 0
}

variable "frontend_min_instances" {
  description = "Minimum warm instances for the 4 website Cloud Run services."
  type        = number
  default     = 0
}

variable "max_instances" {
  description = "Per-service autoscale ceiling (safety cap against runaway billing / noisy-neighbor bugs)."
  type        = number
  default     = 20
}

variable "jwt_secret" {
  description = "Production JWT signing secret. Generate with: openssl rand -hex 32. NEVER commit the real value."
  type        = string
  sensitive   = true
}

variable "internal_api_key" {
  description = "Shared secret for service-to-service internal endpoints. Generate with: openssl rand -hex 32."
  type        = string
  sensitive   = true
}

variable "db_password" {
  description = "Cloud SQL 'ckac' application user password. Generate with: openssl rand -base64 24."
  type        = string
  sensitive   = true
}

variable "github_repository" {
  description = "GitHub 'owner/repo' allowed to federate via Workload Identity (e.g. sinhakgaurav/kitchcu)."
  type        = string
}

variable "alert_notification_email" {
  description = "Email address for Cloud Monitoring alert notifications (deploy/health alerts)."
  type        = string
  default     = ""
}

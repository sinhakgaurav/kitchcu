variable "service_key" {
  description = "Short service name, e.g. \"identity\" — used for image path and Cloud Run service name (ckac-<service_key>)."
  type        = string
}

variable "port" {
  type = number
}

variable "region" {
  type = string
}

variable "registry_prefix" {
  type = string
}

variable "image_tag" {
  type = string
}

variable "run_sa_email" {
  type = string
}

variable "network_id" {
  type = string
}

variable "subnetwork_id" {
  type = string
}

variable "min_instances" {
  type = number
}

variable "max_instances" {
  type = number
}

variable "secret_ids" {
  description = "Bootstrap Secret Manager secret_ids keyed by short name (database-url, redis-url, jwt-secret, internal-api-key, minio-access-key, minio-secret-key)."
  type        = map(string)
}

variable "is_media_service" {
  type    = bool
  default = false
}

variable "media_env_plain" {
  type    = map(string)
  default = {}
}

variable "static_env" {
  description = "Service-specific plain env vars that never change (no secrets, no cross-service URLs)."
  type        = map(string)
  default     = {}
}

variable "cross_service_env" {
  description = "ENV_VAR_NAME => already-resolved sibling Cloud Run service URL. Resolved by the caller (root module) so this module never has to reference its own resource address — that's what keeps multi-tier backend wiring cycle-free."
  type        = map(string)
  default     = {}
}

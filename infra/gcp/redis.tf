# Memorystore Redis — Streams for events (transactional outbox), active-menu / analytics cache.

resource "google_redis_instance" "cache" {
  name           = "ckac-redis-${var.environment}"
  tier           = var.redis_tier
  memory_size_gb = var.redis_memory_gb
  region         = var.region

  redis_version      = "REDIS_7_2"
  authorized_network = google_compute_network.vpc.id
  connect_mode        = "PRIVATE_SERVICE_ACCESS"

  depends_on = [google_service_networking_connection.private_vpc_connection]
}

locals {
  redis_url = "redis://${google_redis_instance.cache.host}:${google_redis_instance.cache.port}/0"
}

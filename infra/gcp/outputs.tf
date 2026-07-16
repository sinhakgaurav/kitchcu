output "load_balancer_ip" {
  description = "Add DNS A records at your registrar pointing every hostname below at this IP."
  value       = google_compute_global_address.lb_ip.address
}

output "dns_records_to_create" {
  description = "Exact DNS records to add (A record, all pointing at load_balancer_ip)."
  value = [
    var.domain_root,
    "www.${var.domain_root}",
    "customer.${var.domain_root}",
    "kitchen.${var.domain_root}",
    "admin.${var.domain_root}",
    "api.${var.domain_root}",
  ]
}

output "artifact_registry_repo" {
  value = local.registry_prefix
}

output "cloud_sql_connection_name" {
  value = google_sql_database_instance.postgres.connection_name
}

output "cloud_sql_private_ip" {
  value = google_sql_database_instance.postgres.private_ip_address
}

output "redis_host" {
  value = google_redis_instance.cache.host
}

output "media_bucket" {
  value = google_storage_bucket.media.name
}

output "workload_identity_provider" {
  description = "Set as GitHub secret GCP_WORKLOAD_IDENTITY_PROVIDER for the deploy-gcp.yml workflow."
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "deployer_service_account" {
  description = "Set as GitHub secret GCP_DEPLOYER_SA for the deploy-gcp.yml workflow."
  value       = google_service_account.deployer_sa.email
}

output "backend_service_urls" {
  value = { for k, v in google_cloud_run_v2_service.backend : k => v.uri }
}

output "gateway_url_internal" {
  description = "Cloud Run-assigned URL — NOT publicly reachable (ingress = internal load balancer). Use the domains above."
  value       = google_cloud_run_v2_service.gateway.uri
}

# 12 internal domain services — never public. Only reachable from the gateway /
# other Cloud Run services in this project, or via the load balancer for the
# gateway itself. This mirrors the existing "gateway is the only public edge"
# rule enforced in services/gateway/app/main.py — zero application code changes.
#
# Split into 3 dependency tiers (see modules/backend_service/main.tf for why):
# tier0 has no cross-service env vars; tier1 depends only on tier0; tier2
# depends on tier0 and/or tier1. Each tier is a distinct module call block, so
# tier1/tier2 can reference tier0/tier1 module outputs without Terraform
# treating it as a resource self-reference cycle.

locals {
  media_services = toset(["identity", "catalog", "billing"])

  backend_tier0 = {
    identity  = { port = 8001 }
    catalog   = { port = 8002 }
    order     = { port = 8003 }
    marketing = { port = 8006 }
    ratings   = { port = 8007 }
    delivery  = { port = 8009 }
    community = { port = 8011 }
    streaming = { port = 8012 }
  }

  # Depends only on tier0.
  backend_tier1 = {
    billing      = { port = 8004 }
    notification = { port = 8005 }
  }

  # Depends on tier0 and/or tier1.
  backend_tier2 = {
    growth   = { port = 8008 }
    learning = { port = 8010 }
  }

  # Single source of truth for ports/migrations — never used as a for_each
  # source for the Cloud Run services themselves (that's tier0/1/2 above).
  backend_services = merge(local.backend_tier0, local.backend_tier1, local.backend_tier2)

  # Static (non-cross-service) extra env vars per service.
  backend_static_env = {
    notification = { WHATSAPP_VERIFY_TOKEN = "REPLACE-VIA-SUPER-ADMIN-CONTROL" } # bootstrap only — DB value in Super Admin -> Control takes precedence
    community    = { COMMUNITY_MIN_ORDERS_RANKING = "3" }
  }

  # Cross-service dependency wiring: service_key => { ENV_VAR_NAME = <other backend_services key> }.
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

  bootstrap_secret_ids = { for k, s in google_secret_manager_secret.bootstrap : k => s.secret_id }

  # Services with an alembic/ dir — see cloud_run_jobs.tf. Kept as a single
  # source of truth alongside backend_services so job + service definitions
  # can't drift.
  services_with_migrations = keys(local.backend_services)
}

module "backend_tier0" {
  for_each = local.backend_tier0
  source   = "./modules/backend_service"

  service_key      = each.key
  port             = each.value.port
  region           = var.region
  registry_prefix  = local.registry_prefix
  image_tag        = var.image_tag
  run_sa_email     = google_service_account.run_sa.email
  network_id       = google_compute_network.vpc.id
  subnetwork_id    = google_compute_subnetwork.run_subnet.id
  min_instances    = var.backend_min_instances
  max_instances    = var.max_instances
  secret_ids       = local.bootstrap_secret_ids
  is_media_service = contains(local.media_services, each.key)
  media_env_plain  = local.media_env_plain
  static_env       = lookup(local.backend_static_env, each.key, {})

  depends_on = [
    google_secret_manager_secret_version.bootstrap,
    google_project_iam_member.run_sa_cloudsql,
  ]
}

module "backend_tier1" {
  for_each = local.backend_tier1
  source   = "./modules/backend_service"

  service_key      = each.key
  port             = each.value.port
  region           = var.region
  registry_prefix  = local.registry_prefix
  image_tag        = var.image_tag
  run_sa_email     = google_service_account.run_sa.email
  network_id       = google_compute_network.vpc.id
  subnetwork_id    = google_compute_subnetwork.run_subnet.id
  min_instances    = var.backend_min_instances
  max_instances    = var.max_instances
  secret_ids       = local.bootstrap_secret_ids
  is_media_service = contains(local.media_services, each.key)
  media_env_plain  = local.media_env_plain
  static_env       = lookup(local.backend_static_env, each.key, {})

  cross_service_env = {
    for env_name, dep_key in lookup(local.backend_service_deps, each.key, {}) :
    env_name => module.backend_tier0[dep_key].uri
  }

  depends_on = [
    google_secret_manager_secret_version.bootstrap,
    google_project_iam_member.run_sa_cloudsql,
  ]
}

module "backend_tier2" {
  for_each = local.backend_tier2
  source   = "./modules/backend_service"

  service_key      = each.key
  port             = each.value.port
  region           = var.region
  registry_prefix  = local.registry_prefix
  image_tag        = var.image_tag
  run_sa_email     = google_service_account.run_sa.email
  network_id       = google_compute_network.vpc.id
  subnetwork_id    = google_compute_subnetwork.run_subnet.id
  min_instances    = var.backend_min_instances
  max_instances    = var.max_instances
  secret_ids       = local.bootstrap_secret_ids
  is_media_service = contains(local.media_services, each.key)
  media_env_plain  = local.media_env_plain
  static_env       = lookup(local.backend_static_env, each.key, {})

  # dep_key is always in tier0 or tier1 (never tier2 — no tier2-to-tier2 deps
  # exist today; if that ever changes, add a tier3).
  cross_service_env = {
    for env_name, dep_key in lookup(local.backend_service_deps, each.key, {}) :
    env_name => (
      contains(keys(local.backend_tier0), dep_key)
      ? module.backend_tier0[dep_key].uri
      : module.backend_tier1[dep_key].uri
    )
  }

  depends_on = [
    google_secret_manager_secret_version.bootstrap,
    google_project_iam_member.run_sa_cloudsql,
  ]
}

locals {
  # Flat, tier-agnostic lookup used by the gateway, migration jobs, and
  # outputs — so nothing outside this file needs to know which tier a given
  # service lives in.
  backend_uris = merge(
    { for k, m in module.backend_tier0 : k => m.uri },
    { for k, m in module.backend_tier1 : k => m.uri },
    { for k, m in module.backend_tier2 : k => m.uri },
  )

  backend_names = merge(
    { for k, m in module.backend_tier0 : k => m.name },
    { for k, m in module.backend_tier1 : k => m.name },
    { for k, m in module.backend_tier2 : k => m.name },
  )
}

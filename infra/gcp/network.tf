# VPC for Cloud Run <-> Cloud SQL (private IP) + Memorystore Redis connectivity.
# Cloud Run reaches this VPC via Direct VPC egress (no separate connector VM needed).

resource "google_compute_network" "vpc" {
  name                    = "ckac-vpc"
  auto_create_subnetworks = false
  depends_on              = [google_project_service.apis]
}

resource "google_compute_subnetwork" "run_subnet" {
  name          = "ckac-run-subnet"
  ip_cidr_range = "10.10.0.0/24"
  region        = var.region
  network       = google_compute_network.vpc.id
}

# Private Service Access range for Cloud SQL + Memorystore private IPs.
resource "google_compute_global_address" "private_service_range" {
  name          = "ckac-private-service-range"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 20
  network       = google_compute_network.vpc.id
}

resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_service_range.name]
  depends_on              = [google_project_service.apis]
}

# Intra-subnet safety net (Cloud SQL/Redis reachability via Private Service Access
# peering is governed by Google's managed producer-side rules, not this firewall —
# this just allows Cloud Run direct-VPC-egress endpoints to reach each other).
resource "google_compute_firewall" "allow_internal" {
  name    = "ckac-allow-internal"
  network = google_compute_network.vpc.id

  allow {
    protocol = "tcp"
  }
  allow {
    protocol = "udp"
  }
  allow {
    protocol = "icmp"
  }

  source_ranges = ["10.10.0.0/24"]
}

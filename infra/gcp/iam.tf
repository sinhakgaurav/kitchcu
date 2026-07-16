# Runtime service account — used by every Cloud Run service/job.
resource "google_service_account" "run_sa" {
  account_id   = "ckac-run"
  display_name = "kitchCU Cloud Run runtime"
}

resource "google_project_iam_member" "run_sa_cloudsql" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.run_sa.email}"
}

resource "google_secret_manager_secret_iam_member" "run_sa_secret_access" {
  for_each  = google_secret_manager_secret.bootstrap
  secret_id = each.value.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.run_sa.email}"
}

resource "google_storage_bucket_iam_member" "run_sa_media_admin" {
  bucket = google_storage_bucket.media.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.run_sa.email}"
}

# --- CI/CD: GitHub Actions deploys via Workload Identity Federation (no JSON keys) ---

resource "google_service_account" "deployer_sa" {
  account_id   = "ckac-deployer"
  display_name = "kitchCU GitHub Actions deployer"
}

resource "google_project_iam_member" "deployer_run_admin" {
  project = var.project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${google_service_account.deployer_sa.email}"
}

resource "google_project_iam_member" "deployer_artifact_writer" {
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${google_service_account.deployer_sa.email}"
}

resource "google_service_account_iam_member" "deployer_act_as_run_sa" {
  service_account_id = google_service_account.run_sa.name
  role                = "roles/iam.serviceAccountUser"
  member              = "serviceAccount:${google_service_account.deployer_sa.email}"
}

resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "ckac-github-pool"
  display_name              = "kitchCU GitHub Actions"
}

resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "ckac-github-provider"
  display_name                       = "GitHub OIDC"

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
    "attribute.ref"        = "assertion.ref"
  }
  attribute_condition = "assertion.repository == \"${var.github_repository}\""

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

resource "google_service_account_iam_member" "github_wif_binding" {
  service_account_id = google_service_account.deployer_sa.name
  role                = "roles/iam.workloadIdentityUser"
  member              = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_repository}"
}

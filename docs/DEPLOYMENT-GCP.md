# kitchCU — GCP Production Deployment Runbook

**Owner posture:** this is a production go-live for a multi-tenant payments platform.
Read this whole doc before running anything. Terraform in `infra/gcp/` provisions
real, billable GCP resources.

## 0. What gets built

| Layer | GCP resource | Notes |
|---|---|---|
| Compute | 17 Cloud Run v2 services (13 backend + gateway, 4 websites) | Region `asia-south1` by default |
| DB | Cloud SQL Postgres 16, private IP | PostGIS + uuid-ossp enabled |
| Cache/Events | Memorystore Redis, private IP | Basic tier by default |
| Media | GCS bucket, S3-interop HMAC keys | Zero code changes to `MinioMediaStorage` |
| Images | Artifact Registry (`ckac` repo) | Built + pushed by GitHub Actions |
| Networking | VPC + Direct VPC egress, Private Service Access | Cloud Run ↔ Cloud SQL/Redis |
| Edge | Global external HTTPS LB, Google-managed cert, 6 hostnames | The **only** public entry point |
| Secrets | Secret Manager (`ckac-database-url`, `ckac-redis-url`, `ckac-jwt-secret`, `ckac-internal-api-key`, `ckac-minio-*`) | Third-party keys (Razorpay/Meta/LiveKit/OAuth) stay DB-backed via Super Admin → Control, **not** here |
| CI/CD | GitHub Actions `deploy-gcp.yml`, Workload Identity Federation | No service-account JSON key ever leaves GCP |
| Observability | Uptime check + alert policy on `/health/ready` | Cloud Logging/Monitoring auto-capture the rest |

**Security posture (read this):** only `ckac-gateway` and the 4 website services are
publicly reachable, and only through the load balancer (`ingress = INTERNAL_LOAD_BALANCER`).
The 12 domain services are `ingress = INTERNAL_ONLY` — unreachable from the public
internet regardless of IAM. Cloud Run's per-call IAM invoker check is left open
(`allUsers`) on those internal services specifically so the gateway's existing
plain `httpx` calls keep working with **zero application code changes**; the network
ingress restriction is the real boundary here, not IAM. Fast-follow: mint Google
ID tokens in the gateway's httpx clients and lock down `roles/run.invoker` per
caller service account for defense-in-depth.

## 1. One-time prerequisites

1. **GCP project + billing** — create a project, link a billing account.
   ```bash
   gcloud projects create YOUR_PROJECT_ID
   gcloud billing projects link YOUR_PROJECT_ID --billing-account=BILLING_ACCOUNT_ID
   gcloud config set project YOUR_PROJECT_ID
   ```
2. **Install locally**: `gcloud` CLI, `terraform` >= 1.7, Docker (for local image builds if you don't want to wait for CI on first deploy).
3. **Auth**: `gcloud auth login && gcloud auth application-default login`
4. **Terraform state bucket** (recommended — keeps state off your laptop):
   ```bash
   gsutil mb -l asia-south1 gs://YOUR_PROJECT_ID-tfstate
   gsutil versioning set on gs://YOUR_PROJECT_ID-tfstate
   ```
   Then uncomment the `backend "gcs"` block in `infra/gcp/versions.tf` with that bucket name, and run `terraform init` again after the first apply.

## 2. Generate secrets

```bash
openssl rand -hex 32     # JWT_SECRET
openssl rand -hex 32     # INTERNAL_API_KEY
openssl rand -base64 24  # DB_PASSWORD
```

Copy `infra/gcp/terraform.tfvars.example` → `infra/gcp/terraform.tfvars`, fill in
`project_id`, `github_repository` (`owner/repo`), and the three secrets above.
**Never commit `terraform.tfvars`** (already gitignored).

## 3. Apply infrastructure

```bash
cd infra/gcp
terraform init
terraform plan   # review every resource before applying — this is real spend
terraform apply
```

First apply takes ~15-25 minutes (Cloud SQL + Redis + LB provisioning are the slow parts).

Note the outputs: `load_balancer_ip`, `workload_identity_provider`, `deployer_service_account`.

### 3b. Enable PostGIS (one-time, manual — Cloud SQL is private-IP-only by design)

Cloud SQL has no public IP, so your laptop can't reach it directly — use
`gcloud sql connect`, which tunnels through the Cloud SQL Auth Proxy for you
(no VPC/firewall changes needed):

```bash
gcloud sql connect ckac-postgres-production --user=ckac --database=ckac
# Enter the db_password from your terraform.tfvars when prompted
```

At the `ckac=>` prompt:

```sql
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
\q
```

Do this **before** the first migration run (step 6) — several migrations use
PostGIS `GEOGRAPHY` columns and `uuid_generate_v4()`.

## 4. Point DNS at the load balancer

At your DNS provider (you control `kitchcu.in` DNS per your own setup), add **A
records** for every host in `terraform output dns_records_to_create`, all pointing
at `terraform output load_balancer_ip`:

| Host | Type | Value |
|---|---|---|
| `kitchcu.in` | A | `<load_balancer_ip>` |
| `www.kitchcu.in` | A | `<load_balancer_ip>` |
| `customer.kitchcu.in` | A | `<load_balancer_ip>` |
| `kitchen.kitchcu.in` | A | `<load_balancer_ip>` |
| `admin.kitchcu.in` | A | `<load_balancer_ip>` |
| `api.kitchcu.in` | A | `<load_balancer_ip>` |

The Google-managed SSL certificate (`ckac-cert`) only starts provisioning once DNS
resolves to the LB IP, and can take up to ~60 minutes. Check status:

```bash
gcloud compute ssl-certificates describe ckac-cert --global --format="value(managed.status, managed.domainStatus)"
```

Until it's `ACTIVE`, HTTPS requests to these hostnames will fail/warn — that's expected.

## 5. Wire up GitHub Actions

Add these **repository secrets** (Settings → Secrets and variables → Actions):

| Secret | Value |
|---|---|
| `GCP_PROJECT_ID` | your project id |
| `GCP_REGION` | `asia-south1` (or whatever you set) |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | `terraform output workload_identity_provider` |
| `GCP_DEPLOYER_SA` | `terraform output deployer_service_account` |

Add this **repository variable**:

| Variable | Value |
|---|---|
| `DOMAIN_ROOT` | `kitchcu.in` |

## 6. First deploy

The workflow is manual-trigger by design (`workflow_dispatch`) — go-live is a
deliberate action. From the GitHub UI: Actions → **Deploy to GCP (Cloud Run)** →
Run workflow. It will:

1. Build + push all 13 backend/gateway images and 4 website images to Artifact Registry
2. Run every service's `alembic upgrade head` as a Cloud Run Job (fail-fast, sequential)
3. Deploy backend services, then gateway, then websites
4. Smoke-test `https://api.kitchcu.in/health/ready`

## 7. Populate runtime secrets (post-deploy, in-app)

Log in as Super Admin (`admin@kitchcu.dev` bootstrap, **change this immediately**
via the identity service admin user table) → **Control → API Keys**, and set:

- `razorpay_key_id`, `razorpay_key_secret`, `razorpay_webhook_secret` — live Razorpay keys
- `whatsapp_verify_token`, `whatsapp_app_secret` — from Meta App dashboard
- `livekit_url`, `livekit_api_key`, `livekit_api_secret` — if enabling live streaming
- `google_maps_api_key` — for delivery tracking map embeds
- OAuth client id/secrets — for customer social login

These are DB-backed (encrypted with `JWT_SECRET`) and take effect immediately, no
redeploy needed. The Terraform-managed `WHATSAPP_VERIFY_TOKEN` env var is a
throwaway bootstrap placeholder — the DB value above takes precedence per
`get_platform_secret()`.

**Change the default admin password and demo OTP behavior before real traffic**:
`allows_fixed_dev_otp()` is already gated to `development`/`test` — confirm
`APP_ENV=production` is set everywhere (it is, via Terraform) so OTP `123456` is refused in prod.

## 8. Rollback

Every deploy is tagged with the git short SHA. To roll back a bad deploy:

```bash
gcloud run services update-traffic ckac-gateway --region asia-south1 \
  --to-revisions=ckac-gateway-<previous-good-revision>=100
```

Repeat per affected service. Cloud Run keeps prior revisions indefinitely by default
(subject to Cloud Run's revision retention), so this is a fast, zero-downtime revert.
**Database migrations are not automatically reversible** — check the specific
Alembic migration's `downgrade()` before rolling back a release that shipped one.

## 9. Known gaps / fast-follows (don't block go-live, do track)

| Gap | Risk | Fix |
|---|---|---|
| Backend services allow unauthenticated Cloud Run invocation (network-only boundary) | Low — internal ingress blocks all public access anyway | Add ID-token auth in gateway's httpx clients |
| Media bucket is public-read | Matches existing MinIO dev/prod behavior, not a regression | Move to signed URLs per `kitchcu-security-observability.mdc` |
| Cloud SQL is `ZONAL` (no HA standby) | Single-zone outage = downtime until manual failover | Switch `db_availability_type = "REGIONAL"` before serious traffic |
| Redis is `BASIC` tier (no replica) | Redis restart loses Streams outbox buffer (DB outbox is durable; Redis is the delivery layer) | Switch `redis_tier = "STANDARD_HA"` |
| No load test yet at 100k concurrent sessions | Unknown real capacity | Run k6/Locust against staging before marketing push |
| `deploy-gcp.yml` is manual-trigger only | No accidental prod deploys, but no auto-deploy either | Flip to `on: push` once confidence is high |

## 10. Cost estimate (rough, `asia-south1`, minimums)

- Cloud SQL `db-custom-2-7680` ZONAL: ~$120-150/mo
- Memorystore Redis 1GB BASIC: ~$35/mo
- Cloud Run (mostly scale-to-zero, gateway min=1): ~$20-60/mo at low traffic
- Load Balancer + CDN: ~$20-30/mo + egress
- Artifact Registry + GCS: <$5/mo at this scale

**Estimate: ~$200-280/mo at near-zero traffic**, scaling with Cloud Run request volume
and Cloud SQL/Redis tier upgrades as usage grows.

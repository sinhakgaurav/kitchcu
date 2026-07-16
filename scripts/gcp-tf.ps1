<#
.SYNOPSIS
  Run infra/gcp Terraform via Docker — no local Terraform install needed.

.DESCRIPTION
  Wraps `docker run hashicorp/terraform:1.9` with the working directory and
  gcloud credential mounts already needed for infra/gcp. This is the exact
  image used to verify the tiered backend_service module has no dependency
  cycle (init / validate / graph -type=plan all passed against it) — this
  script extends the same approach to plan/apply/output against the real
  "kitchcu" GCP project, replacing the Cloud Shell workflow.

  One-time setup (no local gcloud install required):
    .\scripts\gcp-auth.ps1

  infra/gcp/terraform.tfvars (gitignored — see terraform.tfvars.example) must
  exist with real values before `plan`/`apply` will succeed.

.EXAMPLE
  .\scripts\gcp-tf.ps1 init -upgrade
  .\scripts\gcp-tf.ps1 plan
  .\scripts\gcp-tf.ps1 apply
  .\scripts\gcp-tf.ps1 output backend_service_urls
#>
param(
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$TfArgs
)

$ErrorActionPreference = "Stop"

if (-not $TfArgs -or $TfArgs.Count -eq 0) {
  Write-Host "Usage: .\scripts\gcp-tf.ps1 <terraform-command> [args...]" -ForegroundColor Yellow
  Write-Host "Examples: init | init -upgrade | plan | apply | output | destroy" -ForegroundColor Yellow
  exit 1
}

$gcpDir = (Resolve-Path (Join-Path $PSScriptRoot "..\infra\gcp")).Path
$gcloudConfigDir = Join-Path $env:APPDATA "gcloud"
$adcFile = Join-Path $gcloudConfigDir "application_default_credentials.json"

if (-not (Test-Path $adcFile)) {
  Write-Host "No Application Default Credentials found at $adcFile." -ForegroundColor Yellow
  Write-Host "Run .\scripts\gcp-auth.ps1 first (one-time, no local gcloud install needed)." -ForegroundColor Yellow
  exit 1
}

$dockerArgs = @(
  "run", "--rm", "-it",
  "-v", "${gcpDir}:/workspace",
  "-v", "${gcloudConfigDir}:/root/.config/gcloud",
  "-w", "/workspace",
  "-e", "GOOGLE_APPLICATION_CREDENTIALS=/root/.config/gcloud/application_default_credentials.json"
) + @("hashicorp/terraform:1.9") + $TfArgs

& docker @dockerArgs
exit $LASTEXITCODE

<#
.SYNOPSIS
  Run one-off gcloud commands via Docker — no local gcloud install needed.

.DESCRIPTION
  Companion to scripts/gcp-tf.ps1 for things Terraform doesn't do for you
  (checking service status, tailing logs, listing revisions, etc). Uses the
  same %APPDATA%\gcloud credential mount, so run scripts/gcp-auth.ps1 first.

  NOTE: commands that need a database client on the PATH (e.g.
  `gcloud sql connect` for the one-time manual "CREATE EXTENSION postgis"
  step in docs/DEPLOYMENT-GCP.md) do NOT work through this wrapper — the
  google/cloud-sdk image has no psql binary. Use Cloud Shell for that one
  specific step, or `docker run --rm -it postgres:16 psql ...` through the
  Cloud SQL Auth Proxy if you want to stay fully local.

.EXAMPLE
  .\scripts\gcp-cli.ps1 config set project kitchcu
  .\scripts\gcp-cli.ps1 run services list --region=asia-south1
  .\scripts\gcp-cli.ps1 run services logs read ckac-gateway --region=asia-south1 --limit=50
#>
param(
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$GcloudArgs
)

$ErrorActionPreference = "Stop"

if (-not $GcloudArgs -or $GcloudArgs.Count -eq 0) {
  Write-Host "Usage: .\scripts\gcp-cli.ps1 <gcloud-args...>" -ForegroundColor Yellow
  exit 1
}

$gcloudConfigDir = Join-Path $env:APPDATA "gcloud"
$adcFile = Join-Path $gcloudConfigDir "application_default_credentials.json"

if (-not (Test-Path $adcFile)) {
  Write-Host "No credentials found. Run .\scripts\gcp-auth.ps1 first." -ForegroundColor Yellow
  exit 1
}

$dockerArgs = @(
  "run", "--rm", "-it",
  "-v", "${gcloudConfigDir}:/root/.config/gcloud",
  "google/cloud-sdk:slim",
  "gcloud"
) + $GcloudArgs

& docker @dockerArgs
exit $LASTEXITCODE

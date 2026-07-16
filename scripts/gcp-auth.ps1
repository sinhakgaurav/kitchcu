<#
.SYNOPSIS
  One-time GCP login for the Docker-based Terraform workflow (scripts/gcp-tf.ps1)
  — no local gcloud install needed.

.DESCRIPTION
  Runs `gcloud auth application-default login` inside the official
  google/cloud-sdk container and persists the resulting Application Default
  Credentials (ADC) to %APPDATA%\gcloud on the host. scripts/gcp-tf.ps1 mounts
  that same folder into the Terraform container on every later run, so the
  google provider authenticates exactly like it would in Cloud Shell.

  Re-run this whenever the token expires (ADC refresh tokens are long-lived,
  but if `gcp-tf.ps1 plan` starts failing with a credentials error, run this
  again).

.EXAMPLE
  .\scripts\gcp-auth.ps1
#>

$ErrorActionPreference = "Stop"

$gcloudConfigDir = Join-Path $env:APPDATA "gcloud"
New-Item -ItemType Directory -Force -Path $gcloudConfigDir | Out-Null

Write-Host "This will print a URL." -ForegroundColor Cyan
Write-Host "Open it in any browser, sign in with the Google account that owns the 'kitchcu' project, and paste the resulting code back here." -ForegroundColor Cyan
Write-Host ""

docker run --rm -it -v "${gcloudConfigDir}:/root/.config/gcloud" google/cloud-sdk:slim gcloud auth application-default login --no-launch-browser

if ($LASTEXITCODE -eq 0) {
  Write-Host ""
  Write-Host "Done. Credentials saved to $gcloudConfigDir\application_default_credentials.json" -ForegroundColor Green
  Write-Host "You can now run: .\scripts\gcp-tf.ps1 init" -ForegroundColor Green
}

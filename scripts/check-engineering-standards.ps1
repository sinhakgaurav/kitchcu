# Fail CI-local checks for kitchCU engineering standards (Phase 1).

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$failed = $false

Write-Host "kitchCU engineering standards check" -ForegroundColor Cyan

# 1. No TODO/FIXME in production Python (exclude tests)
$todoPattern = '(TODO|FIXME|HACK|XXX)\b'
$pyPaths = @(
    "$root\services\*\app\*.py",
    "$root\packages\ckac-common\ckac_common\*.py"
)
foreach ($glob in $pyPaths) {
    Get-ChildItem -Path $glob -ErrorAction SilentlyContinue | ForEach-Object {
        $matches = Select-String -Path $_.FullName -Pattern $todoPattern
        if ($matches) {
            $failed = $true
            Write-Host "FAIL: TODO/FIXME in $($_.FullName)" -ForegroundColor Red
            $matches | ForEach-Object { Write-Host "  $($_.LineNumber): $($_.Line.Trim())" }
        }
    }
}

# 2. Required docs exist
$requiredDocs = @(
    "$root\AGENTS.md",
    "$root\docs\KITCHCU-ENGINEERING-STANDARDS.md",
    "$root\docs\templates\MODULE-DESIGN-PACK.md"
)
foreach ($doc in $requiredDocs) {
    if (-not (Test-Path $doc)) {
        $failed = $true
        Write-Host "FAIL: Missing required doc $doc" -ForegroundColor Red
    }
}

# 3. Cursor rules present
$rules = @(
    "ckac-agent-spec.mdc",
    "ckac-tdd-edd.mdc",
    "ckac-backend.mdc",
    "ckac-frontend.mdc",
    "kitchcu-security-observability.mdc"
)
foreach ($rule in $rules) {
    $path = Join-Path $root ".cursor\rules\$rule"
    if (-not (Test-Path $path)) {
        $failed = $true
        Write-Host "FAIL: Missing Cursor rule $rule" -ForegroundColor Red
    }
}

if ($failed) {
    Write-Host "`nStandards check FAILED" -ForegroundColor Red
    exit 1
}

Write-Host "`nStandards check PASSED" -ForegroundColor Green
exit 0

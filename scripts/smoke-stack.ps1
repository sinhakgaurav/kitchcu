# Post-deploy smoke checks - gateway, PWAs, public menu API
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$gateway = if ($env:CKAC_GATEWAY_URL) { $env:CKAC_GATEWAY_URL } else { "http://localhost:18000" }
$customer = if ($env:CKAC_CUSTOMER_URL) { $env:CKAC_CUSTOMER_URL } else { "http://localhost:13001" }
$kitchen = if ($env:CKAC_KITCHEN_URL) { $env:CKAC_KITCHEN_URL } else { "http://localhost:13002" }
$admin = if ($env:CKAC_ADMIN_URL) { $env:CKAC_ADMIN_URL } else { "http://localhost:13003" }
$demoKitchenId = if ($env:CKAC_DEMO_KITCHEN_ID) { $env:CKAC_DEMO_KITCHEN_ID } else { "" }
$demoKitchenCode = if ($env:CKAC_DEMO_KITCHEN_CODE) { $env:CKAC_DEMO_KITCHEN_CODE } else { "CKPNQ001" }

function Resolve-DemoKitchenId {
    param([string]$Gateway, [string]$Code, [string]$FallbackId)
    if ($FallbackId) { return $FallbackId }
    try {
        $json = Invoke-RestMethod -Uri "$Gateway/api/v1/kitchens/public/by-code/$Code" -TimeoutSec 20
        if ($json.id) { return [string]$json.id }
    } catch {
        Write-Host "WARN resolve kitchen $Code - $($_.Exception.Message)" -ForegroundColor Yellow
    }
    return $null
}

function Test-HttpStatus {
    param([string]$Name, [string]$Url, [int]$Expected = 200)
    try {
        $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 30
        if ($resp.StatusCode -ne $Expected) {
            Write-Host "FAIL $Name - $($resp.StatusCode) (expected $Expected)" -ForegroundColor Red
            return $false
        }
        Write-Host "OK   $Name - $Expected" -ForegroundColor Green
        return $true
    } catch {
        Write-Host "FAIL $Name - $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

function Test-PublicMenu {
    param([string]$Name, [string]$Url)
    try {
        $json = Invoke-RestMethod -Uri $Url -TimeoutSec 30
        if (-not ($json.dishes -is [array]) -or $json.dishes.Count -le 0) {
            Write-Host "FAIL $Name - dishes empty" -ForegroundColor Red
            return $false
        }
        Write-Host "OK   $Name - $($json.dishes.Count) dishes" -ForegroundColor Green
        return $true
    } catch {
        Write-Host "FAIL $Name - $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

function Test-NearbyKitchens {
    param([string]$Name, [string]$Url)
    try {
        $json = Invoke-RestMethod -Uri $Url -TimeoutSec 30
        if (-not ($json.kitchens -is [array])) {
            Write-Host "FAIL $Name - kitchens field missing" -ForegroundColor Red
            return $false
        }
        Write-Host "OK   $Name - $($json.kitchens.Count) kitchens" -ForegroundColor Green
        return $true
    } catch {
        Write-Host "FAIL $Name - $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

Write-Host ""
Write-Host "KitchCu stack smoke test" -ForegroundColor Cyan
Write-Host "Gateway: $gateway"
Write-Host ""

$ok = $true
$ok = (Test-HttpStatus "Gateway live" "$gateway/health/live") -and $ok
$ok = (Test-HttpStatus "Gateway ready" "$gateway/health/ready") -and $ok
$ok = (Test-HttpStatus "Customer PWA" $customer) -and $ok
$ok = (Test-HttpStatus "Kitchen PWA" $kitchen) -and $ok
$ok = (Test-HttpStatus "Admin PWA" $admin) -and $ok

$resolvedKitchenId = Resolve-DemoKitchenId -Gateway $gateway -Code $demoKitchenCode -FallbackId $demoKitchenId
if (-not $resolvedKitchenId) {
    Write-Host "FAIL Public menu API - could not resolve kitchen $demoKitchenCode" -ForegroundColor Red
    $ok = $false
} else {
    Write-Host "Demo kitchen: $demoKitchenCode -> $resolvedKitchenId"
    $ok = (Test-PublicMenu "Public menu API" "$gateway/api/v1/kitchens/$resolvedKitchenId/menu") -and $ok
}
$nearbyUrl = '{0}/api/v1/kitchens/public/nearby?latitude=18.52&longitude=73.85&limit=3' -f $gateway
$ok = (Test-NearbyKitchens "Nearby kitchens API" $nearbyUrl) -and $ok

if ($ok) {
    Write-Host ""
    Write-Host "All smoke checks passed." -ForegroundColor Green
    exit 0
}

Write-Host ""
Write-Host "Smoke checks failed." -ForegroundColor Red
exit 1

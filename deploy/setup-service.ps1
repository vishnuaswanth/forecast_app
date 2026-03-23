#Requires -RunAsAdministrator
# Sets NSSM service environment variables and restarts the CenteneForecasting service.
# Run this after the service is already registered via register-service.ps1.

# =============================================================================
# CONFIGURE THESE VALUES
# =============================================================================

$NssmPath    = "C:\nssm.exe"
$ServiceName = "CenteneForecasting"

$EnvVars = @{
    "DJANGO_SETTINGS_MODULE"    = "centene_forecast_project.settings"
    "SECRET_KEY"                = "REPLACE_WITH_YOUR_SECRET_KEY"
    "DEBUG"                     = "False"
    "ALLOWED_HOSTS"             = "YOUR_SERVER_HOSTNAME,localhost"
    "SECURE_SSL_REDIRECT"       = "False"
    "CSRF_TRUSTED_ORIGINS"      = "https://YOUR_SERVER_HOSTNAME"
    "OPENAI_API_KEY"            = "REPLACE_WITH_YOUR_OPENAI_KEY"
    "PBIRS_CLAIMS_CAPACITY_URL" = "http://10.111.36.98/reports/powerbi/COMMERCIAL/Centene/Claims%20Capacity%20Planning%20Dashboard?rs:Embed=true"
}

# =============================================================================
# SET ENV VARS VIA NSSM AND RESTART SERVICE
# =============================================================================

$svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if (-not $svc) {
    Write-Error "Service not found: $ServiceName. Register it first using register-service.ps1."
    exit 1
}

# Stop service before updating env vars
Write-Host "Stopping $ServiceName..." -ForegroundColor Cyan
Stop-Service -Name $ServiceName -Force
Start-Sleep -Seconds 2

# Build all env vars as an array and set in a single NSSM call
# (multiple calls replace each other — all vars must be passed at once)
Write-Host "Setting environment variables..." -ForegroundColor Cyan
$envArray = $EnvVars.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" }
& $NssmPath set $ServiceName AppEnvironmentExtra @envArray | Out-Null
$EnvVars.Keys | ForEach-Object { Write-Host "  Set $_" -ForegroundColor Gray }
Write-Host "[OK] Environment variables set." -ForegroundColor Green

# Start service
Write-Host "Starting $ServiceName..." -ForegroundColor Cyan
Start-Service -Name $ServiceName
Start-Sleep -Seconds 2

$svc = Get-Service -Name $ServiceName
Write-Host "Status: $($svc.Status)" -ForegroundColor Green

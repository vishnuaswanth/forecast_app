#Requires -RunAsAdministrator
# Sets system environment variables and starts the CenteneForecasting service.
# Run this after the service is already registered via NSSM.

# =============================================================================
# CONFIGURE THESE VALUES
# =============================================================================

$ServiceName = "CenteneForecasting"

$EnvVars = @{
    "DJANGO_SETTINGS_MODULE"    = "centene_forecast_project.settings"
    "SECRET_KEY"                = "REPLACE_WITH_YOUR_SECRET_KEY"
    "DEBUG"                     = "False"
    "ALLOWED_HOSTS"             = "YOUR_SERVER_HOSTNAME,localhost"
    "SECURE_SSL_REDIRECT"       = "False"
    "OPENAI_API_KEY"            = "REPLACE_WITH_YOUR_OPENAI_KEY"
    "PBIRS_CLAIMS_CAPACITY_URL" = "http://10.111.36.98/reports/powerbi/COMMERCIAL/Centene/Claims%20Capacity%20Planning%20Dashboard?rs:Embed=true"
}

# =============================================================================
# SET ENV VARS AND START SERVICE
# =============================================================================

Write-Host "Setting environment variables..." -ForegroundColor Cyan
foreach ($key in $EnvVars.Keys) {
    [System.Environment]::SetEnvironmentVariable($key, $EnvVars[$key], [System.EnvironmentVariableTarget]::Machine)
    Write-Host "  Set $key" -ForegroundColor Gray
}
Write-Host "[OK] Environment variables set." -ForegroundColor Green

$svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if (-not $svc) {
    Write-Error "Service not found: $ServiceName. Register it first using NSSM."
    exit 1
}

Write-Host "Restarting $ServiceName..." -ForegroundColor Cyan
Restart-Service -Name $ServiceName -Force
Start-Sleep -Seconds 2

$svc = Get-Service -Name $ServiceName
Write-Host "Status: $($svc.Status)" -ForegroundColor Green

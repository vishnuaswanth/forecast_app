#Requires -RunAsAdministrator
# Sets NSSM service environment variables and restarts the CenteneForecasting service.
# Run this after the service is already registered via register-service.ps1.

# =============================================================================
# CONFIGURE THESE VALUES
# =============================================================================

$NssmPath    = "C:\nssm.exe"
$ServiceName = "CenteneForecasting"

$EnvVars = @{
    "DJANGO_SETTINGS_MODULE"           = "centene_forecast_project.settings"
    "CENTENE_SECRET_KEY"               = "REPLACE_WITH_YOUR_SECRET_KEY"
    "CENTENE_DEBUG"                    = "False"
    "CENTENE_ALLOWED_HOSTS"            = "YOUR_SERVER_HOSTNAME,localhost"
    "CENTENE_SECURE_SSL_REDIRECT"      = "False"
    "CENTENE_CSRF_TRUSTED_ORIGINS"     = "https://YOUR_SERVER_HOSTNAME"
    "CENTENE_OPENAI_API_KEY"           = "REPLACE_WITH_YOUR_OPENAI_KEY"
    "CENTENE_API_BASE_URL"             = "http://127.0.0.1:8888"
    "CENTENE_PBIRS_CLAIMS_CAPACITY_URL"= "http://10.111.36.98/reports/powerbi/COMMERCIAL/Centene/Claims%20Capacity%20Planning%20Dashboard?rs:Embed=true"
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

# Clear NSSM AppEnvironmentExtra so it does not override system env vars
$regPath = "HKLM:\SYSTEM\CurrentControlSet\Services\$ServiceName\Parameters"
Set-ItemProperty -Path $regPath -Name "AppEnvironmentExtra" -Value @() -Type MultiString

# Set all values in Windows system environment — the service inherits these on start
Write-Host "Setting environment variables..." -ForegroundColor Cyan
foreach ($key in $EnvVars.Keys) {
    [System.Environment]::SetEnvironmentVariable($key, $EnvVars[$key], [System.EnvironmentVariableTarget]::Machine)
    Write-Host "  Set $key" -ForegroundColor Gray
}
Write-Host "[OK] Environment variables set." -ForegroundColor Green

# Start service
Write-Host "Starting $ServiceName..." -ForegroundColor Cyan
Start-Service -Name $ServiceName
Start-Sleep -Seconds 2

$svc = Get-Service -Name $ServiceName
Write-Host "Status: $($svc.Status)" -ForegroundColor Green

# Requires -RunAsAdministrator
# One-time script to register CenteneForecasting as a Windows service using NSSM.
# Run this once on first deployment. Use setup-service.ps1 for env vars and restarts.

# =============================================================================
# CONFIGURE THESE VALUES
# =============================================================================

$NssmPath               = "C:\nssm.exe"
$ServiceName            = "CenteneForecasting"
$ProjectRoot            = "C:\inetpub\wwwroot\Centene_Forecasting"
$VenvDaphne             = "$ProjectRoot\.venv\Scripts\daphne.exe"
$DjangoDir              = "$ProjectRoot\centene_forecast_project"
$CenteneForecastingHost = "127.0.0.1"
$CenteneForecastingPort = 8096
$AsgiModule             = "centene_forecast_project.asgi:application"
$LogDir                 = "C:\Logs\CenteneForecasting"

# =============================================================================
# REGISTER SERVICE
# =============================================================================

if (-not (Test-Path $VenvDaphne)) {
    Write-Error "daphne.exe not found at $VenvDaphne"
    exit 1
}

$existing = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Stopping and removing existing service..." -ForegroundColor Yellow
    & $NssmPath stop $ServiceName confirm 2>&1 | Out-Null
    & $NssmPath remove $ServiceName confirm 2>&1 | Out-Null
}

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

Write-Host "Registering $ServiceName..." -ForegroundColor Cyan
& $NssmPath install $ServiceName $VenvDaphne
& $NssmPath set $ServiceName AppParameters "-b $CenteneForecastingHost -p $CenteneForecastingPort $AsgiModule"
& $NssmPath set $ServiceName AppDirectory $DjangoDir
& $NssmPath set $ServiceName DisplayName "Centene Forecasting (Daphne ASGI)"
& $NssmPath set $ServiceName Start SERVICE_AUTO_START
& $NssmPath set $ServiceName AppStdout "$LogDir\daphne_stdout.log"
& $NssmPath set $ServiceName AppStderr "$LogDir\daphne_stderr.log"
& $NssmPath set $ServiceName AppRotateFiles 1
& $NssmPath set $ServiceName AppRotateSeconds 86400
& $NssmPath set $ServiceName AppRotateBytes 5242880

Write-Host "[OK] $ServiceName registered." -ForegroundColor Green
Write-Host "Now run setup-service.ps1 to set environment variables and start the service." -ForegroundColor Yellow

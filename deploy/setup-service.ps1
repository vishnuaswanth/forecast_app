#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Deploy Centene Forecasting on Windows via NSSM (Non-Sucking Service Manager).
    Registers two Windows services: CenteneForecasting (daphne ASGI) and CenteneQ (Django-Q worker).

.NOTES
    Prerequisites:
      - Python virtualenv already created and dependencies installed
      - NSSM installed (https://nssm.cc/download) and on PATH, OR place nssm.exe in $NssmPath
      - .env file created and populated in the Django project directory
      - Run this script as Administrator in PowerShell
#>

# =============================================================================
# CONFIGURABLE VARIABLES — edit these before running
# =============================================================================
$ProjectRoot    = "C:\inetpub\wwwroot\Centene_Forecasting"
$DjangoDir      = "$ProjectRoot\centene_forecast_project"
$VenvPython     = "$ProjectRoot\.venv\Scripts\python.exe"
$VenvDaphne     = "$ProjectRoot\.venv\Scripts\daphne.exe"
$LogDir         = "C:\Logs\CenteneForecasting"
$Port           = 8000
$Host           = "0.0.0.0"
$AsgiModule     = "centene_forecast_project.asgi:application"
$NssmPath       = "nssm"   # Change to full path if nssm is not on PATH, e.g. "C:\tools\nssm.exe"

# Windows environment variables to set for both services
$EnvVars = @{
    "DJANGO_SETTINGS_MODULE" = "centene_forecast_project.settings"
    "SECRET_KEY"             = "REPLACE_WITH_YOUR_SECRET_KEY"
    "DEBUG"                  = "False"
    "ALLOWED_HOSTS"          = "YOUR_SERVER_HOSTNAME,localhost"
    "OPENAI_API_KEY"         = "REPLACE_WITH_YOUR_OPENAI_KEY"
    "PBIRS_CLAIMS_CAPACITY_URL" = "http://10.111.36.98/reports/powerbi/COMMERCIAL/Centene/Claims%20Capacity%20Planning%20Dashboard?rs:Embed=true"
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
function Ensure-NssmInstalled {
    try {
        $null = & $NssmPath version 2>&1
        Write-Host "[OK] NSSM found." -ForegroundColor Green
    } catch {
        Write-Error @"
NSSM not found at '$NssmPath'.
Download from https://nssm.cc/download, extract nssm.exe, and either:
  - Add its directory to your PATH, OR
  - Set `$NssmPath in this script to the full path of nssm.exe
"@
        exit 1
    }
}

function Stop-AndRemove-Service($ServiceName) {
    $svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if ($svc) {
        Write-Host "Removing existing service: $ServiceName" -ForegroundColor Yellow
        & $NssmPath stop $ServiceName confirm 2>&1 | Out-Null
        & $NssmPath remove $ServiceName confirm 2>&1 | Out-Null
    }
}

function Set-ServiceEnvironment($ServiceName, [hashtable]$Vars) {
    foreach ($key in $Vars.Keys) {
        & $NssmPath set $ServiceName AppEnvironmentExtra "$key=$($Vars[$key])" | Out-Null
    }
}

function Register-DaphneService {
    $ServiceName = "CenteneForecasting"
    Stop-AndRemove-Service $ServiceName

    Write-Host "Registering $ServiceName service..." -ForegroundColor Cyan
    & $NssmPath install $ServiceName $VenvDaphne
    & $NssmPath set $ServiceName AppParameters "-b $Host -p $Port $AsgiModule"
    & $NssmPath set $ServiceName AppDirectory $DjangoDir
    & $NssmPath set $ServiceName DisplayName "Centene Forecasting (Daphne ASGI)"
    & $NssmPath set $ServiceName Description "Centene Forecasting Django/Channels application served via Daphne."
    & $NssmPath set $ServiceName Start SERVICE_AUTO_START
    & $NssmPath set $ServiceName AppStdout "$LogDir\daphne_stdout.log"
    & $NssmPath set $ServiceName AppStderr "$LogDir\daphne_stderr.log"
    & $NssmPath set $ServiceName AppRotateFiles 1
    & $NssmPath set $ServiceName AppRotateSeconds 86400
    & $NssmPath set $ServiceName AppRotateBytes 5242880
    Set-ServiceEnvironment $ServiceName $EnvVars
    Write-Host "[OK] $ServiceName registered." -ForegroundColor Green
}

function Register-QClusterService {
    $ServiceName = "CenteneQ"
    Stop-AndRemove-Service $ServiceName

    Write-Host "Registering $ServiceName service..." -ForegroundColor Cyan
    & $NssmPath install $ServiceName $VenvPython
    & $NssmPath set $ServiceName AppParameters "manage.py qcluster"
    & $NssmPath set $ServiceName AppDirectory $DjangoDir
    & $NssmPath set $ServiceName DisplayName "Centene Forecasting Django-Q Worker"
    & $NssmPath set $ServiceName Description "Django-Q background task worker for Centene Forecasting."
    & $NssmPath set $ServiceName Start SERVICE_AUTO_START
    & $NssmPath set $ServiceName AppStdout "$LogDir\qcluster_stdout.log"
    & $NssmPath set $ServiceName AppStderr "$LogDir\qcluster_stderr.log"
    & $NssmPath set $ServiceName AppRotateFiles 1
    & $NssmPath set $ServiceName AppRotateSeconds 86400
    & $NssmPath set $ServiceName AppRotateBytes 5242880
    Set-ServiceEnvironment $ServiceName $EnvVars
    Write-Host "[OK] $ServiceName registered." -ForegroundColor Green
}

# =============================================================================
# MAIN
# =============================================================================
Write-Host "=== Centene Forecasting — IIS/NSSM Service Setup ===" -ForegroundColor White

# Validate paths
if (-not (Test-Path $VenvDaphne)) {
    Write-Error "daphne.exe not found at '$VenvDaphne'. Activate your virtualenv and run: pip install daphne"
    exit 1
}
if (-not (Test-Path $VenvPython)) {
    Write-Error "python.exe not found at '$VenvPython'. Check your virtualenv path."
    exit 1
}

Ensure-NssmInstalled

# Create log directory
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
Write-Host "[OK] Log directory: $LogDir" -ForegroundColor Green

# Set system-wide environment variables
Write-Host "Setting system environment variables..." -ForegroundColor Cyan
foreach ($key in $EnvVars.Keys) {
    [System.Environment]::SetEnvironmentVariable($key, $EnvVars[$key], [System.EnvironmentVariableTarget]::Machine)
}
Write-Host "[OK] Environment variables set." -ForegroundColor Green

# Register services
Register-DaphneService
Register-QClusterService

# Start services
Write-Host "Starting services..." -ForegroundColor Cyan
Start-Service -Name "CenteneForecasting" -ErrorAction SilentlyContinue
Start-Service -Name "CenteneQ" -ErrorAction SilentlyContinue

# Status summary
Write-Host ""
Write-Host "=== Service Status ===" -ForegroundColor White
Get-Service -Name "CenteneForecasting", "CenteneQ" | Format-Table Name, Status, DisplayName -AutoSize

Write-Host ""
Write-Host "Setup complete." -ForegroundColor Green
Write-Host "App is available at http://localhost:$Port/" -ForegroundColor Green
Write-Host "Logs: $LogDir" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Update SECRET_KEY and OPENAI_API_KEY in `$EnvVars at the top of this script and re-run, OR"
Write-Host "     populate centene_forecast_project\.env with correct values."
Write-Host "  2. Configure IIS as a reverse proxy to http://localhost:$Port/ (Application Request Routing module)."
Write-Host "  3. Run 'python manage.py collectstatic --noinput' to serve static files via IIS."

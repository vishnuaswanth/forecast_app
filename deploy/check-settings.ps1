# Checks Django settings and NSSM environment variables.
# Run from anywhere on the server.

# =============================================================================
# CONFIGURE THESE
# =============================================================================

$NssmPath    = "C:\nssm.exe"
$ServiceName = "CenteneForecasting"
$DjangoDir   = "C:\inetpub\wwwroot\Centene_Forecasting\centene_forecast_project"
$Python      = "C:\inetpub\wwwroot\Centene_Forecasting\.venv\Scripts\python.exe"

# =============================================================================
# CHECKS
# =============================================================================

Write-Host ""
Write-Host "=== Service Status ===" -ForegroundColor White
Get-Service -Name $ServiceName -ErrorAction SilentlyContinue | Format-Table Name, Status, DisplayName -AutoSize

Write-Host "=== NSSM AppEnvironmentExtra ===" -ForegroundColor White
& $NssmPath get $ServiceName AppEnvironmentExtra

Write-Host "=== System Environment Variables ===" -ForegroundColor White
@("DJANGO_SETTINGS_MODULE","SECRET_KEY","DEBUG","ALLOWED_HOSTS","SECURE_SSL_REDIRECT",
  "CSRF_TRUSTED_ORIGINS","OPENAI_API_KEY") | ForEach-Object {
    $val = [System.Environment]::GetEnvironmentVariable($_, "Machine")
    $display = if ($_ -eq "SECRET_KEY" -and $val) { "***hidden***" }
               elseif ($val) { $val } else { "<NOT SET>" }
    "{0,-30} = {1}" -f $_, $display
}

Write-Host ""
Write-Host "=== Django Settings ===" -ForegroundColor White
& $Python -c @"
import os, sys
sys.path.insert(0, r"$DjangoDir")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "centene_forecast_project.settings")
import django
django.setup()
from django.conf import settings
print(f"DEBUG              : {settings.DEBUG}")
print(f"ALLOWED_HOSTS      : {settings.ALLOWED_HOSTS}")
print(f"CSRF_ORIGINS       : {settings.CSRF_TRUSTED_ORIGINS}")
print(f"SSL_REDIRECT       : {settings.SECURE_SSL_REDIRECT}")
print(f"API_BASE_URL       : {settings.API_BASE_URL}")
print(f"SECRET_KEY set     : {bool(settings.SECRET_KEY)}")
print(f"OPENAI key set     : {bool(getattr(settings, \"OPENAI_API_KEY\", \"\"))}")
"@

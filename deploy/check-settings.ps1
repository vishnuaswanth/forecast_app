# Checks Django settings and NSSM environment variables.
# Run from anywhere on the server.

# =============================================================================
# CONFIGURE THESE
# =============================================================================

$NssmPath    = "C:\nssm.exe"
$ServiceName = "CenteneForecasting"
$DjangoDir   = "C:\inetpub\wwwroot\Centene_Forecasting\centene_forecast_project"
$Python      = "C:\inetpub\wwwroot\Centene_Forecasting\.venv\Scripts\python.exe"
$CheckScript = "C:\inetpub\wwwroot\Centene_Forecasting\deploy\check_settings.py"

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
Push-Location $DjangoDir
& $Python $CheckScript
Pop-Location

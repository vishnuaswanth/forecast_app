# Centene Forecasting - Deployment Guide

**Stack:** Django 5 · Daphne (ASGI) · SQLite / MS SQL Server · IIS (reverse proxy) · NSSM (Windows services)

---

## Table of Contents

1. [Dev Environment Checks](#1-dev-environment-checks)
2. [Prepare the Production Server](#2-prepare-the-production-server)
3. [Deploy the Application](#3-deploy-the-application)
4. [Register and Configure the Service](#4-register-and-configure-the-service)
5. [Verify Environment Variables](#5-verify-environment-variables)
6. [Configure IIS as Reverse Proxy](#6-configure-iis-as-reverse-proxy)
7. [Verify the Application Is Working](#7-verify-the-application-is-working)
8. [Common Issues and Fixes](#8-common-issues-and-fixes)

---

## 1. Dev Environment Checks

Run all of these on your **development machine** before touching the server.

### 1.1 Confirm the app starts cleanly

```powershell
cd centene_forecast_project
python manage.py check
```

Expected output: `System check identified no issues (0 silenced).`

### 1.2 Run the deployment checklist

```powershell
# Set DEBUG=False temporarily to surface production warnings
$env:CENTENE_DEBUG = "False"
$env:CENTENE_SECRET_KEY = "temp-check-key"
$env:CENTENE_ALLOWED_HOSTS = "localhost"
$env:CENTENE_SECURE_SSL_REDIRECT = "False"
python manage.py check --deploy
$env:CENTENE_DEBUG = $null   # restore
```

Fix any `CRITICAL` items before proceeding. `WARNING` items about HTTPS are expected since IIS handles SSL termination.

### 1.3 Confirm migrations are up to date

```powershell
python manage.py showmigrations
```

All migrations should show `[X]`. If any show `[ ]`, run `python manage.py migrate` and commit the result.

### 1.4 Confirm static files collect without errors

```powershell
python manage.py collectstatic --noinput --dry-run
```

Should list files without any errors. The actual output goes to `centene_forecast_project/staticfiles/`.

### 1.5 Confirm the FastAPI backend is reachable

```powershell
curl http://127.0.0.1:8888/health   # or any known endpoint
```

The Django app is a frontend only — the FastAPI backend at `API_BASE_URL` must be running independently.

### 1.6 Confirm WebSocket route is registered

```powershell
python -c "import os, django; os.environ['DJANGO_SETTINGS_MODULE']='centene_forecast_project.settings'; django.setup(); from chat_app.routing import websocket_urlpatterns; print(websocket_urlpatterns)"
```

Should print the `centene_forecasting/ws/chat/` pattern without import errors.

### 1.7 Confirm Daphne starts and serves the app

Run Daphne directly (the same way NSSM will run it on the server) and verify it responds before setting it up as a service.

```powershell
cd centene_forecast_project
daphne -b 127.0.0.1 -p 8096 centene_forecast_project.asgi:application
```

In a **separate terminal**, test HTTP and static files:

```powershell
# HTTP - should return a redirect to login page
curl -I http://127.0.0.1:8096/centene_forecasting/

# Static files - should return 200 (WhiteNoise serves them through Daphne)
curl -I http://127.0.0.1:8096/centene_forecasting/static/css/base.css
```

Expected responses:

| Response | Meaning |
|----------|---------|
| `200 OK` | Page served directly |
| `302 Found` | Redirecting to login page (normal) |
| `301 Moved Permanently` | `SECURE_SSL_REDIRECT=True` — set it to `False` in `.env` |

Any `Connection refused` means Daphne did not start — check the terminal output for errors.

Stop Daphne with `Ctrl+C` once verified.

### 1.8 Freeze dependencies

```powershell
pip freeze > requirements-lock.txt
```

Commit `requirements-lock.txt` so the exact versions used in dev are reproducible on the server.

---

## 2. Prepare the Production Server

### 2.1 Prerequisites

Install the following on the Windows server:

| Tool | Notes |
|------|-------|
| Python 3.11+ | Download from python.org; add to PATH |
| NSSM | Download from https://nssm.cc/download; place `nssm.exe` at `C:\nssm.exe` |
| IIS with ARR | Enable Application Request Routing, URL Rewrite, and WebSocket Protocol modules |
| Git | To pull source code |
| ODBC Driver 17 | Required only if switching from SQLite to MS SQL Server |

Verify WebSocket Protocol is installed:

```powershell
Get-WindowsFeature Web-WebSockets
```

`InstallState` should show `Installed`. If not:

```powershell
Install-WindowsFeature Web-WebSockets
```

### 2.2 Copy the source code

```powershell
# Option A - git clone
git clone <repo-url> C:\inetpub\wwwroot\Centene_Forecasting

# Option B - xcopy from dev machine
xcopy /E /I /Y \\devmachine\share\Centene_Forecasting C:\inetpub\wwwroot\Centene_Forecasting
```

### 2.3 Create a virtual environment and install dependencies

```powershell
cd C:\inetpub\wwwroot\Centene_Forecasting
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

> **Do not** copy the `.venv` from your dev machine — always create a fresh one on the server.

### 2.4 Check the port is free

```powershell
netstat -ano | findstr ":8096"
```

No output means the port is free. If occupied, choose a different port and update it in `deploy\register-service.ps1` and the IIS `web.config` rule.

---

## 3. Deploy the Application

### 3.1 Run database migrations

```powershell
cd C:\inetpub\wwwroot\Centene_Forecasting\centene_forecast_project

# Set minimal env vars for this step
$env:CENTENE_SECRET_KEY    = "temp"
$env:CENTENE_DEBUG         = "True"
$env:CENTENE_ALLOWED_HOSTS = "localhost"

.\.venv\Scripts\python.exe manage.py migrate
```

### 3.2 Collect static files

```powershell
.\.venv\Scripts\python.exe manage.py collectstatic --noinput
```

Output lands in `centene_forecast_project\staticfiles\`. Static files are served by WhiteNoise through Daphne — no IIS virtual directory needed.

### 3.3 Create an admin user (first deployment only)

```powershell
.\.venv\Scripts\python.exe manage.py createsuperuser
```

On subsequent deployments, skip this step — the database already has users.

---

## 4. Register and Configure the Service

Two scripts in `deploy\` handle the service setup:

| Script | When to run |
|--------|-------------|
| `register-service.ps1` | **Once** — first deployment, registers the NSSM service |
| `setup-service.ps1` | **Every deployment** — sets environment variables and restarts the service |

Open **PowerShell as Administrator** for both scripts:

```powershell
Set-ExecutionPolicy RemoteSigned -Scope Process
cd C:\inetpub\wwwroot\Centene_Forecasting
```

### 4.1 Register the service (first deployment only)

Open `deploy\register-service.ps1` and confirm the variables at the top:

```powershell
$NssmPath               = "C:\nssm.exe"
$ProjectRoot            = "C:\inetpub\wwwroot\Centene_Forecasting"
$CenteneForecastingHost = "127.0.0.1"   # loopback only - IIS proxies from outside
$CenteneForecastingPort = 8096          # must match web.config rewrite rule port
```

Then run:

```powershell
.\deploy\register-service.ps1
```

### 4.2 Set environment variables and start the service

Open `deploy\setup-service.ps1` and fill in the `$EnvVars` block:

```powershell
$EnvVars = @{
    "DJANGO_SETTINGS_MODULE"           = "centene_forecast_project.settings"
    "CENTENE_SECRET_KEY"               = "your-actual-secret-key-here"       # <- change
    "CENTENE_DEBUG"                    = "False"
    "CENTENE_ALLOWED_HOSTS"            = "your.server.hostname,localhost"     # <- change
    "CENTENE_SECURE_SSL_REDIRECT"      = "False"   # IIS handles HTTPS, not Django
    "CENTENE_OPENAI_API_KEY"           = "sk-..."                             # <- change
    "CENTENE_API_BASE_URL"             = "http://127.0.0.1:8888"
    "CENTENE_PBIRS_CLAIMS_CAPACITY_URL"= "http://10.111.36.98/reports/..."   # <- confirm
}
```

Then run:

```powershell
.\deploy\setup-service.ps1
```

This sets all variables in the Windows system environment (registry) and restarts the service.

### 4.3 Confirm service is running

```powershell
Get-Service CenteneForecasting | Format-Table Name, Status
```

Should show `Status: Running`. Also visible in `services.msc`.

---

## 5. Verify Environment Variables

### 5.1 Check Windows system environment (registry)

Open a **new** PowerShell window (must be fresh — not the one that ran the script):

```powershell
@('CENTENE_SECRET_KEY','CENTENE_DEBUG','CENTENE_ALLOWED_HOSTS','CENTENE_SECURE_SSL_REDIRECT',
  'CENTENE_OPENAI_API_KEY','CENTENE_API_BASE_URL','DJANGO_SETTINGS_MODULE') | ForEach-Object {
    $val = [System.Environment]::GetEnvironmentVariable($_, 'Machine')
    $preview = if ($val) { $val.Substring(0, [Math]::Min(30, $val.Length)) + '...' } else { '<NOT SET>' }
    "{0,-40} = {1}" -f $_, $preview
}
```

### 5.2 Check Django reads them correctly

```powershell
cd C:\inetpub\wwwroot\Centene_Forecasting\centene_forecast_project

.\.venv\Scripts\python.exe manage.py shell -c "
from django.conf import settings
print('SECRET_KEY set    :', bool(settings.SECRET_KEY) and 'insecure' not in settings.SECRET_KEY)
print('DEBUG             :', settings.DEBUG)
print('ALLOWED_HOSTS     :', settings.ALLOWED_HOSTS)
print('SSL_REDIRECT      :', settings.SECURE_SSL_REDIRECT)
print('API_BASE_URL      :', settings.API_BASE_URL)
print('OPENAI key set    :', bool(settings.LLM_CONFIG.get('api_key')))
"
```

Expected output:
```
SECRET_KEY set    : True
DEBUG             : False
ALLOWED_HOSTS     : ['your.server.hostname', 'localhost']
SSL_REDIRECT      : False
API_BASE_URL      : http://127.0.0.1:8888
OPENAI key set    : True
```

### 5.3 Run the full deployment check

```powershell
.\.venv\Scripts\python.exe manage.py check --deploy
```

`System check identified no issues (0 silenced).`

---

## 6. Configure IIS as Reverse Proxy

IIS forwards incoming HTTPS traffic to Daphne running on `127.0.0.1:8096` over plain HTTP internally. SSL termination happens at IIS — Daphne only ever receives plain HTTP. Static files are served by WhiteNoise through Daphne — no IIS virtual directory required.

### 6.1 Required IIS modules

Make sure these are installed via **Server Manager -> Add Roles and Features -> Web Server (IIS)**:

- Application Request Routing (ARR) 3.0
- URL Rewrite 2.1
- WebSocket Protocol

### 6.2 Enable ARR proxy

Open **IIS Manager -> Server node -> Application Request Routing Cache -> Server Proxy Settings**:
- Check **Enable proxy**
- Click **Apply**

### 6.3 Add URL Rewrite rules to your site's `web.config`

Edit `C:\inetpub\wwwroot\web.config` on the IIS site that hosts multiple apps. Add the Centene Forecasting rules alongside your existing app rules:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
  <system.webServer>
    <rewrite>
      <rules>

        <!-- your other app rules (uarboi, bipapp, etc.) remain here -->

        <!-- Centene Forecasting - WebSocket (must come before HTTP rule) -->
        <rule name="centene_forecasting_ws" stopProcessing="true">
          <match url="^centene_forecasting/(.*)" />
          <conditions>
            <add input="{HTTP_UPGRADE}" pattern="^WebSocket$" />
          </conditions>
          <action type="Rewrite" url="ws://127.0.0.1:8096/centene_forecasting/{R:1}" />
        </rule>

        <!-- Centene Forecasting - all HTTP/HTTPS traffic -->
        <rule name="centene_forecasting" stopProcessing="true">
          <match url="^centene_forecasting(/.*)?$" />
          <action type="Rewrite" url="http://127.0.0.1:8096/centene_forecasting{R:1}" />
        </rule>

        <!-- Root redirect to app -->
        <rule name="centene_forecasting_root" stopProcessing="true">
          <match url="^$" />
          <action type="Redirect" url="/centene_forecasting/" redirectType="Found" />
        </rule>

      </rules>
    </rewrite>
  </system.webServer>
</configuration>
```

### 6.4 Restart IIS

```powershell
iisreset
```

---

## 7. Verify the Application Is Working

### 7.1 Daphne responds directly

```powershell
curl -I http://127.0.0.1:8096/centene_forecasting/
```

Expected: `HTTP/1.1 302` (redirect to login). Any response confirms Daphne is running.

### 7.2 Login page loads

Open a browser and navigate to `https://your.server.hostname/centene_forecasting/`. The login page should render with correct styling.

Check:
- [ ] Logo and CSS load (static files working via WhiteNoise)
- [ ] No browser console errors about missing JS files

### 7.3 LDAP login works

Log in with a valid NTT Data `AMERICAS\username` and password. If login fails, see [Common Issues](#8-common-issues-and-fixes).

### 7.4 WebSocket connects

Open the Chat page. In browser developer tools -> Network tab -> filter by `WS`:
- A WebSocket connection to `wss://your.server.hostname/centene_forecasting/ws/chat/` should show status `101 Switching Protocols`.

### 7.5 FastAPI backend connectivity

```powershell
# From the server - confirms the backend is reachable from Django's perspective
.\.venv\Scripts\python.exe -c "
import httpx, os
url = os.environ.get('API_BASE_URL', 'http://127.0.0.1:8888')
r = httpx.get(url + '/health', verify=False, timeout=5)
print(r.status_code, r.text[:200])
"
```

### 7.6 Check application logs

```powershell
# Live tail of Daphne stderr (startup errors, unhandled exceptions)
Get-Content C:\Logs\CenteneForecasting\daphne_stderr.log -Tail 50 -Wait

# Structured Django logs
Get-Content (Get-ChildItem C:\Logs\CenteneForecasting\*.log | Sort LastWriteTime -Desc | Select -First 1).FullName -Tail 30
```

---

## 8. Common Issues and Fixes

### `KeyError: 'CENTENE_SECRET_KEY'` on startup

**Cause:** Environment variable not set, or the service started before the script finished writing to the registry.

```powershell
# Verify it is set in the Machine scope
[System.Environment]::GetEnvironmentVariable('CENTENE_SECRET_KEY', 'Machine')

# Restart service to pick up registry changes
Restart-Service CenteneForecasting
```

---

### `DisallowedHost` - 400 Bad Request

**Cause:** The server hostname is not in `ALLOWED_HOSTS`.

Update `CENTENE_ALLOWED_HOSTS` in `deploy\setup-service.ps1` and re-run it, or update directly:

```powershell
[System.Environment]::SetEnvironmentVariable('CENTENE_ALLOWED_HOSTS','new.hostname,localhost','Machine')
Restart-Service CenteneForecasting
```

---

### Static files return 404

**Cause:** `collectstatic` was not run.

```powershell
cd C:\inetpub\wwwroot\Centene_Forecasting\centene_forecast_project
.\.venv\Scripts\python.exe manage.py collectstatic --noinput
Restart-Service CenteneForecasting
```

---

### WebSocket handshake fails (403 or connection refused)

**Cause A:** `ALLOWED_HOSTS` does not include the server hostname.
-> Fix: add the hostname to `ALLOWED_HOSTS` and restart the service.

**Cause B:** IIS ARR WebSocket rewrite rule is missing or ARR proxy not enabled.
-> Fix: re-check [Section 6](#6-configure-iis-as-reverse-proxy).

**Cause C:** WebSocket Protocol IIS feature not installed.
-> Fix: `Install-WindowsFeature Web-WebSockets` then `iisreset`.

---

### Page redirects to `https://127.0.0.1:8096/` and fails

**Cause:** `SECURE_SSL_REDIRECT` is `True` — Django is redirecting HTTP to HTTPS internally, but Daphne only serves HTTP.

```powershell
[System.Environment]::SetEnvironmentVariable('CENTENE_SECURE_SSL_REDIRECT','False','Machine')
Restart-Service CenteneForecasting
```

---

### LDAP login fails - "Invalid credentials"

**Cause A:** The user has not been assigned a Django Group (ADMIN / MANAGER / VIEWER).
-> Fix: Log in as superuser at `/centene_forecasting/admin/`, go to **Users**, find the user, assign a group.

**Cause B:** The server cannot reach the LDAP host.
```powershell
Test-NetConnection americas.global.nttdata.com -Port 389
```
Should show `TcpTestSucceeded: True`. If not, raise a firewall ticket.

---

### `django.db.OperationalError: no such table`

**Cause:** Migrations were not run on the production database.

```powershell
cd C:\inetpub\wwwroot\Centene_Forecasting\centene_forecast_project
.\.venv\Scripts\python.exe manage.py migrate
Restart-Service CenteneForecasting
```

---

### Service fails to start after server reboot

**Cause:** Daphne starts before the network stack is ready.

```powershell
C:\nssm.exe set CenteneForecasting DependOnService Tcpip
Restart-Service CenteneForecasting
```

---

## Quick Reference

```powershell
# Start / stop / restart
Start-Service   CenteneForecasting
Stop-Service    CenteneForecasting
Restart-Service CenteneForecasting

# Live log tailing
Get-Content C:\Logs\CenteneForecasting\daphne_stderr.log -Tail 30 -Wait

# Django shell on the server
cd C:\inetpub\wwwroot\Centene_Forecasting\centene_forecast_project
.\.venv\Scripts\python.exe manage.py shell

# Re-deploy (pull + migrate + collectstatic + restart)
git -C C:\inetpub\wwwroot\Centene_Forecasting pull
.\.venv\Scripts\python.exe manage.py migrate --noinput
.\.venv\Scripts\python.exe manage.py collectstatic --noinput
.\deploy\setup-service.ps1
```

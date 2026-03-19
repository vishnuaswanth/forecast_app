# Centene Forecasting — Deployment Guide

**Stack:** Django 5 · Daphne (ASGI) · SQLite / MS SQL Server · IIS (reverse proxy) · NSSM (Windows services)

---

## Table of Contents

1. [Dev Environment Checks](#1-dev-environment-checks)
2. [Prepare the Production Server](#2-prepare-the-production-server)
3. [Deploy the Application](#3-deploy-the-application)
4. [Run the PowerShell Setup Script](#4-run-the-powershell-setup-script)
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
$env:DEBUG = "False"
$env:SECRET_KEY = "temp-check-key"
$env:ALLOWED_HOSTS = "localhost"
python manage.py check --deploy
$env:DEBUG = $null   # restore
```

Fix any `CRITICAL` items before proceeding. `WARNING` items about HTTPS are expected for an internal HTTP deployment.

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
python -c "from chat_app.routing import websocket_urlpatterns; print(websocket_urlpatterns)"
```

Should print the `centene_forecasting/ws/chat/` pattern without import errors.

### 1.7 Freeze dependencies

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
| NSSM | Download from https://nssm.cc/download; add `nssm.exe` to PATH or `C:\tools\` |
| IIS with ARR | Enable Application Request Routing and URL Rewrite modules |
| Git | To pull source code |
| ODBC Driver 17 | Required only if switching from SQLite to MS SQL Server |

### 2.2 Copy the source code

```powershell
# Option A — git clone
git clone <repo-url> C:\inetpub\wwwroot\Centene_Forecasting

# Option B — xcopy from dev machine
xcopy /E /I /Y \\devmachine\share\Centene_Forecasting C:\inetpub\wwwroot\Centene_Forecasting
```

### 2.3 Create a virtual environment and install dependencies

```powershell
cd C:\inetpub\wwwroot\Centene_Forecasting
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

> **Do not** copy the `.venv` from your dev machine — always create a fresh one on the server.

### 2.4 Create the log directory

```powershell
New-Item -ItemType Directory -Force -Path C:\Logs\CenteneForecasting
```

---

## 3. Deploy the Application

### 3.1 Run database migrations

```powershell
cd C:\inetpub\wwwroot\Centene_Forecasting\centene_forecast_project

# Set minimal env vars for this step
$env:SECRET_KEY   = "temp"
$env:DEBUG        = "True"
$env:ALLOWED_HOSTS = "localhost"

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

## 4. Run the PowerShell Setup Script

### 4.1 Edit the script variables

Open `deploy\setup-service.ps1` and fill in the `$EnvVars` block at the top:

```powershell
$EnvVars = @{
    "DJANGO_SETTINGS_MODULE" = "centene_forecast_project.settings"
    "SECRET_KEY"             = "your-actual-secret-key-here"        # ← change
    "DEBUG"                  = "False"
    "ALLOWED_HOSTS"          = "your.server.hostname,localhost"      # ← change
    "OPENAI_API_KEY"         = "sk-..."                              # ← change
    "PBIRS_CLAIMS_CAPACITY_URL" = "http://10.111.36.98/reports/..."  # ← confirm
}
```

Also confirm the path variables match your server layout:

```powershell
$ProjectRoot = "C:\inetpub\wwwroot\Centene_Forecasting"
$Port        = 8000
```

### 4.2 Run the script

Open **PowerShell as Administrator**, then:

```powershell
Set-ExecutionPolicy RemoteSigned -Scope Process   # allow running unsigned scripts
cd C:\inetpub\wwwroot\Centene_Forecasting
.\deploy\setup-service.ps1
```

The script will:
1. Validate that `daphne.exe` and `python.exe` exist in the venv
2. Verify NSSM is installed
3. Write all variables to the Windows system environment (registry)
4. Register and start one Windows service:
   - **CenteneForecasting** — runs `daphne -b 0.0.0.0 -p 8000 centene_forecast_project.asgi:application`

### 4.3 Confirm service is running

```powershell
Get-Service CenteneForecasting | Format-Table Name, Status
```

Should show `Status: Running`.

You can also see it in `services.msc` (Windows Services).

---

## 5. Verify Environment Variables

### 5.1 Check Windows system environment (registry)

Open a **new** PowerShell window (must be fresh — not the one that ran the script):

```powershell
@('SECRET_KEY','DEBUG','ALLOWED_HOSTS','OPENAI_API_KEY','PBIRS_CLAIMS_CAPACITY_URL',
  'DJANGO_SETTINGS_MODULE') | ForEach-Object {
    $val = [System.Environment]::GetEnvironmentVariable($_, 'Machine')
    $preview = if ($val) { $val.Substring(0, [Math]::Min(30, $val.Length)) + '...' } else { '<NOT SET>' }
    "{0,-35} = {1}" -f $_, $preview
}
```

### 5.2 Check NSSM picked them up

```powershell
nssm get CenteneForecasting AppEnvironmentExtra
```

### 5.3 Check Django reads them correctly

```powershell
cd C:\inetpub\wwwroot\Centene_Forecasting\centene_forecast_project

.\.venv\Scripts\python.exe manage.py shell -c "
from django.conf import settings
print('SECRET_KEY set    :', bool(settings.SECRET_KEY) and 'insecure' not in settings.SECRET_KEY)
print('DEBUG             :', settings.DEBUG)
print('ALLOWED_HOSTS     :', settings.ALLOWED_HOSTS)
print('API_BASE_URL      :', settings.API_BASE_URL)
print('PBIRS URL set     :', bool(settings.PBIRS_CLAIMS_CAPACITY_URL))
print('OPENAI key set    :', bool(settings.LLM_CONFIG.get('api_key')))
"
```

Expected output:
```
SECRET_KEY set    : True
DEBUG             : False
ALLOWED_HOSTS     : ['your.server.hostname', 'localhost']
API_BASE_URL      : http://127.0.0.1:8888
PBIRS URL set     : True
OPENAI key set    : True
```

### 5.4 Run the full deployment check

```powershell
.\.venv\Scripts\python.exe manage.py check --deploy
```

`System check identified no issues (0 silenced).`

---

## 6. Configure IIS as Reverse Proxy

IIS forwards incoming HTTP/HTTPS and WebSocket traffic to Daphne running on `localhost:8000`. The app is served under the `/centene_forecasting/` path. Static files are served by WhiteNoise directly through Daphne — no IIS virtual directory required.

### 6.1 Required IIS modules

Make sure these are installed via **Server Manager → Add Roles and Features → Web Server (IIS)**:

- Application Request Routing (ARR) 3.0
- URL Rewrite 2.1
- WebSocket Protocol

### 6.2 Enable ARR proxy

Open **IIS Manager → Server node → Application Request Routing Cache → Server Proxy Settings**:
- Check **Enable proxy**
- Click **Apply**

### 6.3 Add URL Rewrite rules to your site's `web.config`

Create or edit `C:\inetpub\wwwroot\web.config` on the IIS site that hosts multiple apps:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
  <system.webServer>
    <rewrite>
      <!-- Allow URL Rewrite to set the X-Forwarded-Proto server variable -->
      <allowedServerVariables>
        <add name="HTTP_X_FORWARDED_PROTO" />
        <add name="HTTP_X_FORWARDED_HOST" />
      </allowedServerVariables>

      <rules>
        <!-- WebSocket upgrade — must come before HTTP rule -->
        <rule name="Centene Forecasting - WebSocket" stopProcessing="true">
          <match url="^centene_forecasting/(.*)" />
          <conditions>
            <add input="{HTTP_UPGRADE}" pattern="^WebSocket$" />
          </conditions>
          <serverVariables>
            <set name="HTTP_X_FORWARDED_PROTO" value="https" />
            <set name="HTTP_X_FORWARDED_HOST" value="{HTTP_HOST}" />
          </serverVariables>
          <action type="Rewrite" url="ws://localhost:8000/centene_forecasting/{R:1}" />
        </rule>

        <!-- HTTP/HTTPS traffic (pages + static files via WhiteNoise) → Daphne -->
        <rule name="Centene Forecasting - HTTP" stopProcessing="true">
          <match url="^centene_forecasting/(.*)" />
          <serverVariables>
            <set name="HTTP_X_FORWARDED_PROTO" value="https" />
            <set name="HTTP_X_FORWARDED_HOST" value="{HTTP_HOST}" />
          </serverVariables>
          <action type="Rewrite" url="http://localhost:8000/centene_forecasting/{R:1}" />
        </rule>

        <!-- Root redirect to app -->
        <rule name="Centene Forecasting - Root Redirect" stopProcessing="true">
          <match url="^$" />
          <action type="Redirect" url="/centene_forecasting/" redirectType="Found" />
        </rule>
      </rules>
    </rewrite>
  </system.webServer>
</configuration>
```

> **Note:** The `allowedServerVariables` block is required — IIS URL Rewrite will throw an error if you try to set a server variable that isn't declared there first. The `HTTP_X_FORWARDED_PROTO` variable tells Django (via `SECURE_PROXY_SSL_HEADER`) that the original request came over HTTPS.

### 6.4 Restart IIS

```powershell
iisreset
```

---

## 7. Verify the Application Is Working

### 7.1 HTTP response

```powershell
# Should return 302 redirect to /centene_forecasting/
Invoke-WebRequest http://localhost:8000/ -MaximumRedirection 0 -ErrorAction SilentlyContinue |
    Select-Object StatusCode, Headers
```

Expected: `StatusCode: 302`, `Location: /centene_forecasting/`

### 7.2 Login page loads

Open a browser and navigate to `http://your.server.hostname/centene_forecasting/`. The login page should render with NTT Data styling.

Check:
- [ ] Logo and CSS load (static files working via WhiteNoise)
- [ ] The email link at the bottom opens a mail client (`mailto:` working)
- [ ] No browser console errors about missing JS files

### 7.3 LDAP login works

Log in with a valid NTT Data `AMERICAS\username` and password. The LDAP backend authenticates against `ldap://americas.global.nttdata.com`. If login fails, see [Common Issues](#8-common-issues-and-fixes).

### 7.4 WebSocket connects

Open the Chat page. In the browser developer tools → Network tab → filter by `WS`:
- A WebSocket connection to `ws://your.server.hostname/centene_forecasting/ws/chat/` should show status `101 Switching Protocols`.

### 7.5 FastAPI backend connectivity

```powershell
# From the server — confirms the backend is reachable from Django's perspective
.\.venv\Scripts\python.exe -c "
import httpx, os
url = os.environ.get('API_BASE_URL', 'http://127.0.0.1:8888')
r = httpx.get(url + '/health', verify=False, timeout=5)
print(r.status_code, r.text[:200])
"
```

### 7.6 Power BI nav link

Log in, open the sidebar. The **Power BI Dashboard** link should point to the `PBIRS_CLAIMS_CAPACITY_URL` value — not a hardcoded IP. Right-click the link → Copy URL to verify.

### 7.7 Check application logs

```powershell
# Live tail of Daphne stderr (startup errors, unhandled exceptions)
Get-Content C:\Logs\CenteneForecasting\daphne_stderr.log -Tail 50 -Wait

# Structured LLM/chat logs (JSON format)
Get-Content (Get-ChildItem C:\Logs\CenteneForecasting\*.log | Sort LastWriteTime -Desc | Select -First 1).FullName -Tail 30
```

---

## 8. Common Issues and Fixes

### `KeyError: 'SECRET_KEY'` on startup

**Cause:** Environment variable not set, or the service started before the script finished writing to the registry.

```powershell
# Verify it is set in the Machine scope
[System.Environment]::GetEnvironmentVariable('SECRET_KEY', 'Machine')

# Restart service to pick up registry changes
Restart-Service CenteneForecasting
```

---

### `DisallowedHost` — 400 Bad Request

**Cause:** The server's hostname is not in `ALLOWED_HOSTS`.

```powershell
# Add the hostname without rerunning the full script
nssm set CenteneForecasting AppEnvironmentExtra "ALLOWED_HOSTS=new.hostname,localhost"
[System.Environment]::SetEnvironmentVariable('ALLOWED_HOSTS','new.hostname,localhost','Machine')
Restart-Service CenteneForecasting
```

---

### Static files return 404

**Cause:** `collectstatic` was not run.

```powershell
# Re-run collectstatic
cd C:\inetpub\wwwroot\Centene_Forecasting\centene_forecast_project
.\.venv\Scripts\python.exe manage.py collectstatic --noinput

# Confirm the directory exists and has files
Get-ChildItem .\staticfiles\ | Measure-Object
```

Static files are served by WhiteNoise through Daphne at `/centene_forecasting/static/` — no IIS virtual directory configuration needed.

---

### WebSocket handshake fails (403 or connection refused)

**Cause A:** `ALLOWED_HOSTS` does not include the server hostname — Django's `AllowedHostsOriginValidator` rejects the upgrade.
→ Fix: add the hostname to `ALLOWED_HOSTS` (see above).

**Cause B:** IIS ARR WebSocket rewrite rule is missing or ARR proxy not enabled.
→ Fix: re-check [Section 6](#6-configure-iis-as-reverse-proxy) and confirm the WebSocket IIS feature is installed.

---

### LDAP login fails — "Invalid credentials"

**Cause A:** The user has not been assigned a Django Group (ADMIN / MANAGER / VIEWER).
→ Fix: Log in as superuser at `/centene_forecasting/admin/`, go to **Users**, find the user, assign a group.

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

### `.env` file overrides production secrets

**Cause:** `django-environ` reads `.env` from the project directory if it exists, overriding the system environment variables.

```powershell
# Confirm no .env is present on the server
Test-Path C:\inetpub\wwwroot\Centene_Forecasting\centene_forecast_project\.env
# Should return False
```

If it exists and was accidentally deployed, delete it:
```powershell
Remove-Item C:\inetpub\wwwroot\Centene_Forecasting\centene_forecast_project\.env
Restart-Service CenteneForecasting
```

---

### Service fails to start after server reboot

**Cause:** NSSM service dependency on the network not configured — Daphne starts before the network stack is ready.

```powershell
# Add network dependency so the service waits for network
nssm set CenteneForecasting DependOnService Tcpip
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
Restart-Service CenteneForecasting
```

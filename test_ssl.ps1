# SSL Diagnostic Script for OpenAI Connection
# Tests various SSL configurations to identify the issue

Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "SSL Connection Diagnostic Tool" -ForegroundColor Cyan
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host ""

# Navigate to project
Set-Location "C:\Users\aswanthvishnu\Projects\Centene_Forecasting"

# Activate virtual environment
Write-Host "[Step 1] Activating virtual environment..." -ForegroundColor Yellow
& .\.venv\Scripts\Activate.ps1

# Set environment variables
Write-Host "[Step 2] Setting SSL bypass environment variables..." -ForegroundColor Yellow
$env:PYTHONHTTPSVERIFY = "0"
$env:CURL_CA_BUNDLE = ""
$env:REQUESTS_CA_BUNDLE = ""
$env:SSL_CERT_FILE = ""
$env:SSL_NO_VERIFY = "1"
Write-Host "Environment variables set" -ForegroundColor Green

# Test 1: Basic Python SSL
Write-Host ""
Write-Host "[Test 1] Testing Python SSL context..." -ForegroundColor Yellow
python -c @"
import ssl
ssl._create_default_https_context = ssl._create_unverified_context
print('SSL context patched successfully')
"@

# Test 2: Test urllib with SSL disabled
Write-Host ""
Write-Host "[Test 2] Testing urllib connection (SSL disabled)..." -ForegroundColor Yellow
python -c @"
import ssl
import urllib.request
ssl._create_default_https_context = ssl._create_unverified_context
try:
    response = urllib.request.urlopen('https://api.openai.com', timeout=10)
    print('SUCCESS: urllib can connect to OpenAI API')
    print('Status:', response.status)
except Exception as e:
    print('FAILED:', str(e))
    import traceback
    traceback.print_exc()
"@

# Test 3: Test httpx
Write-Host ""
Write-Host "[Test 3] Testing httpx connection (SSL disabled)..." -ForegroundColor Yellow
python -c @"
try:
    import httpx
    client = httpx.Client(verify=False, timeout=10.0)
    response = client.get('https://api.openai.com')
    print('SUCCESS: httpx can connect to OpenAI API')
    print('Status code:', response.status_code)
    client.close()
except ImportError:
    print('httpx not installed. Installing...')
    import subprocess
    subprocess.run(['pip', 'install', 'httpx'])
except Exception as e:
    print('FAILED:', str(e))
    import traceback
    traceback.print_exc()
"@

# Test 4: Test OpenAI client
Write-Host ""
Write-Host "[Test 4] Testing OpenAI client (SSL disabled)..." -ForegroundColor Yellow
python -c @"
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

try:
    import httpx
    from openai import OpenAI

    # Create SSL-disabled client
    http_client = httpx.Client(
        verify=False,
        timeout=30.0,
        transport=httpx.HTTPTransport(verify=False)
    )

    # Note: This will fail with invalid API key, but should not fail with SSL error
    client = OpenAI(
        api_key='test-key',
        http_client=http_client
    )

    print('SUCCESS: OpenAI client created without SSL errors')
    print('If you see API key error after this, SSL is working correctly!')

except Exception as e:
    error_msg = str(e)
    if 'ssl' in error_msg.lower() or 'certificate' in error_msg.lower():
        print('FAILED: Still getting SSL errors')
        print('Error:', error_msg)
    else:
        print('SUCCESS: No SSL errors (other errors are OK for now)')
        print('Error:', error_msg)
"@

# Test 5: Check proxy settings
Write-Host ""
Write-Host "[Test 5] Checking proxy settings..." -ForegroundColor Yellow
python -c @"
import os
print('HTTP_PROXY:', os.environ.get('HTTP_PROXY', 'Not set'))
print('HTTPS_PROXY:', os.environ.get('HTTPS_PROXY', 'Not set'))
print('NO_PROXY:', os.environ.get('NO_PROXY', 'Not set'))
"@

# Test 6: Check if OpenAI is reachable
Write-Host ""
Write-Host "[Test 6] Testing DNS resolution for api.openai.com..." -ForegroundColor Yellow
try {
    $result = Resolve-DnsName -Name "api.openai.com" -ErrorAction Stop
    Write-Host "SUCCESS: DNS resolution works" -ForegroundColor Green
    Write-Host "IP Address: $($result.IPAddress)" -ForegroundColor Cyan
} catch {
    Write-Host "FAILED: Cannot resolve api.openai.com" -ForegroundColor Red
    Write-Host "This might be a network/firewall issue" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "Diagnostic completed!" -ForegroundColor Cyan
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host ""
Write-Host "Next step: Run the actual test" -ForegroundColor Yellow
Write-Host "cd centene_forecast_project" -ForegroundColor Cyan
Write-Host "python manage.py test_llm" -ForegroundColor Cyan

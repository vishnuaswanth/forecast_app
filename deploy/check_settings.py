import os, sys, django

# Accept Django project directory as argument
if len(sys.argv) > 1:
    sys.path.insert(0, sys.argv[1])

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "centene_forecast_project.settings")
django.setup()

from django.conf import settings

print(f"DEBUG              : {settings.DEBUG}")
print(f"ALLOWED_HOSTS      : {settings.ALLOWED_HOSTS}")
print(f"CSRF_ORIGINS       : {settings.CSRF_TRUSTED_ORIGINS}")
print(f"API_BASE_URL       : {settings.API_BASE_URL}")
print(f"SECRET_KEY set     : {bool(settings.SECRET_KEY)}")
print(f"OPENAI key set     : {bool(settings.LLM_CONFIG.get('api_key'))}")
print(f"LLM_PROVIDER       : {settings.LLM_CONFIG.get('provider')}")
print(f"LLM_MODEL          : {settings.LLM_CONFIG.get('model')}")

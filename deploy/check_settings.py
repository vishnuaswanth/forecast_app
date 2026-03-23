import os, sys, django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "centene_forecast_project.settings")
django.setup()

from django.conf import settings

print(f"DEBUG              : {settings.DEBUG}")
print(f"ALLOWED_HOSTS      : {settings.ALLOWED_HOSTS}")
print(f"CSRF_ORIGINS       : {settings.CSRF_TRUSTED_ORIGINS}")
print(f"SSL_REDIRECT       : {settings.SECURE_SSL_REDIRECT}")
print(f"API_BASE_URL       : {settings.API_BASE_URL}")
print(f"SECRET_KEY set     : {bool(settings.SECRET_KEY)}")
print(f"OPENAI key set     : {bool(getattr(settings, 'OPENAI_API_KEY', ''))}")

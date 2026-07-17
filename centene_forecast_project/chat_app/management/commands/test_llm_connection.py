"""
Provider-aware LLM connectivity check. Uses the exact same client-construction
path as the running app (chat_app.services.llm_client_factory.build_llm_client),
so a pass here means the app will actually work - not just that credentials
look well-formed.

Usage:
    python manage.py test_llm_connection
    python manage.py test_llm_connection --provider azure_openai
"""
import copy

import httpx
from django.conf import settings
from django.core.management.base import BaseCommand
from langchain_core.messages import HumanMessage

from chat_app.services.llm_client_factory import AZURE_REQUIRED_FIELDS, build_llm_client

_SENSITIVE_FIELDS = {'api_key', 'azure_api_key'}


class Command(BaseCommand):
    help = 'Verify the configured LLM provider is reachable before starting the server'

    def add_arguments(self, parser):
        parser.add_argument(
            '--provider',
            default=None,
            help="Override settings.LLM_CONFIG['provider'] for this test run (e.g. azure_openai)",
        )

    def handle(self, *args, **options):
        llm_config = copy.deepcopy(getattr(settings, 'LLM_CONFIG', {}))
        if options['provider']:
            llm_config['provider'] = options['provider']
        provider = llm_config.get('provider', 'openai')

        self.stdout.write(self.style.SUCCESS(f"\nTesting LLM provider: {provider}"))
        self._print_config_summary(provider, llm_config)

        if provider == 'azure_openai':
            missing = [f for f in AZURE_REQUIRED_FIELDS if not llm_config.get(f)]
            if missing:
                self.stdout.write(self.style.ERROR(
                    f"\nFAILED: missing required Azure config field(s): {', '.join(missing)}"
                ))
                self.stdout.write(self.style.WARNING(
                    "Set these in .env: AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT, "
                    "AZURE_OPENAI_API_VERSION, AZURE_OPENAI_API_KEY"
                ))
                raise SystemExit(1)
        elif not llm_config.get('api_key'):
            self.stdout.write(self.style.ERROR("\nFAILED: CENTENE_OPENAI_API_KEY is not set"))
            raise SystemExit(1)

        http_client = httpx.Client(verify=False, timeout=30.0, transport=httpx.HTTPTransport(verify=False))
        http_async_client = httpx.AsyncClient(verify=False, timeout=30.0, transport=httpx.AsyncHTTPTransport(verify=False))

        try:
            llm = build_llm_client(llm_config, http_client, http_async_client)
            self.stdout.write("Sending test prompt...")
            response = llm.invoke([HumanMessage(content="Reply with exactly: OK")])
            self.stdout.write(self.style.SUCCESS(f"Response: {response.content!r}"))
            self.stdout.write(self.style.SUCCESS(f"\n[{provider}] connectivity test PASSED\n"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n[{provider}] connectivity test FAILED"))
            self.stdout.write(self.style.ERROR(str(e)))
            self._print_hint(provider, e)
            raise SystemExit(1)
        finally:
            http_client.close()

    def _print_config_summary(self, provider, llm_config):
        fields = AZURE_REQUIRED_FIELDS if provider == 'azure_openai' else ('api_key', 'model')
        for field in fields:
            value = llm_config.get(field)
            if field in _SENSITIVE_FIELDS:
                display = f"{'*' * 6}{value[-4:]}" if value else '(missing)'
            else:
                display = value if value else '(missing)'
            self.stdout.write(f"  {field}: {display}")

    def _print_hint(self, provider, error):
        if provider != 'azure_openai':
            return
        error_str = str(error).lower()
        if '404' in error_str or 'deploymentnotfound' in error_str.replace(' ', ''):
            self.stdout.write(self.style.WARNING(
                "Hint: Deployment not found - check AZURE_OPENAI_DEPLOYMENT matches the "
                "*deployment name* you set in Azure OpenAI Studio, not the underlying model name."
            ))
        elif '401' in error_str or 'unauthorized' in error_str or 'invalid api key' in error_str:
            self.stdout.write(self.style.WARNING("Hint: Invalid API key - check AZURE_OPENAI_API_KEY."))
        elif 'api_version' in error_str or 'api version' in error_str:
            self.stdout.write(self.style.WARNING(
                "Hint: Unsupported/mismatched API version - check AZURE_OPENAI_API_VERSION for this resource."
            ))

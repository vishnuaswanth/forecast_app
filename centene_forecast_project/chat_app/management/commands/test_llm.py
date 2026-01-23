"""
Management command to test OpenAI and LangChain integration.
Tests basic API connectivity and response generation.

Usage:
    python manage.py test_llm
"""
import os
import ssl
import warnings

# AGGRESSIVE SSL DISABLING FOR CORPORATE NETWORKS
# Step 1: Environment variables
os.environ['PYTHONHTTPSVERIFY'] = '0'
os.environ['CURL_CA_BUNDLE'] = ''
os.environ['REQUESTS_CA_BUNDLE'] = ''
os.environ['SSL_CERT_FILE'] = ''
os.environ['SSL_NO_VERIFY'] = '1'

# Step 2: SSL context monkey-patching
ssl._create_default_https_context = ssl._create_unverified_context

# Step 3: Disable all SSL warnings
warnings.filterwarnings('ignore')
try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    urllib3.disable_warnings()
except:
    pass

from django.core.management.base import BaseCommand
from django.conf import settings
from openai import OpenAI
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import httpx


class Command(BaseCommand):
    help = 'Test OpenAI and LangChain API integration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-openai',
            action='store_true',
            help='Skip direct OpenAI API test',
        )
        parser.add_argument(
            '--skip-langchain',
            action='store_true',
            help='Skip LangChain test',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n' + '='*70))
        self.stdout.write(self.style.SUCCESS('Testing OpenAI and LangChain Integration'))
        self.stdout.write(self.style.SUCCESS('='*70 + '\n'))

        # Check if API key is configured
        api_key = settings.LLM_CONFIG.get('api_key')
        if not api_key:
            self.stdout.write(self.style.ERROR('ERROR: OPENAI_API_KEY is not set!'))
            self.stdout.write(self.style.WARNING('\nPlease set it in your .env file:'))
            self.stdout.write(self.style.WARNING('OPENAI_API_KEY=sk-proj-your-key-here\n'))
            return

        self.stdout.write(self.style.SUCCESS(f'API Key configured: {api_key[:20]}...'))
        self.stdout.write(self.style.SUCCESS(f'Model: {settings.LLM_CONFIG.get("model")}\n'))

        # Pre-test: Check basic connectivity
        self.test_basic_connectivity()

        # Test 1: Direct OpenAI API
        if not options['skip_openai']:
            self.test_openai_direct(api_key)

        # Test 2: LangChain ChatOpenAI
        if not options['skip_langchain']:
            self.test_langchain(api_key)

        self.stdout.write(self.style.SUCCESS('\n' + '='*70))
        self.stdout.write(self.style.SUCCESS('All tests completed successfully!'))
        self.stdout.write(self.style.SUCCESS('='*70 + '\n'))

    def test_basic_connectivity(self):
        """Test basic network connectivity to OpenAI"""
        self.stdout.write(self.style.WARNING('\n[PRE-TEST] Basic Connectivity Check'))
        self.stdout.write('-' * 70)

        try:
            # Test with httpx
            self.stdout.write('Testing connection with httpx (SSL disabled)...')
            client = httpx.Client(
                verify=False,
                timeout=10.0,
                transport=httpx.HTTPTransport(verify=False)
            )
            response = client.get('https://api.openai.com')
            self.stdout.write(self.style.SUCCESS(f'Connection successful! Status: {response.status_code}'))
            client.close()

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Connection failed: {str(e)}'))
            self.stdout.write(self.style.WARNING('\nThis might be a network/proxy issue, not just SSL.'))
            self.stdout.write(self.style.WARNING('Check if you need proxy settings or if OpenAI is blocked.\n'))
            raise

    def test_openai_direct(self, api_key):
        """Test direct OpenAI API call"""
        self.stdout.write(self.style.WARNING('\n[TEST 1] Direct OpenAI API Call'))
        self.stdout.write('-' * 70)

        try:
            # Create httpx client with all SSL verification disabled
            http_client = httpx.Client(
                verify=False,
                timeout=30.0,
                follow_redirects=True,
                transport=httpx.HTTPTransport(
                    verify=False,
                    retries=3
                )
            )

            self.stdout.write(f'HTTP Client created with SSL verification: {http_client._transport._pool._ssl_context.check_hostname if hasattr(http_client, "_transport") else "disabled"}')

            client = OpenAI(api_key=api_key, http_client=http_client)

            self.stdout.write('Sending test message to OpenAI...')

            response = client.chat.completions.create(
                model="gpt-4o-mini",  # Use cheaper model for testing
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that responds concisely."},
                    {"role": "user", "content": "Say 'Hello! OpenAI API is working correctly.' in exactly that format."}
                ],
                max_tokens=50,
                temperature=0
            )

            result = response.choices[0].message.content

            self.stdout.write(self.style.SUCCESS('\nResponse received:'))
            self.stdout.write(self.style.SUCCESS(f'"{result}"'))
            self.stdout.write(self.style.SUCCESS(f'\nTokens used: {response.usage.total_tokens}'))
            self.stdout.write(self.style.SUCCESS('[TEST 1] PASSED ✓'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n[TEST 1] FAILED ✗'))
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
            raise

    def test_langchain(self, api_key):
        """Test LangChain ChatOpenAI"""
        self.stdout.write(self.style.WARNING('\n[TEST 2] LangChain ChatOpenAI'))
        self.stdout.write('-' * 70)

        try:
            # Create httpx client with all SSL verification disabled
            http_client = httpx.Client(
                verify=False,
                timeout=30.0,
                follow_redirects=True,
                transport=httpx.HTTPTransport(
                    verify=False,
                    retries=3
                )
            )

            self.stdout.write('HTTP Client configured with SSL verification disabled')

            llm = ChatOpenAI(
                model="gpt-4o-mini",  # Use cheaper model for testing
                temperature=0,
                openai_api_key=api_key,
                max_tokens=100,
                http_client=http_client
            )

            self.stdout.write('Testing LangChain message format...')

            # Test with LangChain message format
            messages = [
                SystemMessage(content="You are a forecast data assistant for the Centene forecasting application."),
                HumanMessage(content="Extract the following: month=January, year=2025, platform=Amisys. Respond with just 'Parameters extracted successfully'")
            ]

            response = llm.invoke(messages)

            self.stdout.write(self.style.SUCCESS('\nResponse received:'))
            self.stdout.write(self.style.SUCCESS(f'"{response.content}"'))
            self.stdout.write(self.style.SUCCESS('[TEST 2] PASSED ✓'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n[TEST 2] FAILED ✗'))
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
            raise

    def test_langchain_categorization(self, api_key):
        """Test LangChain for intent categorization (like Phase 2 will use)"""
        self.stdout.write(self.style.WARNING('\n[TEST 3] LangChain Intent Categorization'))
        self.stdout.write('-' * 70)

        try:
            # Create httpx client with all SSL verification disabled
            http_client = httpx.Client(
                verify=False,
                timeout=30.0,
                follow_redirects=True,
                transport=httpx.HTTPTransport(
                    verify=False,
                    retries=3
                )
            )

            llm = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0,
                openai_api_key=api_key,
                max_tokens=200,
                http_client=http_client
            )

            prompt = """You are a forecast assistant. Categorize this user request:
User: "Show me forecast data for January 2025"

Respond in JSON format:
{
    "category": "forecast_query",
    "parameters": {"month": 1, "year": 2025}
}"""

            messages = [HumanMessage(content=prompt)]
            response = llm.invoke(messages)

            self.stdout.write(self.style.SUCCESS('\nCategorization response:'))
            self.stdout.write(self.style.SUCCESS(response.content))
            self.stdout.write(self.style.SUCCESS('[TEST 3] PASSED ✓'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n[TEST 3] FAILED ✗'))
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
            raise

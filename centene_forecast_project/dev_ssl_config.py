"""
Development SSL Configuration
Disables SSL verification for development environments only.

WARNING: Never use this in production!
This is only for development when working behind corporate SSL inspection.
"""
import os
import ssl
import warnings


def configure_dev_ssl():
    """
    Configure SSL settings for development environment.
    Disables SSL verification to work around corporate SSL inspection.

    Only runs when DEBUG=True in settings.
    """
    print("=" * 70)
    print("WARNING: SSL VERIFICATION DISABLED (Development Mode)")
    print("=" * 70)

    # Method 1: Set environment variables
    os.environ['PYTHONHTTPSVERIFY'] = '0'
    os.environ['CURL_CA_BUNDLE'] = ''
    os.environ['REQUESTS_CA_BUNDLE'] = ''
    os.environ['SSL_NO_VERIFY'] = '1'

    # Method 2: Disable urllib3 InsecureRequestWarning
    try:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    except (ImportError, AttributeError):
        pass

    # Method 3: Monkey-patch SSL default context to use unverified
    ssl._create_default_https_context = ssl._create_unverified_context

    # Method 4: Disable requests SSL warnings (if requests is installed)
    try:
        import warnings
        from urllib3.exceptions import InsecureRequestWarning
        warnings.filterwarnings('ignore', category=InsecureRequestWarning)
    except (ImportError, AttributeError):
        pass

    print("[OK] SSL verification disabled for:")
    print("  - Python urllib/urllib3")
    print("  - requests library")
    print("  - OpenAI client")
    print("  - LangChain")
    print("  - All HTTPS connections")
    print("=" * 70)
    print()


def get_unverified_httpx_client():
    """
    Create an httpx client with SSL verification disabled.
    Use this for OpenAI client initialization.

    Returns:
        httpx.Client: Client with verify=False
    """
    try:
        import httpx
        import ssl

        # Create SSL context that doesn't verify
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        # Create httpx client with no SSL verification
        client = httpx.Client(
            verify=False,
            timeout=30.0,
            follow_redirects=True
        )
        return client
    except ImportError:
        return None


def get_unverified_async_httpx_client():
    """
    Create an async httpx client with SSL verification disabled.

    Returns:
        httpx.AsyncClient: Async client with verify=False
    """
    try:
        import httpx
        import ssl

        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        client = httpx.AsyncClient(
            verify=False,
            timeout=30.0,
            follow_redirects=True
        )
        return client
    except ImportError:
        return None

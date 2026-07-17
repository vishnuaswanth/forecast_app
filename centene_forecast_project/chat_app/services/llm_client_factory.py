"""
Builds the LangChain chat client for the configured LLM provider.

Shared by LLMService and the `test_llm_connection` management command so both
use the exact same construction path - a passing connectivity test guarantees
the app will actually work, not just that credentials look well-formed.

Provider priority for future integrations (easiest -> hardest):
  1. azure_openai - implemented. Same BaseChatModel interface as ChatOpenAI.
  2. anthropic     - not yet implemented (needs langchain-anthropic).
  3. home-grown    - not yet implemented (effort depends on target API shape).
"""
from langchain_openai import ChatOpenAI

AZURE_REQUIRED_FIELDS = ('azure_endpoint', 'azure_deployment', 'azure_api_version', 'azure_api_key')


def build_llm_client(llm_config: dict, http_client, http_async_client):
    """Construct the LangChain chat client for llm_config['provider']."""
    provider = llm_config.get('provider', 'openai')
    common = dict(
        model=llm_config.get('model', 'gpt-4o-mini'),
        temperature=llm_config.get('temperature', 0.1),
        max_tokens=llm_config.get('max_tokens', 4096),
        http_client=http_client,
        http_async_client=http_async_client,
    )

    if provider == 'azure_openai':
        from langchain_openai import AzureChatOpenAI

        missing = [f for f in AZURE_REQUIRED_FIELDS if not llm_config.get(f)]
        if missing:
            raise ValueError(f"Azure OpenAI config missing: {', '.join(missing)}")

        return AzureChatOpenAI(
            azure_endpoint=llm_config['azure_endpoint'],
            azure_deployment=llm_config['azure_deployment'],
            api_version=llm_config['azure_api_version'],
            api_key=llm_config['azure_api_key'],
            **common,
        )

    return ChatOpenAI(openai_api_key=llm_config.get('api_key'), **common)

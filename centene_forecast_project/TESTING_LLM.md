# Testing OpenAI and LangChain Integration

This guide will help you test that OpenAI and LangChain are working correctly before enabling Phase 2.

## Prerequisites

1. **OpenAI API Key**: Get one from https://platform.openai.com/api-keys
2. **LLM Dependencies Installed**: Should already be done
3. **.env file configured**: With your API key

---

## Step 1: Configure Your API Key

### Create .env file

```bash
cd /Users/aswanthvishnu/Projects/Centene_Forecasting/centene_forecast_project

# Copy example file
cp .env.example .env

# Edit with your API key
nano .env  # or use any text editor
```

### Add your API key

```bash
OPENAI_API_KEY=sk-proj-your-actual-key-here
```

**Important**: Replace `sk-proj-your-actual-key-here` with your real API key!

---

## Step 2: Run the Test Command

```bash
# Activate virtual environment
source /Users/aswanthvishnu/Projects/Centene_Forecasting/.venv/bin/activate

# Navigate to project
cd /Users/aswanthvishnu/Projects/Centene_Forecasting/centene_forecast_project

# Run tests
python manage.py test_llm
```

---

## Expected Output

If everything works correctly, you should see:

```
======================================================================
Testing OpenAI and LangChain Integration
======================================================================

API Key configured: sk-proj-abc123456...
Model: gpt-4-turbo-preview

[TEST 1] Direct OpenAI API Call
----------------------------------------------------------------------
Sending test message to OpenAI...

Response received:
"Hello! OpenAI API is working correctly."

Tokens used: 25
[TEST 1] PASSED ✓

[TEST 2] LangChain ChatOpenAI
----------------------------------------------------------------------
Testing LangChain message format...

Response received:
"Parameters extracted successfully"
[TEST 2] PASSED ✓

======================================================================
All tests completed successfully!
======================================================================
```

---

## Common Errors and Fixes

### Error: "OPENAI_API_KEY is not set!"

**Solution**: Create `.env` file with your API key

```bash
echo "OPENAI_API_KEY=sk-proj-your-key" > .env
```

### Error: "AuthenticationError: Incorrect API key"

**Solutions**:
1. Check your API key is correct (copy it again from OpenAI)
2. Make sure there are no extra spaces
3. Key should start with `sk-proj-` or `sk-`

### Error: "RateLimitError: Rate limit reached"

**Solutions**:
1. Wait a few minutes and try again
2. Check your OpenAI account has credits
3. Upgrade your OpenAI plan if needed

### Error: "Connection timeout"

**Solutions**:
1. Check your internet connection
2. Try again in a few minutes
3. Check if OpenAI API is down: https://status.openai.com/

### Error: "Module not found: openai"

**Solution**: Install LLM dependencies

```bash
source /Users/aswanthvishnu/Projects/Centene_Forecasting/.venv/bin/activate
pip install openai langchain langchain-openai
```

---

## Step 3: Test Individual Components

### Test only OpenAI (skip LangChain)

```bash
python manage.py test_llm --skip-langchain
```

### Test only LangChain (skip direct OpenAI)

```bash
python manage.py test_llm --skip-openai
```

---

## Step 4: Check API Usage and Costs

After testing, check your OpenAI dashboard to see API usage:

1. Go to https://platform.openai.com/usage
2. Look for the test requests
3. Each test costs approximately:
   - Test 1: ~$0.0001 (about 50 tokens)
   - Test 2: ~$0.0002 (about 100 tokens)
   - **Total**: Less than $0.001 per test run

Using `gpt-4o-mini` model keeps costs extremely low for testing.

---

## Step 5: Enable Phase 2 (Real LLM)

Once tests pass, you can enable real LLM in chat:

### Update settings.py

```python
# File: centene_forecast_project/settings.py

CHAT_CONFIG = {
    'enabled': True,
    'mock_mode': False,  # ← Change from True to False
    'max_conversation_history': 50,
    'rate_limit_messages_per_minute': 10,
}
```

### Restart server

```bash
python manage.py runserver
```

### Test in chat

1. Open chat widget
2. Type: "Show me forecast data for January 2025"
3. Should get intelligent response instead of keyword matching

---

## Troubleshooting

### Test passes but chat doesn't work

1. **Check settings**: Ensure `mock_mode=False`
2. **Restart server**: Django caches settings
3. **Check browser console**: Look for WebSocket errors
4. **Check Django logs**: Look for Python exceptions

### LangChain version issues

If you get import errors, update to latest:

```bash
pip install --upgrade openai langchain langchain-openai
```

### Want to use different model

Edit `settings.py`:

```python
LLM_CONFIG = {
    'model': 'gpt-4o-mini',  # Cheaper for testing
    # or
    'model': 'gpt-4o',  # More powerful
    # or
    'model': 'gpt-4-turbo-preview',  # Current default
}
```

**Model costs** (per 1M tokens input/output):
- `gpt-4o-mini`: $0.15 / $0.60 (cheapest, fast)
- `gpt-4o`: $2.50 / $10.00 (balanced)
- `gpt-4-turbo-preview`: $10.00 / $30.00 (most powerful)

For production chat, we recommend `gpt-4o-mini` or `gpt-4o`.

---

## Security Checklist

Before deploying to production:

- [ ] API key is in `.env` file (not hardcoded)
- [ ] `.env` is in `.gitignore`
- [ ] Different API keys for dev/staging/production
- [ ] Rate limiting enabled in `CHAT_CONFIG`
- [ ] Monitoring API usage on OpenAI dashboard
- [ ] Set spending limits on OpenAI account

---

## Next Steps

After successful testing:

1. **Update .gitignore**: Ensure `.env` is ignored
2. **Enable Phase 2**: Set `mock_mode=False`
3. **Monitor costs**: Watch OpenAI usage dashboard
4. **Add logging**: Track LLM requests and responses
5. **Implement caching**: Cache common queries to reduce API calls

---

## Support

If tests fail or you need help:

1. Check error message carefully
2. Verify API key is correct
3. Check OpenAI dashboard for errors
4. Review Django logs
5. Test with simpler prompt first

**Common test prompts**:
- "Hello" (very simple)
- "What is 2+2?" (basic logic)
- "Show me forecast" (app-specific)

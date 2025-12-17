# Quick guide to work around quota limits

## Current Situation
Your Gemini API free tier has very limited quotas:
- gemini-2.5-flash: 20 requests/day (exhausted)
- gemini-2.0-flash: 0 quota available
- All other Gemini 2.x models: Limited/exhausted

## Options:

### Option 1: Use Mock Mode (Recommended for Testing)
```python
# In config/settings.py
LLM_PROVIDER = "mock"
```
This will generate template HVAC configs without API calls.

### Option 2: Wait Until Tomorrow
Quotas reset daily (typically at midnight PST).

### Option 3: Upgrade to Paid Gemini API
- Remove quota restrictions
- Cost: Pay-as-you-go (very affordable)
- Sign up at: https://ai.google.dev/pricing

### Option 4: Use Different API Provider
If you have API keys for:
- **OpenAI**: gpt-4o-mini (affordable, $0.15/1M tokens)
- **Anthropic**: claude-3-haiku (fast, affordable)

Example:
```python
# In config/settings.py
LLM_PROVIDER = "openai"
LLM_MODEL = "gpt-4o-mini"

# In .env file
OPENAI_API_KEY=your_key_here
```

### Option 5: Try gemini-2.0-flash-lite-001
Already updated settings.py to try this - it might have separate quotas.

## Your API Quota Status
Based on errors, your free tier has:
- ✗ gemini-2.5-flash: 20/day limit - EXHAUSTED
- ✗ gemini-2.0-flash: 0 quota - NOT AVAILABLE
- ? gemini-2.0-flash-lite-001: Unknown - TRYING NOW
- ✗ All models: Input token quota exhausted

## Recommendation
For development/testing on Linux, either:
1. Use Mock mode to test pipeline logic
2. Wait until tomorrow to continue with Gemini
3. Get a paid API key (costs ~$0.10 for 1000 HVAC generations)

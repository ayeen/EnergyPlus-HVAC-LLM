"""
Check Gemini API quota and usage information
"""
import os
from pathlib import Path
import google.generativeai as genai

# Load .env file
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    with open(env_path, 'r') as f:
        for line in f:
            if '=' in line and not line.strip().startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value

# Get API key
api_key = os.environ.get('GEMINI_API_KEY')
if not api_key:
    print("ERROR: GEMINI_API_KEY not set in .env file")
    exit(1)

# Configure
genai.configure(api_key=api_key)

print("=" * 70)
print("GEMINI API QUOTA INFORMATION")
print("=" * 70)
print()

# List all available models with their details
print("Available Models & Their Capabilities:")
print("-" * 70)

for model in genai.list_models():
    if 'generateContent' in model.supported_generation_methods:
        print(f"\n✓ Model: {model.name}")
        print(f"  Display Name: {model.display_name}")
        
        # Show rate limits if available
        if hasattr(model, 'rate_limits'):
            print(f"  Rate Limits:")
            for limit in model.rate_limits:
                print(f"    - {limit}")
        
        # Show input/output token limits
        if hasattr(model, 'input_token_limit'):
            print(f"  Input Token Limit: {model.input_token_limit:,}")
        if hasattr(model, 'output_token_limit'):
            print(f"  Output Token Limit: {model.output_token_limit:,}")
        
        # Show supported methods
        print(f"  Supported Methods: {', '.join(model.supported_generation_methods)}")

print()
print("=" * 70)
print("QUOTA LIMITS (Free Tier)")
print("=" * 70)
print("""
Typical Free Tier Limits:

Gemini 1.5 Models (if available):
  • gemini-1.5-flash: 1,500 requests/day, 15 requests/min
  • gemini-1.5-pro: 50 requests/day, 2 requests/min

Gemini 2.0/2.5 Models:
  • gemini-2.5-flash: 20 requests/day (very limited)
  • gemini-2.0-flash: Varies by account
  • gemini-2.0-flash-lite: May have separate limits

To check your ACTUAL current usage:
1. Visit: https://ai.google.dev/usage?tab=rate-limit
2. Sign in with the Google account that owns the API key
3. View real-time usage and remaining quota

To upgrade to paid tier (no limits):
1. Visit: https://ai.google.dev/pricing
2. Enable billing on your Google Cloud project
3. Pay-as-you-go pricing (very affordable)
""")

print()
print("=" * 70)
print("CURRENT CONFIGURATION")
print("=" * 70)
print(f"API Key: {api_key[:20]}... (hidden)")
print(f"Key Length: {len(api_key)} characters")
print()
print("To check usage dashboard:")
print("  https://ai.google.dev/usage?tab=rate-limit")
print()

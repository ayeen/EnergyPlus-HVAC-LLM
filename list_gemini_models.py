"""
List available Gemini models
"""
import os
import sys
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
    print("Please create .env file with: GEMINI_API_KEY=your_key_here")
    exit(1)

# Configure
genai.configure(api_key=api_key)

# List models
print("Available Gemini models:")
print("-" * 60)
for model in genai.list_models():
    if 'generateContent' in model.supported_generation_methods:
        print(f"✓ {model.name}")
        print(f"  Display Name: {model.display_name}")
        print(f"  Methods: {', '.join(model.supported_generation_methods)}")
        print()

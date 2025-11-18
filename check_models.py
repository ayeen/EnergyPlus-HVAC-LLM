#!/usr/bin/env python3
"""
Check Available Gemini Models and Test Generation
"""

import os
from pathlib import Path
import google.generativeai as genai

# Load .env file
env_file = Path('.env')
if env_file.exists():
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                key, value = line.split('=', 1)
                os.environ[key] = value

api_key = os.environ.get('GEMINI_API_KEY')
if not api_key:
    print("No GEMINI_API_KEY found")
    exit(1)

genai.configure(api_key=api_key)

print("--- Available Models ---")
try:
    models = genai.list_models()
    for model in models:
        if 'generateContent' in model.supported_generation_methods:
            print(f"✓ {model.name} - {model.display_name}")
except Exception as e:
    print(f"Error listing models: {e}")

print("\n--- Testing Generation with Different Models ---")

# Test models to try
test_models = [
    'gemini-1.5-flash',
    'gemini-1.5-pro', 
    'gemini-pro',
    'models/gemini-1.5-flash',
    'models/gemini-1.5-pro'
]

for model_name in test_models:
    try:
        print(f"\nTesting {model_name}...")
        model = genai.GenerativeModel(model_name)
        
        response = model.generate_content(
            "Generate a brief HVAC system description.",
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=100,
                temperature=0.3,
            )
        )
        
        print(f"✓ {model_name} works!")
        print(f"Response: {response.text[:80]}...")
        break  # Stop at first working model
        
    except Exception as e:
        print(f"✗ {model_name}: {str(e)[:100]}...")

print("\n=== Model Test Complete ===")
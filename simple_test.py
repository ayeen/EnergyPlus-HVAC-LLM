#!/usr/bin/env python3
"""
Simple Gemini Test with Basic Prompt
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
genai.configure(api_key=api_key)

print("=== Simple Gemini Test ===\n")

# Test with minimal safety settings
safety_settings = [
    {
        "category": "HARM_CATEGORY_HARASSMENT",
        "threshold": "BLOCK_NONE",
    },
    {
        "category": "HARM_CATEGORY_HATE_SPEECH", 
        "threshold": "BLOCK_NONE",
    },
    {
        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "threshold": "BLOCK_NONE", 
    },
    {
        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
        "threshold": "BLOCK_NONE",
    },
]

try:
    model = genai.GenerativeModel(
        'gemini-2.5-flash',
        safety_settings=safety_settings
    )
    
    # Very simple test
    print("Testing simple prompt...")
    response = model.generate_content("What is HVAC?")
    
    print(f"Response: {response}")
    print(f"Candidates: {len(response.candidates) if response.candidates else 0}")
    
    if response.candidates:
        for i, candidate in enumerate(response.candidates):
            print(f"Candidate {i}: finish_reason={candidate.finish_reason}")
            if candidate.content and candidate.content.parts:
                print(f"Text: {candidate.content.parts[0].text[:100]}...")
            else:
                print("No content parts")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

print("\n=== Test Complete ===")
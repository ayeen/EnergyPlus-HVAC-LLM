#!/usr/bin/env python3
"""
Test HVAC-LLM Gemini Integration
"""

import os
import sys
from pathlib import Path

# Manually load .env file
env_file = Path('.env')
if env_file.exists():
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                key, value = line.split('=', 1)
                os.environ[key] = value

print("=== HVAC-LLM Gemini Integration Test ===\n")

# Add current directory to path
sys.path.insert(0, str(Path.cwd()))

try:
    from src.agents.llm_interface import UniversalLLM
    print("✓ UniversalLLM imported successfully")
    
    # Test with auto provider (should detect Gemini)
    print("\n--- Testing Auto Provider ---")
    llm = UniversalLLM(provider='auto')
    print(f"✓ Auto-detected provider: {llm.provider}")
    
    # Test with explicit Gemini provider
    print("\n--- Testing Explicit Gemini Provider ---")
    llm_gemini = UniversalLLM(provider='gemini')
    print(f"✓ Explicit provider: {llm_gemini.provider}")
    
    if llm_gemini.provider == 'gemini':
        print("\n--- Testing Gemini Generation ---")
        
        # Test 1: Simple HVAC system generation
        response1 = llm_gemini.generate(
            system_prompt="You are an HVAC design assistant for EnergyPlus building simulations.",
            user_prompt="Generate a simple VRF (Variable Refrigerant Flow) system configuration for 2 office zones: Office_Zone_1 and Office_Zone_2. Include thermostats and basic settings.",
            max_tokens=300
        )
        
        if response1:
            print("✓ Test 1 - VRF Generation Successful!")
            print(f"Response length: {len(response1)} characters")
            print(f"Sample: {response1[:150]}...")
        else:
            print("✗ Test 1 - Empty response")
        
        # Test 2: Error correction scenario
        response2 = llm_gemini.generate(
            system_prompt="You are an EnergyPlus error correction assistant.",
            user_prompt="Fix this error: 'Thermostat_Office1 not found'. The IDF file has a zone named Office_Zone_1 but references Thermostat_Office1 which doesn't exist.",
            max_tokens=200
        )
        
        if response2:
            print("\n✓ Test 2 - Error Correction Successful!")
            print(f"Response length: {len(response2)} characters")
            print(f"Sample: {response2[:150]}...")
        else:
            print("\n✗ Test 2 - Empty response")
            
        # Test 3: Configuration advice
        response3 = llm_gemini.generate(
            system_prompt="You are an HVAC configuration expert.",
            user_prompt="What are the key parameters for a VRF system in EnergyPlus? Provide a brief list.",
            max_tokens=150
        )
        
        if response3:
            print("\n✓ Test 3 - Configuration Advice Successful!")
            print(f"Response length: {len(response3)} characters")
            print(f"Sample: {response3[:150]}...")
        else:
            print("\n✗ Test 3 - Empty response")
            
    else:
        print(f"✗ Expected 'gemini' provider, got '{llm_gemini.provider}'")
        
except Exception as e:
    print(f"✗ Test failed: {e}")
    import traceback
    traceback.print_exc()

print("\n=== Integration Test Complete ===")
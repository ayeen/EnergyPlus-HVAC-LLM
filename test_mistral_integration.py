#!/usr/bin/env python3
"""
Test Mistral Fine-tuned Model Integration
==========================================

This script tests the integrated Mistral fine-tuned model in the multi-agent
HVAC system. It verifies that the model works correctly with the pipeline.

Usage:
    python test_mistral_integration.py

To switch back to Gemini:
    1. Edit config/settings.py
    2. Change LLM_PROVIDER = "gemini"
    3. Run your pipeline normally

Author: HVAC-LLM Integration
Date: December 12, 2025
"""

import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from src.pipeline import HVACLLMPipeline

def test_mistral_small_building():
    """Test Mistral with a small 3-zone building"""
    
    print("=" * 80)
    print("TEST 1: MISTRAL INTEGRATION - SMALL OFFICE BUILDING")
    print("=" * 80)
    print(f"\nProvider: {Config.LLM_PROVIDER}")
    print(f"Model Path: {Config.MISTRAL_FINETUNED_PATH}")
    print()
    
    # Initialize pipeline
    pipeline = HVACLLMPipeline()
    
    # Use a base IDF file
    base_idf = "data/base_idfs/4ZoneWithShading_Simple_2_NoHVAC.idf"
    
    # Define zones (auto-detection will also work)
    zones = ["ZONE ONE", "ZONE TWO", "ZONE THREE"]
    
    # User request
    user_request = "Design a VRF system with heat recovery for energy efficiency"
    
    # Run pipeline
    output_name = f"mistral_test_small_office_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    try:
        results = pipeline.run(
            base_idf=base_idf,
            zones=zones,
            output_name=output_name,
            system_name="Office_VRF_System",
            user_request=user_request,
            enable_quick_validation=True
        )
        
        print("\n" + "=" * 80)
        print("TEST 1 RESULTS")
        print("=" * 80)
        print(f"Status: {results.get('final_status', 'UNKNOWN')}")
        
        if results.get('final_status') == 'SUCCESS':
            print("✅ Mistral integration test PASSED!")
            print(f"\nGenerated files:")
            print(f"  - outputs/generated_idfs/{output_name}_FINAL.idf")
            print(f"  - outputs/logs/{output_name}_pipeline.json")
        else:
            print("⚠️  Test completed with status:", results.get('final_status'))
            if 'error' in results:
                print(f"Error: {results['error']}")
        
        return results
        
    except Exception as e:
        print(f"\n❌ Test FAILED with exception: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_mistral_auto_detection():
    """Test Mistral with auto zone detection"""
    
    print("\n\n" + "=" * 80)
    print("TEST 2: MISTRAL INTEGRATION - AUTO ZONE DETECTION")
    print("=" * 80)
    print(f"\nProvider: {Config.LLM_PROVIDER}")
    print()
    
    # Initialize pipeline
    pipeline = HVACLLMPipeline()
    
    # Use a base IDF file
    base_idf = "data/base_idfs/4ZoneWithShading_Simple_2_NoHVAC.idf"
    
    # Let it auto-detect zones
    zones = None  # Auto-detect
    
    # User request
    user_request = "Create a high-efficiency VRF system with intelligent thermostat controls"
    
    # Run pipeline
    output_name = f"mistral_test_auto_detect_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    try:
        results = pipeline.run(
            base_idf=base_idf,
            zones=zones,  # Auto-detect
            output_name=output_name,
            system_name="AutoDetect_VRF_System",
            user_request=user_request,
            enable_quick_validation=True
        )
        
        print("\n" + "=" * 80)
        print("TEST 2 RESULTS")
        print("=" * 80)
        print(f"Status: {results.get('final_status', 'UNKNOWN')}")
        print(f"Zones Auto-detected: {results.get('zones_auto_detected', False)}")
        print(f"Number of zones: {len(results.get('zones', []))}")
        
        if results.get('final_status') == 'SUCCESS':
            print("✅ Auto-detection test PASSED!")
        else:
            print("⚠️  Test completed with status:", results.get('final_status'))
            if 'error' in results:
                print(f"Error: {results['error']}")
        
        return results
        
    except Exception as e:
        print(f"\n❌ Test FAILED with exception: {e}")
        import traceback
        traceback.print_exc()
        return None


def compare_providers_info():
    """Display information about switching between providers"""
    
    print("\n\n" + "=" * 80)
    print("PROVIDER SWITCHING GUIDE")
    print("=" * 80)
    
    print("""
To switch between Mistral and Gemini:

1. Edit config/settings.py:
   
   For Mistral:
     LLM_PROVIDER = "mistral"
   
   For Gemini:
     LLM_PROVIDER = "gemini"

2. Restart your Python session or application

Current Configuration:
""")
    
    print(f"  Provider: {Config.LLM_PROVIDER}")
    
    if Config.LLM_PROVIDER == "mistral":
        print(f"  Mistral Base Model: {Config.MISTRAL_BASE_MODEL}")
        print(f"  Mistral Fine-tuned Path: {Config.MISTRAL_FINETUNED_PATH}")
        print(f"  Temperature: {Config.MISTRAL_TEMPERATURE}")
        print(f"  Top-P: {Config.MISTRAL_TOP_P}")
        print(f"  Max Tokens per Object: {Config.MISTRAL_MAX_TOKENS_PER_OBJECT}")
    elif Config.LLM_PROVIDER == "gemini":
        print(f"  Gemini Model: {Config.LLM_MODEL}")
        print(f"  Temperature: {Config.LLM_TEMPERATURE}")
        print(f"  Max Tokens: {Config.LLM_MAX_TOKENS}")
    
    print("""
Both providers use the same multi-agent architecture:
  - Agent 1: HVAC Generator (uses Mistral or Gemini)
  - Agent 1.5: Quick Validator (uses Mistral or Gemini)
  - Agent 3: Error Corrector (uses Mistral or Gemini)

Mistral uses iterative generation for better quality:
  1. Generate System VRF
  2. Generate Zone VRFs (one per zone)
  3. Generate Thermostats (one per zone)
  
This approach reduces hallucinations and ensures complete systems.
""")


def main():
    """Main test runner"""
    
    print("\n" + "╔" + "═" * 78 + "╗")
    print("║" + " " * 78 + "║")
    print("║" + "   Mistral Fine-tuned Model Integration Test".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("║" + "  Testing the integrated Mistral model in multi-agent HVAC system".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("╚" + "═" * 78 + "╝\n")
    
    # Check configuration
    if Config.LLM_PROVIDER != "mistral":
        print("⚠️  WARNING: Current LLM_PROVIDER is set to:", Config.LLM_PROVIDER)
        print("To test Mistral, edit config/settings.py and set:")
        print("  LLM_PROVIDER = 'mistral'")
        print()
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            print("Test cancelled.")
            return
    
    # Check if model exists
    if not os.path.exists(Config.MISTRAL_FINETUNED_PATH):
        print(f"❌ ERROR: Mistral model not found at:")
        print(f"   {Config.MISTRAL_FINETUNED_PATH}")
        print()
        print("Please ensure the fine-tuned model is available at the configured path.")
        return
    
    print(f"✓ Model found: {Config.MISTRAL_FINETUNED_PATH}\n")
    
    # Run tests
    results1 = test_mistral_small_building()
    
    if results1:
        results2 = test_mistral_auto_detection()
    
    # Display provider info
    compare_providers_info()
    
    print("\n" + "=" * 80)
    print("TESTING COMPLETE")
    print("=" * 80)
    print()


if __name__ == "__main__":
    main()

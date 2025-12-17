#!/usr/bin/env python3
"""
Simple test to verify Scenario 1 (Gemini) and Scenario 2 (Mistral+RAG) work correctly.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.pipeline import HVACLLMPipeline
from src.agents.llm_interface import UniversalLLM

def test_scenario_1():
    """Test Scenario 1: Gemini with RAG (matching working implementation)"""
    print("\n" + "="*70)
    print("TESTING SCENARIO 1: Gemini + RAG")
    print("="*70)
    
    # Reset LLM to ensure fresh instance
    UniversalLLM.reset()
    
    try:
        # Initialize with Gemini WITH RAG (matching working implementation)
        pipeline = HVACLLMPipeline(use_rag=True, llm_provider="gemini")
        
        # Run a simple test - use auto zone detection
        result = pipeline.run(
            base_idf="data/base_idfs/4ZoneWithShading_Simple_2_NoHVAC.idf",
            user_request="Design a simple VRF system for heating and cooling",
            zones=None,  # Auto-detect zones
            output_name="test_scenario1_gemini"
        )
        
        print(f"\n📊 Scenario 1 Results:")
        print(f"   Status: {result.get('final_status', 'UNKNOWN')}")
        print(f"   HVAC Objects: {result.get('hvac_objects_count', 0)}")
        print(f"   Iterations: {result.get('iterations', 0)}")
        
        return result.get('final_status') == 'SUCCESS'
        
    except Exception as e:
        print(f"\n❌ Scenario 1 Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_scenario_2():
    """Test Scenario 2: Mistral with RAG"""
    print("\n" + "="*70)
    print("TESTING SCENARIO 2: Mistral + RAG")
    print("="*70)
    
    # Reset LLM to ensure fresh instance
    UniversalLLM.reset()
    
    try:
        # Initialize with Mistral, with RAG
        pipeline = HVACLLMPipeline(use_rag=True, llm_provider="mistral")
        
        # Run a simple test - use auto zone detection
        result = pipeline.run(
            base_idf="data/base_idfs/4ZoneWithShading_Simple_2_NoHVAC.idf",
            user_request="Design a simple VRF system for heating and cooling",
            zones=None,  # Auto-detect zones
            output_name="test_scenario2_mistral_rag"
        )
        
        print(f"\n📊 Scenario 2 Results:")
        print(f"   Status: {result.get('final_status', 'UNKNOWN')}")
        print(f"   HVAC Objects: {result.get('hvac_objects_count', 0)}")
        print(f"   Iterations: {result.get('iterations', 0)}")
        
        return result.get('final_status') == 'SUCCESS'
        
    except Exception as e:
        print(f"\n❌ Scenario 2 Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n" + "#"*70)
    print("# SCENARIO COMPARISON TEST")
    print("# Testing Scenario 1 (Gemini) vs Scenario 2 (Mistral+RAG)")
    print("#"*70)
    
    # Test Scenario 2 first (Mistral should work without quota issues)
    s2_success = test_scenario_2()
    
    # Test Scenario 1 (may hit Gemini quota limits)
    s1_success = test_scenario_1()
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Scenario 1 (Gemini, No RAG):     {'✅ SUCCESS' if s1_success else '❌ FAILED'}")
    print(f"Scenario 2 (Mistral + RAG):      {'✅ SUCCESS' if s2_success else '❌ FAILED'}")
    print("="*70)

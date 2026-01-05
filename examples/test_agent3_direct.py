#!/usr/bin/env python3
"""
Direct Test of Agent 3 Error Correction with Fine-tuned Mistral Model

This test directly calls Agent 3 with synthetic errors without running the full pipeline.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agents.agent3_corrector import ErrorCorrector
from config.settings import Config


def main():
    print("\n" + "="*70)
    print("DIRECT AGENT 3 ERROR CORRECTION TEST")
    print(f"Model: {'Fine-tuned Mistral (agent3-balanced)' if Config.LLM_PROVIDER == 'mistral' else 'Gemini pre-trained'}")
    print("="*70 + "\n")
    
    # Initialize Agent 3
    print("[1] Initializing Agent 3...")
    corrector = ErrorCorrector(use_rag=True)
    
    # Create synthetic test errors that Agent 3 should be able to fix
    test_errors = [
        "** Severe  ** GetInputProcessor: Error validating HVACTemplate:System:VRF, field Zone Name for Master Thermostat Location must be entered when Master Thermostat Priority Control Type = MASTERTHERMOSTATPRIORITY",
        "** Severe  ** HVACTemplate:System:VRF 'VRF_System_1': Invalid value 'InvalidCondenser' for field 'Condenser Type'. Valid values: AirCooled, EvaporativelyCooled, WaterCooled.",
        "** Severe  ** GetVRFInput: AirConditioner:VariableRefrigerantFlow 'VRF_System_1': Value type 'string' for input 'DrawThrough' not permitted by 'type' constraint.",
    ]
    
    # Create a fake IDF path (we'll use an existing valid one just for context)
    test_idf = "outputs/generated_idfs/test_agent3_base_FINAL.idf"
    
    if not os.path.exists(test_idf):
        # Use any existing IDF
        test_idf = "data/base_idfs/building_with_zones_fixed.idf"
    
    print(f"\n[2] Running Agent 3 with synthetic errors...")
    print("    Test errors:")
    for i, err in enumerate(test_errors, 1):
        print(f"    {i}. {err[:100]}...")
    
    print("\n" + "-"*60)
    print("Agent 3 analyzing errors and generating fixes...")
    print("-"*60 + "\n")
    
    # Call Agent 3
    fixes = corrector.analyze_and_fix(test_idf, test_errors)
    
    print(f"\n[3] Results: Agent 3 generated {len(fixes)} fixes")
    
    if fixes:
        print("\n    Fixes generated:")
        for i, fix in enumerate(fixes, 1):
            print(f"    {i}. {fix['object_type']}[{fix.get('object_name', 'N/A')}]")
            print(f"       Field: {fix['field_to_change']}")
            print(f"       Value: {fix['new_value']}")
        
        print("\n✅ SUCCESS! Agent 3 generated valid fixes")
    else:
        print("\n❌ Agent 3 did not generate any fixes")
        print("   This may indicate the model needs different training or prompting")
    
    print("\n" + "="*70)
    print("TEST COMPLETE")
    print("="*70)


if __name__ == "__main__":
    main()

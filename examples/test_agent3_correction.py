#!/usr/bin/env python3
"""
Test Agent 3 Error Correction with Fine-tuned Mistral Model

This script directly tests Agent 3's error correction capability by:
1. Loading a valid base IDF
2. Running Agent 1 to generate HVAC
3. Injecting intentional errors into the generated IDF
4. Running Agent 3 to correct the errors
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.pipeline import HVACLLMPipeline
from src.agents.agent3_corrector import ErrorCorrector
from src.core.idf_handler import IDFHandler
from src.core.validator import IDFValidator
from config.settings import Config
import re


def inject_hvac_errors(idf_content: str) -> str:
    """
    Inject intentional errors into the HVAC section of an IDF file.
    These errors should trigger Agent 3 error correction.
    """
    print("\n" + "="*60)
    print("INJECTING INTENTIONAL ERRORS INTO GENERATED HVAC")
    print("="*60)
    
    errors_injected = []
    
    # Error 1: Change Master Thermostat Priority to require zone name
    # but leave zone name empty
    if "LoadPriority" in idf_content:
        idf_content = idf_content.replace(
            "LoadPriority,",
            "MasterThermostatPriority,",
            1  # Only replace first occurrence
        )
        errors_injected.append("Changed LoadPriority → MasterThermostatPriority (requires zone name)")
    
    # Error 2: Find Zone Name for Master Thermostat Location and clear it
    # This makes MasterThermostatPriority invalid
    pattern = r'(Zone_Name_for_Master_Thermostat_Location[^,]*,)\s*([^,]+),'
    if re.search(pattern, idf_content):
        idf_content = re.sub(pattern, r'\1 ,', idf_content, count=1)
        errors_injected.append("Cleared Zone Name for Master Thermostat Location")
    
    # Error 3: Change Condenser Type to invalid value
    if "AirCooled" in idf_content:
        idf_content = idf_content.replace(
            "AirCooled,                   !- Condenser Type",
            "InvalidCondenser,           !- Condenser Type",
            1
        )
        errors_injected.append("Changed AirCooled → InvalidCondenser (invalid enum)")
    
    print("Errors injected:")
    for i, err in enumerate(errors_injected, 1):
        print(f"  {i}. {err}")
    print("="*60 + "\n")
    
    return idf_content


def main():
    print("\n" + "="*70)
    print("AGENT 3 ERROR CORRECTION TEST")
    print(f"Using: {'Fine-tuned Mistral' if Config.LLM_PROVIDER == 'mistral' else 'Gemini'}")
    print("="*70 + "\n")
    
    # Change to project root directory
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)
    print(f"Working directory: {os.getcwd()}")
    
    # Step 1: Initialize components
    print("[1] Initializing components...")
    handler = IDFHandler()
    validator = IDFValidator()
    
    # Step 2: Use pipeline to generate valid HVAC first
    print("\n[2] Generating valid HVAC system using Agent 1...")
    pipeline = HVACLLMPipeline()
    
    base_idf = "data/base_idfs/building_with_zones_fixed.idf"
    
    result = pipeline.run(
        base_idf=base_idf,
        user_request="Design a VRF HVAC system for efficient heating and cooling",
        zones=["Zone1", "Zone2"],
        output_name="test_agent3_base"
    )
    
    if result.get('final_status') != 'SUCCESS' and result.get('status') != 'SUCCESS' and not result.get('success', False):
        print("❌ Failed to generate base HVAC system")
        print(f"Result: {result}")
        return
    
    print("✓ Generated valid HVAC system")
    
    # Step 3: Read the generated IDF and inject errors
    print("\n[3] Injecting errors into generated IDF...")
    generated_idf_path = result.get('final_idf') or result.get('output_path') or result.get('idf_path')
    
    if not generated_idf_path or not os.path.exists(generated_idf_path):
        # Try to find the generated file
        generated_idf_path = "outputs/generated_idfs/test_agent3_base_FINAL.idf"
        if not os.path.exists(generated_idf_path):
            generated_idf_path = "outputs/generated_idfs/test_agent3_base_hvac.idf"
    
    with open(generated_idf_path, 'r') as f:
        original_content = f.read()
    
    # Inject errors
    broken_content = inject_hvac_errors(original_content)
    
    # Save broken IDF
    broken_idf_path = "outputs/generated_idfs/test_agent3_broken.idf"
    with open(broken_idf_path, 'w') as f:
        f.write(broken_content)
    print(f"✓ Saved broken IDF to: {broken_idf_path}")
    
    # Step 4: Validate the broken IDF to get errors
    print("\n[4] Validating broken IDF to get errors...")
    is_valid = validator.validate(broken_idf_path)
    errors = validator.errors if hasattr(validator, 'errors') else []
    
    print(f"\nValidation result: {'VALID' if is_valid else 'INVALID'}")
    print(f"Errors found: {len(errors)}")
    
    if errors:
        print("\nErrors detected:")
        for i, err in enumerate(errors[:10], 1):
            print(f"  {i}. {err[:100]}...")
    
    if not errors:
        print("⚠ No validation errors found. The injected errors may not trigger validation failures.")
        print("  Attempting simulation to find runtime errors...")
        
        # Try simulation
        from src.core.simulator import EnergyPlusSimulator
        sim = EnergyPlusSimulator()
        sim_result = sim.run(broken_idf_path, "outputs/simulations/test_agent3")
        
        if not sim_result.get('success'):
            # Collect errors from simulation
            sim_errors = sim_result.get('severe_errors', []) + sim_result.get('fatal_errors', [])
            if sim_result.get('error'):
                sim_errors.insert(0, sim_result.get('error'))
            errors = sim_errors
            
            print(f"\nSimulation errors found: {len(errors)}")
            for i, err in enumerate(errors[:10], 1):
                print(f"  {i}. {err[:150]}...")
    
    if not errors:
        print("\n⚠ No errors to correct. Agent 3 test skipped.")
        return
    
    # Step 5: Run Agent 3 error correction
    print("\n[5] Running Agent 3 Error Correction...")
    print(f"    Using: {'Fine-tuned Mistral (agent3-balanced)' if Config.LLM_PROVIDER == 'mistral' else 'Gemini pre-trained'}")
    
    corrector = ErrorCorrector(use_rag=True)
    
    print("\n" + "-"*60)
    print("Agent 3 analyzing errors and generating fixes...")
    print("-"*60)
    
    fixes = corrector.analyze_and_fix(broken_idf_path, errors)
    
    print(f"\n✓ Agent 3 generated {len(fixes)} fixes:")
    for i, fix in enumerate(fixes, 1):
        print(f"  {i}. {fix['object_type']}[{fix.get('object_name', 'N/A')}].{fix['field_to_change']} = '{fix['new_value']}'")
    
    if fixes:
        # Step 6: Apply fixes
        print("\n[6] Applying fixes...")
        corrected_idf_path = "outputs/generated_idfs/test_agent3_corrected.idf"
        applied = corrector.apply_fixes(broken_idf_path, fixes, corrected_idf_path)
        print(f"✓ Applied {applied} fixes")
        
        # Step 7: Re-validate
        print("\n[7] Re-validating corrected IDF...")
        is_valid_after = validator.validate(corrected_idf_path)
        errors_after = validator.errors if hasattr(validator, 'errors') else []
        
        print(f"\nAfter correction:")
        print(f"  Valid: {is_valid_after}")
        print(f"  Errors: {len(errors_after)}")
        
        if is_valid_after:
            print("\n✅ SUCCESS! Agent 3 successfully corrected the errors!")
        else:
            print(f"\n⚠ Still has {len(errors_after)} errors:")
            for i, err in enumerate(errors_after[:5], 1):
                print(f"  {i}. {err[:100]}...")
    else:
        print("\n❌ Agent 3 did not generate any fixes")
    
    print("\n" + "="*70)
    print("AGENT 3 TEST COMPLETE")
    print("="*70)


if __name__ == "__main__":
    main()

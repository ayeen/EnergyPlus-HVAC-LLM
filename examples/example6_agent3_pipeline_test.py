#!/usr/bin/env python3
"""
Example 6: Test Agent 3 Error Correction in Complete Pipeline Flow

This example intentionally creates a scenario where Agent 3 must be called:
1. Run Agent 1 to generate HVAC
2. Inject errors into the generated HVAC
3. Run validation/simulation (which will fail)
4. Agent 3 will be called to fix the errors

This tests the complete research pipeline flow with Agent 3 fine-tuned Mistral model.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Change to project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(project_root)

from src.pipeline import HVACLLMPipeline
from src.core.idf_handler import IDFHandler
from src.core.simulator import EnergyPlusSimulator
from src.core.validator import IDFValidator
from src.agents.agent3_corrector import ErrorCorrector
from config.settings import Config
import re
import shutil


def inject_errors_into_idf(idf_path: str, output_path: str) -> list:
    """
    Inject intentional errors into an IDF file to trigger Agent 3.
    Returns list of injected errors.
    """
    with open(idf_path, 'r') as f:
        content = f.read()
    
    errors_injected = []
    
    # Error 1: Change LoadPriority to MasterThermostatPriority 
    # but the zone_name_for_master_thermostat_location might be empty
    if "LoadPriority" in content:
        content = content.replace(
            "LoadPriority,",
            "MasterThermostatPriority,",
            1
        )
        errors_injected.append("Changed LoadPriority → MasterThermostatPriority")
    
    # Error 2: Change a valid condenser type to invalid
    if "AirCooled," in content:
        # Only change in the System:VRF section
        pattern = r'(AirCooled,\s*!-\s*Condenser Type)'
        if re.search(pattern, content):
            content = re.sub(pattern, r'WrongCondenser, !- Condenser Type', content, count=1)
            errors_injected.append("Changed AirCooled → WrongCondenser (invalid enum)")
    
    # Error 3: Set an invalid heating COP value (string instead of number)
    pattern = r'(\d+\.?\d*,\s*!-\s*Gross Rated Heating COP)'
    if re.search(pattern, content):
        content = re.sub(pattern, r'InvalidCOP, !- Gross Rated Heating COP', content, count=1)
        errors_injected.append("Changed numeric Heating COP → InvalidCOP (string in numeric field)")
    
    with open(output_path, 'w') as f:
        f.write(content)
    
    return errors_injected


def run_agent3_pipeline_test():
    """
    Run a complete pipeline test that exercises Agent 3.
    """
    print("\n" + "="*80)
    print("AGENT 3 COMPLETE PIPELINE TEST")
    print("="*80)
    print(f"LLM Provider: {Config.LLM_PROVIDER}")
    print(f"Using RAG: {Config.USE_RAG}")
    print("="*80 + "\n")
    
    # Step 1: Generate valid HVAC using the standard pipeline
    print("[Phase 1] Generating valid HVAC with Agent 1...")
    print("-"*60)
    
    pipeline = HVACLLMPipeline(use_rag=True)
    
    base_idf = "data/base_idfs/building_with_zones_fixed.idf"
    
    # Run pipeline to generate HVAC (should succeed)
    result = pipeline.run(
        base_idf=base_idf,
        user_request="Design a VRF HVAC system for efficient heating and cooling",
        zones=["Zone1", "Zone2"],
        output_name="agent3_test_phase1"
    )
    
    if result.get('final_status') != 'SUCCESS':
        print("❌ Phase 1 failed - Agent 1 couldn't generate valid HVAC")
        return
    
    print("\n✅ Phase 1 Complete - Valid HVAC generated")
    generated_idf = result.get('final_idf')
    print(f"   Generated IDF: {generated_idf}")
    
    # Step 2: Inject errors into the generated IDF
    print("\n" + "-"*60)
    print("[Phase 2] Injecting intentional errors...")
    print("-"*60)
    
    broken_idf = "outputs/generated_idfs/agent3_test_broken.idf"
    errors_injected = inject_errors_into_idf(generated_idf, broken_idf)
    
    print(f"Errors injected:")
    for i, err in enumerate(errors_injected, 1):
        print(f"  {i}. {err}")
    
    if not errors_injected:
        print("⚠ No errors could be injected. Trying alternative approach...")
        # Alternative: manually create an error by modifying the file
        with open(generated_idf, 'r') as f:
            content = f.read()
        
        # Force an error by changing zone name reference
        content = content.replace("Zone1,", "NonExistentZone999,", 1)
        with open(broken_idf, 'w') as f:
            f.write(content)
        errors_injected.append("Changed Zone1 → NonExistentZone999 (invalid reference)")
    
    print(f"\n✅ Phase 2 Complete - Broken IDF saved to: {broken_idf}")
    
    # Step 3: Run simulation on broken IDF to trigger errors
    print("\n" + "-"*60)
    print("[Phase 3] Running simulation on broken IDF...")
    print("-"*60)
    
    simulator = EnergyPlusSimulator()
    sim_dir = "outputs/simulations/agent3_test_broken"
    sim_result = simulator.run(broken_idf, sim_dir)
    
    print(f"Simulation success: {sim_result['success']}")
    error_count = sim_result.get('error_count', len(sim_result.get('severe_errors', [])) + len(sim_result.get('fatal_errors', [])))
    print(f"Error count: {error_count}")
    
    # Gather all errors from simulation result
    severe = sim_result.get('severe_errors', [])
    fatal = sim_result.get('fatal_errors', [])
    warnings = sim_result.get('warnings', [])
    errors = sim_result.get('errors', [])  # Some simulators use this key
    
    print(f"  Severe errors: {len(severe)}")
    print(f"  Fatal errors: {len(fatal)}")
    print(f"  Warnings: {len(warnings)}")
    print(f"  General errors: {len(errors)}")
    
    if sim_result['success']:
        print("⚠ Simulation unexpectedly succeeded. Errors may not be severe enough.")
        print("   Checking for warnings that Agent 3 could address...")
        
        # Even if simulation "succeeds", there may be warnings to fix
        all_errors = severe + warnings[:5]
    else:
        all_errors = severe + fatal + errors
    
    print(f"\nErrors/warnings to fix: {len(all_errors)}")
    for i, err in enumerate(all_errors[:5], 1):
        print(f"  {i}. {err[:100]}...")
    
    # Step 4: Run Agent 3 Error Correction
    print("\n" + "-"*60)
    print("[Phase 4] Running Agent 3 Error Correction...")
    print("-"*60)
    print(f"Model: {'Fine-tuned Mistral (agent3-balanced)' if Config.LLM_PROVIDER == 'mistral' else 'Gemini pre-trained'}")
    
    corrector = ErrorCorrector(use_rag=True)
    
    print("\n🔧 Agent 3 analyzing errors and generating fixes...")
    fixes = corrector.analyze_and_fix(broken_idf, all_errors)
    
    print(f"\n✅ Agent 3 generated {len(fixes)} fixes:")
    for i, fix in enumerate(fixes, 1):
        print(f"  {i}. {fix['object_type']}[{fix.get('object_name', 'N/A')}]")
        print(f"     Field: {fix['field_to_change']} = '{fix['new_value']}'")
    
    if not fixes:
        print("\n⚠ Agent 3 generated no fixes.")
        print("   This may indicate the errors are not patterns it was trained on.")
        return
    
    # Step 5: Apply fixes
    print("\n" + "-"*60)
    print("[Phase 5] Applying Agent 3 fixes...")
    print("-"*60)
    
    fixed_idf = "outputs/generated_idfs/agent3_test_fixed.idf"
    applied = corrector.apply_fixes(broken_idf, fixes, fixed_idf)
    print(f"✅ Applied {applied} fixes to: {fixed_idf}")
    
    # Step 6: Re-run simulation on fixed IDF
    print("\n" + "-"*60)
    print("[Phase 6] Re-running simulation on fixed IDF...")
    print("-"*60)
    
    sim_dir_fixed = "outputs/simulations/agent3_test_fixed"
    sim_result_fixed = simulator.run(fixed_idf, sim_dir_fixed)
    
    print(f"Simulation success: {sim_result_fixed['success']}")
    error_count_fixed = sim_result_fixed.get('error_count', len(sim_result_fixed.get('severe_errors', [])) + len(sim_result_fixed.get('fatal_errors', [])))
    print(f"Error count: {error_count_fixed}")
    
    # Final Summary
    print("\n" + "="*80)
    print("AGENT 3 PIPELINE TEST SUMMARY")
    print("="*80)
    print(f"Phase 1 (Agent 1 Generation): SUCCESS")
    print(f"Phase 2 (Error Injection): {len(errors_injected)} errors injected")
    print(f"Phase 3 (Broken Simulation): {'FAILED' if not sim_result['success'] else 'WARNINGS'} ({error_count} issues)")
    print(f"Phase 4 (Agent 3 Analysis): {len(fixes)} fixes generated")
    print(f"Phase 5 (Fix Application): {applied} fixes applied")
    print(f"Phase 6 (Fixed Simulation): {'SUCCESS' if sim_result_fixed['success'] else 'FAILED'}")
    print("-"*80)
    
    if sim_result_fixed['success']:
        # Copy to final location
        final_idf = "outputs/generated_idfs/agent3_test_FINAL.idf"
        shutil.copy(fixed_idf, final_idf)
        print(f"\n🎉 SUCCESS! Agent 3 successfully corrected the errors!")
        print(f"   Final IDF: {final_idf}")
    else:
        print(f"\n⚠ Simulation still has {error_count_fixed} errors after Agent 3 fix")
        remaining_errors = sim_result_fixed.get('severe_errors', []) + sim_result_fixed.get('fatal_errors', [])
        if remaining_errors:
            print("   Remaining errors:")
            for err in remaining_errors[:3]:
                print(f"   - {err[:80]}...")
    
    print("="*80)


if __name__ == "__main__":
    run_agent3_pipeline_test()

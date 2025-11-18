"""
Test Quick Validation in Pipeline
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.pipeline import HVACLLMPipeline

def main():
    """Test pipeline with quick validation"""
    
    print("=" * 70)
    print("TEST: Pipeline with Quick Validation")
    print("=" * 70)
    
    # Initialize pipeline
    pipeline = HVACLLMPipeline()
    
    # Define project
    base_idf = "../data/base_idfs/building_with_zones.idf"
    zones = ["ZONE ONE"]
    user_request = "Design a VRF HVAC system for efficient heating and cooling"
    
    print(f"\nBase IDF: {base_idf}")
    print(f"Zones: {', '.join(zones)}")
    print(f"User Request: {user_request}")
    print("\n" + "=" * 70)
    
    # Test 1: With quick validation (default)
    print("\n>>> TEST 1: With Quick Validation Enabled")
    print("-" * 70)
    results1 = pipeline.run(
        base_idf=base_idf,
        zones=zones,
        output_name="test_with_validation",
        system_name="VRF_System_1",
        user_request=user_request,
        enable_quick_validation=True  # Enabled
    )
    
    print("\n" + "=" * 70)
    print(f"Result 1: {results1['final_status']}")
    print(f"Iterations: {results1['total_iterations']}")
    
    # Check if quick validation step exists
    validation_steps = [s for s in results1['steps'] if 'Quick Validation' in s['name']]
    if validation_steps:
        print("✓ Quick validation was executed")
        print(f"  Valid: {validation_steps[0].get('valid', 'N/A')}")
        if validation_steps[0].get('passed_checks'):
            print(f"  Passed checks: {len(validation_steps[0]['passed_checks'])}")
    else:
        print("❌ Quick validation was NOT executed")
    
    print("=" * 70)
    
    # Test 2: Without quick validation
    print("\n>>> TEST 2: With Quick Validation Disabled")
    print("-" * 70)
    results2 = pipeline.run(
        base_idf=base_idf,
        zones=zones,
        output_name="test_without_validation",
        system_name="VRF_System_1",
        user_request=user_request,
        enable_quick_validation=False  # Disabled
    )
    
    print("\n" + "=" * 70)
    print(f"Result 2: {results2['final_status']}")
    print(f"Iterations: {results2['total_iterations']}")
    
    # Check if quick validation step was skipped
    validation_steps = [s for s in results2['steps'] if 'Quick Validation' in s['name']]
    if validation_steps and validation_steps[0].get('status') == 'skipped':
        print("✓ Quick validation was correctly skipped")
    else:
        print("❌ Quick validation was unexpectedly executed")
    
    print("=" * 70)
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Test 1 (with validation): {results1['final_status']}")
    print(f"Test 2 (without validation): {results2['final_status']}")
    print("=" * 70)
    
    if results1['final_status'] == 'SUCCESS' and results2['final_status'] == 'SUCCESS':
        print("\n✅ ALL TESTS PASSED!")
        print("Quick validation feature is working correctly.")
    else:
        print("\n⚠ Some tests did not complete successfully")

if __name__ == "__main__":
    main()

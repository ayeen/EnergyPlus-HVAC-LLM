"""
Test to verify if the system generates prompt-specific outputs or generic IDFs.

This test runs the same base IDF with different prompts and compares outputs.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.pipeline import HVACLLMPipeline
import difflib
from pathlib import Path

def extract_key_parameters(idf_content):
    """Extract key parameters from IDF for comparison."""
    params = {
        'cooling_cop': None,
        'heating_cop': None,
        'cooling_capacity': None,
        'heating_capacity': None,
        'min_cooling_temp': None,
        'max_cooling_temp': None,
        'min_heating_temp': None,
        'max_heating_temp': None,
        'heating_setpoint': None,
        'cooling_setpoint': None,
        'supplemental_heating': None,
        'heat_recovery': False,
    }

    lines = idf_content.split('\n')
    in_system_vrf = False
    in_thermostat = False
    field_count = 0

    for line in lines:
        stripped = line.strip()

        # Check for heat recovery mention
        if 'heat recovery' in stripped.lower() or 'HeatRecovery' in stripped:
            params['heat_recovery'] = True

        # Track object types
        if 'HVACTemplate:System:VRF' in stripped:
            in_system_vrf = True
            field_count = 0
            continue
        elif 'HVACTemplate:Thermostat' in stripped:
            in_thermostat = True
            field_count = 0
            continue
        elif stripped.endswith(';'):
            in_system_vrf = False
            in_thermostat = False
            field_count = 0

        if in_system_vrf:
            field_count += 1
            value = stripped.rstrip(',;')

            # Extract System:VRF parameters
            if field_count == 4 and value and value != 'Autosize':  # Cooling COP
                try:
                    params['cooling_cop'] = float(value)
                except: pass
            elif field_count == 9 and value and value != 'Autosize':  # Heating COP
                try:
                    params['heating_cop'] = float(value)
                except: pass
            elif field_count == 5:  # Min cooling temp
                try:
                    params['min_cooling_temp'] = float(value)
                except: pass
            elif field_count == 6:  # Max cooling temp
                try:
                    params['max_cooling_temp'] = float(value)
                except: pass
            elif field_count == 10:  # Min heating temp
                try:
                    params['min_heating_temp'] = float(value)
                except: pass
            elif field_count == 11:  # Max heating temp
                try:
                    params['max_heating_temp'] = float(value)
                except: pass

        if in_thermostat:
            field_count += 1
            value = stripped.rstrip(',;')

            if field_count == 3 and value:  # Heating setpoint
                try:
                    params['heating_setpoint'] = float(value)
                except: pass
            elif field_count == 5 and value:  # Cooling setpoint
                try:
                    params['cooling_setpoint'] = float(value)
                except: pass

        # Check for supplemental heating
        if 'supplemental' in stripped.lower() and ('Electric' in stripped or 'Gas' in stripped):
            params['supplemental_heating'] = 'Yes'

    return params

def run_test():
    """Run test with different prompts."""

    print("=" * 80)
    print("PROMPT SPECIFICITY TEST")
    print("=" * 80)
    print("\nTesting if the system generates different outputs for different prompts...")
    print()

    # Test cases with very different requirements
    test_cases = [
        {
            'name': 'generic',
            'prompt': 'Design a VRF HVAC system for efficient heating and cooling',
            'expected': 'Generic system with standard settings'
        },
        {
            'name': 'cold_climate',
            'prompt': 'Design a VRF system optimized for cold climate operation with enhanced heating performance and supplemental electric heating',
            'expected': 'Enhanced heating COP, wider heating temp range, supplemental heating'
        },
        {
            'name': 'high_efficiency',
            'prompt': 'Design a high-efficiency VRF system with advanced control strategies for maximum energy savings and very high COP values',
            'expected': 'Higher COP values (>4.0), advanced controls'
        },
        {
            'name': 'heat_recovery',
            'prompt': 'Design a VRF system with heat recovery for simultaneous heating and cooling in different zones',
            'expected': 'Heat recovery configuration, special controls'
        }
    ]

    results = {}
    base_idf = 'data/base_idfs/building_with_zones_fixed.idf'

    for test in test_cases:
        print(f"\n{'=' * 80}")
        print(f"Test Case: {test['name']}")
        print(f"{'=' * 80}")
        print(f"Prompt: {test['prompt']}")
        print(f"Expected: {test['expected']}")
        print()

        pipeline = HVACLLMPipeline()

        try:
            result = pipeline.run(
                base_idf=base_idf,
                zones=['Zone1'],
                output_name=f"test_{test['name']}",
                user_request=test['prompt'],
                enable_quick_validation=False
            )

            # Read generated IDF
            if result['final_idf'] and os.path.exists(result['final_idf']):
                with open(result['final_idf'], 'r') as f:
                    idf_content = f.read()

                # Extract parameters
                params = extract_key_parameters(idf_content)
                results[test['name']] = {
                    'params': params,
                    'content': idf_content,
                    'file': result['final_idf']
                }

                print(f"✓ Generation successful")
                print(f"  File: {result['final_idf']}")
                print(f"\n  Extracted Parameters:")
                for key, value in params.items():
                    print(f"    {key}: {value}")
            else:
                print(f"✗ Generation failed - no output file")
                results[test['name']] = None

        except Exception as e:
            print(f"✗ Error: {e}")
            results[test['name']] = None

    # Compare results
    print(f"\n\n{'=' * 80}")
    print("COMPARISON ANALYSIS")
    print("=" * 80)

    # Check if all tests generated outputs
    valid_results = {k: v for k, v in results.items() if v is not None}

    if len(valid_results) < 2:
        print("\n✗ Not enough successful generations to compare")
        return

    # Compare parameters
    print("\nParameter Comparison:")
    print("-" * 80)

    param_keys = ['cooling_cop', 'heating_cop', 'min_heating_temp', 'max_heating_temp',
                  'heating_setpoint', 'cooling_setpoint', 'supplemental_heating', 'heat_recovery']

    # Create comparison table
    print(f"{'Parameter':<30}", end='')
    for name in valid_results.keys():
        print(f"{name:<20}", end='')
    print()
    print("-" * 80)

    differences_found = False
    for param in param_keys:
        print(f"{param:<30}", end='')
        values = []
        for name in valid_results.keys():
            value = valid_results[name]['params'].get(param)
            values.append(value)
            print(f"{str(value):<20}", end='')
        print()

        # Check if all values are the same
        if len(set(str(v) for v in values)) > 1:
            differences_found = True
            print(f"  {'^^^ DIFFERENT VALUES ^^^':<30}")

    # Text similarity comparison
    print(f"\n\nContent Similarity Analysis:")
    print("-" * 80)

    names = list(valid_results.keys())
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            name1, name2 = names[i], names[j]
            content1 = valid_results[name1]['content']
            content2 = valid_results[name2]['content']

            # Calculate similarity
            similarity = difflib.SequenceMatcher(None, content1, content2).ratio()

            print(f"{name1} vs {name2}: {similarity:.1%} similar")

            if similarity > 0.95:
                print(f"  ⚠️  WARNING: Files are >95% identical!")

    # Final verdict
    print(f"\n\n{'=' * 80}")
    print("VERDICT")
    print("=" * 80)

    if differences_found:
        print("✓ PROMPT-SPECIFIC: System generates different parameters based on prompts")
        print("  Different values were found in key parameters across test cases.")
    else:
        print("✗ GENERIC OUTPUT: System appears to generate similar IDFs regardless of prompt")
        print("  All key parameters are identical across different prompts.")
        print("\n  POSSIBLE ISSUES:")
        print("  1. Technical template is too restrictive")
        print("  2. LLM is not interpreting user prompts correctly")
        print("  3. Template overrides user-specific requirements")

    print("\n" + "=" * 80)

if __name__ == "__main__":
    run_test()

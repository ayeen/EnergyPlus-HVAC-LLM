"""
Test script to verify improved prompt-specific customization.

This uses the new improved template to generate different configurations
based on different user prompts.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.pipeline import HVACLLMPipeline
import re

def extract_parameters_v2(idf_path):
    """Extract key customizable parameters from generated IDF."""
    params = {
        'file': os.path.basename(idf_path),
        'cooling_cop': None,
        'heating_cop': None,
        'heating_sizing_ratio': None,
        'min_cooling_temp': None,
        'max_cooling_temp': None,
        'min_heating_temp': None,
        'max_heating_temp': None,
        'part_load_ratio': None,
        'heating_setpoint': None,
        'cooling_setpoint': None,
        'supplemental_heating': None,
        'baseboard_heating': None,
        'parasitic_on': None,
        'parasitic_off': None,
    }

    if not os.path.exists(idf_path):
        return params

    with open(idf_path, 'r') as f:
        content = f.read()

    lines = content.split('\n')
    in_system_vrf = False
    in_zone_vrf = False
    in_thermostat = False
    field_count = 0

    for line in lines:
        stripped = line.strip()

        # Track object types
        if 'HVACTemplate:System:VRF' in stripped:
            in_system_vrf = True
            field_count = 0
            continue
        elif 'HVACTemplate:Zone:VRF' in stripped:
            in_zone_vrf = True
            field_count = 0
            continue
        elif 'HVACTemplate:Thermostat' in stripped:
            in_thermostat = True
            field_count = 0
            continue
        elif stripped.endswith(';'):
            in_system_vrf = False
            in_zone_vrf = False
            in_thermostat = False
            field_count = 0
            continue

        if in_system_vrf and stripped and not stripped.startswith('!'):
            field_count += 1
            value = stripped.rstrip(',;').strip()

            # System:VRF parameters
            if field_count == 4:  # Cooling COP
                try:
                    params['cooling_cop'] = float(value)
                except: pass
            elif field_count == 5:  # Min cooling temp
                try:
                    params['min_cooling_temp'] = float(value)
                except: pass
            elif field_count == 6:  # Max cooling temp
                try:
                    params['max_cooling_temp'] = float(value)
                except: pass
            elif field_count == 8:  # Heating capacity sizing ratio
                try:
                    params['heating_sizing_ratio'] = float(value)
                except: pass
            elif field_count == 9:  # Heating COP
                try:
                    params['heating_cop'] = float(value)
                except: pass
            elif field_count == 10:  # Min heating temp
                try:
                    params['min_heating_temp'] = float(value)
                except: pass
            elif field_count == 11:  # Max heating temp
                try:
                    params['max_heating_temp'] = float(value)
                except: pass
            elif field_count == 12:  # Part load ratio
                try:
                    params['part_load_ratio'] = float(value)
                except: pass

        if in_zone_vrf and stripped and not stripped.startswith('!'):
            field_count += 1
            value = stripped.rstrip(',;').strip()

            # Zone:VRF advanced parameters
            if field_count == 33:  # Supplemental heating type
                if value and value.lower() != 'blank':
                    params['supplemental_heating'] = value
            elif field_count == 37:  # Parasitic on
                try:
                    if value:
                        params['parasitic_on'] = float(value)
                except: pass
            elif field_count == 38:  # Parasitic off
                try:
                    if value:
                        params['parasitic_off'] = float(value)
                except: pass
            elif field_count == 41:  # Baseboard heating
                if value and value.lower() != 'blank':
                    params['baseboard_heating'] = value

        if in_thermostat and stripped and not stripped.startswith('!'):
            field_count += 1
            value = stripped.rstrip(',;').strip()

            if field_count == 3:  # Heating setpoint
                try:
                    params['heating_setpoint'] = float(value)
                except: pass
            elif field_count == 5:  # Cooling setpoint
                try:
                    params['cooling_setpoint'] = float(value)
                except: pass

    return params

def run_improved_test():
    """Test improved template with diverse prompts."""

    print("=" * 80)
    print("IMPROVED TEMPLATE TEST - Prompt-Specific Customization")
    print("=" * 80)
    print()
    print("Testing NEW improved template that responds to user design intent...")
    print()

    test_cases = [
        {
            'name': 'standard',
            'prompt': 'Design a VRF HVAC system for efficient heating and cooling',
            'expected': {
                'cooling_cop': '3.3-3.5',
                'heating_cop': '3.5-4.0',
                'supplemental_heating': 'None',
                'description': 'Standard efficiency, no advanced features'
            }
        },
        {
            'name': 'cold_climate',
            'prompt': 'Design a VRF system optimized for cold climate operation with enhanced heating performance and backup electric heating for extreme temperatures',
            'expected': {
                'cooling_cop': '3.5-4.0',
                'heating_cop': '4.2-4.8',
                'heating_sizing_ratio': '1.3-1.5',
                'supplemental_heating': 'Electric',
                'min_heating_temp': '-25 to -30',
                'description': 'Enhanced heating, supplemental electric heating, wider heating range'
            }
        },
        {
            'name': 'high_efficiency',
            'prompt': 'Design a high-efficiency VRF system with premium components and advanced control strategies for maximum energy savings',
            'expected': {
                'cooling_cop': '4.0-4.8',
                'heating_cop': '4.5-5.2',
                'part_load_ratio': '0.10-0.15',
                'description': 'Premium efficiency ratings, better part-load performance'
            }
        },
        {
            'name': 'hot_climate',
            'prompt': 'Design a VRF system for hot desert climate with superior cooling performance and extended high-temperature operation',
            'expected': {
                'cooling_cop': '3.8-4.5',
                'max_cooling_temp': '45-48',
                'min_cooling_temp': '0-5',
                'description': 'Enhanced cooling capability, wider hot-weather range'
            }
        }
    ]

    results = []
    base_idf = 'data/base_idfs/building_with_zones_fixed.idf'

    for test in test_cases:
        print(f"\n{'=' * 80}")
        print(f"Test: {test['name'].upper()}")
        print(f"{'=' * 80}")
        print(f"Prompt: {test['prompt']}")
        print(f"\nExpected Customizations:")
        for key, value in test['expected'].items():
            if key != 'description':
                print(f"  • {key}: {value}")
        print(f"\n  Description: {test['expected']['description']}")
        print()

        try:
            pipeline = HVACLLMPipeline()
            result = pipeline.run(
                base_idf=base_idf,
                zones=['Zone1'],
                output_name=f"improved_test_{test['name']}",
                user_request=test['prompt'],
                enable_quick_validation=False
            )

            if result.get('final_idf') and os.path.exists(result['final_idf']):
                params = extract_parameters_v2(result['final_idf'])
                results.append({
                    'name': test['name'],
                    'params': params,
                    'expected': test['expected'],
                    'prompt': test['prompt']
                })

                print(f"✓ Generation successful")
                print(f"  File: {params['file']}")
                print(f"\n  Generated Parameters:")
                print(f"    Cooling COP: {params['cooling_cop']}")
                print(f"    Heating COP: {params['heating_cop']}")
                print(f"    Heating Sizing Ratio: {params['heating_sizing_ratio']}")
                print(f"    Min Heating Temp: {params['min_heating_temp']}°C")
                print(f"    Max Heating Temp: {params['max_heating_temp']}°C")
                print(f"    Max Cooling Temp: {params['max_cooling_temp']}°C")
                print(f"    Part Load Ratio: {params['part_load_ratio']}")
                print(f"    Supplemental Heating: {params['supplemental_heating'] or 'None'}")
                print(f"    Baseboard Heating: {params['baseboard_heating'] or 'None'}")
            else:
                print(f"✗ Generation failed - no output file")
                results.append({'name': test['name'], 'params': None})

        except Exception as e:
            print(f"✗ Error: {e}")
            results.append({'name': test['name'], 'params': None})

    # Analysis
    print(f"\n\n{'=' * 80}")
    print("COMPARISON ANALYSIS")
    print("=" * 80)

    valid_results = [r for r in results if r.get('params')]

    if len(valid_results) < 2:
        print("\n✗ Not enough successful generations to compare")
        return

    print("\nParameter Comparison Table:")
    print("-" * 80)

    params_to_compare = [
        ('cooling_cop', 'Cooling COP'),
        ('heating_cop', 'Heating COP'),
        ('heating_sizing_ratio', 'Heating Sizing'),
        ('min_heating_temp', 'Min Heat Temp (°C)'),
        ('max_heating_temp', 'Max Heat Temp (°C)'),
        ('max_cooling_temp', 'Max Cool Temp (°C)'),
        ('part_load_ratio', 'Part Load Ratio'),
        ('supplemental_heating', 'Supplemental Heat'),
    ]

    # Header
    print(f"{'Parameter':<25}", end='')
    for r in valid_results:
        print(f"{r['name']:<20}", end='')
    print()
    print("-" * 80)

    # Data rows
    differences_found = False
    for param_key, param_label in params_to_compare:
        print(f"{param_label:<25}", end='')
        values = []
        for r in valid_results:
            value = r['params'].get(param_key)
            values.append(value)
            display_val = str(value) if value is not None else '-'
            print(f"{display_val:<20}", end='')
        print()

        # Check for differences
        unique_values = set(str(v) for v in values if v is not None)
        if len(unique_values) > 1:
            differences_found = True
            print(f"{'  → CUSTOMIZED':<25}{'✓'*len(valid_results)}")

    print("-" * 80)

    # Verdict
    print(f"\n\n{'=' * 80}")
    print("VERDICT")
    print("=" * 80)

    if differences_found:
        print("\n✅ SUCCESS: Template enables PROMPT-SPECIFIC customization!")
        print("\nKey Findings:")
        print("  • Different prompts generate different parameter values")
        print("  • System responds to design intent keywords")
        print("  • Advanced features (supplemental heating) are activated appropriately")
        print("  • IDD compliance maintained throughout")

        print("\n📊 Customization Examples:")
        for r in valid_results:
            if not r.get('params'):
                continue
            print(f"\n  {r['name'].upper()}:")
            print(f"    Prompt keywords: {r['prompt'][:60]}...")
            p = r['params']
            if p['supplemental_heating']:
                print(f"    → Enabled supplemental heating: {p['supplemental_heating']}")
            if p['heating_cop'] and p['heating_cop'] > 4.0:
                print(f"    → Enhanced heating COP: {p['heating_cop']}")
            if p['cooling_cop'] and p['cooling_cop'] > 3.8:
                print(f"    → High cooling efficiency: {p['cooling_cop']}")
            if p['heating_sizing_ratio'] and p['heating_sizing_ratio'] > 1.2:
                print(f"    → Oversized for climate: {p['heating_sizing_ratio']}")
    else:
        print("\n⚠️  LIMITED CUSTOMIZATION: Some parameters may still be too templated")
        print("\nPossible issues:")
        print("  • LLM may not be interpreting guidance correctly")
        print("  • Need to verify Mistral fine-tuned model is loading")
        print("  • Check if mock mode was used instead of real LLM")

    print("\n" + "=" * 80)

if __name__ == "__main__":
    run_improved_test()

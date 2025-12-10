"""
Test Multi-Zone Building Context Extraction
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.idf_handler import IDFHandler

def test_multi_zone():
    """Test with multi-zone IDF"""
    print("=" * 70)
    print("TEST: Multi-Zone Building Context Extraction")
    print("=" * 70)
    
    handler = IDFHandler()
    
    # Test with 4-zone IDF
    base_idf = "data/base_idfs/4ZoneWithShading_Simple_2.idf"
    
    if not os.path.exists(base_idf):
        print(f"\n⚠️  Base IDF not found: {base_idf}")
        return
    
    print(f"\nLoading IDF: {base_idf}")
    idf = handler.load(base_idf)
    
    # Extract zones
    zones = handler.get_zones(idf)
    print(f"\n✓ Found {len(zones)} zones:")
    for i, zone in enumerate(zones, 1):
        print(f"  {i}. {zone}")
    
    # Extract full building context
    context = handler.extract_building_context(idf)
    
    print(f"\n📊 Building Context Summary:")
    print(f"{'='*70}")
    print(f"  Number of Zones: {context['num_zones']}")
    print(f"  Zone Names:")
    for i, zone in enumerate(context['zone_names'], 1):
        print(f"    {i}. {zone}")
    
    if context['total_area'] > 0:
        print(f"\n  Total Floor Area: {context['total_area']:.1f} m²")
    else:
        print(f"\n  Total Floor Area: Not explicitly defined in IDF")
    
    if context['total_volume'] > 0:
        print(f"  Total Volume: {context['total_volume']:.1f} m³")
    else:
        print(f"  Total Volume: Not explicitly defined in IDF")
    
    print(f"\n  Building Orientation: {context['orientation']}°")
    
    print(f"\n  Internal Loads:")
    if context['has_internal_loads']:
        print(f"    ✓ Has internal loads")
        if context['has_people']:
            print(f"      • People: Yes")
        if context['has_lights']:
            print(f"      • Lights: Yes")
        if context['has_equipment']:
            print(f"      • Equipment: Yes")
    else:
        print(f"    ✗ No internal loads defined")
    
    print(f"\n  Construction: {context['construction_type']}")
    print(f"  Location: {context['weather_file']}")
    
    # Test validation
    print(f"\n{'='*70}")
    print("Validation Tests:")
    print(f"{'='*70}")
    
    issues = handler.validate_base_idf(idf)
    if issues:
        print(f"\n⚠️  Validation Issues ({len(issues)}):")
        for issue in issues:
            print(f"  {issue}")
    else:
        print("\n✓ Base IDF passed all validation checks")
    
    # Test zone validation
    print(f"\n--- Test selective zone validation ---")
    selected_zones = zones[:2]  # First 2 zones
    print(f"Testing with selected zones: {selected_zones}")
    
    try:
        handler.validate_zones(idf, selected_zones)
        print(f"✓ Validation passed for selected zones")
    except ValueError as e:
        print(f"❌ Validation failed: {e}")
    
    print(f"\n{'='*70}")
    print("✅ MULTI-ZONE TEST COMPLETED")
    print(f"{'='*70}")
    
    # Show what would be passed to Agent 1
    print(f"\n💡 Building Context for Agent 1 Generation:")
    print(f"{'='*70}")
    print(f"""
This context would be automatically passed to the LLM for better sizing:

BUILDING CONTEXT:
- Number of Zones: {context['num_zones']}
- Zone Names: {', '.join(context['zone_names'])}
- Total Floor Area: {context['total_area']:.1f} m² {'(estimated from geometry)' if context['total_area'] > 0 else '(not defined)'}
- Building Orientation: {context['orientation']}°
- Internal Loads: {'Yes (' + ', '.join([l for l, v in [('People', context['has_people']), ('Lights', context['has_lights']), ('Equipment', context['has_equipment'])] if v]) + ')' if context['has_internal_loads'] else 'No'}
- Location: {context['weather_file']}

SIZING GUIDANCE:
- Use building area for capacity estimation (typical: 100-150 W/m² cooling load)
- Consider {context['num_zones']} zones for outdoor unit sizing
- Account for orientation in heat gain/loss calculations
- {'Include' if context['has_internal_loads'] else 'Warning: No'} internal loads in sizing
""")

if __name__ == "__main__":
    try:
        test_multi_zone()
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()

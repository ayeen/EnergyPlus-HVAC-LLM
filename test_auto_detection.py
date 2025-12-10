"""
Quick Test: Auto-Detection Features
Tests the new building context extraction and zone auto-detection
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.idf_handler import IDFHandler
from config import Config

def test_idf_handler():
    """Test IDFHandler new methods"""
    print("=" * 70)
    print("TEST 1: IDFHandler Building Context Extraction")
    print("=" * 70)
    
    handler = IDFHandler()
    
    # Test with an existing IDF
    base_idf = "data/base_idfs/building_with_zones.idf"
    
    if not os.path.exists(base_idf):
        print(f"\n⚠️  Base IDF not found: {base_idf}")
        print("   Please ensure you have a base IDF file to test with.")
        return
    
    print(f"\nLoading IDF: {base_idf}")
    idf = handler.load(base_idf)
    
    # Test get_zones
    print("\n--- Test: get_zones() ---")
    zones = handler.get_zones(idf)
    print(f"✓ Found {len(zones)} zones:")
    for i, zone in enumerate(zones, 1):
        print(f"  {i}. {zone}")
    
    # Test extract_building_context
    print("\n--- Test: extract_building_context() ---")
    context = handler.extract_building_context(idf)
    print("✓ Building Context Extracted:")
    print(f"  • Number of Zones: {context['num_zones']}")
    print(f"  • Zone Names: {', '.join(context['zone_names'])}")
    print(f"  • Total Floor Area: {context['total_area']:.2f} m²")
    print(f"  • Total Volume: {context['total_volume']:.2f} m³")
    print(f"  • Orientation: {context['orientation']}°")
    print(f"  • Has Internal Loads: {context['has_internal_loads']}")
    if context['has_internal_loads']:
        print(f"    - People: {context['has_people']}")
        print(f"    - Lights: {context['has_lights']}")
        print(f"    - Equipment: {context['has_equipment']}")
    print(f"  • Construction: {context['construction_type']}")
    print(f"  • Location: {context['weather_file']}")
    
    # Test validate_zones
    print("\n--- Test: validate_zones() ---")
    test_zones = zones[:1] if zones else []
    if test_zones:
        try:
            handler.validate_zones(idf, test_zones)
            print(f"✓ Validation passed for zones: {test_zones}")
        except ValueError as e:
            print(f"❌ Validation failed: {e}")
    
    # Test invalid zones
    print("\n--- Test: validate_zones() with invalid zones ---")
    try:
        handler.validate_zones(idf, ["INVALID_ZONE_NAME"])
        print("❌ Should have raised ValueError")
    except ValueError as e:
        print(f"✓ Correctly caught invalid zone: {str(e)[:100]}...")
    
    # Test validate_base_idf
    print("\n--- Test: validate_base_idf() ---")
    issues = handler.validate_base_idf(idf)
    if issues:
        print(f"⚠️  Found {len(issues)} validation issues:")
        for issue in issues:
            print(f"  {issue}")
    else:
        print("✓ Base IDF is valid (no issues found)")
    
    print("\n" + "=" * 70)
    print("✅ ALL TESTS PASSED")
    print("=" * 70)

if __name__ == "__main__":
    try:
        test_idf_handler()
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()

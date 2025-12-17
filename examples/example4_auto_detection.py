"""
Example 4: Automatic Zone Detection and Building Context
Demonstrates the new automated workflow with building metadata extraction
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.pipeline import HVACLLMPipeline

def main():
    """Run pipeline with automatic zone detection and building context extraction"""
    
    print("=" * 70)
    print("EXAMPLE 4: Auto-Detection & Building Context Extraction")
    print("=" * 70)
    print("\n✨ NEW FEATURES:")
    print("  • Automatic zone detection from IDF")
    print("  • Building metadata extraction (area, orientation, loads)")
    print("  • Context-aware HVAC generation")
    print("  • Base IDF validation")
    print("")
    
    # Initialize pipeline
    pipeline = HVACLLMPipeline()
    
    # ========== MODE 1: Full Auto-Detection (Recommended) ==========
    print("\n" + "=" * 70)
    print("MODE 1: Full Auto-Detection (All zones, auto-extracted metadata)")
    print("=" * 70)
    
    base_idf = "../data/base_idfs/building_with_zones.idf"
    user_request = "Design a high-efficiency VRF system with heat recovery for cold climate"
    
    print(f"\nBase IDF: {base_idf}")
    print(f"Zones: Auto-detect from IDF")
    print(f"User Request: {user_request}")
    print("\n" + "-" * 70)
    
    try:
        results = pipeline.run(
            base_idf=base_idf,
            # zones=None (default) - auto-detects ALL zones from IDF
            output_name="example4_auto_all_zones",
            system_name="VRF_Auto_System",
            user_request=user_request,
            enable_quick_validation=True
        )
        
        print("\n✓ MODE 1 COMPLETED")
        print(f"  Status: {results['final_status']}")
        print(f"  Zones detected: {len(results['zones'])}")
        print(f"  Zone names: {', '.join(results['zones'])}")
        print(f"  Building area: {results['building_context']['total_area']:.1f} m²")
        
    except Exception as e:
        print(f"\n❌ MODE 1 FAILED: {e}")
    
    
    # ========== MODE 2: Selective Zones (Manual Override) ==========
    print("\n\n" + "=" * 70)
    print("MODE 2: Selective Zone Override (Manual zone selection)")
    print("=" * 70)
    
    base_idf = "../data/base_idfs/4ZoneWithShading_Simple_2.idf"
    selected_zones = ["SPACE1-1", "SPACE2-1"]  # Only these zones
    user_request = "Design VRF for office spaces only, exclude storage and mechanical"
    
    print(f"\nBase IDF: {base_idf}")
    print(f"Zones: {', '.join(selected_zones)} (manual selection)")
    print(f"User Request: {user_request}")
    print("\n" + "-" * 70)
    
    try:
        results = pipeline.run(
            base_idf=base_idf,
            zones=selected_zones,  # Manual zone selection
            output_name="example4_selective_zones",
            system_name="VRF_Office_Only",
            user_request=user_request,
            enable_quick_validation=True
        )
        
        print("\n✓ MODE 2 COMPLETED")
        print(f"  Status: {results['final_status']}")
        print(f"  Zones used: {len(results['zones'])}")
        print(f"  Auto-detected: {results['zones_auto_detected']}")
        
    except Exception as e:
        print(f"\n❌ MODE 2 FAILED: {e}")
    
    
    # ========== MODE 3: Batch Processing ==========
    print("\n\n" + "=" * 70)
    print("MODE 3: Batch Processing (Multiple buildings)")
    print("=" * 70)
    
    batch_configs = [
        {
            "base_idf": "../data/base_idfs/building_with_zones.idf",
            "zones": None,  # Auto-detect
            "request": "Standard efficiency VRF",
            "output": "batch_building1"
        },
        {
            "base_idf": "../data/base_idfs/4ZoneWithShading_Simple_2.idf",
            "zones": None,  # Auto-detect
            "request": "High-efficiency VRF with heat recovery",
            "output": "batch_building2"
        }
    ]
    
    for i, config in enumerate(batch_configs, 1):
        print(f"\n--- Processing Building {i}/{len(batch_configs)} ---")
        print(f"IDF: {config['base_idf']}")
        
        try:
            results = pipeline.run(
                base_idf=config['base_idf'],
                zones=config['zones'],
                output_name=config['output'],
                user_request=config['request'],
                enable_quick_validation=False  # Disable for speed in batch
            )
            
            print(f"✓ Building {i} completed: {results['final_status']}")
            
        except Exception as e:
            print(f"❌ Building {i} failed: {e}")
    
    
    # ========== Summary ==========
    print("\n\n" + "=" * 70)
    print("SUMMARY: Benefits of Auto-Detection")
    print("=" * 70)
    print("""
✅ ADVANTAGES:
  • Zero manual zone input required
  • Eliminates typos and case sensitivity errors
  • Building metadata automatically extracted (area, orientation, loads)
  • Context-aware HVAC sizing
  • Scalable to batch processing (100s of buildings)
  • Self-validating (checks zones exist)

📊 BUILDING CONTEXT EXTRACTED:
  • Number of zones
  • Zone names
  • Total floor area (m²)
  • Total volume (m³)
  • Building orientation (degrees)
  • Internal loads (People, Lights, Equipment)
  • Location/climate

💡 USAGE MODES:
  1. Auto-detect all zones: zones=None (default)
  2. Manual selection: zones=["Zone1", "Zone2"]
  3. Hybrid: Validate + use specific zones

🎯 RECOMMENDATION:
  Use auto-detection (zones=None) for most cases.
  Use manual selection only for partial building HVAC.
""")

if __name__ == "__main__":
    main()

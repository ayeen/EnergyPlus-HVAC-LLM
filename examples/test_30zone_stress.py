"""
Example: 30-Zone Commercial Building Stress Test
=================================================
Tests the HVAC-LLM pipeline with a 30-zone, 3-floor commercial building
to verify scalability beyond the previous 20-zone maximum.

Building Layout:
  Floor 1 (Ground):  Reception, Lobby, 5 Offices, 2 Conference Rooms, IT Server Room  (10 zones)
  Floor 2 (Middle):  6 Offices, 2 Conference Rooms, Research Lab, Break Room           (10 zones)
  Floor 3 (Top):     5 Offices, Executive Suite, 2 Conference Rooms, Break Room, Rooftop Lounge  (10 zones)

Total: 30 zones — stress test for max zone handling capacity.
"""

import sys
import os
import json
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.pipeline import HVACLLMPipeline

# ──────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BASE_IDF = os.path.join(PROJECT_ROOT, "data", "base_idfs", "commercial_building_30zone.idf")

USER_REQUEST = (
    "Design a comprehensive VRF HVAC system for a 3-floor commercial building "
    "with 30 zones. The building includes offices, conference rooms, a research lab, "
    "an IT server room, break rooms, reception, lobby, an executive suite, and a "
    "rooftop lounge. The server room needs continuous high-capacity cooling. "
    "Ensure proper sizing, efficient operation with heat recovery, and independent "
    "temperature control for each zone."
)

OUTPUT_NAME = "vrf_commercial_30zone"


def main():
    print("\n" + "=" * 80)
    print("  🏢  HVAC-LLM STRESS TEST: 30-ZONE COMMERCIAL BUILDING")
    print("=" * 80)
    print(f"\n📄 Base IDF:      {BASE_IDF}")
    print(f"📝 Output Name:   {OUTPUT_NAME}")
    print(f"🔢 Expected Zones: 30 (3 floors × 10 zones each)")
    print(f"\n💬 User Request:\n   {USER_REQUEST}\n")
    print("=" * 80)

    # Verify the base IDF exists
    if not os.path.exists(BASE_IDF):
        print(f"\n❌ ERROR: Base IDF not found: {BASE_IDF}")
        print("   Please ensure commercial_building_30zone.idf exists in data/base_idfs/")
        sys.exit(1)

    # Count zones in the IDF for verification
    zone_count = 0
    zone_names = []
    with open(BASE_IDF, 'r') as f:
        lines = f.readlines()
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("Zone,"):
                # Next non-comment line should have the zone name
                for j in range(i + 1, min(i + 5, len(lines))):
                    name_line = lines[j].strip()
                    if name_line and not name_line.startswith("!"):
                        zone_name = name_line.split(",")[0].strip().rstrip(";")
                        zone_names.append(zone_name)
                        zone_count += 1
                        break

    print(f"\n✅ Base IDF verified: {zone_count} zones detected")
    print(f"\n📋 Zone List:")
    print("   ─── Floor 1 (Ground) ───")
    for z in zone_names[:10]:
        print(f"     • {z}")
    print("   ─── Floor 2 (Middle) ───")
    for z in zone_names[10:20]:
        print(f"     • {z}")
    print("   ─── Floor 3 (Top) ───")
    for z in zone_names[20:30]:
        print(f"     • {z}")

    print(f"\n{'='*80}")
    print("  🚀 Starting Pipeline...")
    print(f"{'='*80}\n")

    # Initialize and run pipeline
    start_time = time.time()

    pipeline = HVACLLMPipeline()
    result = pipeline.run(
        base_idf=BASE_IDF,
        zones=None,           # Auto-detect all 30 zones
        output_name=OUTPUT_NAME,
        user_request=USER_REQUEST,
        enable_quick_validation=False
    )

    elapsed = time.time() - start_time

    # ──────────────────────────────────────────────────────────────────
    # Results Summary
    # ──────────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("  📊  30-ZONE STRESS TEST RESULTS")
    print("=" * 80)
    print(f"  ✅ Final Status:        {result['final_status']}")
    print(f"  🔁 Total Iterations:    {result['total_iterations']}")
    print(f"  ⏱️  Total Time:          {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
    print(f"  📄 Final IDF:           {result['final_idf']}")
    print(f"  🔢 Zones Attempted:     30")
    first_try = result['total_iterations'] == 0
    print(f"  🎯 First-Try Success:   {'Yes' if first_try else 'No'}")
    print("=" * 80)

    # Verify the output IDF has all 30 zones covered
    if result['final_status'].upper() == 'SUCCESS' and result['final_idf']:
        final_idf_path = result['final_idf']
        if os.path.exists(final_idf_path):
            with open(final_idf_path, 'r') as f:
                content = f.read()

            # Count HVACTemplate:Zone:VRF objects in output
            hvac_zone_count = content.lower().count("hvactemplate:zone:vrf")
            thermostat_count = content.lower().count("hvactemplate:thermostat")
            system_count = content.lower().count("hvactemplate:system:vrf")

            print(f"\n  📋 Output IDF Analysis:")
            print(f"     • HVACTemplate:System:VRF objects:  {system_count}")
            print(f"     • HVACTemplate:Zone:VRF objects:    {hvac_zone_count}")
            print(f"     • HVACTemplate:Thermostat objects:  {thermostat_count}")
            print(f"     • Expected zone coverage:           30")
            print(f"     • Zone coverage:                    {hvac_zone_count}/30 ({hvac_zone_count/30*100:.0f}%)")

            if hvac_zone_count >= 30:
                print(f"\n  🎉 ALL 30 ZONES COVERED — STRESS TEST PASSED!")
            else:
                print(f"\n  ⚠️  Only {hvac_zone_count}/30 zones covered — PARTIAL COVERAGE")
        else:
            print(f"\n  ⚠️  Output IDF file not found at: {final_idf_path}")
    else:
        print(f"\n  ❌ Pipeline did not succeed. Status: {result['final_status']}")

    print("=" * 80)

    # Save results to JSON for analysis
    results_data = {
        "test_name": "30_zone_stress_test",
        "zones_count": 30,
        "building_type": "3-floor commercial (offices, conference, lab, server room, break rooms, lounge)",
        "final_status": result["final_status"],
        "total_iterations": result["total_iterations"],
        "elapsed_seconds": round(elapsed, 2),
        "first_try_success": first_try,
        "final_idf": result["final_idf"],
        "zone_names": zone_names
    }

    results_path = os.path.join(PROJECT_ROOT, "outputs", "30zone_stress_test_results.json")
    with open(results_path, 'w') as f:
        json.dump(results_data, f, indent=2)
    print(f"\n  💾 Results saved to: {results_path}")
    print("=" * 80 + "\n")

    return result


if __name__ == "__main__":
    main()

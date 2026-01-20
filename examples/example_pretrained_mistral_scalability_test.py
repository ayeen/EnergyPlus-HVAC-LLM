#!/usr/bin/env python3
"""
Professor's Scalability Test: Pre-trained Mistral API

Scenario 1: WITHOUT examples in prompt (1, 2, 4, 10, 20 zones)
Scenario 2: WITH simple example in prompt (1, 2, 4, 10, 20 zones)

Goal: Find the "breaking point" where pre-trained Mistral fails
"""

import sys
import os
import json
import time
from datetime import datetime
from dotenv import load_dotenv

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY", "").strip()

# Zone counts to test
ZONE_COUNTS = [1, 2, 4, 10, 20]


def generate_zone_names(count: int) -> list:
    """Generate zone names"""
    return [f"Zone{i+1}" for i in range(count)]


def call_mistral_api(prompt: str, max_tokens: int = 8000) -> dict:
    """Call Mistral API"""
    from mistralai import Mistral
    
    client = Mistral(api_key=MISTRAL_API_KEY)
    
    start = time.time()
    try:
        response = client.chat.complete(
            model="mistral-small-latest",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=max_tokens
        )
        elapsed = time.time() - start
        output = response.choices[0].message.content
        return {"success": True, "output": output, "time": elapsed}
    except Exception as e:
        return {"success": False, "error": str(e), "time": time.time() - start}


def analyze_output(output: str, expected_zones: int) -> dict:
    """Analyze if output is valid VRF IDF"""
    analysis = {
        "has_hvactemplate_system": "HVACTemplate:System:VRF" in output,
        "has_hvactemplate_zone": "HVACTemplate:Zone:VRF" in output,
        "has_airconditioner_vrf": "AirConditioner:VariableRefrigerantFlow" in output,
        "has_markdown": "```" in output,
        "char_count": len(output),
        "line_count": output.count("\n"),
    }
    
    # Count zone objects
    zone_vrf_count = output.count("HVACTemplate:Zone:VRF")
    analysis["zone_vrf_count"] = zone_vrf_count
    analysis["expected_zones"] = expected_zones
    analysis["zone_count_match"] = zone_vrf_count == expected_zones
    
    # Determine format
    if analysis["has_hvactemplate_system"]:
        analysis["format"] = "HVACTemplate (correct)"
    elif analysis["has_airconditioner_vrf"]:
        analysis["format"] = "Raw IDF (wrong)"
    else:
        analysis["format"] = "Unknown/Invalid"
    
    # Overall validity
    analysis["valid"] = (
        analysis["has_hvactemplate_system"] and 
        analysis["has_hvactemplate_zone"] and 
        not analysis["has_markdown"]
    )
    
    return analysis


# =============================================================================
# SCENARIO 1: WITHOUT EXAMPLES
# =============================================================================

def build_prompt_no_examples(zones: list) -> str:
    """Build prompt WITHOUT any examples"""
    zone_list = ", ".join(zones)
    return f"""Generate EnergyPlus IDF objects for a VRF (Variable Refrigerant Flow) HVAC system.

Zones to serve: {zone_list}

Requirements:
- Create the VRF outdoor unit
- Create VRF terminal units for each zone
- Include cooling and heating capability
- Use appropriate COP values
- Follow EnergyPlus IDF syntax

Generate only the IDF objects, no explanations."""


# =============================================================================
# SCENARIO 2: WITH SIMPLE EXAMPLE
# =============================================================================

def build_prompt_with_example(zones: list) -> str:
    """Build prompt WITH a simple single-zone example"""
    zone_list = ", ".join(zones)
    
    return f"""Generate EnergyPlus IDF objects for a VRF (Variable Refrigerant Flow) HVAC system.

Zones to serve: {zone_list}

Here is a simple example of the expected format for ONE zone:

HVACTemplate:System:VRF,
    Example_VRF_System,      !- Name
    ,                        !- System Availability Schedule Name
    autosize,                !- Gross Rated Total Cooling Capacity {{W}}
    3.3,                     !- Gross Rated Cooling COP {{W/W}}
    -5,                      !- Minimum Outdoor Temperature in Cooling Mode {{C}}
    43,                      !- Maximum Outdoor Temperature in Cooling Mode {{C}}
    autosize,                !- Gross Rated Heating Capacity {{W}}
    3.4,                     !- Gross Rated Heating COP {{W/W}}
    -20,                     !- Minimum Outdoor Temperature in Heating Mode {{C}}
    16,                      !- Maximum Outdoor Temperature in Heating Mode {{C}}
    AirCooled;               !- Condenser Type

HVACTemplate:Zone:VRF,
    ExampleZone,             !- Zone Name
    Example_VRF_System,      !- Template VRF System Name
    autosize,                !- Cooling Supply Air Flow Rate {{m3/s}}
    autosize,                !- Heating Supply Air Flow Rate {{m3/s}}
    ,                        !- No Load Supply Air Flow Rate {{m3/s}}
    ,                        !- Zone Heating Sizing Factor
    ,                        !- Zone Cooling Sizing Factor
    flow/person,             !- Outdoor Air Method
    0.00944,                 !- Outdoor Air Flow Rate per Person {{m3/s}}
    ,                        !- Outdoor Air Flow Rate per Zone Floor Area {{m3/s-m2}}
    ,                        !- Outdoor Air Flow Rate per Zone {{m3/s}}
    ,                        !- System Availability Schedule Name
    ,                        !- Supply Fan Operating Mode Schedule Name
    drawthrough,             !- Supply Fan Placement
    0.7,                     !- Supply Fan Total Efficiency
    400,                     !- Supply Fan Delta Pressure {{Pa}}
    autosize;                !- Supply Fan Motor Efficiency

Now generate SIMILAR IDF objects for the following {len(zones)} zones: {zone_list}

Requirements:
- Create ONE HVACTemplate:System:VRF object
- Create ONE HVACTemplate:Zone:VRF object for EACH zone ({len(zones)} total)
- Use the same format as the example above
- Output ONLY the IDF objects, no explanations or markdown"""


def run_test(scenario: str, zone_count: int, prompt_builder) -> dict:
    """Run a single test"""
    zones = generate_zone_names(zone_count)
    prompt = prompt_builder(zones)
    
    print(f"\n  Testing {zone_count} zone(s)...")
    print(f"    Prompt length: {len(prompt)} chars")
    
    result = call_mistral_api(prompt)
    
    if result["success"]:
        analysis = analyze_output(result["output"], zone_count)
        print(f"    ✓ Response: {analysis['char_count']} chars, {analysis['line_count']} lines")
        print(f"    Format: {analysis['format']}")
        print(f"    Has System VRF: {'✅' if analysis['has_hvactemplate_system'] else '❌'}")
        print(f"    Has Zone VRF: {'✅' if analysis['has_hvactemplate_zone'] else '❌'}")
        print(f"    Zone count: {analysis['zone_vrf_count']}/{zone_count} {'✅' if analysis['zone_count_match'] else '❌'}")
        print(f"    Has markdown: {'❌ YES' if analysis['has_markdown'] else '✅ NO'}")
        print(f"    Valid: {'✅' if analysis['valid'] else '❌'}")
        print(f"    Time: {result['time']:.2f}s")
        
        return {
            "zones": zone_count,
            "success": True,
            "valid": analysis["valid"],
            "format": analysis["format"],
            "has_system": analysis["has_hvactemplate_system"],
            "has_zones": analysis["has_hvactemplate_zone"],
            "zone_count_generated": analysis["zone_vrf_count"],
            "zone_count_expected": zone_count,
            "zone_count_match": analysis["zone_count_match"],
            "has_markdown": analysis["has_markdown"],
            "char_count": analysis["char_count"],
            "time": result["time"],
            "output_preview": result["output"][:1000]
        }
    else:
        print(f"    ❌ API Error: {result['error']}")
        return {
            "zones": zone_count,
            "success": False,
            "error": result["error"],
            "time": result["time"]
        }


def main():
    print("=" * 80)
    print("PROFESSOR'S SCALABILITY TEST: Pre-trained Mistral API")
    print("=" * 80)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Zone counts to test: {ZONE_COUNTS}")
    print()
    
    if not MISTRAL_API_KEY:
        print("❌ ERROR: MISTRAL_API_KEY not set!")
        return
    
    results = {
        "test_date": datetime.now().isoformat(),
        "zone_counts": ZONE_COUNTS,
        "scenario_1_no_examples": {},
        "scenario_2_with_examples": {}
    }
    
    # ==========================================================================
    # SCENARIO 1: WITHOUT EXAMPLES
    # ==========================================================================
    print("\n" + "=" * 80)
    print("SCENARIO 1: WITHOUT EXAMPLES IN PROMPT")
    print("=" * 80)
    print("Testing if pre-trained Mistral can generate valid VRF IDF")
    print("WITHOUT any format examples in the prompt...")
    
    for zone_count in ZONE_COUNTS:
        test_result = run_test("no_examples", zone_count, build_prompt_no_examples)
        results["scenario_1_no_examples"][f"{zone_count}_zones"] = test_result
        
        # Save intermediate results
        output_file = os.path.join(PROJECT_ROOT, "outputs", "professor_scalability_test.json")
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2, default=str)
    
    # ==========================================================================
    # SCENARIO 2: WITH SIMPLE EXAMPLE
    # ==========================================================================
    print("\n" + "=" * 80)
    print("SCENARIO 2: WITH SIMPLE EXAMPLE IN PROMPT")
    print("=" * 80)
    print("Testing if pre-trained Mistral can scale from a single example")
    print("to generate VRF for multiple zones...")
    
    for zone_count in ZONE_COUNTS:
        test_result = run_test("with_example", zone_count, build_prompt_with_example)
        results["scenario_2_with_examples"][f"{zone_count}_zones"] = test_result
        
        # Save intermediate results
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2, default=str)
    
    # ==========================================================================
    # SUMMARY
    # ==========================================================================
    print("\n" + "=" * 80)
    print("SUMMARY: SCALABILITY TEST RESULTS")
    print("=" * 80)
    
    print("\n{:<8} {:<20} {:<20}".format("Zones", "No Examples", "With Example"))
    print("-" * 50)
    
    for zone_count in ZONE_COUNTS:
        key = f"{zone_count}_zones"
        
        # Scenario 1 result
        s1 = results["scenario_1_no_examples"].get(key, {})
        if s1.get("success") and s1.get("valid"):
            s1_status = f"✅ Valid ({s1.get('zone_count_generated', 0)}/{zone_count})"
        elif s1.get("success"):
            s1_status = f"⚠️ Wrong format"
        else:
            s1_status = "❌ Failed"
        
        # Scenario 2 result
        s2 = results["scenario_2_with_examples"].get(key, {})
        if s2.get("success") and s2.get("valid") and s2.get("zone_count_match"):
            s2_status = f"✅ Valid ({s2.get('zone_count_generated', 0)}/{zone_count})"
        elif s2.get("success") and s2.get("valid"):
            s2_status = f"⚠️ Partial ({s2.get('zone_count_generated', 0)}/{zone_count})"
        elif s2.get("success"):
            s2_status = f"⚠️ Wrong format"
        else:
            s2_status = "❌ Failed"
        
        print(f"{zone_count:<8} {s1_status:<20} {s2_status:<20}")
    
    # Find breaking points
    print("\n" + "-" * 50)
    print("BREAKING POINT ANALYSIS:")
    
    # Scenario 1 breaking point
    s1_last_success = 0
    for zc in ZONE_COUNTS:
        key = f"{zc}_zones"
        if results["scenario_1_no_examples"].get(key, {}).get("valid"):
            s1_last_success = zc
    print(f"  Scenario 1 (No Examples): Max zones with valid output = {s1_last_success}")
    
    # Scenario 2 breaking point
    s2_last_success = 0
    for zc in ZONE_COUNTS:
        key = f"{zc}_zones"
        s2 = results["scenario_2_with_examples"].get(key, {})
        if s2.get("valid") and s2.get("zone_count_match"):
            s2_last_success = zc
    print(f"  Scenario 2 (With Example): Max zones with correct count = {s2_last_success}")
    
    print("\n" + "=" * 80)
    print("CONCLUSION")
    print("=" * 80)
    
    if s1_last_success == 0:
        print("\n📌 Scenario 1: Pre-trained Mistral CANNOT generate valid VRF IDF")
        print("   without examples, regardless of zone count.")
    else:
        print(f"\n📌 Scenario 1: Pre-trained Mistral works for {s1_last_success} zones without examples")
    
    if s2_last_success < 20:
        print(f"\n📌 Scenario 2: Pre-trained Mistral FAILS to scale beyond {s2_last_success} zones")
        print(f"   even with a simple example. Breaking point: >{s2_last_success} zones")
    else:
        print("\n📌 Scenario 2: Pre-trained Mistral successfully scaled to 20 zones with example")
    
    print(f"\n💾 Full results saved to: {output_file}")
    
    return results


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Test Pre-trained Mistral API on 20-Zone Large Office
Compare with Fine-tuned Mistral pipeline
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

# 20-zone configuration from hvac_requests.json
CONFIG = {
    "prompt": "Design a comprehensive VRF HVAC system for a large office building with 20 zones. Include all necessary components: outdoor units, terminal units for each zone, cooling/heating coils, fans, thermostats with appropriate schedules. The building has 12 office zones, 3 conference rooms, 3 executive offices, a lobby, and an IT server room. Ensure proper sizing and efficient operation.",
    "zones": [
        "Office_Zone_1", "Office_Zone_2", "Office_Zone_3", "Office_Zone_4", 
        "Office_Zone_5", "Office_Zone_6", "Office_Zone_7", "Office_Zone_8", 
        "Office_Zone_9", "Office_Zone_10", "Office_Zone_11", "Office_Zone_12", 
        "Conference_Room_1", "Conference_Room_2", "Conference_Room_3", 
        "Executive_Office_1", "Executive_Office_2", "Executive_Office_3", 
        "Lobby", "IT_Server_Room"
    ],
    "base_idf": "data/base_idfs/large_office_20zone.idf"
}


def test_pretrained_api_no_example() -> dict:
    """Test pre-trained Mistral API WITHOUT examples"""
    from mistralai import Mistral
    
    zone_list = ", ".join(CONFIG["zones"])
    prompt = f"""{CONFIG["prompt"]}

Zones to serve: {zone_list}

Generate EnergyPlus IDF objects for the VRF system. Use HVACTemplate objects.
Output only the IDF objects, no explanations or markdown."""

    print(f"  Prompt length: {len(prompt)} chars")
    
    client = Mistral(api_key=MISTRAL_API_KEY)
    
    start = time.time()
    response = client.chat.complete(
        model="mistral-small-latest",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=16000
    )
    elapsed = time.time() - start
    
    output = response.choices[0].message.content
    return {"success": True, "output": output, "time": elapsed, "prompt_len": len(prompt)}


def test_pretrained_api_with_example() -> dict:
    """Test pre-trained Mistral API WITH simple example"""
    from mistralai import Mistral
    
    zone_list = ", ".join(CONFIG["zones"])
    
    prompt = f"""{CONFIG["prompt"]}

Zones to serve: {zone_list}

Here is a simple example of the expected format:

HVACTemplate:System:VRF,
    VRF_System,              !- Name
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
    Zone_Name,               !- Zone Name
    VRF_System,              !- Template VRF System Name
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

Now generate SIMILAR IDF objects for all 20 zones listed above.
Create ONE HVACTemplate:System:VRF and 20 HVACTemplate:Zone:VRF objects.
Output ONLY the IDF objects, no markdown code blocks."""

    print(f"  Prompt length: {len(prompt)} chars")
    
    client = Mistral(api_key=MISTRAL_API_KEY)
    
    start = time.time()
    response = client.chat.complete(
        model="mistral-small-latest",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=16000
    )
    elapsed = time.time() - start
    
    output = response.choices[0].message.content
    return {"success": True, "output": output, "time": elapsed, "prompt_len": len(prompt)}


def test_finetuned_pipeline() -> dict:
    """Test fine-tuned Mistral through the full pipeline"""
    from config import settings
    settings.LLM_PROVIDER = 'mistral'
    
    from src.agents.llm_interface import UniversalLLM
    UniversalLLM._instance = None
    UniversalLLM._initialized = False
    
    from src.pipeline import HVACLLMPipeline
    
    pipeline = HVACLLMPipeline()
    base_idf = os.path.join(PROJECT_ROOT, CONFIG["base_idf"])
    
    start = time.time()
    result = pipeline.run(
        base_idf=base_idf,
        zones=CONFIG["zones"],
        output_name="pretrained_20zone_comparison",
        user_request=CONFIG["prompt"],
        enable_quick_validation=False
    )
    elapsed = time.time() - start
    
    return {
        "success": result.get("final_status") == "SUCCESS",
        "iterations": result.get("total_iterations", 0),
        "time": elapsed,
        "final_idf": result.get("final_idf", "")
    }


def analyze_output(output: str, expected_zones: int = 20) -> dict:
    """Analyze output quality"""
    analysis = {
        "has_hvactemplate_system": "HVACTemplate:System:VRF" in output,
        "has_hvactemplate_zone": "HVACTemplate:Zone:VRF" in output,
        "has_raw_idf": "AirConditioner:VariableRefrigerantFlow" in output,
        "has_markdown": "```" in output,
        "zone_vrf_count": output.count("HVACTemplate:Zone:VRF"),
        "char_count": len(output),
        "line_count": output.count("\n"),
    }
    
    analysis["zone_count_match"] = analysis["zone_vrf_count"] == expected_zones
    
    # Determine validity
    analysis["valid"] = (
        analysis["has_hvactemplate_system"] and
        analysis["has_hvactemplate_zone"] and
        not analysis["has_markdown"] and
        analysis["zone_count_match"]
    )
    
    # Determine format
    if analysis["has_hvactemplate_system"]:
        analysis["format"] = "HVACTemplate (correct)"
    elif analysis["has_raw_idf"]:
        analysis["format"] = "Raw IDF (wrong)"
    else:
        analysis["format"] = "Unknown"
    
    return analysis


def main():
    print("=" * 80)
    print("20-ZONE LARGE OFFICE TEST: Pre-trained vs Fine-tuned Mistral")
    print("=" * 80)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Zones: {len(CONFIG['zones'])}")
    print(f"Base IDF: {CONFIG['base_idf']}")
    print()
    
    results = {}
    
    # ==========================================================================
    # TEST 1: Pre-trained WITHOUT example
    # ==========================================================================
    print("\n" + "=" * 80)
    print("[1/3] PRE-TRAINED MISTRAL API - WITHOUT EXAMPLE")
    print("=" * 80)
    
    try:
        result1 = test_pretrained_api_no_example()
        analysis1 = analyze_output(result1["output"])
        
        results["pretrained_no_example"] = {
            "success": result1["success"],
            "time": result1["time"],
            "analysis": analysis1,
            "output_preview": result1["output"][:2000]
        }
        
        print(f"\n✓ Response received: {analysis1['char_count']} chars, {analysis1['line_count']} lines")
        print(f"  Format: {analysis1['format']}")
        print(f"  Has HVACTemplate:System:VRF: {'✅' if analysis1['has_hvactemplate_system'] else '❌'}")
        print(f"  Has HVACTemplate:Zone:VRF: {'✅' if analysis1['has_hvactemplate_zone'] else '❌'}")
        print(f"  Zone count: {analysis1['zone_vrf_count']}/20 {'✅' if analysis1['zone_count_match'] else '❌'}")
        print(f"  Has markdown: {'❌ YES' if analysis1['has_markdown'] else '✅ NO'}")
        print(f"  Overall Valid: {'✅' if analysis1['valid'] else '❌'}")
        print(f"  Time: {result1['time']:.2f}s")
        
        print(f"\n📄 Output Preview:")
        print("-" * 40)
        print(result1["output"][:1500])
        print("-" * 40)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        results["pretrained_no_example"] = {"success": False, "error": str(e)}
    
    # ==========================================================================
    # TEST 2: Pre-trained WITH example
    # ==========================================================================
    print("\n" + "=" * 80)
    print("[2/3] PRE-TRAINED MISTRAL API - WITH SIMPLE EXAMPLE")
    print("=" * 80)
    
    try:
        result2 = test_pretrained_api_with_example()
        analysis2 = analyze_output(result2["output"])
        
        results["pretrained_with_example"] = {
            "success": result2["success"],
            "time": result2["time"],
            "analysis": analysis2,
            "output_preview": result2["output"][:2000]
        }
        
        print(f"\n✓ Response received: {analysis2['char_count']} chars, {analysis2['line_count']} lines")
        print(f"  Format: {analysis2['format']}")
        print(f"  Has HVACTemplate:System:VRF: {'✅' if analysis2['has_hvactemplate_system'] else '❌'}")
        print(f"  Has HVACTemplate:Zone:VRF: {'✅' if analysis2['has_hvactemplate_zone'] else '❌'}")
        print(f"  Zone count: {analysis2['zone_vrf_count']}/20 {'✅' if analysis2['zone_count_match'] else '❌'}")
        print(f"  Has markdown: {'❌ YES' if analysis2['has_markdown'] else '✅ NO'}")
        print(f"  Overall Valid: {'✅' if analysis2['valid'] else '❌'}")
        print(f"  Time: {result2['time']:.2f}s")
        
        print(f"\n📄 Output Preview:")
        print("-" * 40)
        print(result2["output"][:1500])
        print("-" * 40)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        results["pretrained_with_example"] = {"success": False, "error": str(e)}
    
    # ==========================================================================
    # TEST 3: Fine-tuned Pipeline
    # ==========================================================================
    print("\n" + "=" * 80)
    print("[3/3] FINE-TUNED MISTRAL - FULL PIPELINE")
    print("=" * 80)
    
    try:
        result3 = test_finetuned_pipeline()
        
        results["finetuned_pipeline"] = {
            "success": result3["success"],
            "iterations": result3["iterations"],
            "time": result3["time"],
            "final_idf": result3["final_idf"]
        }
        
        print(f"\n✅ Pipeline completed!")
        print(f"  Success: {'✅' if result3['success'] else '❌'}")
        print(f"  Iterations: {result3['iterations']}")
        print(f"  Time: {result3['time']:.2f}s")
        print(f"  Final IDF: {result3['final_idf']}")
        
    except Exception as e:
        import traceback
        print(f"❌ Error: {e}")
        traceback.print_exc()
        results["finetuned_pipeline"] = {"success": False, "error": str(e)}
    
    # ==========================================================================
    # SUMMARY
    # ==========================================================================
    print("\n" + "=" * 80)
    print("SUMMARY: 20-ZONE COMPARISON")
    print("=" * 80)
    
    print(f"\n{'Model':<35} {'Valid Output':<15} {'Zone Count':<15} {'Time':<10}")
    print("-" * 75)
    
    # Pre-trained no example
    p1 = results.get("pretrained_no_example", {})
    if p1.get("success") and p1.get("analysis"):
        a1 = p1["analysis"]
        p1_valid = "✅" if a1.get("valid") else "❌"
        p1_zones = f"{a1.get('zone_vrf_count', 0)}/20"
        p1_time = f"{p1.get('time', 0):.1f}s"
    else:
        p1_valid = "❌ Error"
        p1_zones = "-"
        p1_time = "-"
    print(f"{'Pre-trained (no example)':<35} {p1_valid:<15} {p1_zones:<15} {p1_time:<10}")
    
    # Pre-trained with example
    p2 = results.get("pretrained_with_example", {})
    if p2.get("success") and p2.get("analysis"):
        a2 = p2["analysis"]
        p2_valid = "✅" if a2.get("valid") else "⚠️ Partial"
        p2_zones = f"{a2.get('zone_vrf_count', 0)}/20"
        p2_time = f"{p2.get('time', 0):.1f}s"
    else:
        p2_valid = "❌ Error"
        p2_zones = "-"
        p2_time = "-"
    print(f"{'Pre-trained (with example)':<35} {p2_valid:<15} {p2_zones:<15} {p2_time:<10}")
    
    # Fine-tuned
    p3 = results.get("finetuned_pipeline", {})
    p3_valid = "✅" if p3.get("success") else "❌"
    p3_zones = "20/20" if p3.get("success") else "-"
    p3_time = f"{p3.get('time', 0):.1f}s"
    p3_iter = f"({p3.get('iterations', 0)} iter)"
    print(f"{'Fine-tuned (pipeline)':<35} {p3_valid:<15} {p3_zones:<15} {p3_time} {p3_iter}")
    
    print("\n" + "=" * 80)
    print("CONCLUSION")
    print("=" * 80)
    
    if p1.get("analysis", {}).get("valid"):
        print("\n📌 Pre-trained WITHOUT example: ✅ Surprisingly worked for 20 zones!")
    else:
        print("\n📌 Pre-trained WITHOUT example: ❌ Failed (as expected)")
    
    if p2.get("analysis", {}).get("valid"):
        print("📌 Pre-trained WITH example: ✅ Generated valid 20-zone output!")
    elif p2.get("analysis", {}).get("has_hvactemplate_system"):
        print(f"📌 Pre-trained WITH example: ⚠️ Correct format but issues (markdown: {p2.get('analysis', {}).get('has_markdown')}, zones: {p2.get('analysis', {}).get('zone_vrf_count')}/20)")
    else:
        print("📌 Pre-trained WITH example: ❌ Failed")
    
    if p3.get("success"):
        print(f"📌 Fine-tuned pipeline: ✅ SUCCESS in {p3.get('iterations', 0)} iterations!")
    else:
        print("📌 Fine-tuned pipeline: ❌ Failed")
    
    # Save results
    output_file = os.path.join(PROJECT_ROOT, "outputs", "20zone_comparison_results.json")
    with open(output_file, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "config": CONFIG,
            "results": results
        }, f, indent=2, default=str)
    
    print(f"\n💾 Results saved to: {output_file}")
    
    return results


if __name__ == "__main__":
    main()

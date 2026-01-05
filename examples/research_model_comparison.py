#!/usr/bin/env python3
"""
Research Model Comparison Script
Runs systematic tests with both Mistral (fine-tuned) and Gemini (pre-trained) models.
Logs results for research paper.
"""

import sys
import os
import time
import json
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.pipeline import HVACLLMPipeline
from src.agents.llm_interface import UniversalLLM


def run_test(provider: str, test_name: str, zones: list, user_request: str):
    """
    Run a single test and return results.
    """
    print(f"\n{'='*70}")
    print(f"TEST: {test_name}")
    print(f"MODEL: {provider.upper()}")
    print(f"ZONES: {len(zones)}")
    print(f"{'='*70}\n")
    
    start_time = time.time()
    
    result = {
        "test_name": test_name,
        "provider": provider,
        "zones": len(zones),
        "zone_names": zones,
        "user_request": user_request,
        "start_time": datetime.now().isoformat(),
    }
    
    try:
        # Reset LLM singleton to switch providers
        UniversalLLM.reset()
        
        # Create pipeline with specified provider
        pipeline = HVACLLMPipeline(llm_provider=provider)
        
        # Get project root path
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        base_idf = os.path.join(project_root, "data/base_idfs/4ZoneWithShading_Simple_2_NoHVAC.idf")
        
        # Run pipeline
        final_result = pipeline.run(
            base_idf=base_idf,
            zones=zones,
            output_name=f"research_{provider}_{test_name}",
            user_request=user_request,
            enable_quick_validation=False
        )
        
        end_time = time.time()
        
        result["success"] = final_result.get("final_status") == "SUCCESS"
        result["iterations"] = final_result.get("total_iterations", 0)
        result["simulation_success"] = final_result.get("simulation_status") == "SUCCESS"
        result["duration_seconds"] = round(end_time - start_time, 2)
        result["first_try_success"] = result["iterations"] == 0 and result["success"]
        result["final_idf"] = final_result.get("final_idf", "")
        
        print(f"\n✅ Test completed in {result['duration_seconds']}s")
        print(f"   Iterations: {result['iterations']}")
        print(f"   First-try success: {result['first_try_success']}")
        
    except Exception as e:
        import traceback
        end_time = time.time()
        result["success"] = False
        result["error"] = str(e)
        result["traceback"] = traceback.format_exc()
        result["duration_seconds"] = round(end_time - start_time, 2)
        result["first_try_success"] = False
        result["iterations"] = -1
        print(f"\n❌ Test failed: {e}")
    
    result["end_time"] = datetime.now().isoformat()
    return result


def main():
    """Run all comparison tests."""
    
    print("\n" + "="*70)
    print(" RESEARCH MODEL COMPARISON TEST SUITE")
    print(" Pre-trained (Gemini) vs Fine-tuned (Mistral)")
    print("="*70)
    
    # Test configurations - using zones from 4ZoneWithShading_Simple_2_NoHVAC.idf
    # The base IDF has zones: ZONE 1, ZONE 2, ZONE 3, ZONE 4
    test_configs = [
        {
            "name": "single_zone",
            "zones": ["ZONE 1"],
            "request": "Design a simple VRF system for single zone"
        },
        {
            "name": "two_zone",
            "zones": ["ZONE 1", "ZONE 2"],
            "request": "Design a VRF system for 2 zones"
        },
        {
            "name": "four_zone",
            "zones": ["ZONE 1", "ZONE 2", "ZONE 3", "ZONE 4"],
            "request": "Design a VRF system with heat recovery for 4-zone commercial building"
        },
    ]
    
    # Models to test
    providers = ["mistral", "gemini"]
    
    all_results = []
    
    for provider in providers:
        print(f"\n{'#'*70}")
        print(f"# TESTING WITH {provider.upper()}")
        print(f"{'#'*70}")
        
        for config in test_configs:
            result = run_test(
                provider=provider,
                test_name=config["name"],
                zones=config["zones"],
                user_request=config["request"]
            )
            all_results.append(result)
            
            # Small delay between tests
            time.sleep(2)
    
    # Save results
    output_file = "outputs/scenario_comparison/research_comparison_results.json"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, "w") as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\n✅ Results saved to {output_file}")
    
    # Print summary table
    print("\n" + "="*70)
    print(" SUMMARY RESULTS")
    print("="*70)
    print(f"\n{'Test Case':<25} {'Provider':<10} {'Zones':<6} {'Iters':<6} {'Success':<8} {'Time(s)':<8}")
    print("-"*70)
    
    for r in all_results:
        print(f"{r['test_name']:<25} {r['provider']:<10} {r['zones']:<6} {r.get('iterations', 'N/A'):<6} "
              f"{'✅' if r['success'] else '❌':<8} {r['duration_seconds']:<8}")
    
    print("-"*70)
    
    # Calculate statistics
    mistral_results = [r for r in all_results if r['provider'] == 'mistral']
    gemini_results = [r for r in all_results if r['provider'] == 'gemini']
    
    mistral_first_try = sum(1 for r in mistral_results if r.get('first_try_success', False))
    gemini_first_try = sum(1 for r in gemini_results if r.get('first_try_success', False))
    
    mistral_avg_iters = sum(r.get('iterations', 0) for r in mistral_results) / len(mistral_results)
    gemini_avg_iters = sum(r.get('iterations', 0) for r in gemini_results) / len(gemini_results)
    
    print(f"\nMistral (Fine-tuned): {mistral_first_try}/{len(mistral_results)} first-try success, avg {mistral_avg_iters:.1f} iterations")
    print(f"Gemini (Pre-trained):  {gemini_first_try}/{len(gemini_results)} first-try success, avg {gemini_avg_iters:.1f} iterations")
    
    return all_results


if __name__ == "__main__":
    results = main()

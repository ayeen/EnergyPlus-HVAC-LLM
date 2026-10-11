"""
Compare Fine-tuned Mistral vs Pre-trained Mistral Models
This script tests both Mistral variants on the same 5 test cases
"""

import sys
import os
import json
import time
from datetime import datetime
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.pipeline import HVACLLMPipeline
from config.settings import Config
from src.agents.llm_interface import UniversalLLM

# Test cases: same as used for Gemini vs Fine-tuned comparison
TEST_CASES = [
    {
        "name": "single_zone",
        "zones": ["ZONE 1"],
        "base_idf": "data/base_idfs/4ZoneWithShading_Simple_2_NoHVAC.idf",
        "prompt": "Design a simple VRF system for single zone",
        "description": "Single zone office"
    },
    {
        "name": "two_zone",
        "zones": ["ZONE 1", "ZONE 2"],
        "base_idf": "data/base_idfs/4ZoneWithShading_Simple_2_NoHVAC.idf",
        "prompt": "Design a VRF system for 2 zones",
        "description": "Two zone building"
    },
    {
        "name": "four_zone",
        "zones": ["ZONE 1", "ZONE 2", "ZONE 3", "ZONE 4"],
        "base_idf": "data/base_idfs/4ZoneWithShading_Simple_2_NoHVAC.idf",
        "prompt": "Design a VRF system with heat recovery for 4-zone commercial building",
        "description": "Four zone commercial"
    },
    {
        "name": "ten_zone",
        "zones": None,  # Auto-detect
        "base_idf": "data/base_idfs/large_office_10zone.idf",
        "prompt": "Design VRF for a large office building with 10 zones",
        "description": "Large office with 10 zones"
    },
    {
        "name": "twenty_zone",
        "zones": None,  # Auto-detect
        "base_idf": "data/base_idfs/large_office_20zone.idf",
        "prompt": "Design a comprehensive VRF HVAC system for a large office building with 20 zones",
        "description": "Large office with 20 zones"
    },
]

def get_project_root():
    """Get absolute path to project root"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(script_dir)

def resolve_base_idf(relative_path):
    """Resolve base IDF path relative to project root"""
    project_root = get_project_root()
    return os.path.join(project_root, relative_path)

def run_test_with_model(test_case, provider, model_label):
    """Run a single test case with specified model"""
    print(f"\n{'='*70}")
    print(f"Test: {test_case['name'].upper()} ({test_case['description']})")
    print(f"Model: {model_label}")
    print(f"{'='*70}")
    
    try:
        # Reset LLM to ensure fresh model load for this provider
        UniversalLLM.reset()
        
        # Temporarily change provider
        original_provider = Config.LLM_PROVIDER
        Config.LLM_PROVIDER = provider
        
        # Create pipeline
        pipeline = HVACLLMPipeline()
        
        # Resolve base IDF path
        base_idf_path = resolve_base_idf(test_case["base_idf"])
        
        # Record start time
        start_time = time.time()
        
        # Run pipeline
        result = pipeline.run(
            base_idf=base_idf_path,
            zones=test_case.get("zones"),  # None for auto-detect
            output_name=f"mistral_compare_{provider}_{test_case['name']}",
            user_request=test_case["prompt"],
            enable_quick_validation=False
        )
        
        # Record end time
        end_time = time.time()
        duration = end_time - start_time
        
        # Extract results
        success = result.get('final_status') == 'SUCCESS'
        iterations = result.get('total_iterations', 0)
        first_try = iterations == 0
        
        # Restore original provider
        Config.LLM_PROVIDER = original_provider
        
        return {
            "test_name": test_case["name"],
            "provider": provider,
            "model_label": model_label,
            "zones": len(test_case.get("zones") or []) or "auto-detect",
            "success": success,
            "iterations": iterations,
            "first_try_success": first_try,
            "duration_seconds": round(duration, 2),
            "final_idf": result.get('final_idf', ''),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        
        # Restore original provider
        Config.LLM_PROVIDER = original_provider
        
        return {
            "test_name": test_case["name"],
            "provider": provider,
            "model_label": model_label,
            "zones": len(test_case.get("zones") or []) or "auto-detect",
            "success": False,
            "iterations": -1,
            "first_try_success": False,
            "duration_seconds": 0,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

def main():
    print("\n" + "="*70)
    print("MISTRAL MODEL COMPARISON: Fine-tuned vs Pre-trained")
    print("="*70)
    print(f"Fine-tuned Model: {Config.MISTRAL_FINETUNED_PATH}")
    print(f"Pre-trained Model: {Config.MISTRAL_PRETRAINED_PATH}")
    print(f"Total Test Cases: {len(TEST_CASES)}")
    print("="*70 + "\n")
    
    all_results = []
    
    # Test each case with both models
    for test_case in TEST_CASES:
        print(f"\n\n{'#'*70}")
        print(f"# TEST CASE: {test_case['name'].upper()}")
        print(f"{'#'*70}")
        
        # Test with fine-tuned model
        print("\n[1/2] Running with Fine-tuned Mistral...")
        ft_result = run_test_with_model(test_case, "mistral", "Fine-tuned")
        all_results.append(ft_result)
        
        # Test with pre-trained model
        print("\n[2/2] Running with Pre-trained Mistral...")
        pt_result = run_test_with_model(test_case, "mistral-pretrained", "Pre-trained")
        all_results.append(pt_result)
    
    # Generate summary report
    print("\n\n" + "="*70)
    print("SUMMARY REPORT")
    print("="*70 + "\n")
    
    # Create summary table
    print("Test Results:")
    print("-" * 120)
    print(f"{'Test':<15} {'Zones':<10} {'Model':<15} {'Success':<10} {'Iterations':<12} {'First-try':<12} {'Time (s)':<10}")
    print("-" * 120)
    
    for result in all_results:
        test_name = result['test_name']
        zones = str(result['zones'])
        model = result['model_label']
        success = "✅ YES" if result['success'] else "❌ NO"
        iterations = result['iterations'] if result['iterations'] >= 0 else "ERROR"
        first_try = "✅ YES" if result['first_try_success'] else "❌ NO"
        duration = result['duration_seconds']
        
        print(f"{test_name:<15} {zones:<10} {model:<15} {success:<10} {str(iterations):<12} {first_try:<12} {duration:<10}")
    
    print("-" * 120 + "\n")
    
    # Calculate statistics
    ft_results = [r for r in all_results if r['provider'] == 'mistral']
    pt_results = [r for r in all_results if r['provider'] == 'mistral-pretrained']
    
    ft_success_count = sum(1 for r in ft_results if r['first_try_success'])
    pt_success_count = sum(1 for r in pt_results if r['first_try_success'])
    
    ft_total_success = sum(1 for r in ft_results if r['success'])
    pt_total_success = sum(1 for r in pt_results if r['success'])
    
    ft_avg_iterations = sum(r['iterations'] for r in ft_results if r['iterations'] >= 0) / len([r for r in ft_results if r['iterations'] >= 0]) if ft_results else 0
    pt_avg_iterations = sum(r['iterations'] for r in pt_results if r['iterations'] >= 0) / len([r for r in pt_results if r['iterations'] >= 0]) if pt_results else 0
    
    ft_first_try_rate = (ft_success_count / len(ft_results) * 100) if ft_results else 0
    pt_first_try_rate = (pt_success_count / len(pt_results) * 100) if pt_results else 0
    
    print("STATISTICS:")
    print("-" * 70)
    print(f"\nFine-tuned Mistral Model:")
    print(f"  • First-try Success Rate: {ft_first_try_rate:.1f}% ({ft_success_count}/{len(ft_results)})")
    print(f"  • Total Success Rate: {ft_total_success/len(ft_results)*100:.1f}% ({ft_total_success}/{len(ft_results)})")
    print(f"  • Average Iterations: {ft_avg_iterations:.2f}")
    
    print(f"\nPre-trained Mistral Model:")
    print(f"  • First-try Success Rate: {pt_first_try_rate:.1f}% ({pt_success_count}/{len(pt_results)})")
    print(f"  • Total Success Rate: {pt_total_success/len(pt_results)*100:.1f}% ({pt_total_success}/{len(pt_results)})")
    print(f"  • Average Iterations: {pt_avg_iterations:.2f}")
    
    # Comparison
    print(f"\nComparison:")
    print(f"  • First-try Advantage: Fine-tuned by {ft_first_try_rate - pt_first_try_rate:.1f}%")
    print(f"  • Iteration Advantage: Fine-tuned by {pt_avg_iterations - ft_avg_iterations:.2f} iterations")
    
    print("-" * 70 + "\n")
    
    # Save results to JSON
    project_root = get_project_root()
    output_dir = os.path.join(project_root, "outputs", "scenario_comparison")
    os.makedirs(output_dir, exist_ok=True)
    
    results_file = os.path.join(output_dir, "mistral_comparison_results.json")
    with open(results_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print(f"✓ Results saved to: {results_file}")
    
    print("\n" + "="*70)
    print("COMPARISON COMPLETE")
    print("="*70)

if __name__ == "__main__":
    main()

"""
Quick Comparison: Fine-tuned vs Pre-trained Mistral
Tests both models on the same simple scenario
"""

import sys
import os
import time
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.pipeline import HVACLLMPipeline
from config.settings import Config
from src.agents.llm_interface import UniversalLLM

def run_test(provider, model_name):
    """Run a single zone test with specified model"""
    print(f"\n{'='*70}")
    print(f"Testing: {model_name}")
    print(f"Provider: {provider}")
    print(f"{'='*70}\n")
    
    try:
        # Reset to ensure fresh model load
        UniversalLLM.reset()
        
        # Set provider
        Config.LLM_PROVIDER = provider
        
        # Create pipeline
        pipeline = HVACLLMPipeline()
        
        # Base IDF path
        base_idf = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "data/base_idfs/4ZoneWithShading_Simple_2_NoHVAC.idf"
        )
        
        start_time = time.time()
        
        # Run test - single zone
        result = pipeline.run(
            base_idf=base_idf,
            zones=["ZONE 1"],
            output_name=f"comparison_{provider}_single_zone",
            user_request="Design a simple VRF system for single zone office",
            enable_quick_validation=False
        )
        
        duration = time.time() - start_time
        
        # Extract results
        success = result.get('final_status') == 'SUCCESS'
        iterations = result.get('total_iterations', 0)
        first_try = iterations == 0
        
        print(f"\n{'='*70}")
        print(f"RESULT for {model_name}:")
        print(f"  • Success: {'✅ YES' if success else '❌ NO'}")
        print(f"  • First-try Success: {'✅ YES' if first_try else '❌ NO'}")
        print(f"  • Total Iterations: {iterations}")
        print(f"  • Duration: {duration:.2f} seconds")
        print(f"{'='*70}\n")
        
        return {
            "model": model_name,
            "provider": provider,
            "success": success,
            "first_try": first_try,
            "iterations": iterations,
            "duration": duration
        }
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "model": model_name,
            "provider": provider,
            "success": False,
            "first_try": False,
            "iterations": -1,
            "duration": 0,
            "error": str(e)
        }

def main():
    print("\n" + "="*70)
    print("QUICK COMPARISON: Fine-tuned vs Pre-trained Mistral")
    print("="*70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Test: Single zone VRF system")
    print("="*70 + "\n")
    
    results = []
    
    # Test 1: Fine-tuned Mistral
    print("\n[1/2] Testing FINE-TUNED Mistral...")
    ft_result = run_test("mistral", "Fine-tuned Mistral (VRF-trained)")
    results.append(ft_result)
    
    # Test 2: Pre-trained Mistral
    print("\n[2/2] Testing PRE-TRAINED Mistral...")
    pt_result = run_test("mistral-pretrained", "Pre-trained Mistral (General)")
    results.append(pt_result)
    
    # Summary
    print("\n" + "="*70)
    print("COMPARISON SUMMARY")
    print("="*70)
    print(f"\n{'Model':<35} {'Success':<12} {'First-try':<12} {'Iterations':<12} {'Time (s)':<10}")
    print("-" * 85)
    
    for r in results:
        model = r['model'][:32] + "..." if len(r['model']) > 35 else r['model']
        success = "✅ YES" if r['success'] else "❌ NO"
        first_try = "✅ YES" if r['first_try'] else "❌ NO"
        iterations = r['iterations'] if r['iterations'] >= 0 else "ERROR"
        duration = f"{r['duration']:.1f}" if r['duration'] > 0 else "N/A"
        
        print(f"{model:<35} {success:<12} {first_try:<12} {str(iterations):<12} {duration:<10}")
    
    print("-" * 85)
    
    # Analysis
    print("\n" + "="*70)
    print("ANALYSIS")
    print("="*70)
    
    if ft_result['first_try'] and not pt_result['first_try']:
        print("\n✅ CONFIRMED: Fine-tuned Mistral outperforms Pre-trained Mistral")
        print("   Fine-tuned succeeded on first try, Pre-trained required corrections")
        print(f"   Iteration difference: {pt_result['iterations'] - ft_result['iterations']} more iterations for pre-trained")
    elif ft_result['first_try'] and pt_result['first_try']:
        print("\n🤔 UNEXPECTED: Both models succeeded on first try")
        print("   This is unusual for pre-trained model - check generated IDF for quality")
    elif not ft_result['first_try'] and not pt_result['first_try']:
        print("\n⚠ BOTH FAILED first try")
        print(f"   Fine-tuned iterations: {ft_result['iterations']}")
        print(f"   Pre-trained iterations: {pt_result['iterations']}")
    else:
        print("\n❓ UNEXPECTED: Pre-trained did better than fine-tuned")
        print("   This is very unusual - verify test conditions")
    
    print("\n" + "="*70)
    print("COMPARISON COMPLETE")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()

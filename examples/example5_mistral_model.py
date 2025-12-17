#!/usr/bin/env python3
"""
Example: Using Mistral Fine-tuned Model
========================================

This example demonstrates using the Mistral fine-tuned model
in the HVAC-LLM pipeline.

The integration supports both Mistral and Gemini seamlessly!

Author: HVAC-LLM
Date: December 12, 2025
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from src.pipeline import HVACLLMPipeline

def main():
    """Run VRF generation with Mistral"""
    
    print("=" * 80)
    print("MISTRAL FINE-TUNED MODEL - VRF GENERATION EXAMPLE")
    print("=" * 80)
    print()
    
    # Configure to use Mistral
    # (You can also edit config/settings.py to set this permanently)
    print("📝 Configuration:")
    print(f"   Provider: {Config.LLM_PROVIDER}")
    
    if Config.LLM_PROVIDER == "mistral":
        print(f"   Mistral Model: {Config.MISTRAL_FINETUNED_PATH}")
        print(f"   Using iterative generation for high-quality VRF systems")
    elif Config.LLM_PROVIDER == "gemini":
        print(f"   Gemini Model: {Config.LLM_MODEL}")
        print(f"   Using single-pass generation")
    
    print()
    print("💡 To switch providers, edit config/settings.py:")
    print("   - LLM_PROVIDER = 'mistral'  # Use fine-tuned Mistral")
    print("   - LLM_PROVIDER = 'gemini'   # Use Gemini API")
    print()
    
    # Initialize pipeline
    pipeline = HVACLLMPipeline()
    
    # Configuration
    base_idf = "data/base_idfs/4ZoneWithShading_Simple_2_NoHVAC.idf"
    output_name = "mistral_example_vrf"
    
    # User request (natural language)
    user_request = """
    Design a high-efficiency VRF system with the following features:
    - Heat recovery for energy savings
    - Intelligent thermostat controls
    - Optimized for office building usage
    - Reliable operation in all seasons
    """
    
    print("🏢 Building: 4-Zone Office")
    print(f"📄 Base IDF: {base_idf}")
    print(f"💬 User Request: {user_request.strip()}")
    print()
    
    # Run pipeline
    print("🚀 Starting VRF generation...")
    print()
    
    results = pipeline.run(
        base_idf=base_idf,
        zones=None,  # Auto-detect zones
        output_name=output_name,
        system_name="Office_VRF_System",
        user_request=user_request,
        enable_quick_validation=True  # Enable LLM pre-validation
    )
    
    # Display results
    print()
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)
    print()
    
    status = results.get('final_status', 'UNKNOWN')
    print(f"Status: {status}")
    
    if status == 'SUCCESS':
        print("✅ VRF system generated successfully!")
        print()
        print("📁 Output files:")
        print(f"   - outputs/generated_idfs/{output_name}_FINAL.idf")
        print(f"   - outputs/logs/{output_name}_pipeline.json")
        print()
        
        # Show generation details
        if 'steps' in results:
            for step in results['steps']:
                if step.get('name') == 'HVAC Generation':
                    print(f"   Generated {step.get('objects_generated', 0)} HVAC objects")
        
        # Show building context
        if 'building_context' in results:
            bc = results['building_context']
            print()
            print("📊 Building Context:")
            print(f"   - Zones: {bc.get('num_zones', 0)}")
            if bc.get('total_area', 0) > 0:
                print(f"   - Floor Area: {bc['total_area']:.1f} m²")
            if bc.get('total_volume', 0) > 0:
                print(f"   - Volume: {bc['total_volume']:.1f} m³")
        
        # Show simulation results
        if 'simulation' in results:
            sim = results['simulation']
            print()
            print("⚡ Simulation:")
            print(f"   - Status: {sim.get('status', 'unknown')}")
            if sim.get('status') == 'success':
                print(f"   - Warnings: {sim.get('warnings', 0)}")
                print(f"   - Errors: {sim.get('errors', 0)}")
        
        print()
        print("✅ Pipeline completed successfully!")
        
    else:
        print(f"⚠️  Pipeline completed with status: {status}")
        if 'error' in results:
            print(f"   Error: {results['error']}")
    
    print()
    print("=" * 80)
    print()
    
    return results


if __name__ == "__main__":
    main()

"""
Example 2: Complete Pipeline
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.pipeline import HVACLLMPipeline

def main():
    """Run complete pipeline"""
    
    print("=" * 70)
    print("EXAMPLE 2: Complete HVAC-LLM Pipeline")
    print("=" * 70)
    
    # Initialize pipeline
    pipeline = HVACLLMPipeline()
    
    # Define project - use path relative to project root
    base_idf = "data/base_idfs/building_with_zones.idf"
    zones = ["ZONE ONE"]  # Must match the exact zone name in the IDF
    
    # Optional: Natural language design request
    user_request = "Design a VRF HVAC system with heat recovery for efficient heating and cooling"
    
    print(f"\nBase IDF: {base_idf}")
    print(f"Zones: {', '.join(zones)}")
    if user_request:
        print(f"User Request: {user_request}")
    print("\nStarting pipeline...")
    print("-" * 70)
    
    # Run pipeline
    # NOTE: You need to create the base IDF file first
    results = pipeline.run(
        base_idf=base_idf,
        zones=zones,
        output_name="example2_complete",
        system_name="VRF_System_1",
        user_request=user_request,  # Pass the user's design request
        enable_quick_validation=False  # Enable quick validation
    )
    # 
    print("\n" + "=" * 70)
    print("PIPELINE RESULTS")
    print("=" * 70)
    print(f"Status: {results['final_status']}")
    print(f"Iterations: {results['total_iterations']}")
    print(f"Final IDF: {results['final_idf']}")
    
    # print("\nTo run this example:")
    # print("1. Create a base IDF file in data/base_idfs/")
    # print("2. Update the base_idf path above")
    # print("3. Uncomment the pipeline.run() code")
    # print("4. Run: python example2_complete_pipeline.py")

if __name__ == "__main__":
    main()

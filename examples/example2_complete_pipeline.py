"""
Example 2: Complete Pipeline
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.pipeline import HVACLLMPipeline

def main():
    """Run complete pipeline with automatic zone detection"""
    
    print("=" * 70)
    print("EXAMPLE 2: Complete HVAC-LLM Pipeline (Auto-Detection)")
    print("=" * 70)
    
    # Initialize pipeline
    pipeline = HVACLLMPipeline()
    
    # Define project - use path relative to project root
    base_idf = "data/base_idfs/4ZoneWithShading_Simple_2_NoHVAC.idf"
    
    # NEW: zones parameter is now OPTIONAL!
    # If zones=None (or omitted), pipeline auto-detects all zones from IDF
    # If zones=["Zone1", "Zone2"], only those zones are used
    
    # Optional: Natural language design request
    user_request = "Design a VRF HVAC system with heat recovery for efficient heating and cooling"
    
    print(f"\nBase IDF: {base_idf}")
    print(f"Zone Selection: Auto-detect from IDF")
    if user_request:
        print(f"User Request: {user_request}")
    print("\nStarting pipeline...")
    print("-" * 70)
    
    # Run pipeline with AUTO-DETECTION (recommended)
    results = pipeline.run(
        base_idf=base_idf,
        # zones=None,  # Auto-detect all zones (default)
        # zones=["ZONE ONE"],  # Or specify specific zones
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

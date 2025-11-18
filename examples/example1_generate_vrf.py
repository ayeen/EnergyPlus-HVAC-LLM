"""
Example 1: Simple VRF System Generation
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agents.agent1_generator import HVACGenerator

def main():
    """Generate simple VRF system"""
    
    print("=" * 70)
    print("EXAMPLE 1: Generate VRF System")
    print("=" * 70)
    
    # Initialize generator
    generator = HVACGenerator()
    
    # Generate VRF system
    user_request = "Design a VRF HVAC system with heat recovery for efficient heating and cooling"
    zones = ["Zone One"]
    
    print(f"\nGenerating VRF system for {len(zones)} zones...")
    
    hvac_response = generator.generate_vrf_system(
        zones=zones,
        system_name="Office_VRF_System",
        user_request=user_request
    )
    
    # Check if response is empty (blocked by content filter)
    if not hvac_response or hvac_response.strip() == "":
        print("\n❌ Error: Empty HVAC configuration generated")
        return # Exit on failure
    
    print("\n✓ Generated HVAC configuration:")
    print("-" * 70)
    print(hvac_response[:500] + "..." if len(hvac_response) > 500 else hvac_response)
    print("-" * 70)
    
    # Add to IDF (using clean base IDF file)
    base_idf = "../data/base_idfs/building_with_zones.idf"
    output_idf = "../outputs/generated_idfs/building_with_vrf.idf"
    
    # Simple approach: manually combine base IDF + HVAC
    try:
        # Read base IDF
        with open(base_idf, 'r') as f:
            base_content = f.read()
        
        # Combine base + HVAC
        complete_idf = base_content + "\n\n! === HVAC SYSTEM ===\n\n" + hvac_response
        
        # Write complete IDF
        import os
        os.makedirs(os.path.dirname(output_idf), exist_ok=True)
        with open(output_idf, 'w') as f:
            f.write(complete_idf)
        
        # Count HVAC objects
        hvac_count = hvac_response.count('HVACTemplate:')
        
        print(f"\n✓ Successfully created complete IDF file")
        print(f"✓ Added {hvac_count} HVAC template objects")
        print(f"✓ Output: {output_idf}")
        print(f"✓ File size: {len(complete_idf)} characters")
        
    except Exception as e:
        print(f"\n❌ Failed to create IDF file: {str(e)}")

if __name__ == "__main__":
    main()

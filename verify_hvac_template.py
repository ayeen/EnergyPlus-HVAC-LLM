"""
Verify that the HVAC generator is creating HVACTemplate objects (not detailed VRF)
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.agents.agent1_generator import HVACGenerator

def main():
    """Verify HVAC object types"""
    
    print("=" * 70)
    print("VERIFICATION: HVAC Object Type Analysis")
    print("=" * 70)
    
    # Initialize generator
    generator = HVACGenerator()
    
    # Generate VRF system
    print("\nGenerating VRF system...")
    hvac_response = generator.generate_vrf_system(
        zones=["Zone One"],
        system_name="Test_VRF",
        user_request="Design a standard VRF system"
    )
    
    if not hvac_response:
        print("❌ No HVAC content generated")
        return
    
    print("\n" + "=" * 70)
    print("ANALYSIS OF GENERATED OBJECTS:")
    print("=" * 70)
    
    # Check for HVACTemplate objects (high-level, desired)
    hvac_template_system = "HVACTemplate:System:VRF" in hvac_response
    hvac_template_zone = "HVACTemplate:Zone:VRF" in hvac_response
    
    # Check for detailed VRF objects (low-level, undesired)
    detailed_airconditioner = "AirConditioner:VariableRefrigerantFlow" in hvac_response
    detailed_terminal = "ZoneHVAC:TerminalUnit:VariableRefrigerantFlow" in hvac_response
    
    print("\n✓ HVACTemplate Objects (High-level, Desired):")
    print(f"  - HVACTemplate:System:VRF: {'✓ FOUND' if hvac_template_system else '✗ NOT FOUND'}")
    print(f"  - HVACTemplate:Zone:VRF: {'✓ FOUND' if hvac_template_zone else '✗ NOT FOUND'}")
    
    print("\n✗ Detailed VRF Objects (Low-level, Undesired):")
    print(f"  - AirConditioner:VariableRefrigerantFlow: {'✗ FOUND (BAD!)' if detailed_airconditioner else '✓ NOT FOUND (GOOD)'}")
    print(f"  - ZoneHVAC:TerminalUnit:VariableRefrigerantFlow: {'✗ FOUND (BAD!)' if detailed_terminal else '✓ NOT FOUND (GOOD)'}")
    
    print("\n" + "=" * 70)
    print("CONCLUSION:")
    print("=" * 70)
    
    if hvac_template_system and hvac_template_zone and not detailed_airconditioner and not detailed_terminal:
        print("✅ CORRECT: System is generating HVACTemplate objects")
        print("   This is the recommended approach for EnergyPlus HVAC design.")
        print("   HVACTemplate objects are automatically expanded by EnergyPlus")
        print("   into detailed objects during simulation.")
    elif detailed_airconditioner or detailed_terminal:
        print("❌ INCORRECT: System is generating detailed VRF objects")
        print("   Should be changed to generate HVACTemplate objects instead.")
    else:
        print("⚠️  UNCLEAR: Unable to identify object types")
    
    print("\n" + "=" * 70)
    print("GENERATED CONTENT PREVIEW:")
    print("=" * 70)
    # Show first 1000 characters
    preview = hvac_response[:1000]
    print(preview)
    if len(hvac_response) > 1000:
        print("\n... (truncated, total length: {} characters)".format(len(hvac_response)))

if __name__ == "__main__":
    main()

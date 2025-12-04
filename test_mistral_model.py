"""
Test script to verify fine-tuned Mistral model integration
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.agents.llm_interface import UniversalLLM
from config import Config

def test_mistral_model():
    """Test the fine-tuned Mistral model"""
    
    print("=" * 80)
    print("Testing Fine-Tuned Mistral Model Integration")
    print("=" * 80)
    print()
    
    # Display configuration
    print(f"LLM Provider: {Config.LLM_PROVIDER}")
    print(f"Model Path: {Config.LLM_MODEL}")
    print(f"Max Tokens: {Config.LLM_MAX_TOKENS}")
    print(f"Temperature: {Config.LLM_TEMPERATURE}")
    print()
    
    # Initialize LLM
    print("Initializing Mistral model...")
    print("-" * 80)
    llm = UniversalLLM()
    print("-" * 80)
    print()
    
    # Test generation
    print("Testing generation...")
    print("-" * 80)
    
    system_prompt = """You are an expert in EnergyPlus HVAC system modeling. 
Generate valid IDF object definitions for HVAC components."""
    
    user_prompt = """Create a simple VRF outdoor unit object with the following specifications:
- Name: VRF_Outdoor_Unit_1
- Rated Cooling Capacity: 50000 W
- Rated Heating Capacity: 56000 W"""
    
    response = llm.generate(system_prompt, user_prompt)
    
    print("-" * 80)
    print()
    print("Generated Response:")
    print("=" * 80)
    print(response)
    print("=" * 80)
    print()
    
    if response and response != "************No response generated.*************":
        print("✓ SUCCESS: Mistral model is working correctly!")
    else:
        print("⚠ WARNING: No valid response generated")
    
    print()
    print("=" * 80)
    print("Test Complete")
    print("=" * 80)

if __name__ == "__main__":
    test_mistral_model()

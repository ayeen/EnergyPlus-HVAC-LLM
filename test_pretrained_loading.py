"""
Diagnostic script to test pre-trained Mistral model loading
This helps verify the model can be loaded without running full pipeline
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import Config

print("\n" + "="*70)
print("MISTRAL PRE-TRAINED MODEL LOADING TEST")
print("="*70)

print("\nConfiguration:")
print(f"  Pre-trained Model ID: {Config.MISTRAL_PRETRAINED_PATH}")
print(f"  Model Type: {Config.MISTRAL_PRETRAINED_TYPE}")
print("\nNote: First run will download ~13GB model from HuggingFace")
print("This may take 5-15 minutes depending on internet speed\n")

try:
    from src.agents.llm_interface import UniversalLLM
    
    print("Loading pre-trained Mistral model...")
    print("-" * 70)
    
    # Create instance with pre-trained provider
    llm = UniversalLLM(provider="mistral-pretrained")
    
    print("-" * 70)
    print("\n✓ Model loaded successfully!")
    
    # Test a simple generation
    print("\nTesting simple generation...")
    system_prompt = "You are a helpful assistant."
    user_prompt = "What is 2+2?"
    
    response = llm.generate(system_prompt, user_prompt)
    print(f"\nGenerated response:\n{response}\n")
    
    print("="*70)
    print("✓ TEST PASSED - Pre-trained model is working!")
    print("="*70)
    
except KeyboardInterrupt:
    print("\n\n⚠ Test interrupted by user")
    sys.exit(1)
except Exception as e:
    print(f"\n✗ Test failed with error:")
    print(f"  {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

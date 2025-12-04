"""
Diagnose Mistral Model Generation Issues
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.agents.llm_interface import UniversalLLM
from config import Config
import time

print("=" * 80)
print("Mistral Model Diagnostic Test")
print("=" * 80)

# Temporarily switch to Mistral
original_provider = Config.LLM_PROVIDER
original_model = Config.LLM_MODEL

Config.LLM_PROVIDER = "mistral"
Config.LLM_MODEL = r"D:\Ayeen\Project\Hvac-finedtuned-mistral-model\mistral-7b-vrf-merged"

print(f"Provider: {Config.LLM_PROVIDER}")
print(f"Model: {Config.LLM_MODEL}")
print()

# Initialize model
print("Loading model...")
start_time = time.time()
llm = UniversalLLM()
load_time = time.time() - start_time
print(f"✓ Model loaded in {load_time:.1f} seconds")
print()

# Test 1: Simple generation
print("=" * 80)
print("Test 1: Simple Text Generation")
print("=" * 80)

system_prompt = "You are a helpful assistant."
user_prompt = "Say 'Hello, I am working!' in one sentence."

print("Generating...")
start_time = time.time()
response = llm.generate(system_prompt, user_prompt)
gen_time = time.time() - start_time

print(f"Response ({gen_time:.1f}s):")
print(response)
print()

# Test 2: VRF Generation
print("=" * 80)
print("Test 2: VRF Object Generation")
print("=" * 80)

system_prompt = """You are an EnergyPlus IDF expert. Generate valid IDF object definitions."""

user_prompt = """Generate a simple AirConditioner:VariableRefrigerantFlow outdoor unit with:
- Name: VRF_Outdoor_Unit_1
- Cooling Capacity: 50000 W
- Heating Capacity: 56000 W

Output only the IDF object, nothing else."""

print("Generating VRF object...")
start_time = time.time()
response = llm.generate(system_prompt, user_prompt)
gen_time = time.time() - start_time

print(f"Response ({gen_time:.1f}s):")
print(response)
print()

# Analysis
print("=" * 80)
print("Analysis")
print("=" * 80)

if not response or response == "************No response generated.*************":
    print("❌ FAILED: No response generated")
    print("\nPossible causes:")
    print("1. Model is timing out (too slow on GPU)")
    print("2. Prompt format mismatch (model expects different format)")
    print("3. Memory issues (disk offloading)")
    print("4. Fine-tuning didn't work properly")
    print("\nRecommendations:")
    print("- Install vLLM for 10-20x speedup")
    print("- Check fine-tuning dataset quality")
    print("- Verify model wasn't corrupted during merge")
elif len(response) < 50:
    print("⚠ WARNING: Response too short")
    print(f"Length: {len(response)} characters")
elif "AirConditioner:VariableRefrigerantFlow" in response:
    print("✓ SUCCESS: Model generated VRF object!")
    print(f"Response length: {len(response)} characters")
    print(f"Generation time: {gen_time:.1f}s")
else:
    print("⚠ WARNING: Response generated but no VRF object found")
    print(f"Length: {len(response)} characters")

print("=" * 80)

# Restore original settings
Config.LLM_PROVIDER = original_provider
Config.LLM_MODEL = original_model

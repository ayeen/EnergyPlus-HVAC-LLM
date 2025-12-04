"""
Test Singleton Pattern - Verify Model Loads Only Once
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.agents.llm_interface import UniversalLLM
from config import Config

print("=" * 80)
print("Testing Singleton Pattern")
print("=" * 80)
print(f"Provider: {Config.LLM_PROVIDER}")
print(f"Model: {Config.LLM_MODEL}")
print()

# Simulate what happens in the pipeline
print("[Simulating Agent 1 - Generator]")
agent1_llm = UniversalLLM()
print()

print("[Simulating Agent 2 - Validator]")
agent2_llm = UniversalLLM()
print()

print("[Simulating Agent 3 - Corrector]")
agent3_llm = UniversalLLM()
print()

# Verify they're the same instance
print("=" * 80)
print("Verification:")
print("=" * 80)
print(f"Agent 1 LLM ID: {id(agent1_llm)}")
print(f"Agent 2 LLM ID: {id(agent2_llm)}")
print(f"Agent 3 LLM ID: {id(agent3_llm)}")
print()

if agent1_llm is agent2_llm is agent3_llm:
    print("✓ SUCCESS: All agents share the same LLM instance!")
    print("✓ Model will load only ONCE")
else:
    print("❌ FAILED: Agents have different instances")

print("=" * 80)

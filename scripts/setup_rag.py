"""
RAG Setup Script for HVAC-LLM

Automated setup script that:
1. Checks dependencies
2. Builds knowledge base
3. Tests retrieval
4. Provides integration instructions

Usage:
    python scripts/setup_rag.py
"""

import sys
import subprocess
from pathlib import Path

def check_dependencies():
    """Check if required packages are installed"""
    print("Checking dependencies...")
    
    required = {
        'chromadb': 'chromadb',
        'sentence_transformers': 'sentence-transformers'
    }
    
    missing = []
    for module, package in required.items():
        try:
            __import__(module)
            print(f"  ✓ {package}")
        except ImportError:
            print(f"  ❌ {package}")
            missing.append(package)
    
    if missing:
        print(f"\nMissing packages: {', '.join(missing)}")
        print("\nInstall with:")
        print(f"  pip install {' '.join(missing)}")
        return False
    
    return True

def build_knowledge_base():
    """Run knowledge base builder"""
    print("\nBuilding knowledge base...")
    
    try:
        result = subprocess.run(
            [sys.executable, "-m", "src.rag.knowledge_builder"],
            check=True,
            capture_output=False
        )
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"❌ Error building knowledge base: {e}")
        return False

def test_retrieval():
    """Run retrieval tests"""
    print("\nTesting retrieval...")
    
    try:
        result = subprocess.run(
            [sys.executable, "-m", "src.rag.rag_retriever"],
            check=True,
            capture_output=False
        )
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"❌ Error testing retrieval: {e}")
        return False

def main():
    """Main setup workflow"""
    print("=" * 70)
    print("HVAC-LLM RAG SETUP")
    print("=" * 70 + "\n")
    
    # Step 1: Check dependencies
    if not check_dependencies():
        print("\n❌ Setup failed: Missing dependencies")
        return 1
    
    # Step 2: Build knowledge base
    print("\n" + "=" * 70)
    if not build_knowledge_base():
        print("\n❌ Setup failed: Knowledge base build error")
        return 1
    
    # Step 3: Test retrieval
    print("\n" + "=" * 70)
    if not test_retrieval():
        print("\n⚠ Warning: Retrieval test failed")
    
    # Success
    print("\n" + "=" * 70)
    print("✅ RAG SETUP COMPLETE")
    print("=" * 70)
    print("\nNext Steps:")
    print("1. Review vector database: data/vector_db/")
    print("2. Integrate RAG into Agent 1: src/agents/agent1_generator.py")
    print("3. Integrate RAG into Agent 3: src/agents/agent3_corrector.py")
    print("\nSee documentation for integration examples.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

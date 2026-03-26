#!/usr/bin/env python
"""Quick test for backend imports"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

try:
    print("Testing imports...")

    print("  - Flask imports...", end=" ")
    from flask import Flask
    print("✓")

    print("  - Backend config...", end=" ")
    from backend_config import Config
    print("✓")

    print("  - Upload routes...", end=" ")
    from routes.upload import upload_bp
    print("✓")

    print("  - Pipeline routes...", end=" ")
    from routes.pipeline import pipeline_bp
    print("✓")

    print("  - Files routes...", end=" ")
    from routes.files import files_bp
    print("✓")

    print("\n✅ All imports successful!")
    print(f"\nConfig values:")
    print(f"  CORS_ORIGINS: {Config.CORS_ORIGINS}")
    print(f"  UPLOAD_FOLDER: {Config.UPLOAD_FOLDER}")
    print(f"  OUTPUT_FOLDER: {Config.OUTPUT_FOLDER}")

except Exception as e:
    print(f"\n❌ Import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

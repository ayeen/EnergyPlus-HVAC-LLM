#!/usr/bin/env python3
"""
Test script to debug pipeline execution
"""

import requests
import json
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

BASE_URL = "http://localhost:5000"

def test_upload():
    """Test file upload"""
    print("Testing file upload...")

    # Use existing uploaded file or create a simple one
    test_idf_content = """
    Version,9.5;

    Building,
        Simple Building,         !- Name
        0.0,                     !- North Axis {deg}
        Suburbs,                 !- Terrain
        0.04,                    !- Loads Convergence Tolerance Value
        0.40,                    !- Temperature Convergence Tolerance Value {deltaC}
        FullInteriorAndExterior, !- Solar Distribution
        25,                      !- Maximum Number of Warmup Days
        6;                       !- Minimum Number of Warmup Days

    Zone,
        TestZone,                !- Name
        0.0,                     !- Direction of Relative North {deg}
        0.0,                     !- X Origin {m}
        0.0,                     !- Y Origin {m}
        0.0,                     !- Z Origin {m}
        1,                       !- Type
        1,                       !- Multiplier
        autocalculate,           !- Ceiling Height {m}
        autocalculate;           !- Volume {m3}
    """

    # Save test file
    test_file_path = "/tmp/test_building.idf"
    with open(test_file_path, 'w') as f:
        f.write(test_idf_content)

    # Upload file
    with open(test_file_path, 'rb') as f:
        files = {'file': f}
        response = requests.post(f"{BASE_URL}/api/upload/idf", files=files)

    if response.status_code == 200:
        data = response.json()
        print(f"✓ Upload successful: {data['file_id']}")
        return data['file_id']
    else:
        print(f"✗ Upload failed: {response.text}")
        return None

def test_pipeline(file_id):
    """Test pipeline execution"""
    print(f"Testing pipeline execution with file_id: {file_id}")

    payload = {
        "file_id": file_id,
        "user_request": "Design a simple VRF system for testing",
        "system_name": "Test_VRF_System",
        "zones": None,
        "use_rag": False,  # Disable RAG for faster testing
        "llm_provider": "mock"  # Use mock provider for testing
    }

    response = requests.post(f"{BASE_URL}/api/pipeline/run", json=payload)

    if response.status_code == 200:
        data = response.json()
        print(f"✓ Pipeline started: {data['execution_id']}")
        return data['execution_id']
    else:
        print(f"✗ Pipeline failed: {response.text}")
        return None

def check_status(execution_id):
    """Check pipeline status"""
    print(f"Checking status for execution_id: {execution_id}")

    response = requests.get(f"{BASE_URL}/api/pipeline/status/{execution_id}")

    if response.status_code == 200:
        data = response.json()
        print(f"Status: {data['status']}")
        print(f"Progress: {data['progress']}%")
        print(f"Current step: {data['current_step']}")
        print(f"Logs: {len(data['logs'])} entries")
        return data
    else:
        print(f"✗ Status check failed: {response.text}")
        return None

if __name__ == "__main__":
    print("=== HVAC-LLM Pipeline Debug Test ===\n")

    # Test upload
    file_id = test_upload()
    if not file_id:
        sys.exit(1)

    print()

    # Test pipeline
    execution_id = test_pipeline(file_id)
    if not execution_id:
        sys.exit(1)

    print()

    # Check status
    import time
    for i in range(5):
        print(f"\n--- Status Check {i+1} ---")
        status = check_status(execution_id)
        time.sleep(2)
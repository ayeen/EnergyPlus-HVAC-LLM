#!/usr/bin/env python3
"""
Test script to verify download and preview functionality
"""

import requests
import json

BASE_URL = "http://localhost:5000"

def test_download_and_preview():
    """Test download and preview with existing file"""
    execution_id = "vrf_two_zone"  # Using existing file for testing

    # Test preview
    print("=== Testing Preview ===")
    preview_response = requests.get(f"{BASE_URL}/api/files/preview/{execution_id}?lines=10")

    if preview_response.status_code == 200:
        preview_data = preview_response.json()
        print(f"✓ Preview successful!")
        print(f"  Filename: {preview_data['filename']}")
        print(f"  Total lines: {preview_data['total_lines']}")
        print(f"  Content preview: {preview_data['content'][:100]}...")
    else:
        print(f"✗ Preview failed: {preview_response.text}")
        return False

    # Test download endpoint accessibility
    print("\n=== Testing Download ===")
    download_response = requests.head(f"{BASE_URL}/api/files/download/{execution_id}")

    if download_response.status_code == 200:
        print(f"✓ Download endpoint working!")
        print(f"  Content-Type: {download_response.headers.get('Content-Type', 'N/A')}")
        print(f"  Content-Length: {download_response.headers.get('Content-Length', 'N/A')}")
    else:
        print(f"✗ Download failed: {download_response.status_code}")
        return False

    # Test list files
    print("\n=== Testing File List ===")
    list_response = requests.get(f"{BASE_URL}/api/files/list/{execution_id}")

    if list_response.status_code == 200:
        list_data = list_response.json()
        print(f"✓ File list successful!")
        print(f"  IDF files found: {len(list_data['idfs'])}")
        print(f"  Log files found: {len(list_data['logs'])}")
        if list_data['idfs']:
            print(f"  Sample IDF: {list_data['idfs'][0]['filename']}")
    else:
        print(f"✗ File list failed: {list_response.text}")
        return False

    return True

if __name__ == "__main__":
    print("=== Download and Preview Test ===\n")

    success = test_download_and_preview()

    if success:
        print("\n🎉 All download and preview functionality working!")
        print("\nYour React frontend should now be able to:")
        print("  ✓ Preview generated IDF files")
        print("  ✓ Download generated IDF files")
        print("  ✓ List all execution files")
    else:
        print("\n❌ Some issues detected")
"""
Example 3: Config File Based Pipeline
Run HVAC generation from configuration file
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from pathlib import Path
from src.pipeline import HVACLLMPipeline

def load_config(config_path: str = '../config/hvac_requests.json'):
    """Load HVAC design requests from configuration file."""
    with open(config_path, 'r') as f:
        return json.load(f)

def run_single_request(request_id: str, config: dict):
    """Run pipeline for a single configuration request."""
    print("\n" + "=" * 70)
    print(f"Processing Request: {request_id}")
    print("=" * 70)
    print(f"User Prompt: {config['prompt']}")
    print(f"Zones: {', '.join(config['zones'])}")
    print(f"Base IDF: {config.get('base_idf', 'default')}")
    print("=" * 70)
    
    # Create pipeline
    pipeline = HVACLLMPipeline()
    
    # Run pipeline with configuration
    # NOTE: config['prompt'] is the user's natural language design request
    # The system will merge it with the technical template from energyplus_vrf_prompt.json
    result = pipeline.run(
        base_idf=config.get('base_idf', '../data/base_idfs/building_with_zones.idf'),
        zones=config['zones'],
        output_name=request_id,
        user_request=config['prompt'],  # User's natural language request
        enable_quick_validation=True  # Enable LLM validation
    )
    
    # Print results
    print("\n" + "=" * 70)
    print(f"Results for {request_id}")
    print("=" * 70)
    print(f"Success: {result['final_status']}")
    print(f"Iterations: {result['total_iterations']}")
    print(f"Final IDF: {result['final_idf']}")
    print("=" * 70)
    
    return result

def create_example_config():
    """Create example configuration file if it doesn't exist."""
    config_dir = Path('../config')
    config_dir.mkdir(exist_ok=True)
    
    example_config = {
        "vrf_single_zone": {
            "prompt": "Design a VRF HVAC system for efficient heating and cooling",
            "zones": ["ZONE ONE"],
            "base_idf": "../data/base_idfs/building_with_zones.idf"
        },
        "vrf_heat_recovery": {
            "prompt": "Design a VRF system with heat recovery for simultaneous heating and cooling in different zones",
            "zones": ["ZONE ONE"],
            "base_idf": "../data/base_idfs/building_with_zones.idf"
        },
        "vrf_multi_zone_office": {
            "prompt": "Design a VRF system to serve multiple office zones with independent temperature control",
            "zones": ["ZONE ONE"],
            "base_idf": "../data/base_idfs/building_with_zones.idf",
            "note": "For actual multi-zone, create a multi-zone base IDF first"
        },
        "vrf_high_efficiency": {
            "prompt": "Design a high-efficiency VRF system with advanced control strategies for energy savings",
            "zones": ["ZONE ONE"],
            "base_idf": "../data/base_idfs/building_with_zones.idf"
        },
        "vrf_cold_climate": {
            "prompt": "Design a VRF system optimized for cold climate operation with enhanced heating performance",
            "zones": ["ZONE ONE"],
            "base_idf": "../data/base_idfs/building_with_zones.idf"
        }
    }
    
    config_path = config_dir / 'hvac_requests.json'
    with open(config_path, 'w') as f:
        json.dump(example_config, f, indent=2)
    
    print(f"✓ Created example configuration: {config_path}")
    print("  Edit this file to add your HVAC design requests!")
    return str(config_path)

def main():
    """Run HVAC generation pipeline from configuration file."""
    
    print("=" * 70)
    print("EXAMPLE 3: Config-Based HVAC Generation")
    print("=" * 70)
    
    # Load configuration
    config_path = '../config/hvac_requests.json'
    
    try:
        requests = load_config(config_path)
        print(f"\n✓ Loaded configuration from: {config_path}")
    except FileNotFoundError:
        print(f"\n✗ Configuration file not found: {config_path}")
        print("  Creating example configuration file...")
        config_path = create_example_config()
        print(f"\n  Please edit {config_path} and run again.")
        return
    
    # Show available requests
    print("\nAvailable HVAC Design Requests:")
    print("-" * 70)
    for req_id, config in requests.items():
        print(f"  {req_id}:")
        print(f"    Prompt: {config['prompt']}")
        print(f"    Zones: {', '.join(config['zones'])}")
    print("-" * 70)
    
    # Get user selection
    print("\nOptions:")
    print("  - Enter a request ID to process that request")
    print("  - Enter 'all' to process all requests (batch mode)")
    print("  - Press Ctrl+C to exit")
    
    try:
        choice = input("\nYour choice: ").strip()
    except KeyboardInterrupt:
        print("\n\nExiting...")
        return
    
    if choice.lower() == 'all':
        # Process all requests (batch mode)
        results = {}
        print(f"\n{'=' * 70}")
        print("BATCH PROCESSING MODE: Processing all requests")
        print("=" * 70)
        
        for req_id, config in requests.items():
            try:
                results[req_id] = run_single_request(req_id, config)
            except Exception as e:
                print(f"\n✗ Error processing {req_id}: {e}")
                results[req_id] = {"final_status": "ERROR", "error": str(e)}
        
        # Summary
        print("\n\n" + "=" * 70)
        print("BATCH PROCESSING SUMMARY")
        print("=" * 70)
        for req_id, result in results.items():
            status = "✓ SUCCESS" if result.get('final_status') == 'SUCCESS' else "✗ FAILED"
            iterations = result.get('total_iterations', 'N/A')
            print(f"{req_id}: {status} ({iterations} iterations)")
        print("=" * 70)
    
    elif choice in requests:
        # Process single request
        try:
            run_single_request(choice, requests[choice])
        except Exception as e:
            print(f"\n✗ Error: {e}")
            import traceback
            traceback.print_exc()
    
    else:
        print(f"\n✗ Error: Unknown request ID '{choice}'")
        print(f"   Available IDs: {', '.join(requests.keys())}")

if __name__ == "__main__":
    main()

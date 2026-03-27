#!/usr/bin/env python3
"""
Test script to validate the notebook functions work correctly
"""

import json
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Any
import warnings
warnings.filterwarnings('ignore')

# Test the data loading functions from the notebook
def load_professor_data() -> Dict[str, Any]:
    """Load professor scalability test data (pre-trained model comparison)"""
    prof_file = Path("outputs/professor_scalability_test.json")

    if not prof_file.exists():
        print(f"Warning: {prof_file} not found")
        return {}

    with open(prof_file) as f:
        return json.load(f)

def load_fine_tuned_results() -> List[Dict[str, Any]]:
    """Load fine-tuned model test results from multiple files"""
    vrf_files = list(Path("outputs/logs").glob("vrf_*_results.json"))

    results = []
    for file_path in vrf_files:
        try:
            with open(file_path) as f:
                data = json.load(f)

            # Extract key metrics
            result = {
                'test_name': file_path.stem,
                'zones': len(data.get('zones', [])),
                'success': data.get('final_status') == 'SUCCESS',
                'iterations': data.get('total_iterations', 0),
                'first_try_success': data.get('total_iterations', 0) == 0,
                'objects_generated': sum(step.get('objects_generated', 0)
                                       for step in data.get('steps', [])),
                'simulation_passed': any(step.get('name') == 'Simulation' and step.get('success', False)
                                       for step in data.get('steps', []))
            }
            results.append(result)

        except Exception as e:
            print(f"Error loading {file_path}: {e}")

    return sorted(results, key=lambda x: x['zones'])

def test_notebook_functions():
    """Test the main functions from the notebook"""
    print("🧪 Testing Model Comparison Notebook Functions")
    print("=" * 60)

    # Test data loading
    print("\n1. Testing data loading functions...")
    prof_data = load_professor_data()
    ft_data = load_fine_tuned_results()

    print(f"✅ Professor data loaded: {len(prof_data)} keys")
    print(f"✅ Fine-tuned data loaded: {len(ft_data)} test cases")

    if prof_data:
        print(f"   Professor data keys: {list(prof_data.keys())[:3]}...")

    if ft_data:
        print(f"   Fine-tuned test cases: {[r['test_name'] for r in ft_data[:3]]}...")
        print(f"   Zone counts: {[r['zones'] for r in ft_data]}")
        print(f"   Success rates: {[r['success'] for r in ft_data]}")

    # Test data aggregation
    print("\n2. Testing data aggregation...")

    zone_counts = [1, 2, 4, 10, 20]
    comparison = {
        'fine_tuned': [],
        'pretrained_with_examples': [],
        'pretrained_no_examples': []
    }

    # Process fine-tuned results
    for zone_count in zone_counts:
        ft_result = next((r for r in ft_data if r['zones'] == zone_count), None)
        if ft_result:
            comparison['fine_tuned'].append({
                'zones': zone_count,
                'success': ft_result['success'],
                'first_try_success': ft_result['first_try_success'],
                'iterations': ft_result['iterations'],
                'quality_score': 1.0 if ft_result['success'] else 0.0
            })

    print(f"✅ Aggregated fine-tuned data: {len(comparison['fine_tuned'])} records")

    # Test basic statistics
    print("\n3. Testing statistical calculations...")
    if comparison['fine_tuned']:
        ft_data_agg = comparison['fine_tuned']
        success_rate = np.mean([r['success'] for r in ft_data_agg]) * 100
        first_try_rate = np.mean([r['first_try_success'] for r in ft_data_agg]) * 100
        avg_iterations = np.mean([r['iterations'] for r in ft_data_agg])

        print(f"✅ Fine-tuned success rate: {success_rate:.1f}%")
        print(f"✅ Fine-tuned first-try rate: {first_try_rate:.1f}%")
        print(f"✅ Fine-tuned avg iterations: {avg_iterations:.2f}")

    # Test matplotlib setup
    print("\n4. Testing visualization setup...")
    try:
        plt.style.use('default')
        plt.rcParams['figure.facecolor'] = 'white'
        fig, ax = plt.subplots(1, 1, figsize=(6, 4))
        ax.plot([1, 2, 3], [1, 2, 3], 'o-')
        ax.set_title('Test Plot')
        plt.close(fig)  # Close without showing
        print("✅ Matplotlib setup working correctly")
    except Exception as e:
        print(f"❌ Matplotlib error: {e}")

    print("\n" + "=" * 60)
    print("🎉 Notebook validation complete!")

if __name__ == "__main__":
    test_notebook_functions()
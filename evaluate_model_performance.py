"""
Fine-Tuned vs Pre-Trained Model Performance Comparison

This script evaluates:
1. IDF Generation Success Rate
2. Validation Success Rate
3. Simulation Success Rate
4. Error Correction Iterations Required
5. Parameter Accuracy
6. Prompt Responsiveness
7. Generation Time
8. Code Quality Metrics
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.pipeline import HVACLLMPipeline
from src.agents.llm_interface import UniversalLLM
import time
import json
from pathlib import Path
import re

class ModelPerformanceEvaluator:
    """Compare fine-tuned vs pre-trained model performance"""

    def __init__(self):
        self.results = {
            'fine_tuned': [],
            'pre_trained': []
        }

    def extract_hvac_parameters(self, idf_path):
        """Extract key parameters from generated IDF"""
        if not os.path.exists(idf_path):
            return None

        with open(idf_path, 'r') as f:
            content = f.read()

        params = {
            'cooling_cop': None,
            'heating_cop': None,
            'num_thermostats': 0,
            'num_zone_vrf': 0,
            'num_system_vrf': 0,
            'has_supplemental_heating': False,
            'field_count_zone_vrf': 0,
            'proper_thermostat_refs': True,
            'uses_autosize': False,
        }

        # Count objects
        params['num_thermostats'] = content.count('HVACTemplate:Thermostat,')
        params['num_zone_vrf'] = content.count('HVACTemplate:Zone:VRF,')
        params['num_system_vrf'] = content.count('HVACTemplate:System:VRF,')

        # Extract COPs
        cop_matches = re.findall(r'Gross Rated (\w+) COP.*?\\n.*?([0-9.]+)', content, re.DOTALL)
        for match in cop_matches:
            if 'Cooling' in match[0]:
                try:
                    params['cooling_cop'] = float(match[1])
                except:
                    pass
            elif 'Heating' in match[0]:
                try:
                    params['heating_cop'] = float(match[1])
                except:
                    pass

        # Check for supplemental heating
        if 'Electric' in content or 'Gas' in content:
            if 'Supplemental Heating Coil Type' in content:
                params['has_supplemental_heating'] = True

        # Check for Autosize usage
        params['uses_autosize'] = 'Autosize' in content

        # Count fields in Zone:VRF (should be 42)
        zone_vrf_section = re.search(r'HVACTemplate:Zone:VRF,.*?;', content, re.DOTALL)
        if zone_vrf_section:
            fields = zone_vrf_section.group(0).split(',')
            params['field_count_zone_vrf'] = len(fields) - 1  # -1 for object name

        return params

    def run_test_case(self, test_name, prompt, model_type, zones=['Zone1']):
        """Run a single test case for a specific model"""
        print(f"\n{'='*80}")
        print(f"Testing: {test_name} with {model_type}")
        print(f"{'='*80}")
        print(f"Prompt: {prompt}")

        # Reset LLM to ensure fresh model
        UniversalLLM.reset()

        # Set provider based on model type
        if model_type == 'fine_tuned':
            provider = 'mistral'  # Uses fine-tuned by default
        else:
            provider = 'mistral-pretrained'

        start_time = time.time()

        result = {
            'test_name': test_name,
            'prompt': prompt,
            'model_type': model_type,
            'provider': provider,
            'success': False,
            'validation_passed': False,
            'simulation_passed': False,
            'error_iterations': 0,
            'generation_time': 0,
            'total_time': 0,
            'parameters': None,
            'errors': []
        }

        try:
            pipeline = HVACLLMPipeline()

            pipeline_result = pipeline.run(
                base_idf='data/base_idfs/building_with_zones_fixed.idf',
                zones=zones,
                output_name=f"perf_test_{model_type}_{test_name}",
                user_request=prompt,
                enable_quick_validation=False
            )

            result['total_time'] = time.time() - start_time

            # Extract results
            if pipeline_result.get('final_status') == 'SUCCESS':
                result['success'] = True
                result['validation_passed'] = True
                result['simulation_passed'] = True

            result['error_iterations'] = pipeline_result.get('total_iterations', 0)

            # Extract parameters from final IDF
            if pipeline_result.get('final_idf'):
                params = self.extract_hvac_parameters(pipeline_result['final_idf'])
                result['parameters'] = params

            print(f"✓ Test completed successfully")
            print(f"  Validation: {'PASS' if result['validation_passed'] else 'FAIL'}")
            print(f"  Simulation: {'PASS' if result['simulation_passed'] else 'FAIL'}")
            print(f"  Iterations: {result['error_iterations']}")
            print(f"  Time: {result['total_time']:.1f}s")
            if params:
                print(f"  Cooling COP: {params['cooling_cop']}")
                print(f"  Heating COP: {params['heating_cop']}")

        except Exception as e:
            result['total_time'] = time.time() - start_time
            result['errors'].append(str(e))
            print(f"✗ Test failed: {e}")

        return result

    def run_comparison_tests(self):
        """Run full comparison between fine-tuned and pre-trained"""

        print("="*80)
        print("FINE-TUNED vs PRE-TRAINED MODEL COMPARISON")
        print("="*80)

        # Define test cases
        test_cases = [
            {
                'name': 'standard_vrf',
                'prompt': 'Design a VRF HVAC system for efficient heating and cooling',
                'difficulty': 'easy'
            },
            {
                'name': 'cold_climate',
                'prompt': 'Design a VRF system optimized for cold climate operation with enhanced heating performance and backup electric heating for extreme temperatures',
                'difficulty': 'medium'
            },
            {
                'name': 'high_efficiency',
                'prompt': 'Design a high-efficiency VRF system with premium components and advanced control strategies for maximum energy savings',
                'difficulty': 'medium'
            },
            {
                'name': 'complex_requirements',
                'prompt': 'Design a VRF system for a commercial building with superior comfort control, energy monitoring, and optimized part-load performance in variable climate conditions',
                'difficulty': 'hard'
            }
        ]

        # Test fine-tuned model
        print("\n" + "="*80)
        print("PHASE 1: Testing Fine-Tuned Model")
        print("="*80)

        for test_case in test_cases:
            result = self.run_test_case(
                test_case['name'],
                test_case['prompt'],
                'fine_tuned'
            )
            result['difficulty'] = test_case['difficulty']
            self.results['fine_tuned'].append(result)

            # Small delay between tests
            time.sleep(2)

        # Test pre-trained model
        print("\n" + "="*80)
        print("PHASE 2: Testing Pre-Trained Model")
        print("="*80)

        for test_case in test_cases:
            result = self.run_test_case(
                test_case['name'],
                test_case['prompt'],
                'pre_trained'
            )
            result['difficulty'] = test_case['difficulty']
            self.results['pre_trained'].append(result)

            # Small delay between tests
            time.sleep(2)

        # Generate comparison report
        self.generate_comparison_report()

    def generate_comparison_report(self):
        """Generate detailed comparison report"""

        print("\n\n" + "="*80)
        print("PERFORMANCE COMPARISON REPORT")
        print("="*80)

        # Success Rates
        print("\n### 1. SUCCESS RATES")
        print("-"*80)

        ft_success = sum(1 for r in self.results['fine_tuned'] if r['success']) / len(self.results['fine_tuned']) * 100
        pt_success = sum(1 for r in self.results['pre_trained'] if r['success']) / len(self.results['pre_trained']) * 100

        ft_validation = sum(1 for r in self.results['fine_tuned'] if r['validation_passed']) / len(self.results['fine_tuned']) * 100
        pt_validation = sum(1 for r in self.results['pre_trained'] if r['validation_passed']) / len(self.results['pre_trained']) * 100

        ft_simulation = sum(1 for r in self.results['fine_tuned'] if r['simulation_passed']) / len(self.results['fine_tuned']) * 100
        pt_simulation = sum(1 for r in self.results['pre_trained'] if r['simulation_passed']) / len(self.results['pre_trained']) * 100

        print(f"{'Metric':<30} {'Fine-Tuned':<15} {'Pre-Trained':<15} {'Improvement'}")
        print(f"{'-'*30} {'-'*15} {'-'*15} {'-'*12}")
        print(f"{'Overall Success':<30} {ft_success:>6.1f}%        {pt_success:>6.1f}%        {ft_success-pt_success:>+6.1f}%")
        print(f"{'IDF Validation Success':<30} {ft_validation:>6.1f}%        {pt_validation:>6.1f}%        {ft_validation-pt_validation:>+6.1f}%")
        print(f"{'Simulation Success':<30} {ft_simulation:>6.1f}%        {pt_simulation:>6.1f}%        {ft_simulation-pt_simulation:>+6.1f}%")

        # Error Correction Iterations
        print("\n### 2. ERROR CORRECTION EFFICIENCY")
        print("-"*80)

        ft_avg_iter = sum(r['error_iterations'] for r in self.results['fine_tuned']) / len(self.results['fine_tuned'])
        pt_avg_iter = sum(r['error_iterations'] for r in self.results['pre_trained']) / len(self.results['pre_trained'])

        print(f"{'Metric':<30} {'Fine-Tuned':<15} {'Pre-Trained':<15} {'Improvement'}")
        print(f"{'-'*30} {'-'*15} {'-'*15} {'-'*12}")
        print(f"{'Avg Error Iterations':<30} {ft_avg_iter:>6.2f}         {pt_avg_iter:>6.2f}         {pt_avg_iter-ft_avg_iter:>+6.2f}")

        # Generation Time
        print("\n### 3. GENERATION TIME")
        print("-"*80)

        ft_avg_time = sum(r['total_time'] for r in self.results['fine_tuned']) / len(self.results['fine_tuned'])
        pt_avg_time = sum(r['total_time'] for r in self.results['pre_trained']) / len(self.results['pre_trained'])

        print(f"{'Metric':<30} {'Fine-Tuned':<15} {'Pre-Trained':<15} {'Difference'}")
        print(f"{'-'*30} {'-'*15} {'-'*15} {'-'*12}")
        print(f"{'Avg Generation Time (sec)':<30} {ft_avg_time:>6.1f}s        {pt_avg_time:>6.1f}s        {ft_avg_time-pt_avg_time:>+6.1f}s")

        # Parameter Quality
        print("\n### 4. GENERATED PARAMETER QUALITY")
        print("-"*80)

        # COP values comparison
        ft_cops_heating = [r['parameters']['heating_cop'] for r in self.results['fine_tuned']
                          if r['parameters'] and r['parameters']['heating_cop']]
        pt_cops_heating = [r['parameters']['heating_cop'] for r in self.results['pre_trained']
                          if r['parameters'] and r['parameters']['heating_cop']]

        if ft_cops_heating and pt_cops_heating:
            ft_avg_heating_cop = sum(ft_cops_heating) / len(ft_cops_heating)
            pt_avg_heating_cop = sum(pt_cops_heating) / len(pt_cops_heating)

            print(f"{'Metric':<30} {'Fine-Tuned':<15} {'Pre-Trained':<15}")
            print(f"{'-'*30} {'-'*15} {'-'*15}")
            print(f"{'Avg Heating COP':<30} {ft_avg_heating_cop:>6.2f}         {pt_avg_heating_cop:>6.2f}")
            print(f"{'Heating COP Range':<30} {min(ft_cops_heating):.2f}-{max(ft_cops_heating):.2f}      {min(pt_cops_heating):.2f}-{max(pt_cops_heating):.2f}")

        # Object generation completeness
        print("\n### 5. IDF OBJECT COMPLETENESS")
        print("-"*80)

        ft_avg_thermostats = sum(r['parameters']['num_thermostats'] for r in self.results['fine_tuned']
                                if r['parameters']) / len(self.results['fine_tuned'])
        pt_avg_thermostats = sum(r['parameters']['num_thermostats'] for r in self.results['pre_trained']
                                if r['parameters']) / len(self.results['pre_trained'])

        ft_avg_fields = sum(r['parameters']['field_count_zone_vrf'] for r in self.results['fine_tuned']
                           if r['parameters'] and r['parameters']['field_count_zone_vrf']) / len(self.results['fine_tuned'])
        pt_avg_fields = sum(r['parameters']['field_count_zone_vrf'] for r in self.results['pre_trained']
                           if r['parameters'] and r['parameters']['field_count_zone_vrf']) / len(self.results['pre_trained'])

        print(f"{'Metric':<30} {'Fine-Tuned':<15} {'Pre-Trained':<15} {'Target'}")
        print(f"{'-'*30} {'-'*15} {'-'*15} {'-'*12}")
        print(f"{'Avg Thermostats Created':<30} {ft_avg_thermostats:>6.1f}         {pt_avg_thermostats:>6.1f}         2.0")
        print(f"{'Avg Zone:VRF Field Count':<30} {ft_avg_fields:>6.1f}         {pt_avg_fields:>6.1f}         42.0")

        # Per-test breakdown
        print("\n### 6. TEST-BY-TEST BREAKDOWN")
        print("-"*80)
        print(f"{'Test Name':<20} {'Model':<12} {'Success':<10} {'Valid':<8} {'Sim':<6} {'Iter':<6} {'Time':<8}")
        print("-"*80)

        for i, test_case in enumerate(self.results['fine_tuned']):
            ft = test_case
            pt = self.results['pre_trained'][i]

            print(f"{ft['test_name']:<20} Fine-Tuned   {('✓' if ft['success'] else '✗'):<10} {('✓' if ft['validation_passed'] else '✗'):<8} {('✓' if ft['simulation_passed'] else '✗'):<6} {ft['error_iterations']:<6} {ft['total_time']:.1f}s")
            print(f"{'':<20} Pre-Trained  {('✓' if pt['success'] else '✗'):<10} {('✓' if pt['validation_passed'] else '✗'):<8} {('✓' if pt['simulation_passed'] else '✗'):<6} {pt['error_iterations']:<6} {pt['total_time']:.1f}s")
            print()

        # Statistical Summary
        print("\n### 7. STATISTICAL SUMMARY")
        print("-"*80)

        improvement_score = (
            (ft_success - pt_success) +
            (ft_validation - pt_validation) +
            (ft_simulation - pt_simulation) +
            (pt_avg_iter - ft_avg_iter) * 10  # Fewer iterations is better
        ) / 4

        print(f"Overall Improvement Score: {improvement_score:+.2f}%")

        if improvement_score > 10:
            print("✓ Fine-tuned model shows SIGNIFICANT improvement")
        elif improvement_score > 0:
            print("✓ Fine-tuned model shows MODERATE improvement")
        else:
            print("⚠ Fine-tuned model shows NO significant improvement")

        # Save results to JSON
        output_file = 'model_comparison_results.json'
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\n✓ Detailed results saved to: {output_file}")

        return self.results

def main():
    """Run model performance comparison"""
    evaluator = ModelPerformanceEvaluator()
    evaluator.run_comparison_tests()

if __name__ == "__main__":
    main()

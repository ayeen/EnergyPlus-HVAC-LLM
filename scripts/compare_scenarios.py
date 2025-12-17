#!/usr/bin/env python3
"""
Scenario Comparison Script for HVAC-LLM Research
================================================

This script compares two scenarios:
- Scenario 1: Single LLM (Gemini WITHOUT RAG) - Base LLM only
- Scenario 2: Pre-trained LLM + RAG (Fine-tuned Mistral WITH RAG) - Enhanced system

Metrics Measured:
- Generation success rate
- IDF validation pass rate
- Simulation success rate
- Number of correction iterations needed
- Generation time
- Token usage (if available)

Usage:
    python scripts/compare_scenarios.py [--runs N] [--output results.json]
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.pipeline import HVACLLMPipeline
from src.agents.llm_interface import UniversalLLM
from src.core.idf_handler import IDFHandler
from config import Config


@dataclass
class TestResult:
    """Results from a single test run"""
    scenario: str
    test_case: str
    prompt: str
    zones: List[str]
    llm_provider: str  # Added to track which LLM was used
    
    # Success metrics
    generation_success: bool
    validation_success: bool
    simulation_success: bool
    
    # Performance metrics
    generation_time_seconds: float
    total_time_seconds: float
    correction_iterations: int
    
    # Quality metrics
    hvac_objects_generated: int
    errors_encountered: List[str]
    warnings_encountered: List[str]
    
    # IDD compliance
    idd_issues_found: int
    idd_issues_auto_fixed: int
    
    # Output files
    output_idf_path: Optional[str]
    
    # Timestamp
    timestamp: str


@dataclass
class ScenarioComparison:
    """Comparison results between scenarios"""
    scenario_1_results: List[TestResult]
    scenario_2_results: List[TestResult]
    
    # Aggregate metrics
    scenario_1_success_rate: float
    scenario_2_success_rate: float
    
    scenario_1_avg_time: float
    scenario_2_avg_time: float
    
    scenario_1_avg_iterations: float
    scenario_2_avg_iterations: float
    
    # Improvement metrics
    success_rate_improvement: float
    time_improvement_percent: float
    iteration_reduction: float


class ScenarioComparator:
    """
    Compare Scenario 1 (LLM only) vs Scenario 2 (LLM + RAG)
    """
    
    def __init__(self, output_dir: str = "outputs/scenario_comparison"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.idf_handler = IDFHandler()
        
        # Test cases for comparison
        self.test_cases = self._get_test_cases()
        
    def _get_test_cases(self) -> List[Dict[str, Any]]:
        """Define test cases for comparison"""
        return [
            {
                "name": "single_zone_office",
                "prompt": "Design a VRF HVAC system for efficient heating and cooling",
                "zones": ["Zone1"],
                "base_idf": "data/base_idfs/building_with_zones_fixed.idf"
            },
            {
                "name": "two_zone_building",
                "prompt": "Design a VRF HVAC system for efficient heating and cooling for a two-zone building",
                "zones": ["Zone1", "Zone2"],
                "base_idf": "data/base_idfs/building_with_zones_fixed.idf"
            },
            {
                "name": "multi_zone_office",
                "prompt": "Design a VRF system to serve multiple office zones with independent temperature control",
                "zones": ["ZONE 1", "ZONE 2", "ZONE 3", "ZONE 4"],
                "base_idf": "data/base_idfs/4ZoneWithShading_Simple_2_NoHVAC.idf"
            },
            {
                "name": "residential_home",
                "prompt": "Design VRF for residential home with 3 bedrooms and living areas",
                "zones": None,  # Auto-detect
                "base_idf": "data/base_idfs/residential_5zone.idf"
            },
            {
                "name": "retail_store",
                "prompt": "Design VRF for retail store with sales floor and storage",
                "zones": None,  # Auto-detect
                "base_idf": "data/base_idfs/retail_3zone.idf"
            },
            {
                "name": "large_office",
                "prompt": "Design VRF for a large office building with 10 zones",
                "zones": None,  # Auto-detect
                "base_idf": "data/base_idfs/large_office_10zone.idf"
            },
        ]
    
    def run_scenario_1(self, test_case: Dict[str, Any], run_id: int) -> TestResult:
        """
        Run Scenario 1: Single LLM (Gemini) WITHOUT RAG
        
        This tests the base Gemini model without RAG enhancement.
        This represents the simplest baseline: a general-purpose LLM.
        """
        print(f"\n{'='*70}")
        print(f"SCENARIO 1: GEMINI (Single LLM, No RAG)")
        print(f"Test Case: {test_case['name']} (Run {run_id})")
        print(f"{'='*70}")
        
        start_time = time.time()
        generation_start = time.time()
        
        errors = []
        warnings = []
        llm_provider = "gemini"
        
        try:
            # Reset LLM singleton to switch provider
            UniversalLLM.reset()
            
            # Initialize pipeline with Gemini, WITHOUT RAG (Scenario 1)
            pipeline = HVACLLMPipeline(
                use_rag=False,           # <-- KEY: No RAG
                llm_provider="gemini"    # <-- KEY: Use Gemini
            )
            
            generation_time = time.time() - generation_start
            
            # Run pipeline
            result = pipeline.run(
                base_idf=test_case['base_idf'],
                user_request=test_case['prompt'],
                zones=test_case['zones'],
                output_name=f"scenario1_{test_case['name']}_run{run_id}"
            )
            
            total_time = time.time() - start_time
            
            # Extract metrics from result dict
            final_status = result.get('final_status', 'UNKNOWN')
            generation_success = final_status != 'FAILED'
            validation_success = result.get('validation_passed', False) 
            simulation_success = final_status == 'SUCCESS'
            iterations = result.get('iterations', 0)
            hvac_objects = result.get('hvac_objects_count', 0)
            output_path = result.get('final_idf_path', None)
            
            errors = result.get('errors', [])
            warnings = result.get('warnings', [])
            
            # Get IDD compliance info
            idd_issues = result.get('idd_issues_found', 0)
            idd_fixed = result.get('idd_issues_fixed', 0)
            
            print(f"\n✓ Scenario 1 Complete (Gemini)")
            print(f"  Generation: {'✓' if generation_success else '✗'}")
            print(f"  Validation: {'✓' if validation_success else '✗'}")
            print(f"  Simulation: {'✓' if simulation_success else '✗'}")
            print(f"  Time: {total_time:.2f}s")
            
        except Exception as e:
            total_time = time.time() - start_time
            generation_time = time.time() - generation_start
            errors.append(str(e))
            print(f"\n✗ Scenario 1 Failed: {e}")
            
            return TestResult(
                scenario="Scenario 1: Gemini (Single LLM, No RAG)",
                test_case=test_case['name'],
                prompt=test_case['prompt'],
                zones=test_case.get('zones', []),
                llm_provider=llm_provider,
                generation_success=False,
                validation_success=False,
                simulation_success=False,
                generation_time_seconds=generation_time,
                total_time_seconds=total_time,
                correction_iterations=0,
                hvac_objects_generated=0,
                errors_encountered=errors,
                warnings_encountered=warnings,
                idd_issues_found=0,
                idd_issues_auto_fixed=0,
                output_idf_path=None,
                timestamp=datetime.now().isoformat()
            )
        
        return TestResult(
            scenario="Scenario 1: Gemini Only (No RAG)",
            test_case=test_case['name'],
            prompt=test_case['prompt'],
            zones=test_case.get('zones', []) or result.get('detected_zones', []),
            llm_provider="gemini",
            generation_success=generation_success,
            validation_success=validation_success,
            simulation_success=simulation_success,
            generation_time_seconds=generation_time,
            total_time_seconds=total_time,
            correction_iterations=iterations,
            hvac_objects_generated=hvac_objects,
            errors_encountered=errors,
            warnings_encountered=warnings,
            idd_issues_found=idd_issues,
            idd_issues_auto_fixed=idd_fixed,
            output_idf_path=output_path,
            timestamp=datetime.now().isoformat()
        )
    
    def run_scenario_2(self, test_case: Dict[str, Any], run_id: int) -> TestResult:
        """
        Run Scenario 2: Pre-trained Mistral LLM WITH RAG
        
        This tests the fine-tuned Mistral model WITH RAG enhancement.
        Uses llm_provider="mistral" with use_rag=True
        """
        print(f"\n{'='*70}")
        print(f"SCENARIO 2: Pre-trained Mistral LLM + RAG")
        print(f"Test Case: {test_case['name']} (Run {run_id})")
        print(f"{'='*70}")
        
        start_time = time.time()
        generation_start = time.time()
        
        errors = []
        warnings = []
        
        try:
            # Reset UniversalLLM singleton to allow different provider
            from src.agents.llm_interface import UniversalLLM
            UniversalLLM.reset()  # Reset to allow different provider
            
            # Initialize pipeline WITH RAG and Mistral (Scenario 2)
            # KEY: use_rag=True, llm_provider="mistral" for pre-trained LLM + RAG
            pipeline = HVACLLMPipeline(use_rag=True, llm_provider="mistral")
            
            generation_time = time.time() - generation_start
            
            # Run pipeline
            result = pipeline.run(
                base_idf=test_case['base_idf'],
                user_request=test_case['prompt'],
                zones=test_case['zones'],
                output_name=f"scenario2_{test_case['name']}_run{run_id}"
            )
            
            total_time = time.time() - start_time
            
            # Extract metrics from result dict
            final_status = result.get('final_status', 'UNKNOWN')
            generation_success = final_status != 'FAILED'
            validation_success = result.get('validation_passed', False)
            simulation_success = final_status == 'SUCCESS'
            iterations = result.get('iterations', 0)
            hvac_objects = result.get('hvac_objects_count', 0)
            output_path = result.get('final_idf_path', None)
            
            errors = result.get('errors', [])
            warnings = result.get('warnings', [])
            
            # Get IDD compliance info
            idd_issues = result.get('idd_issues_found', 0)
            idd_fixed = result.get('idd_issues_fixed', 0)
            
            print(f"\n✓ Scenario 2 Complete")
            print(f"  Generation: {'✓' if generation_success else '✗'}")
            print(f"  Validation: {'✓' if validation_success else '✗'}")
            print(f"  Simulation: {'✓' if simulation_success else '✗'}")
            print(f"  Time: {total_time:.2f}s")
            
        except Exception as e:
            total_time = time.time() - start_time
            generation_time = time.time() - generation_start
            errors.append(str(e))
            print(f"\n✗ Scenario 2 Failed: {e}")
            
            return TestResult(
                scenario="Scenario 2: Mistral + RAG",
                test_case=test_case['name'],
                prompt=test_case['prompt'],
                zones=test_case.get('zones', []),
                llm_provider="mistral",
                generation_success=False,
                validation_success=False,
                simulation_success=False,
                generation_time_seconds=generation_time,
                total_time_seconds=total_time,
                correction_iterations=0,
                hvac_objects_generated=0,
                errors_encountered=errors,
                warnings_encountered=warnings,
                idd_issues_found=0,
                idd_issues_auto_fixed=0,
                output_idf_path=None,
                timestamp=datetime.now().isoformat()
            )
        
        return TestResult(
            scenario="Scenario 2: Mistral + RAG",
            test_case=test_case['name'],
            prompt=test_case['prompt'],
            zones=test_case.get('zones', []) or result.get('detected_zones', []),
            llm_provider="mistral",
            generation_success=generation_success,
            validation_success=validation_success,
            simulation_success=simulation_success,
            generation_time_seconds=generation_time,
            total_time_seconds=total_time,
            correction_iterations=iterations,
            hvac_objects_generated=hvac_objects,
            errors_encountered=errors,
            warnings_encountered=warnings,
            idd_issues_found=idd_issues,
            idd_issues_auto_fixed=idd_fixed,
            output_idf_path=output_path,
            timestamp=datetime.now().isoformat()
        )
    
    def run_comparison(self, num_runs: int = 1, test_cases: Optional[List[str]] = None) -> ScenarioComparison:
        """
        Run full comparison between Scenario 1 and Scenario 2
        
        Args:
            num_runs: Number of runs per test case (for statistical significance)
            test_cases: Optional list of test case names to run (default: all)
        """
        print("\n" + "="*70)
        print("SCENARIO COMPARISON: LLM Only vs LLM + RAG")
        print("="*70)
        print(f"Number of runs per test case: {num_runs}")
        print(f"Total test cases: {len(self.test_cases)}")
        print("="*70)
        
        scenario_1_results: List[TestResult] = []
        scenario_2_results: List[TestResult] = []
        
        # Filter test cases if specified
        cases_to_run = self.test_cases
        if test_cases:
            cases_to_run = [tc for tc in self.test_cases if tc['name'] in test_cases]
        
        for test_case in cases_to_run:
            print(f"\n{'#'*70}")
            print(f"# TEST CASE: {test_case['name']}")
            print(f"# Prompt: {test_case['prompt'][:60]}...")
            print(f"{'#'*70}")
            
            for run_id in range(1, num_runs + 1):
                # Run Scenario 1 (No RAG)
                result_1 = self.run_scenario_1(test_case, run_id)
                scenario_1_results.append(result_1)
                
                # Run Scenario 2 (With RAG)
                result_2 = self.run_scenario_2(test_case, run_id)
                scenario_2_results.append(result_2)
        
        # Calculate aggregate metrics
        comparison = self._calculate_comparison(scenario_1_results, scenario_2_results)
        
        # Save results
        self._save_results(comparison)
        
        # Print summary
        self._print_summary(comparison)
        
        return comparison
    
    def _calculate_comparison(
        self, 
        scenario_1_results: List[TestResult], 
        scenario_2_results: List[TestResult]
    ) -> ScenarioComparison:
        """Calculate aggregate comparison metrics"""
        
        # Scenario 1 metrics
        s1_successes = sum(1 for r in scenario_1_results if r.simulation_success)
        s1_success_rate = s1_successes / len(scenario_1_results) if scenario_1_results else 0
        s1_avg_time = sum(r.total_time_seconds for r in scenario_1_results) / len(scenario_1_results) if scenario_1_results else 0
        s1_avg_iterations = sum(r.correction_iterations for r in scenario_1_results) / len(scenario_1_results) if scenario_1_results else 0
        
        # Scenario 2 metrics
        s2_successes = sum(1 for r in scenario_2_results if r.simulation_success)
        s2_success_rate = s2_successes / len(scenario_2_results) if scenario_2_results else 0
        s2_avg_time = sum(r.total_time_seconds for r in scenario_2_results) / len(scenario_2_results) if scenario_2_results else 0
        s2_avg_iterations = sum(r.correction_iterations for r in scenario_2_results) / len(scenario_2_results) if scenario_2_results else 0
        
        # Improvement metrics
        success_improvement = (s2_success_rate - s1_success_rate) * 100
        time_improvement = ((s1_avg_time - s2_avg_time) / s1_avg_time * 100) if s1_avg_time > 0 else 0
        iteration_reduction = s1_avg_iterations - s2_avg_iterations
        
        return ScenarioComparison(
            scenario_1_results=scenario_1_results,
            scenario_2_results=scenario_2_results,
            scenario_1_success_rate=s1_success_rate,
            scenario_2_success_rate=s2_success_rate,
            scenario_1_avg_time=s1_avg_time,
            scenario_2_avg_time=s2_avg_time,
            scenario_1_avg_iterations=s1_avg_iterations,
            scenario_2_avg_iterations=s2_avg_iterations,
            success_rate_improvement=success_improvement,
            time_improvement_percent=time_improvement,
            iteration_reduction=iteration_reduction
        )
    
    def _save_results(self, comparison: ScenarioComparison):
        """Save comparison results to JSON"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Convert to serializable format
        results = {
            "comparison_timestamp": timestamp,
            "scenario_1": {
                "name": "Scenario 1: Gemini Only (No RAG)",
                "description": "Gemini API without fine-tuning or Retrieval-Augmented Generation",
                "success_rate": comparison.scenario_1_success_rate,
                "avg_time_seconds": comparison.scenario_1_avg_time,
                "avg_correction_iterations": comparison.scenario_1_avg_iterations,
                "total_runs": len(comparison.scenario_1_results),
                "results": [asdict(r) for r in comparison.scenario_1_results]
            },
            "scenario_2": {
                "name": "Scenario 2: Mistral + RAG",
                "description": "Fine-tuned Mistral 7B with Retrieval-Augmented Generation",
                "success_rate": comparison.scenario_2_success_rate,
                "avg_time_seconds": comparison.scenario_2_avg_time,
                "avg_correction_iterations": comparison.scenario_2_avg_iterations,
                "total_runs": len(comparison.scenario_2_results),
                "results": [asdict(r) for r in comparison.scenario_2_results]
            },
            "comparison": {
                "success_rate_improvement_percent": comparison.success_rate_improvement,
                "time_improvement_percent": comparison.time_improvement_percent,
                "iteration_reduction": comparison.iteration_reduction,
                "rag_benefit": "positive" if comparison.success_rate_improvement > 0 else "negative" if comparison.success_rate_improvement < 0 else "neutral"
            }
        }
        
        output_file = self.output_dir / f"scenario_comparison_{timestamp}.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n✓ Results saved to: {output_file}")
        
        # Also save a summary CSV for easy analysis
        self._save_csv_summary(comparison, timestamp)
    
    def _save_csv_summary(self, comparison: ScenarioComparison, timestamp: str):
        """Save a CSV summary for easy analysis"""
        import csv
        
        csv_file = self.output_dir / f"scenario_comparison_{timestamp}.csv"
        
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow([
                "Scenario", "Test Case", "Run", "Prompt",
                "Generation Success", "Validation Success", "Simulation Success",
                "Time (s)", "Iterations", "HVAC Objects", "Errors"
            ])
            
            # Scenario 1 results
            for i, r in enumerate(comparison.scenario_1_results, 1):
                writer.writerow([
                    "Scenario 1 (No RAG)",
                    r.test_case,
                    i,
                    r.prompt[:50] + "...",
                    r.generation_success,
                    r.validation_success,
                    r.simulation_success,
                    f"{r.total_time_seconds:.2f}",
                    r.correction_iterations,
                    r.hvac_objects_generated,
                    len(r.errors_encountered)
                ])
            
            # Scenario 2 results
            for i, r in enumerate(comparison.scenario_2_results, 1):
                writer.writerow([
                    "Scenario 2 (With RAG)",
                    r.test_case,
                    i,
                    r.prompt[:50] + "...",
                    r.generation_success,
                    r.validation_success,
                    r.simulation_success,
                    f"{r.total_time_seconds:.2f}",
                    r.correction_iterations,
                    r.hvac_objects_generated,
                    len(r.errors_encountered)
                ])
        
        print(f"✓ CSV summary saved to: {csv_file}")
    
    def _print_summary(self, comparison: ScenarioComparison):
        """Print comparison summary"""
        print("\n" + "="*70)
        print("COMPARISON SUMMARY")
        print("="*70)
        
        print("\n┌" + "─"*68 + "┐")
        print(f"│{'METRIC':<30}│{'SCENARIO 1':>18}│{'SCENARIO 2':>18}│")
        print(f"│{'':30}│{'(No RAG)':>18}│{'(With RAG)':>18}│")
        print("├" + "─"*30 + "┼" + "─"*18 + "┼" + "─"*18 + "┤")
        
        print(f"│{'Success Rate':<30}│{comparison.scenario_1_success_rate*100:>17.1f}%│{comparison.scenario_2_success_rate*100:>17.1f}%│")
        print(f"│{'Avg Time (seconds)':<30}│{comparison.scenario_1_avg_time:>18.2f}│{comparison.scenario_2_avg_time:>18.2f}│")
        print(f"│{'Avg Correction Iterations':<30}│{comparison.scenario_1_avg_iterations:>18.2f}│{comparison.scenario_2_avg_iterations:>18.2f}│")
        print(f"│{'Total Runs':<30}│{len(comparison.scenario_1_results):>18}│{len(comparison.scenario_2_results):>18}│")
        
        print("└" + "─"*30 + "┴" + "─"*18 + "┴" + "─"*18 + "┘")
        
        # RAG Impact Analysis
        print("\n┌" + "─"*68 + "┐")
        print(f"│{'RAG IMPACT ANALYSIS':<68}│")
        print("├" + "─"*68 + "┤")
        
        if comparison.success_rate_improvement > 0:
            impact = "✅ POSITIVE"
        elif comparison.success_rate_improvement < 0:
            impact = "❌ NEGATIVE"
        else:
            impact = "➖ NEUTRAL"
        
        print(f"│  Overall Impact: {impact:<49}│")
        print(f"│  Success Rate Improvement: {comparison.success_rate_improvement:>+.1f}%{'':<29}│")
        print(f"│  Time Improvement: {comparison.time_improvement_percent:>+.1f}%{'':<37}│")
        print(f"│  Iteration Reduction: {comparison.iteration_reduction:>+.2f}{'':<35}│")
        print("└" + "─"*68 + "┘")
        
        # Detailed breakdown by test case
        print("\n┌" + "─"*68 + "┐")
        print(f"│{'DETAILED RESULTS BY TEST CASE':<68}│")
        print("├" + "─"*68 + "┤")
        
        # Group by test case
        test_cases = set(r.test_case for r in comparison.scenario_1_results)
        
        for tc in test_cases:
            s1_tc = [r for r in comparison.scenario_1_results if r.test_case == tc]
            s2_tc = [r for r in comparison.scenario_2_results if r.test_case == tc]
            
            s1_success = sum(1 for r in s1_tc if r.simulation_success)
            s2_success = sum(1 for r in s2_tc if r.simulation_success)
            
            s1_icon = "✓" if s1_success > 0 else "✗"
            s2_icon = "✓" if s2_success > 0 else "✗"
            
            print(f"│  {tc:<30} S1:{s1_icon} ({s1_success}/{len(s1_tc)})  S2:{s2_icon} ({s2_success}/{len(s2_tc)}){'':<10}│")
        
        print("└" + "─"*68 + "┘")
        
        print("\n" + "="*70)
        print("CONCLUSION")
        print("="*70)
        
        if comparison.success_rate_improvement > 5:
            print("🎉 RAG significantly improves HVAC generation quality!")
            print(f"   Success rate increased by {comparison.success_rate_improvement:.1f}%")
        elif comparison.success_rate_improvement > 0:
            print("👍 RAG provides modest improvement in generation quality.")
            print(f"   Success rate increased by {comparison.success_rate_improvement:.1f}%")
        elif comparison.success_rate_improvement == 0:
            print("➖ RAG has no significant impact on success rate.")
            print("   Consider evaluating qualitative differences in generated code.")
        else:
            print("⚠️ RAG shows negative impact (unexpected - investigate RAG data quality)")
            print(f"   Success rate decreased by {abs(comparison.success_rate_improvement):.1f}%")
        
        print("="*70)


def main():
    parser = argparse.ArgumentParser(
        description="Compare Scenario 1 (LLM only) vs Scenario 2 (LLM + RAG)"
    )
    parser.add_argument(
        "--runs", "-r",
        type=int,
        default=1,
        help="Number of runs per test case (default: 1)"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="outputs/scenario_comparison",
        help="Output directory for results"
    )
    parser.add_argument(
        "--test-cases", "-t",
        nargs="+",
        type=str,
        help="Specific test cases to run (default: all)"
    )
    parser.add_argument(
        "--quick", "-q",
        action="store_true",
        help="Quick mode: run only 2 test cases"
    )
    
    args = parser.parse_args()
    
    comparator = ScenarioComparator(output_dir=args.output)
    
    test_cases = args.test_cases
    if args.quick:
        test_cases = ["single_zone_office", "two_zone_building"]
    
    comparison = comparator.run_comparison(
        num_runs=args.runs,
        test_cases=test_cases
    )
    
    print("\n✓ Comparison complete!")
    print(f"  Results saved to: {args.output}/")


if __name__ == "__main__":
    main()

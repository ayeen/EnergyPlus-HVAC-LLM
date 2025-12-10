"""
HVAC-LLM Complete Pipeline
"""

import os
import json
from datetime import datetime
from config import Config
from src.core.idf_handler import IDFHandler
from src.core.simulator import EnergyPlusSimulator
from src.core.validator import IDFValidator
from src.agents.agent1_generator import HVACGenerator
from src.agents.agent1_5_validator import QuickValidator
from src.agents.agent3_corrector import ErrorCorrector

class HVACLLMPipeline:
    """Complete HVAC-LLM pipeline"""
    
    def __init__(self):
        self.handler = IDFHandler()
        self.simulator = EnergyPlusSimulator()
        self.validator = IDFValidator()
        self.generator = HVACGenerator()
        self.quick_validator = QuickValidator()
        self.corrector = ErrorCorrector()
    
    def run(self, base_idf, zones=None, output_name="pipeline_output", system_name="VRF_System_1", user_request=None, enable_quick_validation=None):
        """
        Run complete pipeline with automatic building context extraction.
        
        Args:
            base_idf: Path to base IDF file
            zones: Optional list of zone names. If None, auto-detects all zones from IDF.
                   If provided, validates zones exist and uses only those zones.
            output_name: Name for output files
            system_name: HVAC system name
            user_request: Optional natural language design request
                         (e.g., "Design a VRF system with heat recovery")
            enable_quick_validation: Enable LLM pre-validation before simulation (default: True)
        """
        
        # Convert relative path to absolute
        if not os.path.isabs(base_idf):
            # Resolve relative to current working directory
            base_idf = os.path.abspath(base_idf)
        
        # Verify file exists
        if not os.path.exists(base_idf):
            raise FileNotFoundError(f"Base IDF file not found: {base_idf}")
        
        print("=" * 70)
        print("HVAC-LLM PIPELINE")
        print("=" * 70)
        
        # ========== NEW: Step 0 - Extract Building Context ==========
        print("\n[0] Analyzing base IDF...")
        base_idf_obj = self.handler.load(base_idf)
        
        # Validate base IDF
        validation_issues = self.handler.validate_base_idf(base_idf_obj)
        if validation_issues:
            print("\n⚠ Base IDF validation warnings:")
            for issue in validation_issues:
                print(f"  {issue}")
            print()
        
        # Auto-detect zones if not provided
        zones_auto_detected = False
        if zones is None:
            zones = self.handler.get_zones(base_idf_obj)
            zones_auto_detected = True
            print(f"✓ Auto-detected {len(zones)} zones from IDF")
            for i, zone in enumerate(zones, 1):
                print(f"  {i}. {zone}")
        else:
            print(f"✓ Using provided zones: {', '.join(zones)}")
            # Validate provided zones exist
            try:
                self.handler.validate_zones(base_idf_obj, zones)
                print(f"✓ All {len(zones)} zones validated")
            except ValueError as e:
                print(f"\n{e}")
                raise
        
        # Extract building metadata for context-aware generation
        building_context = self.handler.extract_building_context(base_idf_obj)
        
        print(f"\n📊 Building Context:")
        print(f"  • Zones: {building_context['num_zones']}")
        if building_context['total_area'] > 0:
            print(f"  • Total Floor Area: {building_context['total_area']:.1f} m²")
        if building_context['total_volume'] > 0:
            print(f"  • Total Volume: {building_context['total_volume']:.1f} m³")
        print(f"  • Orientation: {building_context['orientation']}°")
        print(f"  • Internal Loads: {'✓ Yes' if building_context['has_internal_loads'] else '✗ None'}")
        if building_context['has_internal_loads']:
            loads = []
            if building_context['has_people']: loads.append("People")
            if building_context['has_lights']: loads.append("Lights")
            if building_context['has_equipment']: loads.append("Equipment")
            print(f"    ({', '.join(loads)})")
        print(f"  • Location: {building_context['weather_file']}")
        # ========== END Building Context Extraction ==========
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "base_idf": base_idf,
            "zones": zones,
            "zones_auto_detected": zones_auto_detected,
            "building_context": building_context,
            "user_request": user_request,
            "quick_validation_enabled": enable_quick_validation,
            "steps": []
        }
        
        # Step 1: Generate HVAC
        print("\n[1] Generating HVAC...")
        if user_request:
            print(f"User Request: {user_request}")
        
        # Pass building context to generator for context-aware generation
        hvac_response = self.generator.generate_vrf_system(
            zones, 
            system_name=system_name, 
            user_request=user_request,
            building_context=building_context
        )
        
        if not hvac_response or hvac_response.strip() == "":
            print("❌ Error: Empty HVAC configuration generated")
            print("❌ Error: Empty HVAC configuration generated")
            results["final_status"] = "GENERATION_FAILED"
            results["error"] = "Empty HVAC response"
            return results
        
        # Count HVAC objects before validation
        hvac_count = hvac_response.count('HVACTemplate:') + hvac_response.count('HVACTEMPLATE:')
        print(f"✓ Generated {hvac_count} HVAC objects")
        
        results["steps"].append({
            "step": 1,
            "name": "HVAC Generation",
            "objects_generated": hvac_count,
            "hvac_content_length": len(hvac_response)
        })
        
        # ========== NEW: Step 1.5 - LLM Quick Validation ==========
        if enable_quick_validation:
            print("\n[1.5] LLM validation (pre-simulation)...")
            
            validation_result = self.quick_validator.validate(
                idf_content=hvac_response,
                zones=zones,
                user_request=user_request
            )
            
            results["steps"].append({
                "step": 1.5,
                "name": "Quick Validation (LLM)",
                "valid": validation_result['valid'],
                "errors": validation_result['errors'],
                "warnings": validation_result['warnings'],
                "passed_checks": validation_result['passed_checks']
            })
            
            # If validation found errors, attempt quick fix
            if not validation_result['valid']:
                print("\n[1.5b] Attempting quick fix before simulation...")
                
                try:
                    # Use corrector to fix validation errors
                    error_text = "\n".join(validation_result['errors'])
                    
                    # Read base IDF to pass to corrector
                    with open(base_idf, 'r') as f:
                        base_content = f.read()
                    
                    # Create temporary complete IDF for corrector
                    temp_complete = base_content.rstrip() + "\n\n! === HVAC SYSTEM ===\n\n" + hvac_response.strip() + "\n"
                    temp_idf_path = os.path.join(Config.OUTPUT_DIR, "generated_idfs", f"{output_name}_temp.idf")
                    os.makedirs(os.path.dirname(temp_idf_path), exist_ok=True)
                    with open(temp_idf_path, 'w') as f:
                        f.write(temp_complete)
                    
                    # Get fixes
                    fixes = self.corrector.analyze_and_fix(temp_idf_path, [error_text])
                    
                    if fixes:
                        # Apply fixes to temp file
                        temp_fixed_path = os.path.join(Config.OUTPUT_DIR, "generated_idfs", f"{output_name}_temp_fixed.idf")
                        applied = self.corrector.apply_fixes(temp_idf_path, fixes, temp_fixed_path)
                        
                        if applied > 0:
                            # Extract just the HVAC section from fixed file
                            with open(temp_fixed_path, 'r') as f:
                                fixed_complete = f.read()
                            
                            # Extract HVAC section (after the marker)
                            if "! === HVAC SYSTEM ===" in fixed_complete:
                                hvac_response = fixed_complete.split("! === HVAC SYSTEM ===")[1].strip()
                            
                            print(f"✓ Quick fix applied ({applied} fixes)")
                            
                            results["steps"].append({
                                "step": "1.5b",
                                "name": "Quick Fix Applied",
                                "fixes_applied": applied,
                                "status": "success"
                            })
                            
                            # Re-validate after fix
                            print("\n[1.5c] Re-validating after quick fix...")
                            revalidation = self.quick_validator.validate(
                                idf_content=hvac_response,
                                zones=zones,
                                user_request=user_request
                            )
                            
                            results["steps"].append({
                                "step": "1.5c",
                                "name": "Re-validation After Quick Fix",
                                "valid": revalidation['valid'],
                                "errors": revalidation['errors']
                            })
                        else:
                            print("⚠ Quick fix returned no fixes")
                            results["steps"].append({
                                "step": "1.5b",
                                "name": "Quick Fix Failed",
                                "status": "no_fixes"
                            })
                    else:
                        print("⚠ Corrector returned no fixes")
                        results["steps"].append({
                            "step": "1.5b",
                            "name": "Quick Fix Failed",
                            "status": "no_fixes"
                        })
                        
                except Exception as e:
                    print(f"⚠ Quick fix failed: {e}")
                    results["steps"].append({
                        "step": "1.5b",
                        "name": "Quick Fix Error",
                        "error": str(e)
                    })
        else:
            print("\n[1.5] LLM validation SKIPPED (disabled)")
            results["steps"].append({
                "step": 1.5,
                "name": "LLM Validation",
                "status": "skipped"
            })
        # ========== END LLM Validation ==========
        
        # Save complete IDF (after potential quick fix)
        hvac_idf = os.path.join(Config.OUTPUT_DIR, "generated_idfs", f"{output_name}_hvac.idf")
        os.makedirs(os.path.dirname(hvac_idf), exist_ok=True)
        
        # Manual approach: combine base IDF and HVAC response with clear section marker
        with open(base_idf, 'r') as f:
            base_content = f.read()
        
        # Add clear HVAC section header
        hvac_section_header = """
!-======================================================================
!- HVAC SYSTEM SECTION - GENERATED BY HVAC-LLM
!-======================================================================
!- Generated from user request (if provided)
!- This section contains all HVAC equipment objects
!- Generation timestamp: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """
!-======================================================================

"""
        # step 1.6: Combine base IDF and HVAC section
        complete_idf = base_content.rstrip() + "\n" + hvac_section_header + hvac_response.strip() + "\n"
        with open(hvac_idf, 'w') as f:
            f.write(complete_idf)
        # Count HVAC objects
        hvac_count = hvac_response.count('HVACTemplate:') + hvac_response.count('HVACTEMPLATE:')
        print(f"✓ Added {hvac_count} HVAC objects")
        results["steps"].append({
            "step": 1,
            "name": "HVAC Generation",
            "output": hvac_idf,
            "objects_added": hvac_count
        })
        
        # Step 2: Validate IDF Using standard validator Eppy
        print("\n[2] Validating IDF...")
        is_valid = self.validator.validate(hvac_idf)
        report = self.validator.get_report()
        print(f"Valid: {is_valid}, Errors: {len(report['errors'])}")
        
        results["steps"].append({
            "step": 2,
            "name": "Validation",
            "valid": is_valid,
            "errors": report['errors']
        })
        
        # Step 2.5: Attempt Auto-Fix if validation failed
        if not is_valid and len(report['errors']) > 0:
            print("\n[2.5] Validation failed. Attempting pre-simulation fix...")
            print(f"      Found {len(report['errors'])} validation errors")
            
            try:
                # Prepare error text for corrector
                error_text = "VALIDATION ERRORS:\n" + "\n".join(report['errors'][:10])  # Limit to first 10 errors
                
                # Use corrector to analyze and fix validation errors
                fixes = self.corrector.analyze_and_fix(hvac_idf, [error_text])
                
                if fixes and len(fixes) > 0:
                    # Apply fixes
                    pre_fixed_idf = os.path.join(
                        Config.OUTPUT_DIR, 
                        "generated_idfs", 
                        f"{output_name}_pre_fixed.idf"
                    )
                    applied = self.corrector.apply_fixes(hvac_idf, fixes, pre_fixed_idf)
                    
                    if applied > 0:
                        print(f"✓ Applied {applied} pre-simulation fixes")
                        
                        # Re-validate the fixed file
                        print("[2.6] Re-validating after fix...")
                        is_valid_after_fix = self.validator.validate(pre_fixed_idf)
                        re_report = self.validator.get_report()
                        
                        results["steps"].append({
                            "step": 2.5,
                            "name": "Pre-Simulation Fix",
                            "fixes_applied": applied,
                            "revalidation_valid": is_valid_after_fix,
                            "errors_before": len(report['errors']),
                            "errors_after": len(re_report['errors'])
                        })
                        
                        if is_valid_after_fix:
                            print("✓ Validation passed after fix!")
                            hvac_idf = pre_fixed_idf  # Use fixed version for simulation
                            is_valid = True  # Update validation status
                        else:
                            print(f"⚠ Still {len(re_report['errors'])} validation errors after fix")
                            
                            # Check if we made progress
                            if len(re_report['errors']) < len(report['errors']):
                                print(f"✓ Reduced errors from {len(report['errors'])} to {len(re_report['errors'])}")
                                print("  Proceeding to simulation with remaining errors...")
                                hvac_idf = pre_fixed_idf  # Use partially fixed version
                            else:
                                print("❌ Fixes didn't reduce errors. Stopping pipeline.")
                                results["final_status"] = "VALIDATION_FAILED_AFTER_FIX"
                                results["final_idf"] = hvac_idf
                                results["total_iterations"] = 0
                                results["error_reason"] = f"Validation failed with {len(report['errors'])} errors, fix attempt didn't help"
                                
                                # Save results
                                result_file = os.path.join(Config.OUTPUT_DIR, "logs", f"{output_name}_results.json")
                                os.makedirs(os.path.dirname(result_file), exist_ok=True)
                                with open(result_file, 'w') as f:
                                    json.dump(results, f, indent=2)
                                
                                print(f"\nResults saved: {result_file}")
                                print("\n💡 Suggestion: Review validation errors or check generated HVAC objects")
                                return results
                    else:
                        print("❌ No fixes could be applied")
                        results["final_status"] = "VALIDATION_FAILED_NO_FIX_APPLIED"
                        results["final_idf"] = hvac_idf
                        results["total_iterations"] = 0
                        
                        # Save results
                        result_file = os.path.join(Config.OUTPUT_DIR, "logs", f"{output_name}_results.json")
                        os.makedirs(os.path.dirname(result_file), exist_ok=True)
                        with open(result_file, 'w') as f:
                            json.dump(results, f, indent=2)
                        
                        print(f"\nResults saved: {result_file}")
                        return results
                else:
                    print("❌ Corrector found no fixes for validation errors")
                    results["final_status"] = "VALIDATION_FAILED_NO_FIX"
                    results["final_idf"] = hvac_idf
                    results["total_iterations"] = 0
                    
                    # Save results
                    result_file = os.path.join(Config.OUTPUT_DIR, "logs", f"{output_name}_results.json")
                    os.makedirs(os.path.dirname(result_file), exist_ok=True)
                    with open(result_file, 'w') as f:
                        json.dump(results, f, indent=2)
                    
                    print(f"\nResults saved: {result_file}")
                    print("\n💡 Suggestion: Review validation errors manually")
                    return results
                    
            except Exception as e:
                print(f"❌ Pre-simulation fix failed with error: {e}")
                results["steps"].append({
                    "step": 2.5,
                    "name": "Pre-Simulation Fix Error",
                    "error": str(e)
                })
                results["final_status"] = "VALIDATION_FIX_ERROR"
                results["error"] = str(e)
                
                # Save results
                result_file = os.path.join(Config.OUTPUT_DIR, "logs", f"{output_name}_results.json")
                os.makedirs(os.path.dirname(result_file), exist_ok=True)
                with open(result_file, 'w') as f:
                    json.dump(results, f, indent=2)
                
                print(f"\nResults saved: {result_file}")
                return results
        else:
            if is_valid:
                print("✓ Validation passed - proceeding to simulation")
        
        # Step 3: Simulate (only if validation passed or was successfully fixed)
        print("\n[3] Simulating...")
        sim_dir = os.path.join(Config.OUTPUT_DIR, "simulations", f"{output_name}_sim1")
        sim_result = self.simulator.run(hvac_idf, sim_dir)
        print(f"Success: {sim_result['success']}, Errors: {sim_result['error_count']}")
        
        results["steps"].append({
            "step": 3,
            "name": "Simulation",
            "success": sim_result['success'],
            "error_count": sim_result['error_count']
        })
        
        # Step 4: Fix using Error Corrector iteratively (Agent 3)
        iteration = 1
        current_idf = hvac_idf
        
        while not sim_result['success'] and iteration <= Config.MAX_ERROR_CORRECTION_ITERATIONS:
            print(f"\n[4.{iteration}] Fixing errors...")
            
            all_errors = sim_result.get('error_blocks', sim_result['severe_errors'] + sim_result['fatal_errors'])
            fixes = self.corrector.analyze_and_fix(current_idf, all_errors)
            
            fixed_idf = os.path.join(
                Config.OUTPUT_DIR, 
                "generated_idfs", 
                f"{output_name}_fixed_{iteration}.idf"
            )
            
            applied = self.corrector.apply_fixes(current_idf, fixes, fixed_idf)
            print(f"✓ Applied {applied} fixes")
            
            results["steps"].append({
                "step": f"4.{iteration}",
                "name": f"Error Correction {iteration}",
                "fixes_applied": applied
            })
            
            # Re-simulate
            print(f"\n[5.{iteration}] Re-simulating...")
            sim_dir = os.path.join(
                Config.OUTPUT_DIR, 
                "simulations", 
                f"{output_name}_sim{iteration+1}"
            )
            sim_result = self.simulator.run(fixed_idf, sim_dir)
            print(f"Success: {sim_result['success']}")
            
            results["steps"].append({
                "step": f"5.{iteration}",
                "name": f"Re-simulation {iteration}",
                "success": sim_result['success'],
                "error_count": sim_result['error_count']
            })
            
            current_idf = fixed_idf
            iteration += 1
        
        # Final results
        results["final_status"] = "SUCCESS" if sim_result['success'] else "FAILED"
        results["final_idf"] = current_idf
        results["total_iterations"] = iteration - 1
        
        # Copy final IDF to a consistent name for easy access
        if sim_result['success']:
            final_output = os.path.join(
                Config.OUTPUT_DIR, 
                "generated_idfs", 
                f"{output_name}_FINAL.idf"
            )
            import shutil
            shutil.copy(current_idf, final_output)
            print(f"\n✓ Final corrected IDF copied to: {final_output}")
            print(f"  Use this file in EP-Launch for simulation!")
        
        # Save results
        result_file = os.path.join(Config.OUTPUT_DIR, "logs", f"{output_name}_results.json")
        os.makedirs(os.path.dirname(result_file), exist_ok=True)
        
        with open(result_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print("\n" + "=" * 70)
        print(f"PIPELINE COMPLETE: {results['final_status']}")
        print(f"Results saved: {result_file}")
        if sim_result['success']:
            print(f"\n🎉 SUCCESS! Use this file:")
            print(f"   {final_output}")
        print("=" * 70)
        
        return results

def main():
    """Main entry point"""
    
    # Example usage
    pipeline = HVACLLMPipeline()
    
    # You need to provide a base IDF with zones
    base_idf = "data/base_idfs/building_with_zones.idf"
    zones = ["Zone_1"]
    
    results = pipeline.run(base_idf, zones, output_name="example_run")
    
    return results

if __name__ == "__main__":
    main()

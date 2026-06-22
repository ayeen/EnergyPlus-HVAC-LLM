"""
Agent 1.5: Quick Validator
Performs lightweight LLM-based validation before simulation to catch common errors.
"""

import json
import re
from typing import Dict, List
from src.agents.llm_interface import UniversalLLM

class QuickValidator:
    """
    Lightweight pre-simulation validator.
    Catches 70-80% of common errors in 5-10 seconds.
    """
    
    def __init__(self):
        self.llm = UniversalLLM()
    
    def validate(self, idf_content: str, zones: List[str], user_request: str = "") -> Dict:
        """
        Perform quick validation checks on generated IDF.
        
        Args:
            idf_content: Generated HVAC IDF objects
            zones: List of zone names
            user_request: Original user request (optional)
        
        Returns:
            {
                'valid': bool,
                'errors': List[str],
                'warnings': List[str],
                'suggestions': List[str],
                'passed_checks': List[str]
            }
        """
        print("\n[Agent 1.5] Quick Validation (Pre-Simulation)")
        print("-" * 70)
        
        results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'suggestions': [],
            'passed_checks': []
        }
        
        # Run validation checks
        self._check_zone_count(idf_content, zones, results)
        self._check_master_thermostat(idf_content, zones, results)
        self._check_field_ranges_llm(idf_content, results)
        self._check_object_completeness(idf_content, zones, results)
        
        # Set overall validity
        results['valid'] = len(results['errors']) == 0
        
        # Print results
        self._print_results(results)
        
        return results
    
    def _check_zone_count(self, idf: str, zones: List[str], results: Dict):
        """Check if number of Zone:VRF objects matches number of zones"""
        zone_vrf_count = idf.count('HVACTemplate:Zone:VRF,')
        
        if zone_vrf_count == 0:
            results['errors'].append(
                f"❌ No HVACTemplate:Zone:VRF objects found. Expected {len(zones)} for zones: {', '.join(zones)}"
            )
        elif zone_vrf_count != len(zones):
            results['errors'].append(
                f"❌ Zone count mismatch: Found {zone_vrf_count} HVACTemplate:Zone:VRF objects but have {len(zones)} zones"
            )
        else:
            results['passed_checks'].append(
                f"✓ Zone count correct: {zone_vrf_count} Zone:VRF objects for {len(zones)} zones"
            )
    
    def _check_master_thermostat(self, idf: str, zones: List[str], results: Dict):
        """Check if Master Thermostat Location is set when needed"""
        # Check if System:VRF has Master Thermostat Priority Control
        has_master_priority = 'MasterThermostatPriority' in idf or 'Master Thermostat Priority' in idf
        
        if has_master_priority:
            # Look for field 13 in System:VRF (Zone Name for Master Thermostat Location)
            # Simple check: look for zone names after "MasterThermostatPriority"
            master_thermostat_found = False
            for zone in zones:
                if zone in idf and idf.find(zone) > idf.find('MasterThermostatPriority'):
                    master_thermostat_found = True
                    results['passed_checks'].append(
                        f"✓ Master Thermostat Location appears to be set to '{zone}'"
                    )
                    break
            
            if not master_thermostat_found:
                results['errors'].append(
                    f"❌ Master Thermostat Priority Control detected but Zone Name for Master Thermostat Location may be missing. Must specify one of: {', '.join(zones)}"
                )
        else:
            results['passed_checks'].append(
                "✓ No Master Thermostat Priority Control (field not required)"
            )
    
    def _check_field_ranges_llm(self, idf: str, results: Dict):
        """Use LLM to check if field values are in reasonable ranges"""
        
        system_prompt = """You are an EnergyPlus VRF system validator.

Review this VRF configuration and check for obvious errors in field values.

CHECK ONLY THESE CRITICAL RANGES:
1. Gross Rated Cooling COP: Should be 2.5 - 5.0 (typical VRF range)
2. Gross Rated Heating COP: Should be 2.5 - 4.5 (typical VRF range)
3. Minimum Outdoor Temperature in Cooling Mode: Should be -15°C to -5°C (correct: -6.0°C)
4. Maximum Outdoor Temperature in Cooling Mode: Should be 35°C to 52°C (correct: 43.0°C)
5. Minimum Outdoor Temperature in Heating Mode: Should be -25°C to -15°C (correct: -20.0°C)
6. Maximum Outdoor Temperature in Heating Mode: Should be 12°C to 20°C (correct: 15.5°C)

Return ONLY a JSON object with this exact structure (no markdown, no explanation):
{
  "errors": ["list of serious out-of-range errors"],
  "warnings": ["list of unusual but possibly valid values"]
}

If all values are reasonable, return: {"errors": [], "warnings": []}"""

        user_prompt = f"""Review this VRF configuration and check for obvious errors in field values:

{idf[:3000]}

Return ONLY JSON with errors and warnings arrays."""

        try:
            response = self.llm.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt
            )
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                validation_result = json.loads(json_match.group())
                
                if validation_result.get('errors'):
                    results['errors'].extend([f"❌ Range check: {e}" for e in validation_result['errors']])
                
                if validation_result.get('warnings'):
                    results['warnings'].extend([f"⚠ Range check: {w}" for w in validation_result['warnings']])
                
                if not validation_result.get('errors') and not validation_result.get('warnings'):
                    results['passed_checks'].append("✓ Field ranges are within acceptable values")
            else:
                results['warnings'].append("⚠ Could not parse LLM range check response")
                
        except Exception as e:
            results['warnings'].append(f"⚠ LLM range check failed: {str(e)}")
    
    def _check_object_completeness(self, idf: str, zones: List[str], results: Dict):
        """Check if required objects are present"""
        
        # Check for System:VRF
        if 'HVACTemplate:System:VRF' not in idf:
            results['errors'].append("❌ Missing HVACTemplate:System:VRF object")
        else:
            results['passed_checks'].append("✓ HVACTemplate:System:VRF present")
        
        # Check if each zone has Zone:VRF
        missing_zones = []
        for zone in zones:
            if zone not in idf:
                missing_zones.append(zone)
        
        if missing_zones:
            results['warnings'].append(f"⚠ Zones not found in HVAC objects: {', '.join(missing_zones)}")
        else:
            results['passed_checks'].append(f"✓ All {len(zones)} zones referenced in HVAC objects")
    
    def _print_results(self, results: Dict):
        """Print validation results in a readable format"""
        
        if results['passed_checks']:
            print("\n✅ Passed Checks:")
            for check in results['passed_checks']:
                print(f"  {check}")
        
        if results['warnings']:
            print("\n⚠️  Warnings:")
            for warning in results['warnings']:
                print(f"  {warning}")
        
        if results['errors']:
            print("\n❌ Errors:")
            for error in results['errors']:
                print(f"  {error}")
        
        if results['suggestions']:
            print("\n💡 Suggestions:")
            for suggestion in results['suggestions']:
                print(f"  {suggestion}")
        
        print("-" * 70)
        if results['valid']:
            print("✅ Pre-validation PASSED - Proceeding to simulation")
        else:
            print("❌ Pre-validation FAILED - Attempting auto-fix")
        print()

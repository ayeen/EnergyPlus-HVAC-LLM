"""
LLM Agent 3: Error Corrector
"""

from src.agents.llm_interface import UniversalLLM
from src.core.idf_handler import IDFHandler
import json
import re

class ErrorCorrector:
    """Fix EnergyPlus errors using LLM"""
    
    def __init__(self):
        self.llm = UniversalLLM()
        self.handler = IDFHandler()
    
    def analyze_and_fix(self, idf_path, errors):
        """Analyze errors and suggest fixes"""
        
        # Try to load IDF, but handle cases where it's malformed
        try:
            idf = self.handler.load(idf_path)
            summary = self.handler.get_summary(idf)
        except Exception as e:
            print(f"⚠ Warning: Could not parse IDF with eppy ({e}). Using basic text analysis.")
            summary = {'zones': ['Unknown'], 'vrf_systems': ['Unknown'], 'thermostats': ['Unknown']}
            # For malformed IDFs, we'll do text-based analysis
        
        # Provide more errors for better context - increased from 15 to 40
        error_text = "\n".join(errors[:40])
        
        system_prompt = """You are an expert EnergyPlus IDF debugger specializing in HVACTemplate objects. 
Your task is to analyze EnergyPlus validation errors and generate precise field corrections in JSON format.

CRITICAL UNDERSTANDING:
- Errors like "Value type 'string' for input 'X' not permitted by 'type' constraint" mean field X is in the WRONG field position
- The value 'X' belongs in a different field that accepts strings
- You must identify WHERE the value should go and WHAT should be in the current field
- If you see "Zone Name for Master Thermostat Location must be entered when Master Thermostat Priority Control Type = MASTERTHERMOSTATPRIORITY", set zone_name_for_master_thermostat_location to the first zone name in the zones list

HVACTemplate:System:VRF FIELD ORDER (first 10 fields after Name):
1. name (string)
2. system_availability_schedule_name (string, optional)
3. gross_rated_total_cooling_capacity (number or "Autosize")
4. gross_rated_cooling_cop (number)
5. minimum_outdoor_temperature_in_cooling_mode (number)
6. maximum_outdoor_temperature_in_cooling_mode (number)
7. gross_rated_heating_capacity (number or "Autosize")
8. rated_heating_capacity_sizing_ratio (number)
9. gross_rated_heating_cop (number)
10. minimum_outdoor_temperature_in_heating_mode (number)
11. maximum_outdoor_temperature_in_heating_mode (number)
12. minimum_heat_pump_part_load_ratio (number)
13. zone_name_for_master_thermostat_location (string)
14. master_thermostat_priority_control_type (enum: "LoadPriority", "ZonePriority", "ThermostatOffsetPriority", "Scheduled", "MasterThermostatPriority")
15. thermostat_priority_schedule_name (string, optional)
16. zone_terminal_unit_list_name (string, optional)
17. heat_pump_waste_heat_recovery (enum: "No", "Yes")
18. equivalent_piping_length_used_for_piping_correction_factor (number)
19. vertical_height_used_for_piping_correction_factor (number)
20. piping_correction_factor_for_length_in_cooling_mode_curve_name (string, optional)
21. piping_correction_factor_for_height_in_cooling_mode_curve_name (string, optional)
22. equivalent_piping_length_used_for_piping_correction_factor_in_heating_mode (number)
23. vertical_height_used_for_piping_correction_factor_in_heating_mode (number)
24. piping_correction_factor_for_length_in_heating_mode_curve_name (string, optional)
25. piping_correction_factor_for_height_in_heating_mode_curve_name (string, optional)
26. crankcase_heater_power_per_compressor (number)
27. number_of_compressors (integer)
28. ratio_of_compressor_size_to_total_compressor_capacity (number)
29. maximum_outdoor_drybulb_temperature_for_crankcase_heater (number)
30. defrost_strategy (enum: "ReverseCycle", "Resistive")
31. defrost_control (enum: "Timed", "OnDemand")
32. defrost_energy_input_ratio_modifier_function_of_temperature_curve_name (string, optional)
33. defrost_time_period_fraction (number)
34. resistive_defrost_heater_capacity (number or "Autosize")
35. maximum_outdoor_drybulb_temperature_for_defrost_operation (number)
36. condenser_type (enum: "AirCooled", "WaterCooled", "EvaporativelyCooled")
37. condenser_inlet_node_name (string, optional)
38. condenser_outlet_node_name (string, optional)
39. water_condenser_volume_flow_rate (number or "Autosize")
40. evaporative_condenser_effectiveness (number)
41. evaporative_condenser_air_flow_rate (number or "Autosize")
42. evaporative_condenser_pump_rated_power_consumption (number or "Autosize")
43. basin_heater_capacity (number)
44. basin_heater_setpoint_temperature (number)
45. basin_heater_operating_schedule_name (string, optional)
46. fuel_type (enum: "Electricity", "NaturalGas", "Propane", "Diesel", "Gasoline", "FuelOilNo1", "FuelOilNo2", "OtherFuel1", "OtherFuel2")

HVACTemplate:Zone:VRF FIELD ORDER (first 15 fields after Zone_Name):
1. zone_name (string)
2. template_vrf_system_name (string)
3. template_thermostat_name (string, optional)
4. supply_air_fan_operating_mode_schedule_name (string, optional)
5. cooling_supply_air_flow_rate (number or "Autosize")
6. no_cooling_supply_air_flow_rate (number or "Autosize")
7. heating_supply_air_flow_rate (number or "Autosize")
8. no_heating_supply_air_flow_rate (number or "Autosize")
9. cooling_outdoor_air_flow_rate (number or "Autosize")
10. heating_outdoor_air_flow_rate (number or "Autosize")
11. no_load_outdoor_air_flow_rate (number or "Autosize")
12. supply_air_fan_placement (enum: "DrawThrough", "BlowThrough")
13. supply_air_fan_total_efficiency (number)
14. supply_air_fan_delta_pressure (number)
15. supply_air_fan_motor_efficiency (number)
16. supply_air_fan_motor_in_air_stream_fraction (number)
17. cooling_coil_type (enum: "VariableRefrigerantFlowDX")
18. cooling_coil_availability_schedule_name (string, optional)
19. cooling_coil_gross_rated_total_capacity (number or "Autosize")
20. cooling_coil_gross_rated_sensible_heat_ratio (number or "Autosize")
21. heating_coil_type (enum: "VariableRefrigerantFlowDX", "Electric", "Gas", "Water")
22. heating_coil_availability_schedule_name (string, optional)
23. heating_coil_gross_rated_capacity (number or "Autosize")
24. zone_heating_sizing_factor (number)
25. zone_cooling_sizing_factor (number)
26. rated_total_heating_capacity_sizing_ratio (number, >=1.0)
27. baseboard_heating_type (enum: "None", "Electric", "HotWater")
28. baseboard_heating_availability_schedule_name (string, optional)
29. baseboard_heating_capacity (number or "Autosize")
30. dedicated_outdoor_air_system_name (string, optional)
31. outdoor_air_method (enum: "None", "Flow/Zone", "Flow/Person", "Flow/Area", "Sum", "Maximum", "DetailedSpecification")

Output ONLY a valid JSON array of fix objects."""
        
        user_prompt = f"""Analyze these EnergyPlus errors and generate corrections in JSON format.

**IDF Structure:**
- Zones: {summary['zones']}
- VRF Systems: {summary['vrf_systems']}
- Thermostats: {summary['thermostats']}

**EnergyPlus Errors:**
```
{error_text}
```

**Analysis Guidelines:**
1. For "Value type 'string' for input 'X' not permitted" errors:
   - The string value 'X' is in a numeric field
   - Find the correct field that accepts 'X' as a string
   - Set the numeric field to an appropriate number (or "Autosize")

2. For "Failed to match against any enum values" errors:
   - The value is in the wrong enum field
   - Find the correct enum field for that value
   - Set the incorrect field to a valid enum value

3. Common Misplacements in HVACTemplate:System:VRF:
   - "AirCooled" → should be in field 36 (condenser_type), not field 3
   - "ZoneVRF" → likely a terminal unit type, check context
   - Schedule names → should be in schedule name fields (2, 15, 45, etc.)
   - Curve names → should be in curve name fields (20, 21, 24, 25, 32, etc.)
   - "Electric", "Gas", etc. → should be in field 46 (fuel_type)
   - "ReverseCycle", "Resistive" → should be in field 30 (defrost_strategy)
   - Numeric values (3.0, 10000.0, etc.) → should be in capacity/COP fields (3, 4, 7, 9, etc.)

4. Common Misplacements in HVACTemplate:Zone:VRF:
   - Schedule names → should be in schedule name fields (4, 18, 22, 28, etc.)
   - "Flow/Zone", "Flow/Person" → should be in field 31 (outdoor_air_method)
   - "DrawThrough", "BlowThrough" → should be in field 12 (supply_air_fan_placement)
   - Numeric flow rates → should be in flow rate fields (5-11, 19, 23, etc.)
   - "VariableRefrigerantFlowDX" → should be in fields 17 or 21 (coil type)
   - Sizing ratios >=1.0 → should be in field 26 (rated_total_heating_capacity_sizing_ratio)

**Required Output Format:**
```json
[
  {{
    "object_type": "HVACTemplate:System:VRF",
    "object_name": "VRF_System_1",
    "field_to_change": "condenser_type",
    "new_value": "AirCooled"
  }},
  {{
    "object_type": "HVACTemplate:System:VRF",
    "object_name": "VRF_System_1",
    "field_to_change": "gross_rated_total_cooling_capacity",
    "new_value": "Autosize"
  }}
]
```

Generate the complete JSON array of ALL necessary fixes now:"""
        
        response = self.llm.generate(system_prompt, user_prompt)
        
        print("\n" + "="*80)
        print("LLM RESPONSE FOR ERROR CORRECTION:")
        print("="*80)
        print(response[:1000] + ("..." if len(response) > 1000 else ""))
        print("="*80 + "\n")
        
        # Extract JSON from response, handling markdown
        json_match = re.search(r'```(?:json)?\s*(\[[\s\S]*?\])\s*```', response)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find JSON array without markdown
            json_match = re.search(r'\[\s*\{[\s\S]*?\}\s*\]', response)
            if json_match:
                json_str = json_match.group(0)
            else:
                # Last resort: find between first [ and last ]
                if '[' in response and ']' in response:
                    start = response.find('[')
                    end = response.rfind(']')
                    json_str = response[start:end+1]
                else:
                    json_str = "[]"

        try:
            fixes = json.loads(json_str)
            print(f"\n✓ Successfully parsed {len(fixes)} fixes from LLM response\n")
            return fixes
        except json.JSONDecodeError as e:
            print(f"❌ Failed to decode JSON from LLM response: {e}")
            print(f"Attempted to parse: {json_str[:500]}")
            return []
        

    def apply_fixes(self, idf_path, fixes, output_path):
        """Apply fixes to IDF"""
        
        idf = self.handler.load(idf_path)
        applied = 0
        failed = 0
        
        print(f"\n{'='*80}")
        print(f"APPLYING {len(fixes)} FIXES TO IDF")
        print(f"{'='*80}\n")
        
        for i, fix in enumerate(fixes, 1):
            obj_type = fix['object_type']
            obj_name = fix.get('object_name', 'N/A')
            field = fix['field_to_change']
            new_value = fix['new_value']
            
            print(f"{i}. {obj_type}[{obj_name}].{field} = '{new_value}'")
            
            objects = idf.idfobjects.get(obj_type, [])
            
            if not objects:
                print(f"   ❌ No objects of type '{obj_type}' found in IDF")
                failed += 1
                continue
            
            fix_applied = False
            for obj in objects:
                matched = False
                
                # Try multiple matching strategies
                if obj_name == 'N/A' or not obj_name:
                    # No name specified, apply to first object
                    matched = True
                elif hasattr(obj, 'Name') and obj.Name == obj_name:
                    matched = True
                elif hasattr(obj, 'Zone_Name') and obj.Zone_Name == obj_name:
                    matched = True
                elif hasattr(obj, 'Template_VRF_System_Name') and obj.Template_VRF_System_Name == obj_name:
                    matched = True
                
                if matched:
                    try:
                        # Convert field name to eppy format
                        # Try direct name first (in case it's already correct)
                        if hasattr(obj, field):
                            eppy_field = field
                        else:
                            # Convert snake_case to Title_Case with special handling
                            # Preserve lowercase articles like "for", "in", "of", "to", "per", "used"
                            lowercase_words = {'for', 'in', 'of', 'to', 'per', 'used', 'or', 'and', 'the'}
                            parts = field.split('_')
                            eppy_parts = []
                            for i, part in enumerate(parts):
                                if i > 0 and part.lower() in lowercase_words:
                                    eppy_parts.append(part.lower())
                                else:
                                    eppy_parts.append(part.capitalize())
                            eppy_field = '_'.join(eppy_parts)
                        
                        # Get old value for logging
                        old_value = getattr(obj, eppy_field, '<not set>')
                        
                        # Convert numeric strings to appropriate types
                        if isinstance(new_value, str) and new_value.replace('.', '').replace('-', '').isdigit():
                            if '.' in new_value:
                                new_value = float(new_value)
                            else:
                                new_value = int(new_value)
                        
                        setattr(obj, eppy_field, new_value)
                        print(f"   ✓ Changed from '{old_value}' to '{new_value}'")
                        applied += 1
                        fix_applied = True
                        break
                    except Exception as e:
                        print(f"   ❌ Error applying fix: {e}")
                        failed += 1
                        break
            
            if not fix_applied and not failed:
                print(f"   ⚠ No matching object found for '{obj_name}'")
                failed += 1
        
        print(f"\n{'='*80}")
        print(f"FIXES APPLIED: {applied} successful, {failed} failed")
        print(f"{'='*80}\n")
        
        idf.saveas(output_path)
        return applied

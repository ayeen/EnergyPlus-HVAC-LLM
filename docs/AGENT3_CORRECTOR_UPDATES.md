# Agent 3 Corrector Updates

## Overview
Updated the `agent3_corrector.py` to handle EnergyPlus HVACTemplate validation errors more effectively by providing comprehensive field order documentation and improved error analysis.

## Key Changes Made

### 1. Enhanced System Prompt
Added detailed field order specifications for both `HVACTemplate:System:VRF` and `HVACTemplate:Zone:VRF` objects (46 fields for System:VRF, 31 fields for Zone:VRF).

**Critical Understanding Added:**
- Errors like "Value type 'string' for input 'X' not permitted by 'type' constraint" mean the value X is in the WRONG field position
- The corrector must identify WHERE the value should go and WHAT should be in the current field

### 2. Common Error Patterns Documented
Added specific guidance for common misplacements:

**HVACTemplate:System:VRF:**
- `"AirCooled"` → field 36 (condenser_type), not field 3
- Schedule names → fields 2, 15, 45, etc.
- Curve names → fields 20, 21, 24, 25, 32, etc.
- `"Electric"`, `"Gas"` → field 46 (fuel_type)
- Numeric values (COP, capacity) → fields 3, 4, 7, 9, etc.

**HVACTemplate:Zone:VRF:**
- `"Flow/Zone"`, `"Flow/Person"` → field 31 (outdoor_air_method)
- `"DrawThrough"`, `"BlowThrough"` → field 12 (supply_air_fan_placement)
- Schedule names → fields 4, 18, 22, 28, etc.
- Sizing ratios (>=1.0) → field 26 (rated_total_heating_capacity_sizing_ratio)

### 3. Improved Error Context
- Increased error analysis from 15 to 40 errors
- Added detailed analysis guidelines for the LLM
- Provides specific examples of how to map errors to fixes

### 4. Better Error Handling
- Added try-catch for IDF loading (handles malformed IDFs)
- Improved JSON extraction with multiple fallback strategies
- Added detailed logging of LLM responses and fix application

### 5. Enhanced Fix Application
- Better object matching (supports Name, Zone_Name, Template_VRF_System_Name)
- Automatic type conversion for numeric values
- Detailed progress reporting for each fix attempt
- Tracks successful vs failed fixes

## Example Error Fixes

### Before:
```
** Severe  ** <root>[HVACTemplate:System:VRF][VRF_System_1][gross_rated_cooling_cop] - Value type "string" for input "AirCooled" not permitted
```

### After (Suggested Fix):
```json
{
  "object_type": "HVACTemplate:System:VRF",
  "object_name": "VRF_System_1",
  "field_to_change": "condenser_type",
  "new_value": "AirCooled"
},
{
  "object_type": "HVACTemplate:System:VRF",
  "object_name": "VRF_System_1",
  "field_to_change": "gross_rated_cooling_cop",
  "new_value": "Autosize"
}
```

## Root Cause Analysis

The errors you encountered occur because:

1. **Agent 1 (Generator)** creates HVACTemplate objects with fields in incorrect positions
2. **EnergyPlus Validator** detects type mismatches (string values in numeric fields, etc.)
3. **Agent 3 (Corrector)** now has complete field order documentation to correctly identify and fix these misplacements

## Testing

To test the updated corrector:

```powershell
cd examples
python example2_complete_pipeline.py
```

The corrector will now:
1. Parse up to 40 errors for comprehensive analysis
2. Generate specific fixes with proper field names
3. Apply fixes with detailed logging
4. Report success/failure for each fix

## Future Improvements

Consider also updating **Agent 1 (Generator)** with similar field order specifications to prevent these errors from occurring in the first place. The `energyplus_vrf_prompt.json` could include the complete field order to ensure correct generation from the start.

## Files Modified

1. `src/agents/agent3_corrector.py`
   - Enhanced system prompt with complete field specifications
   - Improved error handling and logging
   - Better fix application with multiple matching strategies
   - Added robust JSON extraction

## Known Limitations

1. The corrector relies on the LLM's ability to understand complex field mappings
2. Some extremely malformed IDFs may not be parseable by eppy
3. The corrector attempts fixes iteratively (max 5 iterations in pipeline)
4. Each LLM call may produce slightly different results due to non-deterministic nature

## Recommendation

For best results, also update the Agent 1 generator prompt to include field order specifications, which will reduce the need for extensive corrections.

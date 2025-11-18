# User Request Merging - Implementation Documentation

## Overview

This document explains how **Approach A** has been implemented to merge user's natural language design requests with technical EnergyPlus templates.

## Architecture

### Three-Layer Prompt System

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 1: User's Design Request (hvac_requests.json)        │
│ ----------------------------------------                     │
│ Natural language: "Design VRF with heat recovery"           │
│ Purpose: What the user wants                                │
│ Edited by: End users, building designers                    │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ Layer 2: Technical Template (energyplus_vrf_prompt.json)   │
│ ----------------------------------------                     │
│ Template: "Generate VRF for zones: {zone_list}..."          │
│ Purpose: Exact format and field order                       │
│ Edited by: Developers                                       │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ Layer 3: Combined Prompt (sent to LLM)                     │
│ ----------------------------------------                     │
│ USER REQUEST: Design VRF with heat recovery                 │
│ TECHNICAL SPEC: Generate VRF for ZONE ONE...                │
│   - Field 17: Heat_Pump_Waste_Heat_Recovery                 │
│   - Must follow exact 32-field structure                    │
└─────────────────────────────────────────────────────────────┘
```

## Implementation Details

### 1. Updated Agent1Generator (`src/agents/agent1_generator.py`)

**Method: `generate_vrf_system()`**
- Added `user_request` parameter (optional)
- Passes user request to prompt creation method

```python
def generate_vrf_system(self, zones, system_name="VRF_System_1", user_request=None):
    """
    Args:
        zones: List of zone names
        system_name: HVAC system name
        user_request: Natural language design request (NEW!)
    """
    [system_prompt, user_prompt] = self._create_energyplus_template_prompt(
        zone_list, 
        system_name, 
        user_request  # Pass through
    )
```

**Method: `_create_energyplus_template_prompt()`**
- Accepts optional `user_request` parameter
- Merges user request with technical template
- Returns combined prompt

```python
def _create_energyplus_template_prompt(self, zone_list, system_name, user_request=None):
    # Load technical template
    technical_template = prompt_data[0]["user_prompt"].format(
        zone_list=zone_list, 
        system_name=system_name
    )
    
    # APPROACH A: Merge user request with technical specification
    if user_request:
        combined_prompt = f"""USER DESIGN REQUEST:
{user_request}

TECHNICAL IMPLEMENTATION REQUIREMENTS:
{technical_template}

Please generate the EnergyPlus IDF objects that fulfill the user's design request 
while strictly following the technical specifications above."""
    else:
        combined_prompt = technical_template
    
    return system_prompt, combined_prompt
```

### 2. Updated Pipeline (`src/pipeline.py`)

**Method: `run()`**
- Added `user_request` parameter (optional)
- Stores user request in results
- Passes to Agent1Generator

```python
def run(self, base_idf, zones, output_name="pipeline_output", user_request=None):
    """
    Args:
        base_idf: Path to base IDF file
        zones: List of zone names
        output_name: Name for output files
        user_request: Natural language design request (NEW!)
    """
    results = {
        "user_request": user_request,  # Store in results
        # ...
    }
    
    # Pass to generator
    hvac_response = self.generator.generate_vrf_system(
        zones, 
        user_request=user_request
    )
```

### 3. Updated Example2 (`examples/example2_complete_pipeline.py`)

```python
# Define user's natural language request
user_request = "Design a VRF HVAC system with heat recovery for efficient heating and cooling"

# Pass to pipeline
results = pipeline.run(
    base_idf=base_idf,
    zones=zones,
    output_name="example2_complete",
    user_request=user_request  # NEW!
)
```

### 4. New Example3 - Config File Based (`examples/example3_config_based.py`)

**Features:**
- Loads requests from `config/hvac_requests.json`
- Interactive menu to select request
- Batch mode to process all requests
- Creates example config if not found

**Usage:**
```bash
python examples/example3_config_based.py
# Choose: vrf_heat_recovery
```

### 5. Configuration File (`config/hvac_requests.json`)

```json
{
  "vrf_heat_recovery": {
    "prompt": "Design a VRF system with heat recovery...",
    "zones": ["ZONE ONE"],
    "base_idf": "../data/base_idfs/building_with_zones.idf"
  },
  "vrf_high_efficiency": {
    "prompt": "Design a high-efficiency VRF system...",
    "zones": ["ZONE ONE"],
    "base_idf": "../data/base_idfs/building_with_zones.idf"
  }
}
```

## How It Works - Step by Step

### Example: Heat Recovery Request

1. **User defines request** in `hvac_requests.json`:
   ```json
   {
     "prompt": "Design a VRF system with heat recovery",
     "zones": ["ZONE ONE"]
   }
   ```

2. **Pipeline loads config** and passes to Agent1:
   ```python
   user_request = "Design a VRF system with heat recovery"
   ```

3. **Agent1 loads technical template**:
   ```
   Generate VRF system for zones: ZONE ONE
   **GENERATE EXACTLY:**
   1. HVACTemplate:System:VRF with first 12 fields...
   ```

4. **Agent1 merges prompts**:
   ```
   USER DESIGN REQUEST:
   Design a VRF system with heat recovery
   
   TECHNICAL IMPLEMENTATION REQUIREMENTS:
   Generate VRF system for zones: ZONE ONE
   - Field 17: Heat_Pump_Waste_Heat_Recovery (enum: "No", "Yes")
   - Follow exact 32-field structure
   ```

5. **LLM receives combined prompt**:
   - Understands user wants heat recovery
   - Follows exact technical format
   - Sets Field 17 = "Yes"

6. **Output generated**:
   ```idf
   HVACTemplate:System:VRF,
     VRF_System_1,           !- Name
     ,                       !- System Availability Schedule
     ...
     Yes;                    !- Heat Pump Waste Heat Recovery (Field 17)
   ```

## Benefits of Approach A

### ✅ Flexibility
- Users can write natural language requests
- No need to understand EnergyPlus field syntax

### ✅ Precision
- Technical template ensures exact format
- Field order strictly maintained
- Required fields always included

### ✅ Intelligence
- LLM interprets user intent
- Maps concepts (heat recovery) to fields (Field 17 = Yes)
- Maintains technical correctness

### ✅ Maintainability
- User requests separate from technical templates
- Update template without changing user configs
- Add new request types easily

## Usage Examples

### Example 1: Basic Usage (Example2)
```python
python examples/example2_complete_pipeline.py
# Uses hardcoded user_request in the script
```

### Example 2: Config File - Single Request (Example3)
```bash
python examples/example3_config_based.py
# Choose: vrf_heat_recovery
```

### Example 3: Config File - Batch Mode (Example3)
```bash
python examples/example3_config_based.py
# Choose: all
# Processes all requests in hvac_requests.json
```

### Example 4: Programmatic Usage
```python
from src.pipeline import HVACLLMPipeline

pipeline = HVACLLMPipeline()

result = pipeline.run(
    base_idf="data/base_idfs/building_with_zones.idf",
    zones=["ZONE ONE"],
    output_name="my_vrf_system",
    user_request="Design a high-efficiency VRF system with economizer"
)

if result['final_status'] == 'SUCCESS':
    print(f"Generated: {result['final_idf']}")
```

## Adding New Request Types

1. **Edit `config/hvac_requests.json`**:
   ```json
   {
     "vrf_economizer": {
       "prompt": "Design a VRF system with air-side economizer for free cooling",
       "zones": ["ZONE ONE"],
       "base_idf": "../data/base_idfs/building_with_zones.idf"
     }
   }
   ```

2. **Run Example3**:
   ```bash
   python examples/example3_config_based.py
   # Choose: vrf_economizer
   ```

That's it! The system automatically merges your request with the technical template.

## Testing Results

### Test 1: Example2 with User Request ✅
- User Request: "Design a VRF system with heat recovery"
- Status: SUCCESS
- Iterations: 1
- Output: `example2_complete_fixed_1.idf`

### Test 2: Example3 Config Load ✅
- Loaded 5 requests from config file
- Interactive menu displayed correctly
- Ready for user selection

## Future Enhancements

### Option 1: Requirement Extraction
- Use LLM to extract structured requirements from user request
- Map requirements to specific field values
- More precise control over generated system

### Option 2: Two-Stage Generation
- Stage 1: High-level design from user request
- Stage 2: Convert design to IDF format
- Separates design thinking from code generation

### Option 3: Template Library
- Support multiple HVAC system types (VAV, DOAS, etc.)
- Auto-select template based on user request
- More flexible system generation

## Conclusion

**Approach A** successfully merges user's natural language design requests with technical EnergyPlus templates, providing:

- ✅ **User-friendly interface** - Natural language input
- ✅ **Technical precision** - Exact IDF format maintained
- ✅ **Intelligent mapping** - LLM interprets intent
- ✅ **Flexible configuration** - Easy to add new requests
- ✅ **Production ready** - Tested and working

The system is now ready for end users to specify HVAC design requirements in natural language while maintaining strict EnergyPlus format compliance.

# Quick Start Guide - User Request System

## What Was Implemented?

**Approach A: Prefix User Request** - Merges user's natural language design request with technical EnergyPlus template.

## Three Ways to Use It

### 1. **Example 2: Direct Code** (Simple)
```bash
cd examples
python example2_complete_pipeline.py
```

**Edit the script to change request:**
```python
user_request = "Design a VRF system with heat recovery"
```

### 2. **Example 3: Config File** (Recommended)
```bash
cd examples
python example3_config_based.py
```

**Interactive menu:**
```
Your choice: vrf_heat_recovery
```

**Or batch mode:**
```
Your choice: all
```

### 3. **Programmatic** (Advanced)
```python
from src.pipeline import HVACLLMPipeline

pipeline = HVACLLMPipeline()
result = pipeline.run(
    base_idf="../data/base_idfs/building_with_zones.idf",
    zones=["ZONE ONE"],
    output_name="my_vrf",
    user_request="Design a high-efficiency VRF system"
)
```

## Add Your Own Requests

**Edit:** `config/hvac_requests.json`

```json
{
  "my_custom_request": {
    "prompt": "Your natural language request here",
    "zones": ["ZONE ONE"],
    "base_idf": "../data/base_idfs/building_with_zones.idf"
  }
}
```

**Run:**
```bash
python examples/example3_config_based.py
# Choose: my_custom_request
```

## How It Works

```
User Request (Natural Language)
    ↓
    "Design VRF with heat recovery"
    ↓
Combined with Technical Template
    ↓
    "USER REQUEST: Design VRF with heat recovery
     TECHNICAL SPEC: Generate VRF for ZONE ONE...
       - Field 17: Heat_Pump_Waste_Heat_Recovery
       - 32 fields exact format"
    ↓
Sent to LLM
    ↓
IDF Generated (with heat recovery enabled)
```

## Example Requests in Config

1. **vrf_single_zone** - Basic VRF system
2. **vrf_heat_recovery** - VRF with heat recovery
3. **vrf_high_efficiency** - High-efficiency VRF
4. **vrf_cold_climate** - Optimized for cold climates
5. **vrf_multi_zone_office** - Multi-zone control

## Testing

**Test Example 2:**
```bash
cd examples
python example2_complete_pipeline.py
```

**Expected output:**
```
User Request: Design a VRF HVAC system with heat recovery...
SUCCESS
Iterations: 1
Final IDF: ../outputs/generated_idfs/example2_complete_fixed_1.idf
```

**Test Example 3:**
```bash
cd examples
python example3_config_based.py
# Choose: vrf_heat_recovery
```

**Expected output:**
```
Processing Request: vrf_heat_recovery
User Prompt: Design a VRF system with heat recovery...
SUCCESS
```

## Key Files

- **Agent:** `src/agents/agent1_generator.py` - Merges prompts
- **Pipeline:** `src/pipeline.py` - Passes user request through
- **Example2:** `examples/example2_complete_pipeline.py` - Direct usage
- **Example3:** `examples/example3_config_based.py` - Config-based usage
- **Config:** `config/hvac_requests.json` - User request definitions
- **Template:** `src/agents/energyplus_vrf_prompt.json` - Technical template

## What Changed?

### Before (Old Way)
```python
# No user input - fixed template only
pipeline.run(base_idf=idf, zones=zones)
```

### After (New Way - Approach A)
```python
# User request merged with template
pipeline.run(
    base_idf=idf, 
    zones=zones,
    user_request="Design a VRF system with heat recovery"  # NEW!
)
```

## Benefits

✅ **User-friendly** - Write requests in natural language  
✅ **Flexible** - Easy to add new requests in config file  
✅ **Precise** - Technical format automatically maintained  
✅ **Intelligent** - LLM interprets design intent  
✅ **Production-ready** - Tested and working  

## Documentation

- Full details: `docs/USER_REQUEST_MERGING.md`
- This guide: `docs/QUICK_START_USER_REQUESTS.md`

## Need Help?

1. Check `config/hvac_requests.json` for examples
2. Read `docs/USER_REQUEST_MERGING.md` for architecture
3. Look at `examples/example2_complete_pipeline.py` for code samples

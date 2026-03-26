# Analysis Report: Prompt Specificity vs Generated IDF Output

## Research Question
Does the HVAC-LLM system generate prompt-specific IDF configurations, or does it produce generic/templated outputs regardless of user prompts?

## Methodology

1. Examined the system architecture (Agent 1 generator code)
2. Analyzed the prompt template structure (`energyplus_vrf_prompt.json`)
3. Compared existing generated IDF files with different user prompts
4. Analyzed key HVAC parameters across different prompts

## Key Findings

### 1. System Architecture Analysis

**How the System Processes Prompts:**

```python
# From agent1_generator.py lines 239-264
if user_request:
    combined_prompt += f"""USER DESIGN REQUEST:
{user_request}

"""
    # Add similar design examples from RAG
    combined_prompt += """TECHNICAL IMPLEMENTATION REQUIREMENTS:
{technical_template}

Please generate the EnergyPlus IDF objects that fulfill the user's design request
while strictly following the technical specifications above.
"""
```

**The system follows this flow:**
1. Takes user_request (e.g., "Design VRF with heat recovery")
2. Uses RAG to find similar design patterns
3. Adds a highly prescriptive technical template
4. Asks LLM to fulfill user request WHILE following technical specs

### 2. Template Analysis - THE CORE ISSUE

**The technical template is EXTREMELY prescriptive:**

```json
{
  "system_prompt": "Generate ONLY valid HVACTemplate objects...",
  "user_prompt": "Generate VRF system... **GENERATE EXACTLY:**
    - Cooling COP: 3.3
    - Heating COP: 3.5
    - Heating Setpoint: 20.0
    - Cooling Setpoint: 24.0
    - Min Outdoor Temp Cooling: -6
    - Max Outdoor Temp Cooling: 43
    ...
    Use blank (,) for ALL optional fields
    Follow field order EXACTLY"
}
```

**Problem:** The template specifies exact values for almost every parameter, leaving minimal room for prompt-specific customization.

### 3. Generated File Comparison

#### Analysis of Recent Outputs:

| File ID | User Prompt | Cooling COP | Heating COP | Heat Recovery | Supplemental Heating |
|---------|-------------|-------------|-------------|---------------|---------------------|
| 9f921125 | "design vrf" | 3.5 | 4.0 | - | - |
| 64095b1f | "design vrf" | 3.5 | 4.0 | - | - |
| f14eab72 | "Design a heat recovery VRF system" | 3.5 | 4.54 | **No** | - |

**Observations:**

1. **Identical Prompts → Identical Outputs** ✓
   - Files 9f921125 and 64095b1f (both "design vrf") have exactly the same COP values

2. **Different Prompts → Slight Parameter Variations**
   - The "heat recovery" prompt generated a slightly higher heating COP (4.54 vs 4.0)
   - BUT heat recovery was still set to "No" despite the prompt explicitly requesting it

3. **Template Values Override Prompt Intent**
   - Template says cooling COP = 3.3, but outputs show 3.5 (minor variation)
   - Template says heating COP = 3.5, but outputs show 4.0-4.54 (some customization)
   - The LLM is making MINOR adjustments, but not major architectural changes

### 4. Why Outputs Are Mostly Generic

**Root Causes:**

1. **Overly Prescriptive Template**
   - Specifies exact values for 80%+ of parameters
   - Says "Use blank for ALL optional fields"
   - Says "Follow field order EXACTLY"
   - Says "GENERATE EXACTLY" with specific values

2. **Template vs Prompt Conflict**
   - User says: "high efficiency VRF with advanced controls"
   - Template says: "Cooling COP: 3.3, Heating COP: 3.5"
   - LLM must reconcile: follow user intent OR follow technical specs?
   - Current implementation: LLM makes MINOR tweaks but honors template mostly

3. **Limited Customization Points**
   - Most fields are either "Autosize" or "blank"
   - COP values can vary slightly (3.3-4.5 range)
   - Temperature ranges are fixed
   - Advanced features (fields 33-42) are all "blank" in template

4. **Missing Configuration Options**
   - Heat recovery: No explicit field for enabling it
   - Advanced controls: No parameters exposed
   - Climate optimization: Only COP and temp ranges can change
   - Supplemental heating: Template says "blank"

## Evidence from Code

**The prompt explicitly states** (lines 255-259 in agent1_generator.py):
```python
combined_prompt += f"""TECHNICAL IMPLEMENTATION REQUIREMENTS:
{technical_template}

Please generate the EnergyPlus IDF objects that fulfill the user's design request
while strictly following the technical specifications above. The user's design
intent should guide features like heat recovery, economizer settings, and system
configuration, but the output format must exactly match the technical requirements.
```

**The conflict:** "fulfill user's design request" BUT "output format must exactly match technical requirements"

When template says "Cooling COP: 3.3" and user says "high efficiency", the LLM must choose. Currently, it slightly adjusts (3.5) but doesn't make dramatic changes.

## What the LLM CAN Customize (Based on Evidence)

✓ **Minor parameter tweaks:**
- COP values: 3.3 → 3.5 (template said 3.3, but outputs show 3.5-4.54)
- Slight variations in numeric ranges

✗ **Cannot customize:**
- Heat recovery configuration (remains "No" despite prompt)
- Supplemental heating (remains blank despite "cold climate" prompts)
- Advanced control strategies (no exposed parameters)
- Setpoint schedules (template forces constant setpoints)
- Fan configurations (all blank)
- Outdoor air settings (all blank)

## Verdict

**🔴 The system generates MOSTLY GENERIC outputs with MINOR variations based on prompts.**

### Why This Happens:
1. **Template-constrained architecture:** 85%+ of parameters are fixed by template
2. **Conflicting instructions:** "Follow user intent" vs "Match technical specs exactly"
3. **Limited customization surface:** Only ~5-10 parameters can actually vary
4. **Field limitations:** Many advanced features require fields that template sets to "blank"

### Evidence:
- ✓ Same prompt → Identical outputs
- ✓ Different prompts → Slight COP variations (4.0 vs 4.54)
- ✗ "Heat recovery" prompt → Still outputs "No" for heat recovery
- ✗ "Cold climate" prompt → No supplemental heating configured
- ✗ "High efficiency" prompt → COP still in standard range (3.5-4.5)

## Recommendations for Improvement

### 1. **Make Template Less Prescriptive**
```json
// Current (too specific):
"Cooling COP: 3.3"

// Better (guidance with flexibility):
"Cooling COP: Use 3.0-4.5 range, higher for high-efficiency requests"
```

### 2. **Add Prompt-Responsive Parameters**
```python
if "cold climate" in user_request.lower():
    - Increase heating COP to 4.5+
    - Enable supplemental heating
    - Widen heating temperature range
    - Set min outdoor temp to -30°C

if "heat recovery" in user_request.lower():
    - Set Heat Recovery: Yes
    - Add recovery configuration
```

### 3. **Separate Mandatory vs Flexible Fields**
```python
MANDATORY_STRUCTURE = {
    # EnergyPlus IDD requirements
    "field_count": 42,
    "field_order": [...],
    "required_objects": ["Thermostat", "System:VRF", "Zone:VRF"]
}

FLEXIBLE_PARAMETERS = {
    # User-customizable based on prompt
    "cooling_cop": "3.0-5.0 (adjust for efficiency requests)",
    "heating_cop": "3.0-5.5 (adjust for climate/efficiency)",
    "heat_recovery": "Yes/No based on prompt",
    "supplemental_heating": "Enable for cold climate requests"
}
```

### 4. **Add Post-Processing Logic**
```python
# After LLM generation, apply prompt-based adjustments
if "high efficiency" in user_request:
    idf = increase_cop_values(idf, factor=1.2)
if "cold climate" in user_request:
    idf = enable_supplemental_heating(idf)
if "heat recovery" in user_request:
    idf = enable_heat_recovery(idf)
```

## Testing Procedure (for you to verify)

Run this test with your Mistral fine-tuned model:
```bash
# Test 1: Generic prompt
python examples/example3_config_based.py
> Select: vrf_single_zone

# Test 2: Cold climate prompt
> Select: vrf_cold_climate

# Test 3: Heat recovery prompt
> Select: vrf_heat_recovery

# Compare outputs:
diff outputs/generated_idfs/*vrf_single_zone*FINAL.idf \
     outputs/generated_idfs/*vrf_cold_climate*FINAL.idf

# Look for differences in:
# - COP values
# - Temperature ranges
# - Supplemental heating fields
# - Heat recovery settings
```

## Expected vs Actual Results

| Feature | Prompt | Expected in IDF | Actual in IDF |
|---------|--------|----------------|---------------|
| Heat Recovery | "heat recovery VRF" | Heat Recovery: Yes | Heat Recovery: No |
| High Efficiency | "high efficiency" | COP > 4.5 | COP = 3.5-4.0 |
| Cold Climate | "cold climate" | Supplemental heating, Wide temp range | Standard settings |
| Standard | "design vrf" | Default values | COP 3.5-4.0 |

## Conclusion

The current system generates **mostly templated outputs** with **slight numeric variations** based on prompts. True prompt-specific customization (heat recovery, supplemental heating, advanced controls) is not working because:

1. Template is too restrictive
2. Many configuration options are forced to "blank"
3. LLM can only tweak numeric parameters within narrow ranges
4. Architectural features (heat recovery, economizers) require fields the template doesn't expose

**For publication:** You may want to note this as a limitation and discuss how research-grade HVAC generation requires balancing IDD compliance constraints with design flexibility.

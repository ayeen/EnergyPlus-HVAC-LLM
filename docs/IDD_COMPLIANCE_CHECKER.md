# IDD Compliance Checker

## Overview

The HVAC-LLM pipeline now includes an **IDD Compliance Checker** that automatically validates base IDF files against EnergyPlus Input Data Dictionary (IDD) rules before HVAC generation.

This feature helps catch common IDF issues early, preventing simulation failures and reducing error correction iterations.

## Features

### 1. Automatic Compliance Checking
The pipeline automatically checks base IDF files for:

- **Zone objects**: Validates Type field (max value is 1)
- **People objects**: Ensures calculation method is specified
- **Lights objects**: Ensures calculation method is specified  
- **ElectricEquipment objects**: Ensures calculation method is specified
- **SimulationControl**: Checks if present (required for sizing)
- **SizingPeriod:DesignDay**: Checks if present (required for HVAC sizing)
- **BuildingSurface:Detailed**: Warns if no geometry defined
- **RunPeriod**: Validates month values (1-12)

### 2. Auto-Fix Capability
When `auto_fix_compliance=True` (default), the checker automatically fixes:

- Zone Type values > 1 → set to 1
- Missing calculation methods → adds appropriate defaults
- Missing SimulationControl → adds with sizing enabled
- Missing design days → adds Chicago winter/summer defaults
- Invalid RunPeriod months → corrects to valid range

### 3. Detailed Reporting
Generates clear compliance reports showing:
- Each issue with object name, field, and description
- Severity level (error vs warning)
- What fixes were applied

## Usage

### In Pipeline (Default Behavior)

```python
from src.pipeline import HVACLLMPipeline

pipeline = HVACLLMPipeline()

# Default: check compliance and auto-fix issues
result = pipeline.run(
    base_idf='path/to/building.idf',
    output_name='my_output'
)

# Disable auto-fix (fail on compliance issues)
result = pipeline.run(
    base_idf='path/to/building.idf',
    output_name='my_output',
    auto_fix_compliance=False
)

# Disable compliance checking entirely
result = pipeline.run(
    base_idf='path/to/building.idf',
    output_name='my_output',
    check_idd_compliance=False
)
```

### Standalone Usage

```python
from src.core.idf_handler import IDFHandler

handler = IDFHandler()
idf = handler.load('path/to/building.idf')

# Check compliance (without fixing)
result = handler.check_idd_compliance(idf, auto_fix=False)
handler.print_compliance_report(result)

# Check and auto-fix
result = handler.check_idd_compliance(idf, auto_fix=True)

# Save fixed IDF
if result['fixes_applied']:
    idf.saveas('path/to/building_fixed.idf')
```

### Command Line

```bash
# Check any IDF file
python test_idd_compliance.py path/to/building.idf

# Check and auto-fix (saves to *_auto_fixed.idf)
python test_idd_compliance.py path/to/building.idf --fix
```

## Return Value

The `check_idd_compliance()` method returns a dictionary:

```python
{
    'compliant': bool,          # True if no errors (or all fixed)
    'issues': [                 # List of detected issues
        {
            'object': str,      # e.g., "Zone: Zone1"
            'field': str,       # e.g., "Type"
            'issue': str,       # Description
            'severity': str,    # 'error' or 'warning'
            'fix_applied': bool # True if auto-fixed
        }
    ],
    'warnings': [str],          # General warnings
    'fixes_applied': [str],     # List of fix descriptions
    'summary': str              # Human-readable summary
}
```

## Common Issues Detected

| Object | Field | Issue | Auto-Fix |
|--------|-------|-------|----------|
| Zone | Type | Value > 1 (IDD max is 1) | Set to 1 |
| People | Number_of_People_Calculation_Method | Missing | Set to 'People' |
| Lights | Design_Level_Calculation_Method | Missing | Set to 'LightingLevel' |
| ElectricEquipment | Design_Level_Calculation_Method | Missing | Set to 'EquipmentLevel' |
| SimulationControl | N/A | Missing object | Add with sizing enabled |
| SizingPeriod:DesignDay | N/A | No design days | Add Chicago defaults |
| RunPeriod | Begin/End_Month | Invalid (not 1-12) | Correct to 1 or 12 |

## Example Output

```
============================================================
IDD COMPLIANCE REPORT
============================================================

❌ IDF has 3 error(s) and 0 warning(s). Fix before simulation.
🔧 Auto-fixed 3 issue(s).

------------------------------------------------------------
ISSUES FOUND:
------------------------------------------------------------

1. [✅ FIXED] Zone: Zone1
   Field: Type
   Issue: Zone Type = 5, but IDD maximum is 1

2. [✅ FIXED] SimulationControl
   Field: N/A
   Issue: Missing SimulationControl object (required for sizing)

3. [✅ FIXED] SizingPeriod:DesignDay
   Field: N/A
   Issue: No design days found (required for HVAC sizing)

------------------------------------------------------------
FIXES APPLIED:
------------------------------------------------------------
  🔧 Fixed Zone 'Zone1' Type: 5 → 1
  🔧 Added SimulationControl object with sizing enabled
  🔧 Added default design days (Chicago winter/summer)

============================================================
```

## Integration with Pipeline

When the pipeline runs with compliance checking:

1. **Step 0.1**: Loads base IDF and runs compliance check
2. If `auto_fix_compliance=True`:
   - Fixes are applied to the in-memory IDF object
   - Pipeline continues with the fixed IDF
   - Fixes are logged in the results
3. If `auto_fix_compliance=False` and issues exist:
   - Pipeline stops with `IDD_COMPLIANCE_FAILED` status
   - Full compliance report is printed
   - User must fix issues manually or enable auto-fix

## Best Practices

1. **Always use compliant base IDFs** - While auto-fix handles common issues, starting with a properly formatted IDF is best.

2. **Review auto-fixes** - The auto-fix uses sensible defaults, but review them for your specific project needs.

3. **Create a fixed copy** - If your base IDF has persistent issues, fix it once and save the corrected version.

4. **Use the standalone checker** - For debugging, run `test_idd_compliance.py` to see exactly what issues exist in a file.

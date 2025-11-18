# Which IDF File to Use? - Complete Guide

## The Problem You Encountered

You ran the HVAC-LLM pipeline, it reported **SUCCESS**, but when you opened the generated IDF in EP-Launch, you got:

```
** Severe  ** AirConditioner:VariableRefrigerantFlow = "VRF_SYSTEM_1 VRF HEAT PUMP"
**   ~~~   ** Zone Name for Master Thermostat Location must be entered...
**  Fatal  ** GetVRFInput: Errors found...
```

**Why?** You opened the **wrong file**! ❌

## Understanding the Pipeline Output Files

The pipeline creates **multiple IDF files** during the correction process:

### File Naming Convention:

```
outputs/generated_idfs/
├── {output_name}_hvac.idf          ← Initial generation (may have errors)
├── {output_name}_fixed_1.idf       ← After correction iteration 1
├── {output_name}_fixed_2.idf       ← After correction iteration 2
├── {output_name}_fixed_3.idf       ← After correction iteration 3
└── {output_name}_FINAL.idf         ← ALWAYS USE THIS! ✅
```

### Example for `vrf_single_zone`:

```
vrf_single_zone_hvac.idf       ← ❌ DON'T USE (missing Master Thermostat)
vrf_single_zone_fixed_1.idf    ← ✅ CORRECTED (Master Thermostat added)
vrf_single_zone_FINAL.idf      ← ✅ COPY OF FINAL CORRECTED FILE
```

## Which File to Use in EP-Launch? 🎯

### ✅ ALWAYS USE: `*_FINAL.idf`

```
D:\Ayeen\Project\HVAC-LLM\outputs\generated_idfs\vrf_single_zone_FINAL.idf
```

This file:
- ✅ Has ALL corrections applied
- ✅ Passed simulation successfully
- ✅ Ready for EP-Launch
- ✅ Consistent name (easy to find)

### ❌ DON'T USE: `*_hvac.idf`

This is the **raw generation** before error correction. It likely has errors!

## How to Find the Correct File

### Method 1: Look for `*_FINAL.idf` (NEW!)

The pipeline now automatically copies the final corrected file to:

```
outputs/generated_idfs/{output_name}_FINAL.idf
```

Just search for files ending in `_FINAL.idf`!

### Method 2: Check the Results JSON

```json
{
  "final_status": "SUCCESS",
  "final_idf": "D:\\Ayeen\\Project\\HVAC-LLM\\outputs\\generated_idfs\\vrf_single_zone_fixed_1.idf",
  "total_iterations": 1
}
```

The `final_idf` field tells you which file passed simulation.

### Method 3: Look at Pipeline Output

```
🎉 SUCCESS! Use this file:
   D:\Ayeen\Project\HVAC-LLM\outputs\generated_idfs\vrf_single_zone_FINAL.idf
```

The pipeline now prints the exact file to use!

## Pipeline Process Explained

```
┌─────────────────────────────────────────────────────────────┐
│ Step 1: Agent 1 Generates HVAC                              │
│ Output: vrf_single_zone_hvac.idf                            │
│ Status: May have errors (Master Thermostat missing)         │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 2: Validate IDF Structure                              │
│ Status: Valid ✓ (structure is correct)                      │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 3: Simulate with EnergyPlus                            │
│ Status: FAILED ✗                                            │
│ Error: "Zone Name for Master Thermostat Location must..."   │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 4: Agent 3 Analyzes Errors                             │
│ Detected: Master Thermostat Location missing                │
│ Generated Fix: Set to "ZONE ONE"                            │
│ Applied Fix: vrf_single_zone_fixed_1.idf                    │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 5: Re-simulate                                         │
│ Status: SUCCESS ✓                                           │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 6: Copy to Final                                       │
│ Output: vrf_single_zone_FINAL.idf                           │
│ Status: Ready for EP-Launch ✓                               │
└─────────────────────────────────────────────────────────────┘
```

## Common Mistakes

### ❌ Mistake 1: Using `*_hvac.idf`

```
You: *opens vrf_single_zone_hvac.idf in EP-Launch*
EP-Launch: FATAL ERROR - Master Thermostat missing!
You: "But the pipeline said SUCCESS?!"
```

**Fix:** Use `vrf_single_zone_FINAL.idf` instead!

### ❌ Mistake 2: Using Old File After Re-run

```
Run 1: Creates vrf_single_zone_fixed_1.idf ✓
Run 2: Creates vrf_single_zone_fixed_1.idf ✓ (overwrites)
You: *opens the old file still open in EP-Launch*
EP-Launch: Same old errors!
```

**Fix:** Close and reopen the file, or check file timestamp!

### ❌ Mistake 3: Not Checking Pipeline Status

```
Pipeline Output: "FAILED after 6 iterations"
You: *opens any of the fixed files*
EP-Launch: Still has errors!
```

**Fix:** Only use files from **successful** pipeline runs!

## Quick Reference

| File Type | Use Case | Status |
|-----------|----------|--------|
| `*_hvac.idf` | Initial generation | ❌ May have errors |
| `*_fixed_1.idf` | After 1 correction | ⚠️ May still have errors |
| `*_fixed_2.idf` | After 2 corrections | ⚠️ May still have errors |
| `*_fixed_N.idf` | After N corrections | ⚠️ Check if final |
| **`*_FINAL.idf`** | **Final corrected** | **✅ ALWAYS USE THIS** |

## Updated Pipeline Behavior (NEW!)

The pipeline now:

1. ✅ **Automatically copies** the final corrected file to `*_FINAL.idf`
2. ✅ **Prints clear message** showing which file to use
3. ✅ **Consistent naming** - easy to identify correct file

### Pipeline Output (New):

```
======================================================================
PIPELINE COMPLETE: SUCCESS
Results saved: D:\...\logs\vrf_single_zone_results.json

🎉 SUCCESS! Use this file:
   D:\Ayeen\Project\HVAC-LLM\outputs\generated_idfs\vrf_single_zone_FINAL.idf
======================================================================
```

## For Your Specific Case

### What Happened:

1. Pipeline ran successfully with 1 correction iteration
2. Created `vrf_single_zone_hvac.idf` (initial, **has error**)
3. Detected Master Thermostat error
4. Created `vrf_single_zone_fixed_1.idf` (corrected, **works!**)
5. You opened `vrf_single_zone_hvac.idf` in EP-Launch (**wrong file!**)

### Solution:

Open this file in EP-Launch:

```
D:\Ayeen\Project\HVAC-LLM\outputs\generated_idfs\vrf_single_zone_FINAL.idf
```

or

```
D:\Ayeen\Project\HVAC-LLM\outputs\generated_idfs\vrf_single_zone_fixed_1.idf
```

Both are the same (the `_FINAL.idf` is a copy of `_fixed_1.idf`).

## Summary

**Golden Rule:** 🌟

```
When pipeline says "SUCCESS", 
ALWAYS use the file ending in "_FINAL.idf"
```

This file:
- Has all corrections applied
- Passed EnergyPlus simulation
- Is ready for analysis in EP-Launch
- Will simulate successfully without errors

**Never use** `*_hvac.idf` directly - it's the raw generation before error correction!

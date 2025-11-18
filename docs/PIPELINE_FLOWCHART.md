# HVAC-LLM Pipeline Flowchart

## Complete System Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         HVAC-LLM PIPELINE                           │
│                     Multi-Agent Architecture                         │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                            INPUT PHASE                               │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │   User Inputs:          │
                    │   • Base IDF File       │
                    │   • Zone Names          │
                    │   • User Request (NL)   │
                    │   • System Name         │
                    │   • Validation Flag     │
                    └───────────┬─────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    STEP 1: HVAC GENERATION                          │
│                       (Agent 1)                                      │
└─────────────────────────────────────────────────────────────────────┘
                                │
                    ┌───────────┴───────────┐
                    │  HVACGenerator        │
                    │  • Load template      │
                    │  • Merge user request │
                    │  • Call LLM           │
                    │  • Generate objects   │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌─────────────────────────┐
                    │ Generated HVAC Objects: │
                    │ • HVACTemplate:System   │
                    │ • HVACTemplate:Zone     │
                    │ • Thermostat            │
                    │ • Schedules             │
                    └───────────┬─────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│              STEP 1.5: QUICK LLM VALIDATION                         │
│                    (Agent 1.5 - Optional)                            │
└─────────────────────────────────────────────────────────────────────┘
                                │
                    ┌───────────┴───────────┐
                    │ Quick Validation      │
                    │ Enabled?              │
                    └───────────┬───────────┘
                                │
                ┌───────────────┼───────────────┐
                │               │               │
                ▼               ▼               ▼
            ┌───────┐      ┌────────┐      ┌────────┐
            │  Yes  │      │   No   │      │ Skip   │
            └───┬───┘      └────┬───┘      └───┬────┘
                │               │               │
                ▼               │               │
    ┌───────────────────┐      │               │
    │ QuickValidator    │      │               │
    │ • Zone count      │      │               │
    │ • Thermostat      │      │               │
    │ • Field ranges    │      │               │
    │ • Completeness    │      │               │
    └───────┬───────────┘      │               │
            │                  │               │
            ▼                  │               │
    ┌───────────┐             │               │
    │  Valid?   │             │               │
    └───┬───────┘             │               │
        │                     │               │
    ┌───┴───┐                 │               │
    │       │                 │               │
    ▼       ▼                 │               │
┌──────┐ ┌──────┐            │               │
│ Yes  │ │  No  │            │               │
└──┬───┘ └──┬───┘            │               │
   │        │                │               │
   │        ▼                │               │
   │   ┌─────────────────┐  │               │
   │   │ Step 1.5b:      │  │               │
   │   │ Quick Fix       │  │               │
   │   │ • Use Corrector │  │               │
   │   │ • Apply fixes   │  │               │
   │   │ • Re-validate   │  │               │
   │   └────────┬────────┘  │               │
   │            │            │               │
   └────────────┼────────────┴───────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────────────┐
│              STEP 1.6: COMBINE BASE + HVAC                          │
└─────────────────────────────────────────────────────────────────────┘
                                │
                    ┌───────────┴───────────┐
                    │ • Read base IDF       │
                    │ • Add HVAC header     │
                    │ • Append HVAC objects │
                    │ • Save complete IDF   │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌─────────────────────────┐
                    │  Complete IDF File:     │
                    │  {output_name}_hvac.idf │
                    └───────────┬─────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│              STEP 2: EPPY IDF VALIDATION                            │
│                   (Syntax Checking)                                  │
└─────────────────────────────────────────────────────────────────────┘
                                │
                    ┌───────────┴───────────┐
                    │  IDFValidator         │
                    │  • Parse IDF syntax   │
                    │  • Check object types │
                    │  • Validate fields    │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌─────────────────────────┐
                    │  Validation Report:     │
                    │  • is_valid: True/False │
                    │  • errors: [...]        │
                    └───────────┬─────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│           STEP 2.5: PRE-SIMULATION AUTO-FIX                         │
│                    (Agent 3 - Corrector)                             │
└─────────────────────────────────────────────────────────────────────┘
                                │
                    ┌───────────┴───────────┐
                    │ Validation Failed?    │
                    │ (errors > 0)          │
                    └───────────┬───────────┘
                                │
                ┌───────────────┼───────────────┐
                │               │               │
                ▼               ▼               ▼
            ┌───────┐      ┌────────┐      ┌────────┐
            │  Yes  │      │   No   │      │ Valid  │
            └───┬───┘      └────┬───┘      └───┬────┘
                │               │               │
                ▼               │               │
    ┌───────────────────┐      │               │
    │ ErrorCorrector    │      │               │
    │ • Analyze errors  │      │               │
    │ • Generate fixes  │      │               │
    │ • Apply fixes     │      │               │
    └───────┬───────────┘      │               │
            │                  │               │
            ▼                  │               │
    ┌───────────────────┐     │               │
    │ Fixes applied?    │     │               │
    └───────┬───────────┘     │               │
            │                 │               │
        ┌───┴───┐             │               │
        │       │             │               │
        ▼       ▼             │               │
    ┌──────┐ ┌──────┐        │               │
    │ Yes  │ │  No  │        │               │
    └──┬───┘ └──┬───┘        │               │
       │        │             │               │
       │        ▼             │               │
       │   ┌─────────────┐   │               │
       │   │  STOP       │   │               │
       │   │  Return:    │   │               │
       │   │  FAILED     │   │               │
       │   └─────────────┘   │               │
       │                     │               │
       ▼                     │               │
    ┌─────────────────┐     │               │
    │ Step 2.6:       │     │               │
    │ Re-Validate     │     │               │
    └────────┬────────┘     │               │
             │               │               │
             ▼               │               │
    ┌─────────────────┐     │               │
    │ Valid now?      │     │               │
    └────────┬────────┘     │               │
             │               │               │
         ┌───┴───┐           │               │
         │       │           │               │
         ▼       ▼           │               │
     ┌──────┐ ┌──────┐      │               │
     │ Yes  │ │  No  │      │               │
     └──┬───┘ └──┬───┘      │               │
        │        │           │               │
        │        ▼           │               │
        │   ┌────────────┐  │               │
        │   │ Errors     │  │               │
        │   │ reduced?   │  │               │
        │   └─────┬──────┘  │               │
        │         │          │               │
        │     ┌───┴───┐      │               │
        │     │       │      │               │
        │     ▼       ▼      │               │
        │  ┌─────┐ ┌─────┐  │               │
        │  │ Yes │ │ No  │  │               │
        │  └──┬──┘ └──┬──┘  │               │
        │     │       │      │               │
        │     │       ▼      │               │
        │     │   ┌───────┐ │               │
        │     │   │ STOP  │ │               │
        │     │   │ FAILED│ │               │
        │     │   └───────┘ │               │
        │     │             │               │
        └─────┼─────────────┴───────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────────┐
│            STEP 3: ENERGYPLUS SIMULATION                            │
│                  (Physics Validation)                                │
└─────────────────────────────────────────────────────────────────────┘
                                │
                    ┌───────────┴───────────┐
                    │ EnergyPlusSimulator   │
                    │ • Run EnergyPlus exe  │
                    │ • Parse .err file     │
                    │ • Extract errors      │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌─────────────────────────┐
                    │  Simulation Result:     │
                    │  • success: True/False  │
                    │  • error_count: N       │
                    │  • severe_errors: [..] │
                    │  • fatal_errors: [...]  │
                    └───────────┬─────────────┘
                                │
                                ▼
                    ┌─────────────────────────┐
                    │  Simulation Success?    │
                    └───────────┬─────────────┘
                                │
                ┌───────────────┼───────────────┐
                │               │               │
                ▼               ▼               ▼
            ┌───────┐      ┌────────┐      ┌────────┐
            │  Yes  │      │   No   │      │ Errors │
            └───┬───┘      └────┬───┘      └───┬────┘
                │               │               │
                ▼               │               │
    ┌───────────────────┐      │               │
    │                   │      │               │
    │   SUCCESS! ✅     │      │               │
    │                   │      │               │
    │ • Copy to FINAL   │      │               │
    │ • Save results    │      │               │
    │ • Return SUCCESS  │      │               │
    │                   │      │               │
    └───────────────────┘      │               │
                               │               │
                               └───────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│         STEP 4: ITERATIVE ERROR CORRECTION LOOP                     │
│                    (Agent 3 - Corrector)                             │
│                  (Max 3 iterations)                                  │
└─────────────────────────────────────────────────────────────────────┘
                                       │
                          ┌────────────┴────────────┐
                          │ Iteration = 1           │
                          │ Max = 3                 │
                          └────────────┬────────────┘
                                       │
                    ┌──────────────────┴──────────────────┐
                    │                                     │
                    ▼                                     │
        ┌───────────────────────┐                       │
        │ Step 4.{n}:           │                       │
        │ ErrorCorrector        │                       │
        │                       │                       │
        │ • Parse error blocks  │                       │
        │ • Analyze with LLM    │                       │
        │ • Generate fixes      │                       │
        │ • Apply fixes to IDF  │                       │
        └───────────┬───────────┘                       │
                    │                                     │
                    ▼                                     │
        ┌───────────────────────┐                       │
        │ Fixes Applied         │                       │
        │ Save to:              │                       │
        │ {name}_fixed_{n}.idf  │                       │
        └───────────┬───────────┘                       │
                    │                                     │
                    ▼                                     │
┌─────────────────────────────────────────────────────────────────────┐
│            STEP 5: RE-SIMULATION                                    │
└─────────────────────────────────────────────────────────────────────┘
                    │                                     │
        ┌───────────┴───────────┐                       │
        │ Step 5.{n}:           │                       │
        │ Re-run EnergyPlus     │                       │
        │ on fixed IDF          │                       │
        └───────────┬───────────┘                       │
                    │                                     │
                    ▼                                     │
        ┌───────────────────────┐                       │
        │ Simulation Success?   │                       │
        └───────────┬───────────┘                       │
                    │                                     │
            ┌───────┴───────┐                           │
            │               │                           │
            ▼               ▼                           │
        ┌───────┐      ┌────────┐                      │
        │  Yes  │      │   No   │                      │
        └───┬───┘      └────┬───┘                      │
            │               │                           │
            ▼               ▼                           │
    ┌───────────┐  ┌─────────────────┐                │
    │  SUCCESS  │  │ Iteration < 3?  │                │
    │           │  └────────┬─────────┘                │
    │ Copy to   │           │                          │
    │ FINAL.idf │       ┌───┴───┐                      │
    │           │       │       │                      │
    │ Return    │       ▼       ▼                      │
    │ SUCCESS   │   ┌─────┐ ┌─────┐                    │
    │           │   │ Yes │ │ No  │                    │
    └───────────┘   └──┬──┘ └──┬──┘                    │
                       │       │                        │
                       │       ▼                        │
                       │   ┌─────────────┐              │
                       │   │  FAILED     │              │
                       │   │  Return     │              │
                       │   │  Max iter   │              │
                       │   │  reached    │              │
                       │   └─────────────┘              │
                       │                                │
                       ▼                                │
                 ┌──────────┐                          │
                 │iteration+│                          │
                 │    +1    │                          │
                 └─────┬────┘                          │
                       │                                │
                       └────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        OUTPUT PHASE                                 │
└─────────────────────────────────────────────────────────────────────┘
                                       │
                          ┌────────────┴────────────┐
                          │ Save Results:           │
                          │ • Final status          │
                          │ • Final IDF path        │
                          │ • Total iterations      │
                          │ • All step details      │
                          │ • Errors (if any)       │
                          └────────────┬────────────┘
                                       │
                                       ▼
                          ┌────────────────────────┐
                          │ Files Generated:       │
                          │                        │
                          │ • {name}_hvac.idf      │
                          │ • {name}_pre_fixed.idf │
                          │ • {name}_fixed_n.idf   │
                          │ • {name}_FINAL.idf ✅  │
                          │ • {name}_results.json  │
                          │ • Simulation outputs   │
                          └────────────┬───────────┘
                                       │
                                       ▼
                          ┌────────────────────────┐
                          │   PIPELINE COMPLETE    │
                          │                        │
                          │ Status: SUCCESS/FAILED │
                          └────────────────────────┘
```

## Legend

### Symbols
- `┌─┐` : Process/Step box
- `▼` : Flow direction
- `├─┤` : Decision branch
- `•` : Sub-item/action
- `✅` : Success indicator
- `❌` : Failure indicator
- `⚠️` : Warning indicator

### Agents
- **Agent 1**: HVACGenerator - Generates HVAC objects using LLM
- **Agent 1.5**: QuickValidator - Pre-simulation LLM validation (optional)
- **Agent 2**: IDFValidator - Eppy-based syntax validation
- **Agent 3**: ErrorCorrector - LLM-based error analysis and fixing

### Key Decision Points
1. **Step 1.5**: Enable/Skip quick validation
2. **Step 1.5b**: Valid after quick validation?
3. **Step 2.5**: Validation errors found?
4. **Step 2.6**: Errors reduced after fix?
5. **Step 3**: Simulation successful?
6. **Step 5.n**: Re-simulation successful? / Max iterations reached?

### Exit Points
- ✅ **SUCCESS**: After Step 3 (first try) or Step 5.n (after corrections)
- ❌ **FAILED**: After Step 2.5 (no fix possible), Step 4 (max iterations), or errors

### File Outputs
- `{name}_hvac.idf` - Initial complete IDF (base + HVAC)
- `{name}_temp.idf` - Temporary for quick validation
- `{name}_temp_fixed.idf` - After quick fix
- `{name}_pre_fixed.idf` - After Step 2.5 fix
- `{name}_fixed_1.idf` - After 1st correction iteration
- `{name}_fixed_2.idf` - After 2nd correction iteration
- `{name}_fixed_3.idf` - After 3rd correction iteration
- `{name}_FINAL.idf` - ✅ Final successful IDF
- `{name}_results.json` - Pipeline execution results

## Pipeline Characteristics

### Self-Healing
- Automatic error detection and correction at multiple stages
- LLM-based intelligent fixes
- Iterative refinement (up to 3 attempts)

### Multi-Layer Validation
1. **Pre-validation** (Step 1.5): Quick LLM checks before simulation
2. **Syntax validation** (Step 2): Eppy structural checks
3. **Physics validation** (Step 3): EnergyPlus simulation

### Fault Tolerance
- Continues with partial fixes if progress is made
- Stops early if no improvement detected
- Saves results at every failure point for debugging

### Efficiency
- Quick validation saves simulation time
- Pre-simulation fixes prevent wasted EnergyPlus runs
- Smart stopping prevents infinite loops

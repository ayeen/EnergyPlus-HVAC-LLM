# Scenario Comparison: Research Methodology

This document explains how to use the scenario comparison script for your research project.

## Overview

Your research involves comparing multiple scenarios for HVAC system generation using LLMs:

| Scenario | Description | LLM | RAG | Status |
|----------|-------------|-----|-----|--------|
| **Scenario 1** | Single LLM (No RAG) | Gemini API | ❌ | ✅ Implemented |
| **Scenario 2** | Pre-trained LLM + RAG | Fine-tuned Mistral 7B | ✅ | ✅ Implemented |
| Scenario 3 | Multiple LLMs without training | Multiple | ❌ | ❌ Not implemented |
| Scenario 3b | Two LLMs + One using Scenario 2 output | Multiple | Partial | ❌ Not implemented |
| Scenario 4 | Multiple pre-trained LLMs + RAG each | Multiple fine-tuned | ✅ | ❌ Not implemented |

### Key Difference Between Scenarios

- **Scenario 1 (Gemini)**: Uses Google's Gemini API as a general-purpose LLM without any domain-specific training or RAG
- **Scenario 2 (Mistral + RAG)**: Uses a fine-tuned Mistral-7B model specifically trained on HVAC/EnergyPlus data, enhanced with RAG for additional context

This comparison helps validate the benefit of domain-specific fine-tuning combined with RAG over general-purpose LLMs.

## Quick Start

### Run a Quick Comparison (2 test cases)

```bash
cd /home/hubel/Documents/Ayeen/EnergyPlus-HVAC-LLM
.venv/bin/python scripts/compare_scenarios.py --quick
```

### Run Full Comparison (all 6 test cases)

```bash
.venv/bin/python scripts/compare_scenarios.py --runs 3
```

### Run Specific Test Cases

```bash
.venv/bin/python scripts/compare_scenarios.py --test-cases single_zone_office retail_store --runs 5
```

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--runs N` | Number of runs per test case | 1 |
| `--quick` | Run only 2 test cases (quick mode) | False |
| `--test-cases` | Specific test cases to run | All |
| `--output DIR` | Output directory for results | `outputs/scenario_comparison` |

## Test Cases

The comparison script includes these test cases:

1. **single_zone_office** - Simple single-zone VRF system
2. **two_zone_building** - Two-zone VRF system
3. **multi_zone_office** - 4-zone office building
4. **residential_home** - 5-zone residential (auto-detect zones)
5. **retail_store** - 3-zone retail (auto-detect zones)
6. **large_office** - 10-zone large office (auto-detect zones)

## Metrics Collected

For each scenario and test case, the script measures:

### Success Metrics
- **Generation Success**: Did the LLM generate valid HVAC objects?
- **Validation Success**: Did the IDF pass EnergyPlus validation?
- **Simulation Success**: Did the EnergyPlus simulation complete successfully?

### Performance Metrics
- **Generation Time**: Time to generate HVAC objects
- **Total Time**: Total pipeline execution time
- **Correction Iterations**: Number of error correction cycles needed

### Quality Metrics
- **HVAC Objects Generated**: Number of HVAC objects created
- **Errors Encountered**: List of errors during generation
- **IDD Issues Found/Fixed**: IDD compliance issues detected and auto-fixed

## Output Files

The script generates:

1. **JSON Results** (`scenario_comparison_YYYYMMDD_HHMMSS.json`)
   - Complete detailed results for all runs
   - Machine-readable format for further analysis

2. **CSV Summary** (`scenario_comparison_YYYYMMDD_HHMMSS.csv`)
   - Tabular format for spreadsheet analysis
   - Easy import into Excel/Google Sheets

3. **Console Summary**
   - Formatted comparison table
   - RAG impact analysis
   - Per-test-case breakdown

## Example Output

```
======================================================================
COMPARISON SUMMARY
======================================================================

┌────────────────────────────────────────────────────────────────────┐
│METRIC                        │        SCENARIO 1│        SCENARIO 2│
│                              │          (No RAG)│        (With RAG)│
├──────────────────────────────┼──────────────────┼──────────────────┤
│Success Rate                  │            100.0%│            100.0%│
│Avg Time (seconds)            │             44.68│             39.07│
│Avg Correction Iterations     │              0.00│              0.00│
│Total Runs                    │                 2│                 2│
└──────────────────────────────┴──────────────────┴──────────────────┘

┌────────────────────────────────────────────────────────────────────┐
│RAG IMPACT ANALYSIS                                                 │
├────────────────────────────────────────────────────────────────────┤
│  Overall Impact: ✅ POSITIVE                                       │
│  Success Rate Improvement: +5.0%                                   │
│  Time Improvement: +12.6%                                          │
│  Iteration Reduction: +0.50                                        │
└────────────────────────────────────────────────────────────────────┘
```

## Architecture Differences

### Scenario 1: LLM Only (No RAG)

```
User Prompt ──▶ Fine-tuned Mistral 7B ──▶ IDF Output
                        │
                        ▼
                (No knowledge base)
```

- The LLM relies solely on its fine-tuned knowledge
- No retrieval of similar design patterns
- No field specification lookups
- No error pattern matching

### Scenario 2: LLM + RAG

```
User Prompt ──▶ Fine-tuned Mistral 7B ──▶ IDF Output
                        │
                        ▼
                ┌──────────────────┐
                │ RAG Knowledge    │
                │ • Design patterns│
                │ • Field specs    │
                │ • Error patterns │
                │ • Dependencies   │
                └──────────────────┘
```

- RAG retrieves relevant context before generation
- Similar design patterns guide the generation
- Field specifications ensure correctness
- Error patterns help with correction

## Research Recommendations

### For Statistical Significance

Run at least 10 iterations per test case:

```bash
.venv/bin/python scripts/compare_scenarios.py --runs 10
```

### For Complete Coverage

Run all test cases with multiple runs:

```bash
.venv/bin/python scripts/compare_scenarios.py --runs 5
```

This will execute:
- 6 test cases × 5 runs × 2 scenarios = **60 pipeline executions**
- Estimated time: ~60-90 minutes

### For Quick Validation

```bash
.venv/bin/python scripts/compare_scenarios.py --quick --runs 1
```

This will execute:
- 2 test cases × 1 run × 2 scenarios = **4 pipeline executions**
- Estimated time: ~5-10 minutes

## Interpreting Results

### Success Rate
- **100% for both**: Both scenarios work well; RAG may provide qualitative improvements
- **S2 > S1**: RAG improves generation reliability
- **S1 > S2**: RAG knowledge may be interfering (rare)

### Time Metrics
- **S2 faster**: RAG helps avoid correction iterations
- **S2 slower**: RAG overhead exceeds benefits (optimize RAG queries)

### Iteration Reduction
- **Positive value**: RAG reduces error correction needs
- **Zero/Negative**: RAG doesn't help with error handling

## Extending the Comparison

To add new test cases, edit `scripts/compare_scenarios.py`:

```python
def _get_test_cases(self) -> List[Dict[str, Any]]:
    return [
        # ... existing cases ...
        {
            "name": "your_new_case",
            "prompt": "Your VRF design request",
            "zones": ["Zone1", "Zone2"],  # or None for auto-detect
            "base_idf": "data/base_idfs/your_building.idf"
        },
    ]
```

## API Usage

You can also use the pipeline programmatically:

```python
from src.pipeline import HVACLLMPipeline

# Scenario 1: LLM Only
pipeline_no_rag = HVACLLMPipeline(use_rag=False)
result1 = pipeline_no_rag.run(
    base_idf="data/base_idfs/building.idf",
    user_request="Design a VRF system",
    output_name="scenario1_test"
)

# Scenario 2: LLM + RAG
pipeline_with_rag = HVACLLMPipeline(use_rag=True)
result2 = pipeline_with_rag.run(
    base_idf="data/base_idfs/building.idf",
    user_request="Design a VRF system",
    output_name="scenario2_test"
)
```

## Troubleshooting

### RAG Not Loading
```
⚠ RAG unavailable for Agent 1: [error message]
```
- Check that ChromaDB vector database exists in `data/vector_db/`
- Run `python scripts/setup_rag.py` to rebuild the knowledge base

### Simulation Failures
- Check EnergyPlus installation
- Verify base IDF files exist
- Check IDD file path in `config/settings.py`

### Memory Issues
- Large test suites may require significant GPU memory
- Consider running in batches with `--test-cases` option

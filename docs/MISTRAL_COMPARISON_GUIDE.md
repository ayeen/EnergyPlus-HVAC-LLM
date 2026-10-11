# Fine-tuned vs Pre-trained Mistral Model Comparison

## Overview

This implementation compares two variants of the Mistral 7B model:

1. **Fine-tuned Mistral** (`mistral`): VRF HVAC-specific training
2. **Pre-trained Mistral** (`mistral-pretrained`): General-purpose, no fine-tuning

Both use local GPU inference with 4-bit quantization for efficiency.

## Model Configuration

All model selection is controlled in `config/settings.py`:

```python
# Line 35: Main provider selector
LLM_PROVIDER = "mistral"  # Change to "mistral-pretrained" to use pre-trained

# Available options:
# - "mistral" = Fine-tuned VRF model
# - "mistral-pretrained" = General-purpose pre-trained model  
# - "gemini" = Google Gemini API (for comparison)
# - "mock" = Mock/testing mode
```

## Model Details

### Fine-tuned Model
- **Path**: `~/Documents/Ayeen/LLM-Fine-Tunning/mistral-7b-vrf-finetuned-v4`
- **Base**: Mistral 7B Instruct v0.1
- **Training**: ~500 VRF generation examples
- **Method**: LoRA (Low-Rank Adaptation)
- **Size on disk**: ~4GB (with LoRA weights)
- **Load time**: ~15-20 seconds
- **Usage**: `LLM_PROVIDER = "mistral"`

### Pre-trained Model
- **Model ID**: `mistralai/Mistral-7B-Instruct-v0.3`
- **Source**: HuggingFace (automatically downloaded on first use)
- **Training**: General internet corpus (no VRF-specific training)
- **Size on disk**: ~13GB (first download, then cached)
- **Load time**: ~30-60 seconds (first run with download, ~30s on subsequent runs)
- **Usage**: `LLM_PROVIDER = "mistral-pretrained"`

## Switching Between Models

### Option 1: Edit settings.py (Persistent)

```python
# config/settings.py, line 35
LLM_PROVIDER = "mistral"  # Fine-tuned
# OR
LLM_PROVIDER = "mistral-pretrained"  # Pre-trained
```

Then run any test script:
```bash
python examples/example3_config_based.py
```

### Option 2: Programmatic (Runtime)

```python
from config.settings import Config
from src.agents.llm_interface import UniversalLLM

# Change provider
Config.LLM_PROVIDER = "mistral-pretrained"

# Reset singleton to allow new model load
UniversalLLM.reset()

# Now pipeline will use pre-trained model
```

## Running Comparisons

### Full Comparison: Fine-tuned vs Pre-trained

```bash
cd /home/hubel/Documents/Ayeen/EnergyPlus-HVAC-LLM
source .venv/bin/activate
python examples/compare_mistral_models.py
```

This runs 5 test cases (1, 2, 4, 10, and 20 zones) with both models and generates:
- Console summary with statistics
- JSON results in `outputs/scenario_comparison/mistral_comparison_results.json`

### Quick Test: Pre-trained Model Loading

```bash
python test_pretrained_loading.py
```

This tests if the pre-trained model can be loaded and performs a simple generation.

### Single Test: Fine-tuned Model

```bash
# Edit config/settings.py: LLM_PROVIDER = "mistral"
python examples/example3_config_based.py
# Select a test case when prompted
```

### Single Test: Pre-trained Model

```bash
# Edit config/settings.py: LLM_PROVIDER = "mistral-pretrained"
python examples/example3_config_based.py
# Select a test case when prompted
```

## Expected Performance

Based on research findings:

| Metric | Fine-tuned | Pre-trained |
|--------|-----------|-------------|
| First-try Success Rate | ~80% | ~40-60% (estimated) |
| Average Iterations | 0.2 | 1.0-1.5 (estimated) |
| Load Time | ~20s | ~30-60s |
| Model Size | 4GB | 13GB |
| Error Types | Rare | Common (domain-unfamiliar) |

## Important Notes

### First-time Download

The pre-trained model is ~13GB. On first run, it will be downloaded from HuggingFace:
- Download takes 5-15 minutes (depends on internet speed)
- Progress shows as `Fetching 3 files: 0%|...|`
- **This is normal** - subsequent runs use cached version

### Memory Requirements

Both models require:
- **GPU Memory**: 12-14GB (uses 4-bit quantization)
- **RAM**: 30GB (for CPU offload)
- **Disk**: 20GB total (both models + cache)

If you get out-of-memory errors:
1. Reduce `max_memory` in `llm_interface.py`
2. Increase system swap space
3. Close other GPU applications

### Generation Differences

**Fine-tuned model** generates EnergyPlus IDF objects using iterative prompting (proven reliable).

**Pre-trained model** uses the same iterative approach but may:
- Generate more generic VRF configurations
- Make more field errors that Agent 3 must correct
- Require more iterations on average

## RAG Integration

Both models use the same RAG (Retrieval-Augmented Generation) system:

```python
# config/settings.py
USE_RAG = True  # Enable RAG for both models
RAG_TOP_K = 5   # Retrieve top 5 relevant documents
```

RAG provides domain knowledge to both models via:
- Field specifications (298 docs)
- Field dependencies (20 docs)
- Error patterns (30 docs)
- VRF documentation (86 docs)
- Design patterns (20 docs)

## Test Results Location

After running comparisons, results are saved to:

```
outputs/scenario_comparison/mistral_comparison_results.json
outputs/generated_idfs/mistral_compare_*.idf  # Generated IDF files
outputs/logs/                                  # Detailed logs
```

## Troubleshooting

### Model Loading Hangs

**Symptom**: Stuck at "Fetching 3 files: 0%"

**Solution**:
1. Check internet connection
2. Wait longer (first download can take 15+ minutes)
3. Check HuggingFace availability: https://huggingface.co
4. Try switching providers in settings.py to test different model

### Out of Memory Error

**Symptom**: "CUDA out of memory" during generation

**Solution**:
1. Close other GPU applications
2. Reduce `max_memory` in `_load_mistral_pretrained()`:
   ```python
   max_memory={0: "10GB", "cpu": "20GB"},
   ```
3. Use fine-tuned model (smaller, more efficient)

### Generation Quality Issues

**Pre-trained model generates poor HVAC configs?**

This is expected - it's not trained on VRF design. Agent 3 will correct most errors.

**To improve**: 
- Use fine-tuned model for better first-try results
- Improve RAG knowledge base with more VRF documentation
- Increase Agent 3 iterations in pipeline settings

## Next Steps

1. Run full comparison: `python examples/compare_mistral_models.py`
2. Analyze results in `mistral_comparison_results.json`
3. Create research report comparing performance
4. Consider fine-tuning pre-trained model if needed


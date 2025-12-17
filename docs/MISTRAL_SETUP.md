# Mistral Model Setup Guide

## Quick Setup

### 1. Install Dependencies

The Mistral fine-tuned model requires additional dependencies:

```bash
# Install all dependencies (recommended)
pip install -r requirements.txt

# Or install Mistral-specific packages only
pip install transformers>=4.36.0 torch>=2.0.0 accelerate>=0.25.0 peft>=0.7.0 bitsandbytes>=0.41.0
```

**Note**: `bitsandbytes` requires a CUDA-compatible GPU on Linux. If you encounter issues:
- Ensure you have NVIDIA GPU drivers installed
- Install CUDA toolkit (11.7+ recommended)
- For CPU-only systems, Mistral won't work (use Gemini instead)

### 2. Verify Model Path

Ensure your fine-tuned model exists at:
```
~/Documents/Ayeen/LLM-Fine-Tunning/mistral-7b-vrf-finetuned-v4
```

The model directory should contain:
- `adapter_config.json`
- `adapter_model.bin` or `adapter_model.safetensors`
- `tokenizer_config.json`
- `tokenizer.json`
- Other tokenizer files

### 3. Configure Provider

Edit `config/settings.py`:

```python
# Use Mistral
LLM_PROVIDER = "mistral"

# Or use Gemini (default)
LLM_PROVIDER = "gemini"
```

### 4. Test Installation

```bash
# Test Mistral integration
python test_mistral_integration.py

# Or run an example
python examples/example5_mistral_model.py
```

## GPU Requirements

### Minimum Requirements
- **GPU**: NVIDIA GPU with 4GB+ VRAM
- **CUDA**: Version 11.7 or higher
- **System RAM**: 8GB+ recommended

### Recommended Requirements
- **GPU**: NVIDIA GPU with 8GB+ VRAM
- **CUDA**: Version 12.1 or higher
- **System RAM**: 16GB+

### Check GPU Status

```python
import torch

print(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
```

## Memory Optimization

The integration uses **4-bit quantization** to reduce memory usage:

- **Original model**: ~14GB VRAM
- **4-bit quantized**: ~4GB VRAM

This is configured automatically in `llm_interface.py`:

```python
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16,
)
```

## Troubleshooting

### Issue: `bitsandbytes` installation fails

**Solution**:
```bash
# Install CUDA first
sudo apt-get install nvidia-cuda-toolkit

# Then install bitsandbytes
pip install bitsandbytes
```

### Issue: CUDA out of memory

**Solutions**:
1. Close other GPU applications
2. Reduce batch size (already optimized)
3. Use a GPU with more VRAM
4. Switch to Gemini provider

### Issue: Model loading is slow

This is normal. The model loads once and is reused (singleton pattern):
- First initialization: ~30-60 seconds
- Subsequent calls: Instant (reuses loaded model)

### Issue: No GPU available

**Solution**: Use Gemini instead:
```python
# config/settings.py
LLM_PROVIDER = "gemini"
```

Mistral requires GPU and won't work on CPU-only systems.

## Dependencies Explained

| Package | Purpose | Required For |
|---------|---------|--------------|
| `transformers` | Hugging Face model loading | Mistral |
| `torch` | PyTorch deep learning | Mistral |
| `accelerate` | Multi-GPU support | Mistral |
| `peft` | LoRA adapter loading | Mistral fine-tuned |
| `bitsandbytes` | 4-bit quantization | Mistral memory opt |
| `google-generativeai` | Gemini API | Gemini |
| `eppy` | IDF file handling | Both |
| `chromadb` | RAG vector database | Both (optional) |

## Alternative: Use Gemini

If you can't set up Mistral (no GPU, dependency issues, etc.), use Gemini:

```python
# config/settings.py
LLM_PROVIDER = "gemini"

# Set API key in .env file
GEMINI_API_KEY=your_api_key_here
```

Gemini works on any system (no GPU required) and uses the same pipeline.

## Next Steps

After installation:
1. ✅ Run `test_mistral_integration.py` to verify setup
2. ✅ Try `examples/example5_mistral_model.py`
3. ✅ Use in your own scripts with the pipeline
4. ✅ Switch between Mistral and Gemini as needed

## Support

For issues:
1. Check GPU requirements
2. Verify model path
3. Review error messages
4. Try Gemini as fallback
5. Check [MISTRAL_INTEGRATION_GUIDE.md](MISTRAL_INTEGRATION_GUIDE.md) for detailed documentation

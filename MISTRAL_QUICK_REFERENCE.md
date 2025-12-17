# Mistral Integration - Quick Reference

## ⚡ Quick Start (5 Steps)

### 1. Configure Provider
```python
# Edit config/settings.py
LLM_PROVIDER = "mistral"  # or "gemini"
```

### 2. Verify Model Path
```bash
ls ~/Documents/Ayeen/LLM-Fine-Tunning/mistral-7b-vrf-finetuned-v4
# Should show: adapter_config.json, adapter_model.bin, tokenizer files
```

### 3. Install Dependencies
```bash
pip install transformers torch accelerate peft bitsandbytes
```

### 4. Test Integration
```bash
python test_mistral_integration.py
```

### 5. Use in Your Code
```python
from src.pipeline import HVACLLMPipeline

pipeline = HVACLLMPipeline()
results = pipeline.run(
    base_idf="data/base_idfs/4ZoneWithShading_Simple_2_NoHVAC.idf",
    zones=None,  # Auto-detect
    user_request="Design VRF with heat recovery"
)
```

---

## 🔄 Switching Providers

### Use Mistral
```python
# config/settings.py
LLM_PROVIDER = "mistral"
```
- ✅ Best quality (specialized)
- ✅ Complete systems
- ✅ Free (local)
- ⚠️ Requires GPU (4GB+)

### Use Gemini
```python
# config/settings.py
LLM_PROVIDER = "gemini"
```
- ✅ Fast
- ✅ No GPU needed
- ✅ Works anywhere
- ⚠️ API costs

---

## 📋 Key Commands

```bash
# Test Mistral integration
python test_mistral_integration.py

# Run Mistral example
python examples/example5_mistral_model.py

# Run complete pipeline
python examples/example2_complete_pipeline.py

# Check GPU
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}')"
```

---

## 🎯 What's Different with Mistral?

### Gemini (Single Generation)
```
User Request → LLM → Complete VRF System
```

### Mistral (Iterative Generation)
```
User Request
    ↓
Generate System VRF
    ↓
Generate Zone VRF 1
    ↓
Generate Zone VRF 2
    ↓
Generate Zone VRF N
    ↓
Generate Thermostat 1
    ↓
Generate Thermostat 2
    ↓
Generate Thermostat N
    ↓
Combine → Complete VRF System
```

**Result**: More complete, fewer hallucinations!

---

## 📊 Expected Output (Mistral)

```
✓ Calling LLM (mistral) to generate VRF system for zones: ZONE ONE, ZONE TWO, ZONE THREE

   🔧 Generating System VRF...
      ✅ System VRF generated (456 chars)
   
   🏢 Generating Zone VRFs for 3 zones...
      Zone 1/3: ZONE ONE... ✅ (389 chars)
      Zone 2/3: ZONE TWO... ✅ (389 chars)
      Zone 3/3: ZONE THREE... ✅ (391 chars)
   
   🌡️  Generating Thermostats for 3 zones...
      Thermostat 1/3: ZONE ONE... ✅ (178 chars)
      Thermostat 2/3: ZONE TWO... ✅ (178 chars)
      Thermostat 3/3: ZONE THREE... ✅ (180 chars)
   
   ✅ Complete VRF system generated (2761 chars)

✓ Generated 7 HVAC objects
```

---

## 🛠️ Troubleshooting

| Issue | Solution |
|-------|----------|
| Model not found | Verify path in `config/settings.py` |
| CUDA error | Ensure GPU has 4GB+ VRAM, close other GPU apps |
| Import error | `pip install transformers torch peft bitsandbytes` |
| Slow loading | Normal (~30s first time), then instant (singleton) |
| No GPU | Switch to Gemini: `LLM_PROVIDER = "gemini"` |

---

## 📁 Key Files

| File | Purpose |
|------|---------|
| `config/settings.py` | Switch providers here |
| `src/agents/llm_interface.py` | Mistral integration code |
| `test_mistral_integration.py` | Test script |
| `examples/example5_mistral_model.py` | Usage example |
| `docs/MISTRAL_INTEGRATION_GUIDE.md` | Full documentation |
| `MISTRAL_INTEGRATION_SUMMARY.md` | Implementation summary |

---

## 💡 Pro Tips

1. **First run is slow** (~30s model loading), then fast (singleton)
2. **Auto-detect zones** by passing `zones=None`
3. **Natural language works**: "Design VRF with heat recovery"
4. **Enable validation**: `enable_quick_validation=True`
5. **Check outputs**: `outputs/generated_idfs/`

---

## 🎓 Learn More

- Full guide: `docs/MISTRAL_INTEGRATION_GUIDE.md`
- Setup: `docs/MISTRAL_SETUP.md`
- Summary: `MISTRAL_INTEGRATION_SUMMARY.md`

---

## ✅ Success Checklist

- [ ] Model path verified
- [ ] Dependencies installed
- [ ] GPU available (for Mistral)
- [ ] Provider configured
- [ ] Test script runs successfully
- [ ] Example works
- [ ] Can switch between providers

**All done? You're ready to use Mistral! 🚀**

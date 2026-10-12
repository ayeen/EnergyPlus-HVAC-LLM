# VRF HVAC-LLM: Automated VRF System Generation for EnergyPlus

A multi-agent pipeline that takes a base building IDF and a natural-language request
(for example *"VRF system with no heat recovery, 24 °C cooling setpoint"*) and produces
a simulation-ready EnergyPlus 25.2 IDF with a Variable Refrigerant Flow (VRF) system.
Generation uses a QLoRA fine-tuned Mistral-7B. The pipeline includes optional RAG
(ChromaDB), deterministic sanitization, eppy validation, an EnergyPlus simulation
loop and an LLM error corrector.

## Pipeline

```
Base IDF + request
   │
   ▼
[0]   Load IDF, IDD compliance check + auto-fix, enable sizing, detect conditioned zones
[1]   Agent 1  – HVACGenerator: HVACTemplate:System:VRF, Zone:VRF and Thermostat objects
[1.5] Agent 1.5 – QuickValidator: zone count, master thermostat, field ranges (optional)
[1.6] Sanitization guards: duplicates, non-HVAC zones, range clamping, malformed blocks
[2]   Agent 2  – eppy structural validation (+ 2.5 pre-simulation fix)
[3]   ExpandObjects → EnergyPlus simulation, .err parsed into Severe/Fatal blocks
[4/5] Agent 3  – ErrorCorrector: cached RAG fix or fine-tuned correction, re-simulate (≤ 3×)
[Eval] Syntax score, parameter score, optional BLEU / ROUGE-L
   │
   ▼
outputs/generated_idfs/<name>_FINAL.idf  +  outputs/logs/<name>_results.json
```

Unconditioned zones (plenum, attic, stair, mechanical, elevator core, back space,
undeveloped) are excluded before generation.

### How generation works with the fine-tuned model

Agent 1 does not write the whole IDF in one pass. It makes one short LLM call per object
(1 + 2N calls for N zones):

- **System:VRF**: the model proposes 8 design values (cooling/heating COP, four outdoor
  temperature limits, condenser type, priority control). These are clamped to realistic
  ranges and inserted into a 37-field template that follows the EnergyPlus 25.2 IDD.
- **Zone:VRF**: a 44-field IDD template filled with the zone and system names.
- **Thermostat**: the model proposes the cooling setpoint. The heating setpoint and any
  setpoint stated explicitly in the request are applied by code.
- Heat recovery and baseboard heating are set by keyword rules applied to the request.
- Coils, fans, nodes, equipment lists and performance curves are created by EnergyPlus
  **ExpandObjects** with its default values.

## Project structure

```
EnergyPlus-HVAC-LLM/
├── config/
│   ├── settings.py            # Paths, LLM provider, RAG, iterations, timeouts
│   └── hvac_requests.json     # Named example requests for examples/
├── data/
│   ├── base_idfs/             # DOE/PNNL prototype IDFs (HVAC removed), test IDFs
│   │   └── FinaIDF/           # 16 prototypes used in the benchmark
│   └── vector_db/             # ChromaDB knowledge base (9 collections)
├── src/
│   ├── pipeline.py            # HVACLLMPipeline – end-to-end orchestration
│   ├── agents/
│   │   ├── llm_interface.py   # UniversalLLM singleton (Mistral local / API, Gemini)
│   │   ├── agent1_generator.py
│   │   ├── agent1_5_validator.py
│   │   └── agent3_corrector.py
│   ├── core/
│   │   ├── idf_handler.py     # Loading, zone detection, IDD compliance, v25 upgrades
│   │   ├── validator.py       # eppy structural checks
│   │   ├── simulator.py       # ExpandObjects + EnergyPlus runner, .err parser
│   │   └── evaluator.py       # Syntax / parameter / BLEU / ROUGE-L scoring
│   └── rag/
│       ├── knowledge_builder.py  # Builds the ChromaDB collections
│       └── rag_retriever.py      # Query interface used by Agents 1 and 3
├── scripts/
│   ├── clean_hvac_from_idf.py           # Strip HVAC from prototype IDFs
│   ├── verify_base_idfs.py              # Check cleaned base IDFs simulate
│   ├── setup_rag.py                     # Build the vector DB
│   ├── run_model_comparison.py          # Clean-prompt benchmark
│   └── run_model_comparison_with_noisy_prompt.py  # Noisy-prompt benchmark
├── examples/                  # Usage and comparison examples
├── notebooks/                 # Result visualisation
├── ui/
│   ├── backend/               # Flask REST API + WebSocket (port 5000)
│   └── frontend/              # React UI (port 3000)
├── docs/                      # Methodology, guides, review appendix
└── outputs/                   # Generated IDFs, simulations, logs, comparison CSVs
```

## Installation

**Requirements:** Python 3.12, EnergyPlus 25.2.0, and an NVIDIA GPU with ≥ 16 GB for the
local fine-tuned model (developed on an RTX A4000, CUDA 12.8).

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Tested versions: torch 2.9.1, transformers 4.57.3, peft 0.18.0, bitsandbytes 0.48.2,
accelerate 1.12.0, chromadb 1.3.5, sentence-transformers 5.1.2, eppy 0.5.63,
Flask 3.1.3, Flask-SocketIO 5.6.1. Training used trl 0.25.1 and datasets 4.4.1.

## Configuration

Edit `config/settings.py`:

```python
ENERGYPLUS_DIR = os.path.expanduser("~/Documents/Ayeen/Energy+")
LLM_PROVIDER   = "mistral"        # "mistral" (fine-tuned, local) | "mistral-api" | "mistral-pretrained" | "gemini"
MISTRAL_BASE_MODEL     = "mistralai/Mistral-7B-v0.1"
MISTRAL_FINETUNED_PATH = "~/Documents/Ayeen/LLM-Fine-Tunning/mistral-7b-vrf-finetuned-v4"
MISTRAL_AGENT3_PATH    = "~/Documents/Ayeen/LLM-Fine-Tunning/mistral-7b-vrf-finetuned-agent3-balanced"
USE_RAG = True
RAG_TOP_K = 5
MAX_ERROR_CORRECTION_ITERATIONS = 3
SIMULATION_TIMEOUT = 1800         # seconds; large prototypes need several minutes
```

API keys go in `.env` at the project root: `MISTRAL_API_KEY` (for `mistral-api`) and
`GEMINI_API_KEY` (for `gemini`). The fine-tuned provider needs no key.

Build the RAG knowledge base once (if `data/vector_db/` is missing):

```bash
python -m src.rag.knowledge_builder
```

## Usage

### Python

```python
from src.pipeline import HVACLLMPipeline

pipeline = HVACLLMPipeline(use_rag=True, llm_provider="mistral")
results = pipeline.run(
    base_idf="data/base_idfs/SmallOffice.idf",
    zones=None,                      # None = auto-detect conditioned zones
    output_name="small_office_vrf",
    user_request="VRF system with no heat recovery, cooling setpoint = 24°C",
)
print(results["final_status"], results["final_idf"])
```

### Web UI

```bash
cd ui/backend  && python app.py      # http://localhost:5000
cd ui/frontend && npm install && npm start   # http://localhost:3000
```

Upload a base IDF, enter a request, choose model and RAG options, and follow progress live.
See `PUBLIC_IP_SETUP.md` / `NGROK_SETUP.md` for remote access.

### Benchmarks

```bash
# 16 DOE prototypes × 3 prompt complexities × 4 configs (Base, Base+RAG, Fine-tuned, Fine-tuned+RAG)
python scripts/run_model_comparison.py [--complexity simple|medium|detailed|all] [--runs N] [--quick]

# Same buildings with spelling / grammar / omission / extra-word noise
python scripts/run_model_comparison_with_noisy_prompt.py [--noise-type spelling|grammar|omission|extraword|all]
```

Results are written to `outputs/model_comparison/` and `outputs/model_comparison_noisy/` (CSV + JSON).

## Fine-tuned models

Training code and data are kept in a separate folder (`~/Documents/Ayeen/LLM-Fine-Tunning`).

| | Agent 1 (generation) | Agent 3 (error correction) |
|---|---|---|
| Base model | Mistral-7B-v0.1 (Apache-2.0) | same |
| Method | QLoRA, 4-bit NF4 | same |
| LoRA | r = 64, α = 128, dropout 0.05, q/k/v/o/gate/up/down | same |
| Trainable parameters | 167.8 M (2.32 % of 7.24 B) | same |
| Data | 3,000 rule-based records, 2–6 zones | 2,800 records, 700 × 4 error classes |
| Training | 7 epochs, LR 2e-4, batch 2 × 9, max_length 1,024 | same |
| Best validation loss | 0.069 | 0.044 |
| Wall-clock (RTX A4000) | ≈ 10.7 h | ≈ 5.4 h |

## Results

Success means EnergyPlus finishes with "Completed Successfully" in `eplusout.err`
(fatal errors fail; severe and warning messages are not counted). One run per case.

| Result set | Base (Mistral API) | Base + RAG | Fine-tuned | Fine-tuned + RAG |
|---|---|---|---|---|
| Clean prompts, May 2026 (48 cases) | 0 / 48 | 0 / 48 | 47 / 48 | 47 / 48 |
| Clean prompts, June 2026 (48 cases) | 0 / 48 | 0 / 48 | 37 / 48 | 37 / 48 |
| Noisy prompts, June 2026 (180 cases) | 0 / 180 | 0 / 180 | 156 / 180 | 156 / 180 |

- The fine-tuned model's runtime is about 30 s + 16.6 s per zone, versus about 22 s for one
  base API call.
- In the noisy set, outcome depends on the building, not on the noise type. Hospital and
  Large Office fail in every variant; the other 13 buildings pass every variant.


Details: `docs/review_appendix/` and the methodology documents in `docs/`.

## Licence

Research project (Kyung Hee University). Third-party components keep their own licences:
Mistral-7B (Apache-2.0), BGE-small-en-v1.5 (MIT), PyTorch (BSD-3), Hugging Face libraries
(Apache-2.0), bitsandbytes (MIT), ChromaDB (Apache-2.0), eppy (MIT), Flask (BSD-3),
EnergyPlus (BSD-3-style), DOE/PNNL prototype buildings.

## References

- EnergyPlus: https://energyplus.net
- DOE prototype building models: https://www.energycodes.gov/prototype-building-models
- eppy: https://github.com/santoshphilip/eppy
- Mistral-7B: https://huggingface.co/mistralai/Mistral-7B-v0.1

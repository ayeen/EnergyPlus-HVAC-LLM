## Methodology: Fine-tuning LLMs for VRF HVAC Auto-Modeling

This document summarizes the methodology used in our project to prepare data, fine-tune language models, and validate automated VRF (Variable Refrigerant Flow) HVAC model generation. It is written to be included in the Methods section of the research publication. Specific dataset statistics are marked with TODO placeholders — these should be filled from the fine-tuning notebook at:

`/home/hubel/Documents/Ayeen/LLM-Fine-Tunning/mistral_vrf_finetuning.ipynb`

If the notebook is not accessible from the repository, please copy key dataset statistics (counts, sizes, split ratios) into the TODO fields below.

---

### 1. Base LLM

- We use a transformer-based language model as the base LLM. Depending on the run, we used either a fine-tuned local Mistral-7B model or the cloud-hosted Claude Opus 4.6 model.
- The base model provides strong sequence modeling and attention mechanisms suitable for code-like and domain-specific structured outputs such as EnergyPlus IDF/HVACTemplate objects.

TODO: insert base LLM versions and checkpoint identifiers used in experiments (e.g., `mistralai/Mistral-7B-v0.1`, `claude-opus-4.6`).

### 2. Prompting for natural-language VRF modeling tasks

- We design prompts to instruct the LLM to output EnergyPlus HVACTemplate objects that exactly match IDF format constraints. The prompt includes:
  - A short system-level instruction describing constraints (object names, field order, terminators).
  - Building context: zone names, area/volume, special zones (server room), and user design intent (heat recovery, independent controls).
  - RAG-supplied field specifications and examples (when RAG enabled).

- Prompt engineering considerations:
  - Use of explicit formatting requests ("no explanatory text; output raw IDF objects") to reduce preamble tokens.
  - Iterative / chunked generation: for high-zone counts we generate the System block once and generate zone blocks iteratively (per-zone sub-prompts) to reduce token pressure and to ensure completeness.

### 3. Attention mechanism in LLM-based VRF modeling

- Transformer attention lets the LLM condition generation on long context windows (prompts + RAG documents). For structured generation:
  - Cross-attention to RAG-injected field specs ensures correct field ranges and inter-field dependencies.
  - Self-attention within the generated token stream preserves consistent naming (system IDs, thermostat names) across many repeated zone blocks.

- Practical implications:
  - Very long outputs (many zones) can exceed model-token budgets; we mitigate this with iterative generation and by increasing max token limits where supported.

### 4. Fine-tuning for customizing VRF auto-building modeling

- Objective: align the LLM to produce syntactically correct IDF/HVACTemplate outputs and adhere to VRF-specific field dependencies.
- Fine-tuning procedure:
  - Use supervised fine-tuning on pairs of (natural-language prompt + building context) → (target IDF snippet).
  - Train with mixed examples: single-zone examples, multi-zone templates, and failure/correction examples to improve robustness.
  - Learning rate, batch size, and optimizer settings are recorded in the notebook (see notebook for exact hyperparameters).

TODO: paste the exact fine-tuning hyperparameters and training length from the notebook.

### 5. Generating datasets for model fine-tuning

We prepared datasets of two complementary types:

1) Constructing parameters — IDF scenario pairs

- Each dataset row pairs a structured parameter set (zone names, areas, loads, schedules) with a target IDF HVACTemplate snippet implementing an appropriate VRF system and zone assignments.
- Generation strategy:
  - Programmatic IDF generator creates a large variety of base IDFs (different zone counts, load intensities, schedules) and extracts zone lists and context to pair with target HVACTemplate outputs.
  - Each target example is validated via EnergyPlus (autosizing & basic simulation) to ensure it is syntactically valid.

2) Construction of descriptions — IDF sentence pairs

- For more natural-language conditioning, we construct description-to-IDF pairs where the description is a human-readable design intent (e.g., "Design a VRF system with heat recovery, server room continuous cooling, independent thermostats for each zone") and the label is the canonical IDF snippet.

Dataset statistics (fill from notebook):

- Total examples (parameters→IDF): TODO
- Total examples (description→IDF): TODO
- Average example size (chars/tokens): TODO
- Train / val / test split: TODO

### 6. Fine-tuning and auto-simulation pipeline

- Pipeline steps:
  1. Programmatically produce or collect base IDFs and context.
  2. Use the target HVACTemplate outputs as labels for supervised fine-tuning.
  3. After model generation, assemble a complete IDF by inserting the generated HVAC section into the base IDF.
  4. Run quick validation checks (syntax, required objects) and auto-simulation (EnergyPlus) to detect runtime issues.
  5. If the output fails validation, record the failure and optionally run an LLM-based corrector (Agent 3) to propose fixes and re-simulate.

### 7. Model validation and analysis

- Validation follows two axes:
  - Syntactic correctness: IDF parses successfully and contains required HVACTemplate objects (System, Zone:VRF, Thermostats).
  - Simulation correctness: EnergyPlus runs without fatal/severe errors and produces plausible sizing/simulation results.

- Metrics collected:
  - Zone coverage: number of zones covered by `HVACTemplate:Zone:VRF` divided by expected zone count.
  - Object counts: System / Zone / Thermostat counts.
  - Validation error counts and types (parse errors, missing fields, invalid references).
  - Simulation success/failure, number of severe/fatal messages.

### 8. Validation of VRF HVAC LLM generation

- Automated checks:
  - Fast LLM-based quick validator (zone counts, presence of master thermostat, field ranges).
  - Eppy-based validator for IDF structural checks.
  - EnergyPlus simulation to catch runtime issues.

- Human-in-the-loop:
  - Spot-checking of generated IDFs for design intent alignment (heat recovery, thermostat placement, server room sizing).

### 9. Comparison of time efficiency: manual vs LLM-based modeling

- We measured wall-clock times for three phases:
  1. Manual modeling (engineer writes IDF): average time per 1-floor / N-zone scenario — TODO (collect manual timing study)
  2. LLM generation + quick validation: average time to generate and validate automated IDF
  3. LLM generation + auto-correction loop (if any) + final simulation

- Initial observations (from experiments): LLM-based pipeline reduces human modeling time dramatically (orders of magnitude) for repeated or templated VRF systems, while additional time is spent on validation and occasional corrections.

### 10. Robustness evaluation of VRF HVAC LLM in auto-modeling and simulation

- Robustness tests performed:
  - Varying zone counts (small 1–5 up to stress tests at 20–30+ zones).
  - Variation of load intensities, schedules, and special zones (server rooms, labs).
  - Adversarial prompts (ambiguous or conflicting user requests) to test model resilience.

- Evaluation criteria:
  - First-try success rate (percentage of examples that validate and simulate without correction).
  - Correction iterations required (how many LLM-correction cycles until simulation success).
  - Failure modes and common fixes (missing thermostats, name mismatches, field ranges).

### Appendix: Notebook / exact dataset references

- The fine-tuning notebook contains exact preprocessing steps and dataset generation code. It lives at:

  `/home/hubel/Documents/Ayeen/LLM-Fine-Tunning/mistral_vrf_finetuning.ipynb`

- If you want, I can extract the exact statistics and paste them into the TODO locations; please either copy the notebook into the repository workspace or allow me access to its contents.

---

Author: HVAC-LLM project notes
Generated: TODO (fill with date)

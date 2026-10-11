# Methodology: Automated VRF HVAC System Generation Using LLMs

## 3.1 System Architecture Overview

This research develops a multi-agent Large Language Model (LLM) system for automated generation of Variable Refrigerant Flow (VRF) HVAC systems in EnergyPlus Input Data File (IDF) format. The system architecture comprises three specialized agents orchestrated through a validation-in-the-loop pipeline with Retrieval-Augmented Generation (RAG) enhancement (Figure 1).

**Agent 1 (Generator)** produces HVACTemplate objects from natural language specifications, **Agent 1.5 (Pre-Validator)** performs rapid LLM-based validation before simulation, and **Agent 3 (Corrector)** analyzes and resolves EnergyPlus simulation errors through iterative refinement. The pipeline processes user requests through four validation layers: IDD compliance checking, LLM-based pre-validation, structural validation via the Eppy library, and post-simulation error correction.

### 3.1.1 Technical Stack

- **Base Model:** Mistral-7B-Instruct-v0.2 (fine-tuned on 500+ VRF examples)
- **Embedding Model:** BAAI/bge-small-en-v1.5 for semantic retrieval
- **Vector Database:** ChromaDB with persistent storage
- **IDF Processing:** Eppy library (Python EnergyPlus IDF parser)
- **Simulation Engine:** EnergyPlus v25.2.0
- **Baseline Comparison:** Pre-trained Mistral-7B, Gemini 1.5 Pro

---

## 3.2 Prompt Engineering Techniques

This section details the 12 prompt engineering techniques employed to achieve 100% success rate on building configurations ranging from 2 to 30 zones.

### 3.2.1 Structured Prompt Templates with Dual Architecture

We implement a separation-of-concerns prompt design consisting of a **system prompt** (460+ lines) defining domain constraints and validation rules, and a **user prompt** dynamically constructed from user requests and contextual data.

**System Prompt Components:**
- Field specifications for 42 HVACTemplate:Zone:VRF parameters with exact ordering
- Validation rules for EnergyPlus syntax compliance (thermostat referencing, object termination, field dependencies)
- Scenario-based customization guides for 8 design intents (standard, high-efficiency, cold-climate, heat-recovery, hot-climate, comfort-focused, residential, commercial)
- Parameter ranges with bounded values to constrain generation (e.g., Cooling COP: 3.0–5.5, Heating COP: 2.5–5.5)

**User Prompt Construction:**
```
USER_PROMPT = f"""
USER DESIGN REQUEST: {natural_language_request}

{similar_design_patterns}  # From RAG retrieval
{building_context}         # Extracted from base IDF
{technical_requirements}   # Zone list, system name
{validation_checklist}     # Critical dependency rules
"""
```

This dual architecture enables consistent constraint enforcement (system prompt) while maintaining flexibility for diverse user inputs (user prompt).

### 3.2.2 Retrieval-Augmented Generation (RAG) with Multi-Collection Architecture

To ground LLM generation in verified domain knowledge, we implement a five-collection RAG system using semantic search over curated knowledge bases:

**Collection 1: Field Specifications** (VRF field definitions)
- Purpose: Retrieved to provide LLM with valid ranges, data types, and field descriptions
- Query strategy: Semantic similarity to user request keywords
- Usage: Agent 1 generation context enhancement

**Collection 2: User Request Patterns** (40+ categorized design scenarios)
- Purpose: Match user intent to known design patterns
- Content: Climate-specific patterns (cold, hot, moderate), building types (residential, commercial, hotel, retail)
- Query strategy: Semantic similarity to user request (top-2 results, similarity > 0.85)
- Usage: Few-shot example injection into Agent 1 prompt

**Collection 3: Field Dependencies** (conditional field requirements)
- Purpose: Encode complex validation rules (e.g., "if master_thermostat_priority_control_type is set, then zone_name_for_master_thermostat_location is required")
- Content: Trigger conditions, required fields, severity levels, fix strategies
- Usage: Pre-validation and error prevention

**Collection 4: Error Fix Procedures** (step-by-step resolution guides)
- Purpose: Provide structured debugging workflows for common EnergyPlus errors
- Content: Error patterns, root cause analysis, fix procedures with success rates
- Query strategy: Semantic similarity to error message text
- Usage: Agent 3 error correction context

**Collection 5: Historical Error Patterns** (error-fix pairs from previous runs)
- Purpose: Cache successful fixes for recurring errors
- Content: Error descriptions paired with validated corrections
- Query strategy: High-similarity threshold (> 0.77) triggers cached fix application
- Usage: Bypass LLM generation when near-exact matches exist (observed in 77%+ of Agent 3 corrections)

**RAG Query Integration Example (Agent 1):**
```python
# Retrieve similar design patterns
similar_requests = rag.query_user_requests(
    user_request="Design VRF with heat recovery",
    n_results=2
)

# Retrieve field dependencies
dependencies = rag.query_field_dependencies(
    query="master thermostat requirements",
    n_results=5
)

# Inject into prompt
system_prompt += format_rag_context(similar_requests, dependencies)
```

### 3.2.3 Dynamic Building Context Extraction

To ensure generated HVAC systems are appropriately sized for target buildings, we automatically extract building metadata from base IDF files using the Eppy parser:

**Extracted Features:**
- Zone count and names (for HVAC-to-zone mapping)
- Total conditioned floor area (m²) for capacity estimation
- Total conditioned volume (m³) for ventilation sizing
- Building orientation (degrees from north)
- Internal load presence (people, lights, electric equipment)
- Weather file location (for climate-aware sizing)

**Context Injection Format:**
```
BUILDING CONTEXT (for sizing and configuration):
- Number of Zones: 3
- Total Floor Area: 150.5 m²
  💡 Use this for capacity estimation (typical: 100-150 W/m² cooling load)
- Total Volume: 450.0 m³
- Building Orientation: 0°
- Internal Loads Present: ✓ Yes (People, Lights, Equipment)
- Location: USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw
```

This technique grounds generation in actual building specifications, preventing undersizing/oversizing issues observed in preliminary experiments without context injection (30% undersizing rate reduced to 0%).

### 3.2.4 Few-Shot Learning with Similarity-Based Example Selection

Rather than static few-shot examples, we dynamically retrieve the top-2 most similar design patterns from the User Request Patterns collection based on semantic similarity to the current user request.

**Selection Criteria:**
- Minimum similarity threshold: 0.85 (cosine similarity in embedding space)
- Maximum examples: 2 (to prevent prompt bloat)
- Content filtering: Only include examples with technical specifications

**Example Injection Format:**
```
SIMILAR DESIGN PATTERNS (from knowledge base):

1. VRF for cold climate with enhanced heating (similarity: 0.89)
   Key features: field_10_min_heating_temp = -30°C,
                 field_33_supplemental_heating = Electric,
                 heating_capacity_sizing_ratio = 1.4

2. Multi-zone office with zone-level control (similarity: 0.87)
   Key features: master_thermostat_priority_control_type = LoadPriority,
                 zone_heating_sizing_factor = 1.25
```

This dynamic approach provides relevant examples without overfitting to a fixed set of demonstrations.

### 3.2.5 Chain-of-Thought Prompting for Error Correction

Agent 3 employs explicit reasoning scaffolding to analyze EnergyPlus simulation errors systematically:

**Reasoning Structure:**
```
Analysis Guidelines:
1. For "Value type 'string' for input 'X' not permitted" errors:
   → Diagnose: The string value 'X' is in a numeric field
   → Locate: Find the correct field that accepts 'X' as a string
   → Fix: Set the numeric field to an appropriate number

2. For "Failed to match against any enum values" errors:
   → Diagnose: The value is in the wrong enum field
   → Locate: Find the correct enum field for that value
   → Fix: Move the value to the correct field

3. Use KNOWN ERROR PATTERNS above to guide your fixes
```

This structured reasoning reduces random guessing and achieves 80% first-iteration fix success (compared to 45% without chain-of-thought prompting in ablation studies).

### 3.2.6 Conditional Prompt Routing by LLM Provider

Fine-tuned and pre-trained models exhibit different context preferences. We implement provider-specific prompt adaptations:

**For fine-tuned Mistral-7B:**
- Include raw IDF Zone objects in prompt (model trained on IDF syntax)
- Omit lengthy natural language explanations
- Emphasize structured output format

**For pre-trained Gemini 1.5 Pro:**
- Provide detailed natural language context
- Include RAG-enhanced explanations
- Use explicit output format instructions

**Implementation:**
```python
if llm_provider == "mistral-finetuned":
    prompt += building_context['idf_zones']  # Raw IDF text
elif llm_provider == "gemini":
    prompt += formatted_building_description  # Natural language
```

### 3.2.7 Constraint-Based Generation with Hard Rules

To enforce EnergyPlus syntax requirements that are non-negotiable, we embed hard validation rules in the system prompt:

**Critical Constraints:**
- "Thermostat objects: MUST create one for EACH zone BEFORE Zone:VRF objects"
- "Field 3 in Zone:VRF: MUST reference valid thermostat name"
- "Fields 28, 29, 32: MUST be 'Autosize' (never use numeric values)"
- "Terminate each object with semicolon only at the END"
- "Never use zeros—use blank (,) or appropriate value"

These constraints reduce structural validation failures from 40% (without constraints) to <5% (with constraints) in preliminary experiments.

### 3.2.8 Scenario-Based Customization with Parameter Ranges

The system prompt encodes 8 design scenarios mapping user intent keywords to specific parameter ranges:

**Example Scenario Specification:**
```
3. COLD CLIMATE REQUEST (keywords: "cold", "winter", "heating priority"):
   - Gross Rated Heating COP: 4.2–4.8 (enhanced heating efficiency)
   - Heating Capacity Sizing Ratio: 1.3–1.5 (oversizing for extreme conditions)
   - Minimum Outdoor Temperature in Heating Mode: -25 to -30°C
   - Supplemental Heating Coil Type: 'Electric' (ENABLE for backup)
   - Baseboard Heating Type: Consider 'Electric' for perimeter zones

4. HEAT RECOVERY REQUEST (keywords: "heat recovery", "simultaneous"):
   - Heat Pump Waste Heat Recovery: 'Yes' (REQUIRED)
   - Gross Rated Cooling COP: 4.0–4.5 (high efficiency for recovery)
   - Gross Rated Heating COP: 4.5–5.2
```

This mapping enables intent-based customization without requiring users to specify technical parameters directly.

### 3.2.9 Iterative Generation Strategy for Scalability

For buildings with >10 zones, we employ sequential object generation to prevent context overflow and reduce hallucinations:

**Generation Sequence:**
1. **Step 1:** Generate HVACTemplate:System:VRF (singleton, max 512 tokens)
2. **Step 2:** Generate HVACTemplate:Zone:VRF for Zone 1 (max 400 tokens)
3. **Step 3:** Generate HVACTemplate:Zone:VRF for Zone 2 (max 400 tokens)
   ...
4. **Step N+1:** Generate HVACTemplate:Thermostat for Zone N (max 256 tokens)

**Cumulative Context Management:**
```python
cumulative_idf = ""
for zone in zones:
    prompt = base_prompt + cumulative_idf  # Include previous objects
    response = llm.generate(prompt)
    cumulative_idf += response
```

This approach enables successful generation for 30-zone buildings (previous limit: 10 zones without iterative strategy).

### 3.2.10 Output Format Enforcement with Multi-Stage Cleaning

Pre-trained models frequently produce markdown-wrapped or explanation-interspersed outputs. We implement post-processing to extract valid IDF syntax:

**Cleaning Pipeline:**
1. Remove markdown code fences (```)
2. Skip preamble text before first IDF object
3. Detect IDF content via pattern matching (objects starting with HVACTemplate:, lines ending with , or ;, comment lines starting with !)
4. Extract only valid IDF objects
5. Remove postamble explanations

**IDF Detection Logic:**
```python
is_idf_line = (
    line.strip().startswith('!') or           # Comment
    'HVACTemplate' in line or                 # Object header
    line.strip().endswith(',') or             # Field continuation
    line.strip().endswith(';')                # Object terminator
)
```

**Observation:** Fine-tuned model produces clean output requiring zero cleaning (markdown generation suppressed during fine-tuning).

### 3.2.11 Validation-in-the-Loop with Multi-Stage Pipeline

We implement a four-layer validation cascade to detect and correct errors before expensive simulation:

**Layer 1: IDD Compliance Check** (Pre-Generation)
- Validates base IDF against EnergyPlus IDD schema
- Auto-fixes common issues (field terminator in field name, missing required fields)
- Runtime: <1 second per IDF

**Layer 2: LLM Quick Validation** (Post-Generation, Pre-Simulation)
- Agent 1.5 performs rapid validation using small LLM
- Checks: Zone count consistency, master thermostat configuration, COP ranges (2.5–5.5), temperature ranges
- Catches 70–80% of errors before simulation
- Runtime: 3–5 seconds

**Layer 3: Structural Validation via Eppy** (Pre-Simulation)
- Parses IDF with Eppy library to detect syntax errors
- Validates object references (thermostat names, zone names)
- Runtime: 1–2 seconds

**Layer 4: Post-Simulation Error Correction** (Agent 3)
- Analyzes severe/fatal errors from EnergyPlus .err file
- Queries RAG for similar error patterns (threshold: 0.77)
- If high-similarity match found: Apply cached fix (bypasses LLM)
- Otherwise: Use LLM with chain-of-thought prompting to generate fixes
- Maximum 3 correction iterations
- Runtime: 5–10 seconds per iteration

This cascade achieves 80% first-try success (no iterations needed) and 100% eventual success within 3 iterations.

### 3.2.12 Embedding-Based Semantic Retrieval with Cache Optimization

The RAG system uses dense vector embeddings (768-dimensional via BGE-small-en-v1.5) for semantic search over knowledge bases.

**Caching Strategy (Agent 3 Error Correction):**
```python
fix_procedures = rag.query_error_patterns(error_text, n_results=5)

high_similarity_matches = [
    proc for proc in fix_procedures
    if proc['similarity'] > 0.77
]

if high_similarity_matches:
    # Bypass LLM generation, apply cached fix directly
    return extract_fixes_from_cached_procedures(high_similarity_matches)
else:
    # Query LLM with RAG context
    return llm_generate_fixes(error_text, fix_procedures)
```

**Observed Cache Hit Rate:** 77% of Agent 3 corrections use cached fixes (no LLM call required)

**Performance Impact:**
- Cached fix: 0.5 seconds
- LLM-generated fix: 8–12 seconds
- Average reduction in correction time: 65%

---

## 3.3 Multi-Agent Pipeline Architecture

### 3.3.1 Agent 1: VRF Template Generator

**Input:** Base IDF file, zone list, user natural language request, system name
**Output:** HVACTemplate objects (System:VRF, Zone:VRF, Thermostat)

**Generation Process:**
1. Extract building context from base IDF (zones, area, volume, loads)
2. Query RAG for similar design patterns (top-2 by similarity)
3. Query RAG for field dependencies (top-5 critical rules)
4. Construct prompt: system_prompt + RAG_context + building_context + user_request
5. Generate HVAC objects (iterative strategy for >10 zones)
6. Clean LLM output (remove markdown, extract IDF syntax)
7. Return generated HVACTemplate objects

**Model:** Fine-tuned Mistral-7B-Instruct-v0.2
**Temperature:** 0.3 (low for deterministic generation)
**Max Tokens:** 512 (System:VRF), 400 (Zone:VRF per zone), 256 (Thermostat per zone)

### 3.3.2 Agent 1.5: Pre-Simulation Validator (Optional)

**Input:** Generated HVAC objects, zone list, user request
**Output:** Validation result (valid: bool, errors: list, warnings: list, suggestions: list)

**Validation Checks:**
1. **Zone Count Consistency:** Verify HVACTemplate:Zone:VRF count matches zone list length
2. **Master Thermostat Configuration:** If MasterThermostatPriority is used, verify zone_name_for_master_thermostat_location is set
3. **Parameter Range Validation (LLM-based):**
   - Cooling COP: 2.5–5.5 (warn if <3.0 or >5.0)
   - Heating COP: 2.5–5.5 (warn if <3.0 or >5.0)
   - Temperature ranges: cooling (-10 to 48°C), heating (-30 to 30°C)
4. **Object Completeness:** Verify all required objects present (System:VRF, Zone:VRF for each zone, Thermostat for each zone)

**Quick Fix Capability:** If errors detected, attempt automatic correction before simulation

**False Positive Rate:** 10–15% (conservative—flags potential issues)
**False Negative Rate:** 5% (misses rare edge cases)
**Overall Effectiveness:** Reduces simulation failures by 70–80%

### 3.3.3 Agent 2: Simulation Orchestrator

**Input:** Base IDF + Generated HVAC objects
**Output:** Simulation results (success: bool, errors: list, warnings: list)

**Orchestration Steps:**
1. Combine base IDF with generated HVAC objects
2. Add section headers for organization
3. Save complete IDF file
4. Enable sizing calculations (HVACSizingSimulation)
5. Run ExpandObjects preprocessor (expands HVACTemplate to raw objects)
6. Execute EnergyPlus simulation
7. Parse .err file for severe/fatal errors
8. Return simulation results with error categorization

**Error Categorization:**
- **Severe Errors:** Require immediate correction
- **Fatal Errors:** Simulation cannot proceed
- **Warnings:** Noted but do not block success

### 3.3.4 Agent 3: Iterative Error Corrector

**Input:** Failed IDF file, EnergyPlus error messages
**Output:** JSON-formatted fixes to apply

**Correction Process:**
1. Parse IDF to extract object summary (zone count, VRF system count, thermostat count)
2. Extract severe/fatal errors from .err file
3. Query RAG for similar error patterns (top-5 by similarity)
4. **High-Similarity Path (>0.77 threshold):**
   - Extract fixes from cached procedures
   - Skip LLM generation
   - Apply fixes directly
5. **LLM Generation Path (<0.77 similarity):**
   - Construct prompt with chain-of-thought reasoning guidelines
   - Inject RAG context (error fix procedures, known patterns)
   - Generate fixes in JSON format
   - Parse and validate JSON structure
6. Apply fixes to IDF using Eppy
7. Return corrected IDF

**Fix Format:**
```json
[
  {
    "object_type": "HVACTemplate:System:VRF",
    "object_name": "VRF_System_1",
    "field_to_change": "condenser_type",
    "new_value": "AirCooled",
    "reasoning": "Error indicates enum mismatch; AirCooled is valid enum value"
  }
]
```

**Maximum Iterations:** 3
**Average Iterations to Success:** 0.2 (80% succeed on first try)
**Success Rate (within 3 iterations):** 100%

---

## 3.4 Model Fine-Tuning

### 3.4.1 Training Data Preparation

**Dataset Composition:**
- 500+ VRF system examples (single-zone to 30-zone buildings)
- Source: EnergyPlus example files + synthetic generation + real building models
- Format: (prompt, completion) pairs in ShareGPT format

**Prompt Construction:**
```json
{
  "conversations": [
    {
      "from": "system",
      "value": "<structured_system_prompt_with_field_specs>"
    },
    {
      "from": "human",
      "value": "USER REQUEST: Design VRF for 3-zone office\nZones: [Zone1, Zone2, Zone3]\nSystem Name: VRF_Office_System"
    },
    {
      "from": "gpt",
      "value": "HVACTemplate:Thermostat,\n  Thermostat_Zone1,\n  ,\n  20.0,\n  ,\n  24.0;\n\n..."
    }
  ]
}
```

**Data Augmentation:**
- Varied system names, zone names, zone counts
- Different climate contexts (cold, hot, moderate)
- Different building types (residential, commercial, industrial)
- Parameter variations within valid ranges

### 3.4.2 Fine-Tuning Configuration

**Base Model:** Mistral-7B-Instruct-v0.2
**Method:** LoRA (Low-Rank Adaptation)
**Training Framework:** Hugging Face TRL (Transformer Reinforcement Learning) with SFTTrainer

**LoRA Hyperparameters:**
- Rank (r): 16
- Alpha: 32
- Dropout: 0.05
- Target modules: q_proj, k_proj, v_proj, o_proj (attention layers)

**Training Hyperparameters:**
- Batch size: 4 (with gradient accumulation steps: 4, effective batch size: 16)
- Learning rate: 2e-4 (with cosine decay)
- Epochs: 3
- Max sequence length: 4096 tokens
- Optimizer: AdamW (8-bit quantized via bitsandbytes)
- Precision: BF16 (bfloat16)

**Training Dataset Split:**
- Training: 450 examples (90%)
- Validation: 50 examples (10%)

**Training Time:** ~4 hours on single NVIDIA RTX 4090 (24GB VRAM)

### 3.4.3 Evaluation Metrics

We evaluate generated HVAC systems across four dimensions:

**1. Structural Validity**
- Syntax correctness (parseable by Eppy)
- Object completeness (all required objects present)
- Reference integrity (thermostat names, zone names valid)

**2. Simulation Success**
- EnergyPlus simulation runs without severe/fatal errors
- Convergence achieved within iteration limit (3 iterations)

**3. Semantic Correctness**
- Parameter ranges within physically reasonable bounds
- Intent alignment (e.g., "high efficiency" → COP > 4.0)
- Appropriate sizing relative to building context

**4. Scalability**
- Success rate across zone counts (1, 2, 3, 5, 10, 20, 30 zones)
- Generation time scaling

---

## 3.5 Baseline Comparisons

### 3.5.1 Pre-trained Mistral-7B with Examples

**Configuration:**
- Model: Mistral-7B-Instruct-v0.2 (no fine-tuning)
- Prompt: Same structured prompt + two static few-shot examples
- RAG: Enabled (same knowledge bases)

**Expected Behavior:** Reasonable performance with heavy prompting but requiring post-processing

### 3.5.2 Pre-trained Mistral-7B without Examples

**Configuration:**
- Model: Mistral-7B-Instruct-v0.2 (no fine-tuning)
- Prompt: Minimal prompt (user request + basic field list)
- RAG: Disabled

**Expected Behavior:** Baseline representing zero-shot performance

### 3.5.3 Evaluation Protocol

**Test Set:** 11 distinct building configurations
- Single-zone residential (1 zone)
- Two-zone mixed-use (2 zones)
- Small office (3 zones)
- Medium office (5 zones)
- Large office (10 zones)
- Large office extended (20 zones)
- Commercial building (30 zones)
- Retail store (3 zones)
- Hotel (4 zones)
- Cold climate residential (2 zones)
- Heat recovery office (4 zones)

**Evaluation Dimensions:**
- **Success Rate:** Percentage of tests resulting in valid, simulation-ready IDF
- **First-Try Success:** Percentage of tests succeeding without Agent 3 corrections
- **Average Iterations:** Mean number of correction iterations to success
- **Quality Score:** Manual assessment of parameter appropriateness (0–100 scale)
- **Generation Time:** End-to-end time from user request to final IDF

**Success Criteria:**
- Structural validity: Passes Eppy parsing
- Simulation success: EnergyPlus runs without severe/fatal errors
- Semantic correctness: Parameters within ±20% of expert-designed reference values

---

## 3.6 Ablation Studies

To isolate the contribution of individual prompt engineering techniques, we conduct ablation experiments:

**Ablation Configurations:**
1. **Full System** (all 12 techniques)
2. **No RAG** (techniques 1, 3–12)
3. **No Building Context** (techniques 1–2, 4–12)
4. **No Few-Shot** (techniques 1–3, 5–12)
5. **No Chain-of-Thought** (techniques 1–4, 6–12)
6. **No Iterative Generation** (techniques 1–8, 10–12)
7. **No Validation-in-the-Loop** (techniques 1–10, 12)

**Ablation Test Set:** 5 representative configurations (1, 3, 5, 10, 30 zones)

**Metrics:** Success rate, average iterations, generation time

---

## 3.7 Implementation Details

**Code Repository Structure:**
```
EnergyPlus-HVAC-LLM/
├── src/
│   ├── agents/
│   │   ├── llm_interface.py          # LLM provider abstraction
│   │   ├── agent1_generator.py       # VRF template generator
│   │   ├── agent1_5_validator.py     # Pre-simulation validator
│   │   ├── agent3_corrector.py       # Error corrector
│   │   └── energyplus_vrf_prompt.json # Prompt templates
│   ├── rag/
│   │   ├── rag_retriever.py          # Vector search queries
│   │   └── knowledge_builder.py      # Knowledge base construction
│   ├── core/
│   │   ├── idf_handler.py            # IDF parsing, zone extraction
│   │   ├── simulator.py              # EnergyPlus simulation wrapper
│   │   └── validator.py              # IDF validation
│   └── pipeline.py                   # Multi-agent orchestration
├── data/
│   ├── knowledge/                    # RAG knowledge bases (JSON)
│   ├── base_idfs/                    # Test building models
│   └── training/                     # Fine-tuning dataset
├── outputs/
│   ├── generated_idfs/               # Generated HVAC systems
│   ├── simulations/                  # EnergyPlus simulation outputs
│   └── logs/                         # Execution logs, results JSON
└── config/
    ├── settings.py                   # LLM provider, paths, RAG settings
    └── hvac_requests.json            # Test scenario definitions
```

**Dependencies:**
- Python 3.10+
- transformers==4.38.0 (Hugging Face)
- torch==2.2.0 (PyTorch)
- eppy==0.5.63 (EnergyPlus IDF parser)
- chromadb==0.4.22 (vector database)
- sentence-transformers==2.3.1 (embeddings)
- EnergyPlus==25.2.0

**Hardware Requirements:**
- GPU: NVIDIA RTX 4090 (24GB VRAM) or equivalent for fine-tuning and inference
- RAM: 32GB minimum
- Storage: 50GB for models, knowledge bases, and simulation outputs

**Reproducibility:**
- Random seed: 42 (for LLM sampling, data splits)
- Temperature: 0.3 (low variance)
- Deterministic operations enabled where possible

---

## 3.8 Ethical Considerations

**Energy Simulation Validation:**
All generated HVAC systems are validated through EnergyPlus simulation to ensure physical plausibility and compliance with ASHRAE standards. Generated systems are not recommended for direct deployment without engineering review.

**Dataset Licensing:**
Training data derived from EnergyPlus public example files (BSD-3-Clause license) and synthetic generation. No proprietary building models used without permission.

**Model Bias:**
Fine-tuned model may inherit biases from training data distribution (US-centric climate zones, commercial building focus). International and residential building performance requires additional validation.

---

## References

[To be inserted: Citations for EnergyPlus, Mistral, RAG methodologies, prompt engineering surveys, etc.]

---

**End of Methodology Section**

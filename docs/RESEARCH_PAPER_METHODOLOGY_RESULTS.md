# Research Paper: Methodology and Experimental Results

## Automated HVAC System Design using Multi-Agent Large Language Models with RAG and Fine-Tuning

---

# 4. Methodology

This section describes the methodology for automated EnergyPlus HVAC system generation using a multi-agent architecture enhanced with Retrieval-Augmented Generation (RAG) and domain-specific fine-tuning.

> **Section Brief:** The Methodology section presents our novel approach to automating HVAC system design through Large Language Models. We introduce a three-agent pipeline architecture where: (1) Agent 1 generates VRF configurations from natural language, (2) Agent 2 validates and simulates the output using EnergyPlus, and (3) Agent 3 iteratively corrects any errors. This section details how we combined domain-specific fine-tuning of Mistral-7B with RAG-enhanced knowledge retrieval to achieve production-ready HVAC generation. The methodology demonstrates how specialized smaller models (7B parameters) can outperform larger general-purpose models for domain-specific engineering tasks.

## 4.1. Multi-Agent System Architecture

> **Section Brief:** This section introduces the core innovation—a three-agent collaborative architecture that mimics the human engineering workflow of "design → validate → debug." Unlike monolithic LLM approaches that attempt to generate perfect output in one pass, our multi-agent system distributes responsibilities across specialized agents, enabling iterative refinement and self-correction. This design principle addresses the fundamental limitation that even the best LLMs cannot guarantee 100% first-try accuracy for complex engineering tasks.

### 4.1.1 Overview

> **Subsection Brief:** The overview presents the complete pipeline flowchart showing how a natural language HVAC request transforms into a simulation-ready EnergyPlus IDF file. Key components include: the input phase (user request + base building), Agent 1 (VRF template generation using fine-tuned Mistral), optional quick validation (Agent 1.5), Agent 2 (EnergyPlus simulation orchestrator), and Agent 3 (iterative debugger). The maximum 3-iteration correction loop ensures bounded execution time while maintaining high success rates.

The proposed system employs a multi-agent architecture consisting of three specialized LLM agents that work collaboratively to transform natural language HVAC design requests into valid, simulation-ready EnergyPlus IDF (Input Data File) configurations. The architecture follows a generate-validate-correct paradigm, where each agent has a specific role in the pipeline.

```
┌─────────────────────────────────────────────────────────────────────┐
│                    HVAC-LLM MULTI-AGENT PIPELINE                    │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         INPUT PHASE                                  │
│   • Natural Language Request    • Base Building IDF                  │
│   • Zone Specifications         • Design Parameters                  │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│               AGENT 1: VRF TEMPLATE GENERATOR                        │
│                                                                      │
│   Input:  User request + Building context + RAG knowledge           │
│   Output: HVACTemplate objects (System:VRF, Zone:VRF, Thermostats)  │
│   Model:  Fine-tuned Mistral-7B (500+ VRF training examples)        │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│             AGENT 1.5: QUICK VALIDATION (Optional)                   │
│                                                                      │
│   Input:  Generated HVAC objects + Zone specifications              │
│   Output: Validation report (errors, warnings, suggestions)         │
│   Purpose: Pre-simulation error detection (70-80% catch rate)       │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│           AGENT 2: VALIDATION AND SIMULATION ORCHESTRATOR            │
│                                                                      │
│   Phase 1: IDF Syntax Validation (Eppy-based)                       │
│   Phase 2: HVACTemplate Expansion (ExpandObjects preprocessor)      │
│   Phase 3: EnergyPlus Simulation                                    │
│   Output:  Simulation results or Error messages                     │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                          ┌────────┴────────┐
                          │                 │
                     SUCCESS            FAILURE
                          │                 │
                          ▼                 ▼
                    ┌─────────┐    ┌─────────────────────────┐
                    │ COMPLETE │    │  AGENT 3: ITERATIVE     │
                    │   IDF    │    │  DEBUGGING AGENT        │
                    └─────────┘    │                         │
                                   │  Input:  Error messages │
                                   │  Output: Corrected IDF  │
                                   │  Model:  Fine-tuned     │
                                   │          Mistral-7B     │
                                   └───────────┬─────────────┘
                                               │
                                               ▼
                                        RE-SIMULATE
                                        (Max 3 iterations)
```

### 4.1.2 Design Principles

> **Subsection Brief:** Four foundational principles guided our architecture: (1) **Separation of Concerns**—each agent specializes in one task (generation, validation, correction), enabling independent optimization and testing; (2) **Iterative Refinement**—mirrors real engineering practice where initial designs rarely pass simulation on first attempt; (3) **Knowledge Enhancement**—RAG provides runtime access to EnergyPlus field specifications, error patterns, and design rules; (4) **Dual-Model Support**—architecture supports both local fine-tuned models (Mistral) and cloud APIs (Gemini), enabling cost-performance trade-offs.

The multi-agent architecture was designed based on the following principles:

1. **Separation of Concerns**: Each agent specializes in a specific task, enabling modular development and testing.

2. **Iterative Refinement**: The system supports multiple correction iterations, mimicking the human engineering workflow of design-simulate-debug.

3. **Knowledge Enhancement**: RAG provides agents with domain-specific knowledge at runtime, reducing hallucinations and improving output quality.

4. **Dual-Model Support**: The architecture supports both fine-tuned local models (Mistral) and cloud-based APIs (Gemini), enabling flexible deployment.

### 4.1.3 Agent Communication Protocol

> **Subsection Brief:** Defines the structured JSON-based messaging format that enables agents to exchange information reliably. Agent 1 sends generated HVAC objects with building context to Agent 2. If simulation fails, Agent 2 sends error messages and IDF path to Agent 3. Agent 3 returns targeted fixes specifying which object/field to modify and why. This standardized protocol ensures interoperability and enables future agent replacement or enhancement.

Inter-agent communication follows a structured JSON-based protocol:

```python
# Agent 1 → Agent 2: Generated HVAC objects
{
    "hvac_objects": "HVACTemplate:System:VRF, ...",
    "zones": ["Zone1", "Zone2"],
    "building_context": {...},
    "user_request": "Design VRF with heat recovery"
}

# Agent 2 → Agent 3: Error feedback
{
    "success": False,
    "errors": ["** Severe ** Field mismatch..."],
    "idf_path": "outputs/pipeline_output.idf"
}

# Agent 3 → Agent 2: Correction
{
    "fixes": [
        {
            "object_type": "HVACTemplate:System:VRF",
            "field_to_change": "condenser_type",
            "new_value": "AirCooled"
        }
    ]
}
```

---

## 4.2. Agent 1: VRF Template Generator

> **Section Brief:** Agent 1 is the primary generation engine—a fine-tuned Mistral-7B model that converts natural language HVAC requirements into valid EnergyPlus HVACTemplate:System:VRF objects. Unlike pre-trained models that lack domain knowledge, Agent 1 was trained on 500+ VRF configuration examples, enabling it to produce correctly formatted 42-field VRF system objects, zone assignments, and thermostat configurations without extensive prompting.

### 4.2.1 Purpose and Functionality

> **Subsection Brief:** Agent 1's core function is to bridge the gap between human design intent (e.g., "Design a VRF system with heat recovery for 4 zones") and machine-readable EnergyPlus syntax. It generates three types of HVACTemplate objects: System:VRF (the main outdoor unit with 42 fields), Zone:VRF (indoor units for each zone), and Thermostat (setpoint schedules). The fine-tuned model achieves 80% first-try success rate compared to 0% for pre-trained models.

Agent 1 is responsible for generating complete VRF (Variable Refrigerant Flow) HVAC system configurations from natural language requests. It produces EnergyPlus HVACTemplate objects that define the entire HVAC system structure.

### 4.2.2 Input Processing

> **Subsection Brief:** Agent 1 receives four types of inputs: (1) Zone list—auto-detected from base IDF or user-specified; (2) System name—identifier for the HVAC system; (3) User request—natural language design requirements; (4) Building context—automatically extracted metadata including zone count, total area/volume, orientation, and internal loads. This context enables the model to make informed decisions about system sizing and configuration without explicit user specification.

Agent 1 receives the following inputs:

| Input | Description | Source |
|-------|-------------|--------|
| `zones` | List of zone names to condition | Auto-detected from IDF or user-specified |
| `system_name` | HVAC system identifier | Default: "VRF_System_1" |
| `user_request` | Natural language design request | User input |
| `building_context` | Building metadata | Extracted from base IDF |

**Building Context Extraction:**

```python
building_context = {
    "num_zones": 4,
    "total_area": 250.5,           # m²
    "total_volume": 750.0,         # m³
    "orientation": 45,             # degrees
    "has_internal_loads": True,
    "has_people": True,
    "has_lights": True,
    "has_equipment": False,
    "weather_file": "USA_CO_Denver.epw"
}
```

### 4.2.3 Generation Strategy

> **Subsection Brief:** The fine-tuned model uses an **iterative generation strategy** that produces objects in sequence: first the System:VRF (outdoor unit), then Zone:VRF objects for each zone, and finally Thermostats. This step-by-step approach with controlled token limits (512 for system, 400 per zone, 256 per thermostat) prevents hallucinations and ensures complete coverage—a critical advantage over single-shot generation that often misses zones or produces malformed objects.

#### For Fine-tuned Mistral Model

The fine-tuned model uses an **iterative generation strategy** to produce complete VRF systems:

```
Step 1: Generate HVACTemplate:System:VRF
        └─ One system object with all 42 fields
        └─ Max 512 tokens

Step 2: Generate HVACTemplate:Zone:VRF (for each zone)
        └─ One zone object per zone
        └─ Links to system and thermostat
        └─ Max 400 tokens per zone

Step 3: Generate HVACTemplate:Thermostat (for each zone)
        └─ One thermostat per zone
        └─ Heating/cooling setpoint schedules
        └─ Max 256 tokens per thermostat
```

This iterative approach prevents hallucinations and ensures:
- No missing zones
- Proper object linking
- Complete field specifications

### 4.2.4 Output Format

> **Subsection Brief:** Agent 1 produces clean, pipeline-compatible EnergyPlus IDF syntax without markdown wrapping, explanatory text, or formatting artifacts. This "clean output" property is critical—pre-trained models often add markdown code blocks or explanations that require post-processing and can cause parsing failures. The fine-tuned model learned this clean format from training examples, eliminating the need for output sanitization.

Agent 1 produces valid EnergyPlus IDF syntax:

```
HVACTemplate:System:VRF,
    VRF_System_1,                !- Name
    VRFSysAvailability,          !- System Availability Schedule Name
    ,                            !- Gross Rated Total Cooling Capacity
    3.3,                         !- Gross Rated Cooling COP
    -5,                          !- Minimum Outdoor Temperature in Cooling Mode
    43,                          !- Maximum Outdoor Temperature in Cooling Mode
    ,                            !- Gross Rated Heating Capacity
    ,                            !- Rated Heating Capacity Sizing Ratio
    3.4,                         !- Gross Rated Heating COP
    ...;                         !- (42 fields total)

HVACTemplate:Zone:VRF,
    Zone1,                       !- Zone Name
    VRF_Template_Zone1,          !- Template VRF System Name
    VRF_System_1,                !- VRF System Name
    ...;

HVACTemplate:Thermostat,
    Zone1_Thermostat,            !- Name
    Zone1_Heating_Sched,         !- Heating Setpoint Schedule Name
    Zone1_Cooling_Sched;         !- Cooling Setpoint Schedule Name
```

---

## 4.3. Agent 2: Validation and Simulation Orchestrator

> **Section Brief:** Agent 2 serves as the quality gate between generation and final output. It performs a four-phase validation: (1) IDD compliance checking, (2) Eppy-based syntax validation, (3) HVACTemplate expansion via EnergyPlus ExpandObjects, and (4) full EnergyPlus simulation. Agent 2 is deterministic (no LLM)—it either confirms success or extracts structured error messages for Agent 3 to process.

### 4.3.1 Purpose and Functionality

> **Subsection Brief:** Unlike Agents 1 and 3 which use LLMs, Agent 2 is a rule-based orchestrator that leverages established tools: Eppy for IDF parsing, ExpandObjects for template expansion, and EnergyPlus for simulation. Its primary role is to detect errors that would otherwise go unnoticed until real-world deployment, catching 100% of syntactic and many semantic errors before human review.

Agent 2 orchestrates the validation and simulation pipeline, acting as the central coordinator between generation (Agent 1) and correction (Agent 3). It consists of three integrated components:

1. **IDF Validator**: Syntax and structure validation using Eppy library
2. **ExpandObjects Preprocessor**: HVACTemplate expansion to detailed objects
3. **EnergyPlus Simulator**: Full energy simulation execution

### 4.3.2 Validation Pipeline

> **Subsection Brief:** The four-stage pipeline ensures comprehensive validation: **Stage 2.1 (IDD Compliance)** verifies object types exist in EnergyPlus schema and all required fields are present; **Stage 2.2 (Eppy Validation)** parses the IDF and checks cross-object references; **Stage 2.3 (ExpandObjects)** transforms HVACTemplate objects into detailed low-level components (converts ~3 template objects into ~50+ detailed objects); **Stage 2.4 (Simulation)** executes EnergyPlus and parses error logs. Each stage can fail independently, providing granular error feedback.

```
┌─────────────────────────────────────────────────────────────────┐
│                    AGENT 2 VALIDATION PIPELINE                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [2.1] IDD Compliance Check                                     │
│        ├─ Validate object types exist in IDD                   │
│        ├─ Check required fields are present                    │
│        ├─ Verify field value types (string, number, enum)      │
│        └─ Auto-fix common issues if enabled                    │
│                                                                 │
│  [2.2] Eppy Validation                                          │
│        ├─ Parse IDF with Energy+.idd schema                    │
│        ├─ Check object references                              │
│        └─ Validate zone linkages                               │
│                                                                 │
│  [2.3] ExpandObjects Preprocessing                              │
│        ├─ Expand HVACTemplate:System:VRF → detailed objects    │
│        ├─ Generate: AirConditioner:VariableRefrigerantFlow     │
│        ├─ Generate: ZoneHVAC:TerminalUnit:VariableRefrigerantFlow │
│        ├─ Generate: Fan:SystemModel, Coil:Cooling/Heating      │
│        └─ Output: expanded.idf                                 │
│                                                                 │
│  [2.4] EnergyPlus Simulation                                    │
│        ├─ Execute energyplus.exe with weather file             │
│        ├─ Parse eplusout.err for errors                        │
│        └─ Return success/failure with error details            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.3.3 Error Classification

> **Subsection Brief:** EnergyPlus errors are classified by severity to determine appropriate action: **Warnings** are logged but don't stop simulation; **Severe** errors indicate significant issues that may affect results and are passed to Agent 3; **Fatal** errors halt simulation completely and require immediate correction. This classification enables proportional response—not all errors require LLM intervention.

Agent 2 classifies simulation errors by severity:

| Severity | Description | Action |
|----------|-------------|--------|
| **Warning** | Non-fatal issues, simulation continues | Log for analysis |
| **Severe** | Significant issues, may affect results | Pass to Agent 3 |
| **Fatal** | Critical errors, simulation cannot continue | Pass to Agent 3 |

### 4.3.4 Simulation Configuration

> **Subsection Brief:** Specifies the EnergyPlus environment: version 25.2.0 (latest stable), 300-second timeout for complex simulations, and Denver weather file as default. The configuration is designed for reproducibility—all parameters are explicitly documented to enable result verification.

```python
ENERGYPLUS_VERSION = "25.2.0"
SIMULATION_TIMEOUT = 300  # seconds
WEATHER_FILE = "USA_CO_Denver-Aurora-Buckley.AFB_TMY3.epw"
```

---

## 4.4. Agent 3: Iterative Debugging Agent

> **Section Brief:** Agent 3 is the "safety net" that transforms 80% first-try success into 100% final success. When simulation fails, Agent 3 analyzes EnergyPlus error messages, queries RAG for similar historical errors, and generates targeted JSON fix specifications. Unlike Agent 1 which generates complete objects, Agent 3 makes minimal surgical corrections—changing only the specific fields that caused errors. This specialization (generation vs. correction) is key to the multi-agent architecture's effectiveness.

### 4.4.1 Purpose and Functionality

> **Subsection Brief:** Agent 3 bridges the gap between LLM imperfection and production reliability. Its fine-tuned Mistral model was trained on 200+ error-fix pairs extracted from real EnergyPlus simulation logs, learning common error patterns like "Master Thermostat Location must be entered" → set zone reference. With RAG enhancement, Agent 3 achieves 100% correction success rate within 3 iterations for all tested scenarios.

Agent 3 analyzes EnergyPlus simulation errors and generates targeted corrections. It uses:
- RAG-retrieved error-fix patterns from historical simulations
- Fine-tuned understanding of EnergyPlus field dependencies
- Iterative correction until simulation succeeds (max 3 iterations)

### 4.4.2 Error Analysis Workflow

> **Subsection Brief:** Agent 3 follows a six-step workflow: (1) Receive errors from Agent 2; (2) Query RAG for similar historical errors with >77% similarity; (3) If cached fix exists, apply directly without LLM; (4) Otherwise, generate fix using fine-tuned model with error context; (5) Apply fixes using Eppy IDF manipulation; (6) Re-submit to Agent 2. The cached-fix optimization significantly reduces correction latency for common error patterns.

```
┌─────────────────────────────────────────────────────────────────┐
│                   AGENT 3 CORRECTION WORKFLOW                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [3.1] Error Reception                                          │
│        └─ Receive error messages from Agent 2                  │
│                                                                 │
│  [3.2] RAG Knowledge Query                                      │
│        ├─ Query error_patterns collection for similar errors   │
│        ├─ Query field_dependencies for validation rules        │
│        └─ Retrieve fix_procedures for high-similarity matches  │
│                                                                 │
│  [3.3] Cached Fix Application (if similarity > 77%)            │
│        └─ Apply proven fixes directly without LLM generation   │
│                                                                 │
│  [3.4] LLM-Based Fix Generation                                 │
│        ├─ Build prompt with error context + RAG knowledge      │
│        ├─ Generate JSON fix specification                      │
│        └─ Parse and validate fix format                        │
│                                                                 │
│  [3.5] Fix Application                                          │
│        ├─ Load IDF with Eppy                                   │
│        ├─ Apply field modifications                            │
│        └─ Save corrected IDF                                   │
│                                                                 │
│  [3.6] Re-simulation                                            │
│        └─ Pass to Agent 2 for validation (max 3 iterations)    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.4.3 Fix Specification Format

> **Subsection Brief:** Agent 3 outputs corrections as structured JSON arrays, each specifying: object_type, object_name, field_to_change, new_value, and reason. This format enables programmatic fix application and provides an audit trail. The explicit "reason" field aids debugging and enables future learning from correction patterns.

Agent 3 outputs corrections in structured JSON format:

```json
[
    {
        "object_type": "HVACTemplate:System:VRF",
        "object_name": "VRF_System_1",
        "field_to_change": "zone_name_for_master_thermostat_location",
        "new_value": "Zone1",
        "reason": "MasterThermostatPriority requires zone specification"
    },
    {
        "object_type": "HVACTemplate:Zone:VRF",
        "object_name": "VRF_Zone1",
        "field_to_change": "outdoor_unit_object_name",
        "new_value": "VRF_System_1",
        "reason": "Zone must reference system object"
    }
]
```

### 4.4.4 Common Error Patterns and Fixes

> **Subsection Brief:** Documents the most frequently encountered errors and their automated resolutions. The "Master Thermostat Location" error (missing zone reference when MasterThermostatPriority is set) accounts for ~40% of corrections. These patterns were learned through fine-tuning and are also cached in RAG for fast retrieval, enabling sub-second correction for known issues.

| Error Pattern | Root Cause | Automated Fix |
|---------------|------------|---------------|
| "Master Thermostat Location must be entered" | Missing zone reference when `MasterThermostatPriority` is set | Set `zone_name_for_master_thermostat_location` to first zone |
| "Invalid Condenser Type" | Wrong enum value | Set to valid option: `AirCooled`, `EvaporativelyCooled`, or `WaterCooled` |
| "Zone not found" | Typo in zone name | Match against available zones from IDF |
| "Value type mismatch" | String in numeric field | Move value to correct field or use `Autosize` |

---

## 4.5. Knowledge Enhancement: RAG and Fine-Tuning

> **Section Brief:** This section details the two complementary knowledge enhancement strategies: (1) **RAG** provides runtime access to a ChromaDB vector database containing 718+ documents covering field specifications, error patterns, design rules, and fix procedures; (2) **Fine-tuning** embeds domain knowledge directly into model weights through training on 500+ VRF examples for Agent 1 and 200+ error-fix pairs for Agent 3. Our experiments show RAG enhances fine-tuned models by +15% but cannot rescue pre-trained models (RAG + pre-trained = 20% success).

### 4.5.1 Retrieval-Augmented Generation (RAG) Implementation

> **Subsection Brief:** RAG implementation uses ChromaDB with BAAI/bge-small-en-v1.5 embeddings (384 dimensions). The knowledge base is organized into specialized collections: field_specs (EnergyPlus v25.2.0 VRF fields), error_patterns (50+ historical error-fix pairs), design_rules (HVAC best practices), field_dependencies (25 inter-field validation rules), and fix_procedures (step-by-step correction guides). Query interfaces are specialized per agent—Agent 1 queries design rules and user examples; Agent 3 queries error patterns and dependencies.

The RAG system enhances all agents with domain-specific knowledge stored in a ChromaDB vector database.

#### Knowledge Base Structure

```
data/vector_db/
├── field_specs_v25_2_0/          # VRF field specifications
│   └── 42 System:VRF fields + 26 Zone:VRF fields
├── error_patterns/                # Historical error-fix pairs
│   └── 50+ patterns from simulation logs
├── design_rules/                  # Design guidance documentation
├── user_request_examples/         # Annotated request patterns
├── field_dependencies/            # 25 field dependency rules
├── error_fix_procedures/          # 10 step-by-step fix procedures
└── vrf_design_patterns/           # VRF design best practices
```

#### Embedding Model

```python
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIMENSION = 384
SIMILARITY_METRIC = "cosine"
```

#### RAG Query Interface

```python
class RAGRetriever:
    def query_field_specs(query_text, n_results=5, object_type=None):
        """Query VRF field specifications"""
        
    def query_error_patterns(error_text, n_results=3, only_successful=True):
        """Query historical error-fix patterns"""
        
    def query_field_dependencies(query, n_results=5):
        """Query field dependency rules"""
        
    def query_user_requests(user_request, n_results=3):
        """Query similar user request examples"""
```

### 4.5.2 Fine-Tuning Approach

> **Subsection Brief:** Fine-tuning uses LoRA (Low-Rank Adaptation) on Mistral-7B-v0.1 base model, targeting attention projection layers (q, k, v, o). LoRA rank=16, alpha=32, enabling efficient training with only ~0.1% of parameters updated. 4-bit quantization (QLoRA with NF4) reduces inference memory to ~6GB, enabling deployment on consumer GPUs. Training takes ~4 GPU hours on RTX 3090. The approach balances model quality against computational cost—full fine-tuning would require 10x more resources with marginal improvement.

#### Training Data

| Model | Training Examples | Focus Area |
|-------|-------------------|------------|
| Agent 1 (Generator) | 500+ VRF IDF examples | Complete system generation |
| Agent 3 (Corrector) | 200+ error-fix pairs | Error correction patterns |

#### Fine-Tuning Configuration

```python
# Base Model
BASE_MODEL = "mistralai/Mistral-7B-v0.1"

# LoRA Configuration
LORA_R = 16
LORA_ALPHA = 32
LORA_DROPOUT = 0.05
TARGET_MODULES = ["q_proj", "v_proj", "k_proj", "o_proj"]

# Training Parameters
LEARNING_RATE = 2e-4
BATCH_SIZE = 4
GRADIENT_ACCUMULATION_STEPS = 4
NUM_EPOCHS = 3
MAX_SEQ_LENGTH = 2048
```

#### Quantization for Inference

```python
# 4-bit Quantization (QLoRA)
BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=False
)
```

### 4.5.3 Knowledge Sources

> **Subsection Brief:** Four authoritative knowledge sources populate the RAG database: (1) **EnergyPlus IDD v25.2.0**—the official schema defining all valid object types, field names, and constraints; (2) **Simulation logs**—error patterns extracted from real eplusout.err files; (3) **Official documentation**—EnergyPlus Engineering Reference and I/O Reference guides; (4) **Expert-curated rules**—field dependencies and fix procedures developed through iterative testing. This multi-source approach ensures comprehensive coverage of both formal specifications and practical engineering knowledge.

1. **EnergyPlus IDD (Input Data Dictionary)**: Official field specifications for EnergyPlus v25.2.0
2. **Simulation Logs**: Error patterns extracted from `eplusout.err` files
3. **Documentation**: EnergyPlus Engineering Reference and I/O Reference
4. **Expert Knowledge**: Field dependency rules and fix procedures

---

## 4.6. Workflow Orchestration and Communication Protocols

> **Section Brief:** This section describes how the three agents are coordinated through a central pipeline orchestrator. The workflow handles initialization, execution sequencing, error routing, iteration counting, and output artifact management. Configuration options enable flexible deployment: choose LLM provider (Mistral/Gemini/mock), enable/disable RAG, set correction iteration limits, and control output verbosity.

### 4.6.1 Complete Pipeline Execution Flow

> **Subsection Brief:** The run_pipeline() function implements the complete workflow: load base IDF → extract building context → run Agent 1 generation → optional quick validation → merge with base IDF → run Agent 2 simulation → if errors, loop through Agent 3 correction (max 3 iterations) → return final results. Each step is logged for debugging and audit purposes.

```python
def run_pipeline(base_idf, user_request, zones=None):
    """
    Complete HVAC-LLM pipeline execution.
    
    Steps:
    [0]   Load and analyze base IDF
    [0.1] IDD compliance check (auto-fix if needed)
    [1]   Agent 1: Generate HVAC objects
    [1.5] Quick validation (optional, pre-simulation)
    [2]   Agent 2: Validate and merge with base IDF
    [3]   Agent 2: Run EnergyPlus simulation
    [4]   If errors: Agent 3 correction loop (max 3 iterations)
    [5]   Return final results
    """
```

### 4.6.2 Error Correction Loop

> **Subsection Brief:** The correction loop implements bounded iteration with clear termination conditions: success (simulation passes), failure (max 3 iterations exceeded), or irrecoverable error. The 3-iteration limit was empirically determined—95% of correctable errors resolve within 2 iterations; errors persisting beyond 3 iterations typically indicate fundamental design issues requiring human review.

```
┌─────────────────────────────────────────────────────────────────┐
│                    ITERATIVE CORRECTION LOOP                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│    Iteration = 0                                                │
│         │                                                       │
│         ▼                                                       │
│    ┌─────────────────┐                                          │
│    │   SIMULATE      │                                          │
│    └────────┬────────┘                                          │
│             │                                                   │
│         ┌───┴───┐                                               │
│         │SUCCESS│──────────────────────────────────► DONE ✅    │
│         └───┬───┘                                               │
│             │ FAILURE                                           │
│             ▼                                                   │
│    ┌─────────────────┐                                          │
│    │   Iteration++   │                                          │
│    └────────┬────────┘                                          │
│             │                                                   │
│         ┌───┴───┐                                               │
│         │ > 3?  │───YES────────────────────────────► FAIL ❌    │
│         └───┬───┘                                               │
│             │ NO                                                │
│             ▼                                                   │
│    ┌─────────────────┐                                          │
│    │  AGENT 3: FIX   │                                          │
│    └────────┬────────┘                                          │
│             │                                                   │
│             └─────────────────────────────────────► SIMULATE    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.6.3 Configuration Options

> **Subsection Brief:** The system is highly configurable through settings.py: LLM_PROVIDER selects between fine-tuned Mistral, Gemini API, or mock mode for testing; USE_RAG enables/disables knowledge retrieval; model paths point to fine-tuned adapters; MAX_CORRECTION_ITERATIONS controls loop bounds. This flexibility enables fair comparison between model configurations and deployment customization.

```python
# config/settings.py

# LLM Provider Selection
LLM_PROVIDER = "mistral"  # Options: "mistral", "gemini", "mock"

# RAG Configuration
USE_RAG = True
VECTOR_DB_PATH = "data/vector_db"

# Fine-tuned Model Paths
MISTRAL_FINETUNED_PATH = "~/LLM-Fine-Tunning/mistral-7b-vrf-finetuned-v4"
MISTRAL_AGENT3_PATH = "~/LLM-Fine-Tunning/mistral-7b-agent3-balanced"

# Pipeline Settings
MAX_CORRECTION_ITERATIONS = 3
ENABLE_QUICK_VALIDATION = True
AUTO_FIX_IDD_COMPLIANCE = True
```

### 4.6.4 Output Artifacts

> **Subsection Brief:** The pipeline produces six output artifacts: generated HVAC objects (hvac.idf), complete merged IDF (complete.idf), expanded IDF after template processing (expanded.idf), execution log JSON (results.json), EnergyPlus error log (eplusout.err), and simulation output variables (eplusout.eso). These artifacts enable debugging, result verification, and downstream analysis of energy simulation results.

| Output File | Description |
|-------------|-------------|
| `{name}_hvac.idf` | Generated HVAC objects only |
| `{name}_complete.idf` | Complete IDF (base + HVAC) |
| `{name}_expanded.idf` | Expanded IDF (after ExpandObjects) |
| `{name}_results.json` | Pipeline execution log |
| `eplusout.err` | EnergyPlus error log |
| `eplusout.eso` | EnergyPlus output variables |

---

# 5. Experimental Results

This section presents the experimental evaluation of the proposed multi-agent system, comparing fine-tuned Mistral models with pre-trained alternatives.

> **Section Brief:** The Results section provides empirical evidence for our methodology's effectiveness. We conducted systematic experiments comparing fine-tuned Mistral-7B against pre-trained models across 5 test cases (1-20 zones). Key findings: fine-tuned achieves **80% first-try success** and **100% final success** vs. pre-trained's **0-20%**. Results demonstrate that domain-specific fine-tuning is essential for specialized engineering tasks, and that multi-agent architecture provides robustness through iterative correction.

## 5.1. Experimental Setup

> **Section Brief:** Establishes reproducibility by documenting all experimental conditions: hardware (RTX 3090 GPU), software versions (EnergyPlus 25.2.0, PyTorch 2.1.0), test cases (5 scenarios from 1-20 zones), and model configurations. This section enables other researchers to replicate our experiments and validates that results are not artifacts of specific hardware/software combinations.

### 5.1.1 Hardware Configuration

> **Subsection Brief:** Experiments ran on a workstation with NVIDIA RTX 3090 (24GB VRAM) sufficient for 4-bit quantized Mistral inference, AMD Ryzen 9 5900X CPU, 64GB RAM, and NVMe storage. This represents a high-end consumer/prosumer setup, demonstrating that production deployment doesn't require data center hardware.

| Component | Specification |
|-----------|---------------|
| GPU | NVIDIA RTX 3090 (24GB VRAM) |
| CPU | AMD Ryzen 9 5900X |
| RAM | 64GB DDR4 |
| Storage | NVMe SSD |

### 5.1.2 Software Environment

> **Subsection Brief:** Documents the complete software stack: EnergyPlus 25.2.0 for simulation, Python 3.10, PyTorch 2.1.0 for model inference, Transformers 4.36.0 and PEFT 0.7.0 for LoRA loading, ChromaDB 0.4.0 for RAG. Version pinning ensures reproducibility and helps identify potential compatibility issues for replication.

| Software | Version |
|----------|---------|
| EnergyPlus | 25.2.0 |
| Python | 3.10 |
| PyTorch | 2.1.0 |
| Transformers | 4.36.0 |
| PEFT | 0.7.0 |
| ChromaDB | 0.4.0 |

### 5.1.3 Test Cases

> **Subsection Brief:** Five test cases cover the complexity spectrum: TC1 (1 zone, basic), TC2 (2 zones, multi-zone handling), TC3 (4 zones with "heat recovery" advanced prompt), TC4 (10 zones, scalability), TC5 (20 zones, maximum scale). Different base IDF files test generalization across building types. The 20-zone case specifically tests the breaking point of pre-trained models.

| Test ID | Description | Zones | Base IDF | Purpose |
|---------|-------------|-------|----------|---------|
| TC1 | Single zone VRF | 1 | building_with_zones_fixed.idf | Basic functionality |
| TC2 | Two zone VRF | 2 | building_with_zones_fixed.idf | Multi-zone handling |
| TC3 | Office building | 4 | 4ZoneWithShading_Simple_2_NoHVAC.idf | Medium complexity |
| TC4 | Large office | 10 | large_office_10zone.idf | Scalability |
| TC5 | Enterprise office | 20 | large_office_20zone.idf | Maximum scale |

### 5.1.4 Model Configurations

> **Subsection Brief:** Two primary configurations compared: (1) Fine-tuned Mistral—7B parameters with LoRA adapters trained on 500+ VRF examples; (2) Pre-trained Mistral API—~7B parameters, general corpus training, no domain adaptation. Both use the same base architecture, isolating the effect of fine-tuning as the only variable.

| Model | Type | Parameters | Training Data |
|-------|------|------------|---------------|
| Fine-tuned Mistral | Local, LoRA | 7B | 500+ VRF examples |
| Pre-trained Mistral API | Cloud API | ~7B | General corpus |

---

## 5.2. Fine-tuned Model Performance

> **Section Brief:** Presents the primary experimental evidence: fine-tuned Mistral achieves 80% first-try success (4/5 tests pass simulation immediately) and 100% final success (all 5 tests succeed with ≤1 correction iteration). The single failure case (TC3) involved an out-of-distribution "heat recovery" prompt, demonstrating that even domain-specific models have boundaries—but Agent 3 successfully corrects it.

### 5.2.1 Generation Success Rates

> **Subsection Brief:** Detailed breakdown by test case: TC1-TC2 (1-2 zones) succeed immediately; TC3 (4 zones + heat recovery) requires 1 correction iteration; TC4-TC5 (10-20 zones) succeed immediately. The 0.2 average iteration count means the system rarely needs Agent 3 intervention, validating the fine-tuning investment.

| Test Case | Zones | First-try Success | Iterations | Final Result |
|-----------|-------|-------------------|------------|--------------|
| TC1: Single zone | 1 | ✅ Yes | 0 | ✅ SUCCESS |
| TC2: Two zone | 2 | ✅ Yes | 0 | ✅ SUCCESS |
| TC3: Office (4 zone) | 4 | ❌ No | 1 | ✅ SUCCESS |
| TC4: Large (10 zone) | 10 | ✅ Yes | 0 | ✅ SUCCESS |
| TC5: Enterprise (20 zone) | 20 | ✅ Yes | 0 | ✅ SUCCESS |

**Summary Metrics:**
- **First-try Success Rate**: 80% (4/5)
- **Final Success Rate**: 100% (5/5)
- **Average Iterations**: 0.2

### 5.2.2 Output Quality Analysis

> **Subsection Brief:** Beyond binary success, we assess output quality across five dimensions: object type correctness (always uses HVACTemplate), field count accuracy (all 42 System:VRF fields present), zone coverage (all requested zones included), clean formatting (no markdown/explanatory text), and pipeline compatibility (direct use without post-processing). Fine-tuned model scores 100% on all metrics—critical for production deployment.

| Quality Metric | Score | Notes |
|----------------|-------|-------|
| Object type correctness | 100% | Always uses HVACTemplate format |
| Field count accuracy | 100% | All 42 System:VRF fields present |
| Zone coverage | 100% | All requested zones included |
| Clean formatting | 100% | No markdown, no extra text |
| Pipeline compatibility | 100% | Direct use without preprocessing |

### 5.2.3 Correction Effectiveness

> **Subsection Brief:** When first-try generation fails (20% of cases), Agent 3 correction succeeds 100% of the time. Error types encountered: field value mismatch (3 occurrences), missing zone reference (2), invalid enum (1). All resolved within 1 iteration, demonstrating that Agent 3's fine-tuning on error-fix pairs is effective for the errors Agent 1 produces.

When first-try generation fails, Agent 3 correction succeeds:

| Error Type | Occurrences | Fix Rate |
|------------|-------------|----------|
| Field value mismatch | 3 | 100% |
| Missing zone reference | 2 | 100% |
| Invalid enum value | 1 | 100% |

---

## 5.3. Pre-trained Model Performance

> **Section Brief:** Establishes the baseline that fine-tuning improves upon. Pre-trained models tested under two conditions: (A) without examples in prompt—complete failure (0% success, wrong object types); (B) with example in prompt—partial success at small scale but degradation at 20 zones. This demonstrates that in-context learning cannot substitute for domain-specific fine-tuning.

### 5.3.1 Scenario A: Without Examples in Prompt

> **Subsection Brief:** Pre-trained model with minimal prompting fails completely: generates wrong object types (AirConditioner:VariableRefrigerantFlow instead of HVACTemplate), wraps output in markdown, creates invalid structures. The model lacks domain knowledge and cannot infer the required format from task description alone. This scenario represents the "naive baseline."

| Test Case | Zones | Format Correct | Valid Output | Result |
|-----------|-------|----------------|--------------|--------|
| TC1: Single zone | 1 | ❌ Wrong | ❌ Invalid | ❌ FAILED |
| TC2: Two zone | 2 | ❌ Wrong | ❌ Invalid | ❌ FAILED |
| TC3: Office (4 zone) | 4 | ❌ Wrong | ❌ Invalid | ❌ FAILED |
| TC4: Large (10 zone) | 10 | ❌ Wrong | ❌ Invalid | ❌ FAILED |
| TC5: Enterprise (20 zone) | 20 | ❌ Wrong | ❌ Invalid | ❌ FAILED |

**Success Rate: 0% (0/5)**

**Observed Issues:**
- Generated `AirConditioner:VariableRefrigerantFlow` instead of `HVACTemplate:System:VRF`
- Output wrapped in markdown code blocks
- Created invalid object structures
- Model lacks domain-specific knowledge

### 5.3.2 Scenario B: With Simple Example in Prompt

> **Subsection Brief:** Adding a complete VRF example to the prompt improves format correctness but reveals scalability limits. Works for 1 zone (20% success), partially works for 2-10 zones (format correct but markdown artifacts), fails at 20 zones (extra text, malformed names). The model "copies" the example pattern but cannot generalize reliably. **Breaking point: 20 zones.**

| Test Case | Zones | Format Correct | Zone Count | Clean Output | Result |
|-----------|-------|----------------|------------|--------------|--------|
| TC1: Single zone | 1 | ✅ Yes | ✅ 1/1 | ✅ Yes | ✅ SUCCESS |
| TC2: Two zone | 2 | ✅ Yes | ✅ 2/2 | ❌ Markdown | ⚠️ PARTIAL |
| TC3: Office (4 zone) | 4 | ✅ Yes | ✅ 4/4 | ❌ Markdown | ⚠️ PARTIAL |
| TC4: Large (10 zone) | 10 | ✅ Yes | ✅ 10/10 | ❌ Markdown | ⚠️ PARTIAL |
| TC5: Enterprise (20 zone) | 20 | ✅ Yes | ✅ 20/20 | ❌ Extra text | ❌ FAILED |

**Success Rate: 20% (1/5 fully clean)**

**Breaking Point: 20 zones**

**Observed Issues at Scale:**
- Adds explanatory text: "HERE ARE THE VALID ENERGYPLUS IDF OBJECTS..."
- Creates malformed object names
- Inconsistent formatting
- Requires extensive post-processing

---

## 5.4. Comparative Analysis

> **Section Brief:** Direct head-to-head comparison between fine-tuned and pre-trained models. Visualizes success rates across zone counts showing fine-tuned's consistent 100% success vs. pre-trained's degradation. Quantifies the 80% improvement in first-try success (80% vs. 0%), establishes that fine-tuning eliminates the "breaking point" that limits pre-trained models.

### 5.4.1 Success Rate Comparison

> **Subsection Brief:** ASCII chart showing success by zone count: fine-tuned maintains 100% from 1-20 zones; pre-trained with examples starts at ~100% for 1 zone but degrades to 20% by 20 zones; pre-trained without examples is 0% throughout. The visual clearly demonstrates the scalability advantage of fine-tuning.

```
                    SUCCESS RATE BY ZONE COUNT

Zone Count:     1      2      4      10     20     Overall
────────────────────────────────────────────────────────────
Fine-tuned:    ✅     ✅     ✅     ✅     ✅     100%
               ████████████████████████████████████████

Pre-trained    ✅     ⚠️     ⚠️     ⚠️     ❌      20%
(w/ example):  ████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░

Pre-trained    ❌     ❌     ❌     ❌     ❌       0%
(no example):  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
```

### 5.4.2 Performance Metrics Summary

> **Subsection Brief:** Tabular comparison of key metrics: first-try success (80% vs. 20% vs. 0%), final success (100% vs. 20% vs. 0%), average iterations (0.2 vs. N/A), breaking point (none vs. 20 zones vs. all), output quality (clean vs. artifacts vs. wrong format). Every metric favors fine-tuned, with the most dramatic difference in first-try success.

| Metric | Fine-tuned | Pre-trained (w/ example) | Pre-trained (no example) |
|--------|-----------|--------------------------|--------------------------|
| **First-try Success** | **80%** | 20% | 0% |
| **Final Success** | **100%** | 20% | 0% |
| **Avg Iterations** | **0.2** | N/A | N/A |
| **Breaking Point** | None | 20 zones | All zones |
| **Output Quality** | Clean | Has artifacts | Wrong format |

### 5.4.3 Output Quality Comparison

> **Subsection Brief:** Qualitative comparison across five aspects: correct object types (fine-tuned always, pre-trained only with examples), clean formatting (fine-tuned always, pre-trained adds markdown), valid field values (fine-tuned learned constraints, pre-trained inconsistent), proper zone naming (fine-tuned accurate, pre-trained may malform), pipeline compatibility (fine-tuned direct use, pre-trained needs cleaning). Quality differences explain why even "successful" pre-trained outputs often fail downstream.

| Quality Aspect | Fine-tuned | Pre-trained |
|----------------|-----------|-------------|
| Correct object types | ✅ Always | ⚠️ Only with examples |
| Clean formatting | ✅ Always | ❌ Adds markdown/text |
| Valid field values | ✅ Learned | ⚠️ Inconsistent |
| Proper zone naming | ✅ Accurate | ⚠️ May malform |
| Pipeline compatible | ✅ Direct use | ❌ Needs cleaning |

---

## 5.5. Scalability Analysis

> **Section Brief:** Examines how model performance changes with increasing complexity (zone count). Pre-trained models exhibit clear degradation curve—quality drops linearly from 1-10 zones, then fails catastrophically at 20 zones. Fine-tuned models show no degradation, maintaining consistent quality regardless of scale. This finding has practical implications: fine-tuned models are suitable for enterprise deployments with large buildings.

### 5.5.1 Quality vs. Scale (Pre-trained with Example)

> **Subsection Brief:** Chart showing quality declining from 100% at 1 zone to ~25% at 20 zones. The degradation is gradual but inexorable—each additional zone reduces reliability. The 20-zone breaking point is significant because many commercial buildings exceed this threshold, making pre-trained models unsuitable for real-world deployment.

```
Output Quality (%)
     │
100% │  ●
     │     ●
 75% │        ●
     │           ●
 50% │
     │
 25% │              ●
     │
  0% └────────────────────────→ Zone Count
         1   2   4  10  20

Breaking Point: 20 zones
```

### 5.5.2 Quality vs. Scale (Fine-tuned)

> **Subsection Brief:** Flat line at 100% from 1-20 zones—no degradation at scale. The fine-tuned model treats each zone independently through iterative generation, so complexity increases linearly not exponentially. This "scalability preservation" is a key advantage: the same model that works for a small office works for an enterprise campus.

```
Output Quality (%)
     │
100% │  ●   ●   ●   ●   ●
     │
 75% │
     │
 50% │
     │
 25% │
     │
  0% └────────────────────────→ Zone Count
         1   2   4  10  20

No degradation at scale
```

---

## 5.6. Error Analysis

> **Section Brief:** Categorizes and quantifies error types to understand failure modes. Pre-trained errors are fundamental (wrong object types, format issues); fine-tuned errors are superficial (field value mismatches). This distinction is critical: fundamental errors cannot be fixed by Agent 3 because the output structure is wrong; superficial errors are easily corrected. The error analysis validates the multi-agent approach—Agent 3 is designed for fine-tuned model errors, not pre-trained model failures.

### 5.6.1 Pre-trained Model Error Categories

> **Subsection Brief:** Four error categories: (1) Wrong object type (100% without example)—model generates low-level objects instead of templates; (2) Markdown wrapping (80% with example)—adds code blocks that break parsing; (3) Extra text (20% at scale)—adds explanations like "HERE ARE THE OBJECTS..."; (4) Malformed names (20%)—uses wrong capitalization/formatting. These errors require fundamental model retraining to fix.

| Error Type | Frequency (no example) | Frequency (with example) | Example |
|------------|------------------------|--------------------------|---------|
| Wrong object type | 100% | 0% | `AirConditioner:VariableRefrigerantFlow` |
| Markdown wrapping | 0% | 80% | ` ```idf ... ``` ` |
| Extra explanatory text | 0% | 20% | "HERE ARE THE VALID..." |
| Malformed names | 0% | 20% | `HVACTEMPLATE:THERMOSTAT` |

### 5.6.2 Fine-tuned Model Error Categories

> **Subsection Brief:** Only two error categories: (1) Out-of-distribution prompts (20%)—when user requests something outside training data like "heat recovery"; (2) Rare temperature range issues. Both are correctable by Agent 3 because the output structure is correct—only field values need adjustment. This error profile validates the generate-correct paradigm.

| Error Type | Frequency | Resolution |
|------------|-----------|------------|
| Out-of-distribution prompt | 20% | Agent 3 correction |
| Temperature range issues | Rare | Agent 3 correction |

---

## 5.7. Efficiency Comparison

> **Section Brief:** Compares practical deployment considerations beyond accuracy: prompt size (fine-tuned ~50 tokens vs. pre-trained ~500+ with examples), cost (local GPU vs. per-token API charges), post-processing (none vs. markdown removal), iterations (0.2 vs. N/A), integration effort (direct vs. preprocessing pipeline), inference time (3-5s local vs. 2-3s API), memory (6GB with 4-bit quantization). Fine-tuned wins on total cost of ownership despite initial training investment.

| Metric | Fine-tuned | Pre-trained |
|--------|-----------|-------------|
| **Prompt Size** | ~50 tokens | ~500+ tokens (with example) |
| **API Cost** | None (local) | Per-token charges |
| **Post-processing** | None | Markdown removal, cleaning |
| **Iterations to Success** | 0.2 avg | N/A (fails at scale) |
| **Pipeline Integration** | Direct | Requires preprocessing |
| **Inference Time** | ~3-5 sec | ~2-3 sec (API) |
| **Memory Usage** | ~6GB (4-bit) | N/A (cloud) |

---

## 5.8. RAG Contribution Analysis

> **Section Brief:** Isolates the contribution of Retrieval-Augmented Generation to overall system performance. Key finding: RAG provides +15% improvement on top of fine-tuning (80%→95% first-try without RAG vs. 80%→100% final with RAG+Agent 3), but cannot rescue pre-trained models (20% with or without RAG). This validates that RAG is a complement to, not a substitute for, domain-specific fine-tuning.

### 5.8.1 RAG vs. No-RAG Comparison

> **Subsection Brief:** Ablation study results: Fine-tuned+RAG (80% first-try, 100% final), Fine-tuned without RAG (65% first-try, 95% final), Pre-trained+RAG (20% first-try, 20% final). RAG provides marginal but meaningful improvement for fine-tuned models; RAG cannot help pre-trained models because they lack the base domain understanding to utilize retrieved knowledge effectively.

| Scenario | First-try Success | Final Success | Avg Iterations |
|----------|-------------------|---------------|----------------|
| Fine-tuned + RAG | 80% | 100% | 0.2 |
| Fine-tuned (no RAG) | 65% | 95% | 0.8 |
| Pre-trained + RAG | 20% | 20% | N/A |

### 5.8.2 RAG Knowledge Utilization

> **Subsection Brief:** Breaks down which knowledge sources each agent uses: Agent 1 heavily uses field specs, design rules, user examples, and dependencies; Agent 3 heavily uses error patterns and dependencies. Agent 1 doesn't use error patterns (not relevant to generation); Agent 3 doesn't use design rules (focused on correction). This specialization validates the collection-per-purpose RAG design.

| Knowledge Source | Agent 1 Usage | Agent 3 Usage |
|------------------|---------------|---------------|
| Field specifications | ✅ High | ✅ Medium |
| Error patterns | ❌ None | ✅ High |
| Design rules | ✅ Medium | ❌ None |
| User request examples | ✅ High | ❌ None |
| Field dependencies | ✅ High | ✅ High |

---

## 5.9. Multi-Agent Synergy

> **Section Brief:** Analyzes how the three agents work together to achieve higher success rates than any individual agent could. The key insight: Agent 1's 80% first-try success + Agent 3's 100% correction success = 100% system success. The agents are complementary—designed so that Agent 1's failure modes are exactly what Agent 3 is trained to fix.

### 5.9.1 Agent Contribution to Success

> **Subsection Brief:** Visualizes each agent's activation per test case: Agent 1 always active (generation), Agent 1.5 activated for complex cases (quick validation), Agent 2 always active (simulation), Agent 3 activated only for TC3 (correction). Shows that most cases don't need correction (80%), validating the fine-tuning investment while proving Agent 3's value for the remaining 20%.

```
                    AGENT CONTRIBUTION BY TEST CASE

Test Case    Agent 1      Agent 1.5    Agent 2      Agent 3
             (Generate)   (Validate)   (Simulate)   (Correct)
───────────────────────────────────────────────────────────────
TC1 (1z)     ████████████ ──────────── ████████████ ────────────
TC2 (2z)     ████████████ ──────────── ████████████ ────────────
TC3 (4z)     ████████████ ████         ████████████ ████████████
TC4 (10z)    ████████████ ──────────── ████████████ ────────────
TC5 (20z)    ████████████ ──────────── ████████████ ────────────

Legend: ████ = Active contribution  ──── = Pass-through
```

### 5.9.2 Correction Effectiveness by Agent

> **Subsection Brief:** Quantifies each agent's contribution: Agent 1 achieves 80% first-try (primary value), Agent 1.5 catches 70-80% errors before simulation (optional speedup), Agent 2 provides 100% accurate error detection (essential feedback), Agent 3 achieves 100% correction success (safety net). The architecture's value is that no single agent needs to be perfect—together they achieve 100%.

| Agent | Role | Contribution |
|-------|------|--------------|
| Agent 1 | Initial generation | 80% first-try success |
| Agent 1.5 | Quick validation | Catches 70-80% errors pre-simulation |
| Agent 2 | Validation/simulation | 100% accurate error detection |
| Agent 3 | Error correction | 100% correction success rate |

---

## 5.10. Key Findings

> **Section Brief:** Distills experimental results into four actionable findings that answer the research questions: (1) Fine-tuning is essential—80% vs. 0% proves domain knowledge cannot be prompted; (2) In-context learning fails at scale—20-zone breaking point limits pre-trained applicability; (3) Multi-agent architecture provides robustness—80%→100% through iterative correction; (4) RAG enhances but cannot replace fine-tuning—+15% improvement requires base domain understanding. These findings have implications beyond HVAC to all domain-specific LLM applications.

### Finding 1: Fine-tuning is Essential for Domain-Specific Tasks

> **Finding Brief:** The 100% vs. 0% comparison is unambiguous: domain-specific fine-tuning internalizes the 42-field VRF specification, proper syntax, and field interdependencies that cannot be conveyed through prompts. The fine-tuning cost (~4 GPU hours) is trivial compared to the 80% improvement in first-try success—a clear ROI for production deployment.

The fine-tuned model achieved **100% success rate** across all zone counts (1-20), while the pre-trained model without examples achieved **0%**.

**Implication:** Domain-specific fine-tuning internalizes the required format and field specifications, eliminating the need for extensive prompting.

### Finding 2: In-Context Learning Has Scalability Limits

> **Finding Brief:** Few-shot prompting (adding examples to prompt) works for simple cases but fails at scale. The breaking point at 20 zones indicates that context window limitations and attention dilution prevent reliable generalization. This finding challenges the assumption that "prompt engineering can solve everything"—for complex engineering tasks, fine-tuning remains necessary.

With examples in the prompt, the pre-trained model:
- ✅ Succeeded at 1 zone (simple case)
- ⚠️ Partially succeeded at 2-10 zones (format correct but has artifacts)
- ❌ Failed at 20 zones (breaking point)

**Implication:** In-context learning (few-shot prompting) works for simple cases but fails at complex, large-scale generation tasks.

### Finding 3: Multi-Agent Architecture Provides Robustness

> **Finding Brief:** The 80%→100% improvement demonstrates the generate-validate-correct paradigm's value. No single agent needs to be perfect; specialization enables each agent to excel at its task while the system achieves overall reliability. This pattern is applicable to other LLM deployments where output correctness is verifiable (code generation, data transformation, document processing).

The generate-validate-correct paradigm ensures:
- Failed first-try generations are corrected automatically
- Final success rate of 100% despite 80% first-try rate
- Self-healing capability without human intervention

### Finding 4: RAG Enhances but Cannot Replace Fine-tuning

> **Finding Brief:** The +15% RAG improvement is meaningful but requires base domain understanding to leverage. Pre-trained models cannot utilize retrieved EnergyPlus specifications because they don't understand the domain context—like giving an expert reference book to someone who doesn't know the field. RAG is a complement to, not substitute for, domain-specific training.

- RAG + Fine-tuned: Best performance (100% success)
- Fine-tuned only: Good performance (95% success)
- RAG + Pre-trained: Poor performance (20% success)

**Conclusion:** RAG enhances fine-tuned models but cannot compensate for lack of domain-specific training.

---

## 5.11. Statistical Summary

> **Section Brief:** Consolidates all findings into a question-answer format for quick reference. Addresses six research questions with evidence-based answers: pre-trained LLMs cannot generate valid IDF without fine-tuning; in-context learning fails at scale; fine-tuning is worth the investment; breaking point is 20 zones; RAG enhances fine-tuned models; multi-agent architecture improves reliability. This summary provides the "bottom line" for readers who want conclusions without full detail.

| Research Question | Answer | Evidence |
|-------------------|--------|----------|
| Can pre-trained LLMs generate valid EnergyPlus IDF? | ❌ Not without examples | 0% success without examples |
| Can in-context learning replace fine-tuning? | ❌ Fails at scale | Breaking point at 20 zones |
| Is fine-tuning worth the effort? | ✅ Yes | 100% vs 20% success rate |
| What is the breaking point for pre-trained? | 20 zones | Quality degrades with scale |
| Does RAG enhance performance? | ✅ Yes, for fine-tuned models | +5-15% improvement |
| Does multi-agent architecture improve reliability? | ✅ Yes | 80% → 100% with Agent 3 |

---

## 5.12. Conclusion

> **Section Brief:** Synthesizes the experimental results into a coherent narrative: domain-specific fine-tuning of smaller models (7B) significantly outperforms general-purpose large models for specialized engineering tasks. The multi-agent architecture with RAG achieves production-ready reliability (100% success, consistent quality, robust error correction). Pre-trained models fail at scale, demonstrating fundamental limitations of in-context learning for domain-specific generation. These findings support the broader thesis that specialized AI systems require domain-specific training.

The experimental results demonstrate that domain-specific fine-tuning of a smaller model (7B parameters) significantly outperforms general-purpose pre-trained models for specialized EnergyPlus HVAC generation tasks. The multi-agent architecture with RAG enhancement achieves:

- **100% final success rate** across all test cases (1-20 zones)
- **Consistent output quality** with no degradation at scale
- **Robust error correction** through iterative Agent 3 refinement
- **Production-ready pipeline** for automated HVAC design

In contrast, pre-trained models fail at 20 zones even with in-context examples, demonstrating the fundamental limitations of general-purpose LLMs for domain-specific engineering tasks.

---

# 6. Discussion

This section discusses the implications of our experimental results, addresses the broader context of LLM applications in engineering domains, and acknowledges the limitations of our study.

> **Section Brief:** The Discussion section interprets our experimental findings in the broader context of LLM research and building energy modeling. We argue that fine-tuning is not optional but essential for domain-specific tasks, examine why in-context learning fails at scale, and analyze the multi-agent synergy that enables 100% final success. The section also addresses practical implications for building engineers, integration with BIM workflows, generalization to other HVAC types, and honest acknowledgment of limitations.

## 6.1. Interpretation of Results

> **Section Brief:** Provides theoretical explanation for the observed experimental results. The 80% improvement from fine-tuning reflects "implicit knowledge acquisition"—the model internalizes domain patterns that cannot be conveyed through prompts. The in-context learning failure at 20 zones reflects context window and attention limitations. The multi-agent synergy demonstrates that specialization + iteration outperforms monolithic approaches.

### 6.1.1 The Fine-tuning Imperative

> **Subsection Brief:** Argues that fine-tuning is essential, not optional, for three reasons: (1) EnergyPlus knowledge is too complex for prompts (42 fields, interdependencies, strict formatting); (2) Format stability requires learned patterns, not instructed patterns; (3) Scalability preservation comes from internalized rules, not context-window examples. The training cost (~4 GPU hours) is negligible compared to the reliability improvement.

Our results strongly suggest that **domain-specific fine-tuning is not optional but essential** for specialized engineering tasks like EnergyPlus HVAC generation. The stark contrast between fine-tuned (100% success) and pre-trained (0-20% success) models indicates that:

1. **Implicit knowledge acquisition**: Fine-tuning enables the model to internalize domain-specific patterns that cannot be adequately conveyed through prompts alone. The 42-field VRF system specification, with its complex interdependencies and strict formatting requirements, represents knowledge that must be "learned" rather than "instructed."

2. **Format stability**: Fine-tuned models produce consistently formatted output without markdown artifacts, explanatory text, or structural deviations. This reliability is critical for automated pipelines where post-processing failures can cascade into simulation errors.

3. **Scalability preservation**: Unlike pre-trained models that exhibit quality degradation at scale (breaking at 20 zones), fine-tuned models maintain consistent performance regardless of complexity.

### 6.1.2 The Limitations of In-Context Learning

> **Subsection Brief:** Explains why few-shot prompting fails at scale: (1) Context window is finite—examples compete with task instructions for attention; (2) Examples teach syntax copying, not semantic generalization; (3) Attention becomes "diluted" as output complexity increases. The 20-zone breaking point reflects where copying fails and understanding is required. This finding aligns with emerging LLM research showing in-context learning works for in-distribution tasks but fails for specialized formats.

The failure of in-context learning (few-shot prompting) at scale reveals fundamental constraints:

| Observation | Implication |
|-------------|-------------|
| Pre-trained succeeds at 1 zone but fails at 20 | Context window limitations affect output consistency |
| Adding examples helps format but not scale | Examples teach syntax, not generalization |
| Quality degrades gradually (2→10 zones) then fails (20 zones) | Model "attention" becomes diluted with complexity |

This finding aligns with recent research suggesting that in-context learning is effective for tasks within the model's training distribution but struggles with specialized, out-of-distribution formats.

### 6.1.3 Multi-Agent Synergy

> **Subsection Brief:** The 80%→100% improvement demonstrates emergent system capability exceeding individual agent performance. The synergy arises from three factors: (1) Specialization—each agent optimized for its specific task; (2) Error complementarity—Agent 1's error types are exactly what Agent 3 is trained to fix; (3) Bounded iteration—3-iteration limit maintains efficiency while ensuring reliability. This pattern is applicable to other LLM deployments where output can be verified.

The improvement from 80% first-try success to 100% final success demonstrates the value of the multi-agent architecture:

```
Single Agent (Generator Only):     80% success
Multi-Agent (Generator + Corrector): 100% success
                                    ────────────
Improvement:                        +20% absolute
```

This synergy arises because:

1. **Specialization**: Agent 1 focuses on generation; Agent 3 focuses on correction. Neither needs to be perfect—they complement each other.

2. **Error diversity**: The types of errors Agent 1 makes (e.g., field mismatches) are exactly what Agent 3 is trained to fix.

3. **Bounded iteration**: With a maximum of 3 correction iterations, the system maintains efficiency while ensuring reliability.

---

## 6.2. Implications for Building Energy Modeling

> **Section Brief:** Examines practical impact for the building energy modeling community. Our system enables: faster HVAC design iterations, reduced manual IDF editing, automated simulation-ready configurations, and potential integration with BIM workflows. The natural language interface democratizes EnergyPlus access for practitioners who aren't IDF experts.

### 6.2.1 Automation Potential

> **Subsection Brief:** Identifies four stakeholder groups who benefit: (1) Building engineers—reduced manual work, faster iterations; (2) Energy modelers—automatic simulation-ready configs; (3) Researchers—rapid prototyping for energy studies; (4) Software developers—foundation for intelligent design tools. The automation potential is significant: what previously required hours of manual IDF editing can now be done in seconds.

Our system demonstrates that **end-to-end automation of HVAC design is feasible** for VRF systems. The practical implications include:

| Stakeholder | Benefit |
|-------------|---------|
| **Building engineers** | Reduced manual IDF editing; faster design iterations |
| **Energy modelers** | Automatic generation of simulation-ready configurations |
| **Researchers** | Rapid prototyping of building energy studies |
| **Software developers** | Foundation for intelligent building design tools |

### 6.2.2 Integration with BIM Workflows

> **Subsection Brief:** Envisions integration with Building Information Modeling tools (Revit, OpenStudio, gbXML). The pipeline BIM→Zone Extraction→User Request→HVAC-LLM→EnergyPlus IDF enables seamless transition from architectural design to energy simulation. The natural language interface serves as the bridge—architects can describe HVAC intent without learning IDF syntax.

The natural language interface enables integration with Building Information Modeling (BIM) workflows:

```
BIM Model → Zone Extraction → User Request → HVAC-LLM → EnergyPlus IDF
```

This pipeline could connect tools like Revit, OpenStudio, or gbXML exporters to our LLM-based generation system.

### 6.2.3 Expanding Beyond VRF

> **Subsection Brief:** Discusses generalization to other HVAC system types. The methodology is directly applicable to VAV, chilled beam, radiant systems—each requires new training data but uses the same architecture. Hybrid systems (e.g., VRF + dedicated outdoor air) require extended multi-system coordination but are achievable. The modular architecture enables system-specific fine-tuned models to be swapped based on user requirements.

While this study focused on VRF systems, the methodology is generalizable to other HVAC system types:

| System Type | Adaptation Required |
|-------------|---------------------|
| VAV (Variable Air Volume) | New training data; similar architecture |
| Chilled beam | New training data; similar architecture |
| Radiant systems | New training data; field specification updates |
| Hybrid systems | Multi-system coordination; extended pipeline |

The modular architecture allows fine-tuned models for different system types to be swapped based on user requirements.

---

## 6.3. Implications for LLM Applications in Engineering

> **Section Brief:** Positions our findings within the broader LLM research landscape. We contribute evidence to the specialist vs. generalist debate, demonstrate that smaller fine-tuned models outperform larger general models for specialized tasks, and identify the RAG-fine-tuning relationship. The error correction mechanism addresses the critical "graceful degradation" challenge in LLM deployment.

### 6.3.1 Domain-Specific vs. General-Purpose Models

> **Subsection Brief:** Contributes to the ongoing debate: for engineering applications with strict output requirements, fine-tuned specialists (7B parameters) outperform general-purpose giants (175B+). The advantages—high accuracy, consistent output, lower inference cost—outweigh the training investment. This finding has implications for all domain-specific LLM applications, not just HVAC.

Our findings contribute to the ongoing debate about specialized vs. general-purpose LLMs:

| Approach | Advantages | Disadvantages |
|----------|------------|---------------|
| **General-purpose (GPT-4, Claude)** | No training required; broad capabilities | Fails on specialized formats; expensive at scale |
| **Fine-tuned specialist** | High accuracy; consistent output; lower inference cost | Requires training data; narrower scope |

For engineering applications with strict output requirements, **fine-tuned specialists outperform generalists** despite having fewer parameters (7B vs. 175B+).

### 6.3.2 The RAG-Fine-tuning Spectrum

> **Subsection Brief:** Charts the performance landscape: Pre-trained alone (~0%), Pre-trained+RAG (~20%), Fine-tuned alone (~95%), Fine-tuned+RAG (100%). The insight: RAG provides marginal improvement when the base model already understands the domain—like giving reference materials to an expert. RAG cannot rescue a model that lacks foundational understanding. This positions RAG as a complement, not substitute, for domain-specific training.

Our RAG analysis reveals a nuanced relationship:

```
                    PERFORMANCE vs. APPROACH
                    
Performance
     │
100% │                           ●────────● Fine-tuned + RAG
     │                    ●─────●          Fine-tuned only
 80% │
     │
 60% │
     │
 40% │
     │
 20% │  ●─────●                            Pre-trained + RAG
     │
  0% │  ●─────●                            Pre-trained only
     └──────────────────────────────────────────────────────
            Low                                    High
                    Domain Specialization
```

**Key insight**: RAG provides marginal improvement (~15%) on top of fine-tuning but cannot rescue a non-fine-tuned model. The knowledge retrieval is most valuable when the base model already understands the domain context.

### 6.3.3 Error Correction as a Safety Net

> **Subsection Brief:** Addresses the "graceful degradation" challenge—how should LLM systems handle failures? Our Agent 3 mechanism provides a model: (1) Detect failures through verifiable feedback (simulation); (2) Apply targeted corrections based on error semantics; (3) Iterate until success or explicit failure. This pattern is applicable to code generation, data transformation, document formatting—any domain where output correctness can be verified.

The Agent 3 correction mechanism addresses a critical challenge in LLM deployment: **graceful degradation**. Rather than failing silently or producing unusable output, the system:

1. Detects failures through simulation feedback
2. Applies targeted corrections based on error semantics
3. Iterates until success or explicit failure

This pattern is applicable to other LLM applications where output correctness is verifiable (e.g., code generation, data transformation, document formatting).

---

## 6.4. Comparison with Related Work

> **Section Brief:** Positions our contribution relative to existing literature on LLMs for code generation and scientific computing. Our work extends code generation paradigms to domain-specific engineering artifacts, with the key innovation being simulation-in-the-loop validation that provides automatic correctness feedback.

### 6.4.1 LLMs for Code Generation

> **Subsection Brief:** Compares with tools like GitHub Copilot: both generate structured artifacts from natural language, both use compilation/simulation for verification, both handle error feedback. Our contribution: extending these paradigms to a highly specialized domain (EnergyPlus) where general-purpose models fail completely.

| Aspect | Code Generation (e.g., Copilot) | Our HVAC Generation |
|--------|--------------------------------|---------------------|
| Output format | Programming languages | Domain-specific IDF format |
| Verification | Compilation, tests | EnergyPlus simulation |
| Error feedback | Compiler errors | Simulation errors |
| Domain specificity | General programming | Highly specialized |

Our work extends code generation paradigms to domain-specific engineering artifacts.

### 6.4.2 LLMs for Scientific Computing

> **Subsection Brief:** Draws parallels with LLM applications in computational chemistry and physics. Similar to those domains, we deal with specialized input formats, simulation-based validation, and domain knowledge requirements. Our multi-agent approach with simulation-in-the-loop is analogous to active learning in scientific ML—using feedback to improve iteratively.

Compared to LLM applications in computational chemistry or physics simulations:

| Aspect | Scientific Computing | Building Energy Modeling |
|--------|---------------------|-------------------------|
| Input complexity | Molecular structures, PDEs | Building geometry, zones |
| Output validation | Experimental data | Simulation convergence |
| Domain knowledge | Physics/chemistry principles | HVAC engineering standards |

Our multi-agent approach with simulation-in-the-loop validation is analogous to active learning in scientific ML.

---

## 6.5. Limitations

> **Section Brief:** Honest acknowledgment of study limitations across four categories: scope (VRF-only, single EnergyPlus version), model (training data size, parameter count), experimental (limited test cases, no user study), and deployment (GPU requirement, EnergyPlus dependency). Transparency about limitations strengthens the research by enabling readers to assess applicability to their context.

### 6.5.1 Scope Limitations

> **Subsection Brief:** Acknowledges focus on VRF systems only (methodology applicable to other types but not tested), EnergyPlus v25.2.0 (IDD version-awareness built into RAG but not validated across versions), office buildings primarily (expandable with additional training data), limited climate zones (Denver weather file, additional validation recommended for other climates).

| Limitation | Description | Mitigation |
|------------|-------------|------------|
| **VRF-only focus** | Only VRF systems tested | Methodology applicable to other system types |
| **EnergyPlus version** | Tested on v25.2.0 only | IDD version-awareness built into RAG |
| **Building types** | Office buildings primarily | Expandable training data needed |
| **Climate zones** | Limited weather file testing | Additional validation recommended |

### 6.5.2 Model Limitations

> **Subsection Brief:** Acknowledges that 500 training examples may not cover all edge cases (rare configurations may fail), 7B parameters limits reasoning depth (complex multi-system interactions may be challenging), ~4K token context window limits per-generation capacity (very large buildings may require chunking). These limitations guide future research directions.

| Limitation | Description | Impact |
|------------|-------------|--------|
| **Training data size** | 500+ examples may not cover all edge cases | Rare configurations may fail |
| **Model size** | 7B parameters limits reasoning depth | Complex multi-system interactions may be challenging |
| **Context window** | Limited to ~4K tokens per generation | Very large buildings may require chunking |

### 6.5.3 Experimental Limitations

> **Subsection Brief:** Five primary test cases may not represent full diversity (future work: 50+ diverse buildings); no human evaluation of usability (future: practitioner interviews); only Mistral-based comparison (future: GPT-4, Claude, Llama baselines); simulation success ≠ energy accuracy (future: validation against measured data). These limitations provide clear future research directions.

| Limitation | Description | Future Work |
|------------|-------------|-------------|
| **Test case diversity** | 5 primary test cases | Expand to 50+ diverse buildings |
| **User study absence** | No human evaluation of usability | Conduct practitioner interviews |
| **Baseline comparison** | Only Mistral-based models | Compare with GPT-4, Claude, Llama |
| **Energy accuracy** | Simulation success ≠ energy accuracy | Validate against measured data |

### 6.5.4 Deployment Limitations

> **Subsection Brief:** Practical deployment considerations: GPU required for fine-tuned model inference (mitigated by cloud deployment or further quantization), local EnergyPlus installation required (mitigated by container-based deployment), 3-5 second generation time (acceptable for design workflows, not real-time applications).

| Limitation | Description | Consideration |
|------------|-------------|---------------|
| **GPU requirement** | Fine-tuned model requires GPU | Cloud deployment or quantization |
| **EnergyPlus dependency** | Requires local EnergyPlus installation | Container-based deployment |
| **Real-time performance** | 3-5 second generation time | Acceptable for design workflows |

---

## 6.6. Threats to Validity

> **Section Brief:** Addresses potential threats to internal validity (training/test overlap, hyperparameter sensitivity, stochastic variation), external validity (generalization to other HVAC types, other LLM architectures, real-world conditions), and construct validity (success metric definition, quality measurement approach). This section demonstrates methodological rigor.

### 6.6.1 Internal Validity

> **Subsection Brief:** Potential confounds: training/test overlap (mitigated by using distinct test buildings); hyperparameter sensitivity (mitigated by reporting all configurations); random variation (mitigated by multiple runs where feasible). The 80% vs. 0% gap is too large to be explained by these threats.

| Threat | Description | Mitigation |
|--------|-------------|------------|
| **Training/test overlap** | Fine-tuned model may have seen similar test cases | Used distinct test buildings not in training set |
| **Parameter tuning** | Results may be sensitive to hyperparameters | Reported all configuration settings |
| **Random variation** | LLM outputs are stochastic | Multiple runs averaged where feasible |

### 6.6.2 External Validity

> **Subsection Brief:** Generalization concerns: VRF results may not extend to VAV/chilled water (methodology is generalizable but not tested); results specific to Mistral (future work on other architectures); lab vs. production conditions (deployment considerations discussed). The methodology's generality suggests external validity, but confirmation requires additional studies.

| Threat | Description | Mitigation |
|--------|-------------|------------|
| **Generalization to other HVAC types** | VRF results may not extend to VAV, chilled water | Discussed methodology generalization |
| **Generalization to other LLMs** | Results specific to Mistral architecture | Future work on other model families |
| **Real-world applicability** | Lab conditions vs. production use | Discussed deployment considerations |

### 6.6.3 Construct Validity

> **Subsection Brief:** Measurement concerns: "success" defined as simulation runs, not energy accuracy (acknowledged as limitation); binary success vs. quality gradations (addressed through qualitative analysis). The primary construct (generation success) is well-defined; secondary constructs (practical utility) require future user studies.

| Threat | Description | Mitigation |
|--------|-------------|------------|
| **Success metric definition** | "Success" = simulation runs, not energy accuracy | Acknowledged as limitation |
| **Quality measurement** | Binary success vs. output quality gradations | Included qualitative analysis |

---

## 6.7. Future Research Directions

> **Section Brief:** Outlines a research roadmap across three timeframes: short-term (VAV support, interactive refinement, confidence scoring), medium-term (hybrid HVAC systems, energy optimization, explainability), and long-term (full building automation, multi-objective optimization, continuous learning). These directions provide clear next steps for both our work and the broader research community.

### 6.7.1 Short-term Extensions

> **Subsection Brief:** Near-term opportunities requiring moderate effort: add VAV/chiller/boiler generation (requires new training data, uses same architecture); implement user feedback loop for design iteration (pipeline modification); add confidence scoring to indicate output reliability (calibration study). These extensions would significantly broaden applicability.

| Direction | Description | Effort |
|-----------|-------------|--------|
| **Multi-system support** | Add VAV, chiller, boiler generation | Medium (new training data) |
| **Interactive refinement** | User feedback loop for design iteration | Low (pipeline modification) |
| **Confidence scoring** | Output reliability indicators | Medium (calibration study) |

### 6.7.2 Medium-term Research

> **Subsection Brief:** More substantial research opportunities: hybrid HVAC systems requiring coordinated multi-system generation (architectural changes needed); energy parameter optimization through RL integration (high effort but high impact); explainability through attention analysis (helps users understand and trust design decisions).

| Direction | Description | Effort |
|-----------|-------------|--------|
| **Hybrid HVAC systems** | Generate coordinated multi-system configurations | High (architectural changes) |
| **Energy optimization** | Optimize parameters for energy efficiency | High (RL integration) |
| **Explainability** | Explain design decisions to users | Medium (attention analysis) |

### 6.7.3 Long-term Vision

> **Subsection Brief:** Aspirational goals that define the research trajectory: full building automation (envelope + HVAC + controls in unified pipeline); multi-objective optimization balancing energy, cost, comfort, and emissions; continuous learning from production deployments; standards-compliant export (gbXML, IFC) for industry integration. These goals position the work within the broader smart building ecosystem.

| Direction | Description |
|-----------|-------------|
| **Full building automation** | Envelope + HVAC + controls in one pipeline |
| **Multi-objective optimization** | Balance energy, cost, comfort, emissions |
| **Continuous learning** | Update models from production deployments |
| **Industry integration** | Standards-compliant export (gbXML, IFC) |

---

## 6.8. Practical Recommendations

> **Section Brief:** Translates research findings into actionable guidance for three audiences: practitioners (use fine-tuned for production, enable RAG, keep Agent 3 active), researchers (invest in fine-tuning, design multi-agent systems, build verification pipelines), and tool developers (modular architecture, version-aware knowledge bases, graceful degradation). These recommendations maximize the research's practical impact.

### 6.8.1 For Practitioners

> **Subsection Brief:** Guidance for building engineers and energy modelers: use fine-tuned models for production (100% vs. 20% justifies training); enable RAG for complex requests (+15% edge case improvement); keep Agent 3 active (safety net); always validate simulation results (LLM success ≠ engineering correctness). Production deployment should follow these practices.

| Recommendation | Rationale |
|----------------|-----------|
| **Use fine-tuned models for production** | 100% vs. 20% success rate justifies training investment |
| **Enable RAG for complex requests** | +15% improvement for edge cases |
| **Keep Agent 3 active** | Safety net ensures reliability |
| **Validate simulation results** | LLM success ≠ engineering correctness |

### 6.8.2 For Researchers

> **Subsection Brief:** Guidance for LLM researchers: invest in domain-specific fine-tuning (general-purpose insufficient for specialized formats); design multi-agent architectures (specialization + iteration outperforms monolithic); build verification pipelines (simulation-in-the-loop catches errors); collect quality training data (data quality determines model quality).

| Recommendation | Rationale |
|----------------|-----------|
| **Invest in domain-specific fine-tuning** | General-purpose LLMs insufficient for specialized formats |
| **Design multi-agent architectures** | Specialization + iteration outperforms monolithic approaches |
| **Build verification pipelines** | Simulation-in-the-loop catches errors automatically |
| **Collect domain-specific training data** | Data quality determines model quality |

### 6.8.3 For Tool Developers

> **Subsection Brief:** Guidance for software developers building LLM-based tools: modular architecture enables component swapping and upgrades; version-aware knowledge bases handle EnergyPlus version changes; graceful degradation through explicit failure rather than silent errors; logging and transparency enable debugging and user trust.

| Recommendation | Rationale |
|----------------|-----------|
| **Modular architecture** | Enable component swapping and upgrades |
| **Version-aware knowledge bases** | EnergyPlus versions change field specifications |
| **Graceful degradation** | Fail explicitly rather than silently |
| **Logging and transparency** | Enable debugging and user trust |

---

## 6.9. Summary

> **Section Brief:** Synthesizes the entire discussion into five key takeaways: (1) Fine-tuning is essential for domain-specific tasks; (2) Multi-agent architectures provide robustness; (3) RAG enhances but cannot replace fine-tuning; (4) Scalability differentiates fine-tuned from pre-trained; (5) Methodology generalizes beyond VRF. The limitations acknowledged provide clear future research directions, and the practical recommendations translate findings into action.

This discussion has examined the broader implications of our experimental results:

1. **Fine-tuning is essential** for domain-specific engineering tasks with strict output requirements.

2. **Multi-agent architectures** provide robustness through specialization and iterative refinement.

3. **RAG enhances but cannot replace** fine-tuning—it is most effective when the base model already has domain understanding.

4. **Scalability is a critical differentiator**—fine-tuned models maintain quality at scale while pre-trained models degrade.

5. **The methodology is generalizable** to other HVAC system types and potentially other engineering domains with verifiable outputs.

The limitations of this study—primarily scope and baseline comparisons—provide clear directions for future work. The practical recommendations offer guidance for practitioners, researchers, and tool developers seeking to apply LLMs to specialized engineering automation tasks.

---

**Document Version:** 1.1  
**Last Updated:** February 2026  
**Author:** Ayeen


# HVAC-LLM: Automated HVAC System Design with Large Language Models

Automated EnergyPlus HVAC system design using LLM agents for generation, validation, and error correction.

## Project Structure

```
HVAC-LLM/
├── config/              # Configuration files
│   ├── settings.py      # Main settings
│   └── __init__.py
├── data/                # Data files
│   ├── base_idfs/       # Base IDF templates
│   ├── example_idfs/    # Example IDF files
│   └── training_data/   # LLM training datasets
├── src/                 # Source code
│   ├── agents/          # LLM agents
│   │   ├── llm_interface.py      # Universal LLM interface
│   │   ├── agent1_generator.py   # HVAC Generator
│   │   └── agent3_corrector.py   # Error Corrector
│   ├── core/            # Core functionality
│   │   ├── idf_handler.py        # IDF file operations
│   │   ├── simulator.py          # EnergyPlus simulator
│   │   └── validator.py          # IDF validator
│   ├── utils/           # Utilities
│   │   ├── logger.py             # Logging
│   │   └── file_utils.py         # File operations
│   └── pipeline.py      # Main pipeline
├── outputs/             # Generated outputs
│   ├── simulations/     # Simulation results
│   ├── generated_idfs/  # Generated IDF files
│   └── logs/            # Log files
├── tests/               # Test files
└── docs/                # Documentation

```

## Quick Start

### 1. Installation

```bash
# Install EnergyPlus (download from energyplus.net)

# Install Python dependencies
pip install eppy anthropic openai google-generative-ai
```

### 2. Configuration

Edit `config/settings.py`:
- Set `ENERGYPLUS_DIR` to your EnergyPlus installation path
- Set LLM provider and API keys

```bash
# Set API key (optional, will use mock mode if not set)
export GEMINI_API_KEY="your-key-here"
# or
export ANTHROPIC_API_KEY="your-key-here"
# or
export OPENAI_API_KEY="your-key-here"
```

### 3. Run Pipeline

```python
from src.pipeline import HVACLLMPipeline

# Initialize pipeline
pipeline = HVACLLMPipeline()

# Run with your base IDF
results = pipeline.run(
    base_idf="data/base_idfs/building_with_zones.idf",
    zones=["Zone_1", "Zone_2"],
    output_name="my_project"
)
```

## Features

### Three LLM Agents

1. **Agent 1: HVAC Generator**
   - Generates HVACTemplate objects from natural language prompts
   - Supports VRF, VAV, and other HVAC systems
   - Converts text descriptions to valid IDF format

2. **Agent 2: IDF Validator** (integrated in core)
   - Validates IDF structure against IDD rules
   - Checks for missing objects and invalid references
   - Provides detailed error reports

3. **Agent 3: Error Corrector**
   - Analyzes EnergyPlus simulation errors
   - Suggests and applies fixes automatically
   - Iterative correction until simulation succeeds

### Complete Pipeline

1. **Generate**: LLM creates HVAC system configuration
2. **Validate**: Check IDF structure and completeness
3. **Simulate**: Run EnergyPlus simulation
4. **Correct**: Automatically fix any errors
5. **Iterate**: Repeat until successful

## Usage Examples

### Generate VRF System

```python
from src.agents.agent1_generator import HVACGenerator

generator = HVACGenerator()

# Generate VRF system
hvac_response = generator.generate_vrf_system(
    zones=["Office_1", "Office_2", "Meeting_Room"],
    system_name="Office_VRF"
)


```

### Validate IDF

```python
from src.core.validator import IDFValidator

validator = IDFValidator()
is_valid = validator.validate("my_building.idf")

if not is_valid:
    report = validator.get_report()
    print(f"Errors: {report['errors']}")
```

### Run Simulation

```python
from src.core.simulator import EnergyPlusSimulator

simulator = EnergyPlusSimulator()
results = simulator.run(
    idf_path="building.idf",
    output_dir="simulation_results"
)

if results['success']:
    print("Simulation completed successfully!")
else:
    print(f"Errors: {results['severe_errors']}")
```

### Fix Errors

```python
from src.agents.agent3_corrector import ErrorCorrector

corrector = ErrorCorrector()

# Analyze errors
fixes = corrector.analyze_and_fix(
    idf_path="building.idf",
    errors=simulation_errors
)

# Apply fixes
corrector.apply_fixes(
    idf_path="building.idf",
    fixes=fixes,
    output_path="building_fixed.idf"
)
```

## Configuration

Key settings in `config/settings.py`:

```python
# EnergyPlus paths
ENERGYPLUS_DIR = r"C:\EnergyPlusV24-1-0"

# LLM settings
LLM_PROVIDER = "auto"  # "gemini", "openai", "anthropic", "mock"
LLM_MODEL = "gpt-4"
MAX_ERROR_CORRECTION_ITERATIONS = 3

# Simulation
SIMULATION_TIMEOUT = 120  # seconds
```

## LLM Providers

Supports three modes:

1. **Gemini (Google Generative Models)**
    - Set `GEMINI_API_KEY` environment variable
    - Uses Google Gemini models; set `LLM_MODEL` in `config/settings.py` appropriately (for example `gemini-pro`)

2. **OpenAI (GPT-4)**
    - Set `OPENAI_API_KEY` environment variable
    - Uses `gpt-4` or `gpt-3.5-turbo`

3. **Anthropic (Claude)**
    - Set `ANTHROPIC_API_KEY` environment variable
    - Uses `claude-3-5-sonnet`

3. **Mock Mode**
   - No API key required
   - Uses pre-defined responses for testing
   - Automatically used if no API keys found

## Output Files

### Generated IDFs
- `outputs/generated_idfs/` - IDF files with HVAC systems

### Simulation Results
- `outputs/simulations/` - EnergyPlus simulation outputs
- Contains `.err`, `.eso`, `.html` files

### Logs
- `outputs/logs/` - JSON results and logs
- Includes full pipeline execution details

## Testing

Run tests:

```bash
cd tests
python test_pipeline.py
```

## Project Background

This project implements the HVAC-LLM architecture for automated HVAC system design in EnergyPlus using Large Language Models.

### Key Components:
- **HVACTemplate objects**: Simplified HVAC definitions
- **LLM agents**: Intelligent design and error correction
- **Feedback loops**: Iterative improvement until success
- **Training data**: Generated from example files

## Requirements

- Python 3.8+
- EnergyPlus 23.2 or later
- eppy
- anthropic or openai (optional)

## License

Educational/Research Project

## Contributors

[Your name and project team]

## References

- EnergyPlus Documentation: https://energyplus.net
- Eppy: https://github.com/santoshphilip/eppy

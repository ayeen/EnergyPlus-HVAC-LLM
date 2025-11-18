# HVAC-LLM User Guide
## Complete Guide from Installation to Advanced Usage

**Version:** 1.0  
**Date:** October 29, 2025  
**Author:** HVAC-LLM Development Team

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [System Requirements](#2-system-requirements)
3. [Project Structure](#3-project-structure)
4. [Installation & Setup](#4-installation--setup)
5. [Configuration](#5-configuration)
6. [Quick Start Guide](#6-quick-start-guide)
7. [Step-by-Step Usage](#7-step-by-step-usage)
8. [Advanced Features](#8-advanced-features)
9. [Troubleshooting](#9-troubleshooting)
10. [Best Practices](#10-best-practices)
11. [API Reference](#11-api-reference)
12. [Examples & Use Cases](#12-examples--use-cases)

---

## 1. Introduction

### 1.1 What is HVAC-LLM?

HVAC-LLM is an AI-powered system that automatically generates, validates, and corrects EnergyPlus HVAC (Heating, Ventilation, and Air Conditioning) configurations using Large Language Models (LLMs).

**Key Features:**
- ✅ Natural language to EnergyPlus IDF conversion
- ✅ Automatic error detection and correction
- ✅ Pre-simulation validation
- ✅ Multi-zone VRF system support
- ✅ 42-field complete VRF coverage
- ✅ Interactive and batch processing modes

### 1.2 How It Works

```
User Request (Natural Language)
    ↓
[Agent 1] Generate HVAC Configuration
    ↓
[Agent 1.5] Quick Validation (Optional)
    ↓
[Agent 2] Structural Validation
    ↓
[EnergyPlus] Simulate Building
    ↓
[Agent 3] Error Correction (if needed)
    ↓
Final Corrected IDF File
```

### 1.3 Use Cases

- **Building Design:** Generate HVAC systems from design requirements
- **Energy Modeling:** Quick prototyping of HVAC configurations
- **Research:** Test multiple HVAC scenarios rapidly
- **Education:** Learn EnergyPlus IDF syntax through examples
- **Automation:** Batch process multiple building configurations

---

## 2. System Requirements

### 2.1 Software Requirements

**Required:**
- Python 3.8 or higher
- EnergyPlus 25.1.0 (or compatible version)
- Windows, macOS, or Linux operating system

**Python Packages:**
```
eppy>=0.5.63
google-generativeai>=0.3.0
python-dotenv>=1.0.0
```

### 2.2 Hardware Requirements

**Minimum:**
- CPU: 2 cores, 2.0 GHz
- RAM: 4 GB
- Storage: 2 GB free space

**Recommended:**
- CPU: 4+ cores, 3.0 GHz
- RAM: 8+ GB
- Storage: 5+ GB free space
- SSD for faster simulation

### 2.3 API Requirements

**LLM Provider (choose one):**
- Google Gemini API (Recommended)
- OpenAI API
- Anthropic Claude API

**API Key Required:** Yes (see Configuration section)

---

## 3. Project Structure

### 3.1 Directory Tree

```
HVAC-LLM/
│
├── README.md                          # Project overview
├── requirements.txt                   # Python dependencies
├── .env                              # API keys (create this)
│
├── config/                           # Configuration files
│   ├── __init__.py
│   ├── settings.py                   # Main configuration
│   └── hvac_requests.json            # Pre-defined HVAC requests
│
├── data/                             # Base IDF files
│   ├── base_idfs/
│   │   ├── building_with_zones.idf              # Single-zone base
│   │   └── 4ZoneWithShading_Simple_2_NoHVAC.idf # Multi-zone base
│   ├── example_idfs/                 # Example IDF files
│   └── training_data/                # Training/testing data
│
├── src/                              # Source code
│   ├── pipeline.py                   # Main pipeline orchestrator
│   │
│   ├── agents/                       # AI agents
│   │   ├── __init__.py
│   │   ├── agent1_generator.py       # HVAC generation
│   │   ├── agent1_5_validator.py     # Quick validation
│   │   ├── agent3_corrector.py       # Error correction
│   │   ├── llm_interface.py          # LLM communication
│   │   └── energyplus_vrf_prompt.json # VRF template (42 fields)
│   │
│   ├── core/                         # Core utilities
│   │   ├── __init__.py
│   │   ├── idf_handler.py            # IDF file operations
│   │   ├── simulator.py              # EnergyPlus simulation
│   │   └── validator.py              # IDF validation
│   │
│   └── utils/                        # Utility functions
│       ├── __init__.py
│       ├── file_utils.py
│       ├── logger.py
│       └── clean_base_idf.py         # Remove HVAC from base IDF
│
├── examples/                         # Example scripts
│   ├── example1_generate_vrf.py      # Simple VRF generation
│   ├── example2_complete_pipeline.py # Complete pipeline with validation
│   └── example3_config_based.py      # Config file-based execution
│
├── outputs/                          # Generated outputs
│   ├── generated_idfs/               # Generated IDF files
│   ├── logs/                         # Execution logs (JSON)
│   └── simulations/                  # EnergyPlus simulation outputs
│
├── tests/                            # Test scripts
│   ├── test_pipeline.py
│   └── test_quick_validation_pipeline.py
│
└── docs/                             # Documentation
    ├── INSTALLATION.md
    ├── QUICK_VALIDATION_IMPLEMENTATION.md
    ├── VRF_42_FIELDS_EXPLAINED.md
    ├── WHICH_FILE_TO_USE.md
    └── USER_GUIDE.md                 # This file
```

### 3.2 Key Files Explained

| File | Purpose |
|------|---------|
| **`config/settings.py`** | System configuration (paths, LLM settings, limits) |
| **`config/hvac_requests.json`** | Pre-defined HVAC design requests |
| **`src/pipeline.py`** | Main pipeline orchestrator |
| **`src/agents/agent1_generator.py`** | Generates HVAC from natural language |
| **`src/agents/agent1_5_validator.py`** | Pre-simulation validation |
| **`src/agents/agent3_corrector.py`** | Fixes EnergyPlus errors |
| **`src/agents/energyplus_vrf_prompt.json`** | 42-field VRF template |
| **`examples/example3_config_based.py`** | Interactive menu-driven interface |
| **`outputs/generated_idfs/*_FINAL.idf`** | Final corrected IDF (use this!) |

---

## 4. Installation & Setup

### 4.1 Step 1: Install Python

**Windows:**
1. Download Python from https://www.python.org/downloads/
2. Run installer
3. ✅ Check "Add Python to PATH"
4. Click "Install Now"
5. Verify: `python --version`

**macOS:**
```bash
brew install python@3.11
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install python3.11 python3-pip
```

### 4.2 Step 2: Install EnergyPlus

**Windows:**
1. Download EnergyPlus 25.1.0 from https://energyplus.net/
2. Run installer (default location: `C:\EnergyPlusV25-1-0\`)
3. Note installation path for configuration

**macOS:**
```bash
# Download .dmg from energyplus.net
# Drag to Applications
```

**Linux:**
```bash
# Download .tar.gz from energyplus.net
sudo tar -xzf EnergyPlus-*.tar.gz -C /usr/local/
```

### 4.3 Step 3: Clone/Download Project

**Option A: Git Clone**
```bash
git clone https://github.com/your-repo/HVAC-LLM.git
cd HVAC-LLM
```

**Option B: Download ZIP**
1. Download ZIP from repository
2. Extract to desired location
3. Open terminal in project folder

### 4.4 Step 4: Install Python Dependencies

```bash
# Navigate to project root
cd HVAC-LLM

# Install dependencies
pip install -r requirements.txt
```

**Expected output:**
```
Successfully installed eppy-0.5.63 google-generativeai-0.3.2 python-dotenv-1.0.0 ...
```

### 4.5 Step 5: Verify Installation

```bash
python -c "import eppy; print('eppy:', eppy.__version__)"
python -c "import google.generativeai; print('Gemini: OK')"
python -c "import dotenv; print('dotenv: OK')"
```

**Expected:**
```
eppy: 0.5.63
Gemini: OK
dotenv: OK
```

---

## 5. Configuration

### 5.1 Step 1: Create `.env` File

Create a file named `.env` in the project root:

```bash
# Location: HVAC-LLM/.env

# === LLM API Keys ===
# Get your key from: https://aistudio.google.com/app/apikey
GEMINI_API_KEY=your_gemini_api_key_here

# Alternative providers (optional)
# OPENAI_API_KEY=your_openai_key_here
# ANTHROPIC_API_KEY=your_anthropic_key_here

# === EnergyPlus Configuration ===
# Windows default:
ENERGYPLUS_EXE=C:/EnergyPlusV25-1-0/energyplus.exe
ENERGYPLUS_IDD=C:/EnergyPlusV25-1-0/Energy+.idd

# macOS default:
# ENERGYPLUS_EXE=/Applications/EnergyPlus-25-1-0/energyplus
# ENERGYPLUS_IDD=/Applications/EnergyPlus-25-1-0/Energy+.idd

# Linux default:
# ENERGYPLUS_EXE=/usr/local/EnergyPlus-25-1-0/energyplus
# ENERGYPLUS_IDD=/usr/local/EnergyPlus-25-1-0/Energy+.idd
```

**Important Notes:**
- ⚠️ **Never commit `.env` to version control**
- ⚠️ **Keep API keys private**
- ⚠️ **Use forward slashes (/) even on Windows**

### 5.2 Step 2: Get API Key

**Google Gemini (Recommended):**
1. Visit https://aistudio.google.com/app/apikey
2. Click "Create API Key"
3. Copy the key
4. Paste in `.env` file

**Free Tier:**
- 60 requests per minute
- Sufficient for most use cases

### 5.3 Step 3: Configure EnergyPlus Paths

**Windows:**
```bash
# Find your EnergyPlus installation
dir "C:\EnergyPlus*"

# Update .env with correct path
ENERGYPLUS_EXE=C:/EnergyPlusV25-1-0/energyplus.exe
```

**macOS:**
```bash
# Find EnergyPlus
ls /Applications/EnergyPlus*

# Update .env
ENERGYPLUS_EXE=/Applications/EnergyPlus-25-1-0/energyplus
```

**Linux:**
```bash
# Find EnergyPlus
ls /usr/local/EnergyPlus*

# Update .env
ENERGYPLUS_EXE=/usr/local/EnergyPlus-25-1-0/energyplus
```

### 5.4 Step 4: Verify Configuration

```bash
python -c "from config import Config; print('LLM Provider:', Config.LLM_PROVIDER)"
python -c "from config import Config; print('EnergyPlus:', Config.ENERGYPLUS_EXE)"
```

**Expected output:**
```
LLM Provider: gemini
EnergyPlus: C:/EnergyPlusV25-1-0/energyplus.exe
```

### 5.5 Advanced Configuration (Optional)

Edit `config/settings.py` to customize:

```python
# LLM Settings
LLM_PROVIDER = "gemini"              # or "openai", "anthropic"
LLM_MODEL = "gemini-1.5-pro"         # Model name
LLM_TEMPERATURE = 0.3                # Creativity (0.0-1.0)
LLM_MAX_TOKENS = 8192                # Response length

# Pipeline Settings
MAX_ERROR_CORRECTION_ITERATIONS = 5  # Max correction attempts
ENABLE_QUICK_VALIDATION = True       # Pre-simulation validation

# Output Settings
OUTPUT_DIR = "outputs"               # Output directory
LOG_LEVEL = "INFO"                   # DEBUG, INFO, WARNING, ERROR
```

---

## 6. Quick Start Guide

### 6.1 First Run (5 Minutes)

**Step 1:** Verify setup
```bash
cd HVAC-LLM
python -c "from config import Config; print('✓ Configuration OK')"
```

**Step 2:** Run Example 2
```bash
cd examples
python example2_complete_pipeline.py
```

**Expected output:**
```
======================================================================
EXAMPLE 2: Complete HVAC-LLM Pipeline
======================================================================

[1] Generating HVAC...
✓ Generated 2 HVAC objects

[1.5] Quick validation (pre-simulation)...
✅ Pre-validation PASSED

[2] Validating IDF...
Valid: True, Errors: 0

[3] Simulating...
Success: True, Errors: 0

✅ SIMULATION SUCCESS!
✓ Final corrected IDF copied to: ../outputs/generated_idfs/example2_complete_FINAL.idf

🎉 SUCCESS! Use this file:
   D:\Ayeen\Project\HVAC-LLM\outputs\generated_idfs\example2_complete_FINAL.idf
```

**Step 3:** Find your output
```
Location: outputs/generated_idfs/example2_complete_FINAL.idf
```

**Step 4:** Open in EP-Launch (optional)
1. Open EnergyPlus EP-Launch application
2. File → Open → Select `example2_complete_FINAL.idf`
3. Click "Simulate"

🎉 **Congratulations!** You've completed your first HVAC generation!

---

## 7. Step-by-Step Usage

### 7.1 Using Example 3 (Interactive Mode)

**Best for:** Beginners, testing different configurations

**Step 1:** Run interactive menu
```bash
cd examples
python example3_config_based.py
```

**Step 2:** Choose a request
```
Available HVAC Design Requests:
----------------------------------------------------------------------
  vrf_single_zone:
    Prompt: Design a VRF HVAC system for efficient heating and cooling
    Zones: ZONE ONE
  
  vrf_heat_recovery:
    Prompt: Design VRF with heat recovery
    Zones: ZONE ONE
  
  vrf_multi_zone_office:
    Prompt: Design VRF for multiple office zones
    Zones: ZONE 1, ZONE 2, ZONE 3, ZONE 4
----------------------------------------------------------------------

Your choice: 
```

**Step 3:** Enter request ID
```
Your choice: vrf_single_zone
```

**Step 4:** Wait for completion
```
[1] Generating HVAC...
[1.5] Quick validation (pre-simulation)...
[2] Validating IDF...
[3] Simulating...

✅ SUCCESS! Use this file:
   outputs/generated_idfs/vrf_single_zone_FINAL.idf
```

**Step 5:** Use the generated file
- File location: `outputs/generated_idfs/vrf_single_zone_FINAL.idf`
- Open in EP-Launch or use in your workflow

### 7.2 Creating Custom Requests

**Step 1:** Edit configuration file
```bash
# Open in text editor
notepad config/hvac_requests.json

# Or VS Code
code config/hvac_requests.json
```

**Step 2:** Add your request
```json
{
  "my_custom_vrf": {
    "prompt": "Design a high-efficiency VRF system with heat recovery for a cold climate building with supplemental electric heating below -15°C",
    "zones": ["ZONE ONE"],
    "base_idf": "../data/base_idfs/building_with_zones.idf"
  }
}
```

**Step 3:** Run with your request
```bash
python example3_config_based.py
# Enter: my_custom_vrf
```

### 7.3 Using Python API (Programmatic)

**Best for:** Integration, automation, batch processing

```python
from src.pipeline import HVACLLMPipeline

# Initialize pipeline
pipeline = HVACLLMPipeline()

# Define parameters
base_idf = "data/base_idfs/building_with_zones.idf"
zones = ["ZONE ONE"]
user_request = "Design a VRF system with heat recovery"

# Run pipeline
results = pipeline.run(
    base_idf=base_idf,
    zones=zones,
    output_name="my_vrf_system",
    system_name="VRF_System_1",
    user_request=user_request,
    enable_quick_validation=True
)

# Check results
if results['final_status'] == 'SUCCESS':
    print(f"✓ Success! Final IDF: {results['final_idf']}")
else:
    print(f"✗ Failed: {results.get('error')}")
```

### 7.4 Batch Processing Multiple Buildings

```python
from src.pipeline import HVACLLMPipeline
import json

# Load requests
with open('config/hvac_requests.json', 'r') as f:
    requests = json.load(f)

pipeline = HVACLLMPipeline()

# Process all requests
for req_id, config in requests.items():
    print(f"\nProcessing: {req_id}")
    
    results = pipeline.run(
        base_idf=config['base_idf'],
        zones=config['zones'],
        output_name=req_id,
        user_request=config['prompt'],
        enable_quick_validation=True
    )
    
    status = "✓" if results['final_status'] == 'SUCCESS' else "✗"
    print(f"{status} {req_id}: {results['final_status']}")
```

---

## 8. Advanced Features

### 8.1 Quick Validation (Pre-Simulation)

**What:** LLM-based validation before EnergyPlus simulation  
**Catches:** 70-80% of common errors in ~5 seconds  
**Saves:** ~30 seconds per error case

**Enable/Disable:**
```python
# Enabled (default)
results = pipeline.run(
    base_idf="...",
    zones=["ZONE ONE"],
    enable_quick_validation=True
)

# Disabled (for batch processing)
results = pipeline.run(
    base_idf="...",
    zones=["ZONE ONE"],
    enable_quick_validation=False
)
```

**Validation Checks:**
1. ✅ Zone count match (fast)
2. ✅ Master thermostat location (fast)
3. ✅ Field value ranges (LLM, 5s)
4. ✅ Object completeness (fast)

**Auto-Fix:** If errors detected, automatically attempts correction before simulation

### 8.2 42-Field VRF System

The system supports **complete VRF configuration** with 42 fields:

**Fields 1-32:** Standard VRF (cooling, heating, airflow)  
**Fields 33-36:** Supplemental heating (cold climates)  
**Fields 37-38:** Parasitic loads (LEED, detailed energy)  
**Field 40:** Multispeed fan control  
**Fields 41-42:** Baseboard heating (perimeter zones)

**Example requests:**

```json
{
  "vrf_cold_climate": {
    "prompt": "Design VRF with electric supplemental heating below -15°C",
    "zones": ["ZONE ONE"],
    "base_idf": "../data/base_idfs/building_with_zones.idf"
  },
  
  "vrf_leed": {
    "prompt": "Design VRF with detailed parasitic load tracking for LEED",
    "zones": ["ZONE ONE"],
    "base_idf": "../data/base_idfs/building_with_zones.idf"
  },
  
  "vrf_perimeter": {
    "prompt": "Design VRF with electric baseboard for perimeter zones",
    "zones": ["ZONE ONE"],
    "base_idf": "../data/base_idfs/building_with_zones.idf"
  }
}
```

### 8.3 Multi-Zone Systems

**Requirements:**
1. ✅ Clean base IDF (no existing HVAC)
2. ✅ Correct zone names in request
3. ✅ Sizing enabled in SimulationControl

**Step 1:** Create clean base IDF
```bash
cd utils
python clean_base_idf.py

# Input: ../data/base_idfs/4ZoneWithShading_Simple_2.idf
# Output: ../data/base_idfs/4ZoneWithShading_Simple_2_NoHVAC.idf
```

**Step 2:** Create multi-zone request
```json
{
  "my_multi_zone": {
    "prompt": "Design VRF for multiple zones with independent control",
    "zones": ["ZONE 1", "ZONE 2", "ZONE 3", "ZONE 4"],
    "base_idf": "../data/base_idfs/4ZoneWithShading_Simple_2_NoHVAC.idf"
  }
}
```

**Step 3:** Run
```bash
python example3_config_based.py
# Choose: my_multi_zone
```

### 8.4 Custom Base IDF Files

**Creating your own base IDF:**

1. **Model building geometry** in DesignBuilder, OpenStudio, or IDF Editor
2. **Add internal loads:**
   - People (occupancy)
   - Lights (lighting power)
   - Equipment (plug loads)
   - Thermostats (setpoints)
3. **Enable sizing:**
   ```
   SimulationControl,
     Yes,  !- Do Zone Sizing Calculation
     Yes,  !- Do System Sizing Calculation
     No,   !- Do Plant Sizing Calculation
     Yes;  !- Run Simulation
   ```
4. **Remove existing HVAC:**
   ```bash
   python utils/clean_base_idf.py
   # Select your IDF file
   ```
5. **Save as:** `data/base_idfs/my_building_NoHVAC.idf`

6. **Use in request:**
   ```json
   {
     "my_request": {
       "prompt": "Design VRF...",
       "zones": ["Zone1", "Zone2"],
       "base_idf": "../data/base_idfs/my_building_NoHVAC.idf"
     }
   }
   ```

### 8.5 Results Analysis

**Locate results:**
```
outputs/
├── generated_idfs/
│   ├── my_system_hvac.idf       # Initial generation
│   ├── my_system_fixed_1.idf    # After correction 1
│   ├── my_system_fixed_2.idf    # After correction 2
│   └── my_system_FINAL.idf      # ✅ USE THIS!
│
├── logs/
│   └── my_system_results.json   # Detailed execution log
│
└── simulations/
    ├── my_system_sim1/          # Initial simulation
    │   ├── eplusout.err         # Error messages
    │   └── eplusout.eso         # Simulation outputs
    └── my_system_sim2/          # Re-simulation after fix
        ├── eplusout.err
        └── eplusout.eso
```

**Read results JSON:**
```python
import json

with open('outputs/logs/my_system_results.json', 'r') as f:
    results = json.load(f)

print(f"Status: {results['final_status']}")
print(f"Iterations: {results['total_iterations']}")
print(f"Quick validation: {results['quick_validation_enabled']}")

# View steps
for step in results['steps']:
    print(f"Step {step['step']}: {step['name']}")
```

---

## 9. Troubleshooting

### 9.1 Common Issues & Solutions

#### Issue 1: "API Key Not Found"

**Error:**
```
⚠ No API keys found, using MOCK mode
```

**Solution:**
1. Check `.env` file exists in project root
2. Verify API key is correct
3. No spaces around `=` in `.env`
4. Restart terminal/IDE after editing `.env`

```bash
# Verify
python -c "from config import Config; print(Config.get_api_key('gemini'))"
```

---

#### Issue 2: "EnergyPlus Not Found"

**Error:**
```
FileNotFoundError: EnergyPlus executable not found
```

**Solution:**
1. Verify EnergyPlus installation
2. Check path in `.env`
3. Use forward slashes `/`
4. Check file exists:
   ```bash
   # Windows
   dir "C:\EnergyPlusV25-1-0\energyplus.exe"
   
   # macOS/Linux
   ls /Applications/EnergyPlus-25-1-0/energyplus
   ```

---

#### Issue 3: "Simulation Failed"

**Error:**
```
** Fatal  ** GetVRFInput: Errors found...
```

**Solution:**
1. ✅ Check if `*_FINAL.idf` was created (success!)
2. ❌ If not, check `*_fixed_N.idf` files
3. Read error in `outputs/simulations/*/eplusout.err`
4. Check zone names match exactly
5. Ensure base IDF has no existing HVAC

**Common causes:**
- Wrong zone names (case-sensitive)
- Base IDF has existing HVAC equipment
- Sizing not enabled in SimulationControl

---

#### Issue 4: "Module Not Found"

**Error:**
```
ModuleNotFoundError: No module named 'eppy'
```

**Solution:**
```bash
pip install -r requirements.txt
```

---

#### Issue 5: "Empty HVAC Configuration Generated"

**Error:**
```
❌ Error: Empty HVAC configuration generated
```

**Solution:**
1. Check LLM API is working
2. Verify API key has quota remaining
3. Check internet connection
4. Try different LLM provider
5. Check prompt is not too complex

---

#### Issue 6: "Too Many ZoneHVAC:EquipmentConnections"

**Error:**
```
** Fatal  ** Too many ZoneHVAC:EquipmentConnections...
```

**Solution:**
Base IDF has existing HVAC equipment!

```bash
# Clean the base IDF
cd utils
python clean_base_idf.py

# Select the IDF with existing HVAC
# Output will have _NoHVAC.idf suffix
```

---

### 9.2 Debug Mode

**Enable detailed logging:**

```python
# In config/settings.py
LOG_LEVEL = "DEBUG"
```

**Or environment variable:**
```bash
export LOG_LEVEL=DEBUG
python example2_complete_pipeline.py
```

---

### 9.3 Test Your Setup

```bash
# Run test suite
cd tests
python test_quick_validation_pipeline.py
```

**Expected:**
```
✅ ALL TESTS PASSED!
Quick validation feature is working correctly.
```

---

## 10. Best Practices

### 10.1 Base IDF Preparation

✅ **DO:**
- Start with clean base IDF (no HVAC)
- Include internal loads (People, Lights, Equipment)
- Include thermostats with setpoints
- Enable sizing in SimulationControl
- Use clear, consistent zone names
- Include weather file reference

❌ **DON'T:**
- Use base IDF with existing HVAC equipment
- Forget internal loads (causes sizing errors)
- Disable sizing calculations
- Use spaces or special characters in zone names

### 10.2 Writing Effective User Requests

✅ **Good Requests:**
```
"Design a VRF HVAC system with heat recovery for efficient heating and cooling"
"Design high-efficiency VRF with COP 4.5 for cold climate below -20°C"
"Design VRF with electric supplemental heating activated below -15°C"
"Design VRF for multiple zones with independent temperature control"
```

❌ **Vague Requests:**
```
"Make HVAC"
"VRF system"
"Something for heating and cooling"
```

**Tips:**
- Be specific about features (heat recovery, high efficiency)
- Mention climate if relevant (cold, hot, humid)
- Specify special requirements (supplemental heating, LEED)
- Include control preferences (independent, master thermostat)

### 10.3 Output File Management

✅ **ALWAYS USE:** `*_FINAL.idf` files  
❌ **DON'T USE:** `*_hvac.idf` files (unfixed)

**File naming convention:**
```
my_system_hvac.idf          # Initial generation (may have errors)
my_system_fixed_1.idf       # After correction 1
my_system_fixed_2.idf       # After correction 2
my_system_FINAL.idf         # ✅ Final corrected (USE THIS!)
```

### 10.4 Performance Optimization

**For single runs:**
- ✅ Enable quick validation (default)
- ✅ Use detailed logging
- ✅ Review validation warnings

**For batch processing (100+ buildings):**
- ❌ Disable quick validation
- ❌ Reduce logging to WARNING
- ✅ Use Python API directly
- ✅ Process in parallel if possible

```python
# Batch processing configuration
results = pipeline.run(
    base_idf="...",
    zones=zones,
    enable_quick_validation=False,  # Disable for speed
)
```

### 10.5 Version Control

**Files to commit:**
- ✅ Source code (`src/`, `examples/`, `tests/`)
- ✅ Configuration templates (`config/*.py`)
- ✅ Documentation (`docs/`, `README.md`)
- ✅ Requirements (`requirements.txt`)

**Files to ignore (add to `.gitignore`):**
- ❌ `.env` (contains API keys!)
- ❌ `outputs/` (generated files)
- ❌ `__pycache__/` (Python cache)
- ❌ `*.pyc` (compiled Python)

---

## 11. API Reference

### 11.1 HVACLLMPipeline Class

```python
class HVACLLMPipeline:
    """Main pipeline orchestrator"""
    
    def __init__(self):
        """Initialize pipeline with all agents"""
        pass
    
    def run(
        self,
        base_idf: str,
        zones: List[str],
        output_name: str = "pipeline_output",
        system_name: str = "VRF_System_1",
        user_request: str = None,
        enable_quick_validation: bool = True
    ) -> Dict:
        """
        Run complete HVAC generation pipeline.
        
        Args:
            base_idf: Path to base IDF file (building without HVAC)
            zones: List of zone names (must match IDF)
            output_name: Prefix for output files
            system_name: Name for VRF system
            user_request: Natural language design request
            enable_quick_validation: Enable pre-simulation validation
        
        Returns:
            {
                'final_status': 'SUCCESS' or 'FAILED',
                'final_idf': 'path/to/final.idf',
                'total_iterations': int,
                'quick_validation_enabled': bool,
                'steps': [...]
            }
        """
```

### 11.2 QuickValidator Class

```python
class QuickValidator:
    """Pre-simulation validation"""
    
    def validate(
        self,
        idf_content: str,
        zones: List[str],
        user_request: str = ""
    ) -> Dict:
        """
        Validate generated HVAC configuration.
        
        Args:
            idf_content: Generated HVAC IDF text
            zones: List of zone names
            user_request: Original user request
        
        Returns:
            {
                'valid': bool,
                'errors': List[str],
                'warnings': List[str],
                'passed_checks': List[str]
            }
        """
```

### 11.3 Configuration Variables

```python
# config/settings.py

# LLM Settings
Config.LLM_PROVIDER         # "gemini", "openai", "anthropic"
Config.LLM_MODEL            # Model name
Config.LLM_TEMPERATURE      # 0.0-1.0
Config.LLM_MAX_TOKENS       # Max response length

# EnergyPlus
Config.ENERGYPLUS_EXE       # Path to energyplus executable
Config.ENERGYPLUS_IDD       # Path to Energy+.idd

# Pipeline
Config.MAX_ERROR_CORRECTION_ITERATIONS  # Max fix attempts
Config.ENABLE_QUICK_VALIDATION         # Pre-simulation validation

# Paths
Config.OUTPUT_DIR           # Output directory
Config.BASE_IDF_DIR         # Base IDF directory
```

---

## 12. Examples & Use Cases

### 12.1 Example 1: Simple Office Building

**Scenario:** Single-zone office, standard VRF

```bash
cd examples
python example3_config_based.py
# Choose: vrf_single_zone
```

**Time:** ~45 seconds  
**Output:** `vrf_single_zone_FINAL.idf`

---

### 12.2 Example 2: Cold Climate Building

**Scenario:** VRF with supplemental heating

**Step 1:** Add to `config/hvac_requests.json`
```json
{
  "cold_climate_office": {
    "prompt": "Design VRF with electric supplemental heating below -15°C for Minnesota cold climate",
    "zones": ["ZONE ONE"],
    "base_idf": "../data/base_idfs/building_with_zones.idf"
  }
}
```

**Step 2:** Run
```bash
python example3_config_based.py
# Choose: cold_climate_office
```

**Expected:** Fields 33-36 populated with supplemental heating

---

### 12.3 Example 3: LEED Platinum Building

**Scenario:** High-efficiency VRF with parasitic load tracking

```json
{
  "leed_platinum": {
    "prompt": "Design high-efficiency VRF with COP 4.5 and detailed parasitic load tracking for LEED Platinum certification",
    "zones": ["ZONE ONE"],
    "base_idf": "../data/base_idfs/building_with_zones.idf"
  }
}
```

**Expected:** Fields 37-38 populated with parasitic loads (25W on, 5W off)

---

### 12.4 Example 4: Multi-Zone Office

**Scenario:** 4-zone office building

```bash
python example3_config_based.py
# Choose: vrf_multi_zone_office
```

**Zones:** ZONE 1, ZONE 2, ZONE 3, ZONE 4  
**Base IDF:** `4ZoneWithShading_Simple_2_NoHVAC.idf` (clean!)  
**Time:** ~60 seconds  

---

### 12.5 Example 5: Batch Processing

**Scenario:** Process all configurations

```bash
python example3_config_based.py
# Choose: all
```

**Processes:**
- vrf_single_zone
- vrf_heat_recovery
- vrf_multi_zone_office
- vrf_high_efficiency
- vrf_cold_climate

**Time:** ~5 minutes  
**Outputs:** 5 FINAL IDF files

---

### 12.6 Example 6: Custom Integration

**Scenario:** Integrate into your Python workflow

```python
#!/usr/bin/env python3
"""
Custom integration example
"""

from src.pipeline import HVACLLMPipeline
import pandas as pd

# Load building parameters from CSV
buildings = pd.read_csv('my_buildings.csv')

pipeline = HVACLLMPipeline()

results_summary = []

for idx, row in buildings.iterrows():
    print(f"\nProcessing building {idx+1}/{len(buildings)}: {row['name']}")
    
    # Generate HVAC
    result = pipeline.run(
        base_idf=row['base_idf_path'],
        zones=row['zones'].split(','),
        output_name=row['name'],
        user_request=row['hvac_requirements'],
        enable_quick_validation=True
    )
    
    # Collect results
    results_summary.append({
        'building': row['name'],
        'status': result['final_status'],
        'iterations': result['total_iterations'],
        'output': result.get('final_idf', 'N/A')
    })

# Save summary
summary_df = pd.DataFrame(results_summary)
summary_df.to_csv('hvac_generation_summary.csv', index=False)

print("\n" + "=" * 70)
print("BATCH PROCESSING COMPLETE")
print("=" * 70)
print(summary_df.to_string(index=False))
```

---

## Appendix A: Keyboard Shortcuts

**Example 3 Interactive Mode:**
- `Ctrl+C` - Exit program
- `all` - Process all requests
- `help` - Show help information
- `novalidation <request_id>` - Run without quick validation

---

## Appendix B: File Extensions

| Extension | Description |
|-----------|-------------|
| `.idf` | EnergyPlus Input Data File |
| `.json` | Configuration/Results (JSON format) |
| `.err` | EnergyPlus error messages |
| `.eso` | EnergyPlus Standard Output |
| `.csv` | EnergyPlus CSV output |
| `.py` | Python source code |
| `.md` | Markdown documentation |

---

## Appendix C: Support & Resources

**Documentation:**
- Project README: `README.md`
- Installation Guide: `docs/INSTALLATION.md`
- Quick Validation: `docs/QUICK_VALIDATION_IMPLEMENTATION.md`
- VRF Fields: `docs/VRF_42_FIELDS_EXPLAINED.md`
- File Guide: `docs/WHICH_FILE_TO_USE.md`

**EnergyPlus Resources:**
- Official Website: https://energyplus.net/
- Documentation: https://energyplus.net/documentation
- Example Files: `C:\EnergyPlusV25-1-0\ExampleFiles\`

**LLM Providers:**
- Google Gemini: https://aistudio.google.com/
- OpenAI: https://platform.openai.com/
- Anthropic: https://console.anthropic.com/

---

## Appendix D: Glossary

| Term | Definition |
|------|------------|
| **IDF** | Input Data File (EnergyPlus format) |
| **VRF** | Variable Refrigerant Flow (HVAC system type) |
| **LLM** | Large Language Model (AI) |
| **Agent** | AI module with specific task |
| **Base IDF** | Building geometry without HVAC |
| **Zone** | Thermal zone in building |
| **Sizing** | Automatic equipment capacity calculation |
| **COP** | Coefficient of Performance (efficiency) |
| **HVACTemplate** | Simplified HVAC input objects |
| **ExpandObjects** | EnergyPlus preprocessor |
| **Simulation** | Running EnergyPlus energy analysis |

---

## Document Information

**Version:** 1.0  
**Last Updated:** October 29, 2025  
**Author:** HVAC-LLM Development Team  
**License:** MIT License  

**For questions or support:**
- GitHub Issues: [repository]/issues
- Email: support@hvac-llm.example.com
- Documentation: https://docs.hvac-llm.example.com

---

**END OF USER GUIDE**

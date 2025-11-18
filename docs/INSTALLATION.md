# Installation Guide

## Prerequisites

### 1. Install EnergyPlus

1. Download EnergyPlus from: https://energyplus.net/downloads
2. Install (recommended: version 23.2 or 24.1)
3. Note the installation directory (e.g., `C:\EnergyPlusV24-1-0`)

### 2. Install Python

- Python 3.8 or higher
- Download from: https://www.python.org/downloads/

## Installation Steps

### Step 1: Clone/Download Project

```bash
# If using git
git clone <repository-url>
cd HVAC-LLM

# Or download and extract ZIP
```

### Step 2: Install Python Dependencies

```bash
# Basic dependencies (required)
pip install eppy pandas

# LLM providers (optional)
pip install openai      # For OpenAI GPT
pip install anthropic   # For Anthropic Claude
pip install google-generative-ai  # For Google Gemini (Generative Models)
```

### Step 3: Configure Settings

1. Open `config/settings.py`
2. Update `ENERGYPLUS_DIR` to your installation path:

```python
ENERGYPLUS_DIR = r"C:\EnergyPlusV25-1-0"  # Windows
# or
ENERGYPLUS_DIR = "/usr/local/EnergyPlus-25-1-0"  # Linux/Mac
```

### Step 4: Set API Keys (Optional)

For real LLM usage, set environment variables:

**Windows (Command Prompt):**
```cmd
set GEMINI_API_KEY=your_key_here
set ANTHROPIC_API_KEY=your_key_here
set OPENAI_API_KEY=your_key_here
```

**Windows (PowerShell):**
```powershell
$env:GEMINI_API_KEY="your_key_here"
$env:ANTHROPIC_API_KEY="your_key_here"
$env:OPENAI_API_KEY="your_key_here"
```

**Linux/Mac:**
```bash
export GEMINI_API_KEY="your_key_here"
export ANTHROPIC_API_KEY="your_key_here"
export OPENAI_API_KEY="your_key_here"
```

**Note:** If no API keys are set, the system will run in **Mock Mode** (simulated responses).

### Step 5: Verify Installation

```python
# Test imports
python -c "from eppy.modeleditor import IDF; print('✓ Eppy installed')"

# Test configuration
python -c "from config import Config; print(f'✓ EnergyPlus: {Config.ENERGYPLUS_DIR}')"
```

## Prepare Base IDF Files

You need a base IDF file with:
- Building definition
- Zones
- Geometry (surfaces)
- Schedules

Place base IDF files in: `data/base_idfs/`

### Quick Start: Use Example File

Copy a complete IDF from your EnergyPlus installation:

```bash
# Copy an example file
cp "C:\EnergyPlusV24-1-0\ExampleFiles\5ZoneAirCooled.idf" data/base_idfs/
```

Remove HVAC objects from the file (keep only building, zones, geometry).

## First Run

```python
from src.pipeline import HVACLLMPipeline

pipeline = HVACLLMPipeline()

results = pipeline.run(
    base_idf="data/base_idfs/your_building.idf",
    zones=["Zone_1", "Zone_2"],
    output_name="first_test"
)
```

## Troubleshooting

### Issue: "Cannot find EnergyPlus"

- Check `ENERGYPLUS_DIR` path in `config/settings.py`
- Ensure `energyplus.exe` exists in that directory

### Issue: "Cannot load IDF"

- Ensure IDF file is valid EnergyPlus format
- Check that `Energy+.idd` file exists in EnergyPlus directory

### Issue: "No module named 'eppy'"

```bash
pip install eppy
```

### Issue: LLM API errors

- Verify API key is set correctly
- System will automatically fall back to Mock Mode if API unavailable

## Next Steps

1. Read `docs/USAGE.md` for detailed usage examples
2. Check `outputs/logs/` for pipeline execution logs
3. View simulation results in `outputs/simulations/`

## Support

For issues related to:
- EnergyPlus: https://energyplus.net/support
- Eppy: https://github.com/santoshphilip/eppy
- This project: [Your contact/repository]

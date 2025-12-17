# Installation Instructions for HVAC-LLM Dependencies

## Step 1: Install pip (Python Package Manager)

```bash
sudo apt install python3-pip
```

## Step 2: Install Python Dependencies

```bash
cd /home/hubel/Documents/Ayeen/EnergyPlus-HVAC-LLM
pip3 install -r requirements.txt
```

Or if you prefer to install without sudo:

```bash
cd /home/hubel/Documents/Ayeen/EnergyPlus-HVAC-LLM
pip3 install --user -r requirements.txt
```

## Step 3: Verify Installation

```bash
python3 -c "import eppy; print('eppy installed successfully')"
python3 -c "import google.generativeai; print('google-generativeai installed successfully')"
python3 -c "import chromadb; print('chromadb installed successfully')"
```

## Step 4: Run Example

```bash
cd /home/hubel/Documents/Ayeen/EnergyPlus-HVAC-LLM/examples
python3 example4_auto_detection.py
```

## Required Packages

The following packages will be installed:

- **eppy** - EnergyPlus IDF file parser
- **pandas** - Data manipulation
- **google-generativeai** - Google Gemini API client
- **transformers** - Hugging Face transformers for LLMs
- **torch** - PyTorch for ML models
- **accelerate** - Model acceleration
- **chromadb** - Vector database for RAG
- **sentence-transformers** - Embedding models for RAG

## Troubleshooting

### If pip installation fails:

Update apt package list first:
```bash
sudo apt update
sudo apt install python3-pip
```

### If package installation is slow:

Some packages like `torch` are large (>1GB). Be patient during installation.

### If you get permission errors:

Use the `--user` flag:
```bash
pip3 install --user -r requirements.txt
```

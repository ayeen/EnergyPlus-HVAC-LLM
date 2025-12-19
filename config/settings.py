"""
Configuration settings for HVAC-LLM
"""

import os
from pathlib import Path

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)
except ImportError:
    # If python-dotenv not installed, manually load .env
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value

class Config:
    """Main configuration class"""
    
    # EnergyPlus Settings
    ENERGYPLUS_DIR = os.path.expanduser("~/Documents/Ayeen/Energy+")
    ENERGYPLUS_EXE = os.path.join(ENERGYPLUS_DIR, "energyplus")
    WEATHER_FILE = os.path.join(ENERGYPLUS_DIR, "WeatherData", 
                                "USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw")
    IDD_FILE = os.path.join(ENERGYPLUS_DIR, "Energy+.idd")
    
    # LLM Settings
    LLM_PROVIDER = "mistral"  # "gemini", "mistral", "anthropic", "mistral", "mock", or "auto"
    LLM_MODEL = "gemini-2.5-flash"  # Latest lite version - may have better quota
    # LLM_MODEl = "gemini-2.5-flash-lite"
    LLM_MAX_TOKENS = 16384
    LLM_TEMPERATURE = 0.3
    
    # Mistral Fine-tuned Model Settings
    MISTRAL_BASE_MODEL = "mistralai/Mistral-7B-v0.1"
    MISTRAL_FINETUNED_PATH = os.path.expanduser("~/Documents/Ayeen/LLM-Fine-Tunning/mistral-7b-vrf-finetuned-v4")
    MISTRAL_MAX_TOKENS_PER_OBJECT = 512  # For iterative generation
    MISTRAL_TEMPERATURE = 0.3
    MISTRAL_TOP_P = 0.9
    
    # RAG Settings
    USE_RAG = True  # Enable/Disable Retrieval-Augmented Generation
    RAG_TOP_K = 5   # Number of relevant documents to retrieve
    
    # Pipeline Settings
    MAX_ERROR_CORRECTION_ITERATIONS = 3
    SIMULATION_TIMEOUT = 120  # seconds
    
    # Paths
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_DIR = os.path.join(BASE_DIR, "data")
    OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
    
    @classmethod
    def get_api_key(cls, provider):
        """Get API key from environment"""
        if provider == "openai":
            return os.environ.get('OPENAI_API_KEY')
        elif provider == "anthropic":
            return os.environ.get('ANTHROPIC_API_KEY')
        elif provider == "gemini":
            # Gemini (Google Generative Models) API key
            return os.environ.get('GEMINI_API_KEY')
        return None

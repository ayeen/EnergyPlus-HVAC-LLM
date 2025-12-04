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
    ENERGYPLUS_DIR = r"C:\EnergyPlusV25-1-0"
    ENERGYPLUS_EXE = os.path.join(ENERGYPLUS_DIR, "energyplus.exe")
    WEATHER_FILE = os.path.join(ENERGYPLUS_DIR, "WeatherData", 
                                "USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw")
    IDD_FILE = os.path.join(ENERGYPLUS_DIR, "Energy+.idd")
    
    # LLM Settings
    # LLM_PROVIDER = "mistral"  # "gemini", "openai", "anthropic", "mistral", "mock", or "auto"
    # # Default model name. For Gemini you might set e.g. "gemini-2.5-flash" or similar.
    # LLM_MODEL = r"D:\Ayeen\Project\Hvac-finedtuned-mistral-model\mistral-7b-vrf-merged"
    LLM_PROVIDER = "gemini"  # Switch back temporarily
    LLM_MODEL = "gemini-2.5-flash"  # Stable model with better quota
    LLM_MAX_TOKENS = 16384
    LLM_TEMPERATURE = 0.3
    LLM_USE_8BIT = True  # Enable 8-bit quantization (faster loading, less memory, GPU only)
    
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
        elif provider == "mistral":
            # Mistral doesn't need API key for local models
            return None
        return None

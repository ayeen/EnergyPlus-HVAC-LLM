#!/usr/bin/env python3
"""
Mistral Model - Installation Verification
==========================================

This script checks if all dependencies for Mistral are properly installed
and if the model is accessible.

Run this BEFORE attempting to use Mistral.

Usage:
    python check_mistral_setup.py
"""

import sys
import os

def check_dependencies():
    """Check if all required packages are installed"""
    
    print("=" * 80)
    print("CHECKING DEPENDENCIES")
    print("=" * 80)
    print()
    
    dependencies = {
        'torch': 'PyTorch (deep learning)',
        'transformers': 'Hugging Face Transformers',
        'accelerate': 'Model acceleration',
        'peft': 'LoRA adapter loading',
        'bitsandbytes': '4-bit quantization',
    }
    
    all_installed = True
    
    for package, description in dependencies.items():
        try:
            __import__(package)
            print(f"✅ {package:20s} - {description}")
        except ImportError:
            print(f"❌ {package:20s} - {description} - NOT INSTALLED")
            all_installed = False
    
    print()
    
    if not all_installed:
        print("⚠️  Some dependencies are missing!")
        print()
        print("Install them with:")
        print("  pip install transformers torch accelerate peft bitsandbytes")
        print()
        return False
    
    print("✅ All dependencies installed!")
    print()
    return True


def check_gpu():
    """Check GPU availability"""
    
    print("=" * 80)
    print("CHECKING GPU")
    print("=" * 80)
    print()
    
    try:
        import torch
        
        if torch.cuda.is_available():
            print(f"✅ CUDA available: Yes")
            print(f"   GPU: {torch.cuda.get_device_name(0)}")
            print(f"   VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
            
            vram = torch.cuda.get_device_properties(0).total_memory / 1e9
            if vram >= 4:
                print(f"   Status: ✅ Sufficient VRAM for Mistral")
            else:
                print(f"   Status: ⚠️  Low VRAM (need 4GB+)")
            
            print()
            return True
        else:
            print("❌ CUDA not available")
            print("   Mistral requires GPU")
            print()
            print("💡 Options:")
            print("   1. Install CUDA and GPU drivers")
            print("   2. Use Gemini instead (no GPU required)")
            print()
            return False
            
    except ImportError:
        print("❌ PyTorch not installed")
        print()
        return False


def check_model_path():
    """Check if model exists"""
    
    print("=" * 80)
    print("CHECKING MODEL PATH")
    print("=" * 80)
    print()
    
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from config import Config
        
        model_path = Config.MISTRAL_FINETUNED_PATH
        print(f"Configured path: {model_path}")
        
        if os.path.exists(model_path):
            print(f"✅ Model directory exists")
            
            # Check for key files
            required_files = [
                'adapter_config.json',
                'tokenizer_config.json',
            ]
            
            missing = []
            for file in required_files:
                file_path = os.path.join(model_path, file)
                if os.path.exists(file_path):
                    print(f"   ✅ {file}")
                else:
                    print(f"   ❌ {file}")
                    missing.append(file)
            
            # Check for adapter model (could be .bin or .safetensors)
            has_adapter = False
            for ext in ['.bin', '.safetensors']:
                adapter_file = os.path.join(model_path, f'adapter_model{ext}')
                if os.path.exists(adapter_file):
                    print(f"   ✅ adapter_model{ext}")
                    has_adapter = True
                    break
            
            if not has_adapter:
                print(f"   ❌ adapter_model.bin or adapter_model.safetensors")
                missing.append('adapter_model')
            
            print()
            
            if missing:
                print(f"⚠️  Model files missing: {', '.join(missing)}")
                print()
                return False
            else:
                print("✅ All model files present")
                print()
                return True
        else:
            print(f"❌ Model directory not found")
            print()
            print("Please ensure the fine-tuned model is at:")
            print(f"  {model_path}")
            print()
            print("Or update the path in config/settings.py:")
            print("  MISTRAL_FINETUNED_PATH = '/your/path/to/model'")
            print()
            return False
            
    except Exception as e:
        print(f"❌ Error checking model: {e}")
        print()
        return False


def check_config():
    """Check configuration"""
    
    print("=" * 80)
    print("CHECKING CONFIGURATION")
    print("=" * 80)
    print()
    
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from config import Config
        
        print(f"Provider: {Config.LLM_PROVIDER}")
        
        if Config.LLM_PROVIDER == "mistral":
            print(f"✅ Configured to use Mistral")
            print()
            print(f"Mistral Settings:")
            print(f"  Base Model: {Config.MISTRAL_BASE_MODEL}")
            print(f"  Fine-tuned Path: {Config.MISTRAL_FINETUNED_PATH}")
            print(f"  Temperature: {Config.MISTRAL_TEMPERATURE}")
            print(f"  Top-P: {Config.MISTRAL_TOP_P}")
            print(f"  Max Tokens/Object: {Config.MISTRAL_MAX_TOKENS_PER_OBJECT}")
        elif Config.LLM_PROVIDER == "gemini":
            print(f"⚠️  Configured to use Gemini")
            print()
            print(f"To use Mistral, edit config/settings.py:")
            print(f"  LLM_PROVIDER = 'mistral'")
        else:
            print(f"⚠️  Unknown provider: {Config.LLM_PROVIDER}")
        
        print()
        return True
        
    except Exception as e:
        print(f"❌ Error reading config: {e}")
        print()
        return False


def test_model_loading():
    """Test if model can be loaded"""
    
    print("=" * 80)
    print("TESTING MODEL LOADING")
    print("=" * 80)
    print()
    
    print("⚠️  This will attempt to load the model (may take 30-60 seconds)")
    response = input("Continue? (y/n): ")
    
    if response.lower() != 'y':
        print("Skipped model loading test")
        print()
        return None
    
    print()
    print("Loading model...")
    
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
        from peft import PeftModel
        
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from config import Config
        
        # Configure quantization
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
        )
        
        # Load base model
        print("  Loading base model...")
        base_model = AutoModelForCausalLM.from_pretrained(
            Config.MISTRAL_BASE_MODEL,
            quantization_config=bnb_config,
            device_map="auto",
            torch_dtype=torch.float16,
        )
        
        # Load LoRA weights
        print("  Loading LoRA weights...")
        model = PeftModel.from_pretrained(base_model, Config.MISTRAL_FINETUNED_PATH)
        
        # Load tokenizer
        print("  Loading tokenizer...")
        tokenizer = AutoTokenizer.from_pretrained(Config.MISTRAL_FINETUNED_PATH)
        
        print()
        print("✅ Model loaded successfully!")
        print(f"   Device: {next(model.parameters()).device}")
        print(f"   Dtype: {next(model.parameters()).dtype}")
        print()
        
        return True
        
    except Exception as e:
        print()
        print(f"❌ Failed to load model: {e}")
        print()
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main verification"""
    
    print()
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 78 + "║")
    print("║" + "   Mistral Model Installation Verification".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("╚" + "═" * 78 + "╝")
    print()
    
    results = {
        'dependencies': check_dependencies(),
        'gpu': check_gpu(),
        'model_path': check_model_path(),
        'config': check_config(),
    }
    
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    
    for check, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status:10s} - {check.replace('_', ' ').title()}")
    
    print()
    
    all_passed = all(results.values())
    
    if all_passed:
        print("🎉 All checks passed! Mistral is ready to use.")
        print()
        print("Next steps:")
        print("  1. Run: python test_mistral_integration.py")
        print("  2. Or: python examples/example5_mistral_model.py")
        print()
        
        # Offer to test model loading
        test_model_loading()
        
    else:
        print("⚠️  Some checks failed. Please fix the issues above.")
        print()
        print("Common solutions:")
        print("  • Install dependencies: pip install -r requirements.txt")
        print("  • Install CUDA and GPU drivers")
        print("  • Verify model path in config/settings.py")
        print()
    
    print("=" * 80)
    print()


if __name__ == "__main__":
    main()

"""
Universal LLM Interface with Singleton Pattern
"""

import os
import json
from config import Config
from google.generativeai.types import HarmCategory, HarmBlockThreshold

class UniversalLLM:
    """Universal interface for LLM providers (Singleton to prevent multiple model loads)"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls, provider=None):
        """Ensure only one instance exists across all agents"""
        if cls._instance is None:
            cls._instance = super(UniversalLLM, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, provider=None):
        """Initialize only once - subsequent calls reuse the same model"""
        requested_provider = provider or Config.LLM_PROVIDER
        
        # If already initialized with a different provider, warn but keep existing
        if UniversalLLM._initialized:
            if hasattr(self, 'provider') and self.provider != requested_provider:
                print(f"⚠ LLM already initialized with '{self.provider}', ignoring request for '{requested_provider}'")
                print(f"  To switch providers, restart your Python session or call UniversalLLM.reset()")
            else:
                print("✓ Reusing existing LLM instance (no reload needed)")
            return
        
        self.provider = requested_provider
        self.client = None
        
        if self.provider == "auto":
            self.provider = self._detect_provider()
        
        print(f"✓ Initializing NEW LLM instance (provider: {self.provider})")
        self._initialize()
        UniversalLLM._initialized = True
    
    @classmethod
    def reset(cls):
        """Reset singleton to allow re-initialization with different provider"""
        cls._instance = None
        cls._initialized = False
        print("✓ LLM instance reset. Next call will create new instance.")
    
    def _detect_provider(self):
        """Auto-detect available provider"""
        # Prefer Mistral (local fine-tuned), then Gemini if available, then Anthropic, then OpenAI
        if self.provider == "mistral" or Config.LLM_PROVIDER == "mistral":
            return "mistral"
        if Config.get_api_key("gemini"):
            return "gemini"
        if Config.get_api_key("anthropic"):
            return "anthropic"
        elif Config.get_api_key("openai"):
            return "openai"
        else:
            print("⚠ No API keys found, using MOCK mode")
            return "mock"
    
    def _initialize(self):
        """Initialize provider"""
        if self.provider == "mistral":
            try:
                from transformers import AutoModelForCausalLM, AutoTokenizer
                import torch
                
                model_path = Config.LLM_MODEL
                print(f"✓ Loading fine-tuned Mistral model from {model_path}")
                
                # Load tokenizer
                self.tokenizer = AutoTokenizer.from_pretrained(
                    model_path,
                    trust_remote_code=True
                )
                
                # Determine if we can use GPU
                use_gpu = torch.cuda.is_available()
                
                if use_gpu:
                    # GPU: Try to use 8-bit quantization, fallback to FP16
                    try:
                        from transformers import BitsAndBytesConfig
                        import bitsandbytes
                        
                        print("✓ Using 8-bit quantization for faster loading and reduced memory...")
                        
                        # Configure 8-bit quantization
                        bnb_config = BitsAndBytesConfig(
                            load_in_8bit=True,
                            bnb_8bit_compute_dtype=torch.float16,
                            bnb_8bit_use_double_quant=True,
                        )
                        
                        self.model = AutoModelForCausalLM.from_pretrained(
                            model_path,
                            quantization_config=bnb_config,
                            device_map="auto",
                            trust_remote_code=True
                        )
                        self.device = "cuda"
                        print(f"✓ Model loaded on GPU with 8-bit quantization")
                    except (ImportError, Exception) as e:
                        print(f"✓ Using FP16 precision on GPU (8-bit unavailable on Windows)")
                        self.model = AutoModelForCausalLM.from_pretrained(
                            model_path,
                            dtype=torch.float16,
                            device_map="auto",
                            trust_remote_code=True,
                            max_memory={0: "7GB"}  # Limit to available VRAM
                        )
                        self.device = "cuda"
                        print(f"✓ Model loaded on GPU with FP16 (half precision)")
                else:
                    # CPU: Use FP32 (8-bit quantization not well supported on CPU)
                    print("⚠ No GPU detected, loading in FP32 (this will be slower)...")
                    self.model = AutoModelForCausalLM.from_pretrained(
                        model_path,
                        dtype=torch.float32,
                        low_cpu_mem_usage=True,
                        trust_remote_code=True
                    )
                    self.device = "cpu"
                    self.model = self.model.to(self.device)
                    print(f"✓ Using fine-tuned Mistral model on CPU")
                
                self.client = "mistral"  # Marker that mistral is loaded
            except Exception as e:
                print(f"⚠ Mistral model loading failed: {e}")
                import traceback
                traceback.print_exc()
                print("⚠ Falling back to MOCK mode")
                self.provider = "mock"
        elif self.provider == "gemini":
            try:
                # Attempt to import Google's generative AI client
                # The package name may vary; many setups use `google.generativeai` or `googleai`.
                # This will attempt a best-effort import and set API key from env.
                import google.generativeai as genai
                genai_api_key = Config.get_api_key("gemini")
                if genai_api_key:
                    genai.configure(api_key=genai_api_key)
                self.client = genai
                print("✓ Using Gemini")
            except Exception:
                # Fallback to mock if gemini client isn't available or fails to init
                print("⚠ Gemini client not available, falling back to MOCK")
    
    
    def generate(self, system_prompt, user_prompt):
        """Generate response with automatic provider fallback"""
        max_tokens = Config.LLM_MAX_TOKENS
       
        # Try primary provider first
        if self.provider == "mistral":
            response = self._generate_mistral(system_prompt, user_prompt, max_tokens)
        else:
            response = self._generate_gemini(system_prompt, user_prompt, max_tokens)
        return response or "************No response generated.*************"
    
    def _generate_gemini(self, system_prompt, user_prompt, max_tokens):
        """Generate using Gemini with enhanced error handling and retry logic."""
        try:
            genai = self.client
            print("✓ User Prompt:", user_prompt)
            # print("✓ System Prompt:", system_prompt)
            # Create multiple safety configurations with decreasing strictness
            safety_configs = [
                # Config 1: No safety filters (maximum permissiveness for technical content)
                {
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                },
                # Config 2: Block only high harm (permissive for technical content)
                {
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                },
                # Config 3: Block medium+ (middle ground)
                {
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                },
                # Config 4: Default settings (most restrictive)
                None
            ]
            
            # Try different temperature and top_p settings to vary response
            generation_configs = [
                # Standard settings
                {"temperature": Config.LLM_TEMPERATURE, "top_p": 0.95},
                
                # More creative
                {"temperature": Config.LLM_TEMPERATURE + 0.2, "top_p": 0.98},
                
                # Most deterministic
                {"temperature": max(0.1, Config.LLM_TEMPERATURE - 0.2), "top_p": 0.90},
            ]
            
            # Main retry loop - try all combinations of safety, prompt and generation settings
            for safety_idx, safety_settings in enumerate(safety_configs):
                for gen_idx, gen_config in enumerate(generation_configs):
                        try:
                            print(f"Gemini attempt: safety {safety_idx+1}, prompt, config {gen_idx+1}")
                            # Create model with current safety settings
                            model = genai.GenerativeModel(
                                Config.LLM_MODEL,
                                safety_settings=safety_settings if safety_settings else None
                            )
                            
                            #  Standard approach
                            combined_prompt = f"{system_prompt}\n\n{user_prompt}"
                            
                            # Try multiple attempts with slight variations
                            for attempt in range(3):
                                try:
                                    # Calculate jittered temperature
                                    temp = gen_config["temperature"] + (attempt * 0.05)
                                    
                                    # Generate content with current settings
                                    response = model.generate_content(
                                        combined_prompt,
                                        generation_config=genai.types.GenerationConfig(
                                            max_output_tokens=max_tokens,
                                            temperature=temp,
                                            top_p=gen_config["top_p"],
                                        )
                                    )
                                    
                                    # Check if we got a valid response
                                    if response and hasattr(response, 'candidates') and response.candidates:
                                        candidate = response.candidates[0]
                                        
                                        # Check finish reason - 2 means safety filter triggered
                                        if hasattr(candidate, 'finish_reason') and candidate.finish_reason == 2:
                                            print(f"⚠ Max Token Limit Reached (finish_reason=2), trying another request...")
                                            continue
                                        
                                        # Try to get content from candidate
                                        if hasattr(candidate, 'content') and candidate.content and hasattr(candidate.content, 'parts'):
                                            content = candidate.content.parts[0].text
                                            if content and content.strip():
                                                print(f"✓ Success with safety {safety_idx+1}, prompt, config {gen_idx+1}")
                                                return content
                                    
                                    # Alternative way to access response content
                                    if hasattr(response, 'text') and response.text and response.text.strip():
                                        print(f"✓ Success via response.text property")
                                        return response.text
                                        
                                except Exception as e:
                                    print(f"⚠ Attempt {attempt+1} error: {str(e)}")
                                    # Sleep briefly before retry
                                    import time
                                    time.sleep(0.5)
                                    continue
                                    
                        except Exception as e:
                            print(f"⚠ Configuration error: {str(e)}")
                            continue
                
        except Exception as e:
            print(f"⚠ Gemini generation failed: {e}")
            return ""
    
    def _generate_mistral(self, system_prompt, user_prompt, max_tokens):
        """Generate using fine-tuned Mistral model"""
        try:
            import torch
            
            # Combine prompts in Mistral format
            full_prompt = f"<s>[INST] {system_prompt}\n\n{user_prompt} [/INST]"
            
            print("✓ Generating with fine-tuned Mistral model...")
            
            # Tokenize input
            inputs = self.tokenizer(full_prompt, return_tensors="pt").to(self.device)
            
            # Generate
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    temperature=Config.LLM_TEMPERATURE,
                    do_sample=True,
                    top_p=0.95,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            
            # Decode output
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Extract only the generated part (after [/INST])
            if "[/INST]" in response:
                response = response.split("[/INST]")[-1].strip()
            
            print("✓ Mistral generation complete")
            return response
            
        except Exception as e:
            print(f"⚠ Mistral generation failed: {e}")
            import traceback
            traceback.print_exc()
            return ""
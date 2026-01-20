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
        self.mistral_model = None
        self.mistral_tokenizer = None
        
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
        # Prefer Gemini if available, then Anthropic, then OpenAI
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
        if self.provider == "gemini":
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
        
        elif self.provider == "mistral":
            self._load_mistral_finetuned()
        
        elif self.provider == "mistral-pretrained":
            self._load_mistral_pretrained()
        
        elif self.provider == "mistral-api":
            self._init_mistral_api()
    
    def _load_mistral_finetuned(self):
        """Load Mistral fine-tuned model with LoRA weights"""
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
            from peft import PeftModel
            
            print("⏳ Loading Mistral fine-tuned model...")
            print(f"   Base model: {Config.MISTRAL_BASE_MODEL}")
            print(f"   Fine-tuned path: {Config.MISTRAL_FINETUNED_PATH}")
            
            # Configure 4-bit quantization for efficient inference
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=False,
                llm_int8_enable_fp32_cpu_offload=True,
            )
            
            # Load base model
            base_model = AutoModelForCausalLM.from_pretrained(
                Config.MISTRAL_BASE_MODEL,
                quantization_config=bnb_config,
                device_map="auto",
                trust_remote_code=True,
                torch_dtype=torch.float16,
                max_memory={0: "14GB", "cpu": "30GB"},
            )
            
            # Load LoRA weights
            self.mistral_model = PeftModel.from_pretrained(base_model, Config.MISTRAL_FINETUNED_PATH)
            
            # Load tokenizer
            self.mistral_tokenizer = AutoTokenizer.from_pretrained(Config.MISTRAL_FINETUNED_PATH)
            self.mistral_tokenizer.pad_token = self.mistral_tokenizer.eos_token
            self.mistral_tokenizer.padding_side = "right"
            
            print("✓ Mistral fine-tuned model loaded successfully")
            print(f"   Model type: {Config.MISTRAL_FINETUNED_TYPE}")
            print(f"   Device: {next(self.mistral_model.parameters()).device}")
            if torch.cuda.is_available():
                print(f"   GPU: {torch.cuda.get_device_name(0)}")
            
        except Exception as e:
            print(f"⚠ Mistral fine-tuned model loading failed: {e}")
            print("  Falling back to MOCK mode")
            self.provider = "mock"
    
    def _load_mistral_pretrained(self):
        """Load Mistral pre-trained model (no LoRA weights) with optimized caching"""
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
            import os
            
            print("⏳ Loading Mistral pre-trained model...")
            print(f"   Model: {Config.MISTRAL_PRETRAINED_PATH}")
            print("   (This may take a few minutes on first run as model is downloaded from HuggingFace)")
            
            # Set HuggingFace cache directory for better control
            hf_cache_dir = os.path.expanduser("~/.cache/huggingface/hub")
            os.makedirs(hf_cache_dir, exist_ok=True)
            
            # Configure 4-bit quantization for efficient inference
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=False,
                llm_int8_enable_fp32_cpu_offload=True,
            )
            
            print("   Loading tokenizer...")
            # Load tokenizer first (smaller, faster)
            self.mistral_tokenizer = AutoTokenizer.from_pretrained(
                Config.MISTRAL_PRETRAINED_PATH,
                cache_dir=hf_cache_dir,
                trust_remote_code=True,
            )
            self.mistral_tokenizer.pad_token = self.mistral_tokenizer.eos_token
            self.mistral_tokenizer.padding_side = "right"
            print("   ✓ Tokenizer loaded")
            
            print("   Loading model weights (this may take 2-5 minutes)...")
            # Load pre-trained model directly (no LoRA)
            self.mistral_model = AutoModelForCausalLM.from_pretrained(
                Config.MISTRAL_PRETRAINED_PATH,
                quantization_config=bnb_config,
                device_map="auto",
                trust_remote_code=True,
                torch_dtype=torch.float16,
                max_memory={0: "14GB", "cpu": "30GB"},
                cache_dir=hf_cache_dir,
            )
            print("   ✓ Model weights loaded")
            
            print("✓ Mistral pre-trained model loaded successfully")
            print(f"   Model type: {Config.MISTRAL_PRETRAINED_TYPE}")
            print(f"   Device: {next(self.mistral_model.parameters()).device}")
            if torch.cuda.is_available():
                print(f"   GPU: {torch.cuda.get_device_name(0)}")
            
        except Exception as e:
            print(f"⚠ Mistral pre-trained model loading failed: {e}")
            print("  Falling back to MOCK mode")
            import traceback
            traceback.print_exc()
            self.provider = "mock"
    
    def _init_mistral_api(self):
        """Initialize Mistral API client (no local model download needed)"""
        try:
            from mistralai import Mistral
            
            api_key = Config.get_api_key("mistral")
            if not api_key:
                print("⚠ MISTRAL_API_KEY not found in environment")
                print("  Set it in .env file: MISTRAL_API_KEY=your-key-here")
                print("  Falling back to MOCK mode")
                self.provider = "mock"
                return
            
            self.mistral_client = Mistral(api_key=api_key)
            print(f"✓ Mistral API initialized")
            print(f"   Model: {Config.MISTRAL_API_MODEL}")
            print(f"   Type: pre-trained (API)")
            
        except ImportError:
            print("⚠ mistralai package not installed")
            print("  Install with: pip install mistralai")
            print("  Falling back to MOCK mode")
            self.provider = "mock"
        except Exception as e:
            print(f"⚠ Mistral API initialization failed: {e}")
            print("  Falling back to MOCK mode")
            self.provider = "mock"
    
    
    def generate(self, system_prompt, user_prompt):
        """Generate response with automatic provider fallback"""
        max_tokens = Config.LLM_MAX_TOKENS
       
        # Generate using configured provider
        if self.provider in ["mistral", "mistral-pretrained"]:
            response = self._generate_mistral(system_prompt, user_prompt, max_tokens)
        elif self.provider == "mistral-api":
            response = self._generate_mistral_api(system_prompt, user_prompt, max_tokens)
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
    
    def _generate_mistral_api(self, system_prompt, user_prompt, max_tokens):
        """
        Generate using Mistral API (pre-trained model, no local download needed).
        This is faster than loading the local model but requires API key.
        """
        try:
            if not hasattr(self, 'mistral_client') or self.mistral_client is None:
                print("⚠ Mistral API client not initialized")
                return ""
            
            print(f"✓ Generating with Mistral API ({Config.MISTRAL_API_MODEL})...")
            
            # Combine system and user prompts
            combined_prompt = f"{system_prompt}\n\n{user_prompt}"
            
            response = self.mistral_client.chat.complete(
                model=Config.MISTRAL_API_MODEL,
                messages=[
                    {"role": "user", "content": combined_prompt}
                ],
                temperature=Config.MISTRAL_TEMPERATURE,
                max_tokens=max_tokens
            )
            
            output = response.choices[0].message.content
            
            # Clean up markdown if present
            if output.startswith("```"):
                # Remove markdown code blocks
                import re
                output = re.sub(r'^```\w*\n?', '', output)
                output = re.sub(r'\n?```$', '', output)
            
            print(f"✓ Mistral API response received ({len(output)} chars)")
            return output
            
        except Exception as e:
            print(f"⚠ Mistral API generation failed: {e}")
            import traceback
            traceback.print_exc()
            return ""
    
    def _generate_mistral(self, system_prompt, user_prompt, max_tokens):
        """
        Generate using Mistral fine-tuned model with iterative prompting.
        This follows the successful pattern from generate_complete_vrf.py test script.
        """
        try:
            import torch
            import re
            
            if self.mistral_model is None or self.mistral_tokenizer is None:
                print("⚠ Mistral model not initialized")
                return ""
            
            print("✓ Generating with Mistral fine-tuned model...")
            
            # Parse the request to understand what to generate
            # Extract zones and system name from user_prompt
            zones = self._extract_zones_from_prompt(user_prompt)
            system_name = self._extract_system_name_from_prompt(user_prompt)
            building_context = self._extract_building_context_from_prompt(user_prompt)
            
            if not zones:
                print("⚠ No zones found in prompt, using direct generation")
                return self._generate_mistral_direct(system_prompt, user_prompt, max_tokens)
            
            print(f"   Found {len(zones)} zones: {', '.join(zones)}")
            print(f"   System name: {system_name}")
            
            # Use iterative generation approach (proven to work in testing)
            complete_config = self._generate_complete_vrf_iterative(
                zones, 
                system_name, 
                building_context
            )
            
            return complete_config
            
        except Exception as e:
            print(f"⚠ Mistral generation failed: {e}")
            import traceback
            traceback.print_exc()
            return ""
    
    def _generate_mistral_direct(self, system_prompt, user_prompt, max_tokens):
        """Direct generation for Mistral (used for error correction and non-VRF tasks)"""
        try:
            import torch
            
            # Limit tokens for direct generation (error correction doesn't need 16k tokens)
            # Error correction just needs to output a small JSON array
            effective_max_tokens = min(max_tokens, 1024)
            
            # Format prompt in Mistral instruction format
            prompt = f"<s>[INST] {system_prompt}\n\n{user_prompt} [/INST]\n\n"
            
            inputs = self.mistral_tokenizer(prompt, return_tensors="pt").to(self.mistral_model.device)
            
            print(f"   Generating response (max {effective_max_tokens} tokens)...")
            
            with torch.no_grad():
                outputs = self.mistral_model.generate(
                    **inputs,
                    max_new_tokens=effective_max_tokens,
                    temperature=Config.MISTRAL_TEMPERATURE,
                    top_p=Config.MISTRAL_TOP_P,
                    do_sample=True,
                    pad_token_id=self.mistral_tokenizer.eos_token_id,
                )
            
            # Decode only the new tokens (not the prompt)
            generated_tokens = outputs[0][len(inputs.input_ids[0]):]
            text = self.mistral_tokenizer.decode(generated_tokens, skip_special_tokens=True)
            
            # For error correction, we need JSON output, not IDF objects
            # Don't use _clean_mistral_output which looks for HVACTemplate
            if 'json' in user_prompt.lower() or '[' in text:
                # Return raw text for JSON responses
                return text.strip()
            
            cleaned = self._clean_mistral_output(text)
            return cleaned
            
        except Exception as e:
            print(f"⚠ Mistral direct generation failed: {e}")
            import traceback
            traceback.print_exc()
            return ""
    
    def _generate_complete_vrf_iterative(self, zones, system_name, building_context):
        """
        Generate complete VRF system using iterative prompting.
        This is the proven approach from the testing script.
        """
        try:
            import torch
            
            results = []
            
            # Step 1: Generate System VRF (pass zones for master thermostat location)
            print(f"   🔧 Generating System VRF...")
            system_vrf = self._generate_system_vrf(building_context, system_name, zones)
            if system_vrf:
                results.append(system_vrf)
                print(f"      ✅ System VRF generated ({len(system_vrf)} chars)")
            
            # Step 2: Generate Zone VRF for each zone
            print(f"   🏢 Generating Zone VRFs for {len(zones)} zones...")
            for i, zone_name in enumerate(zones, 1):
                print(f"      Zone {i}/{len(zones)}: {zone_name}...", end=" ")
                zone_vrf = self._generate_zone_vrf(zone_name, system_name)
                if zone_vrf:
                    results.append(zone_vrf)
                    print(f"✅ ({len(zone_vrf)} chars)")
                else:
                    print(f"⚠ Failed")
            
            # Step 3: Generate Thermostat for each zone
            print(f"   🌡️  Generating Thermostats for {len(zones)} zones...")
            for i, zone_name in enumerate(zones, 1):
                print(f"      Thermostat {i}/{len(zones)}: {zone_name}...", end=" ")
                thermostat = self._generate_thermostat(zone_name)
                if thermostat:
                    results.append(thermostat)
                    print(f"✅ ({len(thermostat)} chars)")
                else:
                    print(f"⚠ Failed")
            
            # Combine all objects
            complete_config = "\n\n".join(results)
            
            print(f"   ✅ Complete VRF system generated ({len(complete_config)} chars)")
            
            return complete_config
            
        except Exception as e:
            print(f"⚠ Iterative generation failed: {e}")
            import traceback
            traceback.print_exc()
            return ""
    
    def _generate_system_vrf(self, building_context, system_name, zones=None):
        """
        HYBRID APPROACH for HVACTemplate:System:VRF generation:
        
        1. Use fine-tuned model to generate DESIGN PARAMETERS (COP, temps, etc.)
           - The model's VALUE is in HVAC engineering knowledge
           
        2. Use template to ensure correct FIELD ORDER (37 fields per IDD)
           - Template handles EnergyPlus syntax compliance
           
        This separation allows:
        - Model updates without retraining (just adjust template)
        - EnergyPlus version compatibility (update template fields)
        - Reliable IDF generation (template guarantees valid syntax)
        """
        try:
            import torch
            import re
            
            # Get first zone name for master thermostat location
            master_zone = zones[0] if zones else "ZONE 1"
            num_zones = len(zones) if zones else 1
            
            # STEP 1: Ask model for HVAC design parameters (not IDF syntax)
            # The model's strength is engineering knowledge, not format compliance
            prompt = f"""<s>[INST] You are an HVAC engineer designing a VRF system.

Building info:
- Number of zones: {num_zones}
- Zone names: {', '.join(zones) if zones else 'Single zone'}
- Climate: Continental (cold winters, warm summers)

Provide optimal VRF system parameters:
1. Cooling COP (efficiency, typical 3.0-5.0)
2. Heating COP (efficiency, typical 3.5-5.5)
3. Min outdoor temp for cooling mode (°C)
4. Max outdoor temp for cooling mode (°C)
5. Min outdoor temp for heating mode (°C)
6. Max outdoor temp for heating mode (°C)
7. Condenser type (AirCooled/WaterCooled/EvaporativelyCooled)
8. Priority control (LoadPriority/ZonePriority/MasterThermostatPriority)

Output format - just values:
Cooling_COP: [value]
Heating_COP: [value]
Min_Cooling_Temp: [value]
Max_Cooling_Temp: [value]
Min_Heating_Temp: [value]
Max_Heating_Temp: [value]
Condenser: [type]
Priority: [type] [/INST]

Cooling_COP:"""
            
            inputs = self.mistral_tokenizer(prompt, return_tensors="pt").to(self.mistral_model.device)
            
            with torch.no_grad():
                outputs = self.mistral_model.generate(
                    **inputs,
                    max_new_tokens=200,  # Shorter - just need parameter values
                    temperature=0.3,
                    top_p=0.9,
                    do_sample=True,
                    pad_token_id=self.mistral_tokenizer.eos_token_id,
                )
            
            # Decode only the new tokens
            generated_tokens = outputs[0][len(inputs.input_ids[0]):]
            text = self.mistral_tokenizer.decode(generated_tokens, skip_special_tokens=True)
            
            # STEP 2: Parse model's design recommendations
            model_values = self._parse_design_parameters(text)
            
            # Log what the model learned
            if model_values:
                learned_params = [f"{k}={v}" for k, v in model_values.items()]
                # print(f"      Model learned: {', '.join(learned_params)}")
            
            # STEP 3: Build complete 37-field System:VRF using template + model values
            # Template guarantees EnergyPlus IDD compliance, model provides engineering values
            complete_system = self._build_system_vrf_template(system_name, master_zone, model_values)
            
            return complete_system
            
        except Exception as e:
            print(f"⚠ System VRF generation failed: {e}")
            return self._get_fallback_system_vrf(system_name, zones[0] if zones else "ZONE 1")
    
    def _parse_design_parameters(self, text):
        """
        Parse HVAC design parameters from model output.
        
        Supports both:
        - Structured format: "Cooling_COP: 3.8"
        - IDF format: "3.8,  !- Gross Rated Cooling COP"
        - Natural language: "Cooling COP should be 3.8"
        """
        import re
        values = {}
        
        # Pattern 1: Structured format (preferred)
        structured_patterns = {
            'cooling_cop': r'[Cc]ooling[_\s]*COP[:\s]+(\d+\.?\d*)',
            'heating_cop': r'[Hh]eating[_\s]*COP[:\s]+(\d+\.?\d*)',
            'min_cool_temp': r'[Mm]in[_\s]*[Cc]ooling[_\s]*[Tt]emp[:\s]+(-?\d+\.?\d*)',
            'max_cool_temp': r'[Mm]ax[_\s]*[Cc]ooling[_\s]*[Tt]emp[:\s]+(-?\d+\.?\d*)',
            'min_heat_temp': r'[Mm]in[_\s]*[Hh]eating[_\s]*[Tt]emp[:\s]+(-?\d+\.?\d*)',
            'max_heat_temp': r'[Mm]ax[_\s]*[Hh]eating[_\s]*[Tt]emp[:\s]+(-?\d+\.?\d*)',
            'condenser_type': r'[Cc]ondenser[:\s]*(AirCooled|WaterCooled|EvaporativelyCooled)',
            'priority': r'[Pp]riority[:\s]*(LoadPriority|ZonePriority|MasterThermostatPriority)',
        }
        
        for key, pattern in structured_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                values[key] = match.group(1)
        
        # Pattern 2: IDF format fallback (if model outputs IDF-style)
        if 'cooling_cop' not in values:
            cop_match = re.search(r'(\d+\.?\d*)\s*,?\s*!-\s*Gross Rated Cooling COP', text)
            if cop_match:
                values['cooling_cop'] = cop_match.group(1)
        
        if 'heating_cop' not in values:
            cop_match = re.search(r'(\d+\.?\d*)\s*,?\s*!-\s*Gross Rated Heating COP', text)
            if cop_match:
                values['heating_cop'] = cop_match.group(1)
        
        if 'min_cool_temp' not in values:
            temp_match = re.search(r'(-?\d+\.?\d*)\s*,?\s*!-\s*Minimum Outdoor Temperature in Cooling', text)
            if temp_match:
                values['min_cool_temp'] = temp_match.group(1)
        
        if 'max_cool_temp' not in values:
            temp_match = re.search(r'(-?\d+\.?\d*)\s*,?\s*!-\s*Maximum Outdoor Temperature in Cooling', text)
            if temp_match:
                values['max_cool_temp'] = temp_match.group(1)
        
        if 'min_heat_temp' not in values:
            temp_match = re.search(r'(-?\d+\.?\d*)\s*,?\s*!-\s*Minimum Outdoor Temperature in Heating', text)
            if temp_match:
                values['min_heat_temp'] = temp_match.group(1)
        
        if 'max_heat_temp' not in values:
            temp_match = re.search(r'(-?\d+\.?\d*)\s*,?\s*!-\s*Maximum Outdoor Temperature in Heating', text)
            if temp_match:
                values['max_heat_temp'] = temp_match.group(1)
        
        if 'condenser_type' not in values:
            cond_match = re.search(r'(AirCooled|WaterCooled|EvaporativelyCooled)\s*,?\s*!-\s*Condenser', text, re.IGNORECASE)
            if cond_match:
                values['condenser_type'] = cond_match.group(1)
        
        if 'priority' not in values:
            priority_match = re.search(r'(LoadPriority|ZonePriority|MasterThermostatPriority|Scheduled)', text, re.IGNORECASE)
            if priority_match:
                values['priority'] = priority_match.group(1)
        
        # Validate and constrain values to realistic ranges
        values = self._validate_design_parameters(values)
        
        return values
    
    def _validate_design_parameters(self, values):
        """Validate and constrain design parameters to realistic HVAC ranges"""
        
        # COP validation (realistic range 2.0 - 6.0)
        if 'cooling_cop' in values:
            try:
                cop = float(values['cooling_cop'])
                if cop < 2.0 or cop > 6.0:
                    values['cooling_cop'] = '3.5'  # Use default if out of range
            except ValueError:
                values['cooling_cop'] = '3.5'
        
        if 'heating_cop' in values:
            try:
                cop = float(values['heating_cop'])
                if cop < 2.0 or cop > 6.0:
                    values['heating_cop'] = '4.0'
            except ValueError:
                values['heating_cop'] = '4.0'
        
        # Temperature validation
        if 'min_cool_temp' in values:
            try:
                temp = float(values['min_cool_temp'])
                if temp < -20 or temp > 10:
                    values['min_cool_temp'] = '-10'
            except ValueError:
                values['min_cool_temp'] = '-10'
        
        if 'max_cool_temp' in values:
            try:
                temp = float(values['max_cool_temp'])
                if temp < 30 or temp > 55:
                    values['max_cool_temp'] = '48'
            except ValueError:
                values['max_cool_temp'] = '48'
        
        if 'min_heat_temp' in values:
            try:
                temp = float(values['min_heat_temp'])
                if temp < -35 or temp > 0:
                    values['min_heat_temp'] = '-25'
            except ValueError:
                values['min_heat_temp'] = '-25'
        
        if 'max_heat_temp' in values:
            try:
                temp = float(values['max_heat_temp'])
                if temp < 10 or temp > 25:
                    values['max_heat_temp'] = '18'
            except ValueError:
                values['max_heat_temp'] = '18'
        
        # Condenser type validation
        if 'condenser_type' in values:
            valid_types = ['AirCooled', 'WaterCooled', 'EvaporativelyCooled']
            if values['condenser_type'] not in valid_types:
                values['condenser_type'] = 'AirCooled'
        
        # Priority validation
        if 'priority' in values:
            valid_priorities = ['LoadPriority', 'ZonePriority', 'MasterThermostatPriority', 'Scheduled']
            if values['priority'] not in valid_priorities:
                values['priority'] = 'LoadPriority'
        
        return values
    
    def _build_system_vrf_template(self, system_name, master_zone, model_values):
        """
        Build complete 37-field HVACTemplate:System:VRF using template + model values.
        
        Template ensures EnergyPlus IDD v25.x compliance.
        Model values provide HVAC engineering intelligence.
        """
        return f"""HVACTemplate:System:VRF,
  {system_name},                  !- Name (A1)
  ,                        !- System Availability Schedule Name (A2)
  Autosize,                !- Gross Rated Total Cooling Capacity {{W}} (N1)
  {model_values.get('cooling_cop', '3.5')},                     !- Gross Rated Cooling COP {{W/W}} (N2)
  {model_values.get('min_cool_temp', '-10')},                    !- Minimum Outdoor Temperature in Cooling Mode {{C}} (N3)
  {model_values.get('max_cool_temp', '48')},                      !- Maximum Outdoor Temperature in Cooling Mode {{C}} (N4)
  Autosize,                !- Gross Rated Heating Capacity {{W}} (N5)
  1.0,                     !- Rated Heating Capacity Sizing Ratio (N6)
  {model_values.get('heating_cop', '4.0')},                     !- Gross Rated Heating COP {{W/W}} (N7)
  {model_values.get('min_heat_temp', '-25')},                   !- Minimum Outdoor Temperature in Heating Mode {{C}} (N8)
  {model_values.get('max_heat_temp', '18')},                      !- Maximum Outdoor Temperature in Heating Mode {{C}} (N9)
  0.15,                    !- Minimum Heat Pump Part-Load Ratio (N10)
  {master_zone},           !- Zone Name for Master Thermostat Location (A3)
  {model_values.get('priority', 'LoadPriority')},            !- Master Thermostat Priority Control Type (A4)
  ,                        !- Thermostat Priority Schedule Name (A5)
  No,                      !- Heat Pump Waste Heat Recovery (A6)
  30,                      !- Equivalent Piping Length for Cooling {{m}} (N11)
  10,                      !- Vertical Height for Piping Correction {{m}} (N12)
  30,                      !- Equivalent Piping Length for Heating {{m}} (N13)
  15,                      !- Crankcase Heater Power per Compressor {{W}} (N14)
  2,                       !- Number of Compressors (N15)
  0.5,                     !- Ratio of Compressor Size to Total Capacity (N16)
  5,                       !- Max Outdoor Dry-bulb Temp for Crankcase Heater {{C}} (N17)
  ReverseCycle,            !- Defrost Strategy (A7)
  OnDemand,                !- Defrost Control (A8)
  0.058333,                !- Defrost Time Period Fraction (N18)
  Autosize,                !- Resistive Defrost Heater Capacity {{W}} (N19)
  5,                       !- Max Outdoor Dry-bulb Temp for Defrost {{C}} (N20)
  {model_values.get('condenser_type', 'AirCooled')},               !- Condenser Type (A9)
  ,                        !- Water Condenser Volume Flow Rate {{m3/s}} (N21)
  0.9,                     !- Evaporative Condenser Effectiveness (N22)
  Autosize,                !- Evaporative Condenser Air Flow Rate {{m3/s}} (N23)
  Autosize,                !- Evaporative Condenser Pump Power {{W}} (N24)
  0.5,                     !- Basin Heater Capacity {{W/K}} (N25)
  2,                       !- Basin Heater Setpoint Temperature {{C}} (N26)
  ,                        !- Basin Heater Operating Schedule Name (A10)
  Electricity;             !- Fuel Type (A11)"""
    
    def _parse_system_vrf_values(self, text):
        """Legacy method - redirects to _parse_design_parameters for backward compatibility"""
        return self._parse_design_parameters(text)
    
    def _get_fallback_system_vrf(self, system_name, master_zone):
        """Fallback template when model generation fails - uses all 37 required fields"""
        return f"""HVACTemplate:System:VRF,
  {system_name},                  !- Name (A1)
  ,                        !- System Availability Schedule Name (A2)
  Autosize,                !- Gross Rated Total Cooling Capacity {{W}} (N1)
  3.5,                     !- Gross Rated Cooling COP {{W/W}} (N2)
  -10,                     !- Minimum Outdoor Temperature in Cooling Mode {{C}} (N3)
  48,                      !- Maximum Outdoor Temperature in Cooling Mode {{C}} (N4)
  Autosize,                !- Gross Rated Heating Capacity {{W}} (N5)
  1.0,                     !- Rated Heating Capacity Sizing Ratio (N6)
  4.0,                     !- Gross Rated Heating COP {{W/W}} (N7)
  -25,                     !- Minimum Outdoor Temperature in Heating Mode {{C}} (N8)
  18,                      !- Maximum Outdoor Temperature in Heating Mode {{C}} (N9)
  0.15,                    !- Minimum Heat Pump Part-Load Ratio (N10)
  {master_zone},           !- Zone Name for Master Thermostat Location (A3)
  LoadPriority,            !- Master Thermostat Priority Control Type (A4)
  ,                        !- Thermostat Priority Schedule Name (A5)
  No,                      !- Heat Pump Waste Heat Recovery (A6)
  30,                      !- Equivalent Piping Length for Cooling {{m}} (N11)
  10,                      !- Vertical Height for Piping Correction {{m}} (N12)
  30,                      !- Equivalent Piping Length for Heating {{m}} (N13)
  15,                      !- Crankcase Heater Power per Compressor {{W}} (N14)
  2,                       !- Number of Compressors (N15)
  0.5,                     !- Ratio of Compressor Size to Total Capacity (N16)
  5,                       !- Max Outdoor Dry-bulb Temp for Crankcase Heater {{C}} (N17)
  ReverseCycle,            !- Defrost Strategy (A7)
  OnDemand,                !- Defrost Control (A8)
  0.058333,                !- Defrost Time Period Fraction (N18)
  Autosize,                !- Resistive Defrost Heater Capacity {{W}} (N19)
  5,                       !- Max Outdoor Dry-bulb Temp for Defrost {{C}} (N20)
  AirCooled,               !- Condenser Type (A9)
  ,                        !- Water Condenser Volume Flow Rate {{m3/s}} (N21)
  0.9,                     !- Evaporative Condenser Effectiveness (N22)
  Autosize,                !- Evaporative Condenser Air Flow Rate {{m3/s}} (N23)
  Autosize,                !- Evaporative Condenser Pump Power {{W}} (N24)
  0.5,                     !- Basin Heater Capacity {{W/K}} (N25)
  2,                       !- Basin Heater Setpoint Temperature {{C}} (N26)
  ,                        !- Basin Heater Operating Schedule Name (A10)
  Electricity;             !- Fuel Type (A11)"""
    
    def _extract_system_vrf_fields(self, text, system_name):
        """Extract System:VRF fields from model output and build complete object"""
        lines = text.strip().split('\n')
        result_lines = ["HVACTemplate:System:VRF,"]
        found_semicolon = False
        
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            
            # Skip if it starts another object type
            if stripped.startswith('HVACTemplate:Zone:') or stripped.startswith('HVACTemplate:Thermostat'):
                break
            
            # Skip duplicate header if model included it
            if stripped.startswith('HVACTemplate:System:VRF'):
                continue
            
            result_lines.append("  " + stripped)
            
            # Stop at semicolon (end of object)
            if ';' in stripped:
                found_semicolon = True
                break
        
        # If no semicolon found, the object is incomplete - add default ending
        if not found_semicolon:
            # Remove trailing comma if present and add semicolon
            if result_lines and result_lines[-1].rstrip().endswith(','):
                result_lines[-1] = result_lines[-1].rstrip()[:-1] + ';'
            else:
                result_lines.append("  LoadPriority;                !- Master Thermostat Priority Control Type")
        
        return '\n'.join(result_lines)
    
    def _generate_zone_vrf(self, zone_name, system_name):
        """Generate HVACTemplate:Zone:VRF object with all 39 required fields per IDD"""
        try:
            import torch
            
            prompt = f"""<s>[INST] Generate a complete HVACTemplate:Zone:VRF object with these specifications:
- Zone Name: {zone_name}
- Template VRF System Name: {system_name}
- Template Thermostat Name: Thermostat_{zone_name}
- Cooling and Heating Supply Air Flow Rate: Autosize

Generate ONLY this single zone VRF object, end with semicolon. [/INST]

HVACTemplate:Zone:VRF,
  {zone_name},"""
            
            inputs = self.mistral_tokenizer(prompt, return_tensors="pt").to(self.mistral_model.device)
            
            with torch.no_grad():
                outputs = self.mistral_model.generate(
                    **inputs,
                    max_new_tokens=400,
                    temperature=0.3,
                    top_p=0.9,
                    do_sample=True,
                    pad_token_id=self.mistral_tokenizer.eos_token_id,
                )
            
            # Decode only the new tokens (not the prompt)
            generated_tokens = outputs[0][len(inputs.input_ids[0]):]
            text = self.mistral_tokenizer.decode(generated_tokens, skip_special_tokens=True)
            cleaned = self._clean_mistral_output(text)
            
            # Prepend the object type with zone name
            if not cleaned.startswith("HVACTemplate:Zone:VRF,"):
                cleaned = f"HVACTemplate:Zone:VRF,\n  {zone_name}," + cleaned
            
            # Validate: should have zone name and system name
            if zone_name not in cleaned or system_name not in cleaned:
                # Fallback: use complete template with all fields
                cleaned = self._get_fallback_zone_vrf(zone_name, system_name)
            
            return cleaned
            
        except Exception as e:
            print(f"⚠ Zone VRF generation failed: {e}")
            return self._get_fallback_zone_vrf(zone_name, system_name)
    
    def _get_fallback_zone_vrf(self, zone_name, system_name):
        """Fallback Zone:VRF template with all 39 required fields per IDD"""
        return f"""HVACTemplate:Zone:VRF,
  {zone_name},                          !- Zone Name (A1)
  {system_name},                        !- Template VRF System Name (A2)
  Thermostat_{zone_name},               !- Template Thermostat Name (A3)
  ,                                     !- Zone Heating Sizing Factor (N1) - blank uses Sizing:Parameters
  ,                                     !- Zone Cooling Sizing Factor (N2) - blank uses Sizing:Parameters
  1.0,                                  !- Rated Total Heating Capacity Sizing Ratio (N3)
  Autosize,                             !- Cooling Supply Air Flow Rate (N4)
  Autosize,                             !- No Cooling Supply Air Flow Rate (N5)
  Autosize,                             !- Heating Supply Air Flow Rate (N6)
  Autosize,                             !- No Heating Supply Air Flow Rate (N7)
  Autosize,                             !- Cooling Outdoor Air Flow Rate (N8)
  Autosize,                             !- Heating Outdoor Air Flow Rate (N9)
  Autosize,                             !- No Load Outdoor Air Flow Rate (N10)
  ,                                     !- Outdoor Air Method (A4)
  ,                                     !- Outdoor Air Flow Rate per Person (N11)
  ,                                     !- Outdoor Air Flow Rate per Zone Floor Area (N12)
  ,                                     !- Outdoor Air Flow Rate per Zone (N13)
  ,                                     !- Design Specification Outdoor Air Object Name (A5)
  ,                                     !- Design Specification Zone Air Distribution Object Name (A6)
  ,                                     !- System Availability Schedule Name (A7)
  ,                                     !- Supply Fan Operating Mode Schedule Name (A8)
  DrawThrough,                          !- Supply Air Fan Placement (A9)
  0.7,                                  !- Supply Fan Total Efficiency (N14)
  300,                                  !- Supply Fan Delta Pressure (N15)
  0.9,                                  !- Supply Fan Motor Efficiency (N16)
  VariableRefrigerantFlowDX,            !- Cooling Coil Type (A10)
  ,                                     !- Cooling Coil Availability Schedule Name (A11)
  Autosize,                             !- Cooling Coil Gross Rated Total Capacity (N17)
  Autosize,                             !- Cooling Coil Gross Rated Sensible Heat Ratio (N18)
  VariableRefrigerantFlowDX,            !- Heat Pump Heating Coil Type (A12)
  ,                                     !- Heat Pump Heating Coil Availability Schedule Name (A13)
  Autosize,                             !- Heat Pump Heating Coil Gross Rated Capacity (N19)
  30,                                   !- Zone Terminal Unit On Parasitic Electric Energy Use (N20)
  20,                                   !- Zone Terminal Unit Off Parasitic Electric Energy Use (N21)
  ,                                     !- Dedicated Outdoor Air System Name (A14)
  SupplyAirTemperature,                 !- Zone Cooling Design Supply Air Temperature Input Method (A15)
  12.8,                                 !- Zone Cooling Design Supply Air Temperature (N22)
  ,                                     !- Zone Cooling Design Supply Air Temperature Difference (N23)
  SupplyAirTemperature,                 !- Zone Heating Design Supply Air Temperature Input Method (A16)
  50;                                   !- Zone Heating Design Supply Air Temperature (N24)"""
    
    def _generate_thermostat(self, zone_name):
        """Generate HVACTemplate:Thermostat object using fine-tuned model with one-shot example"""
        try:
            import torch
            
            # One-shot example with almost complete structure
            # The model only needs to fill in the cooling setpoint value
            prompt = f"""<s>[INST] Generate HVACTemplate:Thermostat objects.

Example for Kitchen_Zone:
HVACTemplate:Thermostat,
  Thermostat_Kitchen_Zone,                !- Name
  ,                        !- Heating Setpoint Schedule Name
  20.5,                    !- Constant Heating Setpoint {{C}}
  ,                        !- Cooling Setpoint Schedule Name
  23.8;                    !- Constant Cooling Setpoint {{C}}

Now generate for {zone_name}: [/INST]

HVACTemplate:Thermostat,
  Thermostat_{zone_name},                !- Name
  ,                        !- Heating Setpoint Schedule Name
  20.0,                    !- Constant Heating Setpoint {{C}}
  ,                        !- Cooling Setpoint Schedule Name
  """
            
            inputs = self.mistral_tokenizer(prompt, return_tensors="pt").to(self.mistral_model.device)
            
            with torch.no_grad():
                outputs = self.mistral_model.generate(
                    **inputs,
                    max_new_tokens=30,  # Only need "24.0;  !- Constant Cooling Setpoint {C}"
                    temperature=0.1,  # Very low for deterministic output
                    top_p=0.9,
                    do_sample=True,
                    pad_token_id=self.mistral_tokenizer.eos_token_id,
                )
            
            # Decode only the new tokens (not the prompt)
            generated_tokens = outputs[0][len(inputs.input_ids[0]):]
            text = self.mistral_tokenizer.decode(generated_tokens, skip_special_tokens=True)
            
            # Clean the continuation - should be just "24.0;  !- Constant Cooling Setpoint {C}" or similar
            continuation = text.strip()
            
            # Find the first semicolon and stop there
            if ';' in continuation:
                end_idx = continuation.find(';')
                continuation = continuation[:end_idx + 1]
            else:
                # No semicolon found, just use the number if it's there
                import re
                num_match = re.search(r'(\d+\.?\d*)', continuation)
                if num_match:
                    continuation = num_match.group(1) + ';                    !- Constant Cooling Setpoint {C}'
                else:
                    continuation = '24.0;                    !- Constant Cooling Setpoint {C}'
            
            # Build the complete thermostat
            complete_thermostat = f"""HVACTemplate:Thermostat,
  Thermostat_{zone_name},                !- Name
  ,                        !- Heating Setpoint Schedule Name
  20.0,                    !- Constant Heating Setpoint {{C}}
  ,                        !- Cooling Setpoint Schedule Name
  {continuation}"""
            
            # Clean up any duplicate semicolons or trailing content
            lines = complete_thermostat.split('\n')
            clean_lines = []
            for line in lines:
                if ';' in line:
                    # Keep only up to the first semicolon and comment
                    semi_idx = line.find(';')
                    clean_lines.append(line[:semi_idx+1] + '                    !- Constant Cooling Setpoint {C}')
                    break
                else:
                    clean_lines.append(line)
            
            complete_thermostat = '\n'.join(clean_lines)
            
            return complete_thermostat
            
        except Exception as e:
            print(f"⚠ Thermostat generation failed: {e}")
            return ""
    
    def _clean_mistral_output(self, text):
        """Clean and extract the generated IDF object from Mistral output"""
        import re
        
        # Remove instruction markers
        if "[/INST]" in text:
            text = text.split("[/INST]")[1].strip()
        
        # Remove any trailing instruction text
        if "[INST]" in text:
            text = text.split("[INST]")[0].strip()
        
        # Find the first complete object (ends with semicolon)
        lines = text.split('\n')
        result_lines = []
        found_start = False
        
        for line in lines:
            # Skip empty lines at start
            if not found_start and not line.strip():
                continue
            
            # Start collecting from HVACTemplate
            if 'HVACTemplate' in line:
                found_start = True
            
            if found_start:
                result_lines.append(line)
                
                # Stop at semicolon (end of object)
                if ';' in line and not '!-' in line.split(';')[0]:
                    break
        
        return '\n'.join(result_lines).strip()
    
    def _extract_zones_from_prompt(self, prompt):
        """Extract zone names from the prompt"""
        import re
        
        zones = []
        
        # ONLY look for Zone objects in building context (most reliable)
        zone_matches = re.findall(r'Zone,\s*\n\s*([A-Za-z0-9_\s]+),', prompt)
        if zone_matches:
            zones.extend(zone_matches)
        
        # If no zones found from Zone objects, try explicit zones list
        if not zones:
            # Look for "zones: Zone1, Zone2, Zone3" pattern but STOP at "system name:"
            # Pattern: "zones:" followed by zone names until "system name:" or newline
            match = re.search(r'zones?:\s*([^,]+(?:,\s*[A-Za-z0-9_\s]+)*?)(?=,?\s*system[_ ]name:|$)', prompt, re.IGNORECASE)
            if match:
                zone_str = match.group(1)
                # Split by comma and clean
                zones = [z.strip() for z in zone_str.split(',') if z.strip()]
        
        # Remove duplicates while preserving order
        seen = set()
        unique_zones = []
        for zone in zones:
            if zone not in seen:
                seen.add(zone)
                unique_zones.append(zone)
        
        return unique_zones
    
    def _extract_system_name_from_prompt(self, prompt):
        """Extract system name from the prompt"""
        import re
        
        # Look for "system name: VRF_System_1" pattern
        match = re.search(r'system[_ ]name:\s*([A-Za-z0-9_]+)', prompt, re.IGNORECASE)
        if match:
            return match.group(1)
        
        # Default
        return "VRF_System_1"
    
    def _extract_building_context_from_prompt(self, prompt):
        """Extract building context from the prompt"""
        # Look for Building object
        if 'Building,' in prompt:
            # Extract from Building, to the end of zones
            start = prompt.find('Building,')
            # Find where building context likely ends (before technical specs)
            end = prompt.find('TECHNICAL')
            if end == -1:
                end = prompt.find('Generate')
            if end == -1:
                end = len(prompt)
            
            return prompt[start:end].strip()
        
        return ""

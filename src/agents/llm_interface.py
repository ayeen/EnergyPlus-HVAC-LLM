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
        """Reset singleton and free GPU memory to allow re-initialization."""
        # Explicitly delete model weights from GPU before clearing singleton
        if cls._instance is not None:
            inst = cls._instance
            if getattr(inst, 'mistral_model', None) is not None:
                del inst.mistral_model
                inst.mistral_model = None
            if getattr(inst, 'mistral_tokenizer', None) is not None:
                del inst.mistral_tokenizer
                inst.mistral_tokenizer = None

        cls._instance = None
        cls._initialized = False

        # Free any remaining cached GPU memory
        try:
            import gc, torch
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
        except Exception:
            pass

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
    
    # ─────────────────────────────────────────────────────────────────────────
    # USER-REQUEST HELPERS  (prompt parsing → design intent → IDF parameters)
    # ─────────────────────────────────────────────────────────────────────────

    def _extract_user_request_from_prompt(self, prompt: str) -> str:
        """
        Pull the user's natural-language design request back out of the combined
        prompt that _create_energyplus_template_prompt() assembled.

        The combined prompt always looks like:
            USER DESIGN REQUEST:
            <user's text here>

            TECHNICAL IMPLEMENTATION REQUIREMENTS: ...

        We return everything between those two headers, stripped of whitespace.
        Returns an empty string when no user request section is found.
        """
        if "USER DESIGN REQUEST:" not in prompt:
            return ""
        req_start = prompt.find("USER DESIGN REQUEST:") + len("USER DESIGN REQUEST:")
        # Stop at whichever section header comes first after the request block.
        end_markers = [
            "TECHNICAL IMPLEMENTATION",
            "**SIMILAR DESIGN PATTERNS",
            "Building IDF Context",
            "IMPORTANT VALIDATION",
        ]
        req_end = len(prompt)
        for marker in end_markers:
            pos = prompt.find(marker, req_start)
            if 0 < pos < req_end:
                req_end = pos
        return prompt[req_start:req_end].strip()

    def _parse_design_intent(self, user_request: str) -> dict:
        """
        Map keyword patterns in the user's natural-language request to concrete
        VRF parameter decisions.

        Returns a dict used by _generate_system_vrf, _generate_zone_vrf, and
        _generate_thermostat to customise the generated EnergyPlus objects.

        Keys and their meanings
        -----------------------
        climate           : description string sent to the model's prompt
        cooling_cop_hint  : starting COP value for model inference
        heating_cop_hint  : starting COP value for model inference
        min_cool_temp     : min outdoor cooling temp (°C)
        max_cool_temp     : max outdoor cooling temp (°C)
        min_heat_temp     : min outdoor heating temp (°C)
        max_heat_temp     : max outdoor heating temp (°C)
        heat_recovery     : 'Yes' | 'No' — HVACTemplate:System:VRF field A6
        supplemental_heating : '' | 'Electric' | 'Gas' | 'HotWater' — Zone field A14
        supplemental_capacity: '' | 'Autosize' — Zone field N20
        supplemental_max_temp: '' | numeric str — Zone field N21
        baseboard_type    : '' | 'Electric' | 'HotWater' — Zone field A17
        parasitic_on      : '' | W value str — Zone field N22
        parasitic_off     : '' | W value str — Zone field N23
        heating_setpoint  : °C str for HVACTemplate:Thermostat
        cooling_setpoint  : °C str for HVACTemplate:Thermostat
        """
        req = user_request.lower()

        # ── Defaults (generic / standard VRF request) ─────────────────────
        # NOTE: HVACTemplate:Zone:VRF in EnergyPlus 25.2 has 44 fields.
        # Supplemental heating coil fields do NOT exist in this object.
        # Baseboard heating type IS supported (fields 42–44).
        intent = {
            'climate'          : 'Continental (mixed climate)',
            'cooling_cop_hint' : '3.5',
            'heating_cop_hint' : '4.0',
            'min_cool_temp'    : '-6.0',
            'max_cool_temp'    : '43.0',
            'min_heat_temp'    : '-20.0',
            'max_heat_temp'    : '15.5',
            'heat_recovery'    : 'No',
            'baseboard_type'   : '',   # '' | 'Electric' | 'HotWater'  — Zone VRF F42
            'heating_setpoint' : '20.0',
            'cooling_setpoint' : '24.0',
        }

        # ── High-efficiency ────────────────────────────────────────────────
        if any(kw in req for kw in [
            'high efficiency', 'high-efficiency', 'energy saving',
            'energy efficient', 'energy-efficient', 'premium', 'efficient',
        ]):
            intent['climate']           = 'Continental — optimise for energy efficiency'
            intent['cooling_cop_hint']  = '4.2'
            intent['heating_cop_hint']  = '4.8'

        # ── Cold climate / enhanced heating ───────────────────────────────
        if any(kw in req for kw in [
            'cold climate', 'cold weather', 'low temperature',
            'winter performance', 'heating performance', 'enhanced heating',
            'extreme cold',
        ]):
            intent['climate']          = 'Cold climate — harsh winters, prioritise heating performance'
            intent['min_heat_temp']    = '-25.0'
            intent['max_heat_temp']    = '20.0'
            intent['heating_cop_hint'] = '4.5'
            # EnergyPlus 25.2 HVACTemplate:Zone:VRF has no supplemental heating
            # coil fields — use electric baseboard instead (F42) for backup heat.
            intent['baseboard_type']   = 'Electric'

        # ── Hot climate / cooling-dominated ───────────────────────────────
        if any(kw in req for kw in [
            'hot climate', 'tropical', 'desert',
            'cooling dominated', 'cooling-dominated', 'high cooling',
        ]):
            intent['climate']          = 'Hot climate — prioritise cooling efficiency'
            intent['max_cool_temp']    = '46.0'
            intent['min_cool_temp']    = '-5.0'
            intent['cooling_cop_hint'] = '4.0'
            intent['heating_setpoint'] = '18.0'
            intent['cooling_setpoint'] = '23.0'

        # ── Heat recovery ─────────────────────────────────────────────────
        # IMPORTANT: check for explicit negation FIRST.
        # "no heat recovery" contains the substring "heat recovery", so a naïve
        # `in` check would falsely enable heat recovery when the user said NOT to.
        # Negation patterns that must lock heat_recovery to 'No':
        _negated_heat_recovery = any(kw in req for kw in [
            'no heat recovery',
            'without heat recovery',
            'not heat recovery',
            'no waste heat',
            'without waste heat',
            'disable heat recovery',
            'skip heat recovery',
        ])
        # Only enable heat recovery when a POSITIVE keyword is found AND no
        # negation phrase was detected above.
        if not _negated_heat_recovery and any(kw in req for kw in [
            'heat recovery', 'simultaneous', 'waste heat',
        ]):
            intent['heat_recovery']    = 'Yes'
            intent['cooling_cop_hint'] = '4.0'
            intent['heating_cop_hint'] = '4.5'

        # ── Perimeter / baseboard heating ─────────────────────────────────
        if any(kw in req for kw in ['baseboard', 'perimeter heating', 'perimeter heat']):
            intent['baseboard_type'] = 'Electric'

        # ── Detailed energy accounting / monitoring ────────────────────────
        if any(kw in req for kw in [
            'detailed', 'energy accounting', 'monitoring',
            'energy tracking', 'energy model',
        ]):
            intent['parasitic_on']  = '25'
            intent['parasitic_off'] = '8'

        # ── Explicit comfort setpoints in the request ──────────────────────
        # e.g. "24°C cooling and 21°C heating", "cooling setpoint = 24°C"
        # Use found flags (not value comparison) so "cooling setpoint = 24°C"
        # is correctly recognised even though 24.0 is also the default value.
        parsed_heat, parsed_cool, h_found, c_found = self._parse_setpoints_from_request(user_request)
        if h_found:
            intent['heating_setpoint'] = parsed_heat
        if c_found:
            intent['cooling_setpoint'] = parsed_cool
        # Flag used by _generate_thermostat() to hard-enforce the value
        intent['setpoints_from_prompt'] = h_found or c_found

        return intent

    def _parse_setpoints_from_request(self, user_request: str) -> tuple:
        """
        Extract explicit heating and cooling thermostat setpoints from the
        user's natural-language request.

        Recognised patterns (case-insensitive):
          "21°C heating"             — temperature before keyword
          "heating setpoint at 21°C" — keyword before temperature with at/of
          "heating setpoint = 21°C"  — keyword before temperature with = sign

        Returns (heating_str, cooling_str, heating_found, cooling_found).
        Falls back to ('20.0', '24.0', False, False) when no explicit values found.
        Valid heating range: 15–25 °C.  Valid cooling range: 20–30 °C.
        """
        import re
        heating, cooling = '20.0', '24.0'
        h_found, c_found = False, False

        # Three alternatives:
        #   g1: "21°C heating"
        #   g2: "heating setpoint at/of 21°C"
        #   g3: "heating setpoint = 21°C"   ← new
        h_match = re.search(
            r'(\d+(?:\.\d+)?)\s*(?:°C|degC|deg\.?\s*C)\s+heating'
            r'|heating\s+(?:setpoint\s+)?(?:at\s+|of\s+)?(\d+(?:\.\d+)?)\s*(?:°C|degC|deg\.?\s*C)'
            r'|heating\s+setpoint\s*=\s*(\d+(?:\.\d+)?)\s*(?:°C|degC|deg\.?\s*C)',
            user_request, re.IGNORECASE
        )
        if h_match:
            raw = h_match.group(1) or h_match.group(2) or h_match.group(3)
            try:
                val = float(raw)
                if 15.0 <= val <= 25.0:
                    heating = f'{val:.1f}'
                    h_found = True
            except ValueError:
                pass

        # Three alternatives:
        #   g1: "24°C cooling"  — negative lookahead (?!\s+setpoint) prevents
        #       "21°C cooling setpoint = 24°C" from falsely matching 21 as cooling
        #   g2: "cooling setpoint at/of 24°C"
        #   g3: "cooling setpoint = 24°C"   ← new
        c_match = re.search(
            r'(\d+(?:\.\d+)?)\s*(?:°C|degC|deg\.?\s*C)\s+cooling(?!\s+setpoint)'
            r'|cooling\s+(?:setpoint\s+)?(?:at\s+|of\s+)?(\d+(?:\.\d+)?)\s*(?:°C|degC|deg\.?\s*C)'
            r'|cooling\s+setpoint\s*=\s*(\d+(?:\.\d+)?)\s*(?:°C|degC|deg\.?\s*C)',
            user_request, re.IGNORECASE
        )
        if c_match:
            raw = c_match.group(1) or c_match.group(2) or c_match.group(3)
            try:
                val = float(raw)
                if 20.0 <= val <= 30.0:
                    cooling = f'{val:.1f}'
                    c_found = True
            except ValueError:
                pass

        return heating, cooling, h_found, c_found

    # ─────────────────────────────────────────────────────────────────────────
    # MISTRAL GENERATION (iterative, prompt-aware)
    # ─────────────────────────────────────────────────────────────────────────

    def _generate_mistral(self, system_prompt, user_prompt, max_tokens):
        """
        Generate using Mistral fine-tuned model with iterative prompting.
        This follows the successful pattern from generate_complete_vrf.py test script.

        Now also extracts the user's design intent and passes it through every
        sub-call so that COP values, temperature limits, supplemental heating,
        baseboard type, and thermostat setpoints all respond to the user request.
        """
        try:
            import torch
            import re

            if self.mistral_model is None or self.mistral_tokenizer is None:
                print("⚠ Mistral model not initialized")
                return ""

            print("✓ Generating with Mistral fine-tuned model...")

            # Extract structural info from the combined prompt
            zones            = self._extract_zones_from_prompt(user_prompt)
            system_name      = self._extract_system_name_from_prompt(user_prompt)
            building_context = self._extract_building_context_from_prompt(user_prompt)

            # ── NEW: extract the user's design intent ─────────────────────
            # The combined prompt embeds the original user_request under a
            # "USER DESIGN REQUEST:" header; pull it back out so we can pass
            # it to every generation sub-function.
            user_request = self._extract_user_request_from_prompt(user_prompt)
            if user_request:
                print(f"   Design intent: {user_request[:120]}{'…' if len(user_request) > 120 else ''}")

            if not zones:
                print("⚠ No zones found in prompt, using direct generation")
                return self._generate_mistral_direct(system_prompt, user_prompt, max_tokens)

            print(f"   Found {len(zones)} zones: {', '.join(zones)}")
            print(f"   System name: {system_name}")

            # Use iterative generation approach (proven to work in testing)
            # user_request is now forwarded so every sub-call is prompt-aware.
            complete_config = self._generate_complete_vrf_iterative(
                zones,
                system_name,
                building_context,
                user_request,
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
    
    def _generate_complete_vrf_iterative(self, zones, system_name, building_context,
                                          user_request: str = ""):
        """
        Generate complete VRF system using iterative prompting.
        This is the proven approach from the testing script.

        user_request is now forwarded to every sub-generator so that design
        intent (efficiency, climate, setpoints, supplemental heating …)
        influences every object in the output.
        """
        try:
            import torch

            results = []

            # Step 1: Generate HVACTemplate:System:VRF
            # user_request tells the model what climate/efficiency profile to target.
            print(f"   🔧 Generating System VRF...")
            system_vrf = self._generate_system_vrf(building_context, system_name, zones,
                                                    user_request=user_request)
            if system_vrf:
                results.append(system_vrf)
                print(f"      ✅ System VRF generated ({len(system_vrf)} chars)")

            # Step 2: Generate HVACTemplate:Zone:VRF for each conditioned zone.
            # user_request drives advanced fields: supplemental heating, baseboard,
            # parasitic loads.
            print(f"   🏢 Generating Zone VRFs for {len(zones)} zones...")
            for i, zone_name in enumerate(zones, 1):
                print(f"      Zone {i}/{len(zones)}: {zone_name}...", end=" ")
                zone_vrf = self._generate_zone_vrf(zone_name, system_name,
                                                    user_request=user_request)
                if zone_vrf:
                    results.append(zone_vrf)
                    print(f"✅ ({len(zone_vrf)} chars)")
                else:
                    print(f"⚠ Failed")

            # Step 3: Generate HVACTemplate:Thermostat for each conditioned zone.
            # user_request is parsed for explicit setpoint values (e.g. "24°C cooling").
            print(f"   🌡️  Generating Thermostats for {len(zones)} zones...")
            for i, zone_name in enumerate(zones, 1):
                print(f"      Thermostat {i}/{len(zones)}: {zone_name}...", end=" ")
                thermostat = self._generate_thermostat(zone_name,
                                                        user_request=user_request)
                if thermostat:
                    results.append(thermostat)
                    print(f"✅ ({len(thermostat)} chars)")
                else:
                    print(f"⚠ Failed")

            # Combine all objects into one IDF text block.
            complete_config = "\n\n".join(results)

            print(f"   ✅ Complete VRF system generated ({len(complete_config)} chars)")

            return complete_config

        except Exception as e:
            print(f"⚠ Iterative generation failed: {e}")
            import traceback
            traceback.print_exc()
            return ""
    
    def _generate_system_vrf(self, building_context, system_name, zones=None,
                              user_request: str = ""):
        """
        HYBRID APPROACH for HVACTemplate:System:VRF generation:

        1. Parse user_request → design intent (climate, efficiency, heat-recovery …)
        2. Use fine-tuned model to pick DESIGN PARAMETERS guided by that intent.
           - The model's value is HVAC engineering knowledge; intent seeds the prompt.
        3. Use a fixed 37-field template for FIELD ORDER (EnergyPlus IDD compliance).

        Previously the model prompt hardcoded "Continental climate" regardless of
        what the user asked.  Now the intent description and seed hints are derived
        from the user's actual request so the model returns relevant parameters.
        """
        try:
            import torch
            import re

            # Get first zone name for master thermostat location
            master_zone = zones[0] if zones else "ZONE 1"
            num_zones   = len(zones) if zones else 1

            # ── STEP 1: Parse user intent → seed values for model prompt ──
            intent = self._parse_design_intent(user_request)

            # Determine heat-recovery phrasing for the prompt
            hr_note = (
                "The system MUST support simultaneous heating and cooling "
                "(Heat_Pump_Waste_Heat_Recovery = Yes)."
                if intent['heat_recovery'] == 'Yes'
                else "Standard VRF — no heat recovery required."
            )

            # ── STEP 2: Ask model for HVAC design parameters (not IDF syntax) ──
            # The model prompt now includes the user's actual climate/efficiency
            # intent so its parameter choices are request-specific.
            prompt = f"""<s>[INST] You are an HVAC engineer designing a VRF system.

User design request: {user_request if user_request else 'Standard VRF HVAC system'}

Building info:
- Number of zones: {num_zones}
- Zone names: {', '.join(zones) if zones else 'Single zone'}
- Climate context: {intent['climate']}
- Heat recovery: {hr_note}

Design guidance from the request:
- Suggested Cooling COP starting point: {intent['cooling_cop_hint']}
- Suggested Heating COP starting point: {intent['heating_cop_hint']}
- Suggested Min Cooling Temp: {intent['min_cool_temp']} °C
- Suggested Max Cooling Temp: {intent['max_cool_temp']} °C
- Suggested Min Heating Temp: {intent['min_heat_temp']} °C
- Suggested Max Heating Temp: {intent['max_heat_temp']} °C

Provide optimal VRF system parameters (adjust guidance values as your engineering judgment dictates):
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
                    max_new_tokens=200,   # Shorter — just need the 8 parameter values
                    temperature=0.3,
                    top_p=0.9,
                    do_sample=True,
                    pad_token_id=self.mistral_tokenizer.eos_token_id,
                )

            # Decode only the newly generated tokens (not the prompt itself)
            generated_tokens = outputs[0][len(inputs.input_ids[0]):]
            text = self.mistral_tokenizer.decode(generated_tokens, skip_special_tokens=True)

            # ── STEP 3: Parse the model's recommendations ─────────────────
            # _parse_design_parameters reads the structured "Key: value" output.
            # _validate_design_parameters then clamps values to realistic ranges.
            model_values = self._parse_design_parameters(text)

            # If the model missed a value, fall back to the intent-derived hint
            # so the template always has a meaningful (non-default) starting point.
            model_values.setdefault('cooling_cop',    intent['cooling_cop_hint'])
            model_values.setdefault('heating_cop',    intent['heating_cop_hint'])
            model_values.setdefault('min_cool_temp',  intent['min_cool_temp'])
            model_values.setdefault('max_cool_temp',  intent['max_cool_temp'])
            model_values.setdefault('min_heat_temp',  intent['min_heat_temp'])
            model_values.setdefault('max_heat_temp',  intent['max_heat_temp'])

            # Inject the heat-recovery flag from the parsed intent
            # (model prompt asked for it, template field A6 controls it)
            model_values['heat_recovery'] = intent['heat_recovery']

            if model_values:
                print(f"      Model values: " +
                      ", ".join(f"{k}={v}" for k, v in model_values.items()))

            # ── STEP 4: Build 37-field System:VRF (template + model values) ─
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
        
        # Temperature validation — enforce real manufacturer specs:
        #   N3 Min Cooling : -6.0 °C  (Daikin/Mitsubishi: −5 °C; EnergyPlus default: −6 °C)
        #   N4 Max Cooling : 43.0 °C  (standard spec; EnergyPlus default: 43 °C)
        #   N8 Min Heating : -20.0 °C (standard cold-climate VRF; EnergyPlus default: −20 °C)
        #   N9 Max Heating : 15.5 °C  (Daikin VRV IV / Mitsubishi CITY MULTI spec)
        if 'min_cool_temp' in values:
            try:
                temp = float(values['min_cool_temp'])
                if temp < -15 or temp > -5:
                    values['min_cool_temp'] = '-6.0'
            except ValueError:
                values['min_cool_temp'] = '-6.0'

        if 'max_cool_temp' in values:
            try:
                temp = float(values['max_cool_temp'])
                if temp < 35 or temp > 52:
                    values['max_cool_temp'] = '43.0'
            except ValueError:
                values['max_cool_temp'] = '43.0'

        if 'min_heat_temp' in values:
            try:
                temp = float(values['min_heat_temp'])
                if temp < -25 or temp > -15:
                    values['min_heat_temp'] = '-20.0'
            except ValueError:
                values['min_heat_temp'] = '-20.0'

        if 'max_heat_temp' in values:
            try:
                temp = float(values['max_heat_temp'])
                if temp < 12 or temp > 20:
                    values['max_heat_temp'] = '15.5'
            except ValueError:
                values['max_heat_temp'] = '15.5'
        
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
  {model_values.get('min_cool_temp', '-6.0')},                    !- Minimum Outdoor Temperature in Cooling Mode {{C}} (N3)
  {model_values.get('max_cool_temp', '43.0')},                     !- Maximum Outdoor Temperature in Cooling Mode {{C}} (N4)
  Autosize,                !- Gross Rated Heating Capacity {{W}} (N5)
  1.0,                     !- Rated Heating Capacity Sizing Ratio (N6)
  {model_values.get('heating_cop', '4.0')},                     !- Gross Rated Heating COP {{W/W}} (N7)
  {model_values.get('min_heat_temp', '-20.0')},                  !- Minimum Outdoor Temperature in Heating Mode {{C}} (N8)
  {model_values.get('max_heat_temp', '15.5')},                     !- Maximum Outdoor Temperature in Heating Mode {{C}} (N9)
  0.15,                    !- Minimum Heat Pump Part-Load Ratio (N10)
  {master_zone},           !- Zone Name for Master Thermostat Location (A3)
  {model_values.get('priority', 'LoadPriority')},            !- Master Thermostat Priority Control Type (A4)
  ,                        !- Thermostat Priority Schedule Name (A5)
  {model_values.get('heat_recovery', 'No')},                      !- Heat Pump Waste Heat Recovery (A6)
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
  -6.0,                    !- Minimum Outdoor Temperature in Cooling Mode {{C}} (N3)
  43.0,                    !- Maximum Outdoor Temperature in Cooling Mode {{C}} (N4)
  Autosize,                !- Gross Rated Heating Capacity {{W}} (N5)
  1.0,                     !- Rated Heating Capacity Sizing Ratio (N6)
  4.0,                     !- Gross Rated Heating COP {{W/W}} (N7)
  -20.0,                   !- Minimum Outdoor Temperature in Heating Mode {{C}} (N8)
  15.5,                    !- Maximum Outdoor Temperature in Heating Mode {{C}} (N9)
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
    
    def _generate_zone_vrf(self, zone_name, system_name, user_request: str = ""):
        """
        Generate HVACTemplate:Zone:VRF with all 42 required fields per IDD.

        The model fills in the core structure; user_request drives the advanced
        fields (supplemental heating type, baseboard, parasitic loads) via
        _parse_design_intent().  If the model output is missing required names,
        _get_fallback_zone_vrf() is called with the intent dict so even the
        fallback path is prompt-aware.
        """
        try:
            import torch

            # Parse design intent once so both the model prompt and fallback use it.
            intent = self._parse_design_intent(user_request)

            # Baseboard note for the model (only valid advanced field in EnergyPlus 25.2)
            base_note = (
                f"Baseboard heating type: {intent['baseboard_type']} (field 42)"
                if intent['baseboard_type']
                else "No baseboard heating (leave field 42 blank)"
            )

            prompt = f"""<s>[INST] Generate a complete HVACTemplate:Zone:VRF object (44 fields, EnergyPlus 25.2):
- Zone Name: {zone_name}
- Template VRF System Name: {system_name}
- Template Thermostat Name: Thermostat_{zone_name}
- Cooling and Heating Supply Air Flow Rate: Autosize
- User design request: {user_request if user_request else 'standard VRF'}
- {base_note}

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

            # Decode only newly generated tokens
            generated_tokens = outputs[0][len(inputs.input_ids[0]):]
            text  = self.mistral_tokenizer.decode(generated_tokens, skip_special_tokens=True)
            cleaned = self._clean_mistral_output(text)

            # Prepend the object type header if the model omitted it
            if not cleaned.startswith("HVACTemplate:Zone:VRF,"):
                cleaned = f"HVACTemplate:Zone:VRF,\n  {zone_name}," + cleaned

            # Validate minimum required references are present
            if zone_name not in cleaned or system_name not in cleaned:
                # Fallback uses intent so advanced fields are still prompt-driven
                cleaned = self._get_fallback_zone_vrf(zone_name, system_name, intent)

            return cleaned

        except Exception as e:
            print(f"⚠ Zone VRF generation failed: {e}")
            intent = self._parse_design_intent(user_request)
            return self._get_fallback_zone_vrf(zone_name, system_name, intent)

    def _get_fallback_zone_vrf(self, zone_name, system_name, intent: dict = None):
        """
        Fallback Zone:VRF template with exactly 44 fields per EnergyPlus 25.2 IDD.

        Field order confirmed from Energy+.idd (v25.2):
          F1–F32  : core zone/fan/coil fields (same as before)
          F33–F34 : parasitic electric energy use (on/off)
          F35     : dedicated outdoor air system name
          F36–F38 : zone cooling design supply air temperature (method, value, diff)
          F39–F41 : zone heating design supply air temperature (method, value, diff)
          F42     : baseboard heating type  ← driven by design intent
          F43     : baseboard heating availability schedule name
          F44     : baseboard heating capacity  ← Autosize when baseboard enabled

        NOTE: HVACTemplate:Zone:VRF in EnergyPlus 25.2 has NO supplemental heating
        coil fields — the Gemini prompt description of those fields was incorrect.
        Supplemental/backup heating for cold climates must be handled at the
        system level or via separate zone equipment objects outside HVACTemplate.

        When `intent` carries baseboard_type (set by _parse_design_intent for
        requests mentioning 'cold climate', 'baseboard', 'perimeter heating'),
        fields 42 and 44 are populated accordingly.
        """
        if intent is None:
            intent = {}

        # Only baseboard is relevant from intent for this object (fields 42–44)
        baseboard     = intent.get('baseboard_type', '')   # '' | 'Electric' | 'HotWater'
        baseboard_cap = 'Autosize' if baseboard else ''    # Autosize when type is set

        return f"""HVACTemplate:Zone:VRF,
  {zone_name},                          !- Zone Name (F1)
  {system_name},                        !- Template VRF System Name (F2)
  Thermostat_{zone_name},               !- Template Thermostat Name (F3)
  ,                                     !- Zone Heating Sizing Factor (F4)
  ,                                     !- Zone Cooling Sizing Factor (F5)
  1.0,                                  !- Rated Total Heating Capacity Sizing Ratio (F6)
  Autosize,                             !- Cooling Supply Air Flow Rate (F7)
  Autosize,                             !- No Cooling Supply Air Flow Rate (F8)
  Autosize,                             !- Heating Supply Air Flow Rate (F9)
  Autosize,                             !- No Heating Supply Air Flow Rate (F10)
  Autosize,                             !- Cooling Outdoor Air Flow Rate (F11)
  Autosize,                             !- Heating Outdoor Air Flow Rate (F12)
  Autosize,                             !- No Load Outdoor Air Flow Rate (F13)
  ,                                     !- Outdoor Air Method (F14)
  ,                                     !- Outdoor Air Flow Rate per Person (F15)
  ,                                     !- Outdoor Air Flow Rate per Zone Floor Area (F16)
  ,                                     !- Outdoor Air Flow Rate per Zone (F17)
  ,                                     !- Design Specification Outdoor Air Object Name (F18)
  ,                                     !- Design Specification Zone Air Distribution Object Name (F19)
  ,                                     !- System Availability Schedule Name (F20)
  ,                                     !- Supply Fan Operating Mode Schedule Name (F21)
  DrawThrough,                          !- Supply Air Fan Placement (F22)
  0.7,                                  !- Supply Fan Total Efficiency (F23)
  300,                                  !- Supply Fan Delta Pressure (F24)
  0.9,                                  !- Supply Fan Motor Efficiency (F25)
  VariableRefrigerantFlowDX,            !- Cooling Coil Type (F26)
  ,                                     !- Cooling Coil Availability Schedule Name (F27)
  Autosize,                             !- Cooling Coil Gross Rated Total Capacity (F28)
  Autosize,                             !- Cooling Coil Gross Rated Sensible Heat Ratio (F29)
  VariableRefrigerantFlowDX,            !- Heat Pump Heating Coil Type (F30)
  ,                                     !- Heat Pump Heating Coil Availability Schedule Name (F31)
  Autosize,                             !- Heat Pump Heating Coil Gross Rated Capacity (F32)
  30,                                   !- Zone Terminal Unit On Parasitic Electric Energy Use (F33)
  20,                                   !- Zone Terminal Unit Off Parasitic Electric Energy Use (F34)
  ,                                     !- Dedicated Outdoor Air System Name (F35)
  SupplyAirTemperature,                 !- Zone Cooling Design Supply Air Temperature Input Method (F36)
  12.8,                                 !- Zone Cooling Design Supply Air Temperature (F37)
  ,                                     !- Zone Cooling Design Supply Air Temperature Difference (F38)
  SupplyAirTemperature,                 !- Zone Heating Design Supply Air Temperature Input Method (F39)
  50,                                   !- Zone Heating Design Supply Air Temperature (F40)
  ,                                     !- Zone Heating Design Supply Air Temperature Difference (F41)
  {baseboard},                          !- Baseboard Heating Type (F42)
  ,                                     !- Baseboard Heating Availability Schedule Name (F43)
  {baseboard_cap};                      !- Baseboard Heating Capacity (F44)"""
    
    def _generate_thermostat(self, zone_name, user_request: str = ""):
        """
        Generate HVACTemplate:Thermostat using the fine-tuned model.

        Previously the heating setpoint was hardcoded to 20.0 °C and the model
        only generated the cooling setpoint (~24 °C by training default).  Now:
          1. _parse_setpoints_from_request() extracts any explicit setpoint values
             mentioned in the user request (e.g. "21°C heating / 24°C cooling").
          2. Those values are embedded in the one-shot example so the model sees
             the intended range and generates a consistent cooling setpoint.
          3. The explicitly parsed values are used in the final object regardless
             of what the model outputs, making setpoints fully prompt-driven.
        """
        try:
            import torch

            # ── Parse setpoints from user request (may override defaults) ──
            heating_sp, cooling_sp, h_found, c_found = self._parse_setpoints_from_request(user_request)
            # heating_sp is used directly (model does not generate this field).
            # cooling_sp: if the user explicitly wrote a value, enforce it;
            # otherwise let the model confirm/refine around the default.

            # One-shot example uses the same setpoints so the model stays in range.
            prompt = f"""<s>[INST] Generate HVACTemplate:Thermostat objects.

Example for Kitchen_Zone (heating {heating_sp}°C, cooling {cooling_sp}°C):
HVACTemplate:Thermostat,
  Thermostat_Kitchen_Zone,                !- Name
  ,                        !- Heating Setpoint Schedule Name
  {heating_sp},                    !- Constant Heating Setpoint {{C}}
  ,                        !- Cooling Setpoint Schedule Name
  {cooling_sp};                    !- Constant Cooling Setpoint {{C}}

Now generate for {zone_name}: [/INST]

HVACTemplate:Thermostat,
  Thermostat_{zone_name},                !- Name
  ,                        !- Heating Setpoint Schedule Name
  {heating_sp},                    !- Constant Heating Setpoint {{C}}
  ,                        !- Cooling Setpoint Schedule Name
  """

            inputs = self.mistral_tokenizer(prompt, return_tensors="pt").to(self.mistral_model.device)

            with torch.no_grad():
                outputs = self.mistral_model.generate(
                    **inputs,
                    max_new_tokens=30,   # Only need the cooling-setpoint value + semicolon
                    temperature=0.1,     # Very low → deterministic output near the example
                    top_p=0.9,
                    do_sample=True,
                    pad_token_id=self.mistral_tokenizer.eos_token_id,
                )

            # Decode only the newly generated tokens
            generated_tokens = outputs[0][len(inputs.input_ids[0]):]
            text = self.mistral_tokenizer.decode(generated_tokens, skip_special_tokens=True)

            # Extract the cooling-setpoint value the model produced
            continuation = text.strip()
            if ';' in continuation:
                continuation = continuation[:continuation.find(';') + 1]
            else:
                import re
                num_match = re.search(r'(\d+\.?\d*)', continuation)
                model_cool = num_match.group(1) if num_match else cooling_sp
                continuation = f'{model_cool};'

            # ── Validate the model's cooling setpoint value ────────────────
            # If the user explicitly wrote a setpoint in the prompt, enforce it
            # directly — the model output is irrelevant.  Otherwise accept the
            # model value if it falls within the realistic range (20–30 °C).
            import re as _re
            if c_found:
                continuation = f'{cooling_sp};'
            else:
                cool_match = _re.search(r'(-?\d+\.?\d*)', continuation)
                if cool_match:
                    try:
                        cool_val = float(cool_match.group(1))
                        if not (20.0 <= cool_val <= 30.0):
                            continuation = f'{cooling_sp};'
                    except ValueError:
                        continuation = f'{cooling_sp};'
                else:
                    continuation = f'{cooling_sp};'

            # ── Build the complete thermostat object ───────────────────────
            complete_thermostat = (
                f"HVACTemplate:Thermostat,\n"
                f"  Thermostat_{zone_name},                !- Name\n"
                f"  ,                        !- Heating Setpoint Schedule Name\n"
                f"  {heating_sp},                    !- Constant Heating Setpoint {{C}}\n"
                f"  ,                        !- Cooling Setpoint Schedule Name\n"
                f"  {continuation}                    !- Constant Cooling Setpoint {{C}}"
            )

            return complete_thermostat

        except Exception as e:
            print(f"⚠ Thermostat generation failed: {e}")
            # Hard fallback — still uses parsed setpoints, not hardcoded 20/24
            heating_sp, cooling_sp, _, _ = self._parse_setpoints_from_request(user_request)
            return (
                f"HVACTemplate:Thermostat,\n"
                f"  Thermostat_{zone_name},                !- Name\n"
                f"  ,                        !- Heating Setpoint Schedule Name\n"
                f"  {heating_sp},                    !- Constant Heating Setpoint {{C}}\n"
                f"  ,                        !- Cooling Setpoint Schedule Name\n"
                f"  {cooling_sp};                    !- Constant Cooling Setpoint {{C}}"
            )
    
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

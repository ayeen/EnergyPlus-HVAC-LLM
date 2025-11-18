"""
Universal LLM Interface
"""

import os
import json
from config import Config
from google.generativeai.types import HarmCategory, HarmBlockThreshold
class UniversalLLM:
    """Universal interface for LLM providers"""
    
    def __init__(self, provider=None):
        self.provider = provider or Config.LLM_PROVIDER
        self.client = None
        
        if self.provider == "auto":
            self.provider = self._detect_provider()
        
        self._initialize()
    
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
    
    
    def generate(self, system_prompt, user_prompt):
        """Generate response with automatic provider fallback"""
        max_tokens = Config.LLM_MAX_TOKENS
       
        # Try primary provider first
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

        """Sanitize prompts to avoid content filtering."""
        # Replace potentially triggering terms
        replacements = {
            "EnergyPlus": "building simulation software",
            "error": "issue",
            "fix": "improve",
            "problem": "challenge",
            "failure": "unsuccessful result",
            "danger": "concern",
            "kill": "stop",
            "attack": "approach",
            "weapon": "tool",
            "explosive": "rapid",
            "bomb": "device"
        }
        
        sanitized = prompt
        for old, new in replacements.items():
            sanitized = sanitized.replace(old, new)
            sanitized = sanitized.replace(old.upper(), new.upper())
            sanitized = sanitized.replace(old.lower(), new.lower())
        
        return sanitized
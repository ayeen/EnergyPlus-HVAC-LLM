"""
LLM Agent 3: Error Corrector with RAG Integration

This agent uses:
- Gemini (pre-trained) when LLM_PROVIDER="gemini"
- Fine-tuned Mistral model (agent3-balanced) when LLM_PROVIDER="mistral"
"""

from src.agents.llm_interface import UniversalLLM
from src.core.idf_handler import IDFHandler
from src.rag.rag_retriever import RAGRetriever
from config.settings import Config
import json
import re


class Agent3MistralModel:
    """Dedicated Mistral model for Agent 3 error correction (separate from Agent 1)"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Agent3MistralModel, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if Agent3MistralModel._initialized:
            return
            
        self.model = None
        self.tokenizer = None
        self._load_model()
        Agent3MistralModel._initialized = True
    
    def _load_model(self):
        """Load the Agent 3 specific fine-tuned Mistral model"""
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
            from peft import PeftModel
            
            print("\n" + "="*60)
            print("Loading Agent 3 Fine-tuned Mistral Model")
            print("="*60)
            print(f"   Base model: {Config.MISTRAL_BASE_MODEL}")
            print(f"   Agent 3 path: {Config.MISTRAL_AGENT3_PATH}")
            
            # Configure 4-bit quantization
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
            
            # Load Agent 3 LoRA weights
            self.model = PeftModel.from_pretrained(base_model, Config.MISTRAL_AGENT3_PATH)
            
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(Config.MISTRAL_AGENT3_PATH)
            self.tokenizer.pad_token = self.tokenizer.eos_token
            self.tokenizer.padding_side = "right"
            
            print("✓ Agent 3 Mistral model loaded successfully")
            print(f"   Device: {next(self.model.parameters()).device}")
            if torch.cuda.is_available():
                print(f"   GPU: {torch.cuda.get_device_name(0)}")
            print("="*60 + "\n")
            
        except Exception as e:
            print(f"⚠ Agent 3 Mistral model loading failed: {e}")
            import traceback
            traceback.print_exc()
            self.model = None
            self.tokenizer = None
    
    def generate(self, system_prompt, user_prompt, max_tokens=1024):
        """Generate error correction response"""
        if self.model is None or self.tokenizer is None:
            print("⚠ Agent 3 Mistral model not available")
            return ""
        
        try:
            import torch
            
            # Format prompt in Mistral instruction format
            prompt = f"<s>[INST] {system_prompt}\n\n{user_prompt} [/INST]\n\n"
            
            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
            
            print(f"   Generating error correction (max {max_tokens} tokens)...")
            
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    temperature=0.3,
                    top_p=0.9,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id,
                    repetition_penalty=1.2,
                    no_repeat_ngram_size=3,
                )
            
            # Decode only the new tokens
            generated_tokens = outputs[0][len(inputs.input_ids[0]):]
            text = self.tokenizer.decode(generated_tokens, skip_special_tokens=True)
            
            return text.strip()
            
        except Exception as e:
            print(f"⚠ Agent 3 Mistral generation failed: {e}")
            import traceback
            traceback.print_exc()
            return ""


class ErrorCorrector:
    """Fix EnergyPlus errors using LLM with RAG-enhanced context"""
    
    def __init__(self, use_rag: bool = True, llm_provider: str = None):
        """
        Initialize Error Corrector.
        
        Args:
            use_rag: Whether to enable RAG (Retrieval-Augmented Generation).
                    Set to False for Scenario 1 comparison (LLM only).
                    Default: True (Scenario 2)
            llm_provider: LLM provider to use (e.g., "gemini", "mistral", None for default)
        """
        # Determine provider
        self.llm_provider = llm_provider or Config.LLM_PROVIDER
        
        # Choose model based on provider:
        # - gemini: Use Gemini pre-trained model (via UniversalLLM)
        # - mistral: Use Agent 3 fine-tuned model (dedicated for error correction)
        if self.llm_provider == "mistral":
            print("\n🔧 Agent 3 using fine-tuned Mistral model for error correction")
            self.agent3_mistral = Agent3MistralModel()
            self.llm = None  # Don't use UniversalLLM for Mistral
        else:
            print("\n🔧 Agent 3 using Gemini pre-trained model")
            self.llm = UniversalLLM(provider=self.llm_provider)
            self.agent3_mistral = None
        
        self.handler = IDFHandler()
        self.use_rag = use_rag
        
        # Initialize RAG retriever for error patterns and fix procedures
        if use_rag:
            try:
                self.rag = RAGRetriever()
                self.rag_enabled = True
                print("✓ RAG enabled for Agent 3 (Error Corrector)")
            except Exception as e:
                print(f"⚠ RAG unavailable for Agent 3: {e}")
                self.rag_enabled = False
        else:
            self.rag = None
            self.rag_enabled = False
            print("ℹ RAG disabled for Agent 3 (Scenario 1: LLM Only)")
    
    def analyze_and_fix(self, idf_path, errors):
        """Analyze errors and suggest fixes with RAG-enhanced context"""
        
        # Try to load IDF, but handle cases where it's malformed
        try:
            idf = self.handler.load(idf_path)
            summary = self.handler.get_summary(idf)
        except Exception as e:
            print(f"⚠ Warning: Could not parse IDF with eppy ({e}). Using basic text analysis.")
            summary = {'zones': ['Unknown'], 'vrf_systems': ['Unknown'], 'thermostats': ['Unknown']}
        
        # Provide more errors for better context
        error_text = "\n".join(errors[:40])
        
        # RAG ENHANCEMENT: Query error fix procedures and field dependencies
        rag_context = ""
        cached_fixes = []
        
        if self.rag_enabled:
            print("\n🔍 Querying RAG knowledge base for error patterns...")
            
            # Query error fix procedures for similar errors
            fix_procedures = self.rag.query_error_patterns(
                error_description=error_text[:500],  # Use first part of errors
                n_results=3
            )
            
            if fix_procedures:
                print(f"  ✓ Found {len(fix_procedures)} similar error patterns")
                
                # Check for high-similarity cached fixes (>77% threshold)
                for proc in fix_procedures:
                    similarity = proc.get('similarity', 0)
                    if similarity > 0.77:
                        print(f"    🎯 High-similarity match ({similarity:.1%}): {proc.get('error_id', 'unknown')}")
                        cached_fixes.append(proc)
                
                # Format fix procedures for LLM context
                rag_context += "\n\n**KNOWN ERROR PATTERNS & PROVEN FIXES:**\n"
                for i, proc in enumerate(fix_procedures, 1):
                    rag_context += f"\n{i}. Error: {proc.get('error_pattern', 'N/A')[:100]}\n"
                    rag_context += f"   Severity: {proc.get('severity', 'Unknown')}\n"
                    rag_context += f"   Similarity: {proc.get('similarity', 0):.1%}\n"
                    if 'content' in proc:
                        # Extract fix strategy from content
                        content = proc['content']
                        if 'Fix Procedures:' in content:
                            fix_section = content.split('Fix Procedures:')[1].split('\n\n')[0]
                            rag_context += f"   Fix Strategy: {fix_section[:300]}...\n"
            
            # Query field dependencies for validation
            dependencies = self.rag.query_field_dependencies(
                query="field requirements validation rules errors",
                n_results=5
            )
            
            if dependencies:
                print(f"  ✓ Found {len(dependencies)} relevant field dependency rules")
                rag_context += "\n\n**FIELD DEPENDENCY RULES:**\n"
                for i, dep in enumerate(dependencies, 1):
                    rag_context += f"\n{i}. {dep.get('dependency_id', 'N/A')}\n"
                    rag_context += f"   Trigger: {dep.get('trigger_field', 'N/A')}\n"
                    rag_context += f"   Severity: {dep.get('severity', 'Unknown')}\n"
                    if 'content' in dep:
                        # Extract key requirements
                        content = dep['content']
                        if 'Required Fields:' in content:
                            req_section = content.split('Required Fields:')[1].split('\n\n')[0]
                            rag_context += f"   {req_section[:200]}...\n"
            
            print("  ✓ RAG context prepared\n")
        
        # If we have high-similarity cached fixes, try to apply them directly
        if cached_fixes and len(cached_fixes) >= 1:
            print(f"\n⚡ Applying cached fixes from high-similarity matches...")
            try:
                fixes = self._extract_fixes_from_cached_procedures(cached_fixes, summary)
                if fixes:
                    print(f"  ✓ Generated {len(fixes)} fixes from cached procedures")
                    return fixes
            except Exception as e:
                print(f"  ⚠ Could not apply cached fixes: {e}")
                print(f"  → Falling back to LLM generation")
        
        # Build enhanced system prompt with RAG context
        system_prompt = self._build_system_prompt(rag_context)
        
        # Build user prompt
        user_prompt = f"""Analyze these EnergyPlus errors and generate corrections in JSON format.

**IDF Structure:**
- Zones: {summary['zones']}
- VRF Systems: {summary['vrf_systems']}
- Thermostats: {summary['thermostats']}

**EnergyPlus Errors:**
```
{error_text}
```

{rag_context}

**Analysis Guidelines:**
1. For "Value type 'string' for input 'X' not permitted" errors:
   - The string value 'X' is in a numeric field
   - Find the correct field that accepts 'X' as a string
   - Set the numeric field to an appropriate number (or "Autosize")

2. For "Failed to match against any enum values" errors:
   - The value is in the wrong enum field
   - Find the correct enum field for that value
   - Set the incorrect field to a valid enum value

3. Use the KNOWN ERROR PATTERNS above to guide your fixes - these are proven solutions

4. Validate your fixes against the FIELD DEPENDENCY RULES to ensure no new violations

**Required Output Format:**
```json
[
  {{
    "object_type": "HVACTemplate:System:VRF",
    "object_name": "VRF_System_1",
    "field_to_change": "condenser_type",
    "new_value": "AirCooled"
  }}
]
```

Generate the complete JSON array of ALL necessary fixes now:"""
        
        # Generate response using the appropriate model
        if self.agent3_mistral is not None:
            # Use Agent 3 fine-tuned Mistral model
            response = self.agent3_mistral.generate(system_prompt, user_prompt)
        else:
            # Use Gemini pre-trained model
            response = self.llm.generate(system_prompt, user_prompt)
        
        print("\n" + "="*80)
        print("LLM RESPONSE FOR ERROR CORRECTION:")
        print("="*80)
        print(response[:1000] + ("..." if len(response) > 1000 else ""))
        print("="*80 + "\n")
        
        # Extract JSON from response, handling markdown
        json_match = re.search(r'```(?:json)?\s*(\[[\s\S]*?\])\s*```', response)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find JSON array without markdown
            json_match = re.search(r'\[\s*\{[\s\S]*?\}\s*\]', response)
            if json_match:
                json_str = json_match.group(0)
            else:
                # Last resort: find between first [ and last ]
                if '[' in response and ']' in response:
                    start = response.find('[')
                    end = response.rfind(']')
                    json_str = response[start:end+1]
                else:
                    json_str = "[]"

        try:
            fixes = json.loads(json_str)
            print(f"\n✓ Successfully parsed {len(fixes)} fixes from LLM response\n")
            return fixes
        except json.JSONDecodeError as e:
            print(f"❌ Failed to decode JSON from LLM response: {e}")
            print(f"Attempted to parse: {json_str[:500]}")
            return []
    
    def _build_system_prompt(self, rag_context=""):
        """Build system prompt with optional RAG context"""
        base_prompt = """You are an expert EnergyPlus IDF debugger specializing in HVACTemplate objects. 
Your task is to analyze EnergyPlus validation errors and generate precise field corrections in JSON format.

CRITICAL UNDERSTANDING:
- Errors like "Value type 'string' for input 'X' not permitted by 'type' constraint" mean field X is in the WRONG field position
- The value 'X' belongs in a different field that accepts strings
- You must identify WHERE the value should go and WHAT should be in the current field
- If you see "Zone Name for Master Thermostat Location must be entered when Master Thermostat Priority Control Type = MASTERTHERMOSTATPRIORITY", set zone_name_for_master_thermostat_location to the first zone name in the zones list

HVACTemplate:System:VRF FIELD ORDER (first 46 fields):
1. name (string)
2. system_availability_schedule_name (string, optional)
3. gross_rated_total_cooling_capacity (number or "Autosize")
4. gross_rated_cooling_cop (number)
5. minimum_outdoor_temperature_in_cooling_mode (number)
6. maximum_outdoor_temperature_in_cooling_mode (number)
7. gross_rated_heating_capacity (number or "Autosize")
8. rated_heating_capacity_sizing_ratio (number)
9. gross_rated_heating_cop (number)
10. minimum_outdoor_temperature_in_heating_mode (number)
11. maximum_outdoor_temperature_in_heating_mode (number)
12. minimum_heat_pump_part_load_ratio (number)
13. zone_name_for_master_thermostat_location (string)
14. master_thermostat_priority_control_type (enum: "LoadPriority", "ZonePriority", "ThermostatOffsetPriority", "Scheduled", "MasterThermostatPriority")
15. thermostat_priority_schedule_name (string, optional)
16. zone_terminal_unit_list_name (string, optional)
17. heat_pump_waste_heat_recovery (enum: "No", "Yes")
18-46. [Additional fields - defrost, condenser, basin heater, fuel type, etc.]

HVACTemplate:Zone:VRF FIELD ORDER (first 31 fields):
1. zone_name (string)
2. template_vrf_system_name (string)
3. template_thermostat_name (string, optional)
4-31. [Flow rates, fan settings, coil types, sizing factors, outdoor air method, etc.]

Output ONLY a valid JSON array of fix objects."""
        
        if rag_context:
            return base_prompt + "\n\n" + rag_context
        return base_prompt
    
    def _extract_fixes_from_cached_procedures(self, cached_procedures, summary):
        """Extract fixes from high-similarity cached error procedures"""
        fixes = []
        
        for proc in cached_procedures:
            error_id = proc.get('error_id', '')
            content = proc.get('content', '')
            
            # Master thermostat error - most common
            if 'master_thermostat' in error_id.lower():
                # Check if we have zones
                if summary.get('zones') and summary['zones'][0] != 'Unknown':
                    first_zone = summary['zones'][0]
                    
                    # Apply recommended fix: change to LoadPriority
                    fixes.append({
                        "object_type": "HVACTemplate:System:VRF",
                        "object_name": "N/A",  # Apply to all
                        "field_to_change": "master_thermostat_priority_control_type",
                        "new_value": "LoadPriority"
                    })
                    
                    # Optionally set the zone name (in case user wants MasterThermostatPriority)
                    fixes.append({
                        "object_type": "HVACTemplate:System:VRF",
                        "object_name": "N/A",
                        "field_to_change": "zone_name_for_master_thermostat_location",
                        "new_value": first_zone
                    })
            
            # Defrost strategy error
            elif 'resistive_defrost' in error_id.lower():
                fixes.append({
                    "object_type": "HVACTemplate:System:VRF",
                    "object_name": "N/A",
                    "field_to_change": "resistive_defrost_heater_capacity",
                    "new_value": "Autosize"
                })
            
            # Temperature range errors
            elif 'cooling_temperature_range' in error_id.lower():
                fixes.extend([
                    {
                        "object_type": "HVACTemplate:System:VRF",
                        "object_name": "N/A",
                        "field_to_change": "minimum_outdoor_temperature_in_cooling_mode",
                        "new_value": "-10"
                    },
                    {
                        "object_type": "HVACTemplate:System:VRF",
                        "object_name": "N/A",
                        "field_to_change": "maximum_outdoor_temperature_in_cooling_mode",
                        "new_value": "48"
                    }
                ])
            
            elif 'heating_temperature_range' in error_id.lower():
                fixes.extend([
                    {
                        "object_type": "HVACTemplate:System:VRF",
                        "object_name": "N/A",
                        "field_to_change": "minimum_outdoor_temperature_in_heating_mode",
                        "new_value": "-25"
                    },
                    {
                        "object_type": "HVACTemplate:System:VRF",
                        "object_name": "N/A",
                        "field_to_change": "maximum_outdoor_temperature_in_heating_mode",
                        "new_value": "18"
                    }
                ])
            
            # Invalid condenser type error
            elif 'invalid_condenser_type' in error_id.lower() or 'condenser_type' in error_id.lower():
                # Fix in both HVACTemplate and expanded form
                fixes.append({
                    "object_type": "HVACTemplate:System:VRF",
                    "object_name": "N/A",
                    "field_to_change": "condenser_type",
                    "new_value": "AirCooled"
                })
            
            # Invalid COP type error (string in numeric field)
            elif 'invalid_cop_type' in error_id.lower() or 'cop' in error_id.lower():
                # Fix in both HVACTemplate and expanded form
                fixes.extend([
                    {
                        "object_type": "HVACTemplate:System:VRF",
                        "object_name": "N/A",
                        "field_to_change": "gross_rated_heating_cop",
                        "new_value": "3.5"
                    },
                    {
                        "object_type": "HVACTemplate:System:VRF",
                        "object_name": "N/A",
                        "field_to_change": "gross_rated_cooling_cop",
                        "new_value": "4.0"
                    }
                ])
        
        return fixes if fixes else None
        

    def apply_fixes(self, idf_path, fixes, output_path):
        """Apply fixes to IDF"""
        
        idf = self.handler.load(idf_path)
        applied = 0
        failed = 0
        
        print(f"\n{'='*80}")
        print(f"APPLYING {len(fixes)} FIXES TO IDF")
        print(f"{'='*80}\n")
        
        for i, fix in enumerate(fixes, 1):
            obj_type = fix['object_type']
            obj_name = fix.get('object_name', 'N/A')
            field = fix['field_to_change']
            new_value = fix['new_value']
            
            print(f"{i}. {obj_type}[{obj_name}].{field} = '{new_value}'")
            
            objects = idf.idfobjects.get(obj_type, [])
            
            if not objects:
                print(f"   ❌ No objects of type '{obj_type}' found in IDF")
                failed += 1
                continue
            
            fix_applied = False
            for obj in objects:
                matched = False
                
                # Try multiple matching strategies
                if obj_name == 'N/A' or not obj_name:
                    # No name specified, apply to first object
                    matched = True
                elif hasattr(obj, 'Name') and obj.Name == obj_name:
                    matched = True
                elif hasattr(obj, 'Zone_Name') and obj.Zone_Name == obj_name:
                    matched = True
                elif hasattr(obj, 'Template_VRF_System_Name') and obj.Template_VRF_System_Name == obj_name:
                    matched = True
                
                if matched:
                    try:
                        # Convert field name to eppy format
                        # Try direct name first (in case it's already correct)
                        if hasattr(obj, field):
                            eppy_field = field
                        else:
                            # Convert snake_case to Title_Case with special handling
                            # Preserve lowercase articles like "for", "in", "of", "to", "per", "used"
                            # Keep acronyms in uppercase: COP, VRF, HVAC, etc.
                            lowercase_words = {'for', 'in', 'of', 'to', 'per', 'used', 'or', 'and', 'the'}
                            uppercase_acronyms = {'cop', 'vrf', 'hvac', 'idf', 'db', 'wb', 'hr', 'dx'}
                            parts = field.split('_')
                            eppy_parts = []
                            for i, part in enumerate(parts):
                                if part.lower() in uppercase_acronyms:
                                    eppy_parts.append(part.upper())
                                elif i > 0 and part.lower() in lowercase_words:
                                    eppy_parts.append(part.lower())
                                else:
                                    eppy_parts.append(part.capitalize())
                            eppy_field = '_'.join(eppy_parts)
                        
                        # Get old value for logging
                        old_value = getattr(obj, eppy_field, '<not set>')
                        
                        # Convert numeric strings to appropriate types
                        if isinstance(new_value, str) and new_value.replace('.', '').replace('-', '').isdigit():
                            if '.' in new_value:
                                new_value = float(new_value)
                            else:
                                new_value = int(new_value)
                        
                        setattr(obj, eppy_field, new_value)
                        print(f"   ✓ Changed from '{old_value}' to '{new_value}'")
                        applied += 1
                        fix_applied = True
                        break
                    except Exception as e:
                        print(f"   ❌ Error applying fix: {e}")
                        failed += 1
                        break
            
            if not fix_applied and not failed:
                print(f"   ⚠ No matching object found for '{obj_name}'")
                failed += 1
        
        print(f"\n{'='*80}")
        print(f"FIXES APPLIED: {applied} successful, {failed} failed")
        print(f"{'='*80}\n")
        
        idf.saveas(output_path)
        return applied

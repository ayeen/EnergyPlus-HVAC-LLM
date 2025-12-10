"""
LLM Agent 1: HVAC Generator with RAG Integration
"""

from src.agents.llm_interface import UniversalLLM
from src.core.idf_handler import IDFHandler
from src.rag.rag_retriever import RAGRetriever
import re
import json
import os

class HVACGenerator:
    """Generate HVAC systems using LLM with RAG-enhanced context"""
    
    def __init__(self):
        self.llm = UniversalLLM()
        self.handler = IDFHandler()
        # Initialize RAG retriever for field specs and user patterns
        try:
            self.rag = RAGRetriever()
            self.rag_enabled = True
            print("✓ RAG enabled for Agent 1 (HVAC Generator)")
        except Exception as e:
            print(f"⚠ RAG unavailable for Agent 1: {e}")
            self.rag_enabled = False
    
    def generate_vrf_system(self, zones, system_name="VRF_System_1", user_request=None, building_context=None):
        """
        Generate VRF system for zones with RAG-enhanced and building context.
        
        Args:
            zones: List of zone names
            system_name: Name for the VRF system (default: "VRF_System_1")
            user_request: Optional natural language design request from user
                         (e.g., "Design a VRF system with heat recovery")
            building_context: Optional dict with building metadata (area, orientation, loads, etc.)
        """
        
        zone_list = ", ".join(zones)
        
        # RAG ENHANCEMENT: Query knowledge base for relevant context
        rag_context = {}
        if self.rag_enabled and user_request:
            print("\n🔍 Querying RAG knowledge base for design patterns...")
            
            # Query user request examples for intent matching
            similar_requests = self.rag.query_user_requests(
                user_request=user_request,
                n_results=3
            )
            
            if similar_requests:
                print(f"  ✓ Found {len(similar_requests)} similar design patterns")
                rag_context['user_examples'] = similar_requests
                
                for i, req in enumerate(similar_requests, 1):
                    similarity = req.get('similarity', 0)
                    print(f"    {i}. {req.get('description', 'N/A')[:60]}... ({similarity:.1%})")
            
            # Query field dependencies for validation
            dependencies = self.rag.query_field_dependencies(
                query=f"{user_request} field requirements",
                n_results=5
            )
            
            if dependencies:
                print(f"  ✓ Found {len(dependencies)} relevant field dependency rules")
                rag_context['dependencies'] = dependencies
            
            # Query field specifications for critical fields
            field_specs = self.rag.query_field_specs(
                query_text="VRF system master thermostat defrost condenser capacity COP",
                n_results=10
            )
            
            if field_specs:
                print(f"  ✓ Found {len(field_specs)} field specifications")
                rag_context['field_specs'] = field_specs
            
            print("  ✓ RAG context prepared\n")
        
        # Load prompt templates and merge with user request and building context
        [system_prompt, user_prompt] = self._create_energyplus_template_prompt(
            zone_list, 
            system_name, 
            user_request,
            rag_context,
            building_context
        )
        
        # print(f"Called LLM to generate VRF system for zones: {zone_list}")
        if user_request:
            # print(f"User Design Request: {user_request}")
            response = self.llm.generate(system_prompt, user_prompt)
        # Clean response: remove markdown and non-IDF lines
        hvac_response_clean = "\n".join(
            line for line in response.splitlines()
            if not line.strip().startswith("```")
        )
        
        # Add HVAC section header for clear identification
        if hvac_response_clean:
            hvac_with_header = self._add_section_header(hvac_response_clean, "VRF HVAC SYSTEM")
            print(f"✓ Successfully generated VRF system with HVAC content")
            return hvac_with_header
        else:
            print(f"✗ Prompt got empty response")
            return ""
    
    def _create_energyplus_template_prompt(self, zone_list, system_name, user_request=None, rag_context=None, building_context=None):
        """
        EnergyPlus HVACTemplate-focused approach with RAG and building context enhancement.
        Merges user's natural language request with technical template, RAG context, and building metadata.
        
        Args:
            zone_list: Comma-separated zone names
            system_name: HVAC system name
            user_request: Optional natural language design request
            rag_context: Optional RAG-retrieved context (user examples, dependencies, field specs)
            building_context: Optional building metadata (area, orientation, loads, etc.)
        
        Returns:
            tuple: (system_prompt, user_prompt)
        """

        prompt_path = os.path.join(os.path.dirname(__file__), "energyplus_vrf_prompt.json")
        with open(prompt_path, "r", encoding="utf-8") as f:
            prompt_data = json.load(f)
        
        system_prompt = prompt_data[0]["system_prompt"]
        
        # Add RAG-enhanced validation rules to system prompt
        if rag_context and rag_context.get('dependencies'):
            system_prompt += "\n\n**CRITICAL FIELD DEPENDENCY RULES (from knowledge base):**\n"
            for dep in rag_context['dependencies'][:3]:  # Top 3 most relevant
                system_prompt += f"\n- {dep.get('dependency_id', 'N/A')}:\n"
                system_prompt += f"  Trigger: {dep.get('trigger_field', 'N/A')}\n"
                system_prompt += f"  Severity: {dep.get('severity', 'Unknown')}\n"
                if 'content' in dep:
                    content = dep['content']
                    if 'Fix Strategy:' in content:
                        fix_strategy = content.split('Fix Strategy:')[1].split('\n')[0]
                        system_prompt += f"  Fix Strategy: {fix_strategy}\n"
        
        # Add building context to system prompt for sizing guidance
        if building_context:
            system_prompt += "\n\n**BUILDING CONTEXT (for sizing and configuration):**\n"
            system_prompt += f"- Number of Zones: {building_context['num_zones']}\n"
            system_prompt += f"- Zone Names: {', '.join(building_context['zone_names'])}\n"
            if building_context['total_area'] > 0:
                system_prompt += f"- Total Floor Area: {building_context['total_area']:.1f} m²\n"
                system_prompt += f"  💡 Use this for capacity estimation (typical: 100-150 W/m² cooling load)\n"
            if building_context['total_volume'] > 0:
                system_prompt += f"- Total Volume: {building_context['total_volume']:.1f} m³\n"
            system_prompt += f"- Building Orientation: {building_context['orientation']}°\n"
            if building_context['orientation'] != 0:
                system_prompt += f"  💡 Non-zero orientation affects solar heat gain\n"
            system_prompt += f"- Internal Loads Present: {'✓ Yes' if building_context['has_internal_loads'] else '✗ No'}\n"
            if building_context['has_internal_loads']:
                loads = []
                if building_context['has_people']: loads.append("People")
                if building_context['has_lights']: loads.append("Lights")  
                if building_context['has_equipment']: loads.append("Equipment")
                system_prompt += f"  ({', '.join(loads)})\n"
            else:
                system_prompt += "  ⚠️ No internal loads may result in undersized HVAC\n"
            system_prompt += f"- Location: {building_context['weather_file']}\n"
        
        # Fill technical template with actual values
        technical_template = prompt_data[0]["user_prompt"].format(
            zone_list=zone_list, 
            system_name=system_name
        )
        
        # Build enhanced user prompt with RAG context
        combined_prompt = ""
        
        if user_request:
            combined_prompt += f"""USER DESIGN REQUEST:
{user_request}

"""
            
            # Add similar design examples from RAG
            if rag_context and rag_context.get('user_examples'):
                combined_prompt += "**SIMILAR DESIGN PATTERNS (from knowledge base):**\n"
                for i, ex in enumerate(rag_context['user_examples'][:2], 1):  # Top 2
                    combined_prompt += f"\n{i}. {ex.get('description', 'N/A')}\n"
                    if 'content' in ex:
                        content = ex['content']
                        # Extract technical specs if available
                        if 'technical_specs' in content or 'keywords' in content:
                            combined_prompt += f"   Key features: {content[:150]}...\n"
                combined_prompt += "\n"
            
            combined_prompt += f"""TECHNICAL IMPLEMENTATION REQUIREMENTS:
{technical_template}

Please generate the EnergyPlus IDF objects that fulfill the user's design request while strictly following the technical specifications above. The user's design intent should guide features like heat recovery, economizer settings, and system configuration, but the output format must exactly match the technical requirements.

**IMPORTANT VALIDATION:**
1. Master Thermostat: If using 'MasterThermostatPriority', MUST set zone_name_for_master_thermostat_location
2. Defrost Strategy: If using 'Resistive', MUST set resistive_defrost_heater_capacity to 'Autosize' or positive value
3. Temperature Ranges: Use wide ranges (cooling: -10 to 48°C, heating: -25 to 18°C) for reliability
4. COP Values: Must be > 0 even when capacity is 'Autosize' (typical: 3.5-4.5)"""
        else:
            # No user request - use template directly with validation notes
            combined_prompt = technical_template + """

**IMPORTANT VALIDATION:**
1. Master Thermostat: Recommend 'LoadPriority' over 'MasterThermostatPriority' (simpler, no zone name required)
2. Defrost Strategy: Use 'ReverseCycle' or set resistive_defrost_heater_capacity to 'Autosize'
3. Temperature Ranges: Use wide ranges for reliability
4. COP Values: Must be > 0 (typical: 3.5-4.5)"""
        
        return system_prompt, combined_prompt
    
    def _add_section_header(self, idf_content, system_type="HVAC SYSTEM"):
        """
        Add clear section header to HVAC objects for easy identification.
        
        Args:
            idf_content: Generated IDF text
            system_type: Type of system (e.g., "VRF HVAC SYSTEM")
        
        Returns:
            IDF content with section header and inline comments
        """
        header = f"""
!-======================================================================
!- {system_type} SECTION - GENERATED BY HVAC-LLM
!-======================================================================
!- This section contains all HVAC equipment objects generated automatically
!- DO NOT MODIFY - Generated from user requirements
!-======================================================================

"""
        
        # Add inline comments to identify specific objects
        lines = idf_content.split('\n')
        annotated_lines = []
        
        for line in lines:
            # Add inline comments for major HVAC objects
            if line.strip().startswith('HVACTemplate:Zone:VRF,'):
                annotated_lines.append(line + '    !- HVAC: VRF Zone Terminal Unit (Indoor Unit)')
            elif line.strip().startswith('HVACTemplate:System:VRF,'):
                annotated_lines.append(line + '    !- HVAC: VRF Outdoor Condensing Unit')
            elif line.strip().startswith('HVACTemplate:Zone:VAV,'):
                annotated_lines.append(line + '    !- HVAC: VAV Terminal Unit')
            elif line.strip().startswith('HVACTemplate:System:VAV,'):
                annotated_lines.append(line + '    !- HVAC: VAV Air Handling Unit')
            elif line.strip().startswith('HVACTemplate:Plant:ChilledWaterLoop,'):
                annotated_lines.append(line + '    !- HVAC: Chilled Water Plant Loop')
            elif line.strip().startswith('HVACTemplate:Plant:Chiller,'):
                annotated_lines.append(line + '    !- HVAC: Chiller Equipment')
            elif line.strip().startswith('HVACTemplate:Plant:Tower,'):
                annotated_lines.append(line + '    !- HVAC: Cooling Tower')
            elif line.strip().startswith('HVACTemplate:Plant:HotWaterLoop,'):
                annotated_lines.append(line + '    !- HVAC: Hot Water Plant Loop')
            elif line.strip().startswith('HVACTemplate:Plant:Boiler,'):
                annotated_lines.append(line + '    !- HVAC: Boiler Equipment')
            elif line.strip().startswith('HVACTemplate:Zone:FanCoil,'):
                annotated_lines.append(line + '    !- HVAC: Fan Coil Unit')
            elif line.strip().startswith('HVACTemplate:Zone:IdealLoadsAirSystem,'):
                annotated_lines.append(line + '    !- HVAC: Ideal Loads Air System')
            elif line.strip().startswith('ZoneControl:Thermostat,'):
                annotated_lines.append(line + '    !- HVAC: Zone Thermostat Control')
            elif line.strip().startswith('ThermostatSetpoint:'):
                annotated_lines.append(line + '    !- HVAC: Thermostat Setpoint Schedule')
            else:
                annotated_lines.append(line)
        
        annotated_content = '\n'.join(annotated_lines)
        
        # Add end marker
        footer = f"""

!-======================================================================
!- END OF {system_type} SECTION
!-======================================================================
"""
        
        return header + annotated_content + footer


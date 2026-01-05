"""
HVAC-LLM Knowledge Base Builder

Extracts knowledge from existing project data and builds ChromaDB vector store.
Run this ONCE before using RAG in agents.

Data Sources:
1. energyplus_vrf_prompt.json - VRF field specifications
2. outputs/simulations/*/eplusout.err - EnergyPlus simulation error patterns
3. docs/*.md - Design guidance documentation
4. data/knowledge/user_request_patterns.json - User request scenarios
5. Energy+.idd - Official EnergyPlus field specifications
6. data/knowledge/field_dependencies.json - Field dependency rules (NEW)
7. data/knowledge/error_fix_procedures.json - Step-by-step fix procedures (NEW)

Usage:
    python -m src.rag.knowledge_builder
    python -m src.rag.knowledge_builder --version 25.2.0
"""

import json
import re
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

try:
    import chromadb
    from chromadb.utils import embedding_functions
except ImportError:
    print("ERROR: chromadb not installed. Run: pip install chromadb")
    exit(1)

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    print("ERROR: sentence-transformers not installed. Run: pip install sentence-transformers")
    exit(1)


class KnowledgeBaseBuilder:
    """Builds ChromaDB vector database from HVAC-LLM project data"""
    
    def __init__(self, db_path="data/vector_db", energyplus_version="25.2.0"):
        """
        Initialize knowledge base builder.
        
        Args:
            db_path: Path to ChromaDB storage directory
            energyplus_version: EnergyPlus version for version-aware indexing
        """
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)
        self.version = energyplus_version
        
        # Initialize embedding model (BGE-small for speed, can upgrade to BGE-M3)
        print("Loading embedding model (BAAI/bge-small-en-v1.5)...")
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="BAAI/bge-small-en-v1.5"
        )
        
        # Initialize ChromaDB persistent client
        self.client = chromadb.PersistentClient(path=str(self.db_path))
        print(f"✓ ChromaDB initialized at: {self.db_path}\n")
    
    def build_all_collections(self):
        """Build all knowledge base collections"""
        print("=" * 70)
        print("BUILDING HVAC-LLM KNOWLEDGE BASE")
        print("=" * 70 + "\n")
        
        # Collection 1: VRF Field Specifications (for Agent 1)
        self.build_field_specs_collection()
        
        # Collection 2: Error-Fix Patterns (for Agent 3) - FROM SIMULATIONS
        self.build_error_patterns_collection()
        
        # Collection 3: Design Rules (for Agent 1 & 1.5)
        self.build_design_rules_collection()
        
        # Collection 4: User Request Examples (for Agent 1)
        self.build_user_request_examples()
        
        # Collection 5: Official EnergyPlus IDD Specifications (NEW)
        self.build_energyplus_idd_collection()
        
        # Collection 6: Field Dependency Rules (NEW)
        self.build_field_dependencies_collection()
        
        # Collection 7: Error Fix Procedures (NEW)
        self.build_error_fix_procedures_collection()
        
        # Collection 8: VRF EnergyPlus Documentation (NEW)
        self.build_vrf_documentation_collection()
        
        # Collection 9: VRF Design Patterns (NEW)
        self.build_vrf_design_patterns_collection()
        
        print("\n" + "=" * 70)
        print("✅ KNOWLEDGE BASE BUILD COMPLETE")
        print("=" * 70)
        print(f"\nVector DB location: {self.db_path.absolute()}")
        print("\nKnowledge Sources:")
        print("  1. VRF prompt templates (existing system)")
        print("  2. Simulation error patterns (auto-updated from runs)")
        print("  3. Documentation files (design guidance)")
        print("  4. User request patterns (expandable scenarios)")
        print("  5. Official EnergyPlus IDD (complete field specs)")
        print("  6. Field dependency rules")
        print("  7. Error fix procedures")
        print("  8. VRF EnergyPlus documentation")
        print("  9. VRF design patterns")
        print("\nCollections created:")
        for collection in self.client.list_collections():
            print(f"  - {collection.name} ({collection.count()} documents)")
        print("\n✓ You can now use RAG in agents via RAGRetriever class")
    
    def build_field_specs_collection(self):
        """Extract VRF field specifications from energyplus_vrf_prompt.json"""
        print("[1/7] Building 'field_specs' collection...")
        
        # Load VRF prompt template
        prompt_path = Path("src/agents/energyplus_vrf_prompt.json")
        
        if not prompt_path.exists():
            print(f"  ❌ Not found: {prompt_path}")
            print("  Skipping field specs collection")
            return
        
        with open(prompt_path, encoding='utf-8') as f:
            prompt_data = json.load(f)
        
        # Extract system prompt containing field specifications
        system_prompt = prompt_data[0]["system_prompt"]
        
        # Parse System:VRF fields
        vrf_system_fields = self._extract_fields_from_prompt(
            system_prompt,
            "HVACTemplate:System:VRF CORRECT FIELD ORDER"
        )
        
        # Parse Zone:VRF fields
        vrf_zone_fields = self._extract_fields_from_prompt(
            system_prompt,
            "HVACTemplate:Zone:VRF CORRECT FIELD ORDER"
        )
        
        # Create version-aware collection
        collection_name = f"field_specs_v{self.version.replace('.', '_')}"
        collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_fn,
            metadata={
                "description": "VRF field specifications for Agent 1",
                "energyplus_version": self.version,
                "created_at": datetime.now().isoformat()
            }
        )
        
        # Prepare documents for embedding
        documents = []
        metadatas = []
        ids = []
        
        # Add System:VRF fields
        for field in vrf_system_fields:
            doc_text = self._format_field_document(field, "System:VRF")
            documents.append(doc_text)
            metadatas.append({
                "object_type": "HVACTemplate:System:VRF",
                "field_number": field['number'],
                "field_name": field['name'],
                "field_type": field['type'],
                "category": "vrf_system",
                "energyplus_version": self.version
            })
            ids.append(f"vrf_system_field_{field['number']}_v{self.version.replace('.', '_')}")
        
        # Add Zone:VRF fields
        for field in vrf_zone_fields:
            doc_text = self._format_field_document(field, "Zone:VRF")
            documents.append(doc_text)
            metadatas.append({
                "object_type": "HVACTemplate:Zone:VRF",
                "field_number": field['number'],
                "field_name": field['name'],
                "field_type": field['type'],
                "category": "vrf_zone",
                "energyplus_version": self.version
            })
            ids.append(f"vrf_zone_field_{field['number']}_v{self.version.replace('.', '_')}")
        
        # Add to ChromaDB
        if documents:
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            print(f"  ✓ Added {len(documents)} field specifications")
            print(f"    - System:VRF: {len(vrf_system_fields)} fields")
            print(f"    - Zone:VRF: {len(vrf_zone_fields)} fields")
        else:
            print("  ⚠ No fields extracted")
    
    def build_error_patterns_collection(self):
        """Extract error-fix patterns from EnergyPlus simulation outputs"""
        print("\n[2/4] Building 'error_patterns' collection...")
        
        sim_dir = Path("outputs/simulations")
        
        if not sim_dir.exists():
            print(f"  ⚠ No simulation directory found: {sim_dir}")
            print("    Creating empty collection for future use")
            self.client.get_or_create_collection(
                name="error_patterns",
                embedding_function=self.embedding_fn,
                metadata={
                    "description": "EnergyPlus error patterns with fixes for Agent 3",
                    "created_at": datetime.now().isoformat()
                }
            )
            return
        
        # Extract patterns from all simulation error files
        all_patterns = []
        
        # Find all eplusout.err files (both failed and successful sims)
        for sim_folder in sim_dir.iterdir():
            if not sim_folder.is_dir():
                continue
            
            err_file = sim_folder / "eplusout.err"
            if not err_file.exists():
                continue
            
            try:
                patterns = self._extract_energyplus_errors(err_file, sim_folder.name)
                all_patterns.extend(patterns)
            except Exception as e:
                print(f"  ⚠ Error reading {err_file.name}: {e}")
        
        if not all_patterns:
            print("  ⚠ No error patterns extracted from simulations")
            print("    Run pipeline with simulations to generate patterns")
            self.client.get_or_create_collection(
                name="error_patterns",
                embedding_function=self.embedding_fn,
                metadata={"description": "EnergyPlus error patterns", "created_at": datetime.now().isoformat()}
            )
            return
        
        # Create collection
        collection = self.client.get_or_create_collection(
            name="error_patterns",
            embedding_function=self.embedding_fn,
            metadata={
                "description": "EnergyPlus error patterns with fixes for Agent 3",
                "created_at": datetime.now().isoformat()
            }
        )
        
        # Prepare documents
        documents = []
        metadatas = []
        ids = []
        
        for i, pattern in enumerate(all_patterns):
            # Document is the error message (what we'll search for)
            documents.append(pattern["error_message"])
            
            # Metadata contains fix details
            metadatas.append({
                "error_type": pattern["error_type"],
                "object_name": pattern.get("object_name", ""),
                "field_hint": pattern.get("field_hint", ""),
                "fix_applied": pattern.get("fix_applied", ""),
                "severity": pattern["severity"],
                "success_after_fix": pattern.get("success_after_fix", False),
                "source_sim": pattern["source"],
                "category": pattern.get("category", "general")
            })
            
            ids.append(f"error_pattern_{i}")
        
        # Add to ChromaDB
        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        
        print(f"  ✓ Added {len(documents)} EnergyPlus error patterns")
        print(f"    Sources: {len(set(p['source'] for p in all_patterns))} simulation runs")
        
        # Show breakdown by severity
        severe_count = sum(1 for p in all_patterns if p['severity'] == 'Severe')
        fatal_count = sum(1 for p in all_patterns if p['severity'] == 'Fatal')
        warning_count = sum(1 for p in all_patterns if p['severity'] == 'Warning')
        print(f"    - Fatal: {fatal_count}, Severe: {severe_count}, Warning: {warning_count}")
    
    def build_design_rules_collection(self):
        """Extract design knowledge from documentation"""
        print("\n[3/4] Building 'design_rules' collection...")
        
        docs_dir = Path("docs")
        
        # Target documentation files with VRF knowledge
        doc_files = [
            "VRF_42_FIELDS_EXPLAINED.md",
            "VRF_42_QUICK_REFERENCE.md",
            "AGENT1_GENERATOR_UPDATES.md",
            "AGENT3_CORRECTOR_UPDATES.md"
        ]
        
        collection = self.client.get_or_create_collection(
            name="design_rules",
            embedding_function=self.embedding_fn,
            metadata={
                "description": "Design guidance from documentation",
                "created_at": datetime.now().isoformat()
            }
        )
        
        documents = []
        metadatas = []
        ids = []
        doc_id = 0
        
        for doc_file in doc_files:
            doc_path = docs_dir / doc_file
            if not doc_path.exists():
                continue
            
            try:
                with open(doc_path, encoding='utf-8') as f:
                    content = f.read()
                
                # Chunk by sections
                chunks = self._chunk_markdown(content)
                
                for chunk in chunks:
                    documents.append(chunk["text"])
                    metadatas.append({
                        "source_file": doc_file,
                        "section": chunk["section"],
                        "category": "design_guidance"
                    })
                    ids.append(f"design_rule_{doc_id}")
                    doc_id += 1
            except Exception as e:
                print(f"  ⚠ Error reading {doc_file}: {e}")
        
        if documents:
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            print(f"  ✓ Added {len(documents)} design rule chunks")
            print(f"    Sources: {len(set(m['source_file'] for m in metadatas))} documentation files")
        else:
            print("  ⚠ No design documentation found")
    
    def build_user_request_examples(self):
        """Extract user request patterns from comprehensive knowledge base"""
        print("\n[4/5] Building 'user_request_examples' collection...")
        
        # Primary source: Comprehensive pattern knowledge base
        knowledge_path = Path("data/knowledge/user_request_patterns.json")
        
        # Fallback: Original config file
        config_path = Path("config/hvac_requests.json")
        
        collection = self.client.get_or_create_collection(
            name="user_request_examples",
            embedding_function=self.embedding_fn,
            metadata={
                "description": "User request patterns for intent recognition and field mapping",
                "created_at": datetime.now().isoformat()
            }
        )
        
        documents = []
        metadatas = []
        ids = []
        doc_id = 0
        
        # Load comprehensive patterns if available
        if knowledge_path.exists():
            try:
                with open(knowledge_path, encoding='utf-8') as f:
                    patterns_data = json.load(f)
                
                # Process each category
                for category, patterns in patterns_data.items():
                    if not isinstance(patterns, list):
                        continue
                    
                    for pattern in patterns:
                        description = pattern.get("description", "")
                        keywords = pattern.get("keywords", [])
                        tech_specs = pattern.get("technical_specs", {})
                        
                        if not description:
                            continue
                        
                        # Create rich document with keywords
                        doc_text = description
                        if keywords:
                            doc_text += " Keywords: " + ", ".join(keywords)
                        
                        documents.append(doc_text)
                        metadatas.append({
                            "category": category,
                            "description": description,
                            "keywords": json.dumps(keywords),
                            "technical_specs": json.dumps(tech_specs),
                            "source": "comprehensive_patterns"
                        })
                        ids.append(f"pattern_{doc_id}")
                        doc_id += 1
                
                print(f"  ✓ Added {len(documents)} comprehensive request patterns")
                
            except Exception as e:
                print(f"  ⚠ Error reading patterns: {e}")
        
        # Also load original config examples as supplementary
        if config_path.exists():
            try:
                with open(config_path, encoding='utf-8') as f:
                    requests_data = json.load(f)
                
                for request_id, request_data in requests_data.items():
                    if not isinstance(request_data, dict):
                        continue
                    
                    prompt = request_data.get("prompt", "")
                    if not prompt:
                        continue
                    
                    documents.append(prompt)
                    metadatas.append({
                        "category": "config_examples",
                        "request_id": request_id,
                        "zones": json.dumps(request_data.get("zones", [])),
                        "source": "hvac_requests_config"
                    })
                    ids.append(f"config_{request_id}")
                    doc_id += 1
                
                print(f"  ✓ Added {doc_id - len(documents)} config examples")
                
            except Exception as e:
                print(f"  ⚠ Error reading config: {e}")
        
        # Add all documents to collection
        if documents:
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            print(f"  ✓ Total user request examples: {len(documents)}")
        else:
            print("  ⚠ No user request examples found")
    
    def build_energyplus_idd_collection(self):
        """Extract official field specifications from Energy+.idd file"""
        print("\n[5/5] Building 'idd_specifications' collection...")
        
        # Try common EnergyPlus installation paths
        version_dash = self.version.replace('.', '-')
        idd_paths = [
            Path(f"C:/EnergyPlusV{version_dash}/Energy+.idd"),  # Exact version match
            Path("C:/EnergyPlusV25-2-0/Energy+.idd"),  # Current most common
            Path("C:/EnergyPlusV25-1-0/Energy+.idd"),  # Fallback v25.1
            Path("C:/EnergyPlusV24-2-0/Energy+.idd"),  # Fallback v24.2
            Path("Energy+.idd"),  # Local copy if available
            Path("data/Energy+.idd")  # Alternative location
        ]
        
        idd_file = None
        for path in idd_paths:
            if path.exists():
                idd_file = path
                print(f"  ✓ Found IDD file: {path}")
                break
        
        if not idd_file:
            print(f"  ⚠ Energy+.idd not found in common locations")
            print(f"    Searched: C:/EnergyPlusV{version_dash}/Energy+.idd and fallbacks")
            print("    Skipping IDD collection (optional - using existing VRF specs)")
            return
        
        # Parse IDD file for HVAC objects
        target_objects = [
            "HVACTemplate:System:VRF",
            "HVACTemplate:Zone:VRF",
            "AirConditioner:VariableRefrigerantFlow",
            "ZoneHVAC:TerminalUnit:VariableRefrigerantFlow"
        ]
        
        try:
            parsed_objects = self._parse_idd_file(idd_file, target_objects)
        except Exception as e:
            print(f"  ⚠ Error parsing IDD file: {e}")
            return
        
        if not parsed_objects:
            print("  ⚠ No VRF objects found in IDD file")
            return
        
        # Create version-aware collection
        collection_name = f"idd_specs_v{self.version.replace('.', '_')}"
        collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_fn,
            metadata={
                "description": "Official EnergyPlus IDD field specifications",
                "source": str(idd_file),
                "energyplus_version": self.version,
                "created_at": datetime.now().isoformat()
            }
        )
        
        documents = []
        metadatas = []
        ids = []
        doc_id = 0
        
        for obj_type, fields in parsed_objects.items():
            for field in fields:
                # Create rich searchable document with official descriptions
                doc_parts = [f"{obj_type} - Field: {field['name']}"]
                
                if field.get('description'):
                    doc_parts.append(f"Description: {field['description']}")
                
                if field.get('type'):
                    doc_parts.append(f"Type: {field['type']}")
                
                if field.get('minimum') is not None:
                    doc_parts.append(f"Minimum: {field['minimum']}")
                
                if field.get('maximum') is not None:
                    doc_parts.append(f"Maximum: {field['maximum']}")
                
                if field.get('default'):
                    doc_parts.append(f"Default: {field['default']}")
                
                if field.get('choices'):
                    doc_parts.append(f"Valid choices: {', '.join(field['choices'])}")
                
                doc_text = ". ".join(doc_parts)
                documents.append(doc_text)
                
                metadatas.append({
                    "object_type": obj_type,
                    "field_name": field['name'],
                    "field_type": field.get('type', 'unknown'),
                    "minimum": str(field.get('minimum', '')),
                    "maximum": str(field.get('maximum', '')),
                    "default": str(field.get('default', '')),
                    "required": field.get('required', False),
                    "source": "official_idd",
                    "energyplus_version": self.version
                })
                
                ids.append(f"idd_{obj_type}_{field['name']}_v{self.version.replace('.', '_')}")
                doc_id += 1
        
        if documents:
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            print(f"  ✓ Added {len(documents)} official IDD field specifications")
            
            # Show breakdown by object type
            for obj_type, fields in parsed_objects.items():
                short_name = obj_type.split(':')[-1]
                print(f"    - {short_name}: {len(fields)} fields")
        else:
            print("  ⚠ No IDD fields extracted")
    
    # ========== Helper Methods ==========
    
    def _extract_fields_from_prompt(self, text: str, section_header: str) -> List[Dict]:
        """Parse field definitions from prompt text"""
        fields = []
        
        if section_header not in text:
            return fields
        
        # Extract section text
        section_start = text.find(section_header)
        # Find next double newline or end of major section
        section_end = text.find("\n\n", section_start + 200)
        if section_end == -1:
            section_end = len(text)
        
        section_text = text[section_start:section_end]
        
        # Parse field lines: "1. A1 - Field_Name (type)" or "1. field_name (type)"
        # Updated pattern to handle both formats
        field_pattern = r'(\d+)\.\s+(?:[AN]\d+\s+-\s+)?([A-Za-z_]+)\s+\(([^)]+)\)'
        
        for match in re.finditer(field_pattern, section_text):
            field_num = int(match.group(1))
            field_name = match.group(2)
            field_type_raw = match.group(3)
            
            # Parse type and extract enum values if present
            field_type = field_type_raw.lower()
            enum_values = []
            
            if '"' in field_type_raw or 'enum' in field_type_raw.lower():
                # Extract quoted enum values
                enum_values = re.findall(r'"([^"]+)"', field_type_raw)
                field_type = "enum"
            elif 'autosize' in field_type_raw.lower():
                field_type = "number or Autosize"
            elif 'number' in field_type_raw.lower():
                field_type = "number"
            elif 'string' in field_type_raw.lower():
                field_type = "string"
            elif 'integer' in field_type_raw.lower():
                field_type = "integer"
            
            fields.append({
                "number": field_num,
                "name": field_name,
                "type": field_type,
                "enum_values": enum_values if enum_values else None,
                "raw_type": field_type_raw
            })
        
        return fields
    
    def _format_field_document(self, field: Dict, object_category: str) -> str:
        """Format field specification as searchable document"""
        parts = [
            f"Field {field['number']}: {field['name']}",
            f"Type: {field['type']}"
        ]
        
        if field.get('enum_values'):
            parts.append(f"Valid values: {', '.join(field['enum_values'])}")
        
        parts.append(f"Object: {object_category}")
        
        # Add searchable keywords
        keywords = field['name'].replace('_', ' ')
        parts.append(f"Keywords: {keywords}")
        
        return ". ".join(parts)
    
    def _extract_energyplus_errors(self, err_file: Path, source_sim: str) -> List[Dict]:
        """Extract meaningful error patterns from EnergyPlus error files"""
        patterns = []
        
        # Determine if this simulation was successful (sim2 typically means fixed)
        success_after_fix = "sim2" in source_sim.lower() or "fixed" in source_sim.lower()
        
        try:
            with open(err_file, encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception as e:
            return patterns
        
        # Extract Severe and Fatal errors (most actionable)
        # Pattern matches: ** Severe ** text
        #                  **   ~~~   ** more text (continuation lines)
        severe_pattern = r'\*\*\s+(Severe|Fatal)\s+\*\*\s+(.+?)(?=\n\s*\*\*\s+(?:Severe|Fatal|Warning)\s+\*\*|$)'
        for match in re.finditer(severe_pattern, content, re.DOTALL):
            severity = match.group(1)
            error_text = match.group(2).strip()
            
            # Clean up multi-line errors - keep continuation lines (**   ~~~   **)
            error_text = re.sub(r'\n\s*\*\*\s*~~~\s*\*\*\s*', ' ', error_text)
            error_text = ' '.join(error_text.split())  # Normalize whitespace
            
            # Skip if too short
            if len(error_text) < 20:
                continue
            
            # Extract object name if present
            object_match = re.search(r'(?:AirConditioner:VariableRefrigerantFlow|HVACTemplate:System:VRF|HVACTemplate:Zone:VRF)\s*[=:]\s*"([^"]+)"', error_text)
            object_name = object_match.group(1) if object_match else ""
            
            # Categorize and extract fix hints
            category, field_hint, fix_applied = self._categorize_error(error_text)
            
            patterns.append({
                "error_message": error_text[:300],  # Limit length
                "error_type": severity,
                "object_name": object_name,
                "field_hint": field_hint,
                "fix_applied": fix_applied if success_after_fix else "",
                "severity": severity,
                "success_after_fix": success_after_fix,
                "source": source_sim,
                "category": category
            })
        
        # Also extract critical warnings that often need fixes
        warning_pattern = r'\*\*\s+Warning\s+\*\*\s+(.+?)(?=\n\s*\*\*\s+(?:Severe|Fatal|Warning)\s+\*\*|$)'
        critical_warnings = [
            "Master Thermostat",
            "Resistive Defrost Heater Capacity",
            "could not find a matching",
            "must be entered when"
        ]
        
        for match in re.finditer(warning_pattern, content, re.DOTALL):
            warning_text = match.group(1).strip()
            warning_text = re.sub(r'\n\s*\*\*\s*~~~\s*\*\*\s*', ' ', warning_text)
            warning_text = ' '.join(warning_text.split())
            
            # Only include critical warnings
            if not any(kw in warning_text for kw in critical_warnings):
                continue
            
            if len(warning_text) < 20:
                continue
            
            object_match = re.search(r'(?:AirConditioner:VariableRefrigerantFlow|HVACTemplate:System:VRF|HVACTemplate:Zone:VRF)\s*[=:]\s*"([^"]+)"', warning_text)
            object_name = object_match.group(1) if object_match else ""
            
            category, field_hint, fix_applied = self._categorize_error(warning_text)
            
            patterns.append({
                "error_message": warning_text[:300],
                "error_type": "Warning",
                "object_name": object_name,
                "field_hint": field_hint,
                "fix_applied": fix_applied if success_after_fix else "",
                "severity": "Warning",
                "success_after_fix": success_after_fix,
                "source": source_sim,
                "category": category
            })
        
        return patterns
    
    def _categorize_error(self, error_text: str) -> tuple:
        """Categorize error and extract fix hints"""
        error_lower = error_text.lower()
        
        # Master Thermostat errors
        if "master thermostat" in error_lower:
            if "must be entered" in error_lower:
                return ("master_thermostat", "Field 14: Master_Thermostat_Priority_Control_Type", "Set to LoadPriority or ThermostatOffsetPriority")
            elif "could not find" in error_lower or "matching" in error_lower:
                return ("master_thermostat", "Field 13: Zone_Name_for_Master_Thermostat_Location", "Provide valid zone name from Zone:VRF objects")
        
        # Defrost errors
        if "defrost" in error_lower and "resistive" in error_lower:
            if "= 0.0" in error_lower or "capacity" in error_lower:
                return ("defrost", "Field 34: Resistive_Defrost_Heater_Capacity", "Set to Autosize or positive value")
        
        # Operating temperature range errors
        if "min/max" in error_lower and "temperature" in error_lower:
            if "cooling" in error_lower:
                return ("operating_range", "Fields 5-6: Cooling temperature limits", "Expand cooling temperature range (-10°C to 50°C)")
            elif "heating" in error_lower:
                return ("operating_range", "Fields 10-11: Heating temperature limits", "Expand heating temperature range (-30°C to 20°C)")
        
        # Curve errors
        if "curve" in error_lower and "not equal to 1.0" in error_lower:
            return ("curve_validation", "Performance curves", "Warning only - typically acceptable")
        
        # Zone connection errors
        if "zone" in error_lower and ("not found" in error_lower or "missing" in error_lower):
            return ("zone_connection", "Zone references", "Verify zone names match exactly")
        
        # Generic
        return ("general", "", "")
    
    def _parse_idd_file(self, idd_path: Path, object_types: List[str]) -> Dict:
        r"""
        Parse Energy+.idd file for specified object types.
        
        IDD format example:
        HVACTemplate:System:VRF,
          \memo Template for VRF system
          A1 , \field Name
               \required-field
               \type alpha
          N1 , \field Gross Rated Total Cooling Capacity
               \type real
               \units W
               \minimum> 0.0
               \autosizable
        """
        parsed = {}
        
        try:
            with open(idd_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception as e:
            print(f"    Error reading IDD file: {e}")
            return parsed
        
        for obj_type in object_types:
            # Find object definition in IDD (case-insensitive)
            # Match: "ObjectType," followed by fields until next object or end
            pattern = rf'^{re.escape(obj_type)},\s*$(.*?)(?=^\w+:|\Z)'
            match = re.search(pattern, content, re.MULTILINE | re.DOTALL | re.IGNORECASE)
            
            if not match:
                continue
            
            obj_content = match.group(1)
            fields = []
            
            # Split into field blocks (A1, N1, A2, etc.)
            # Pattern: field identifier (A1, N1, etc.) followed by field properties
            field_blocks = re.split(r'\n\s*([AN]\d+)\s*[,;]', obj_content)
            
            # Process pairs: field_id, field_content
            for i in range(1, len(field_blocks), 2):
                if i + 1 >= len(field_blocks):
                    break
                
                field_id = field_blocks[i].strip()
                field_content = field_blocks[i + 1]
                
                # Extract field properties
                field_data = {'field_id': field_id}
                
                # Field name
                name_match = re.search(r'\\field\s+([^\n]+)', field_content)
                if name_match:
                    field_data['name'] = name_match.group(1).strip()
                else:
                    field_data['name'] = f"Field_{field_id}"
                
                # Field type
                type_match = re.search(r'\\type\s+(\w+)', field_content)
                if type_match:
                    field_data['type'] = type_match.group(1).strip()
                
                # Minimum value
                min_match = re.search(r'\\minimum(?:>)?\s+([^\n]+)', field_content)
                if min_match:
                    field_data['minimum'] = min_match.group(1).strip()
                
                # Maximum value
                max_match = re.search(r'\\maximum(?:<)?\s+([^\n]+)', field_content)
                if max_match:
                    field_data['maximum'] = max_match.group(1).strip()
                
                # Default value
                default_match = re.search(r'\\default\s+([^\n]+)', field_content)
                if default_match:
                    field_data['default'] = default_match.group(1).strip()
                
                # Required field
                field_data['required'] = bool(re.search(r'\\required-field', field_content))
                
                # Autosizable
                field_data['autosizable'] = bool(re.search(r'\\autosizable', field_content))
                
                # Valid choices (for alpha fields with key values)
                key_matches = re.findall(r'\\key\s+([^\n]+)', field_content)
                if key_matches:
                    field_data['choices'] = [k.strip() for k in key_matches]
                
                # Note/description
                note_match = re.search(r'\\note\s+([^\n]+)', field_content)
                if note_match:
                    field_data['description'] = note_match.group(1).strip()
                else:
                    # Try memo if no note
                    memo_match = re.search(r'\\memo\s+([^\n]+)', field_content)
                    if memo_match:
                        field_data['description'] = memo_match.group(1).strip()
                    else:
                        field_data['description'] = ''
                
                # Units
                units_match = re.search(r'\\units\s+([^\n]+)', field_content)
                if units_match:
                    field_data['units'] = units_match.group(1).strip()
                
                fields.append(field_data)
            
            if fields:
                parsed[obj_type] = fields
        
        return parsed
    
    def build_field_dependencies_collection(self):
        """Extract field dependency rules from field_dependencies.json"""
        print("[6/7] Building 'field_dependencies' collection...")
        
        # Load dependency rules
        dep_path = Path("data/knowledge/field_dependencies.json")
        
        if not dep_path.exists():
            print(f"  ❌ Not found: {dep_path}")
            print("  Skipping field dependencies collection")
            return
        
        with open(dep_path, encoding='utf-8') as f:
            dep_data = json.load(f)
        
        # Create collection
        collection_name = f"field_dependencies_v{self.version.replace('.', '_')}"
        try:
            self.client.delete_collection(collection_name)
        except:
            pass
        
        collection = self.client.create_collection(
            name=collection_name,
            embedding_function=self.embedding_fn,
            metadata={"description": "VRF field dependency rules and constraints"}
        )
        
        documents = []
        metadatas = []
        ids = []
        
        # Process VRF system dependencies
        for dep in dep_data.get("vrf_system_dependencies", []):
            doc_text = f"""
Dependency Rule: {dep['dependency_id']}

Trigger Field: {dep['trigger_field']}
{f"Trigger Values: {', '.join(dep['trigger_values'])}" if dep.get('trigger_values') else ''}

Required Fields:
{self._format_requirements(dep.get('requires', []))}

{f"Optional Fields:\n{self._format_requirements(dep.get('optional', []))}" if dep.get('optional') else ''}

Error if violated: {dep.get('error_if_violated', 'N/A')}
Fix Strategy: {dep.get('fix_strategy', 'N/A')}
Severity: {dep.get('severity', 'Unknown')}
Frequency: {dep.get('frequency', 'Unknown')}
            """.strip()
            
            documents.append(doc_text)
            metadatas.append({
                "dependency_id": dep['dependency_id'],
                "trigger_field": dep['trigger_field'],
                "severity": dep.get('severity', 'Unknown'),
                "frequency": dep.get('frequency', 'Unknown'),
                "object_type": "System:VRF"
            })
            ids.append(f"system_dep_{dep['dependency_id']}")
        
        # Process VRF zone dependencies
        for dep in dep_data.get("vrf_zone_dependencies", []):
            doc_text = f"""
Dependency Rule: {dep['dependency_id']}

Trigger Field: {dep['trigger_field']}
{f"Trigger Values: {', '.join(dep['trigger_values'])}" if dep.get('trigger_values') else ''}

{f"Required Fields:\n{self._format_requirements(dep.get('requires', []))}" if dep.get('requires') else ''}

{f"Constraint: {dep.get('constraint')}" if dep.get('constraint') else ''}
{f"Error if violated: {dep.get('error_if_violated')}" if dep.get('error_if_violated') else ''}
{f"Fix Strategy: {dep.get('fix_strategy')}" if dep.get('fix_strategy') else ''}
Severity: {dep.get('severity', 'Unknown')}
Frequency: {dep.get('frequency', 'Unknown')}
{f"Note: {dep.get('note')}" if dep.get('note') else ''}
            """.strip()
            
            documents.append(doc_text)
            metadatas.append({
                "dependency_id": dep['dependency_id'],
                "trigger_field": dep['trigger_field'],
                "severity": dep.get('severity', 'Unknown'),
                "frequency": dep.get('frequency', 'Unknown'),
                "object_type": "Zone:VRF"
            })
            ids.append(f"zone_dep_{dep['dependency_id']}")
        
        # Process cross-object dependencies
        for dep in dep_data.get("cross_object_dependencies", []):
            doc_text = f"""
Cross-Object Dependency: {dep['dependency_id']}

Rule: {dep['rule']}
Constraint: {dep.get('constraint', 'N/A')}
Error if violated: {dep.get('error_if_violated', 'N/A')}
Severity: {dep.get('severity', 'Unknown')}
Frequency: {dep.get('frequency', 'Unknown')}
            """.strip()
            
            documents.append(doc_text)
            metadatas.append({
                "dependency_id": dep['dependency_id'],
                "severity": dep.get('severity', 'Unknown'),
                "frequency": dep.get('frequency', 'Unknown'),
                "object_type": "Cross-Object"
            })
            ids.append(f"cross_dep_{dep['dependency_id']}")
        
        # Add performance constraints
        for constraint in dep_data.get("performance_constraints", []):
            doc_text = f"""
Performance Constraint: {constraint['constraint_id']}

Field: {constraint.get('field', 'N/A')}
{f"Typical Range: {constraint.get('typical_range')}" if constraint.get('typical_range') else ''}
{f"Minimum Acceptable: {constraint.get('minimum_acceptable')}" if constraint.get('minimum_acceptable') else ''}
{f"High Efficiency: {constraint.get('high_efficiency')}" if constraint.get('high_efficiency') else ''}
{f"Cooling Supply Temp: {constraint.get('cooling_supply_temp')}" if constraint.get('cooling_supply_temp') else ''}
{f"Heating Supply Temp: {constraint.get('heating_supply_temp')}" if constraint.get('heating_supply_temp') else ''}
{f"Rule: {constraint.get('rule')}" if constraint.get('rule') else ''}
Note: {constraint.get('note', 'N/A')}
            """.strip()
            
            documents.append(doc_text)
            metadatas.append({
                "constraint_id": constraint['constraint_id'],
                "object_type": "Performance"
            })
            ids.append(f"perf_{constraint['constraint_id']}")
        
        # Add to collection
        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        
        print(f"  ✅ Added {len(documents)} dependency rules")
        print(f"     - System dependencies: {len(dep_data.get('vrf_system_dependencies', []))}")
        print(f"     - Zone dependencies: {len(dep_data.get('vrf_zone_dependencies', []))}")
        print(f"     - Cross-object dependencies: {len(dep_data.get('cross_object_dependencies', []))}")
        print(f"     - Performance constraints: {len(dep_data.get('performance_constraints', []))}")
    
    def build_error_fix_procedures_collection(self):
        """Extract error fix procedures from error_fix_procedures.json"""
        print("[7/7] Building 'error_fix_procedures' collection...")
        
        # Load fix procedures
        fix_path = Path("data/knowledge/error_fix_procedures.json")
        
        if not fix_path.exists():
            print(f"  ❌ Not found: {fix_path}")
            print("  Skipping error fix procedures collection")
            return
        
        with open(fix_path, encoding='utf-8') as f:
            fix_data = json.load(f)
        
        # Create collection
        collection_name = "error_fix_procedures"
        try:
            self.client.delete_collection(collection_name)
        except:
            pass
        
        collection = self.client.create_collection(
            name=collection_name,
            embedding_function=self.embedding_fn,
            metadata={"description": "Step-by-step error fix procedures for common VRF errors"}
        )
        
        documents = []
        metadatas = []
        ids = []
        
        # Process each error fix procedure
        for error in fix_data.get("vrf_common_errors", []):
            # Create main procedure document
            doc_text = f"""
Error: {error['error_pattern']}

Severity: {error['severity']}
Frequency: {error['frequency']}

Root Cause: {error['root_cause']}

Diagnosis Steps:
{chr(10).join(error['diagnosis_steps'])}

Fix Procedures:
{self._format_fix_procedures(error['fix_procedure'])}

Prevention: {error.get('prevention', 'N/A')}
Related Fields: {', '.join(error.get('related_fields', []))}
{f"Related Errors: {', '.join(error.get('related_errors', []))}" if error.get('related_errors') else ''}
            """.strip()
            
            documents.append(doc_text)
            metadatas.append({
                "error_id": error['error_id'],
                "severity": error['severity'],
                "frequency": error['frequency'],
                "error_pattern": error['error_pattern'][:200]  # Truncate for metadata
            })
            ids.append(f"fix_{error['error_id']}")
        
        # Add to collection
        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        
        print(f"  ✅ Added {len(documents)} error fix procedures")
        print(f"     - Coverage: {fix_data.get('metadata', {}).get('coverage', 'Unknown')}")
    
    def _format_requirements(self, requirements: List[Dict]) -> str:
        """Format requirement items for dependency rules"""
        if not requirements:
            return "None"
        
        lines = []
        for req in requirements:
            field = req.get('field', 'Unknown')
            must_be = req.get('must_be') or req.get('should_be', 'specified')
            valid_values = req.get('valid_values', '')
            note = req.get('note', '')
            recommended = req.get('recommended', '')
            
            line = f"  - {field}: must be {must_be}"
            if valid_values:
                line += f" (valid: {valid_values})"
            if recommended:
                line += f" (recommended: {recommended})"
            if note:
                line += f"\n    Note: {note}"
            lines.append(line)
        
        return '\n'.join(lines)
    
    def _format_fix_procedures(self, fix_proc: Dict) -> str:
        """Format fix procedure options"""
        lines = []
        
        for option_key, option in fix_proc.items():
            desc = option.get('description', 'Fix option')
            steps = option.get('steps', [])
            success_rate = option.get('success_rate', 'Unknown')
            recommended = " [RECOMMENDED]" if option.get('recommended') else ""
            
            lines.append(f"\n{option_key.upper()}{recommended}: {desc}")
            lines.append(f"  Success Rate: {success_rate}")
            if steps:
                lines.append("  Steps:")
                lines.extend([f"    {step}" for step in steps])
            if option.get('note'):
                lines.append(f"  Note: {option['note']}")
            if option.get('typical_values'):
                lines.append(f"  Typical Values: {option['typical_values']}")
            if option.get('use_case'):
                lines.append(f"  Use Case: {option['use_case']}")
        
        return '\n'.join(lines)
    
    def _chunk_markdown(self, content: str) -> List[Dict]:
        """Chunk markdown documentation by sections"""
        chunks = []
        
        # Split on ## headers (but not #)
        sections = re.split(r'\n##\s+', content)
        
        for section in sections:
            if not section.strip():
                continue
            
            lines = section.split("\n", 1)
            section_title = lines[0].strip("#").strip() if lines else "Introduction"
            section_text = lines[1].strip() if len(lines) > 1 else ""
            
            # Skip very short sections
            if len(section_text) < 50:
                continue
            
            # Limit chunk size to prevent token overflow
            max_chunk_size = 800
            if len(section_text) > max_chunk_size:
                # Split into smaller chunks at paragraph boundaries
                paragraphs = section_text.split("\n\n")
                current_chunk = ""
                
                for para in paragraphs:
                    if len(current_chunk) + len(para) < max_chunk_size:
                        current_chunk += para + "\n\n"
                    else:
                        if current_chunk:
                            chunks.append({
                                "section": section_title,
                                "text": current_chunk.strip()
                            })
                        current_chunk = para + "\n\n"
                
                if current_chunk:
                    chunks.append({
                        "section": section_title,
                        "text": current_chunk.strip()
                    })
            else:
                chunks.append({
                    "section": section_title,
                    "text": section_text
                })
        
        return chunks

    def build_vrf_documentation_collection(self):
        """Build collection from VRF EnergyPlus documentation"""
        print("[8/9] Building 'vrf_documentation' collection...")
        
        doc_path = Path("data/knowledge/vrf_energyplus_documentation.json")
        
        if not doc_path.exists():
            print(f"  ❌ Not found: {doc_path}")
            print("  Skipping VRF documentation collection")
            return
        
        with open(doc_path, encoding='utf-8') as f:
            doc_data = json.load(f)
        
        # Create collection
        collection_name = f"vrf_documentation_v{self.version.replace('.', '_')}"
        try:
            self.client.delete_collection(collection_name)
        except:
            pass
        
        collection = self.client.create_collection(
            name=collection_name,
            embedding_function=self.embedding_fn,
            metadata={"description": "VRF EnergyPlus documentation and field specifications"}
        )
        
        documents = []
        metadatas = []
        ids = []
        
        # Add system overview
        overview = doc_data.get("vrf_system_overview", {})
        if overview:
            doc_text = f"""
VRF System Overview

Description: {overview.get('description', '')}

Key Features:
{chr(10).join('- ' + f for f in overview.get('key_features', []))}

Applications:
{chr(10).join('- ' + a for a in overview.get('applications', []))}

EnergyPlus Modeling: {overview.get('energyplus_modeling_approach', '')}
            """.strip()
            documents.append(doc_text)
            metadatas.append({"category": "overview", "object_type": "System:VRF"})
            ids.append("vrf_overview")
        
        # Add HVACTemplate:System:VRF detailed fields
        system_vrf = doc_data.get("hvactemplate_system_vrf", {})
        if system_vrf:
            for field in system_vrf.get("detailed_fields", []):
                doc_text = f"""
Field {field['field_number']}: {field['field_name']}
Object: HVACTemplate:System:VRF
Field ID: {field.get('field_id', 'N/A')}
Type: {field.get('type', 'N/A')}
Required: {field.get('required', False)}

Description: {field.get('description', '')}

Default: {field.get('default', 'None')}
{f"Typical Range: {field.get('typical_range', '')}" if field.get('typical_range') else ''}
{f"Units: {field.get('units', '')}" if field.get('units') else ''}
{f"Example: {field.get('example', '')}" if field.get('example') else ''}
{f"Notes: {field.get('notes', '')}" if field.get('notes') else ''}
{f"CRITICAL: {field.get('critical_dependency', '')}" if field.get('critical_dependency') else ''}
                """.strip()
                
                documents.append(doc_text)
                metadatas.append({
                    "category": "field_spec",
                    "object_type": "HVACTemplate:System:VRF",
                    "field_number": field['field_number'],
                    "field_name": field['field_name']
                })
                ids.append(f"system_vrf_field_{field['field_number']}")
            
            # Add common configurations
            for i, config in enumerate(system_vrf.get("common_configurations", [])):
                doc_text = f"""
VRF Configuration: {config['name']}
Description: {config['description']}

Key Settings:
{chr(10).join(f'- {k}: {v}' for k, v in config.get('key_settings', {}).items())}

{f"Benefits: {config.get('benefits', '')}" if config.get('benefits') else ''}
                """.strip()
                
                documents.append(doc_text)
                metadatas.append({"category": "configuration", "config_name": config['name']})
                ids.append(f"system_config_{i}")
        
        # Add HVACTemplate:Zone:VRF fields
        zone_vrf = doc_data.get("hvactemplate_zone_vrf", {})
        if zone_vrf:
            for field in zone_vrf.get("detailed_fields", []):
                doc_text = f"""
Field {field['field_number']}: {field['field_name']}
Object: HVACTemplate:Zone:VRF
Field ID: {field.get('field_id', 'N/A')}
Type: {field.get('type', 'N/A')}
Required: {field.get('required', False)}

Description: {field.get('description', '')}

Default: {field.get('default', 'None')}
{f"Example: {field.get('example', '')}" if field.get('example') else ''}
{f"Notes: {field.get('notes', '')}" if field.get('notes') else ''}
{f"CRITICAL: {field.get('critical', '')}" if field.get('critical') else ''}
                """.strip()
                
                documents.append(doc_text)
                metadatas.append({
                    "category": "field_spec",
                    "object_type": "HVACTemplate:Zone:VRF",
                    "field_number": field['field_number'],
                    "field_name": field['field_name']
                })
                ids.append(f"zone_vrf_field_{field['field_number']}")
        
        # Add thermostat documentation
        thermostat = doc_data.get("hvactemplate_thermostat", {})
        if thermostat:
            for field in thermostat.get("detailed_fields", []):
                doc_text = f"""
Field {field['field_number']}: {field['field_name']}
Object: HVACTemplate:Thermostat
Field ID: {field.get('field_id', 'N/A')}

Description: {field.get('description', '')}
Default: {field.get('default', 'None')}
{f"Typical Range: {field.get('typical_range', '')}" if field.get('typical_range') else ''}
{f"Example: {field.get('example', '')}" if field.get('example') else ''}
                """.strip()
                
                documents.append(doc_text)
                metadatas.append({
                    "category": "field_spec",
                    "object_type": "HVACTemplate:Thermostat",
                    "field_number": field['field_number'],
                    "field_name": field['field_name']
                })
                ids.append(f"thermostat_field_{field['field_number']}")
        
        # Add design guidance
        design = doc_data.get("design_guidance", {})
        if design:
            # System selection guidance
            selection = design.get("system_selection", {})
            if selection:
                doc_text = f"""
VRF System Selection Guidance

When to Use VRF:
{chr(10).join('- ' + w for w in selection.get('when_to_use_vrf', []))}

Alternatives to Consider:
{chr(10).join(f"- {alt['system']}: {alt['when']}" for alt in selection.get('alternatives_to_consider', []))}
                """.strip()
                
                documents.append(doc_text)
                metadatas.append({"category": "design_guidance", "topic": "system_selection"})
                ids.append("design_system_selection")
            
            # Sizing guidelines
            sizing = design.get("sizing_guidelines", {})
            if sizing:
                doc_text = f"""
VRF Sizing Guidelines

Cooling Capacity:
- Rule of thumb: {sizing.get('cooling_capacity', {}).get('rule_of_thumb', 'N/A')}
- Recommendation: {sizing.get('cooling_capacity', {}).get('recommendation', 'N/A')}

Heating Capacity:
- Sizing ratio: {sizing.get('heating_capacity', {}).get('sizing_ratio', 'N/A')}
- Cold climate: {sizing.get('heating_capacity', {}).get('cold_climate', 'N/A')}

Airflow:
- Cooling: {sizing.get('airflow', {}).get('cooling', 'N/A')}
- Heating: {sizing.get('airflow', {}).get('heating', 'N/A')}
                """.strip()
                
                documents.append(doc_text)
                metadatas.append({"category": "design_guidance", "topic": "sizing"})
                ids.append("design_sizing")
            
            # Climate considerations
            climate = design.get("climate_considerations", {})
            for climate_type, settings in climate.items():
                doc_text = f"""
VRF for {climate_type.replace('_', ' ').title()} Climate

Settings:
{chr(10).join(f'- {k}: {v}' for k, v in settings.items())}
                """.strip()
                
                documents.append(doc_text)
                metadatas.append({"category": "design_guidance", "topic": f"climate_{climate_type}"})
                ids.append(f"design_climate_{climate_type}")
        
        # Add common errors and solutions
        for i, error in enumerate(doc_data.get("common_errors_and_solutions", [])):
            doc_text = f"""
Common VRF Error: {error.get('error', 'Unknown')}

Cause: {error.get('cause', 'Unknown')}
Solution: {error.get('solution', 'Unknown')}
{f"Recommended Fix: {error.get('recommended_fix', '')}" if error.get('recommended_fix') else ''}
{f"Critical: {error.get('critical', '')}" if error.get('critical') else ''}
            """.strip()
            
            documents.append(doc_text)
            metadatas.append({"category": "error_solution", "error_index": i})
            ids.append(f"error_solution_{i}")
        
        # Add best practices
        for i, practice in enumerate(doc_data.get("best_practices", [])):
            doc_text = f"""
VRF Best Practice: {practice['practice']}

Reason: {practice['reason']}
Implementation: {practice['implementation']}
            """.strip()
            
            documents.append(doc_text)
            metadatas.append({"category": "best_practice", "practice_index": i})
            ids.append(f"best_practice_{i}")
        
        # Add to collection
        if documents:
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            print(f"  ✅ Added {len(documents)} VRF documentation chunks")
        else:
            print("  ⚠ No documentation extracted")

    def build_vrf_design_patterns_collection(self):
        """Build collection from VRF design patterns"""
        print("[9/9] Building 'vrf_design_patterns' collection...")
        
        pattern_path = Path("data/knowledge/vrf_design_patterns.json")
        
        if not pattern_path.exists():
            print(f"  ❌ Not found: {pattern_path}")
            print("  Skipping VRF design patterns collection")
            return
        
        with open(pattern_path, encoding='utf-8') as f:
            pattern_data = json.load(f)
        
        # Create collection
        collection_name = f"vrf_design_patterns_v{self.version.replace('.', '_')}"
        try:
            self.client.delete_collection(collection_name)
        except:
            pass
        
        collection = self.client.create_collection(
            name=collection_name,
            embedding_function=self.embedding_fn,
            metadata={"description": "VRF design patterns and real-world configurations"}
        )
        
        documents = []
        metadatas = []
        ids = []
        
        # Add design patterns
        for pattern in pattern_data.get("design_patterns", []):
            config = pattern.get("system_config", {})
            key_settings = pattern.get("key_settings", {})
            considerations = pattern.get("key_considerations", [])
            
            doc_text = f"""
VRF Design Pattern: {pattern['name']}
Pattern ID: {pattern['pattern_id']}

Description: {pattern['description']}

{f"Zones: {pattern.get('zones', 'Variable')}" if pattern.get('zones') else ''}
{f"Typical Area: {pattern.get('typical_area', '')}" if pattern.get('typical_area') else ''}
{f"Climate: {pattern.get('typical_climate', '')}" if pattern.get('typical_climate') else ''}

Use Cases:
{chr(10).join('- ' + uc for uc in pattern.get('use_cases', []))}

System Configuration:
{chr(10).join(f'- {k}: {v}' for k, v in config.items())}

{f"Key Settings:{chr(10)}{chr(10).join(f'- {k}: {v}' for k, v in key_settings.items())}" if key_settings else ''}

{f"Key Considerations:{chr(10)}{chr(10).join('- ' + c for c in considerations)}" if considerations else ''}
            """.strip()
            
            documents.append(doc_text)
            metadatas.append({
                "category": "design_pattern",
                "pattern_id": pattern['pattern_id'],
                "pattern_name": pattern['name']
            })
            ids.append(f"pattern_{pattern['pattern_id']}")
        
        # Add zone configurations
        for zone_type, config in pattern_data.get("zone_configurations", {}).items():
            doc_text = f"""
Zone Configuration: {zone_type.replace('_', ' ').title()}

Description: {config.get('description', '')}

Recommended Settings:
{chr(10).join(f'- {k}: {v}' for k, v in config.get('recommended_settings', {}).items())}
            """.strip()
            
            documents.append(doc_text)
            metadatas.append({"category": "zone_config", "zone_type": zone_type})
            ids.append(f"zone_config_{zone_type}")
        
        # Add COP guidelines
        cop = pattern_data.get("cop_guidelines", {})
        if cop:
            doc_text = f"""
VRF COP (Coefficient of Performance) Guidelines

Cooling COP:
- Minimum acceptable: {cop.get('cooling_cop', {}).get('minimum_acceptable', 'N/A')}
- Typical standard: {cop.get('cooling_cop', {}).get('typical_standard', 'N/A')}
- High efficiency: {cop.get('cooling_cop', {}).get('high_efficiency', 'N/A')}
- Premium: {cop.get('cooling_cop', {}).get('premium', 'N/A')}
Notes: {cop.get('cooling_cop', {}).get('notes', '')}

Heating COP:
- Minimum acceptable: {cop.get('heating_cop', {}).get('minimum_acceptable', 'N/A')}
- Typical standard: {cop.get('heating_cop', {}).get('typical_standard', 'N/A')}
- High efficiency: {cop.get('heating_cop', {}).get('high_efficiency', 'N/A')}
- Cold climate: {cop.get('heating_cop', {}).get('cold_climate', 'N/A')}
Notes: {cop.get('heating_cop', {}).get('notes', '')}
            """.strip()
            
            documents.append(doc_text)
            metadatas.append({"category": "cop_guidelines"})
            ids.append("cop_guidelines")
        
        # Add capacity guidelines
        capacity = pattern_data.get("capacity_guidelines", {})
        for building_type, values in capacity.items():
            doc_text = f"""
VRF Capacity Guidelines for {building_type.replace('_', ' ').title()}

Cooling: {values.get('cooling_watts_per_m2', 'N/A')} W/m²
Heating: {values.get('heating_watts_per_m2', 'N/A')} W/m²
            """.strip()
            
            documents.append(doc_text)
            metadatas.append({"category": "capacity_guidelines", "building_type": building_type})
            ids.append(f"capacity_{building_type}")
        
        # Add piping guidelines
        piping = pattern_data.get("piping_guidelines", {})
        if piping:
            doc_text = f"""
VRF Piping Guidelines

Equivalent Length:
- Small system: {piping.get('equivalent_length', {}).get('small_system', 'N/A')}
- Medium system: {piping.get('equivalent_length', {}).get('medium_system', 'N/A')}
- Large system: {piping.get('equivalent_length', {}).get('large_system', 'N/A')}
- Maximum: {piping.get('equivalent_length', {}).get('maximum', 'N/A')}

Vertical Height:
- Outdoor above indoor: {piping.get('vertical_height', {}).get('outdoor_above_indoor', 'N/A')}
- Indoor above outdoor: {piping.get('vertical_height', {}).get('indoor_above_outdoor', 'N/A')}
- Between indoor units: {piping.get('vertical_height', {}).get('between_indoor_units', 'N/A')}

Capacity Derating: {piping.get('capacity_derating', {}).get('typical_derating', 'N/A')}
            """.strip()
            
            documents.append(doc_text)
            metadatas.append({"category": "piping_guidelines"})
            ids.append("piping_guidelines")
        
        # Add troubleshooting guide
        for issue_type, guide in pattern_data.get("troubleshooting_guide", {}).items():
            doc_text = f"""
VRF Troubleshooting: {issue_type.replace('_', ' ').title()}

Symptoms:
{chr(10).join('- ' + s for s in guide.get('symptoms', []))}

Causes:
{chr(10).join('- ' + c for c in guide.get('causes', []))}

Solutions:
{chr(10).join('- ' + s for s in guide.get('solutions', []))}

{f"Recommended: {guide.get('recommended', '')}" if guide.get('recommended') else ''}
{f"Recommended Ranges: {guide.get('recommended_ranges', '')}" if guide.get('recommended_ranges') else ''}
            """.strip()
            
            documents.append(doc_text)
            metadatas.append({"category": "troubleshooting", "issue_type": issue_type})
            ids.append(f"troubleshoot_{issue_type}")
        
        # Add to collection
        if documents:
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            print(f"  ✅ Added {len(documents)} VRF design pattern chunks")
        else:
            print("  ⚠ No design patterns extracted")


# ========== MAIN: CLI Entry Point ==========

def main():
    """CLI entry point for knowledge base builder"""
    parser = argparse.ArgumentParser(
        description="Build HVAC-LLM knowledge base for RAG",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.rag.knowledge_builder
  python -m src.rag.knowledge_builder --version 25.2.0
  python -m src.rag.knowledge_builder --db-path data/vector_db_v25
        """
    )
    
    parser.add_argument(
        "--version",
        default="25.2.0",
        help="EnergyPlus version for version-aware indexing (default: 25.2.0)"
    )
    
    parser.add_argument(
        "--db-path",
        default="data/vector_db",
        help="Path to ChromaDB storage directory (default: data/vector_db)"
    )
    
    args = parser.parse_args()
    
    print("HVAC-LLM Knowledge Base Builder")
    print("=" * 70)
    print(f"EnergyPlus Version: {args.version}")
    print(f"Database Path: {args.db_path}\n")
    
    try:
        builder = KnowledgeBaseBuilder(
            db_path=args.db_path,
            energyplus_version=args.version
        )
        builder.build_all_collections()
        
        print("\n✅ Setup complete! Next steps:")
        print("1. Verify collections in ChromaDB")
        print("2. Test retrieval: python -m src.rag.rag_retriever")
        print("3. Integrate RAG into Agent 1 and Agent 3")
        
    except Exception as e:
        print(f"\n❌ Error building knowledge base: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())

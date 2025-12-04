"""
HVAC-LLM RAG Retriever

Query interface for agents to retrieve relevant context from vector database.
Used at runtime by Agent 1 (Generator) and Agent 3 (Corrector).

Usage:
    from src.rag.rag_retriever import RAGRetriever
    
    retriever = RAGRetriever()
    results = retriever.query_field_specs("heat recovery")
    results = retriever.query_error_patterns("Master Thermostat Location")
"""

import json
from pathlib import Path
from typing import Dict, List, Optional

try:
    import chromadb
    from chromadb.utils import embedding_functions
except ImportError:
    print("ERROR: chromadb not installed. Run: pip install chromadb")
    raise


class RAGRetriever:
    """Query interface for RAG knowledge base"""
    
    def __init__(self, db_path="data/vector_db", energyplus_version="25.2.0"):
        """
        Initialize RAG retriever.
        
        Args:
            db_path: Path to ChromaDB storage directory
            energyplus_version: EnergyPlus version for version-aware retrieval
        
        Raises:
            FileNotFoundError: If vector DB not found
        """
        self.db_path = Path(db_path)
        self.version = energyplus_version
        
        if not self.db_path.exists():
            raise FileNotFoundError(
                f"Vector DB not found at {self.db_path}. "
                f"Run 'python -m src.rag.knowledge_builder' first!"
            )
        
        # Load same embedding model as builder
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="BAAI/bge-small-en-v1.5"
        )
        
        # Connect to existing ChromaDB
        self.client = chromadb.PersistentClient(path=str(self.db_path))
        
        # Cache available collections
        self.available_collections = [col.name for col in self.client.list_collections()]
    
    def query_field_specs(
        self, 
        query_text: str, 
        n_results: int = 5,
        object_type: Optional[str] = None,
        category: Optional[str] = None
    ) -> Dict:
        """
        Query VRF field specifications.
        
        Args:
            query_text: Natural language query (e.g., "heat recovery fields")
            n_results: Number of results to return
            object_type: Filter by "HVACTemplate:System:VRF" or "HVACTemplate:Zone:VRF"
            category: Filter by "vrf_system" or "vrf_zone"
        
        Returns:
            dict with keys:
                - documents: List of field descriptions
                - metadatas: List of field metadata
                - distances: Similarity scores (lower = more similar)
        
        Example:
            results = retriever.query_field_specs(
                "supplemental heating for cold climate",
                n_results=3,
                object_type="HVACTemplate:System:VRF"
            )
        """
        # Try version-specific collection first
        collection_name = f"field_specs_v{self.version.replace('.', '_')}"
        
        if collection_name not in self.available_collections:
            # Fallback to latest available version
            version_collections = [
                c for c in self.available_collections 
                if c.startswith("field_specs_v")
            ]
            if version_collections:
                collection_name = version_collections[-1]  # Use latest
                print(f"⚠ Version {self.version} not found, using {collection_name}")
            else:
                raise ValueError("No field specs collection found in vector DB")
        
        collection = self.client.get_collection(
            name=collection_name,
            embedding_function=self.embedding_fn
        )
        
        # Build filter
        where_filter = {}
        if object_type:
            where_filter["object_type"] = object_type
        if category:
            where_filter["category"] = category
        
        results = collection.query(
            query_texts=[query_text],
            n_results=n_results,
            where=where_filter if where_filter else None
        )
        
        return results
    
    def query_error_patterns(
        self,
        error_text: str,
        n_results: int = 3,
        only_successful: bool = False  # Changed default to show all patterns
    ) -> Dict:
        """
        Query historical error-fix patterns.
        
        Args:
            error_text: Error message or description
            n_results: Number of similar errors to return
            only_successful: Only return patterns that led to successful fixes
        
        Returns:
            dict with similar error patterns and their fixes
        
        Example:
            results = retriever.query_error_patterns(
                "Master Thermostat Location must be entered",
                n_results=3
            )
            
            # Extract fix from top result
            if results['distances'][0][0] < 0.1:  # High similarity
                fix_field = results['metadatas'][0][0]['fix_field']
                fix_value = results['metadatas'][0][0]['fix_value']
        """
        if "error_patterns" not in self.available_collections:
            print("⚠ No error_patterns collection found")
            return {
                "documents": [[]],
                "metadatas": [[]],
                "distances": [[]]
            }
        
        collection = self.client.get_collection(
            name="error_patterns",
            embedding_function=self.embedding_fn
        )
        
        # Filter for successful fixes only (if requested)
        where_filter = {"success_after_fix": True} if only_successful else None
        
        results = collection.query(
            query_texts=[error_text],
            n_results=n_results,
            where=where_filter if where_filter else None  # None means no filtering
        )
        
        return results
    
    def query_design_rules(
        self,
        query_text: str,
        n_results: int = 3
    ) -> Dict:
        """
        Query design guidance documentation.
        
        Args:
            query_text: Design question or concept
            n_results: Number of relevant docs to return
        
        Returns:
            dict with relevant documentation chunks
        
        Example:
            results = retriever.query_design_rules(
                "when to use baseboard heating with VRF",
                n_results=2
            )
        """
        if "design_rules" not in self.available_collections:
            print("⚠ No design_rules collection found")
            return {
                "documents": [[]],
                "metadatas": [[]],
                "distances": [[]]
            }
        
        collection = self.client.get_collection(
            name="design_rules",
            embedding_function=self.embedding_fn
        )
        
        results = collection.query(
            query_texts=[query_text],
            n_results=n_results
        )
        
        return results
    
    def query_user_requests(
        self,
        user_request: str,
        n_results: int = 3
    ) -> List[Dict]:
        """
        Query user request examples for intent matching (Agent 1).
        Returns formatted list with similarity scores.
        
        Args:
            user_request: User's natural language request
            n_results: Number of similar examples to return
        
        Returns:
            List of dicts with keys: description, content, similarity
        """
        raw_results = self.query_user_request_examples(user_request, n_results)
        
        formatted = []
        if raw_results['documents'][0]:
            for doc, meta, dist in zip(
                raw_results['documents'][0],
                raw_results['metadatas'][0],
                raw_results['distances'][0]
            ):
                formatted.append({
                    'description': meta.get('description', 'N/A'),
                    'category': meta.get('category', 'unknown'),
                    'content': doc,
                    'similarity': 1 - dist
                })
        
        return formatted
    
    def query_field_dependencies(
        self,
        query: str,
        n_results: int = 5
    ) -> List[Dict]:
        """
        Query field dependency rules (Agent 1 and Agent 3).
        
        Args:
            query: Dependency query (e.g., "master thermostat requirements")
            n_results: Number of rules to return
        
        Returns:
            List of dicts with dependency rules
        """
        # Try version-specific collection first
        collection_name = f"field_dependencies_v{self.version.replace('.', '_')}"
        
        if collection_name not in self.available_collections:
            print("⚠ No field_dependencies collection found")
            return []
        
        collection = self.client.get_collection(
            name=collection_name,
            embedding_function=self.embedding_fn
        )
        
        results = collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        formatted = []
        if results['documents'][0]:
            for doc, meta, dist in zip(
                results['documents'][0],
                results['metadatas'][0],
                results['distances'][0]
            ):
                formatted.append({
                    'dependency_id': meta.get('dependency_id', 'N/A'),
                    'trigger_field': meta.get('trigger_field', 'N/A'),
                    'severity': meta.get('severity', 'Unknown'),
                    'frequency': meta.get('frequency', 'Unknown'),
                    'object_type': meta.get('object_type', 'N/A'),
                    'content': doc,
                    'similarity': 1 - dist
                })
        
        return formatted
    
    def query_error_fix_procedures(
        self,
        error_description: str,
        n_results: int = 3
    ) -> List[Dict]:
        """
        Query error fix procedures (Agent 3).
        Returns step-by-step fix procedures for common errors.
        
        Args:
            error_description: Error message or description
            n_results: Number of procedures to return
        
        Returns:
            List of dicts with fix procedures and similarity scores
        """
        if "error_fix_procedures" not in self.available_collections:
            print("⚠ No error_fix_procedures collection found")
            return []
        
        collection = self.client.get_collection(
            name="error_fix_procedures",
            embedding_function=self.embedding_fn
        )
        
        results = collection.query(
            query_texts=[error_description],
            n_results=n_results
        )
        
        formatted = []
        if results['documents'][0]:
            for doc, meta, dist in zip(
                results['documents'][0],
                results['metadatas'][0],
                results['distances'][0]
            ):
                formatted.append({
                    'error_id': meta.get('error_id', 'N/A'),
                    'error_pattern': meta.get('error_pattern', 'N/A'),
                    'severity': meta.get('severity', 'Unknown'),
                    'frequency': meta.get('frequency', 'Unknown'),
                    'content': doc,
                    'similarity': 1 - dist
                })
        
        return formatted
    
    def query_error_patterns(
        self,
        error_text: str = None,
        error_description: str = None,  # Alias for compatibility
        n_results: int = 3,
        only_successful: bool = False
    ) -> List[Dict]:
        """
        Query historical error-fix patterns (Agent 3).
        Updated to return formatted list for consistency.
        
        Args:
            error_text: Error message (legacy parameter)
            error_description: Error message (new parameter, takes precedence)
            n_results: Number of similar errors to return
            only_successful: Only return patterns that led to successful fixes
        
        Returns:
            List of dicts with error patterns and fixes
        """
        # Use error_description if provided, otherwise error_text
        query = error_description or error_text or ""
        
        if "error_patterns" not in self.available_collections:
            print("⚠ No error_patterns collection found")
            return []
        
        # First try error_fix_procedures (more detailed)
        procedures = self.query_error_fix_procedures(query, n_results)
        if procedures:
            return procedures
        
        # Fallback to historical error_patterns
        collection = self.client.get_collection(
            name="error_patterns",
            embedding_function=self.embedding_fn
        )
        
        where_filter = {"success_after_fix": True} if only_successful else None
        
        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where_filter if where_filter else None
        )
        
        formatted = []
        if results['documents'][0]:
            for doc, meta, dist in zip(
                results['documents'][0],
                results['metadatas'][0],
                results['distances'][0]
            ):
                formatted.append({
                    'error_id': meta.get('error_type', 'historical_pattern'),
                    'error_pattern': doc[:200],
                    'severity': meta.get('severity', 'Unknown'),
                    'fix_field': meta.get('fix_field', 'N/A'),
                    'fix_value': meta.get('fix_value', 'N/A'),
                    'content': doc,
                    'similarity': 1 - dist
                })
        
        return formatted
    
    def query_user_request_examples(
        self,
        query_text: str,
        n_results: int = 3
    ) -> Dict:
        """
        Query user request examples for few-shot learning.
        
        Args:
            query_text: User request description
            n_results: Number of similar examples to return
        
        Returns:
            dict with similar user request examples
        
        Example:
            results = retriever.query_user_request_examples(
                "Design VRF with heat recovery",
                n_results=2
            )
        """
        if "user_request_examples" not in self.available_collections:
            print("⚠ No user_request_examples collection found")
            return {
                "documents": [[]],
                "metadatas": [[]],
                "distances": [[]]
            }
        
        collection = self.client.get_collection(
            name="user_request_examples",
            embedding_function=self.embedding_fn
        )
        
        results = collection.query(
            query_texts=[query_text],
            n_results=n_results
        )
        
        return results
    
    def get_collection_stats(self) -> Dict[str, int]:
        """Get statistics about available collections"""
        stats = {}
        for col_name in self.available_collections:
            try:
                collection = self.client.get_collection(name=col_name)
                stats[col_name] = collection.count()
            except:
                stats[col_name] = 0
        return stats
    
    def format_field_context(self, results: Dict, max_fields: int = 5) -> str:
        """
        Format field specification results as context for LLM prompt.
        
        Args:
            results: Results from query_field_specs()
            max_fields: Maximum fields to include
        
        Returns:
            Formatted string for LLM prompt
        """
        if not results['documents'][0]:
            return ""
        
        context_parts = ["RELEVANT VRF FIELDS (from knowledge base):"]
        
        for i, (doc, meta) in enumerate(zip(
            results['documents'][0][:max_fields],
            results['metadatas'][0][:max_fields]
        )):
            field_num = meta.get('field_number', '?')
            field_name = meta.get('field_name', 'unknown')
            field_type = meta.get('field_type', 'unknown')
            
            context_parts.append(
                f"{field_num}. {field_name} ({field_type})"
            )
        
        return "\n".join(context_parts)
    
    def format_error_context(self, results: Dict, max_patterns: int = 3) -> str:
        """
        Format error pattern results as context for LLM prompt.
        
        Args:
            results: Results from query_error_patterns()
            max_patterns: Maximum patterns to include
        
        Returns:
            Formatted string for LLM prompt
        """
        if not results['documents'][0]:
            return ""
        
        context_parts = ["SIMILAR HISTORICAL ERRORS (from knowledge base):"]
        
        for i, (doc, meta) in enumerate(zip(
            results['documents'][0][:max_patterns],
            results['metadatas'][0][:max_patterns]
        )):
            fix_field = meta.get('fix_field', 'unknown')
            fix_value = meta.get('fix_value', 'unknown')
            similarity = 1 - results['distances'][0][i]  # Convert distance to similarity
            
            context_parts.append(
                f"{i+1}. Error: {doc[:100]}..."
            )
            context_parts.append(
                f"   Fix: {fix_field} = {fix_value} (similarity: {similarity:.2%})"
            )
        
        return "\n".join(context_parts)


# ========== TEST SCRIPT ==========

def main():
    """Test RAG retriever functionality"""
    print("=" * 70)
    print("TESTING HVAC-LLM RAG RETRIEVER")
    print("=" * 70 + "\n")
    
    try:
        retriever = RAGRetriever()
    except FileNotFoundError as e:
        print(f"❌ {e}")
        print("\nRun this first:")
        print("  python -m src.rag.knowledge_builder")
        return 1
    
    # Show collection stats
    print("Available Collections:")
    stats = retriever.get_collection_stats()
    for col_name, count in stats.items():
        print(f"  - {col_name}: {count} documents")
    
    print("\n" + "=" * 70)
    print("TEST 1: Query field specs for 'heat recovery'")
    print("=" * 70 + "\n")
    
    results = retriever.query_field_specs(
        "heat recovery waste heat",
        n_results=3
    )
    
    if results['documents'][0]:
        for i, (doc, meta, dist) in enumerate(zip(
            results['documents'][0],
            results['metadatas'][0],
            results['distances'][0]
        )):
            print(f"{i+1}. {doc}")
            print(f"   Field: {meta['field_name']} (#{meta['field_number']})")
            print(f"   Distance: {dist:.4f} (similarity: {1-dist:.2%})\n")
    else:
        print("No results found\n")
    
    print("=" * 70)
    print("TEST 2: Query error patterns for 'Master Thermostat'")
    print("=" * 70 + "\n")
    
    results = retriever.query_error_patterns(
        "Master Thermostat Location must be entered",
        n_results=2
    )
    
    if results['documents'][0]:
        for i, (doc, meta, dist) in enumerate(zip(
            results['documents'][0],
            results['metadatas'][0],
            results['distances'][0]
        )):
            print(f"{i+1}. Error: {doc[:80]}...")
            print(f"   Fix: {meta.get('fix_field', 'N/A')} = {meta.get('fix_value', 'N/A')}")
            print(f"   Success: {meta.get('success', False)}")
            print(f"   Distance: {dist:.4f}\n")
    else:
        print("No error patterns found (run pipeline to generate)\n")
    
    print("=" * 70)
    print("TEST 3: Format context for LLM")
    print("=" * 70 + "\n")
    
    field_results = retriever.query_field_specs("cold climate heating", n_results=3)
    context = retriever.format_field_context(field_results)
    print(context)
    
    print("\n" + "=" * 70)
    print("✅ RAG RETRIEVER TESTS COMPLETE")
    print("=" * 70)
    
    return 0


if __name__ == "__main__":
    exit(main())

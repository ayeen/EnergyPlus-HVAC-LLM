"""
RAG (Retrieval-Augmented Generation) Module for HVAC-LLM

This module provides:
- KnowledgeBaseBuilder: Extracts and indexes knowledge from existing project data
- RAGRetriever: Query interface for agents to retrieve relevant context
"""

from .knowledge_builder import KnowledgeBaseBuilder
from .rag_retriever import RAGRetriever

__all__ = ['KnowledgeBaseBuilder', 'RAGRetriever']

"""
Natural Language Processing module for knowledge extraction.
Includes spaCy integration for entity recognition and relationship extraction.
"""

from .spacy_extractor import SpacyExtractor
from .knowledge_extractor import KnowledgeExtractor
from .triplet_extractor import TripletExtractor
from .llm_extractor import LLMExtractor

__all__ = [
    'SpacyExtractor',
    'KnowledgeExtractor',
    'TripletExtractor',
    'LLMExtractor'
]
"""
Knowledge extraction orchestrator that coordinates multiple extraction methods.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from .spacy_extractor import SpacyExtractor, ExtractedEntity, ExtractedRelationship
from .llm_extractor import LLMExtractor
from config.settings import Config

logger = logging.getLogger(__name__)


class KnowledgeExtractor:
    """Orchestrates knowledge extraction from text using multiple methods."""

    def __init__(self, spacy_model: Optional[str] = None, use_llm: bool = False):
        """
        Initialize knowledge extractor.

        Args:
            spacy_model: spaCy model name
            use_llm: Whether to enable LLM-enhanced extraction
        """
        self.spacy_extractor = SpacyExtractor(model_name=spacy_model)
        self.use_llm = use_llm
        self.extraction_methods = ["spacy"]
        self.llm_extractor = None

        if use_llm:
            try:
                self.llm_extractor = LLMExtractor()
                if self.llm_extractor.is_available():
                    self.extraction_methods.append("llm")
                    logger.info("LLM-enhanced extraction enabled")
                else:
                    logger.warning("LLM extraction configured but not available. Check API key configuration.")
                    self.llm_extractor = None
                    # Don't silently fall back - throw error if LLM was requested but unavailable
                    raise ValueError("LLM 提取器不可用。请检查 API Key 配置是否正确。")
            except Exception as e:
                logger.error(f"Failed to initialize LLM extractor: {e}")
                self.llm_extractor = None
                # Re-raise the error so the caller knows LLM extraction failed
                raise

        logger.info(f"Initialized KnowledgeExtractor with methods: {self.extraction_methods}")

    def extract_from_text(self, text: str, document_id: Optional[str] = None,
                         extraction_methods: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Extract knowledge from text using specified methods.

        Args:
            text: Input text
            document_id: Optional document identifier
            extraction_methods: List of methods to use (default: all available)

        Returns:
            Dictionary with extraction results
        """
        if not text or not text.strip():
            return self._empty_result(document_id, text)

        extraction_methods = extraction_methods or self.extraction_methods
        start_time = datetime.now()

        # Collect results from all methods
        all_entities = []
        all_relationships = []
        all_triplets = []
        method_results = {}

        # spaCy extraction
        if "spacy" in extraction_methods:
            spacy_result = self._extract_with_spacy(text, document_id)
            method_results["spacy"] = spacy_result
            all_entities.extend(spacy_result.get("entities", []))
            all_relationships.extend(spacy_result.get("relationships", []))
            all_triplets.extend(spacy_result.get("triplets", []))

        # LLM extraction
        if "llm" in extraction_methods and self.use_llm:
            llm_result = self._extract_with_llm(text, document_id)
            method_results["llm"] = llm_result

            # Convert LLM entities to ExtractedEntity format
            llm_entities = llm_result.get("entities", [])
            for entity_dict in llm_entities:
                extracted_entity = ExtractedEntity(
                    text=entity_dict.get("text", ""),
                    entity_type=entity_dict.get("type", "OTHER"),
                    start_char=0,  # LLM doesn't provide position info
                    end_char=0,
                    confidence=entity_dict.get("confidence", 0.5),
                    metadata=entity_dict.get("metadata", {})
                )
                all_entities.append(extracted_entity)

            # Convert LLM relationships to ExtractedRelationship format
            llm_relationships = llm_result.get("relationships", [])
            for rel_dict in llm_relationships:
                subject_dict = rel_dict.get("subject", {})
                object_dict = rel_dict.get("object", {})

                subject_entity = ExtractedEntity(
                    text=subject_dict.get("text", ""),
                    entity_type=subject_dict.get("type", "ENTITY"),
                    start_char=0,
                    end_char=0,
                    confidence=subject_dict.get("confidence", 0.8),
                    metadata={}
                )

                object_entity = ExtractedEntity(
                    text=object_dict.get("text", ""),
                    entity_type=object_dict.get("type", "ENTITY"),
                    start_char=0,
                    end_char=0,
                    confidence=object_dict.get("confidence", 0.8),
                    metadata={}
                )

                extracted_relationship = ExtractedRelationship(
                    subject=subject_entity,
                    predicate=rel_dict.get("predicate", "related_to"),
                    object=object_entity,
                    confidence=rel_dict.get("confidence", 0.5),
                    context=rel_dict.get("context", ""),
                    metadata=rel_dict.get("metadata", {})
                )
                all_relationships.append(extracted_relationship)

            # Add LLM triplets
            all_triplets.extend(llm_result.get("triplets", []))

        # Deduplicate and merge results
        merged_entities = self._deduplicate_entities(all_entities)
        merged_relationships = self._deduplicate_relationships(all_relationships)
        merged_triplets = self._deduplicate_triplets(all_triplets)

        # Calculate statistics
        entity_types = self._count_entity_types(merged_entities)
        relationship_types = self._count_relationship_types(merged_relationships)

        processing_time = (datetime.now() - start_time).total_seconds()

        result = {
            "document_id": document_id,
            "entities": merged_entities,
            "relationships": merged_relationships,
            "triplets": merged_triplets,
            "statistics": {
                "total_entities": len(merged_entities),
                "total_relationships": len(merged_relationships),
                "total_triplets": len(merged_triplets),
                "entity_types": entity_types,
                "relationship_types": relationship_types,
                "processing_time_seconds": processing_time,
                "text_length": len(text),
                "word_count": len(text.split()),
                "extraction_methods": extraction_methods
            },
            "method_results": method_results,
            "timestamp": datetime.now().isoformat()
        }

        logger.info(f"Extracted knowledge from document {document_id or 'unknown'}: "
                   f"{len(merged_entities)} entities, {len(merged_relationships)} relationships, "
                   f"{len(merged_triplets)} triplets using methods {extraction_methods}")

        return result

    def _extract_with_spacy(self, text: str, document_id: Optional[str] = None) -> Dict[str, Any]:
        """Extract knowledge using spaCy."""
        return self.spacy_extractor.process_document(text, document_id)

    def _extract_with_llm(self, text: str, document_id: Optional[str] = None) -> Dict[str, Any]:
        """Extract knowledge using LLM."""
        if not self.llm_extractor:
            logger.warning("LLM extractor not available. Check API key configuration.")
            return self._empty_llm_result(document_id, text)

        try:
            logger.info(f"Starting LLM extraction for document {document_id or 'unknown'}")
            result = self.llm_extractor.process_document(text, document_id)
            logger.info(f"LLM extraction completed for document {document_id or 'unknown'}")
            return result
        except Exception as e:
            logger.error(f"Error during LLM extraction for document {document_id or 'unknown'}: {e}")
            return self._empty_llm_result(document_id, text, error=str(e))

    def _empty_result(self, document_id: Optional[str], text: str) -> Dict[str, Any]:
        """Return empty result for empty text."""
        return {
            "document_id": document_id,
            "entities": [],
            "relationships": [],
            "triplets": [],
            "statistics": {
                "total_entities": 0,
                "total_relationships": 0,
                "total_triplets": 0,
                "entity_types": {},
                "relationship_types": {},
                "processing_time_seconds": 0,
                "text_length": len(text),
                "word_count": len(text.split())
            },
            "timestamp": datetime.now().isoformat()
        }

    def _empty_llm_result(self, document_id: Optional[str], text: str, error: Optional[str] = None) -> Dict[str, Any]:
        """Return empty result for failed LLM extraction."""
        result = {
            "document_id": document_id,
            "entities": [],
            "relationships": [],
            "triplets": [],
            "statistics": {
                "total_entities": 0,
                "total_relationships": 0,
                "total_triplets": 0,
                "entity_types": {},
                "relationship_types": {},
                "processing_time_seconds": 0,
                "text_length": len(text),
                "word_count": len(text.split())
            },
            "timestamp": datetime.now().isoformat(),
            "method": "llm",
            "status": "failed"
        }
        if error:
            result["error"] = error
        return result

    def _deduplicate_entities(self, entities: List[ExtractedEntity]) -> List[ExtractedEntity]:
        """Deduplicate entities based on text and type."""
        unique_entities = {}
        for entity in entities:
            key = (entity.text.lower(), entity.entity_type)
            if key not in unique_entities:
                unique_entities[key] = entity
            else:
                # Keep the one with higher confidence
                existing = unique_entities[key]
                if entity.confidence > existing.confidence:
                    unique_entities[key] = entity

        return list(unique_entities.values())

    def _deduplicate_relationships(self, relationships: List[ExtractedRelationship]) -> List[ExtractedRelationship]:
        """Deduplicate relationships."""
        unique_relationships = {}
        for rel in relationships:
            key = (
                rel.subject.text.lower(),
                rel.predicate,
                rel.object.text.lower(),
                rel.subject.entity_type,
                rel.object.entity_type
            )
            if key not in unique_relationships:
                unique_relationships[key] = rel
            else:
                # Keep the one with higher confidence
                existing = unique_relationships[key]
                if rel.confidence > existing.confidence:
                    unique_relationships[key] = rel

        return list(unique_relationships.values())

    def _deduplicate_triplets(self, triplets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate triplets."""
        unique_triplets = {}
        for triplet in triplets:
            key = (
                triplet["subject"]["name"].lower(),
                triplet["predicate"],
                triplet["object"]["name"].lower(),
                triplet["subject"]["type"],
                triplet["object"]["type"]
            )
            if key not in unique_triplets:
                unique_triplets[key] = triplet
            else:
                # Keep the one with higher confidence
                existing = unique_triplets[key]
                if triplet.get("confidence", 0) > existing.get("confidence", 0):
                    unique_triplets[key] = triplet

        return list(unique_triplets.values())

    def _count_entity_types(self, entities: List[ExtractedEntity]) -> Dict[str, int]:
        """Count entities by type."""
        counts = {}
        for entity in entities:
            counts[entity.entity_type] = counts.get(entity.entity_type, 0) + 1
        return counts

    def _count_relationship_types(self, relationships: List[ExtractedRelationship]) -> Dict[str, int]:
        """Count relationships by type."""
        counts = {}
        for rel in relationships:
            counts[rel.predicate] = counts.get(rel.predicate, 0) + 1
        return counts

    def batch_extract(self, texts: List[str], document_ids: Optional[List[str]] = None,
                     extraction_methods: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Extract knowledge from multiple texts.

        Args:
            texts: List of texts
            document_ids: Optional list of document identifiers
            extraction_methods: List of extraction methods to use

        Returns:
            List of extraction results
        """
        results = []
        for i, text in enumerate(texts):
            doc_id = document_ids[i] if document_ids and i < len(document_ids) else f"doc_{i}"
            try:
                result = self.extract_from_text(text, doc_id, extraction_methods)
                results.append(result)
            except Exception as e:
                logger.error(f"Error extracting knowledge from document {doc_id}: {e}")
                results.append(self._empty_result(doc_id, text))
                results[-1]["error"] = str(e)

        return results

    def get_extraction_statistics(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate aggregate statistics across multiple extraction results.

        Args:
            results: List of extraction results

        Returns:
            Aggregate statistics
        """
        total_entities = 0
        total_relationships = 0
        total_triplets = 0
        total_processing_time = 0
        entity_type_counts = {}
        relationship_type_counts = {}

        successful = 0
        failed = 0

        for result in results:
            if "error" not in result:
                successful += 1
                stats = result.get("statistics", {})
                total_entities += stats.get("total_entities", 0)
                total_relationships += stats.get("total_relationships", 0)
                total_triplets += stats.get("total_triplets", 0)
                total_processing_time += stats.get("processing_time_seconds", 0)

                # Aggregate entity type counts
                for entity_type, count in stats.get("entity_types", {}).items():
                    entity_type_counts[entity_type] = entity_type_counts.get(entity_type, 0) + count

                # Aggregate relationship type counts
                for rel_type, count in stats.get("relationship_types", {}).items():
                    relationship_type_counts[rel_type] = relationship_type_counts.get(rel_type, 0) + count
            else:
                failed += 1

        avg_processing_time = total_processing_time / max(1, successful)

        return {
            "total_documents": len(results),
            "successful_documents": successful,
            "failed_documents": failed,
            "total_entities": total_entities,
            "total_relationships": total_relationships,
            "total_triplets": total_triplets,
            "avg_entities_per_document": total_entities / max(1, successful),
            "avg_relationships_per_document": total_relationships / max(1, successful),
            "avg_triplets_per_document": total_triplets / max(1, successful),
            "avg_processing_time_seconds": avg_processing_time,
            "entity_type_distribution": entity_type_counts,
            "relationship_type_distribution": relationship_type_counts,
            "timestamp": datetime.now().isoformat()
        }
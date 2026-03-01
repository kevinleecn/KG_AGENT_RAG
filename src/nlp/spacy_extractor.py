"""
spaCy-based NLP extractor for entity recognition and relationship extraction.
"""

import spacy
import spacy.cli
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from config.settings import Config

logger = logging.getLogger(__name__)


@dataclass
class ExtractedEntity:
    """Represents an extracted entity from text."""
    text: str
    entity_type: str
    start_char: int
    end_char: int
    confidence: float
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ExtractedRelationship:
    """Represents an extracted relationship between entities."""
    subject: ExtractedEntity
    predicate: str
    object: ExtractedEntity
    confidence: float
    context: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class SpacyExtractor:
    """spaCy-based NLP extractor for knowledge extraction."""

    def __init__(self, model_name: Optional[str] = None, disable_components: List[str] = None):
        """
        Initialize spaCy extractor.

        Args:
            model_name: Name of spaCy model to load (default: from config)
            disable_components: List of pipeline components to disable for speed
        """
        self.model_name = model_name or Config.SPACY_MODEL
        self.disable_components = disable_components or ["parser"]

        # Load spaCy model
        self.nlp = self._load_model()

        # Entity type mappings (customize based on your needs)
        self.entity_type_mappings = {
            "PERSON": "PERSON",
            "PER": "PERSON",
            "ORG": "ORGANIZATION",
            "GPE": "LOCATION",
            "LOC": "LOCATION",
            "DATE": "DATE",
            "TIME": "TIME",
            "MONEY": "MONEY",
            "PRODUCT": "PRODUCT",
            "EVENT": "EVENT",
            "NORP": "GROUP",  # Nationalities, religious or political groups
            "FAC": "FACILITY",  # Buildings, airports, highways
            "WORK_OF_ART": "WORK_OF_ART",
        }

        # Relationship patterns (subject-predicate-object patterns)
        self.relationship_patterns = [
            # Person -> works at -> Organization
            {"subject_types": ["PERSON"], "predicate": "works_at", "object_types": ["ORGANIZATION"]},
            # Person -> located in -> Location
            {"subject_types": ["PERSON"], "predicate": "located_in", "object_types": ["LOCATION"]},
            # Organization -> based in -> Location
            {"subject_types": ["ORGANIZATION"], "predicate": "based_in", "object_types": ["LOCATION"]},
            # Person -> part of -> Organization
            {"subject_types": ["PERSON"], "predicate": "part_of", "object_types": ["ORGANIZATION"]},
            # Generic relationships
            {"subject_types": ["PERSON", "ORGANIZATION"], "predicate": "related_to", "object_types": ["PERSON", "ORGANIZATION"]},
        ]

        logger.info(f"Initialized SpacyExtractor with model: {self.model_name}")

    def _load_model(self):
        """Load spaCy model with error handling."""
        try:
            logger.info(f"Loading spaCy model: {self.model_name}")
            nlp = spacy.load(self.model_name, disable=self.disable_components)

            # Add custom pipeline components if needed
            if "ner" not in self.disable_components and "ner" not in nlp.pipe_names:
                logger.warning(f"NER component not available in model {self.model_name}")

            return nlp
        except OSError as e:
            logger.error(f"Failed to load spaCy model {self.model_name}: {e}")
            logger.info("Attempting to download the model...")
            try:
                # Use spaCy's API to download the model
                spacy.cli.download(self.model_name)
                nlp = spacy.load(self.model_name, disable=self.disable_components)
                logger.info(f"Successfully downloaded and loaded model: {self.model_name}")
                return nlp
            except Exception as download_error:
                logger.error(f"Failed to download model: {download_error}")
                # Fallback to blank model
                logger.info("Creating blank model as fallback")
                nlp = spacy.blank("xx")
                return nlp

    def _clean_text(self, text: str) -> str:
        """
        Clean and normalize text for processing.

        Args:
            text: Input text

        Returns:
            Cleaned text
        """
        if not text:
            return ""

        # Remove null characters and excessive whitespace
        import re
        text = re.sub(r'\x00', '', text)  # Remove null bytes
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        text = text.strip()

        return text

    def extract_entities(self, text: str) -> List[ExtractedEntity]:
        """
        Extract entities from text using spaCy NER.

        Args:
            text: Input text to process

        Returns:
            List of extracted entities
        """
        if not text or not text.strip():
            return []

        # Input validation and cleaning
        text = self._clean_text(text)

        # Limit text length to prevent performance issues
        max_text_length = 1000000  # 1MB characters
        if len(text) > max_text_length:
            logger.warning(f"Text too long ({len(text)} chars), truncating to {max_text_length}")
            text = text[:max_text_length]

        try:
            doc = self.nlp(text)

            entities = []
            for ent in doc.ents:
                # Map spaCy entity type to standardized type
                entity_type = self.entity_type_mappings.get(ent.label_, ent.label_)

                # Calculate confidence (simplified - spaCy doesn't provide confidence scores)
                confidence = 0.8  # Default confidence for spaCy NER

                extracted_entity = ExtractedEntity(
                    text=ent.text,
                    entity_type=entity_type,
                    start_char=ent.start_char,
                    end_char=ent.end_char,
                    confidence=confidence,
                    metadata={
                        "spacy_label": ent.label_,
                        "spacy_label_id": ent.label,
                        "lemma": ent.lemma_ if hasattr(ent, 'lemma_') else ent.text,
                        "is_oov": ent.is_oov if hasattr(ent, 'is_oov') else False,
                        "ent_id": ent.ent_id_ if hasattr(ent, 'ent_id_') else None,
                    }
                )
                entities.append(extracted_entity)

            logger.debug(f"Extracted {len(entities)} entities from text")
            return entities

        except Exception as e:
            logger.error(f"Error extracting entities: {e}")
            return []

    def extract_relationships(self, text: str, entities: Optional[List[ExtractedEntity]] = None) -> List[ExtractedRelationship]:
        """
        Extract relationships between entities.

        Args:
            text: Input text
            entities: Pre-extracted entities (if None, will extract them)

        Returns:
            List of extracted relationships
        """
        if not text or not text.strip():
            return []

        # Extract entities if not provided
        if entities is None:
            entities = self.extract_entities(text)

        if len(entities) < 2:
            return []

        try:
            doc = self.nlp(text)
            relationships = []

            # Simple co-occurrence based relationship extraction
            # Entities that appear close to each other in text might be related
            for i, subject_entity in enumerate(entities):
                for j, object_entity in enumerate(entities):
                    if i == j:
                        continue

                    # Check if entities are close in text (within 200 characters)
                    distance = abs(subject_entity.start_char - object_entity.start_char)
                    if distance > 200:
                        continue

                    # Extract context between entities
                    start = min(subject_entity.end_char, object_entity.end_char)
                    end = max(subject_entity.start_char, object_entity.start_char)
                    if start < end:
                        context = text[start:end]
                    else:
                        context = ""

                    # Determine relationship type based on entity types and context
                    predicate = self._infer_relationship(
                        subject_entity, object_entity, context
                    )

                    if predicate:
                        # Calculate confidence based on distance and context
                        confidence = self._calculate_relationship_confidence(
                            subject_entity, object_entity, context, distance
                        )

                        relationship = ExtractedRelationship(
                            subject=subject_entity,
                            predicate=predicate,
                            object=object_entity,
                            confidence=confidence,
                            context=context,
                            metadata={
                                "distance": distance,
                                "extraction_method": "co-occurrence",
                                "timestamp": datetime.now().isoformat()
                            }
                        )
                        relationships.append(relationship)

            logger.debug(f"Extracted {len(relationships)} relationships from text")
            return relationships

        except Exception as e:
            logger.error(f"Error extracting relationships: {e}")
            return []

    def _infer_relationship(self, subject: ExtractedEntity, object: ExtractedEntity, context: str) -> Optional[str]:
        """
        Infer relationship type based on entity types and context.

        Args:
            subject: Subject entity
            object: Object entity
            context: Text context between entities

        Returns:
            Predicate string or None if no relationship inferred
        """
        # Check against predefined patterns
        for pattern in self.relationship_patterns:
            if (subject.entity_type in pattern["subject_types"] and
                object.entity_type in pattern["object_types"]):
                return pattern["predicate"]

        # Check context for common relationship indicators
        context_lower = context.lower()

        relationship_keywords = {
            "works at": "works_at",
            "employed by": "works_at",
            "employee of": "works_at",
            "located in": "located_in",
            "based in": "based_in",
            "headquartered in": "based_in",
            "founder of": "founder_of",
            "ceo of": "ceo_of",
            "director of": "director_of",
            "manager of": "manager_of",
            "member of": "member_of",
            "part of": "part_of",
            "belongs to": "part_of",
            "related to": "related_to",
            "associated with": "associated_with",
            "partner of": "partner_of",
            "competitor of": "competitor_of",
            "customer of": "customer_of",
            "supplier of": "supplier_of",
        }

        for keyword, relationship in relationship_keywords.items():
            if keyword in context_lower:
                return relationship

        return None

    def _calculate_relationship_confidence(self, subject: ExtractedEntity, object: ExtractedEntity,
                                          context: str, distance: int) -> float:
        """
        Calculate confidence score for a relationship.

        Args:
            subject: Subject entity
            object: Object entity
            context: Context text
            distance: Character distance between entities

        Returns:
            Confidence score between 0 and 1
        """
        base_confidence = 0.5

        # Adjust based on distance (closer = higher confidence)
        distance_factor = max(0, 1 - (distance / 500))  # Normalize to 0-500 chars
        base_confidence += distance_factor * 0.3

        # Adjust based on context keywords
        context_keywords = ["works", "based", "located", "founder", "ceo", "director",
                           "manager", "member", "part", "belongs", "related", "associated"]
        context_lower = context.lower()
        keyword_count = sum(1 for keyword in context_keywords if keyword in context_lower)
        if keyword_count > 0:
            base_confidence += min(0.2, keyword_count * 0.05)

        # Adjust based on entity confidence
        entity_confidence = (subject.confidence + object.confidence) / 2
        base_confidence = (base_confidence + entity_confidence) / 2

        return min(1.0, max(0.0, base_confidence))

    def extract_triplets(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract subject-predicate-object triplets from text.

        Args:
            text: Input text

        Returns:
            List of triplets in standardized format
        """
        entities = self.extract_entities(text)
        relationships = self.extract_relationships(text, entities)

        triplets = []
        for rel in relationships:
            triplet = {
                "subject": {
                    "name": rel.subject.text,
                    "type": rel.subject.entity_type,
                    "properties": rel.subject.metadata
                },
                "predicate": rel.predicate,
                "object": {
                    "name": rel.object.text,
                    "type": rel.object.entity_type,
                    "properties": rel.object.metadata
                },
                "confidence": rel.confidence,
                "metadata": {
                    "context": rel.context,
                    "extraction_method": "spacy_cooccurrence",
                    "timestamp": datetime.now().isoformat()
                }
            }
            triplets.append(triplet)

        logger.info(f"Extracted {len(triplets)} triplets from text")
        return triplets

    def process_document(self, text: str, document_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a document and extract all knowledge.

        Args:
            text: Document text
            document_id: Optional document identifier

        Returns:
            Dictionary with extraction results
        """
        start_time = datetime.now()

        entities = self.extract_entities(text)
        relationships = self.extract_relationships(text, entities)
        triplets = self.extract_triplets(text)

        # Group entities by type for statistics
        entity_types = {}
        for entity in entities:
            entity_type = entity.entity_type
            entity_types[entity_type] = entity_types.get(entity_type, 0) + 1

        # Group relationships by type
        relationship_types = {}
        for rel in relationships:
            rel_type = rel.predicate
            relationship_types[rel_type] = relationship_types.get(rel_type, 0) + 1

        processing_time = (datetime.now() - start_time).total_seconds()

        result = {
            "document_id": document_id,
            "entities": entities,
            "relationships": relationships,
            "triplets": triplets,
            "statistics": {
                "total_entities": len(entities),
                "total_relationships": len(relationships),
                "total_triplets": len(triplets),
                "entity_types": entity_types,
                "relationship_types": relationship_types,
                "processing_time_seconds": processing_time,
                "text_length": len(text),
                "word_count": len(text.split())
            },
            "timestamp": datetime.now().isoformat()
        }

        logger.info(f"Processed document {document_id or 'unknown'}: "
                   f"{len(entities)} entities, {len(relationships)} relationships, "
                   f"{len(triplets)} triplets in {processing_time:.2f}s")

        return result

    def batch_process(self, texts: List[str], document_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Process multiple texts in batch.

        Args:
            texts: List of texts to process
            document_ids: Optional list of document identifiers

        Returns:
            List of processing results
        """
        results = []
        for i, text in enumerate(texts):
            doc_id = document_ids[i] if document_ids and i < len(document_ids) else f"doc_{i}"
            try:
                result = self.process_document(text, doc_id)
                results.append(result)
            except Exception as e:
                logger.error(f"Error processing document {doc_id}: {e}")
                results.append({
                    "document_id": doc_id,
                    "error": str(e),
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
                })

        return results
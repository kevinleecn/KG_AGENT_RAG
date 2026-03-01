"""
Triplet extraction and formatting for knowledge graph construction.
Converts NLP extraction results to standardized triplet format for graph building.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from .spacy_extractor import ExtractedEntity, ExtractedRelationship

logger = logging.getLogger(__name__)


class TripletExtractor:
    """Converts extraction results to standardized triplet format."""

    @staticmethod
    def entities_to_triplet_format(entities: List[ExtractedEntity]) -> List[Dict[str, Any]]:
        """
        Convert entities to basic triplet format (entity-IS_A-type).

        Args:
            entities: List of extracted entities

        Returns:
            List of triplets in standardized format
        """
        triplets = []
        for entity in entities:
            triplet = {
                "subject": {
                    "name": entity.text,
                    "type": entity.entity_type,
                    "properties": entity.metadata.copy()
                },
                "predicate": "is_a",
                "object": {
                    "name": entity.entity_type,
                    "type": "ENTITY_TYPE",
                    "properties": {}
                },
                "confidence": entity.confidence,
                "metadata": {
                    "extraction_method": "entity_type_assignment",
                    "timestamp": datetime.now().isoformat()
                }
            }
            triplets.append(triplet)
        return triplets

    @staticmethod
    def relationships_to_triplet_format(relationships: List[ExtractedRelationship]) -> List[Dict[str, Any]]:
        """
        Convert relationships to triplet format.

        Args:
            relationships: List of extracted relationships

        Returns:
            List of triplets in standardized format
        """
        triplets = []
        for rel in relationships:
            triplet = {
                "subject": {
                    "name": rel.subject.text,
                    "type": rel.subject.entity_type,
                    "properties": rel.subject.metadata.copy()
                },
                "predicate": rel.predicate,
                "object": {
                    "name": rel.object.text,
                    "type": rel.object.entity_type,
                    "properties": rel.object.metadata.copy()
                },
                "confidence": rel.confidence,
                "metadata": {
                    "context": rel.context,
                    "extraction_method": "relationship_extraction",
                    "timestamp": datetime.now().isoformat()
                }
            }
            if rel.metadata:
                triplet["metadata"].update(rel.metadata)
            triplets.append(triplet)
        return triplets

    @staticmethod
    def spacy_result_to_triplets(spacy_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Convert spaCy extraction result to triplets.

        Args:
            spacy_result: Result from SpacyExtractor.process_document()

        Returns:
            List of triplets in standardized format
        """
        triplets = []

        # Add entity type triplets
        entities = spacy_result.get("entities", [])
        entity_triplets = TripletExtractor.entities_to_triplet_format(entities)
        triplets.extend(entity_triplets)

        # Add relationship triplets
        relationships = spacy_result.get("relationships", [])
        relationship_triplets = TripletExtractor.relationships_to_triplet_format(relationships)
        triplets.extend(relationship_triplets)

        # If triplets are already in the result, add them too (might be different format)
        existing_triplets = spacy_result.get("triplets", [])
        for triplet in existing_triplets:
            # Ensure the triplet is in the correct format
            standardized = TripletExtractor.standardize_triplet(triplet)
            triplets.append(standardized)

        logger.debug(f"Converted spaCy result to {len(triplets)} triplets")
        return triplets

    @staticmethod
    def knowledge_extractor_result_to_triplets(knowledge_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Convert knowledge extractor result to triplets.

        Args:
            knowledge_result: Result from KnowledgeExtractor.extract_from_text()

        Returns:
            List of triplets in standardized format
        """
        triplets = []

        # Process each method's results
        method_results = knowledge_result.get("method_results", {})
        for method_name, method_result in method_results.items():
            if method_name == "spacy":
                method_triplets = TripletExtractor.spacy_result_to_triplets(method_result)
                for triplet in method_triplets:
                    triplet["metadata"]["source_method"] = method_name
                triplets.extend(method_triplets)
            elif method_name == "llm":
                # Handle LLM results when implemented
                llm_triplets = method_result.get("triplets", [])
                for triplet in llm_triplets:
                    standardized = TripletExtractor.standardize_triplet(triplet)
                    standardized["metadata"]["source_method"] = method_name
                    triplets.append(standardized)

        # Deduplicate triplets
        triplets = TripletExtractor.deduplicate_triplets(triplets)

        logger.debug(f"Converted knowledge extractor result to {len(triplets)} triplets")
        return triplets

    @staticmethod
    def standardize_triplet(triplet: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ensure a triplet is in the standardized format.

        Args:
            triplet: Input triplet in any format

        Returns:
            Triplet in standardized format
        """
        standardized = triplet.copy()

        # Ensure subject is in correct format
        if "subject" not in standardized:
            raise ValueError("Triplet missing 'subject' field")

        if isinstance(standardized["subject"], dict):
            subject = standardized["subject"]
            if "properties" not in subject:
                subject["properties"] = {}
        else:
            # Convert string subject to dict format
            standardized["subject"] = {
                "name": str(standardized["subject"]),
                "type": "ENTITY",
                "properties": {}
            }

        # Ensure object is in correct format
        if "object" not in standardized:
            raise ValueError("Triplet missing 'object' field")

        if isinstance(standardized["object"], dict):
            obj = standardized["object"]
            if "properties" not in obj:
                obj["properties"] = {}
        else:
            # Convert string object to dict format
            standardized["object"] = {
                "name": str(standardized["object"]),
                "type": "ENTITY",
                "properties": {}
            }

        # Ensure predicate is string
        if "predicate" not in standardized:
            standardized["predicate"] = "related_to"

        # Ensure confidence
        if "confidence" not in standardized:
            standardized["confidence"] = 0.5

        # Ensure metadata
        if "metadata" not in standardized:
            standardized["metadata"] = {}
        if "timestamp" not in standardized["metadata"]:
            standardized["metadata"]["timestamp"] = datetime.now().isoformat()

        return standardized

    @staticmethod
    def deduplicate_triplets(triplets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Deduplicate triplets based on subject, predicate, object.

        Args:
            triplets: List of triplets

        Returns:
            Deduplicated list
        """
        unique_triplets = {}
        for triplet in triplets:
            # Create a unique key
            subject_name = triplet["subject"].get("name", "").lower().strip()
            predicate = triplet["predicate"].lower().strip()
            object_name = triplet["object"].get("name", "").lower().strip()

            # Include types in key to distinguish "Apple" (company) vs "Apple" (fruit)
            subject_type = triplet["subject"].get("type", "").lower().strip()
            object_type = triplet["object"].get("type", "").lower().strip()

            key = (subject_name, subject_type, predicate, object_name, object_type)

            if key not in unique_triplets:
                unique_triplets[key] = triplet
            else:
                # Keep the one with higher confidence
                existing = unique_triplets[key]
                existing_conf = existing.get("confidence", 0)
                new_conf = triplet.get("confidence", 0)
                if new_conf > existing_conf:
                    unique_triplets[key] = triplet

        return list(unique_triplets.values())

    @staticmethod
    def filter_triplets_by_confidence(triplets: List[Dict[str, Any]],
                                     min_confidence: float = 0.5) -> List[Dict[str, Any]]:
        """
        Filter triplets by confidence threshold.

        Args:
            triplets: List of triplets
            min_confidence: Minimum confidence score

        Returns:
            Filtered list
        """
        return [t for t in triplets if t.get("confidence", 0) >= min_confidence]

    @staticmethod
    def group_triplets_by_predicate(triplets: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group triplets by predicate.

        Args:
            triplets: List of triplets

        Returns:
            Dictionary mapping predicates to triplets
        """
        groups = {}
        for triplet in triplets:
            predicate = triplet["predicate"]
            if predicate not in groups:
                groups[predicate] = []
            groups[predicate].append(triplet)
        return groups

    @staticmethod
    def create_graph_builder_input(triplets: List[Dict[str, Any]],
                                  source_document: str) -> List[Dict[str, Any]]:
        """
        Prepare triplets for graph_builder.build_graph_from_triplets().

        Args:
            triplets: List of triplets in standardized format
            source_document: Source document identifier

        Returns:
            List of triplets in graph_builder format
        """
        graph_triplets = []
        for triplet in triplets:
            graph_triplet = {
                "subject": {
                    "name": triplet["subject"]["name"],
                    "type": triplet["subject"]["type"],
                    "properties": triplet["subject"]["properties"].copy()
                },
                "predicate": triplet["predicate"],
                "object": {
                    "name": triplet["object"]["name"],
                    "type": triplet["object"]["type"],
                    "properties": triplet["object"]["properties"].copy()
                },
                "confidence": triplet["confidence"],
                "metadata": {
                    "source_document": source_document,
                    "extraction_timestamp": datetime.now().isoformat()
                }
            }
            # Merge additional metadata
            if "metadata" in triplet:
                graph_triplet["metadata"].update(triplet["metadata"])

            graph_triplets.append(graph_triplet)

        return graph_triplets

    @staticmethod
    def extract_entities_from_triplets(triplets: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """
        Extract unique entities from triplets.

        Args:
            triplets: List of triplets

        Returns:
            List of unique entities
        """
        entities = {}
        for triplet in triplets:
            subject = triplet["subject"]
            obj = triplet["object"]

            subject_key = (subject["name"], subject["type"])
            if subject_key not in entities:
                entities[subject_key] = {
                    "name": subject["name"],
                    "type": subject["type"],
                    "properties": subject.get("properties", {})
                }

            object_key = (obj["name"], obj["type"])
            if object_key not in entities:
                entities[object_key] = {
                    "name": obj["name"],
                    "type": obj["type"],
                    "properties": obj.get("properties", {})
                }

        return list(entities.values())
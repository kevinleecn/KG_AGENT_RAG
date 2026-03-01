"""
Graph builder for converting extracted knowledge into graph database entities and relationships.
"""

import uuid
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from .graph_database import GraphDatabase, Entity, Relationship
from .neo4j_adapter import Neo4jAdapter

logger = logging.getLogger(__name__)


class GraphBuilder:
    """Builds knowledge graph from extracted entities and relationships."""

    def __init__(self, graph_db: Optional[GraphDatabase] = None):
        """
        Initialize graph builder.

        Args:
            graph_db: Graph database instance (default: creates Neo4jAdapter)
        """
        print("[GRAPH BUILDER] Initializing GraphBuilder")
        self.graph_db = graph_db or Neo4jAdapter()
        print(f"[GRAPH BUILDER] graph_db type: {type(self.graph_db)}")

        # Connect if not already connected
        if not hasattr(self.graph_db, 'connected') or not self.graph_db.connected:
            print("[GRAPH BUILDER] Connecting to graph database...")
            self.graph_db.connect()

        print(f"[GRAPH BUILDER] Connected: {self.graph_db.connected}")

        # ID generators for entities and relationships
        self.entity_id_prefix = "ent_"
        self.relationship_id_prefix = "rel_"

    def generate_entity_id(self, entity_name: str, entity_type: str) -> str:
        """Generate a unique ID for an entity."""
        # Create a deterministic ID based on name and type
        base_str = f"{entity_type}_{entity_name}".lower().replace(" ", "_")
        # Add UUID to ensure uniqueness
        unique_suffix = str(uuid.uuid4())[:8]
        return f"{self.entity_id_prefix}{base_str[:50]}_{unique_suffix}"

    def generate_relationship_id(self, source_id: str, target_id: str, rel_type: str) -> str:
        """Generate a unique ID for a relationship."""
        base_str = f"{source_id}_{rel_type}_{target_id}".lower()
        unique_suffix = str(uuid.uuid4())[:8]
        return f"{self.relationship_id_prefix}{base_str[:100]}_{unique_suffix}"

    def create_entity_from_extraction(self,
                                     entity_name: str,
                                     entity_type: str,
                                     properties: Optional[Dict[str, Any]] = None,
                                     source_document: Optional[str] = None,
                                     confidence: Optional[float] = None) -> Entity:
        """
        Create an Entity object from extraction results.

        Args:
            entity_name: Name of the entity
            entity_type: Type of entity (PERSON, ORGANIZATION, etc.)
            properties: Additional properties
            source_document: Source document filename
            confidence: Extraction confidence score

        Returns:
            Entity object
        """
        entity_id = self.generate_entity_id(entity_name, entity_type)

        entity_properties = properties or {}
        entity_properties.update({
            "original_name": entity_name,
            "normalized_name": self._normalize_entity_name(entity_name),
            "extraction_timestamp": datetime.now().isoformat()
        })

        return Entity(
            id=entity_id,
            name=entity_name,
            entity_type=entity_type,
            properties=entity_properties,
            source_document=source_document,
            confidence=confidence,
            created_at=datetime.now()
        )

    def create_relationship_from_extraction(self,
                                           source_entity: Entity,
                                           target_entity: Entity,
                                           relationship_type: str,
                                           properties: Optional[Dict[str, Any]] = None,
                                           source_document: Optional[str] = None,
                                           confidence: Optional[float] = None) -> Relationship:
        """
        Create a Relationship object from extraction results.

        Args:
            source_entity: Source entity object
            target_entity: Target entity object
            relationship_type: Type of relationship
            properties: Additional properties
            source_document: Source document filename
            confidence: Extraction confidence score

        Returns:
            Relationship object
        """
        relationship_id = self.generate_relationship_id(
            source_entity.id,
            target_entity.id,
            relationship_type
        )

        rel_properties = properties or {}
        rel_properties.update({
            "extraction_timestamp": datetime.now().isoformat(),
            "source_entity_name": source_entity.name,
            "target_entity_name": target_entity.name
        })

        return Relationship(
            id=relationship_id,
            source_entity_id=source_entity.id,
            target_entity_id=target_entity.id,
            relationship_type=relationship_type,
            properties=rel_properties,
            source_document=source_document,
            confidence=confidence,
            created_at=datetime.now()
        )

    def build_graph_from_triplets(self,
                                 triplets: List[Dict[str, Any]],
                                 source_document: str) -> Dict[str, Any]:
        """
        Build graph from extracted triplets.

        Args:
            triplets: List of triplets in format {
                'subject': {'name': str, 'type': str, 'properties': dict},
                'predicate': str,
                'object': {'name': str, 'type': str, 'properties': dict},
                'confidence': float,
                'metadata': dict
            }
            source_document: Source document filename

        Returns:
            Dictionary with build statistics
        """
        logger.info(f"Building graph from {len(triplets)} triplets for document: {source_document}")

        # Track created entities to avoid duplicates
        entity_cache = {}  # (name, type) -> Entity
        created_entities = []
        created_relationships = []

        # Process each triplet
        for triplet in triplets:
            try:
                subject_info = triplet['subject']
                predicate = triplet['predicate']
                object_info = triplet['object']
                confidence = triplet.get('confidence', 0.5)
                metadata = triplet.get('metadata', {})

                # Create or get subject entity
                subject_key = (subject_info['name'], subject_info['type'])
                if subject_key not in entity_cache:
                    subject_entity = self.create_entity_from_extraction(
                        entity_name=subject_info['name'],
                        entity_type=subject_info['type'],
                        properties=subject_info.get('properties', {}),
                        source_document=source_document,
                        confidence=confidence
                    )
                    entity_cache[subject_key] = subject_entity
                    created_entities.append(subject_entity)

                # Create or get object entity
                object_key = (object_info['name'], object_info['type'])
                if object_key not in entity_cache:
                    object_entity = self.create_entity_from_extraction(
                        entity_name=object_info['name'],
                        entity_type=object_info['type'],
                        properties=object_info.get('properties', {}),
                        source_document=source_document,
                        confidence=confidence
                    )
                    entity_cache[object_key] = object_entity
                    created_entities.append(object_entity)

                # Create relationship
                subject_entity = entity_cache[subject_key]
                object_entity = entity_cache[object_key]

                relationship = self.create_relationship_from_extraction(
                    source_entity=subject_entity,
                    target_entity=object_entity,
                    relationship_type=predicate,
                    properties=metadata,
                    source_document=source_document,
                    confidence=confidence
                )
                created_relationships.append(relationship)

            except Exception as e:
                logger.error(f"Failed to process triplet: {triplet}. Error: {e}")
                continue

        # Batch create entities in graph database
        entity_ids = self.graph_db.batch_create_entities(created_entities)
        successful_entities = sum(1 for eid in entity_ids if eid is not None)

        # Batch create relationships
        relationship_ids = self.graph_db.batch_create_relationships(created_relationships)
        successful_relationships = sum(1 for rid in relationship_ids if rid is not None)

        statistics = {
            "total_triplets": len(triplets),
            "unique_entities": len(entity_cache),
            "created_entities": successful_entities,
            "created_relationships": successful_relationships,
            "failed_entities": len(created_entities) - successful_entities,
            "failed_relationships": len(created_relationships) - successful_relationships,
            "source_document": source_document,
            "timestamp": datetime.now().isoformat()
        }

        logger.info(f"Graph built: {statistics}")
        return statistics

    def merge_duplicate_entities(self, similarity_threshold: float = 0.8) -> Dict[str, Any]:
        """
        Merge duplicate entities in the graph based on similarity.

        Args:
            similarity_threshold: Threshold for considering entities as duplicates

        Returns:
            Merge statistics
        """
        # This is a placeholder implementation
        # In production, you would implement actual entity resolution
        logger.info(f"Merging duplicate entities with threshold {similarity_threshold}")

        # Get all entities
        all_entities = self.graph_db.find_entities({}, limit=10000)

        # Group by normalized name and type
        entity_groups = {}
        for entity in all_entities:
            normalized_name = self._normalize_entity_name(entity.name)
            group_key = (normalized_name, entity.entity_type)
            if group_key not in entity_groups:
                entity_groups[group_key] = []
            entity_groups[group_key].append(entity)

        # Find groups with potential duplicates
        merge_candidates = []
        for group_key, entities in entity_groups.items():
            if len(entities) > 1:
                merge_candidates.append((group_key, entities))

        # For now, just log the duplicates
        statistics = {
            "total_entities": len(all_entities),
            "duplicate_groups": len(merge_candidates),
            "potential_duplicates": sum(len(entities) for _, entities in merge_candidates),
            "merged": 0,  # Placeholder
            "timestamp": datetime.now().isoformat()
        }

        for group_key, entities in merge_candidates:
            entity_names = [e.name for e in entities]
            logger.debug(f"Duplicate group {group_key}: {entity_names}")

        logger.info(f"Entity merge analysis: {statistics}")
        return statistics

    def _normalize_entity_name(self, name: str) -> str:
        """Normalize entity name for comparison."""
        # Convert to lowercase, remove extra spaces, punctuation
        import re
        normalized = name.lower().strip()
        normalized = re.sub(r'[^\w\s]', '', normalized)  # Remove punctuation
        normalized = re.sub(r'\s+', ' ', normalized)  # Normalize whitespace
        return normalized

    def get_graph_for_visualization(self, document_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get graph data formatted for visualization (D3.js compatible).

        Args:
            document_id: Optional document filter

        Returns:
            Dictionary with nodes and links for visualization
        """
        import logging
        logger = logging.getLogger(__name__)

        print(f"[DEBUG] get_graph_for_visualization called with document_id: {document_id}")
        logger.debug(f"get_graph_for_visualization called with document_id: {document_id}")

        # Debug connection state
        print(f"[GRAPH BUILDER DEBUG] self.graph_db type: {type(self.graph_db)}")
        if hasattr(self.graph_db, 'connected'):
            print(f"[GRAPH BUILDER DEBUG] self.graph_db.connected: {self.graph_db.connected}")
        else:
            print(f"[GRAPH BUILDER DEBUG] self.graph_db has no 'connected' attribute")

        if hasattr(self.graph_db, 'driver'):
            print(f"[GRAPH BUILDER DEBUG] self.graph_db.driver: {self.graph_db.driver}")
        else:
            print(f"[GRAPH BUILDER DEBUG] self.graph_db has no 'driver' attribute")

        # Get entities
        if document_id:
            print(f"[DEBUG] Getting entities for document: {document_id}")
            logger.debug(f"Getting entities for document: {document_id}")
            entities = self.graph_db.get_entities_by_document(document_id)
        else:
            print("[DEBUG] Getting all entities (no document filter)")
            logger.debug("Getting all entities (no document filter)")
            entities = self.graph_db.find_entities({}, limit=500)  # Limit for visualization

        print(f"[DEBUG] Retrieved {len(entities)} entities")
        logger.debug(f"Retrieved {len(entities)} entities")

        # Get relationships
        if document_id:
            logger.debug(f"Getting relationships for document: {document_id}")
            relationships = self.graph_db.get_relationships_by_document(document_id)
        else:
            logger.debug("Getting all relationships (no document filter)")
            relationships = self.graph_db.find_relationships({}, limit=1000)

        logger.debug(f"Retrieved {len(relationships)} relationships")

        # Format nodes for D3.js
        nodes = []
        for entity in entities:
            node = {
                "id": entity.id,
                "name": entity.name,
                "type": entity.entity_type,
                "properties": entity.properties,
                "confidence": entity.confidence,
                "source_document": entity.source_document
            }
            nodes.append(node)

        # Format links for D3.js
        links = []
        for relationship in relationships:
            link = {
                "id": relationship.id,
                "source": relationship.source_entity_id,
                "target": relationship.target_entity_id,
                "type": relationship.relationship_type,
                "properties": relationship.properties,
                "confidence": relationship.confidence
            }
            links.append(link)

        # Get statistics
        stats = self.graph_db.get_graph_statistics(document_id)

        return {
            "nodes": nodes,
            "links": links,
            "statistics": {
                "total_nodes": len(nodes),
                "total_links": len(links),
                "entity_types": stats.entity_types,
                "relationship_types": stats.relationship_types
            }
        }

    def export_graph(self, format: str = "json", document_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Export graph data in various formats.

        Args:
            format: Export format (json, csv, graphml)
            document_id: Optional document filter

        Returns:
            Dictionary with exported data
        """
        if format == "json":
            return self.get_graph_for_visualization(document_id)
        elif format == "csv":
            # Placeholder for CSV export
            return {"format": "csv", "message": "CSV export not yet implemented"}
        elif format == "graphml":
            # Placeholder for GraphML export
            return {"format": "graphml", "message": "GraphML export not yet implemented"}
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def cleanup(self):
        """Cleanup resources."""
        if self.graph_db:
            self.graph_db.disconnect()
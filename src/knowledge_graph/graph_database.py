"""
Abstract base class for graph database adapters.
Defines the interface that all graph database implementations must follow.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Entity:
    """Representation of a knowledge graph entity."""
    id: str
    name: str
    entity_type: str
    properties: Dict[str, Any]
    source_document: Optional[str] = None
    confidence: Optional[float] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class Relationship:
    """Representation of a knowledge graph relationship."""
    id: str
    source_entity_id: str
    target_entity_id: str
    relationship_type: str
    properties: Dict[str, Any]
    source_document: Optional[str] = None
    confidence: Optional[float] = None
    created_at: Optional[datetime] = None


@dataclass
class GraphStatistics:
    """Statistics about the knowledge graph."""
    total_entities: int
    total_relationships: int
    entity_types: Dict[str, int]
    relationship_types: Dict[str, int]
    documents_processed: List[str]


class GraphDatabase(ABC):
    """Abstract base class for graph database operations."""

    @abstractmethod
    def connect(self) -> bool:
        """Connect to the graph database."""
        pass

    @abstractmethod
    def disconnect(self) -> bool:
        """Disconnect from the graph database."""
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Check database health and connectivity."""
        pass

    # Entity operations
    @abstractmethod
    def create_entity(self, entity: Entity) -> str:
        """Create a new entity in the graph."""
        pass

    @abstractmethod
    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Retrieve an entity by ID."""
        pass

    @abstractmethod
    def update_entity(self, entity_id: str, properties: Dict[str, Any]) -> bool:
        """Update entity properties."""
        pass

    @abstractmethod
    def delete_entity(self, entity_id: str) -> bool:
        """Delete an entity and its relationships."""
        pass

    @abstractmethod
    def find_entities(self, filters: Dict[str, Any], limit: int = 100) -> List[Entity]:
        """Find entities matching given filters."""
        pass

    # Relationship operations
    @abstractmethod
    def create_relationship(self, relationship: Relationship) -> str:
        """Create a new relationship between entities."""
        pass

    @abstractmethod
    def get_relationship(self, relationship_id: str) -> Optional[Relationship]:
        """Retrieve a relationship by ID."""
        pass

    @abstractmethod
    def delete_relationship(self, relationship_id: str) -> bool:
        """Delete a relationship."""
        pass

    @abstractmethod
    def find_relationships(self, filters: Dict[str, Any], limit: int = 100) -> List[Relationship]:
        """Find relationships matching given filters."""
        pass

    # Graph operations
    @abstractmethod
    def get_graph_statistics(self, document_id: Optional[str] = None) -> GraphStatistics:
        """Get statistics about the graph."""
        pass

    @abstractmethod
    def get_entities_by_document(self, document_id: str) -> List[Entity]:
        """Get all entities extracted from a specific document."""
        pass

    @abstractmethod
    def get_relationships_by_document(self, document_id: str) -> List[Relationship]:
        """Get all relationships extracted from a specific document."""
        pass

    @abstractmethod
    def delete_document_graph(self, document_id: str) -> bool:
        """Delete all entities and relationships from a specific document."""
        pass

    @abstractmethod
    def search_entities(self, query: str, entity_type: Optional[str] = None, limit: int = 50) -> List[Entity]:
        """Search entities by name or properties."""
        pass

    @abstractmethod
    def find_path(self, source_id: str, target_id: str, max_depth: int = 3) -> List[List[Relationship]]:
        """Find paths between two entities."""
        pass

    # Batch operations
    @abstractmethod
    def batch_create_entities(self, entities: List[Entity]) -> List[str]:
        """Create multiple entities in a batch."""
        pass

    @abstractmethod
    def batch_create_relationships(self, relationships: List[Relationship]) -> List[str]:
        """Create multiple relationships in a batch."""
        pass

    # Schema operations
    @abstractmethod
    def create_schema_constraints(self) -> bool:
        """Create database schema constraints and indexes."""
        pass

    @abstractmethod
    def clear_database(self) -> bool:
        """Clear all data from the database (use with caution!)."""
        pass
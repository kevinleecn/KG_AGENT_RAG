"""
Neo4j adapter implementation for graph database operations.
"""

import os
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from neo4j import GraphDatabase, Driver, Session
from neo4j.exceptions import Neo4jError

from .graph_database import GraphDatabase as BaseGraphDatabase, Entity, Relationship, GraphStatistics

logger = logging.getLogger(__name__)


class Neo4jAdapter(BaseGraphDatabase):
    """Neo4j implementation of graph database operations."""

    # Allowed filter fields for entity and relationship queries (security measure)
    ALLOWED_ENTITY_FILTERS = {
        "id", "name", "entity_type", "source_document", "confidence",
        "created_at", "updated_at"
    }

    ALLOWED_RELATIONSHIP_FILTERS = {
        "id", "relationship_type", "source_document", "confidence", "created_at",
        "source_entity_id", "target_entity_id"
    }

    def __init__(self, uri: Optional[str] = None, auth: Optional[Tuple[str, str]] = None,
                 database: str = "neo4j"):
        """
        Initialize Neo4j adapter.

        Args:
            uri: Neo4j connection URI (default: from NEO4J_URI environment variable)
            auth: Tuple of (username, password) (default: from NEO4J_USER/NEO4J_PASSWORD)
            database: Database name (default: "neo4j")
        """
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")

        if auth:
            self.username, self.password = auth
        else:
            self.username = os.getenv("NEO4J_USER")
            self.password = os.getenv("NEO4J_PASSWORD")

            # Warn if using default credentials in production-like environments
            if not self.username or not self.password:
                # Check if this looks like a production environment
                is_production = os.environ.get('FLASK_ENV') == 'production' or os.environ.get('NEO4J_URI', '').startswith('neo4j+s://')
                if is_production:
                    raise ValueError(
                        "NEO4J_USER and NEO4J_PASSWORD environment variables are required in production. "
                        "Set NEO4J_USER and NEO4J_PASSWORD environment variables."
                    )
                else:
                    # Development defaults with warnings
                    self.username = self.username or "neo4j"
                    self.password = self.password or "password"
                    logger.warning(
                        f"Using default Neo4j credentials (user: {self.username}, password: {self.password}). "
                        "Set NEO4J_USER and NEO4J_PASSWORD environment variables for security."
                    )

        self.database = database
        self.driver: Optional[Driver] = None
        self.connected = False

        # Debug logging
        print(f"[NEO4J DEBUG] Neo4jAdapter initialized:")
        print(f"[NEO4J DEBUG]   URI: {self.uri}")
        print(f"[NEO4J DEBUG]   Username: {self.username}")
        print(f"[NEO4J DEBUG]   Password: {'*' * len(self.password) if self.password else 'None'}")
        print(f"[NEO4J DEBUG]   Database: {self.database}")
        print(f"[NEO4J DEBUG]   Environment NEO4J_USER: {os.getenv('NEO4J_USER')}")
        print(f"[NEO4J DEBUG]   Environment NEO4J_PASSWORD: {'*' * len(os.getenv('NEO4J_PASSWORD', '')) if os.getenv('NEO4J_PASSWORD') else 'None'}")
        print(f"[NEO4J DEBUG]   Environment NEO4J_URI: {os.getenv('NEO4J_URI')}")

    def connect(self) -> bool:
        """Connect to Neo4j database."""
        try:
            print(f"[NEO4J DEBUG] Attempting to connect to Neo4j at {self.uri}")
            print(f"[NEO4J DEBUG] Username: {self.username}")
            print(f"[NEO4J DEBUG] Password: {'*' * len(self.password) if self.password else 'None'}")
            print(f"[NEO4J DEBUG] Database: {self.database}")

            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.username, self.password)
            )

            # Test connection
            with self.driver.session(database=self.database) as session:
                result = session.run("RETURN 1 as test")
                test_value = result.single()["test"]
                if test_value == 1:
                    self.connected = True
                    logger.info(f"Connected to Neo4j at {self.uri}")
                    print(f"[NEO4J DEBUG] Connection successful: {self.uri}")

                    # Create schema constraints
                    self.create_schema_constraints()
                    return True

            return False
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            print(f"[NEO4J DEBUG] Connection failed: {e}")
            import traceback
            traceback.print_exc()
            self.connected = False
            return False

    def disconnect(self) -> bool:
        """Disconnect from Neo4j database."""
        try:
            if self.driver:
                self.driver.close()
                self.driver = None
                self.connected = False
                logger.info("Disconnected from Neo4j")
            return True
        except Exception as e:
            logger.error(f"Error disconnecting from Neo4j: {e}")
            return False

    def health_check(self) -> Dict[str, Any]:
        """Check Neo4j health and connectivity."""
        if not self.driver or not self.connected:
            return {"status": "disconnected", "message": "Not connected to Neo4j"}

        try:
            with self.driver.session(database=self.database) as session:
                # Run a simple query to check connectivity
                result = session.run("CALL dbms.components() YIELD name, versions RETURN name, versions[0] as version")
                record = result.single()

                return {
                    "status": "connected",
                    "database": "Neo4j",
                    "version": record["version"] if record else "unknown",
                    "uri": self.uri,
                    "message": "Connection healthy"
                }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "uri": self.uri
            }

    def create_schema_constraints(self) -> bool:
        """Create Neo4j schema constraints and indexes."""
        try:
            with self.driver.session(database=self.database) as session:
                # Create constraints for entity uniqueness
                session.run("""
                    CREATE CONSTRAINT entity_id_unique IF NOT EXISTS
                    FOR (e:Entity) REQUIRE e.id IS UNIQUE
                """)

                session.run("""
                    CREATE CONSTRAINT relationship_id_unique IF NOT EXISTS
                    FOR ()-[r:RELATIONSHIP]-() REQUIRE r.id IS UNIQUE
                """)

                # Create indexes for faster queries
                session.run("""
                    CREATE INDEX entity_name IF NOT EXISTS
                    FOR (e:Entity) ON (e.name)
                """)

                session.run("""
                    CREATE INDEX entity_type IF NOT EXISTS
                    FOR (e:Entity) ON (e.entity_type)
                """)

                session.run("""
                    CREATE INDEX entity_document IF NOT EXISTS
                    FOR (e:Entity) ON (e.source_document)
                """)

                logger.info("Created Neo4j schema constraints and indexes")
                return True
        except Exception as e:
            logger.error(f"Failed to create schema constraints: {e}")
            return False

    def create_entity(self, entity: Entity) -> str:
        """Create a new entity in Neo4j."""
        if not self.driver:
            raise ConnectionError("Not connected to Neo4j")

        try:
            with self.driver.session(database=self.database) as session:
                # Ensure created_at timestamp
                if not entity.created_at:
                    entity.created_at = datetime.now()

                # Prepare properties
                properties = entity.properties.copy()
                properties.update({
                    "id": entity.id,
                    "name": entity.name,
                    "entity_type": entity.entity_type,
                    "source_document": entity.source_document,
                    "confidence": entity.confidence,
                    "created_at": entity.created_at.isoformat() if entity.created_at else None,
                    "updated_at": entity.updated_at.isoformat() if entity.updated_at else None
                })

                # Remove None values
                properties = {k: v for k, v in properties.items() if v is not None}

                # Create entity node
                query = """
                    CREATE (e:Entity $properties)
                    RETURN e.id as entity_id
                """

                result = session.run(query, properties=properties)
                entity_id = result.single()["entity_id"]
                logger.debug(f"Created entity: {entity_id}")
                return entity_id
        except Exception as e:
            logger.error(f"Failed to create entity {entity.id}: {e}")
            raise

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Retrieve an entity by ID from Neo4j."""
        if not self.driver:
            raise ConnectionError("Not connected to Neo4j")

        try:
            with self.driver.session(database=self.database) as session:
                query = """
                    MATCH (e:Entity {id: $entity_id})
                    RETURN e
                """

                result = session.run(query, entity_id=entity_id)
                record = result.single()

                if not record:
                    return None

                node = record["e"]
                properties = dict(node)

                # Extract core fields
                entity = Entity(
                    id=properties.pop("id"),
                    name=properties.pop("name", ""),
                    entity_type=properties.pop("entity_type", "UNKNOWN"),
                    properties=properties,
                    source_document=properties.pop("source_document", None),
                    confidence=properties.pop("confidence", None),
                    created_at=datetime.fromisoformat(properties.pop("created_at")) if properties.get("created_at") else None,
                    updated_at=datetime.fromisoformat(properties.pop("updated_at")) if properties.get("updated_at") else None
                )

                return entity
        except Exception as e:
            logger.error(f"Failed to get entity {entity_id}: {e}")
            return None

    def update_entity(self, entity_id: str, properties: Dict[str, Any]) -> bool:
        """Update entity properties in Neo4j."""
        if not self.driver:
            raise ConnectionError("Not connected to Neo4j")

        try:
            with self.driver.session(database=self.database) as session:
                # Add updated_at timestamp
                update_properties = properties.copy()
                update_properties["updated_at"] = datetime.now().isoformat()

                query = """
                    MATCH (e:Entity {id: $entity_id})
                    SET e += $properties
                    RETURN e.id as entity_id
                """

                result = session.run(query, entity_id=entity_id, properties=update_properties)
                updated = result.single() is not None

                if updated:
                    logger.debug(f"Updated entity: {entity_id}")

                return updated
        except Exception as e:
            logger.error(f"Failed to update entity {entity_id}: {e}")
            return False

    def delete_entity(self, entity_id: str) -> bool:
        """Delete an entity and its relationships from Neo4j."""
        if not self.driver:
            raise ConnectionError("Not connected to Neo4j")

        try:
            with self.driver.session(database=self.database) as session:
                query = """
                    MATCH (e:Entity {id: $entity_id})
                    DETACH DELETE e
                    RETURN count(e) as deleted_count
                """

                result = session.run(query, entity_id=entity_id)
                deleted_count = result.single()["deleted_count"]

                deleted = deleted_count > 0
                if deleted:
                    logger.debug(f"Deleted entity: {entity_id}")

                return deleted
        except Exception as e:
            logger.error(f"Failed to delete entity {entity_id}: {e}")
            return False

    def find_entities(self, filters: Dict[str, Any], limit: int = 100) -> List[Entity]:
        """Find entities matching given filters in Neo4j."""
        if not self.driver:
            raise ConnectionError("Not connected to Neo4j")

        try:
            with self.driver.session(database=self.database) as session:
                # Build WHERE clause from filters with security validation
                where_clauses = []
                params = {}
                param_counter = 0

                for key, value in filters.items():
                    logger.debug(f"Processing filter: key='{key}', value={value}, type={type(value)}")
                    if value is not None:
                        # Security: Validate filter key against allowed fields
                        if key not in self.ALLOWED_ENTITY_FILTERS:
                            logger.warning(f"Attempted to filter entities by disallowed field: {key}")
                            continue

                        param_counter += 1
                        param_name = f"filter_{key}_{param_counter}"

                        # Check if value is a dictionary with operators (e.g., {"$contains": "value"})
                        if isinstance(value, dict):
                            # Debug: log the value dictionary
                            logger.debug(f"Processing operator dict for field {key}: {value}")

                            # Handle operator-based filters
                            for operator, operator_value in value.items():
                                # Skip empty operators
                                if not operator:
                                    logger.debug(f"Skipping empty operator in dict: {value}")
                                    continue

                                logger.debug(f"Processing operator '{operator}' with value '{operator_value}' for field {key}")

                                if operator == "$contains":
                                    where_clauses.append(f"toLower(e.{key}) CONTAINS toLower(${param_name})")
                                    params[param_name] = operator_value
                                    logger.debug(f"Added CONTAINS clause for {key} with value {operator_value}")
                                elif operator == "$startsWith":
                                    where_clauses.append(f"e.{key} STARTS WITH ${param_name}")
                                    params[param_name] = operator_value
                                elif operator == "$endsWith":
                                    where_clauses.append(f"e.{key} ENDS WITH ${param_name}")
                                    params[param_name] = operator_value
                                elif operator == "$regex":
                                    where_clauses.append(f"e.{key} =~ ${param_name}")
                                    params[param_name] = operator_value
                                else:
                                    # Default to equality for unknown operators
                                    logger.warning(f"Unsupported operator '{operator}' for field {key}")
                                    where_clauses.append(f"e.{key} = ${param_name}")
                                    params[param_name] = operator_value
                        else:
                            # Simple equality for non-dictionary values
                            logger.debug(f"Simple value for field {key}: {value}")
                            where_clauses.append(f"e.{key} = ${param_name}")
                            params[param_name] = value

                where_statement = " AND ".join(where_clauses) if where_clauses else "TRUE"

                query = f"""
                    MATCH (e:Entity)
                    WHERE {where_statement}
                    RETURN e
                    LIMIT $limit
                """

                # Debug logging
                logger.debug(f"Generated query: {query}")
                logger.debug(f"Query params: {params}")

                params["limit"] = limit
                result = session.run(query, **params)

                entities = []
                for record in result:
                    node = record["e"]
                    properties = dict(node)

                    entity = Entity(
                        id=properties.pop("id"),
                        name=properties.pop("name", ""),
                        entity_type=properties.pop("entity_type", "UNKNOWN"),
                        properties=properties,
                        source_document=properties.pop("source_document", None),
                        confidence=properties.pop("confidence", None),
                        created_at=datetime.fromisoformat(properties.pop("created_at")) if properties.get("created_at") else None,
                        updated_at=datetime.fromisoformat(properties.pop("updated_at")) if properties.get("updated_at") else None
                    )
                    entities.append(entity)

                return entities
        except Exception as e:
            logger.error(f"Failed to find entities: {e}")
            return []

    def create_relationship(self, relationship: Relationship) -> str:
        """Create a new relationship between entities in Neo4j."""
        if not self.driver:
            raise ConnectionError("Not connected to Neo4j")

        try:
            with self.driver.session(database=self.database) as session:
                # Ensure created_at timestamp
                if not relationship.created_at:
                    relationship.created_at = datetime.now()

                # Prepare properties
                properties = relationship.properties.copy()
                properties.update({
                    "id": relationship.id,
                    "relationship_type": relationship.relationship_type,
                    "source_document": relationship.source_document,
                    "confidence": relationship.confidence,
                    "created_at": relationship.created_at.isoformat() if relationship.created_at else None
                })

                # Remove None values
                properties = {k: v for k, v in properties.items() if v is not None}

                # Create relationship
                query = """
                    MATCH (source:Entity {id: $source_id})
                    MATCH (target:Entity {id: $target_id})
                    CREATE (source)-[r:RELATIONSHIP $properties]->(target)
                    RETURN r.id as relationship_id
                """

                result = session.run(
                    query,
                    source_id=relationship.source_entity_id,
                    target_id=relationship.target_entity_id,
                    properties=properties
                )

                relationship_id = result.single()["relationship_id"]
                logger.debug(f"Created relationship: {relationship_id}")
                return relationship_id
        except Exception as e:
            logger.error(f"Failed to create relationship {relationship.id}: {e}")
            raise

    def get_relationship(self, relationship_id: str) -> Optional[Relationship]:
        """Retrieve a relationship by ID from Neo4j."""
        if not self.driver:
            raise ConnectionError("Not connected to Neo4j")

        try:
            with self.driver.session(database=self.database) as session:
                query = """
                    MATCH (source)-[r:RELATIONSHIP {id: $relationship_id}]->(target)
                    RETURN r, source.id as source_id, target.id as target_id
                """

                result = session.run(query, relationship_id=relationship_id)
                record = result.single()

                if not record:
                    return None

                rel = record["r"]
                properties = dict(rel)

                relationship = Relationship(
                    id=properties.pop("id"),
                    source_entity_id=record["source_id"],
                    target_entity_id=record["target_id"],
                    relationship_type=properties.pop("relationship_type", "RELATED_TO"),
                    properties=properties,
                    source_document=properties.pop("source_document", None),
                    confidence=properties.pop("confidence", None),
                    created_at=datetime.fromisoformat(properties.pop("created_at")) if properties.get("created_at") else None
                )

                return relationship
        except Exception as e:
            logger.error(f"Failed to get relationship {relationship_id}: {e}")
            return None

    def delete_relationship(self, relationship_id: str) -> bool:
        """Delete a relationship from Neo4j."""
        if not self.driver:
            raise ConnectionError("Not connected to Neo4j")

        try:
            with self.driver.session(database=self.database) as session:
                query = """
                    MATCH ()-[r:RELATIONSHIP {id: $relationship_id}]->()
                    DELETE r
                    RETURN count(r) as deleted_count
                """

                result = session.run(query, relationship_id=relationship_id)
                deleted_count = result.single()["deleted_count"]

                deleted = deleted_count > 0
                if deleted:
                    logger.debug(f"Deleted relationship: {relationship_id}")

                return deleted
        except Exception as e:
            logger.error(f"Failed to delete relationship {relationship_id}: {e}")
            return False

    def find_relationships(self, filters: Dict[str, Any], limit: int = 100) -> List[Relationship]:
        """Find relationships matching given filters in Neo4j."""
        if not self.driver:
            raise ConnectionError("Not connected to Neo4j")

        try:
            with self.driver.session(database=self.database) as session:
                # Build WHERE clause from filters with security validation
                where_clauses = []
                params = {}

                for key, value in filters.items():
                    if value is not None:
                        # Security: Validate filter key against allowed fields
                        if key not in self.ALLOWED_RELATIONSHIP_FILTERS:
                            logger.warning(f"Attempted to filter relationships by disallowed field: {key}")
                            continue

                        param_name = f"filter_{key}"
                        where_clauses.append(f"r.{key} = ${param_name}")
                        params[param_name] = value

                where_statement = " AND ".join(where_clauses) if where_clauses else "TRUE"

                query = f"""
                    MATCH (source)-[r:RELATIONSHIP]->(target)
                    WHERE {where_statement}
                    RETURN r, source.id as source_id, target.id as target_id
                    LIMIT $limit
                """

                params["limit"] = limit
                result = session.run(query, **params)

                relationships = []
                for record in result:
                    rel = record["r"]
                    properties = dict(rel)

                    relationship = Relationship(
                        id=properties.pop("id"),
                        source_entity_id=record["source_id"],
                        target_entity_id=record["target_id"],
                        relationship_type=properties.pop("relationship_type", "RELATED_TO"),
                        properties=properties,
                        source_document=properties.pop("source_document", None),
                        confidence=properties.pop("confidence", None),
                        created_at=datetime.fromisoformat(properties.pop("created_at")) if properties.get("created_at") else None
                    )
                    relationships.append(relationship)

                return relationships
        except Exception as e:
            logger.error(f"Failed to find relationships: {e}")
            return []

    def get_graph_statistics(self, document_id: Optional[str] = None) -> GraphStatistics:
        """Get statistics about the graph in Neo4j."""
        if not self.driver:
            raise ConnectionError("Not connected to Neo4j")

        try:
            with self.driver.session(database=self.database) as session:
                # Base queries with optional document filter
                doc_filter = "WHERE e.source_document = $document_id" if document_id else ""
                rel_doc_filter = "WHERE r.source_document = $document_id" if document_id else ""

                # Get total entities
                entity_query = f"""
                    MATCH (e:Entity)
                    {doc_filter}
                    RETURN count(e) as total_entities
                """

                # Get entity types distribution
                entity_types_query = f"""
                    MATCH (e:Entity)
                    {doc_filter}
                    RETURN e.entity_type as type, count(e) as count
                """

                # Get total relationships
                relationship_query = f"""
                    MATCH ()-[r:RELATIONSHIP]->()
                    {rel_doc_filter}
                    RETURN count(r) as total_relationships
                """

                # Get relationship types distribution
                relationship_types_query = f"""
                    MATCH ()-[r:RELATIONSHIP]->()
                    {rel_doc_filter}
                    RETURN r.relationship_type as type, count(r) as count
                """

                # Get documents processed
                documents_query = """
                    MATCH (e:Entity)
                    WHERE e.source_document IS NOT NULL
                    RETURN DISTINCT e.source_document as document
                """

                params = {"document_id": document_id} if document_id else {}

                # Execute queries
                total_entities = session.run(entity_query, **params).single()["total_entities"]

                entity_types = {}
                for record in session.run(entity_types_query, **params):
                    entity_types[record["type"]] = record["count"]

                total_relationships = session.run(relationship_query, **params).single()["total_relationships"]

                relationship_types = {}
                for record in session.run(relationship_types_query, **params):
                    relationship_types[record["type"]] = record["count"]

                documents = [record["document"] for record in session.run(documents_query)]

                return GraphStatistics(
                    total_entities=total_entities,
                    total_relationships=total_relationships,
                    entity_types=entity_types,
                    relationship_types=relationship_types,
                    documents_processed=documents
                )
        except Exception as e:
            logger.error(f"Failed to get graph statistics: {e}")
            # Return empty statistics
            return GraphStatistics(
                total_entities=0,
                total_relationships=0,
                entity_types={},
                relationship_types={},
                documents_processed=[]
            )

    def get_entities_by_document(self, document_id: str) -> List[Entity]:
        """Get all entities extracted from a specific document."""
        return self.find_entities({"source_document": document_id})

    def get_relationships_by_document(self, document_id: str) -> List[Relationship]:
        """Get all relationships extracted from a specific document."""
        return self.find_relationships({"source_document": document_id})

    def delete_document_graph(self, document_id: str) -> bool:
        """Delete all entities and relationships from a specific document."""
        if not self.driver:
            raise ConnectionError("Not connected to Neo4j")

        try:
            with self.driver.session(database=self.database) as session:
                # Delete relationships first, then entities
                relationship_query = """
                    MATCH ()-[r:RELATIONSHIP {source_document: $document_id}]->()
                    DELETE r
                    RETURN count(r) as deleted_relationships
                """

                entity_query = """
                    MATCH (e:Entity {source_document: $document_id})
                    DETACH DELETE e
                    RETURN count(e) as deleted_entities
                """

                deleted_relationships = session.run(relationship_query, document_id=document_id).single()["deleted_relationships"]
                deleted_entities = session.run(entity_query, document_id=document_id).single()["deleted_entities"]

                logger.info(f"Deleted document graph: {deleted_entities} entities, {deleted_relationships} relationships")
                return True
        except Exception as e:
            logger.error(f"Failed to delete document graph for {document_id}: {e}")
            return False

    def search_entities(self, query: str, entity_type: Optional[str] = None, limit: int = 50) -> List[Entity]:
        """Search entities by name or properties in Neo4j."""
        if not self.driver:
            raise ConnectionError("Not connected to Neo4j")

        try:
            with self.driver.session(database=self.database) as session:
                # Build search query
                type_filter = "AND e.entity_type = $entity_type" if entity_type else ""

                search_query = f"""
                    MATCH (e:Entity)
                    WHERE e.name CONTAINS $query OR any(key in keys(e) WHERE key <> 'id' AND toString(e[key]) CONTAINS $query)
                    {type_filter}
                    RETURN e
                    LIMIT $limit
                """

                params = {
                    "query": query,
                    "limit": limit
                }
                if entity_type:
                    params["entity_type"] = entity_type

                result = session.run(search_query, **params)

                entities = []
                for record in result:
                    node = record["e"]
                    properties = dict(node)

                    entity = Entity(
                        id=properties.pop("id"),
                        name=properties.pop("name", ""),
                        entity_type=properties.pop("entity_type", "UNKNOWN"),
                        properties=properties,
                        source_document=properties.pop("source_document", None),
                        confidence=properties.pop("confidence", None),
                        created_at=datetime.fromisoformat(properties.pop("created_at")) if properties.get("created_at") else None,
                        updated_at=datetime.fromisoformat(properties.pop("updated_at")) if properties.get("updated_at") else None
                    )
                    entities.append(entity)

                return entities
        except Exception as e:
            logger.error(f"Failed to search entities: {e}")
            return []

    def find_path(self, source_id: str, target_id: str, max_depth: int = 3) -> List[List[Relationship]]:
        """Find paths between two entities in Neo4j."""
        if not self.driver:
            raise ConnectionError("Not connected to Neo4j")

        try:
            with self.driver.session(database=self.database) as session:
                query = """
                    MATCH path = shortestPath((source:Entity {id: $source_id})-[*..$max_depth]-(target:Entity {id: $target_id}))
                    WHERE all(rel in relationships(path) WHERE rel.id IS NOT NULL)
                    RETURN relationships(path) as rels
                """

                result = session.run(query, source_id=source_id, target_id=target_id, max_depth=max_depth)
                records = list(result)

                if not records:
                    # Try to find any path (not necessarily shortest)
                    query_any = """
                        MATCH path = (source:Entity {id: $source_id})-[*..$max_depth]-(target:Entity {id: $target_id})
                        RETURN relationships(path) as rels
                        LIMIT 5
                    """

                    result = session.run(query_any, source_id=source_id, target_id=target_id, max_depth=max_depth)
                    records = list(result)

                paths = []
                for record in records:
                    rels = record["rels"]
                    if rels:
                        path = []
                        for rel in rels:
                            properties = dict(rel)
                            relationship = Relationship(
                                id=properties.pop("id"),
                                source_entity_id="",  # Will need to extract from path
                                target_entity_id="",  # Will need to extract from path
                                relationship_type=properties.pop("relationship_type", "RELATED_TO"),
                                properties=properties,
                                source_document=properties.pop("source_document", None),
                                confidence=properties.pop("confidence", None),
                                created_at=datetime.fromisoformat(properties.pop("created_at")) if properties.get("created_at") else None
                            )
                            path.append(relationship)
                        paths.append(path)

                return paths
        except Exception as e:
            logger.error(f"Failed to find path between {source_id} and {target_id}: {e}")
            return []

    def batch_create_entities(self, entities: List[Entity]) -> List[str]:
        """Create multiple entities in a batch in Neo4j using UNWIND."""
        if not self.driver:
            raise ConnectionError("Not connected to Neo4j")

        if not entities:
            return []

        try:
            with self.driver.session(database=self.database) as session:
                # Prepare entity data for batch creation
                entity_data = []
                for entity in entities:
                    # Ensure created_at timestamp
                    if not entity.created_at:
                        entity.created_at = datetime.now()

                    # Prepare properties
                    properties = entity.properties.copy()
                    properties.update({
                        "id": entity.id,
                        "name": entity.name,
                        "entity_type": entity.entity_type,
                        "source_document": entity.source_document,
                        "confidence": entity.confidence,
                        "created_at": entity.created_at.isoformat() if entity.created_at else None,
                        "updated_at": entity.updated_at.isoformat() if entity.updated_at else None
                    })

                    # Remove None values
                    properties = {k: v for k, v in properties.items() if v is not None}
                    entity_data.append(properties)

                # Batch create using UNWIND
                query = """
                    UNWIND $entities as entity_props
                    CREATE (e:Entity)
                    SET e = entity_props
                    RETURN e.id as entity_id
                """

                result = session.run(query, entities=entity_data)
                entity_ids = [record["entity_id"] for record in result]

                # Ensure we return the same number of IDs as input entities
                if len(entity_ids) != len(entities):
                    logger.warning(f"Batch create returned {len(entity_ids)} IDs but expected {len(entities)}")
                    # Fallback to individual creation for missing IDs
                    for i, entity in enumerate(entities):
                        if i >= len(entity_ids) or entity_ids[i] is None:
                            try:
                                entity_id = self.create_entity(entity)
                                if i < len(entity_ids):
                                    entity_ids[i] = entity_id
                                else:
                                    entity_ids.append(entity_id)
                            except Exception as e:
                                logger.error(f"Failed to create entity {entity.id} in batch fallback: {e}")
                                if i < len(entity_ids):
                                    entity_ids[i] = None
                                else:
                                    entity_ids.append(None)

                logger.info(f"Batch created {len([eid for eid in entity_ids if eid is not None])} entities")
                return entity_ids
        except Exception as e:
            logger.error(f"Batch entity creation failed: {e}")
            # Fallback to individual creation
            entity_ids = []
            for entity in entities:
                try:
                    entity_id = self.create_entity(entity)
                    entity_ids.append(entity_id)
                except Exception as inner_e:
                    logger.error(f"Failed to create entity {entity.id} in batch fallback: {inner_e}")
                    entity_ids.append(None)
            return entity_ids

    def batch_create_relationships(self, relationships: List[Relationship]) -> List[str]:
        """Create multiple relationships in a batch in Neo4j using UNWIND."""
        if not self.driver:
            raise ConnectionError("Not connected to Neo4j")

        if not relationships:
            return []

        try:
            with self.driver.session(database=self.database) as session:
                # Prepare relationship data for batch creation
                relationship_data = []
                for relationship in relationships:
                    # Ensure created_at timestamp
                    if not relationship.created_at:
                        relationship.created_at = datetime.now()

                    # Prepare properties
                    properties = relationship.properties.copy()
                    properties.update({
                        "id": relationship.id,
                        "relationship_type": relationship.relationship_type,
                        "source_document": relationship.source_document,
                        "confidence": relationship.confidence,
                        "created_at": relationship.created_at.isoformat() if relationship.created_at else None
                    })

                    # Remove None values
                    properties = {k: v for k, v in properties.items() if v is not None}

                    relationship_data.append({
                        "source_id": relationship.source_entity_id,
                        "target_id": relationship.target_entity_id,
                        "properties": properties
                    })

                # Batch create using UNWIND
                query = """
                    UNWIND $relationships as rel_data
                    MATCH (source:Entity {id: rel_data.source_id})
                    MATCH (target:Entity {id: rel_data.target_id})
                    CREATE (source)-[r:RELATIONSHIP]->(target)
                    SET r = rel_data.properties
                    RETURN r.id as relationship_id
                """

                result = session.run(query, relationships=relationship_data)
                relationship_ids = [record["relationship_id"] for record in result]

                # Ensure we return the same number of IDs as input relationships
                if len(relationship_ids) != len(relationships):
                    logger.warning(f"Batch create returned {len(relationship_ids)} IDs but expected {len(relationships)}")
                    # Fallback to individual creation for missing IDs
                    for i, relationship in enumerate(relationships):
                        if i >= len(relationship_ids) or relationship_ids[i] is None:
                            try:
                                rel_id = self.create_relationship(relationship)
                                if i < len(relationship_ids):
                                    relationship_ids[i] = rel_id
                                else:
                                    relationship_ids.append(rel_id)
                            except Exception as e:
                                logger.error(f"Failed to create relationship {relationship.id} in batch fallback: {e}")
                                if i < len(relationship_ids):
                                    relationship_ids[i] = None
                                else:
                                    relationship_ids.append(None)

                logger.info(f"Batch created {len([rid for rid in relationship_ids if rid is not None])} relationships")
                return relationship_ids
        except Exception as e:
            logger.error(f"Batch relationship creation failed: {e}")
            # Fallback to individual creation
            relationship_ids = []
            for relationship in relationships:
                try:
                    rel_id = self.create_relationship(relationship)
                    relationship_ids.append(rel_id)
                except Exception as inner_e:
                    logger.error(f"Failed to create relationship {relationship.id} in batch fallback: {inner_e}")
                    relationship_ids.append(None)
            return relationship_ids

    def clear_database(self) -> bool:
        """Clear all data from the Neo4j database (use with caution!)."""
        if not self.driver:
            raise ConnectionError("Not connected to Neo4j")

        try:
            with self.driver.session(database=self.database) as session:
                result = session.run("MATCH (n) DETACH DELETE n RETURN count(n) as deleted")
                deleted_count = result.single()["deleted"]
                logger.warning(f"Cleared database: {deleted_count} nodes deleted")
                return True
        except Exception as e:
            logger.error(f"Failed to clear database: {e}")
            return False

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
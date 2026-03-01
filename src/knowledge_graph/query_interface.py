"""
Advanced query interface for the knowledge graph.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta

from .graph_database import GraphDatabase, Entity, Relationship
from .neo4j_adapter import Neo4jAdapter

logger = logging.getLogger(__name__)


class QueryInterface:
    """Advanced query interface for knowledge graph operations."""

    def __init__(self, graph_db: Optional[GraphDatabase] = None):
        """
        Initialize query interface.

        Args:
            graph_db: Graph database instance (default: creates Neo4jAdapter)
        """
        self.graph_db = graph_db or Neo4jAdapter()

        # Connect if not already connected
        if not hasattr(self.graph_db, 'connected') or not self.graph_db.connected:
            self.graph_db.connect()

    def find_related_entities(self,
                             entity_id: str,
                             relationship_types: Optional[List[str]] = None,
                             max_depth: int = 2,
                             limit: int = 50) -> Dict[str, Any]:
        """
        Find entities related to a given entity.

        Args:
            entity_id: ID of the source entity
            relationship_types: Filter by relationship types
            max_depth: Maximum relationship depth
            limit: Maximum number of results

        Returns:
            Dictionary with related entities and paths
        """
        try:
            source_entity = self.graph_db.get_entity(entity_id)
            if not source_entity:
                return {"error": f"Entity not found: {entity_id}"}

            # Build relationship type filter
            rel_type_filter = ""
            if relationship_types:
                rel_types_str = ", ".join([f"'{rt}'" for rt in relationship_types])
                rel_type_filter = f"AND type(r) IN [{rel_types_str}]"

            # Query for related entities
            query = f"""
                MATCH path = (source:Entity {{id: $entity_id}})-[r*1..{max_depth}]-(related:Entity)
                WHERE source <> related {rel_type_filter}
                RETURN DISTINCT related, length(path) as depth,
                       [rel in relationships(path) | type(rel)] as path_types
                LIMIT $limit
            """

            if hasattr(self.graph_db, 'driver'):
                with self.graph_db.driver.session(database=self.graph_db.database) as session:
                    result = session.run(
                        query,
                        entity_id=entity_id,
                        limit=limit
                    )

                    related_entities = []
                    for record in result:
                        node = record["related"]
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

                        related_entities.append({
                            "entity": entity,
                            "depth": record["depth"],
                            "path_types": record["path_types"]
                        })

                    return {
                        "source_entity": source_entity,
                        "related_entities": related_entities,
                        "total_related": len(related_entities),
                        "max_depth": max_depth
                    }
            else:
                # Fallback to simple relationship search
                relationships = self.graph_db.find_relationships(
                    {"source_entity_id": entity_id},
                    limit=limit
                )

                related_entities = []
                for rel in relationships:
                    target_entity = self.graph_db.get_entity(rel.target_entity_id)
                    if target_entity:
                        related_entities.append({
                            "entity": target_entity,
                            "depth": 1,
                            "path_types": [rel.relationship_type],
                            "relationship": rel
                        })

                return {
                    "source_entity": source_entity,
                    "related_entities": related_entities,
                    "total_related": len(related_entities),
                    "max_depth": 1
                }

        except Exception as e:
            logger.error(f"Error finding related entities for {entity_id}: {e}")
            return {"error": str(e)}

    def find_entity_clusters(self,
                            entity_type: Optional[str] = None,
                            min_cluster_size: int = 3,
                            relationship_threshold: int = 2) -> Dict[str, Any]:
        """
        Find clusters of densely connected entities.

        Args:
            entity_type: Filter by entity type
            min_cluster_size: Minimum cluster size
            relationship_threshold: Minimum relationships for clustering

        Returns:
            Dictionary with clusters and statistics
        """
        try:
            # This is a simplified clustering implementation
            # In production, use Neo4j's graph algorithms

            entity_filter = "WHERE e.entity_type = $entity_type" if entity_type else ""
            params = {"entity_type": entity_type} if entity_type else {}

            query = f"""
                MATCH (e:Entity)
                {entity_filter}
                WITH e
                MATCH (e)-[r:RELATIONSHIP]-(neighbor:Entity)
                WITH e, count(r) as degree
                WHERE degree >= $relationship_threshold
                RETURN e.id as entity_id, e.name as name, e.entity_type as type, degree
                ORDER BY degree DESC
            """

            params["relationship_threshold"] = relationship_threshold

            if hasattr(self.graph_db, 'driver'):
                with self.graph_db.driver.session(database=self.graph_db.database) as session:
                    result = session.run(query, **params)

                    high_degree_entities = []
                    for record in result:
                        high_degree_entities.append({
                            "entity_id": record["entity_id"],
                            "name": record["name"],
                            "type": record["type"],
                            "degree": record["degree"]
                        })

                    # Simple clustering: group by entity type and degree
                    clusters = {}
                    for entity in high_degree_entities:
                        cluster_key = f"{entity['type']}_degree_{entity['degree'] // 5 * 5}"
                        if cluster_key not in clusters:
                            clusters[cluster_key] = []
                        clusters[cluster_key].append(entity)

                    # Filter by minimum cluster size
                    filtered_clusters = {
                        key: entities
                        for key, entities in clusters.items()
                        if len(entities) >= min_cluster_size
                    }

                    return {
                        "clusters": filtered_clusters,
                        "total_clusters": len(filtered_clusters),
                        "total_entities": sum(len(entities) for entities in filtered_clusters.values()),
                        "min_cluster_size": min_cluster_size
                    }
            else:
                # Fallback implementation
                return {
                    "clusters": {},
                    "total_clusters": 0,
                    "message": "Clustering requires Neo4j driver",
                    "min_cluster_size": min_cluster_size
                }

        except Exception as e:
            logger.error(f"Error finding entity clusters: {e}")
            return {"error": str(e)}

    def find_bridging_entities(self, entity_type_a: str, entity_type_b: str) -> Dict[str, Any]:
        """
        Find entities that bridge two different entity types.

        Args:
            entity_type_a: First entity type
            entity_type_b: Second entity type

        Returns:
            Dictionary with bridging entities
        """
        try:
            query = """
                MATCH (a:Entity {entity_type: $type_a})
                MATCH (b:Entity {entity_type: $type_b})
                MATCH path = shortestPath((a)-[*..3]-(b))
                WITH nodes(path) as path_nodes, relationships(path) as path_rels
                UNWIND path_nodes as node
                WITH node, count(DISTINCT node.entity_type) as types_in_path
                WHERE types_in_path > 1
                RETURN node.id as entity_id, node.name as name, node.entity_type as type,
                       collect(DISTINCT node.entity_type) as connected_types
                LIMIT 50
            """

            if hasattr(self.graph_db, 'driver'):
                with self.graph_db.driver.session(database=self.graph_db.database) as session:
                    result = session.run(
                        query,
                        type_a=entity_type_a,
                        type_b=entity_type_b
                    )

                    bridging_entities = []
                    for record in result:
                        bridging_entities.append({
                            "entity_id": record["entity_id"],
                            "name": record["name"],
                            "type": record["type"],
                            "connected_types": record["connected_types"]
                        })

                    return {
                        "entity_type_a": entity_type_a,
                        "entity_type_b": entity_type_b,
                        "bridging_entities": bridging_entities,
                        "total_bridging": len(bridging_entities)
                    }
            else:
                # Fallback implementation
                entities_a = self.graph_db.find_entities({"entity_type": entity_type_a}, limit=50)
                entities_b = self.graph_db.find_entities({"entity_type": entity_type_b}, limit=50)

                # Simple bridging detection (entities connected to both types)
                bridging_entities = []
                for entity in entities_a + entities_b:
                    # Check if entity has relationships to both types
                    relationships = self.graph_db.find_relationships(
                        {"source_entity_id": entity.id},
                        limit=100
                    )

                    connected_types = set()
                    for rel in relationships:
                        target = self.graph_db.get_entity(rel.target_entity_id)
                        if target:
                            connected_types.add(target.entity_type)

                    if entity_type_a in connected_types and entity_type_b in connected_types:
                        bridging_entities.append({
                            "entity_id": entity.id,
                            "name": entity.name,
                            "type": entity.entity_type,
                            "connected_types": list(connected_types)
                        })

                return {
                    "entity_type_a": entity_type_a,
                    "entity_type_b": entity_type_b,
                    "bridging_entities": bridging_entities[:50],
                    "total_bridging": len(bridging_entities)
                }

        except Exception as e:
            logger.error(f"Error finding bridging entities: {e}")
            return {"error": str(e)}

    def get_temporal_analysis(self,
                             start_date: Optional[datetime] = None,
                             end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Analyze temporal patterns in the graph.

        Args:
            start_date: Start date for analysis
            end_date: End date for analysis

        Returns:
            Dictionary with temporal analysis
        """
        try:
            # Default to last 30 days
            if not end_date:
                end_date = datetime.now()
            if not start_date:
                start_date = end_date - timedelta(days=30)

            date_filter = """
                WHERE date(datetime(r.created_at)) >= date($start_date)
                AND date(datetime(r.created_at)) <= date($end_date)
            """

            query = f"""
                MATCH ()-[r:RELATIONSHIP]->()
                {date_filter}
                RETURN date(datetime(r.created_at)) as date,
                       count(r) as relationship_count,
                       collect(DISTINCT r.relationship_type) as relationship_types
                ORDER BY date
            """

            if hasattr(self.graph_db, 'driver'):
                with self.graph_db.driver.session(database=self.graph_db.database) as session:
                    result = session.run(
                        query,
                        start_date=start_date.isoformat(),
                        end_date=end_date.isoformat()
                    )

                    timeline = []
                    for record in result:
                        timeline.append({
                            "date": record["date"].isoformat(),
                            "relationship_count": record["relationship_count"],
                            "relationship_types": record["relationship_types"]
                        })

                    # Get entity creation timeline
                    entity_query = f"""
                        MATCH (e:Entity)
                        WHERE date(datetime(e.created_at)) >= date($start_date)
                        AND date(datetime(e.created_at)) <= date($end_date)
                        RETURN date(datetime(e.created_at)) as date,
                               count(e) as entity_count,
                               collect(DISTINCT e.entity_type) as entity_types
                        ORDER BY date
                    """

                    entity_result = session.run(
                        entity_query,
                        start_date=start_date.isoformat(),
                        end_date=end_date.isoformat()
                    )

                    entity_timeline = []
                    for record in entity_result:
                        entity_timeline.append({
                            "date": record["date"].isoformat(),
                            "entity_count": record["entity_count"],
                            "entity_types": record["entity_types"]
                        })

                    return {
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat(),
                        "relationship_timeline": timeline,
                        "entity_timeline": entity_timeline,
                        "total_days": len(timeline)
                    }
            else:
                # Fallback implementation
                return {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "message": "Temporal analysis requires Neo4j driver",
                    "relationship_timeline": [],
                    "entity_timeline": []
                }

        except Exception as e:
            logger.error(f"Error in temporal analysis: {e}")
            return {"error": str(e)}

    def search_semantic_patterns(self,
                                pattern: str,
                                entity_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Search for semantic patterns in the graph.

        Args:
            pattern: Pattern to search for (e.g., "PERSON works_at ORGANIZATION")
            entity_types: Filter by entity types

        Returns:
            Dictionary with matching patterns
        """
        try:
            # Parse pattern (simple implementation)
            # Expected format: "ENTITY_TYPE relationship ENTITY_TYPE"
            parts = pattern.split()
            if len(parts) != 3:
                return {"error": "Pattern must be in format 'ENTITY_TYPE relationship ENTITY_TYPE'"}

            source_type, relationship, target_type = parts

            # Build query
            query = """
                MATCH (source:Entity {entity_type: $source_type})
                MATCH (target:Entity {entity_type: $target_type})
                MATCH (source)-[r:RELATIONSHIP]->(target)
                WHERE r.relationship_type CONTAINS $relationship
                RETURN source, target, r
                LIMIT 100
            """

            if entity_types:
                # Filter to only include specified entity types
                if source_type not in entity_types or target_type not in entity_types:
                    return {"matches": [], "pattern": pattern, "message": "Entity types filtered out"}

            if hasattr(self.graph_db, 'driver'):
                with self.graph_db.driver.session(database=self.graph_db.database) as session:
                    result = session.run(
                        query,
                        source_type=source_type.upper(),
                        target_type=target_type.upper(),
                        relationship=relationship.lower()
                    )

                    matches = []
                    for record in result:
                        source_node = record["source"]
                        target_node = record["target"]
                        rel = record["r"]

                        match = {
                            "source": {
                                "id": source_node["id"],
                                "name": source_node["name"],
                                "type": source_node["entity_type"]
                            },
                            "target": {
                                "id": target_node["id"],
                                "name": target_node["name"],
                                "type": target_node["entity_type"]
                            },
                            "relationship": {
                                "type": rel["relationship_type"],
                                "confidence": rel.get("confidence")
                            }
                        }
                        matches.append(match)

                    return {
                        "pattern": pattern,
                        "matches": matches,
                        "total_matches": len(matches)
                    }
            else:
                # Fallback implementation
                source_entities = self.graph_db.find_entities(
                    {"entity_type": source_type.upper()},
                    limit=100
                )
                target_entities = self.graph_db.find_entities(
                    {"entity_type": target_type.upper()},
                    limit=100
                )

                matches = []
                for source in source_entities:
                    relationships = self.graph_db.find_relationships(
                        {"source_entity_id": source.id},
                        limit=100
                    )

                    for rel in relationships:
                        if relationship.lower() in rel.relationship_type.lower():
                            target = self.graph_db.get_entity(rel.target_entity_id)
                            if target and target.entity_type.upper() == target_type.upper():
                                matches.append({
                                    "source": {
                                        "id": source.id,
                                        "name": source.name,
                                        "type": source.entity_type
                                    },
                                    "target": {
                                        "id": target.id,
                                        "name": target.name,
                                        "type": target.entity_type
                                    },
                                    "relationship": {
                                        "type": rel.relationship_type,
                                        "confidence": rel.confidence
                                    }
                                })

                return {
                    "pattern": pattern,
                    "matches": matches[:100],
                    "total_matches": len(matches)
                }

        except Exception as e:
            logger.error(f"Error searching semantic patterns: {e}")
            return {"error": str(e)}

    def get_graph_insights(self, document_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get insights and analytics about the graph.

        Args:
            document_id: Optional document filter

        Returns:
            Dictionary with insights
        """
        try:
            # Get basic statistics
            stats = self.graph_db.get_graph_statistics(document_id)

            # Find most connected entities
            if hasattr(self.graph_db, 'driver'):
                with self.graph_db.driver.session(database=self.graph_db.database) as session:
                    # Most connected entities
                    degree_query = """
                        MATCH (e:Entity)
                        OPTIONAL MATCH (e)-[r:RELATIONSHIP]-()
                        RETURN e.id as entity_id, e.name as name, e.entity_type as type,
                               count(r) as degree
                        ORDER BY degree DESC
                        LIMIT 10
                    """

                    if document_id:
                        degree_query = """
                            MATCH (e:Entity {source_document: $document_id})
                            OPTIONAL MATCH (e)-[r:RELATIONSHIP]-()
                            RETURN e.id as entity_id, e.name as name, e.entity_type as type,
                                   count(r) as degree
                            ORDER BY degree DESC
                            LIMIT 10
                        """

                    params = {"document_id": document_id} if document_id else {}
                    degree_result = session.run(degree_query, **params)

                    most_connected = []
                    for record in degree_result:
                        most_connected.append({
                            "entity_id": record["entity_id"],
                            "name": record["name"],
                            "type": record["type"],
                            "degree": record["degree"]
                        })

                    # Most common relationship types
                    common_rels_query = """
                        MATCH ()-[r:RELATIONSHIP]->()
                        RETURN r.relationship_type as type, count(r) as count
                        ORDER BY count DESC
                        LIMIT 10
                    """

                    if document_id:
                        common_rels_query = """
                            MATCH ()-[r:RELATIONSHIP {source_document: $document_id}]->()
                            RETURN r.relationship_type as type, count(r) as count
                            ORDER BY count DESC
                            LIMIT 10
                        """

                    common_rels_result = session.run(common_rels_query, **params)

                    common_relationships = []
                    for record in common_rels_result:
                        common_relationships.append({
                            "type": record["type"],
                            "count": record["count"]
                        })

                    insights = {
                        "statistics": {
                            "total_entities": stats.total_entities,
                            "total_relationships": stats.total_relationships,
                            "unique_entity_types": len(stats.entity_types),
                            "unique_relationship_types": len(stats.relationship_types)
                        },
                        "most_connected_entities": most_connected,
                        "most_common_relationships": common_relationships,
                        "entity_type_distribution": stats.entity_types,
                        "relationship_type_distribution": stats.relationship_types,
                        "documents_processed": stats.documents_processed[:10]  # Top 10
                    }

                    return insights
            else:
                # Fallback insights
                insights = {
                    "statistics": {
                        "total_entities": stats.total_entities,
                        "total_relationships": stats.total_relationships,
                        "unique_entity_types": len(stats.entity_types),
                        "unique_relationship_types": len(stats.relationship_types)
                    },
                    "most_connected_entities": [],
                    "most_common_relationships": [],
                    "entity_type_distribution": stats.entity_types,
                    "relationship_type_distribution": stats.relationship_types,
                    "documents_processed": stats.documents_processed[:10],
                    "message": "Advanced insights require Neo4j driver"
                }

                return insights

        except Exception as e:
            logger.error(f"Error getting graph insights: {e}")
            return {"error": str(e)}

    def query_by_natural_language(self, question: str, document_id: Optional[str] = None):
        """根据自然语言问题查询知识图谱"""
        try:
            # 简单实现：关键词搜索
            # 提取可能的关键词
            keywords = self._extract_keywords_from_question(question)

            if not keywords:
                return self._fallback_search(question, document_id)

            # 尝试按关键词搜索实体
            results = []
            for keyword in keywords[:5]:  # 限制关键词数量
                filters = {"name": {"$contains": keyword}}
                logger.debug(f"Searching with filters: {filters}")
                entities = self.graph_db.find_entities(
                    filters,
                    limit=10
                )
                results.extend(entities)

            # 去重
            unique_results = []
            seen_ids = set()
            for entity in results:
                if entity.id not in seen_ids:
                    seen_ids.add(entity.id)
                    unique_results.append(entity)

            return unique_results[:50]  # 限制结果数量

        except Exception as e:
            logger.error(f"Error in natural language query: {e}")
            return self._fallback_search(question, document_id)

    def _extract_keywords_from_question(self, question: str) -> List[str]:
        """从问题中提取关键词"""
        # 移除常见停用词
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "is", "are", "was", "were", "be", "been", "being", "what", "who", "where", "when", "why", "how", "which", "do", "does", "did", "can", "could", "will", "would", "should", "may", "might", "must"}

        # 移除标点符号
        import string
        translator = str.maketrans('', '', string.punctuation)
        cleaned_question = question.translate(translator)

        # 简单分词
        words = cleaned_question.lower().split()
        keywords = [word for word in words if word not in stop_words and len(word) > 2]

        return keywords

    def _fallback_search(self, question: str, document_id: Optional[str] = None):
        """回退搜索策略"""
        try:
            # 尝试搜索所有实体，按名称相似度排序
            all_entities = self.graph_db.find_entities({}, limit=100)

            # 简单过滤：检查问题中是否包含实体名称
            question_lower = question.lower()
            matched_entities = []

            for entity in all_entities:
                if entity.name and entity.name.lower() in question_lower:
                    matched_entities.append(entity)
                elif document_id and hasattr(entity, 'source_document'):
                    if entity.source_document == document_id:
                        matched_entities.append(entity)

            return matched_entities[:20]

        except Exception as e:
            logger.error(f"Error in fallback search: {e}")
            return []

    def execute_custom_query(self, cypher_query: str, params: Optional[Dict] = None):
        """执行自定义Cypher查询"""
        try:
            if hasattr(self.graph_db, 'driver'):
                with self.graph_db.driver.session(database=self.graph_db.database) as session:
                    result = session.run(cypher_query, **(params or {}))

                    records = []
                    for record in result:
                        # 将记录转换为字典
                        record_dict = {}
                        for key in record.keys():
                            record_dict[key] = record[key]
                        records.append(record_dict)

                    return records
            else:
                logger.warning("Custom Cypher query requires Neo4j driver")
                return []

        except Exception as e:
            logger.error(f"Error executing custom query: {e}")
            return []

    def cleanup(self):
        """Cleanup resources."""
        if self.graph_db:
            self.graph_db.disconnect()
#!/usr/bin/env python3
"""
Test Neo4j queries directly.
"""

import os
import sys
from neo4j import GraphDatabase

# Set environment variable for Neo4j password
os.environ["NEO4J_PASSWORD"] = "neo4j168"

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.knowledge_graph.neo4j_adapter import Neo4jAdapter
from src.knowledge_graph.graph_builder import GraphBuilder

def test_direct_queries():
    """Test direct Neo4j queries."""
    print("=" * 60)
    print("DIRECT NEO4J QUERY TEST")
    print("=" * 60)

    # Initialize adapter
    adapter = Neo4jAdapter()
    if not adapter.connect():
        print("Failed to connect to Neo4j")
        return

    print("[OK] Connected to Neo4j")

    # Test 1: Find all entities without filters
    print("\n1. Testing find_entities with empty filters:")
    entities = adapter.find_entities({}, limit=100)
    print(f"   Found {len(entities)} entities")
    if entities:
        for i, entity in enumerate(entities[:3]):
            print(f"   Entity {i+1}: {entity.name} ({entity.entity_type})")
        if len(entities) > 3:
            print(f"   ... and {len(entities) - 3} more")

    # Test 2: Get entities by document
    print("\n2. Testing get_entities_by_document with 'test_document.txt':")
    doc_entities = adapter.get_entities_by_document("test_document.txt")
    print(f"   Found {len(doc_entities)} entities for document 'test_document.txt'")
    if doc_entities:
        for i, entity in enumerate(doc_entities[:5]):
            print(f"   Entity {i+1}: {entity.name} ({entity.entity_type}) - source: {entity.source_document}")

    # Test 3: Get all documents
    print("\n3. Testing get_all_documents:")
    stats = adapter.get_graph_statistics()
    if hasattr(stats, 'documents'):
        print(f"   Documents: {stats.documents}")
    else:
        print(f"   Statistics: {stats}")

    # Test 4: Test GraphBuilder
    print("\n4. Testing GraphBuilder.get_graph_for_visualization():")
    builder = GraphBuilder()
    graph_data = builder.get_graph_for_visualization()
    print(f"   Graph data nodes: {len(graph_data.get('nodes', []))}")
    print(f"   Graph data links: {len(graph_data.get('links', []))}")

    if graph_data.get('nodes'):
        print("   Sample nodes:")
        for i, node in enumerate(graph_data['nodes'][:3]):
            print(f"     Node {i+1}: {node.get('name')} ({node.get('type')})")

    # Test 5: Test with specific document
    print("\n5. Testing GraphBuilder.get_graph_for_visualization('test_document.txt'):")
    graph_data_doc = builder.get_graph_for_visualization("test_document.txt")
    print(f"   Graph data nodes: {len(graph_data_doc.get('nodes', []))}")
    print(f"   Graph data links: {len(graph_data_doc.get('links', []))}")

    adapter.disconnect()
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    test_direct_queries()
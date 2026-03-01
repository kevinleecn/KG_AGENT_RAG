#!/usr/bin/env python3
"""
Test Flask graph endpoint directly.
"""

import os
import sys
import requests

# Set environment variable for Neo4j password
os.environ["NEO4J_PASSWORD"] = "neo4j168"

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.knowledge_graph.graph_builder import GraphBuilder

def test_graph_builder_direct():
    """Test GraphBuilder directly."""
    print("=" * 60)
    print("DIRECT GRAPHBUILDER TEST")
    print("=" * 60)

    builder = GraphBuilder()
    print(f"Builder initialized, graph_db connected: {builder.graph_db.connected}")

    # Test without document_id
    graph_data = builder.get_graph_for_visualization()
    print(f"Graph data (no filter): {len(graph_data.get('nodes', []))} nodes, {len(graph_data.get('links', []))} links")

    # Test with document_id
    graph_data_doc = builder.get_graph_for_visualization("test_document.txt")
    print(f"Graph data (with doc filter): {len(graph_data_doc.get('nodes', []))} nodes, {len(graph_data_doc.get('links', []))} links")

    if graph_data_doc.get('nodes'):
        print("\nFirst 3 nodes:")
        for i, node in enumerate(graph_data_doc['nodes'][:3]):
            print(f"  {i+1}. {node.get('name')} ({node.get('type')})")

def test_flask_endpoint():
    """Test Flask endpoint."""
    print("\n" + "=" * 60)
    print("FLASK ENDPOINT TEST")
    print("=" * 60)

    base_url = "http://localhost:5000"

    try:
        # Test without document_id
        response = requests.get(f"{base_url}/graph/data", timeout=5)
        print(f"Response status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Success: {data.get('success')}")
            graph_data = data.get('graph_data', {})
            print(f"Nodes: {len(graph_data.get('nodes', []))}, Links: {len(graph_data.get('links', []))}")
        else:
            print(f"Error: {response.text}")

        # Test with document_id
        response2 = requests.get(f"{base_url}/graph/data?document_id=test_document.txt", timeout=5)
        print(f"\nResponse with document_id status: {response2.status_code}")
        if response2.status_code == 200:
            data2 = response2.json()
            print(f"Success: {data2.get('success')}")
            graph_data2 = data2.get('graph_data', {})
            print(f"Nodes: {len(graph_data2.get('nodes', []))}, Links: {len(graph_data2.get('links', []))}")
        else:
            print(f"Error: {response2.text}")

    except Exception as e:
        print(f"Error testing Flask endpoint: {e}")

if __name__ == "__main__":
    test_graph_builder_direct()
    test_flask_endpoint()
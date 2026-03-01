#!/usr/bin/env python3
"""
Simple test for Neo4j connection and knowledge graph display.
"""

import os
import sys
import requests
from neo4j import GraphDatabase

def test_neo4j():
    """Test Neo4j connection."""
    print("=" * 60)
    print("NEO4J CONNECTION TEST")
    print("=" * 60)

    uri = "bolt://localhost:7687"
    username = "neo4j"
    password = os.environ.get("NEO4J_PASSWORD", "neo4j168")

    print(f"URI: {uri}")
    print(f"Username: {username}")
    print(f"Password: {'*' * len(password)}")

    try:
        driver = GraphDatabase.driver(uri, auth=(username, password))
        with driver.session() as session:
            # Test connection
            result = session.run("RETURN 1 as test")
            test_value = result.single()["test"]
            print(f"[OK] Connection test: {test_value}")

            # Get version
            version_result = session.run("CALL dbms.components() YIELD name, versions RETURN name, versions[0] as version")
            version_record = version_result.single()
            if version_record:
                print(f"[OK] Neo4j version: {version_record['version']}")

            # Check data
            entity_count = session.run("MATCH (e:Entity) RETURN count(e) as count").single()["count"]
            relationship_count = session.run("MATCH ()-[r:RELATIONSHIP]->() RETURN count(r) as count").single()["count"]

            print(f"[OK] Data in database: {entity_count} entities, {relationship_count} relationships")

            driver.close()
            return True, entity_count, relationship_count

    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        return False, 0, 0

def test_flask():
    """Test Flask."""
    print("\n" + "=" * 60)
    print("FLASK APPLICATION")
    print("=" * 60)

    base_url = "http://localhost:5000"

    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"[OK] Flask running: {data.get('status', 'unknown')}")
            return True
        else:
            print(f"[ERROR] Flask HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"[ERROR] Flask: {e}")
        return False

def test_files():
    """Test uploaded files."""
    print("\n" + "=" * 60)
    print("UPLOADED FILES")
    print("=" * 60)

    base_url = "http://localhost:5000"

    try:
        response = requests.get(f"{base_url}/files", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                files = data.get('files', [])
                count = data.get('count', 0)
                parsed = sum(1 for f in files if f.get('parsed'))

                print(f"[OK] Files: {count} total, {parsed} parsed")
                return count, parsed
            else:
                print(f"[ERROR] Files API error: {data.get('error')}")
                return 0, 0
        else:
            print(f"[ERROR] Files HTTP {response.status_code}")
            return 0, 0
    except Exception as e:
        print(f"[ERROR] Files: {e}")
        return 0, 0

def test_graph():
    """Test graph endpoint."""
    print("\n" + "=" * 60)
    print("KNOWLEDGE GRAPH ENDPOINT")
    print("=" * 60)

    base_url = "http://localhost:5000"

    try:
        response = requests.get(f"{base_url}/graph/data", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                graph_data = data.get('graph_data', {})
                nodes = len(graph_data.get('nodes', []))
                links = len(graph_data.get('links', []))

                print(f"[OK] Graph endpoint: {nodes} nodes, {links} links")
                return True, nodes, links
            else:
                print(f"[ERROR] Graph API error: {data.get('error')}")
                return False, 0, 0
        else:
            print(f"[ERROR] Graph HTTP {response.status_code}")
            return False, 0, 0
    except Exception as e:
        print(f"[ERROR] Graph: {e}")
        return False, 0, 0

def main():
    """Run all tests."""
    print("KNOWLEDGE GRAPH DISPLAY - CONNECTION TEST")
    print("=" * 60)

    # Ensure password is set
    if "NEO4J_PASSWORD" not in os.environ:
        os.environ["NEO4J_PASSWORD"] = "neo4j168"

    # Run tests
    neo4j_ok, entities, rels = test_neo4j()
    flask_ok = test_flask()
    file_count, parsed_count = test_files()
    graph_ok, nodes, links = test_graph()

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    print(f"Neo4j Connection: {'PASS' if neo4j_ok else 'FAIL'}")
    print(f"Flask Application: {'PASS' if flask_ok else 'FAIL'}")
    print(f"Uploaded Files: {file_count} ({parsed_count} parsed)")
    print(f"Graph Endpoint: {'PASS' if graph_ok else 'FAIL'}")
    print(f"Data in Neo4j: {entities} entities, {rels} relationships")
    print(f"Graph returns: {nodes} nodes, {links} links")

    # Recommendations
    print("\n" + "=" * 60)
    print("RECOMMENDATIONS")
    print("=" * 60)

    if neo4j_ok:
        print("[OK] Neo4j connection is WORKING with password 'neo4j168'")
        print("  To make permanent, set environment variable:")
        print("    Windows: setx NEO4J_PASSWORD neo4j168")
        print("    Linux/Mac: export NEO4J_PASSWORD=neo4j168")
    else:
        print("[ERROR] Neo4j connection FAILED")
        print("  Check Neo4j service is running")
        print("  Verify password is 'neo4j168'")

    if flask_ok:
        print("[OK] Flask application is RUNNING on http://localhost:5000")
    else:
        print("[ERROR] Flask not running")
        print("  Start with: python app.py")

    if file_count > 0 and parsed_count == 0:
        print("[WARNING] No parsed files. Need to parse documents.")
        print("  Use web interface or API: POST /parse/<filename>")

    if entities == 0 and parsed_count > 0:
        print("[WARNING] Documents parsed but no data in Neo4j")
        print("  Check parsing logic and Neo4j insertion")

    if neo4j_ok and flask_ok and parsed_count > 0 and nodes > 0:
        print("[OK] Knowledge Graph display is FULLY WORKING!")
        print("  Open http://localhost:5000 to see graph data")

    # Exit code
    if neo4j_ok and flask_ok:
        print("\n[SUCCESS] Connection tests passed!")
        sys.exit(0)
    else:
        print("\n[FAILURE] Some tests failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
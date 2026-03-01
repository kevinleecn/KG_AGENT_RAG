#!/usr/bin/env python3
"""
Test and report on Neo4j connection and knowledge graph display functionality.
"""

import os
import sys
import requests
from neo4j import GraphDatabase

def test_neo4j_direct():
    """Test direct Neo4j connection."""
    print("=" * 60)
    print("NEO4J DIRECT CONNECTION TEST")
    print("=" * 60)

    uri = "bolt://localhost:7687"
    username = "neo4j"
    password = os.environ.get("NEO4J_PASSWORD", "neo4j168")

    print(f"URI: {uri}")
    print(f"Username: {username}")
    print(f"Password from env: {'*' * len(password) if password else 'None'}")

    try:
        driver = GraphDatabase.driver(uri, auth=(username, password))
        with driver.session() as session:
            # Test basic connection
            result = session.run("RETURN 1 as test")
            test_value = result.single()["test"]
            print(f"✓ Basic connection test: {test_value}")

            # Get Neo4j version
            version_result = session.run("CALL dbms.components() YIELD name, versions RETURN name, versions[0] as version")
            version_record = version_result.single()
            if version_record:
                print(f"✓ Neo4j version: {version_record['version']}")

            # Check if any data exists
            entity_count = session.run("MATCH (e:Entity) RETURN count(e) as count").single()["count"]
            relationship_count = session.run("MATCH ()-[r:RELATIONSHIP]->() RETURN count(r) as count").single()["count"]

            print(f"✓ Existing data: {entity_count} entities, {relationship_count} relationships")

            driver.close()
            return True, entity_count, relationship_count

    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False, 0, 0

def test_flask_health():
    """Test Flask application health."""
    print("\n" + "=" * 60)
    print("FLASK APPLICATION TEST")
    print("=" * 60)

    base_url = "http://localhost:5000"

    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Flask app is running: {data.get('status', 'unknown')}")
            return True
        else:
            print(f"✗ Flask health check failed: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Flask connection error: {e}")
        return False

def test_graph_endpoint():
    """Test graph data endpoint."""
    print("\n" + "=" * 60)
    print("KNOWLEDGE GRAPH ENDPOINT TEST")
    print("=" * 60)

    base_url = "http://localhost:5000"

    try:
        response = requests.get(f"{base_url}/graph/data", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                graph_data = data.get('graph_data', {})
                nodes = graph_data.get('nodes', [])
                links = graph_data.get('links', [])
                stats = graph_data.get('statistics', {})

                print(f"✓ Graph endpoint working")
                print(f"  - Nodes returned: {len(nodes)}")
                print(f"  - Links returned: {len(links)}")
                print(f"  - Document ID: {data.get('document_id', 'None')}")

                if stats:
                    print(f"  - Statistics: {stats}")

                return True, len(nodes), len(links)
            else:
                error = data.get('error', 'Unknown error')
                print(f"✗ Graph endpoint error: {error}")
                return False, 0, 0
        else:
            print(f"✗ HTTP {response.status_code} from graph endpoint")
            return False, 0, 0
    except Exception as e:
        print(f"✗ Graph endpoint error: {e}")
        return False, 0, 0

def check_uploaded_files():
    """Check uploaded files."""
    print("\n" + "=" * 60)
    print("UPLOADED FILES CHECK")
    print("=" * 60)

    base_url = "http://localhost:5000"

    try:
        response = requests.get(f"{base_url}/files", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                files = data.get('files', [])
                count = data.get('count', 0)
                parsed_count = sum(1 for f in files if f.get('parsed'))

                print(f"✓ Uploaded files: {count} total, {parsed_count} parsed")

                # Show first 3 files
                for i, file in enumerate(files[:3]):
                    filename = file.get('filename', 'Unknown')
                    parsed = file.get('parsed', False)
                    size = file.get('formatted_size', '0 Bytes')
                    print(f"  {i+1}. {filename} ({size}, {'Parsed' if parsed else 'Not parsed'})")

                if count > 3:
                    print(f"  ... and {count - 3} more files")

                return count, parsed_count
            else:
                print(f"✗ Files endpoint error: {data.get('error', 'Unknown')}")
                return 0, 0
        else:
            print(f"✗ HTTP {response.status_code} from files endpoint")
            return 0, 0
    except Exception as e:
        print(f"✗ Files endpoint error: {e}")
        return 0, 0

def main():
    """Run all tests and provide summary."""
    print("KNOWLEDGE GRAPH DISPLAY - CONNECTION TEST REPORT")
    print("=" * 60)

    # Set environment for Neo4j test
    if "NEO4J_PASSWORD" not in os.environ:
        os.environ["NEO4J_PASSWORD"] = "neo4j168"
        print("Note: Set NEO4J_PASSWORD environment variable to 'neo4j168'")

    results = {}

    # Run tests
    results['neo4j_direct'] = test_neo4j_direct()
    results['flask_health'] = test_flask_health()
    results['uploaded_files'] = check_uploaded_files()
    results['graph_endpoint'] = test_graph_endpoint()

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY AND RECOMMENDATIONS")
    print("=" * 60)

    neo4j_ok, entity_count, rel_count = results['neo4j_direct']
    flask_ok = results['flask_health']
    file_count, parsed_count = results['uploaded_files']
    graph_ok, node_count, link_count = results['graph_endpoint']

    print(f"1. Neo4j Connection: {'✓ OK' if neo4j_ok else '✗ FAILED'}")
    if neo4j_ok:
        print(f"   - Database contains: {entity_count} entities, {rel_count} relationships")

    print(f"2. Flask Application: {'✓ OK' if flask_ok else '✗ FAILED'}")

    print(f"3. Uploaded Files: {file_count} files ({parsed_count} parsed)")
    if file_count > 0 and parsed_count == 0:
        print("   ⚠ Warning: No parsed files. Need to parse documents to generate knowledge graph.")

    print(f"4. Graph Endpoint: {'✓ OK' if graph_ok else '✗ FAILED'}")
    if graph_ok:
        print(f"   - Returns: {node_count} nodes, {link_count} links")

    # Recommendations
    print("\n" + "-" * 60)
    print("RECOMMENDATIONS:")
    print("-" * 60)

    if not neo4j_ok:
        print("1. Fix Neo4j connection:")
        print("   - Verify Neo4j service is running")
        print("   - Check password (should be 'neo4j168')")
        print("   - Set NEO4J_PASSWORD environment variable")
        print("   - Test with: python test_neo4j_auth.py neo4j168")

    if not flask_ok:
        print("2. Start Flask application:")
        print("   - Run: python app.py")
        print("   - Or use: start_flask.bat (sets environment variables)")

    if file_count == 0:
        print("3. Upload documents through web interface:")
        print("   - Open: http://localhost:5000")
        print("   - Use upload form to add documents")

    if file_count > 0 and parsed_count == 0:
        print("4. Parse at least one document:")
        print("   - Use web interface: Click 'Parse' button on uploaded file")
        print("   - Or use API: POST /parse/<filename>")
        print("   - Example: curl -X POST http://localhost:5000/parse/2.docx")

    if neo4j_ok and flask_ok and parsed_count > 0 and node_count == 0:
        print("5. Check document parsing:")
        print("   - Parsing may not be extracting text (text_length: 0)")
        print("   - Try different file format (plain text .txt file)")
        print("   - Check parsing logs for errors")

    if neo4j_ok and flask_ok and node_count > 0:
        print("5. Knowledge Graph display is WORKING!")
        print("   - Open: http://localhost:5000")
        print("   - Select parsed document")
        print("   - Knowledge Graph Nodes window should show entities")

    print("\n" + "=" * 60)
    print("Environment setup for permanent fix:")
    print("=" * 60)
    print("To make Neo4j password permanent, set environment variable:")
    print("  Windows (Command Prompt):")
    print("    setx NEO4J_PASSWORD neo4j168")
    print("  Windows (PowerShell):")
    print("    [Environment]::SetEnvironmentVariable('NEO4J_PASSWORD', 'neo4j168', 'User')")
    print("  Linux/Mac:")
    print("    export NEO4J_PASSWORD=neo4j168")
    print("    echo 'export NEO4J_PASSWORD=neo4j168' >> ~/.bashrc")

    # Exit code
    if neo4j_ok and flask_ok:
        print("\n✓ Overall status: CONNECTION TESTS PASSED")
        sys.exit(0)
    else:
        print("\n✗ Overall status: SOME TESTS FAILED")
        sys.exit(1)

if __name__ == "__main__":
    main()
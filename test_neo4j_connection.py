#!/usr/bin/env python3
"""
Test Neo4j connection after fixing import conflict
"""

import sys
import os

# Set environment variables as in app.py
os.environ["NEO4J_PASSWORD"] = "neo4j168"
os.environ["NEO4J_USER"] = "neo4j"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.knowledge_graph.neo4j_adapter import Neo4jAdapter

def test_neo4j_connection():
    """Test if Neo4j connection works after import fix"""
    print("Testing Neo4j connection...")

    try:
        # Create adapter instance
        adapter = Neo4jAdapter()

        # Try to connect
        print(f"Connecting to Neo4j at: {adapter.uri}")
        print(f"Username: {adapter.username}")

        connected = adapter.connect()

        if connected:
            print("[SUCCESS] Connected to Neo4j!")

            # Test health check
            health = adapter.health_check()
            print(f"Health check: {health}")

            # Disconnect
            adapter.disconnect()
            print("Disconnected from Neo4j")
            return True
        else:
            print("[FAILED] Could not connect to Neo4j")
            print("Possible issues:")
            print("1. Neo4j service not running")
            print("2. Wrong credentials (user: neo4j, password: password)")
            print("3. Network connectivity issue")
            return False

    except Exception as e:
        print(f"[ERROR] {e}")
        print("\nDetailed error information:")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_neo4j_connection()
    sys.exit(0 if success else 1)
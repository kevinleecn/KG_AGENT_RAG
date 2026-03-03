#!/usr/bin/env python3
"""
Test Neo4j authentication with custom credentials.
"""

import os
from neo4j import GraphDatabase

def test_neo4j_connection(uri="bolt://localhost:7687", username="neo4j", password=None):
    """Test Neo4j connection with given credentials."""
    print(f"Testing Neo4j connection to: {uri}")
    print(f"Username: {username}")
    print(f"Password: {'*' * len(password) if password else 'None'}")

    if not password:
        print("ERROR: No password provided")
        return False

    try:
        # Create driver
        driver = GraphDatabase.driver(uri, auth=(username, password))

        # Test connection
        with driver.session() as session:
            result = session.run("RETURN 1 as test")
            test_value = result.single()["test"]

            if test_value == 1:
                print("SUCCESS: Connected to Neo4j!")

                # Get Neo4j version
                version_result = session.run("CALL dbms.components() YIELD name, versions RETURN name, versions[0] as version")
                version_record = version_result.single()
                if version_record:
                    print(f"Neo4j version: {version_record['version']}")

                driver.close()
                return True
            else:
                print("ERROR: Connection test failed")
                driver.close()
                return False

    except Exception as e:
        print(f"ERROR: {e}")
        return False

if __name__ == "__main__":
    import sys

    # Get password from command line or use default
    if len(sys.argv) > 1:
        password = sys.argv[1]
    else:
        # Try environment variable
        password = os.environ.get("NEO4J_PASSWORD", "password")

    # Test with default URI and username
    success = test_neo4j_connection(
        uri="bolt://localhost:7687",
        username="neo4j",
        password=password
    )

    sys.exit(0 if success else 1)
#!/usr/bin/env python3
"""
Test the graph endpoint to see if it returns data.
"""

import requests
import json
import sys

def test_graph_endpoint(document_id=None):
    """Test /graph/data endpoint."""
    base_url = "http://localhost:5000"

    url = f"{base_url}/graph/data"
    if document_id:
        url += f"?document_id={document_id}"

    print(f"Testing URL: {url}")

    try:
        response = requests.get(url, timeout=10)
        print(f"Status code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"Success: {data.get('success')}")

            if data.get('success'):
                graph_data = data.get('graph_data', {})
                nodes = graph_data.get('nodes', [])
                links = graph_data.get('links', [])
                stats = graph_data.get('statistics', {})

                print(f"Graph data: {len(nodes)} nodes, {len(links)} links")
                print(f"Statistics: {stats}")

                # Print first few nodes if available
                for i, node in enumerate(nodes[:5]):
                    print(f"  Node {i}: {node.get('name')} ({node.get('type')})")

                return len(nodes) > 0
            else:
                print(f"Error: {data.get('error')}")
                return False
        else:
            print(f"HTTP error: {response.status_code}")
            print(f"Response: {response.text[:200]}")
            return False

    except Exception as e:
        print(f"Request failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_files_endpoint():
    """Test /files endpoint to see available documents."""
    base_url = "http://localhost:5000"

    try:
        response = requests.get(f"{base_url}/files", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                files = data.get('files', [])
                parsed_files = [f for f in files if f.get('parsed')]
                print(f"Files: {len(files)} total, {len(parsed_files)} parsed")

                for f in parsed_files[:5]:
                    print(f"  Parsed: {f.get('filename')} - {f.get('parsed_at')}")

                return [f.get('filename') for f in parsed_files]
        return []
    except Exception as e:
        print(f"Files endpoint error: {e}")
        return []

def main():
    """Run tests."""
    print("GRAPH ENDPOINT TEST")
    print("=" * 60)

    # First, get parsed files
    parsed_files = test_files_endpoint()

    print("\n" + "=" * 60)
    print("TESTING GRAPH ENDPOINT")
    print("=" * 60)

    # Test without document filter
    print("\n--- Testing without document filter ---")
    general_ok = test_graph_endpoint()

    # Test with each parsed document
    for filename in parsed_files[:3]:  # Limit to first 3
        print(f"\n--- Testing with document: {filename} ---")
        test_graph_endpoint(filename)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    if general_ok:
        print("[SUCCESS] Graph endpoint returns data!")
        sys.exit(0)
    else:
        print("[FAILURE] Graph endpoint returns no data")
        sys.exit(1)

if __name__ == "__main__":
    main()
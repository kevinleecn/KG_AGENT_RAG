#!/usr/bin/env python3
"""
Test script for Knowledge Graph display functionality
Tests the complete flow from file upload to graph visualization
"""

import sys
import os
import json
import requests
import time
import subprocess
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configuration
BASE_URL = "http://localhost:5000"
TEST_TIMEOUT = 10  # seconds
SAMPLE_PDF_PATH = None  # Optional: path to a test PDF file

def print_header(title):
    """Print formatted header"""
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)

def print_success(message):
    """Print success message"""
    print(f"[OK] {message}")

def print_warning(message):
    """Print warning message"""
    print(f"[!] {message}")

def print_error(message):
    """Print error message"""
    print(f"[ERROR] {message}")

def check_flask_running():
    """Check if Flask application is running"""
    print_header("1. Checking Flask Application")

    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_success(f"Flask app is running: {data.get('status', 'unknown')}")
            return True
        else:
            print_error(f"Flask health check failed: HTTP {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_error("Flask application is not running")
        print("Please start the Flask app: python app.py")
        return False
    except Exception as e:
        print_error(f"Error checking Flask: {str(e)}")
        return False

def get_uploaded_files():
    """Get list of uploaded files"""
    print_header("2. Checking Uploaded Files")

    try:
        response = requests.get(f"{BASE_URL}/files", timeout=TEST_TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                files = data.get('files', [])
                count = data.get('count', 0)

                print_success(f"Found {count} uploaded file(s)")

                # Display file info
                for file in files[:5]:  # Show first 5 files
                    filename = file.get('filename', 'Unknown')
                    parsed = file.get('parsed', False)
                    size = file.get('formatted_size', '0 Bytes')
                    status = "Parsed" if parsed else "Not parsed"
                    print(f"   - {filename} ({size}, {status})")

                if count > 5:
                    print(f"   ... and {count - 5} more files")

                return files
            else:
                print_error(f"API returned error: {data.get('error', 'Unknown')}")
                return []
        else:
            print_error(f"Failed to get files: HTTP {response.status_code}")
            return []
    except Exception as e:
        print_error(f"Error getting files: {str(e)}")
        return []

def test_graph_data_endpoint(filename=None):
    """Test the /graph/data endpoint"""
    print_header("3. Testing Graph Data Endpoint")

    url = f"{BASE_URL}/graph/data"
    if filename:
        url += f"?document_id={requests.utils.quote(filename)}"
        print(f"Testing with document: {filename}")
    else:
        print("Testing all documents (no document_id)")

    try:
        response = requests.get(url, timeout=TEST_TIMEOUT)

        if response.status_code == 200:
            data = response.json()

            if data.get('success'):
                graph_data = data.get('graph_data', {})
                nodes = graph_data.get('nodes', [])
                links = graph_data.get('links', [])
                stats = graph_data.get('statistics', {})

                print_success(f"Graph data retrieved successfully")
                print(f"   - Nodes: {len(nodes)}")
                print(f"   - Links: {len(links)}")
                print(f"   - Document ID: {data.get('document_id', 'None')}")

                # Show sample node if available
                if nodes:
                    sample_node = nodes[0]
                    print(f"   - Sample node: {sample_node.get('name', 'Unknown')} ({sample_node.get('type', 'Unknown')})")

                # Show statistics
                if stats:
                    print(f"   - Statistics: {stats}")

                return True, data
            else:
                error_msg = data.get('error', 'Unknown error')
                print_error(f"Graph data endpoint error: {error_msg}")

                # Check if it's a Neo4j connection error
                if "Not connected to Neo4j" in error_msg or "Failed to connect" in error_msg:
                    print("   → This indicates Neo4j database connection issue")
                    print("   → Please ensure Neo4j service is running")

                return False, data
        else:
            print_error(f"HTTP {response.status_code} from graph data endpoint")
            try:
                error_data = response.json()
                print_error(f"Error details: {error_data}")
            except:
                print_error(f"Response: {response.text[:200]}")
            return False, None
    except Exception as e:
        print_error(f"Error testing graph data endpoint: {str(e)}")
        return False, None

def test_neo4j_connection():
    """Test direct Neo4j connection"""
    print_header("4. Testing Neo4j Database Connection")

    try:
        from src.knowledge_graph.neo4j_adapter import Neo4jAdapter

        adapter = Neo4jAdapter()

        print(f"Connecting to: {adapter.uri}")
        print(f"Username: {adapter.username}")

        connected = adapter.connect()

        if connected:
            print_success("Neo4j connection successful")

            # Get statistics
            stats = adapter.get_graph_statistics()
            print(f"   - Total entities: {stats.total_entities}")
            print(f"   - Total relationships: {stats.total_relationships}")
            print(f"   - Documents processed: {len(stats.documents_processed)}")

            if stats.documents_processed:
                print(f"   - Documents: {', '.join(stats.documents_processed[:3])}")
                if len(stats.documents_processed) > 3:
                    print(f"     ... and {len(stats.documents_processed) - 3} more")

            adapter.disconnect()
            return True
        else:
            print_error("Failed to connect to Neo4j")
            print("Possible solutions:")
            print("   1. Start Neo4j service")
            print("   2. Check credentials (default: neo4j/password)")
            print("   3. Verify Neo4j is running on bolt://localhost:7687")
            return False
    except ImportError as e:
        print_error(f"Failed to import Neo4j adapter: {str(e)}")
        return False
    except Exception as e:
        print_error(f"Neo4j connection error: {str(e)}")
        return False

def test_file_parsing(filename):
    """Test parsing a specific file"""
    print_header(f"5. Testing File Parsing: {filename}")

    try:
        url = f"{BASE_URL}/parse/{requests.utils.quote(filename)}"
        response = requests.post(url, timeout=30)  # Longer timeout for parsing

        if response.status_code == 200:
            data = response.json()

            if data.get('success'):
                print_success(f"File parsed successfully: {filename}")
                print(f"   - Entities extracted: {data.get('entity_count', 0)}")
                print(f"   - Relationships extracted: {data.get('relationship_count', 0)}")
                print(f"   - Processing time: {data.get('processing_time', 0):.2f}s")
                return True
            else:
                error_msg = data.get('error', 'Unknown error')
                print_error(f"Parsing failed: {error_msg}")
                return False
        else:
            print_error(f"HTTP {response.status_code} from parsing endpoint")
            return False
    except Exception as e:
        print_error(f"Error testing file parsing: {str(e)}")
        return False

def test_frontend_integration():
    """Simulate frontend behavior for graph display"""
    print_header("6. Testing Frontend Integration")

    # Get uploaded files
    files = get_uploaded_files()
    if not files:
        print_warning("No uploaded files found for frontend test")
        return False

    # Find a parsed file
    parsed_files = [f for f in files if f.get('parsed')]
    if not parsed_files:
        print_warning("No parsed files found. Frontend will show 'No nodes available'")
        print("To test frontend display, parse a file first.")
        return False

    # Test with first parsed file
    test_file = parsed_files[0]
    filename = test_file['filename']

    print(f"Testing frontend flow with file: {filename}")

    # Simulate frontend API call
    print("Simulating frontend graph data request...")
    success, graph_data = test_graph_data_endpoint(filename)

    if success:
        print_success("Frontend integration test passed")
        print("Expected frontend behavior:")
        print("   1. Knowledge Graph Nodes card should be visible")
        print("   2. Nodes table should show entities")
        print("   3. Node count badges should update")
        print("   4. Clicking 'Details' should open modal")
        return True
    else:
        print_error("Frontend integration test failed")
        return False

def run_comprehensive_test():
    """Run all tests in sequence"""
    print_header("KNOWLEDGE GRAPH DISPLAY TEST SUITE")
    print("Testing complete functionality of graph visualization")

    results = {
        'flask_running': False,
        'files_available': False,
        'neo4j_connected': False,
        'graph_endpoint_working': False,
        'frontend_integration': False
    }

    # 1. Check Flask
    results['flask_running'] = check_flask_running()
    if not results['flask_running']:
        print("\n[CRITICAL] Flask application not running. Aborting tests.")
        return results

    # 2. Get uploaded files
    files = get_uploaded_files()
    results['files_available'] = len(files) > 0

    # 3. Test Neo4j connection
    results['neo4j_connected'] = test_neo4j_connection()

    # 4. Test graph data endpoint
    if files:
        # Test with first file (if parsed) or without document_id
        parsed_files = [f for f in files if f.get('parsed')]
        test_filename = parsed_files[0]['filename'] if parsed_files else None

        success, _ = test_graph_data_endpoint(test_filename)
        results['graph_endpoint_working'] = success
    else:
        print_warning("Skipping graph endpoint test: No files available")

    # 5. Test frontend integration
    if results['graph_endpoint_working']:
        results['frontend_integration'] = test_frontend_integration()

    # Summary
    print_header("TEST SUMMARY")

    total_tests = len(results)
    passed_tests = sum(1 for v in results.values() if v)

    print(f"Tests passed: {passed_tests}/{total_tests}")

    for test_name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {test_name:30} [{status}]")

    # Recommendations
    print_header("RECOMMENDATIONS")

    if not results['flask_running']:
        print("1. Start Flask application: python app.py")

    if not results['files_available']:
        print("2. Upload at least one document through the web interface")

    if not results['neo4j_connected']:
        print("3. Start Neo4j service and verify connection")
        print("   Default: bolt://localhost:7687, user: neo4j, password: password")

    if results['files_available'] and not results['graph_endpoint_working']:
        files = get_uploaded_files()  # Refresh list
        parsed_files = [f for f in files if f.get('parsed')]
        if not parsed_files:
            print("4. Parse an uploaded file to generate graph data")
            print("   Use: POST /parse/<filename> or parse through web interface")

    if results['graph_endpoint_working'] and not results['frontend_integration']:
        print("5. Check browser console for JavaScript errors")
        print("6. Verify frontend JavaScript is loaded correctly")

    return results

def quick_test():
    """Quick test focusing on graph display functionality"""
    print_header("QUICK GRAPH DISPLAY TEST")

    # Check Flask
    if not check_flask_running():
        return False

    # Get files
    files = get_uploaded_files()
    if not files:
        print_warning("No files uploaded. Upload a document first.")
        return False

    # Find parsed file
    parsed_files = [f for f in files if f.get('parsed')]
    if not parsed_files:
        print_warning("No parsed files found.")
        print("To test graph display, parse a file first.")
        print("Options:")
        print("  1. Use web interface to parse")
        print("  2. Call API: POST /parse/<filename>")
        print("  3. Run: python -c \"import requests; requests.post('http://localhost:5000/parse/FILENAME')\"")
        return False

    # Test graph endpoint
    test_file = parsed_files[0]
    success, data = test_graph_data_endpoint(test_file['filename'])

    if success:
        print_success("Graph display functionality is WORKING!")
        print("\nNext steps:")
        print("  1. Open browser: http://localhost:5000")
        print("  2. Click the parsed file in 'Uploaded Files' list")
        print("  3. Knowledge Graph Nodes window should show entities")
        print("  4. Use chat window to ask questions about the document")
        return True
    else:
        print_error("Graph display functionality is NOT working")
        return False

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test Knowledge Graph display functionality")
    parser.add_argument("--quick", action="store_true", help="Run quick test only")
    parser.add_argument("--parse", type=str, help="Parse a specific filename")
    parser.add_argument("--graph", type=str, help="Test graph data for specific filename")

    args = parser.parse_args()

    if args.parse:
        # Test parsing a specific file
        check_flask_running()
        test_file_parsing(args.parse)
    elif args.graph:
        # Test graph data for specific file
        check_flask_running()
        test_graph_data_endpoint(args.graph)
    elif args.quick:
        # Quick test
        success = quick_test()
        sys.exit(0 if success else 1)
    else:
        # Comprehensive test
        results = run_comprehensive_test()
        sys.exit(0 if all(results.values()) else 1)
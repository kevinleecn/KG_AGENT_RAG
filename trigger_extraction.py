#!/usr/bin/env python3
"""
Trigger knowledge extraction for readme.txt via API.
"""

import requests
import json
import sys
import time

def trigger_extraction(filename='readme.txt'):
    """Trigger knowledge extraction for a file."""
    url = f'http://localhost:5000/graph/extract/{filename}'
    print(f"Triggering extraction for {filename}...")
    print(f"URL: {url}")

    # Set long timeout for LLM processing
    timeout = 300  # 5 minutes

    try:
        start_time = time.time()
        response = requests.get(url, timeout=timeout)
        elapsed = time.time() - start_time

        print(f"Response received after {elapsed:.1f} seconds")
        print(f"Status code: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"Success: {result.get('success', False)}")

            if result.get('success', False):
                print("✅ Extraction successful!")
                if 'extraction_result' in result:
                    extraction = result['extraction_result']
                    if 'statistics' in extraction:
                        stats = extraction['statistics']
                        print(f"   Entities: {stats.get('total_entities', 0)}")
                        print(f"   Relationships: {stats.get('total_relationships', 0)}")
                        print(f"   Triplets: {stats.get('total_triplets', 0)}")
                return True
            else:
                error = result.get('error', 'Unknown error')
                print(f"❌ Extraction failed: {error}")
                return False
        else:
            print(f"❌ HTTP error: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return False

    except requests.exceptions.Timeout:
        elapsed = time.time() - start_time
        print(f"⏱️ Request timed out after {elapsed:.1f} seconds")
        print("This is normal for first-time LLM extraction.")
        print("Extraction may still be running in background.")
        print("Check the Flask app logs for progress.")
        return None  # Timeout, extraction may still be running

    except Exception as e:
        print(f"❌ Error triggering extraction: {e}")
        return False

def check_file_state(filename='readme.txt'):
    """Check current file state."""
    print(f"\nChecking current state for {filename}...")
    try:
        # Try to get state from parsing_state.json
        import os
        state_file = 'data/parsed/parsing_state.json'
        if os.path.exists(state_file):
            with open(state_file, 'r', encoding='utf-8') as f:
                state_data = json.load(f)

            if filename in state_data:
                state = state_data[filename]
                print(f"   Parsed: {state.get('parsed', False)}")
                print(f"   Knowledge extracted: {state.get('knowledge_extracted', False)}")
                if state.get('knowledge_extracted', False):
                    print(f"   Entity count: {state.get('entity_count', 0)}")
                    print(f"   Relationship count: {state.get('relationship_count', 0)}")
                return state
        print(f"   File not found in state")
        return None
    except Exception as e:
        print(f"   Error reading state: {e}")
        return None

def main():
    print("=" * 80)
    print("Trigger Knowledge Extraction")
    print("=" * 80)

    filename = 'readme.txt'

    # Check current state
    state = check_file_state(filename)
    if state and state.get('knowledge_extracted', False):
        print(f"\n{filename} already has extracted knowledge.")
        choice = input("Trigger extraction anyway? (y/n): ")
        if choice.lower() != 'y':
            return True

    # Trigger extraction
    result = trigger_extraction(filename)

    if result is None:
        # Timeout - extraction may still be running
        print("\n⏳ Extraction is taking longer than expected.")
        print("Please check the Flask app logs for progress.")
        print("You can also check the web interface for status updates.")
        return True  # Timeout is not necessarily failure

    elif result:
        print("\n✅ Extraction completed successfully!")
        # Check updated state
        check_file_state(filename)
        return True
    else:
        print("\n❌ Extraction failed.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
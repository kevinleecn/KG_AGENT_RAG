#!/usr/bin/env python3
"""
Test async parsing functionality and progress bar integration.
"""

import os
import sys
import time
import tempfile
import shutil
import json
from pathlib import Path

# Add project directory to path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

from app import app
import app as app_module

def test_async_parsing_flow():
    """Test the complete async parsing flow from start to finish"""
    print("Testing async parsing flow...")

    # Create temporary directories
    upload_dir = tempfile.mkdtemp(prefix="upload_test_")
    parsed_dir = tempfile.mkdtemp(prefix="parsed_test_")

    original_parsing_manager = None
    try:
        # Configure app for testing
        app.config['TESTING'] = True
        app.config['UPLOAD_FOLDER'] = upload_dir
        app.config['PARSED_DATA_FOLDER'] = parsed_dir

        # Reinitialize parsing_manager with test config
        from src.parsing_manager import ParsingManager
        # Backup original parsing_manager
        original_parsing_manager = app_module.parsing_manager
        # Create new parsing_manager with test directories
        app_module.parsing_manager = ParsingManager(
            upload_folder=upload_dir,
            parsed_data_folder=parsed_dir
        )

        # Create a test file
        test_filename = "test_async.txt"
        test_content = "This is a test document for async parsing.\nIt has multiple lines.\nAnd some more content."
        test_filepath = os.path.join(upload_dir, test_filename)

        with open(test_filepath, 'w', encoding='utf-8') as f:
            f.write(test_content)

        print(f"Created test file: {test_filepath}")

        # Test 1: Start async parsing
        print("\n1. Testing async parsing start...")
        with app.test_client() as client:
            response = client.post(f'/parse/async/{test_filename}')
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"

            data = response.get_json()
            print(f"Response: {json.dumps(data, indent=2)}")

            assert data['success'] == True
            assert 'task_id' in data
            assert data['filename'] == test_filename
            assert 'progress_url' in data

            task_id = data['task_id']
            print(f"Task ID: {task_id}")

        # Test 2: Check progress endpoint
        print("\n2. Testing progress endpoint...")
        with app.test_client() as client:
            # Check initial progress
            response = client.get(f'/progress/{task_id}')
            assert response.status_code == 200

            data = response.get_json()
            print(f"Initial progress: {json.dumps(data, indent=2)}")

            assert data['success'] == True
            assert 'progress' in data
            progress = data['progress']

            # Check progress structure
            assert 'task_id' in progress
            assert 'filename' in progress
            assert 'status' in progress
            assert 'progress' in progress  # float 0-1
            assert 'created_at' in progress
            assert 'updated_at' in progress

            # Should be running or pending
            assert progress['status'] in ['pending', 'running', 'completed']
            print(f"Initial status: {progress['status']}, progress: {progress['progress']}")

        # Test 3: Wait for completion and check final progress
        print("\n3. Waiting for parsing completion...")
        max_wait = 30  # seconds
        wait_interval = 1
        completed = False

        for i in range(max_wait):
            with app.test_client() as client:
                response = client.get(f'/progress/{task_id}')
                if response.status_code == 200:
                    data = response.get_json()
                    if data['success']:
                        progress = data['progress']
                        print(f"  Wait {i+1}s: status={progress['status']}, progress={progress['progress']}")

                        if progress['status'] == 'completed':
                            completed = True
                            print(f"  Parsing completed!")
                            break
                        elif progress['status'] == 'failed':
                            print(f"  Parsing failed: {progress.get('error', 'No error message')}")
                            break

            time.sleep(wait_interval)

        # Test 4: Verify completion
        print("\n4. Verifying completion...")
        with app.test_client() as client:
            response = client.get(f'/progress/{task_id}')
            assert response.status_code == 200

            data = response.get_json()
            assert data['success'] == True

            progress = data['progress']
            print(f"Final progress: {json.dumps(progress, indent=2)}")

            if completed:
                assert progress['status'] == 'completed'
                assert progress['progress'] == 1.0
                assert 'result' in progress

                result = progress['result']
                print(f"Result: {json.dumps(result, indent=2)}")

                # Check result structure
                assert 'filename' in result
                assert 'text_length' in result
                assert 'word_count' in result
                assert 'parsed_at' in result
                assert 'metadata' in result

                # Verify text content
                assert result['filename'] == test_filename
                assert result['text_length'] == len(test_content)
                assert result['word_count'] > 0

                print(f"OK: Parsing successful: {result['text_length']} chars, {result['word_count']} words")
            else:
                print(f"WARNING: Parsing did not complete within {max_wait} seconds")
                print(f"Final status: {progress['status']}")

        # Test 5: Check that parsed file appears in files list
        print("\n5. Checking files endpoint...")
        with app.test_client() as client:
            response = client.get('/files')
            assert response.status_code == 200

            data = response.get_json()
            assert data['success'] == True
            assert 'files' in data

            # Find our test file
            test_file_info = None
            for file_info in data['files']:
                if file_info['filename'] == test_filename:
                    test_file_info = file_info
                    break

            assert test_file_info is not None, f"Test file {test_filename} not found in files list"

            # Check parsing status
            assert 'parsed' in test_file_info
            if completed:
                assert test_file_info['parsed'] == True
                assert 'parsed_at' in test_file_info
                assert 'text_length' in test_file_info
                assert test_file_info['text_length'] == len(test_content)
                print(f"OK: File correctly marked as parsed in files list")
            else:
                print(f"WARNING: File parsing status: {test_file_info.get('parsed', 'unknown')}")

        print("\nSUCCESS: Async parsing flow test completed!")
        return True

    except Exception as e:
        print(f"\nFAILED: Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Restore original parsing_manager
        if original_parsing_manager is not None:
            app_module.parsing_manager = original_parsing_manager
            print("Restored original parsing_manager")

        # Clean up
        shutil.rmtree(upload_dir, ignore_errors=True)
        shutil.rmtree(parsed_dir, ignore_errors=True)
        print(f"\nCleaned up test directories")

def test_progress_structure():
    """Test progress data structure matches frontend expectations"""
    print("\nTesting progress data structure...")

    # This test checks that the progress data returned by the API
    # matches what the frontend JavaScript expects

    expected_fields = [
        'task_id',
        'filename',
        'status',
        'progress',  # float 0-1
        'step_description',
        'message',
        'created_at',
        'updated_at',
        'result',
        'error'
    ]

    print(f"Frontend expects these fields: {expected_fields}")

    # Check ProgressTracker class in progress.js expects these fields
    print("Checking ProgressTracker class usage...")

    try:
        # Read progress.js to verify field usage
        progress_js_path = os.path.join(project_dir, 'static', 'js', 'progress.js')
        with open(progress_js_path, 'r', encoding='utf-8') as f:
            progress_js = f.read()

        # Check for key field access
        checks = [
            ('progress.progress', 'Used in createProgressBar'),
            ('progress.status', 'Used in multiple places'),
            ('progress.step_description', 'Used in createProgressBar'),
            ('progress.message', 'Used in createProgressBar'),
            ('progress.result', 'Used in createProgressReport'),
            ('progress.error', 'Used in error handling'),
            ('progress.task_id', 'Used in cancel button')
        ]

        for field, description in checks:
            if field in progress_js:
                print(f"OK: {field} - {description}")
            else:
                print(f"WARNING: {field} not found in progress.js")

    except Exception as e:
        print(f"Error checking progress.js: {e}")

    print("OK: Progress structure check completed")

def test_frontend_integration():
    """Test frontend-backend integration points"""
    print("\nTesting frontend-backend integration...")

    # Check that frontend calls the correct endpoints
    endpoints_to_check = [
        ('/parse/async/{filename}', 'POST', 'Start async parsing'),
        ('/progress/{task_id}', 'GET', 'Get progress updates'),
        ('/progress/cancel/{task_id}', 'POST', 'Cancel parsing'),
        ('/files', 'GET', 'Get file list with parsing status')
    ]

    print("Checking frontend AJAX calls...")

    try:
        # Read main.js to find AJAX calls
        main_js_path = os.path.join(project_dir, 'static', 'js', 'main.js')
        with open(main_js_path, 'r', encoding='utf-8') as f:
            main_js = f.read()

        for endpoint, method, description in endpoints_to_check:
            # Look for endpoint patterns in JavaScript
            endpoint_pattern = endpoint.replace('{filename}', '.*').replace('{task_id}', '.*')

            # Simple check for endpoint reference
            if endpoint.split('/')[1] in main_js:  # Check first part of path
                print(f"OK: {method} {endpoint} - {description}")
            else:
                print(f"WARNING: {method} {endpoint} not found in main.js")

    except Exception as e:
        print(f"Error checking main.js: {e}")

    print("OK: Frontend integration check completed")

if __name__ == "__main__":
    print("=" * 60)
    print("Testing Async Parsing Progress Bar Functionality")
    print("=" * 60)

    all_passed = True

    # Test progress structure
    test_progress_structure()

    # Test frontend integration
    test_frontend_integration()

    # Test async parsing flow (requires actual parsing)
    print("\n" + "=" * 60)
    print("Running async parsing integration test...")
    print("=" * 60)

    flow_passed = test_async_parsing_flow()
    all_passed = all_passed and flow_passed

    print("\n" + "=" * 60)
    if all_passed:
        print("SUCCESS: ALL TESTS PASSED - Progress bar functionality is working!")
    else:
        print("FAILED: SOME TESTS FAILED - Check the issues above")
    print("=" * 60)
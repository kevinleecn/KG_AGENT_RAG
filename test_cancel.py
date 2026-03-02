"""
Test script for cancel functionality - verifies the fix works
"""
import sys
import os
import time
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logging.getLogger('pdfminer').setLevel(logging.WARNING)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.parsing_manager import ParsingManager
from config.settings import Config

print("=" * 60)
print("Cancel Functionality Test")
print("=" * 60)

pm = ParsingManager(Config.UPLOAD_FOLDER, Config.PARSED_DATA_FOLDER)

# Find a PDF file
test_files = os.listdir(Config.UPLOAD_FOLDER)
pdf_files = [f for f in test_files if f.endswith('.pdf')]

if not pdf_files:
    print("No PDF files found")
    sys.exit(1)

# Use largest file
test_file = max(pdf_files, key=lambda f: os.path.getsize(os.path.join(Config.UPLOAD_FOLDER, f)))
print(f"Test file: {test_file}")

# Start parsing
task_id = pm.parse_file_async(test_file)
print(f"Task ID: {task_id}")

# Wait for parsing to start
time.sleep(0.5)

# Check status
progress = pm.get_parsing_progress(task_id)
print(f"Status before cancel: {progress.get('status')}")

# Check cancel event
cancel_event = pm._cancel_events.get(task_id)
print(f"Cancel event exists: {cancel_event is not None}")
if cancel_event:
    print(f"Cancel event is_set: {cancel_event.is_set()}")

# Cancel
print("\nCalling cancel_parsing()...")
start = time.time()
result = pm.cancel_parsing(task_id)
elapsed = time.time() - start

print(f"Cancel result: {result}")
print(f"Time elapsed: {elapsed:.3f}s")

# Wait and check final status
time.sleep(0.5)
progress = pm.get_parsing_progress(task_id)
print(f"\nFinal status: {progress.get('status')}")
print(f"Final message: {progress.get('message')}")

# Verify
status = progress.get('status', '').lower()
if status == 'cancelled':
    print("\n[SUCCESS] Cancel works correctly!")
else:
    print(f"\n[FAILED] Status is '{status}', expected 'cancelled'")

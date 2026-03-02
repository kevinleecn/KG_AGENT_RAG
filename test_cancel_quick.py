"""
Quick test for cancel functionality
"""
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.parsing_manager import ParsingManager
from config.settings import Config

# Create manager
pm = ParsingManager(Config.UPLOAD_FOLDER, Config.PARSED_DATA_FOLDER)

# Find a PDF file
test_files = os.listdir(Config.UPLOAD_FOLDER)
pdf_files = [f for f in test_files if f.endswith('.pdf')]

if not pdf_files:
    print("No PDF files found for testing")
    sys.exit(0)

test_file = pdf_files[0]
print(f"Testing with file: {test_file}")

# Start parsing
task_id = pm.parse_file_async(test_file)
print(f"Task ID: {task_id}")

# Wait a bit
time.sleep(0.3)

# Cancel immediately
print("Cancelling...")
start = time.time()
result = pm.cancel_parsing(task_id)
elapsed = time.time() - start

print(f"Cancel result: {result}, Time: {elapsed:.3f}s")

# Check final status
time.sleep(0.3)
progress = pm.get_parsing_progress(task_id)
status = progress.get('status') if progress else 'N/A'
print(f"Final status: {status}")

if status == 'CANCELLED':
    print("[OK] Task correctly marked as CANCELLED")
else:
    print(f"[INFO] Task status is '{status}'")

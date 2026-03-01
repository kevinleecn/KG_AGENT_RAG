#!/usr/bin/env python3
"""
Start Flask application with Neo4j authentication environment variables.
"""

import os
import sys
import subprocess
import signal
import time

def set_environment():
    """Set Neo4j environment variables."""
    os.environ['NEO4J_URI'] = 'bolt://localhost:7687'
    os.environ['NEO4J_USER'] = 'neo4j'
    os.environ['NEO4J_PASSWORD'] = 'neo4j168'
    os.environ['FLASK_ENV'] = 'development'

    print("Environment variables set:")
    print(f"  NEO4J_URI: {os.environ['NEO4J_URI']}")
    print(f"  NEO4J_USER: {os.environ['NEO4J_USER']}")
    print(f"  NEO4J_PASSWORD: {'*' * len(os.environ['NEO4J_PASSWORD'])}")
    print(f"  FLASK_ENV: {os.environ['FLASK_ENV']}")

def find_flask_process():
    """Find and return Flask process ID if running."""
    try:
        import psutil
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info['cmdline']
                if cmdline and 'python' in ' '.join(cmdline).lower() and 'app.py' in ' '.join(cmdline):
                    return proc.info['pid']
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except ImportError:
        # psutil not available, try netstat approach
        try:
            result = subprocess.run(
                ['netstat', '-ano', '-p', 'tcp'],
                capture_output=True,
                text=True,
                shell=True
            )
            lines = result.stdout.split('\n')
            for line in lines:
                if ':5000' in line and 'LISTENING' in line:
                    parts = line.strip().split()
                    if len(parts) >= 5:
                        return int(parts[-1])
        except:
            pass
    return None

def stop_flask_process(pid=None):
    """Stop Flask process if running."""
    if pid is None:
        pid = find_flask_process()

    if pid:
        print(f"Stopping Flask process (PID: {pid})...")
        try:
            os.kill(pid, signal.SIGTERM)
            time.sleep(2)
            print("Flask process stopped.")
            return True
        except Exception as e:
            print(f"Error stopping Flask process: {e}")
            try:
                subprocess.run(['taskkill', '/PID', str(pid), '/F'], check=False)
                print("Flask process killed.")
                return True
            except Exception as e2:
                print(f"Error killing Flask process: {e2}")
                return False
    else:
        print("No Flask process found.")
        return True

def start_flask():
    """Start Flask application."""
    print("\nStarting Flask application...")
    print("=" * 60)

    # Start Flask with current environment
    flask_process = subprocess.Popen(
        [sys.executable, 'app.py'],
        env=os.environ
    )

    print(f"Flask started with PID: {flask_process.pid}")
    print(f"Application URL: http://localhost:5000")
    print(f"Neo4j Browser URL: http://localhost:7474")
    print("=" * 60)
    print("\nPress Ctrl+C to stop Flask application.")

    try:
        flask_process.wait()
    except KeyboardInterrupt:
        print("\nStopping Flask application...")
        flask_process.terminate()
        flask_process.wait()
        print("Flask application stopped.")

if __name__ == "__main__":
    print("Knowledge Graph QA Demo - Flask Startup Script")
    print("=" * 60)

    # Set environment variables
    set_environment()

    # Check if Flask is already running
    flask_pid = find_flask_process()
    if flask_pid:
        print(f"\nFlask is already running (PID: {flask_pid})")
        response = input("Do you want to stop it and restart? (y/n): ").strip().lower()
        if response == 'y':
            if not stop_flask_process(flask_pid):
                print("Failed to stop Flask process. Exiting.")
                sys.exit(1)
        else:
            print("Keeping existing Flask process. Exiting.")
            sys.exit(0)

    # Start Flask
    start_flask()
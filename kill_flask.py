#!/usr/bin/env python3
"""
Kill Flask process running on port 5000.
"""

import os
import sys
import signal
import subprocess
import time

def kill_flask():
    """Find and kill Flask process on port 5000."""
    # Find process using port 5000
    try:
        # Use netstat to find PID
        result = subprocess.run(
            ['netstat', '-ano', '-p', 'tcp'],
            capture_output=True,
            text=True,
            shell=True
        )

        pid = None
        lines = result.stdout.split('\n')
        for line in lines:
            if ':5000' in line and 'LISTENING' in line:
                parts = line.strip().split()
                if len(parts) >= 5:
                    pid = int(parts[-1])
                    print(f"Found Flask process on port 5000, PID: {pid}")
                    break

        if pid:
            # Try graceful termination first
            try:
                os.kill(pid, signal.SIGTERM)
                print(f"Sent SIGTERM to process {pid}")
                time.sleep(2)

                # Check if still running
                try:
                    os.kill(pid, 0)
                    print("Process still running, sending SIGKILL...")
                    os.kill(pid, signal.SIGKILL)
                except OSError:
                    print("Process terminated successfully.")
                    return True

            except Exception as e:
                print(f"Error with signals: {e}")
                print("Using taskkill...")
                subprocess.run(['taskkill', '/PID', str(pid), '/F'], check=False)
                print("Process killed with taskkill.")
                return True
        else:
            print("No Flask process found on port 5000.")
            return True

    except Exception as e:
        print(f"Error finding/killing Flask process: {e}")
        return False

if __name__ == "__main__":
    print("Stopping Flask application...")
    if kill_flask():
        print("Flask stopped successfully.")
        sys.exit(0)
    else:
        print("Failed to stop Flask.")
        sys.exit(1)
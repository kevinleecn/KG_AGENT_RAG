#!/usr/bin/env python3
"""
Quick Ollama test without Unicode.
"""

import requests
import json
import sys
import time

def test_ollama_quick():
    """Quick test of Ollama with llama3:8b."""
    print("Testing Ollama quick...")

    # Check available models
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        models = resp.json().get("models", [])
        print(f"Models: {[m['name'] for m in models]}")

        if not any(m['name'] == 'llama3:8b' for m in models):
            print("llama3:8b not available")
            return False
    except Exception as e:
        print(f"Cannot connect to Ollama: {e}")
        return False

    # Simple prompt
    payload = {
        "model": "llama3:8b",
        "prompt": "Say hello",
        "stream": False,
        "options": {
            "temperature": 0.1,
            "max_tokens": 10
        }
    }

    print("Sending request (30s timeout)...")
    start = time.time()

    try:
        resp = requests.post("http://localhost:11434/api/generate",
                           json=payload, timeout=30)

        elapsed = time.time() - start
        print(f"Response after {elapsed:.1f}s")

        if resp.status_code == 200:
            result = resp.json()
            print(f"Success! Response: {result.get('response', '')}")
            print(f"Duration: {result.get('total_duration', 0)/1e9:.2f}s")
            return True
        else:
            print(f"Failed: {resp.status_code}")
            return False
    except requests.exceptions.Timeout:
        print("Timeout after 30s")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    success = test_ollama_quick()
    sys.exit(0 if success else 1)
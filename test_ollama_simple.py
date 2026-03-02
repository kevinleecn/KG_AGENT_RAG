#!/usr/bin/env python3
"""
Simple Ollama connection test with shorter timeout.
"""

import requests
import json
import sys

def test_ollama_simple():
    """Test Ollama with simple echo request."""
    print("Testing Ollama simple echo...")

    # First check if Ollama is running
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        if resp.status_code == 200:
            models = resp.json().get("models", [])
            print(f"Ollama running. Models: {[m['name'] for m in models]}")
        else:
            print(f"Ollama API error: {resp.status_code}")
            return False
    except Exception as e:
        print(f"Cannot connect to Ollama: {e}")
        return False

    # Try llama3:8b which should be faster
    print("\nTesting llama3:8b model (should be faster)...")
    payload = {
        "model": "llama3:8b",
        "prompt": "Say 'hello'",
        "stream": False,
        "options": {
            "temperature": 0.1,
            "max_tokens": 10  # Very short response
        }
    }

    try:
        resp = requests.post("http://localhost:11434/api/generate",
                           json=payload, timeout=30)

        if resp.status_code == 200:
            result = resp.json()
            print(f"llama3:8b response: {result.get('response', '')}")
            print(f"Success! Model responded in {result.get('total_duration', 0)/1e9:.2f}s")
            return True
        else:
            print(f"llama3:8b failed: {resp.status_code}")
            print(f"Response: {resp.text}")
            return False
    except Exception as e:
        print(f"llama3:8b error: {e}")
        return False

def test_qwen3_short():
    """Test qwen3:latest with very short request."""
    print("\nTesting qwen3:latest with very short request...")

    payload = {
        "model": "qwen3:latest",
        "prompt": "你好",
        "stream": False,
        "options": {
            "temperature": 0.1,
            "max_tokens": 5  # Extremely short
        }
    }

    try:
        resp = requests.post("http://localhost:11434/api/generate",
                           json=payload, timeout=60)  # Give it more time

        if resp.status_code == 200:
            result = resp.json()
            print(f"qwen3:latest response: {result.get('response', '')}")
            print(f"Success! Model responded in {result.get('total_duration', 0)/1e9:.2f}s")
            return True
        else:
            print(f"qwen3:latest failed: {resp.status_code}")
            return False
    except Exception as e:
        print(f"qwen3:latest error: {e}")
        return False

def main():
    print("=" * 80)
    print("Simple Ollama Connection Test")
    print("=" * 80)

    # Test 1: Basic connection
    if not test_ollama_simple():
        print("\n[ERROR] Basic Ollama test failed.")
        return False

    # Test 2: qwen3 with short request
    qwen_success = test_qwen3_short()

    print("\n" + "=" * 80)
    print("Test Summary")
    print("=" * 80)

    if qwen_success:
        print("[OK] Ollama and qwen3:latest are working!")
        print("\nNote: For knowledge extraction, you might want to:")
        print("1. Use llama3:8b for faster responses (change LLM_MODEL in settings.py)")
        print("2. Ensure qwen3:latest is fully loaded (may take time on first use)")
        print("3. Consider increasing timeouts in llm_extractor.py")
    else:
        print("[WARNING] qwen3:latest may be slow or not fully loaded.")
        print("Recommendation: Use llama3:8b instead for now.")
        print("Update config/settings.py: LLM_MODEL = 'llama3:8b'")

    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
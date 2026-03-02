#!/usr/bin/env python3
"""
Direct Ollama API test with very simple request.
"""

import requests
import json
import sys
import time

def test_ollama_direct():
    """Test direct Ollama API with minimal request."""
    print("Testing direct Ollama API...")

    # Check available models
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        models = resp.json().get("models", [])
        print(f"Available models: {[m['name'] for m in models]}")

        # Try llama3:8b first (smaller)
        test_model = "llama3:8b"
        if any(m['name'] == test_model for m in models):
            print(f"Testing with {test_model}...")
        else:
            print(f"Model {test_model} not available, trying first available model")
            if models:
                test_model = models[0]['name']
            else:
                print("No models available")
                return False
    except Exception as e:
        print(f"Error checking models: {e}")
        return False

    # Minimal prompt
    payload = {
        "model": test_model,
        "prompt": "Hello",
        "stream": False,
        "options": {
            "temperature": 0.1,
            "max_tokens": 5  # Extremely short
        }
    }

    print(f"Sending request to {test_model} with 120 second timeout...")
    start_time = time.time()

    try:
        resp = requests.post("http://localhost:11434/api/generate",
                           json=payload, timeout=120)

        elapsed = time.time() - start_time
        print(f"Response received after {elapsed:.1f} seconds")

        if resp.status_code == 200:
            result = resp.json()
            print(f"Success! Response: {result.get('response', '')}")
            print(f"Total duration: {result.get('total_duration', 0)/1e9:.2f}s")
            return True
        else:
            print(f"Failed with status {resp.status_code}: {resp.text}")
            return False
    except requests.exceptions.Timeout:
        print(f"Request timed out after 120 seconds")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_model_loaded():
    """Check if model is already loaded by Ollama."""
    print("\nChecking if model is loaded...")
    try:
        resp = requests.get("http://localhost:11434/api/ps", timeout=5)
        if resp.status_code == 200:
            processes = resp.json().get("models", [])
            if processes:
                print(f"Loaded models: {[p['name'] for p in processes]}")
                return True
            else:
                print("No models currently loaded (first request will be slow)")
                return False
        else:
            print(f"API /api/ps returned {resp.status_code}")
            return False
    except Exception as e:
        print(f"Error checking loaded models: {e}")
        return False

def main():
    print("=" * 80)
    print("Direct Ollama API Test")
    print("=" * 80)

    # Check if model is loaded
    model_loaded = test_model_loaded()

    if not model_loaded:
        print("\nNote: Model not pre-loaded. First request will load model into memory.")
        print("This can take several minutes for large models (5GB+).")
        print("Please be patient...")

    # Test direct API
    success = test_ollama_direct()

    print("\n" + "=" * 80)
    print("Test Result")
    print("=" * 80)

    if success:
        print("[SUCCESS] Ollama is working!")
        print("\nRecommendations for knowledge extraction:")
        print("1. First extraction will be slow while model loads")
        print("2. Subsequent extractions will be faster")
        print("3. Consider keeping Ollama running to avoid reloading")
        print("4. For production, pre-load model with: ollama run qwen3:latest")
    else:
        print("[FAILED] Ollama not responding properly.")
        print("\nTroubleshooting:")
        print("1. Check Ollama is running: ollama serve")
        print("2. Check model is available: ollama list")
        print("3. Try pulling a smaller model: ollama pull llama3:8b")
        print("4. Check system has enough RAM (5GB+ for qwen3:latest)")

    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
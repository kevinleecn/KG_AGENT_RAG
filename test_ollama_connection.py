#!/usr/bin/env python3
"""
Test Ollama connection and qwen3:latest model availability.
"""

import requests
import json
import sys
import os
from config.settings import Config

def test_ollama_connection():
    """Test basic Ollama connection."""
    print("Testing Ollama connection...")
    print(f"Ollama base URL: http://localhost:11434")

    try:
        # Check Ollama service is running
        response = requests.get("http://localhost:11434/api/tags", timeout=10)
        if response.status_code == 200:
            models = response.json().get("models", [])
            print(f"[OK] Ollama service is running")
            print(f"   Available models: {[model['name'] for model in models]}")

            # Check if qwen3:latest is available
            qwen_available = any(model['name'] == 'qwen3:latest' for model in models)
            if qwen_available:
                print(f"[OK] qwen3:latest model is available")
            else:
                print(f"[ERROR] qwen3:latest model not found in available models")
                print(f"   Please pull the model with: ollama pull qwen3:latest")
                return False
        else:
            print(f"[ERROR] Ollama API returned status code {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("[ERROR] Cannot connect to Ollama service at http://localhost:11434")
        print("   Make sure Ollama is running: ollama serve")
        return False
    except Exception as e:
        print(f"[ERROR] Error connecting to Ollama: {e}")
        return False

    return True

def test_qwen3_generation():
    """Test qwen3:latest model generation with a simple prompt."""
    print("\nTesting qwen3:latest model generation...")

    test_prompt = "Hello, how are you?"
    payload = {
        "model": "qwen3:latest",
        "prompt": test_prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "max_tokens": 50
        }
    }

    try:
        response = requests.post("http://localhost:11434/api/generate",
                               json=payload, timeout=30)

        if response.status_code == 200:
            result = response.json()
            print(f"[OK] Model response successful")
            print(f"   Prompt: {test_prompt}")
            print(f"   Response: {result.get('response', '')[:100]}...")
            print(f"   Total duration: {result.get('total_duration', 0)/1e9:.2f}s")
            return True
        else:
            print(f"[ERROR] Model generation failed with status {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"[ERROR] Error testing model generation: {e}")
        return False

def test_chinese_extraction():
    """Test Chinese text extraction with qwen3:latest."""
    print("\nTesting Chinese text extraction with qwen3:latest...")

    chinese_text = "vsp文件夹里面是继电保护器模块，需要完善。需要增加电网区域控保。"
    payload = {
        "model": "qwen3:latest",
        "prompt": f"提取以下文本中的实体：{chinese_text}",
        "stream": False,
        "options": {
            "temperature": 0.1,
            "max_tokens": 200
        }
    }

    try:
        response = requests.post("http://localhost:11434/api/generate",
                               json=payload, timeout=60)

        if response.status_code == 200:
            result = response.json()
            print(f"[OK] Chinese extraction successful")
            print(f"   Chinese text: {chinese_text}")
            print(f"   Response: {result.get('response', '')[:200]}...")
            return True
        else:
            print(f"[ERROR] Chinese extraction failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"[ERROR] Error testing Chinese extraction: {e}")
        return False

def test_openai_client():
    """Test OpenAI client compatibility with Ollama."""
    print("\nTesting OpenAI client compatibility with Ollama...")

    try:
        from openai import OpenAI

        client = OpenAI(
            base_url="http://localhost:11434/v1",
            api_key="ollama"  # Ollama doesn't require a key
        )

        # Test a simple chat completion
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "user", "content": "Say 'Hello' in Chinese"}
            ],
            model="qwen3:latest",
            temperature=0.1,
            max_tokens=50
        )

        response = chat_completion.choices[0].message.content
        print(f"[OK] OpenAI client compatible with Ollama")
        print(f"   Response: {response}")
        return True
    except Exception as e:
        print(f"[ERROR] OpenAI client test failed: {e}")
        return False

def main():
    print("=" * 80)
    print("Ollama Connection Test")
    print(f"Configuration: BACKEND={Config.LLM_BACKEND}, MODEL={Config.LLM_MODEL}")
    print("=" * 80)

    all_tests_passed = True

    # Test 1: Basic Ollama connection
    if not test_ollama_connection():
        all_tests_passed = False
        print("\n❌ Ollama connection failed. Cannot proceed with other tests.")
        return False

    # Test 2: Simple generation
    if not test_qwen3_generation():
        all_tests_passed = False

    # Test 3: Chinese extraction
    if not test_chinese_extraction():
        all_tests_passed = False

    # Test 4: OpenAI client compatibility
    if not test_openai_client():
        all_tests_passed = False

    # Summary
    print("\n" + "=" * 80)
    print("Test Summary")
    print("=" * 80)
    if all_tests_passed:
        print("[OK] All tests passed! Ollama and qwen3:latest are ready for knowledge extraction.")
        print("\nNext steps:")
        print("1. Run test_llm_extraction.py for full LLM extraction test")
        print("2. Restart Flask app to use new configuration")
        print("3. Trigger knowledge extraction for documents:")
        print("   - http://localhost:5000/graph/extract/readme.txt")
        print("   - http://localhost:5000/graph/extract/2.docx")
    else:
        print("[ERROR] Some tests failed. Please check Ollama service and qwen3:latest model.")

    return all_tests_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
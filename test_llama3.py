#!/usr/bin/env python3
"""
Test llama3:8b model for Chinese knowledge extraction.
"""

import requests
import json
import sys
import time
from config.settings import Config

def check_ollama():
    """Check if Ollama is running and llama3:8b is available."""
    print("Checking Ollama service...")
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=10)
        if resp.status_code == 200:
            models = resp.json().get("models", [])
            model_names = [m['name'] for m in models]
            print(f"Available models: {model_names}")

            if 'llama3:8b' in model_names:
                print("[OK] llama3:8b model is available")
                return True
            else:
                print("[ERROR] llama3:8b not found in available models")
                print(f"   Available: {model_names}")
                return False
        else:
            print(f"[ERROR] Ollama API error: {resp.status_code}")
            return False
    except Exception as e:
        print(f"[ERROR] Cannot connect to Ollama: {e}")
        return False

def test_llama3_simple():
    """Test simple Chinese text with llama3:8b."""
    print("\nTesting simple Chinese extraction with llama3:8b...")

    # Very short Chinese text
    chinese_text = "vsp文件夹是继电保护器模块"

    prompt = f"""Extract entities from this Chinese text:
Text: {chinese_text}

Return JSON format:
[{{"text": "entity name", "type": "entity type", "confidence": 0.9}}]

Only return JSON, no other text."""

    payload = {
        "model": "llama3:8b",
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "max_tokens": 100
        }
    }

    print(f"Sending request with {len(chinese_text)} chars...")
    start_time = time.time()

    try:
        resp = requests.post("http://localhost:11434/api/generate",
                           json=payload, timeout=120)

        elapsed = time.time() - start_time
        print(f"Response time: {elapsed:.1f} seconds")

        if resp.status_code == 200:
            result = resp.json()
            response_text = result.get('response', '')
            print(f"Response preview: {response_text[:200]}...")

            # Try to parse JSON
            try:
                json_start = response_text.find('[')
                json_end = response_text.rfind(']') + 1
                if json_start != -1 and json_end != 0:
                    json_str = response_text[json_start:json_end]
                    entities = json.loads(json_str)
                    print(f"✅ Successfully parsed {len(entities)} entities:")
                    for i, entity in enumerate(entities):
                        print(f"  {i+1}. '{entity.get('text', '')}' ({entity.get('type', '')})")
                    return True
                else:
                    print("❌ No JSON array found in response")
                    print(f"Raw response: {response_text[:300]}")
                    return False
            except json.JSONDecodeError as e:
                print(f"❌ JSON parsing error: {e}")
                print(f"Response: {response_text[:300]}")
                return False
        else:
            print(f"❌ Request failed: {resp.status_code}")
            print(f"Response: {resp.text}")
            return False

    except requests.exceptions.Timeout:
        print("❌ Request timed out after 120 seconds")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_llm_extractor():
    """Test the LLMExtractor class with llama3:8b."""
    print("\nTesting LLMExtractor class...")

    try:
        from src.nlp.llm_extractor import LLMExtractor

        extractor = LLMExtractor(
            api_key=Config.OPENAI_API_KEY,
            model=Config.LLM_MODEL,
            backend=Config.LLM_BACKEND
        )

        print(f"Initialized LLMExtractor: backend={extractor.backend}, model={extractor.model}")

        # Check if available
        is_available = extractor.is_available()
        print(f"LLM extractor available: {is_available}")

        if not is_available:
            print("❌ LLM extractor not available")
            return False

        # Test with very short text
        test_text = "vsp文件夹里面是继电保护器模块。"
        print(f"\nTesting extraction with text: {test_text}")

        # Start extraction in background thread
        import threading
        import queue

        result_queue = queue.Queue()
        error_queue = queue.Queue()

        def extract_thread():
            try:
                entities = extractor.extract_entities(test_text)
                result_queue.put(entities)
            except Exception as e:
                error_queue.put(e)

        thread = threading.Thread(target=extract_thread)
        thread.daemon = True
        thread.start()

        # Wait 60 seconds
        thread.join(timeout=60)

        if thread.is_alive():
            print("❌ LLM extraction timed out after 60 seconds")
            return False
        elif not error_queue.empty():
            error = error_queue.get()
            print(f"❌ Extraction error: {error}")
            return False
        else:
            entities = result_queue.get()
            print(f"✅ Extracted {len(entities)} entities:")
            for i, entity in enumerate(entities[:5]):
                print(f"  {i+1}. '{entity.get('text', '')}' ({entity.get('type', '')})")
            return True

    except Exception as e:
        print(f"❌ Error testing LLMExtractor: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=" * 80)
    print("llama3:8b Chinese Extraction Test")
    print(f"Configuration: BACKEND={Config.LLM_BACKEND}, MODEL={Config.LLM_MODEL}")
    print("=" * 80)

    # Test 1: Check Ollama
    if not check_ollama():
        print("\n❌ Ollama check failed. Cannot proceed.")
        return False

    # Test 2: Simple API test
    print("\n" + "=" * 80)
    print("Test 1: Direct API Test")
    print("=" * 80)
    api_success = test_llama3_simple()

    # Test 3: LLMExtractor test (optional)
    print("\n" + "=" * 80)
    print("Test 2: LLMExtractor Class Test")
    print("=" * 80)
    extractor_success = False
    if api_success:
        extractor_success = test_llm_extractor()
    else:
        print("Skipping LLMExtractor test due to API test failure")

    # Summary
    print("\n" + "=" * 80)
    print("Test Summary")
    print("=" * 80)
    print(f"Direct API test: {'✅ PASS' if api_success else '❌ FAIL'}")
    print(f"LLMExtractor test: {'✅ PASS' if extractor_success else '❌ FAIL/ SKIP'}")

    if api_success:
        print("\n✅ llama3:8b is working for Chinese extraction!")
        print("\nNext steps:")
        print("1. Restart Flask app to use new configuration")
        print("2. Test knowledge extraction for documents:")
        print("   - http://localhost:5000/graph/extract/readme.txt")
        print("   - http://localhost:5000/graph/extract/2.docx")
        print("3. Note: First extraction may be slow as model loads")
    else:
        print("\n❌ Tests failed. Check Ollama service and model.")

    return api_success  # Consider test passed if API test works

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
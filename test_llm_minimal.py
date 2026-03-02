#!/usr/bin/env python3
"""
Minimal test for LLM extraction with shorter timeouts and simpler prompts.
"""

import sys
import os
import json
import requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import Config

def test_ollama_health():
    """Check if Ollama is healthy and model is loaded."""
    print("Checking Ollama health...")
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        if resp.status_code == 200:
            models = resp.json().get("models", [])
            model_names = [m['name'] for m in models]
            print(f"Available models: {model_names}")

            target_model = Config.LLM_MODEL
            if target_model in model_names:
                print(f"Target model {target_model} is available")
                return True
            else:
                print(f"Target model {target_model} not found. Available: {model_names}")
                return False
        else:
            print(f"Ollama API error: {resp.status_code}")
            return False
    except Exception as e:
        print(f"Ollama health check failed: {e}")
        return False

def test_llm_simple_extraction():
    """Test simple extraction with very short prompt."""
    print(f"\nTesting simple extraction with {Config.LLM_MODEL}...")

    # Very simple Chinese text
    test_text = "vsp文件夹里面是继电保护器模块。"

    # Simple prompt
    prompt = f"""请从以下文本中提取实体：
文本：{test_text}

请返回JSON格式：
[{{"text": "实体文本", "type": "实体类型", "confidence": 0.9}}]
"""

    payload = {
        "model": Config.LLM_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "max_tokens": 100  # Very short response
        }
    }

    try:
        resp = requests.post("http://localhost:11434/api/generate",
                           json=payload, timeout=120)  # 2 minute timeout

        if resp.status_code == 200:
            result = resp.json()
            response_text = result.get('response', '')
            print(f"Model responded in {result.get('total_duration', 0)/1e9:.2f}s")
            print(f"Response preview: {response_text[:200]}...")

            # Try to parse JSON
            try:
                # Find JSON in response
                json_start = response_text.find('[')
                json_end = response_text.rfind(']') + 1
                if json_start != -1 and json_end != 0:
                    json_str = response_text[json_start:json_end]
                    entities = json.loads(json_str)
                    print(f"Successfully parsed {len(entities)} entities:")
                    for i, entity in enumerate(entities[:5]):
                        print(f"  {i+1}. '{entity.get('text', '')}' ({entity.get('type', '')})")
                    return True
                else:
                    print("No JSON found in response")
                    return False
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON: {e}")
                print(f"Raw response: {response_text[:300]}")
                return False
        else:
            print(f"Model generation failed: {resp.status_code}")
            print(f"Response: {resp.text}")
            return False
    except Exception as e:
        print(f"Error testing LLM extraction: {e}")
        return False

def test_knowledge_extractor_with_fallback():
    """Test knowledge extractor with LLM, but handle timeout gracefully."""
    print("\nTesting KnowledgeExtractor with LLM (with fallback)...")

    try:
        # Import inside function to avoid loading issues
        from src.nlp.knowledge_extractor import KnowledgeExtractor

        # Initialize with LLM enabled
        extractor = KnowledgeExtractor(spacy_model=Config.SPACY_MODEL, use_llm=True)

        # Check if LLM is actually available
        if extractor.llm_extractor is None:
            print("LLM extractor not initialized (check logs)")
            return False

        # Load short text
        parsed_file = "data/parsed/readme_parsed.txt"
        if not os.path.exists(parsed_file):
            print(f"Parsed file not found: {parsed_file}")
            return False

        with open(parsed_file, 'r', encoding='utf-8') as f:
            text = f.read()

        print(f"Text length: {len(text)} chars")

        # Try extraction with timeout
        import threading
        import queue

        result_queue = queue.Queue()
        error_queue = queue.Queue()

        def extract_thread():
            try:
                result = extractor.extract_from_text(text, document_id='readme.txt')
                result_queue.put(result)
            except Exception as e:
                error_queue.put(e)

        thread = threading.Thread(target=extract_thread)
        thread.daemon = True
        thread.start()

        # Wait with timeout
        thread.join(timeout=60)  # 1 minute timeout

        if thread.is_alive():
            print("LLM extraction timed out after 60 seconds")
            print("Suggestion: Use smaller model or increase timeout")
            return False
        elif not error_queue.empty():
            error = error_queue.get()
            print(f"Extraction error: {error}")
            return False
        else:
            result = result_queue.get()
            stats = result['statistics']
            print(f"Extraction completed in {stats['processing_time_seconds']:.2f}s")
            print(f"Entities: {stats['total_entities']}, Relationships: {stats['total_relationships']}")
            return True

    except Exception as e:
        print(f"Error testing knowledge extractor: {e}")
        return False

def main():
    print("=" * 80)
    print("Minimal LLM Extraction Test")
    print(f"Configuration: BACKEND={Config.LLM_BACKEND}, MODEL={Config.LLM_MODEL}")
    print("=" * 80)

    # Test 1: Ollama health
    if not test_ollama_health():
        print("\n[ERROR] Ollama health check failed. Cannot proceed.")
        return False

    # Test 2: Simple extraction
    print("\n" + "=" * 80)
    print("Test 1: Simple LLM Extraction")
    print("=" * 80)
    simple_success = test_llm_simple_extraction()

    # Test 3: Knowledge extractor (optional, may timeout)
    print("\n" + "=" * 80)
    print("Test 2: Knowledge Extractor with LLM")
    print("=" * 80)
    knowledge_success = False
    if simple_success:
        knowledge_success = test_knowledge_extractor_with_fallback()
    else:
        print("Skipping knowledge extractor test due to simple extraction failure")

    # Summary
    print("\n" + "=" * 80)
    print("Test Summary")
    print("=" * 80)
    print(f"Simple LLM extraction: {'PASS' if simple_success else 'FAIL'}")
    print(f"Knowledge extractor: {'PASS' if knowledge_success else 'FAIL/ TIMEOUT'}")

    if simple_success:
        print("\n[INFO] LLM is working but may be slow for large prompts.")
        print("Recommendations:")
        print("1. Use shorter texts for LLM extraction")
        print("2. Increase timeout in llm_extractor.py (_call_llm method)")
        print("3. Consider using smaller model (e.g., llama3:8b instead of qwen3:latest)")
        print("4. Implement async extraction with progress tracking")
    else:
        print("\n[ERROR] LLM extraction not working properly.")
        print("Check Ollama service and model availability.")

    return simple_success  # Consider test passed if at least simple extraction works

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
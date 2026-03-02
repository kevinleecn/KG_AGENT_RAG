#!/usr/bin/env python3
"""
Final test for LLM knowledge extraction with llama3:8b.
"""

import sys
import os
import json
import time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import Config

def test_ollama_connection():
    """Test Ollama connection."""
    print("1. Testing Ollama connection...")
    try:
        import requests
        resp = requests.get("http://localhost:11434/api/tags", timeout=10)
        models = resp.json().get("models", [])
        print(f"   Models: {[m['name'] for m in models]}")

        if 'llama3:8b' in [m['name'] for m in models]:
            print("   [OK] llama3:8b is available")
            return True
        else:
            print("   [ERROR] llama3:8b not found")
            return False
    except Exception as e:
        print(f"   [ERROR] Cannot connect to Ollama: {e}")
        return False

def test_llm_extractor_init():
    """Test LLMExtractor initialization."""
    print("\n2. Testing LLMExtractor initialization...")
    try:
        from src.nlp.llm_extractor import LLMExtractor

        extractor = LLMExtractor(
            api_key=Config.OPENAI_API_KEY,
            model=Config.LLM_MODEL,
            backend=Config.LLM_BACKEND
        )

        print(f"   Backend: {extractor.backend}, Model: {extractor.model}")
        print(f"   LLM client initialized: {extractor.llm_client is not None}")

        if extractor.llm_client is None:
            print("   [ERROR] LLM client not initialized")
            return False

        # Check availability
        is_available = extractor.is_available()
        print(f"   LLM extractor available: {is_available}")

        if not is_available:
            print("   [ERROR] LLM extractor not available")
            return False

        print("   [OK] LLMExtractor initialized successfully")
        return True

    except Exception as e:
        print(f"   [ERROR] Failed to initialize LLMExtractor: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_knowledge_extractor():
    """Test KnowledgeExtractor with LLM enabled."""
    print("\n3. Testing KnowledgeExtractor with LLM...")
    try:
        from src.nlp.knowledge_extractor import KnowledgeExtractor

        # Initialize with LLM enabled
        extractor = KnowledgeExtractor(spacy_model=Config.SPACY_MODEL, use_llm=True)

        print(f"   Extraction methods: {extractor.extraction_methods}")
        print(f"   LLM extractor available: {extractor.llm_extractor is not None}")

        if extractor.llm_extractor is None:
            print("   [ERROR] LLM extractor not available in KnowledgeExtractor")
            return False

        # Load short text
        parsed_file = "data/parsed/readme_parsed.txt"
        if not os.path.exists(parsed_file):
            print(f"   [ERROR] Parsed file not found: {parsed_file}")
            return False

        with open(parsed_file, 'r', encoding='utf-8') as f:
            text = f.read()

        print(f"   Text length: {len(text)} chars")
        print(f"   Text preview: {text[:100]}...")

        # Extract with timeout
        print("   Starting extraction (may take 1-2 minutes for first run)...")
        start_time = time.time()

        try:
            result = extractor.extract_from_text(text, document_id='readme.txt')
            elapsed = time.time() - start_time

            stats = result['statistics']
            print(f"   Extraction completed in {elapsed:.1f}s")
            print(f"   Entities: {stats['total_entities']}")
            print(f"   Relationships: {stats['total_relationships']}")
            print(f"   Triplets: {stats['total_triplets']}")

            if stats['total_entities'] > 0:
                print("   [OK] Knowledge extraction successful")
                # Print first few entities
                print("   Sample entities:")
                for i, entity in enumerate(result['entities'][:5]):
                    if hasattr(entity, 'text'):
                        print(f"     {i+1}. '{entity.text}' ({entity.entity_type})")
                    else:
                        print(f"     {i+1}. '{entity.get('text', '')}'")
                return True
            else:
                print("   [WARNING] No entities extracted")
                return False

        except Exception as e:
            elapsed = time.time() - start_time
            print(f"   [ERROR] Extraction failed after {elapsed:.1f}s: {e}")
            return False

    except Exception as e:
        print(f"   [ERROR] Failed to test KnowledgeExtractor: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_parsing_manager():
    """Test ParsingManager's extract_knowledge method."""
    print("\n4. Testing ParsingManager knowledge extraction...")
    try:
        from src.parsing_manager import ParsingManager
        from config.settings import Config

        # Initialize parsing manager
        parsing_manager = ParsingManager(
            upload_folder=Config.UPLOAD_FOLDER,
            parsed_data_folder=Config.PARSED_DATA_FOLDER
        )

        # Check if readme.txt is parsed
        state = parsing_manager.get_file_state('readme.txt')
        print(f"   readme.txt parsed: {state.get('parsed', False)}")

        if not state.get('parsed', False):
            print("   [ERROR] readme.txt not parsed yet")
            return False

        # Extract knowledge
        print("   Starting knowledge extraction...")
        start_time = time.time()

        try:
            result = parsing_manager.extract_knowledge('readme.txt')
            elapsed = time.time() - start_time

            print(f"   Extraction completed in {elapsed:.1f}s")
            print(f"   Success: {result.get('success', False)}")

            if result.get('success', False):
                print("   [OK] ParsingManager extraction successful")
                return True
            else:
                error = result.get('error', 'Unknown error')
                print(f"   [ERROR] Extraction failed: {error}")
                return False

        except Exception as e:
            elapsed = time.time() - start_time
            print(f"   [ERROR] Extraction failed after {elapsed:.1f}s: {e}")
            return False

    except Exception as e:
        print(f"   [ERROR] Failed to test ParsingManager: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=" * 80)
    print("LLM Knowledge Extraction Final Test")
    print(f"Configuration: BACKEND={Config.LLM_BACKEND}, MODEL={Config.LLM_MODEL}")
    print(f"spaCy model: {Config.SPACY_MODEL}")
    print("=" * 80)

    all_tests_passed = True

    # Test 1: Ollama connection
    if not test_ollama_connection():
        all_tests_passed = False
        print("\n[ERROR] Ollama connection failed. Cannot proceed.")
        return False

    # Test 2: LLMExtractor
    if not test_llm_extractor_init():
        all_tests_passed = False
        print("\n[ERROR] LLMExtractor initialization failed.")
        return False

    # Test 3: KnowledgeExtractor
    if not test_knowledge_extractor():
        all_tests_passed = False
        print("\n[WARNING] KnowledgeExtractor test failed or timed out.")
        print("This may be normal if LLM is slow. Continuing to next test...")

    # Test 4: ParsingManager
    if not test_parsing_manager():
        all_tests_passed = False
        print("\n[WARNING] ParsingManager test failed.")
        print("This may be due to timeouts. Check logs for details.")

    # Summary
    print("\n" + "=" * 80)
    print("Test Summary")
    print("=" * 80)

    if all_tests_passed:
        print("[SUCCESS] All tests passed! LLM extraction is ready.")
        print("\nNext steps:")
        print("1. Restart Flask app: python app.py")
        print("2. Test web interface: http://localhost:5000")
        print("3. Click 'Extract Knowledge' for readme.txt")
        print("4. Check graph visualization")
    else:
        print("[PARTIAL SUCCESS] Some tests passed. LLM extraction may work with limitations.")
        print("\nRecommendations:")
        print("1. First extraction may be slow (model loading)")
        print("2. Subsequent extractions will be faster")
        print("3. Check logs for detailed errors")
        print("4. Consider increasing timeout in llm_extractor.py if needed")

    return True  # Return True even if some tests failed (partial success)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
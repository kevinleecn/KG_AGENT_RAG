#!/usr/bin/env python3
"""
Test LLM-enhanced knowledge extraction with Ollama.
"""

import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.nlp.llm_extractor import LLMExtractor
from src.nlp.knowledge_extractor import KnowledgeExtractor
from config.settings import Config

def test_llm_extractor():
    """Test direct LLM extractor."""
    print("=" * 80)
    print("Testing LLMExtractor with Ollama backend")
    print(f"Backend: {Config.LLM_BACKEND}, Model: {Config.LLM_MODEL}")
    print("=" * 80)

    # Initialize LLM extractor
    try:
        extractor = LLMExtractor(
            api_key=Config.OPENAI_API_KEY,
            model=Config.LLM_MODEL,
            backend=Config.LLM_BACKEND
        )

        # Check if available
        is_available = extractor.is_available()
        print(f"LLM extractor available: {is_available}")

        if not is_available:
            print("LLM extractor not available. Check Ollama service.")
            return False

        # Test text
        test_text = "vsp文件夹里面是继电保护器模块，需要完善。需要增加电网区域控保。"
        print(f"\nTest text: {test_text}")

        # Test entity extraction
        print("\n1. Testing entity extraction...")
        entities = extractor.extract_entities(test_text)
        print(f"   Extracted {len(entities)} entities:")
        for i, entity in enumerate(entities[:10]):
            print(f"     {i+1}. '{entity['text']}' ({entity['type']}, confidence: {entity['confidence']:.2f})")

        # Test relationship extraction
        print("\n2. Testing relationship extraction...")
        relationships = extractor.extract_relationships(test_text, entities)
        print(f"   Extracted {len(relationships)} relationships:")
        for i, rel in enumerate(relationships[:10]):
            print(f"     {i+1}. '{rel['subject']['text']}' -> {rel['predicate']} -> '{rel['object']['text']}'")

        # Test triplet extraction
        print("\n3. Testing triplet extraction...")
        triplets = extractor.extract_triplets(test_text)
        print(f"   Extracted {len(triplets)} triplets:")
        for i, triplet in enumerate(triplets[:10]):
            print(f"     {i+1}. {triplet['subject']['name']} -- {triplet['predicate']} --> {triplet['object']['name']}")

        # Test full document processing
        print("\n4. Testing full document processing...")
        result = extractor.process_document(test_text, "test_doc")
        stats = result['statistics']
        print(f"   Processing time: {stats['processing_time_seconds']:.2f}s")
        print(f"   Entities: {stats['total_entities']}, Relationships: {stats['total_relationships']}, Triplets: {stats['total_triplets']}")

        return True

    except Exception as e:
        print(f"Error testing LLM extractor: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_knowledge_extractor_with_llm():
    """Test KnowledgeExtractor with LLM enabled."""
    print("\n" + "=" * 80)
    print("Testing KnowledgeExtractor with LLM enabled")
    print("=" * 80)

    # Initialize with LLM enabled
    extractor = KnowledgeExtractor(spacy_model=Config.SPACY_MODEL, use_llm=True)

    # Load readme.txt content
    parsed_file = "data/parsed/readme_parsed.txt"
    if not os.path.exists(parsed_file):
        print(f"Parsed file not found: {parsed_file}")
        return False

    with open(parsed_file, 'r', encoding='utf-8') as f:
        text = f.read()

    print(f"Text length: {len(text)} chars")
    print(f"First 200 chars: {text[:200]}")

    # Extract knowledge
    print("\nExtracting knowledge with LLM...")
    try:
        result = extractor.extract_from_text(text, document_id='readme.txt')

        # Print results
        print(f"\nExtraction completed.")
        stats = result['statistics']
        print(f"Processing time: {stats['processing_time_seconds']:.2f}s")
        print(f"Entities: {stats['total_entities']}")
        print(f"Relationships: {stats['total_relationships']}")
        print(f"Triplets: {stats['total_triplets']}")

        # Print entity details
        if result['entities']:
            print(f"\nEntities ({len(result['entities'])}):")
            for i, entity in enumerate(result['entities'][:20]):
                if hasattr(entity, 'text'):
                    # ExtractedEntity object
                    print(f"  {i+1}. '{entity.text}' ({entity.entity_type}, confidence: {entity.confidence:.2f})")
                else:
                    # Dictionary format
                    print(f"  {i+1}. '{entity.get('text', '')}' ({entity.get('type', '')})")

        # Print relationship details
        if result['relationships']:
            print(f"\nRelationships ({len(result['relationships'])}):")
            for i, rel in enumerate(result['relationships'][:10]):
                if hasattr(rel, 'subject'):
                    # ExtractedRelationship object
                    print(f"  {i+1}. '{rel.subject.text}' -> {rel.predicate} -> '{rel.object.text}'")
                else:
                    # Dictionary format
                    print(f"  {i+1}. '{rel.get('subject', {}).get('text', '')}' -> {rel.get('predicate', '')} -> '{rel.get('object', {}).get('text', '')}'")

        # Check method results
        if 'method_results' in result:
            print(f"\nExtraction methods used: {list(result['method_results'].keys())}")

        return True

    except Exception as e:
        print(f"Error extracting knowledge with LLM: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("LLM Extraction Test")
    print(f"Configuration: BACKEND={Config.LLM_BACKEND}, MODEL={Config.LLM_MODEL}, SPACY_MODEL={Config.SPACY_MODEL}")

    # Test 1: Direct LLM extractor
    print("\n" + "=" * 80)
    print("Test 1: Direct LLM Extractor")
    print("=" * 80)
    llm_success = test_llm_extractor()

    # Test 2: Knowledge extractor with LLM
    print("\n" + "=" * 80)
    print("Test 2: Knowledge Extractor with LLM")
    print("=" * 80)
    knowledge_success = test_knowledge_extractor_with_llm()

    # Summary
    print("\n" + "=" * 80)
    print("Test Summary")
    print("=" * 80)
    print(f"LLM Extractor test: {'✓ PASS' if llm_success else '✗ FAIL'}")
    print(f"Knowledge Extractor test: {'✓ PASS' if knowledge_success else '✗ FAIL'}")

    if llm_success and knowledge_success:
        print("\n✅ All tests passed! LLM extraction is working.")
        print("\nNext steps:")
        print("1. Restart Flask app to use new configuration")
        print("2. Trigger knowledge extraction for readme.txt:")
        print("   - Web: http://localhost:5000 → find readme.txt → click 'Extract Knowledge'")
        print("   - API: GET http://localhost:5000/graph/extract/readme.txt")
        print("3. Build graph: GET http://localhost:5000/graph/build/readme.txt")
        print("4. View graph: http://localhost:5000/graph?document_id=readme.txt")
    else:
        print("\n❌ Some tests failed. Check Ollama service and configuration.")

if __name__ == "__main__":
    main()
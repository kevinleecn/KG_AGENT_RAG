#!/usr/bin/env python3
"""
Test Chinese knowledge extraction with multi-language spaCy model.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.nlp.knowledge_extractor import KnowledgeExtractor

def main():
    # Load the parsed text
    parsed_file = "data/parsed/2_parsed.txt"
    if not os.path.exists(parsed_file):
        print(f"Parsed file not found: {parsed_file}")
        return

    with open(parsed_file, 'r', encoding='utf-8') as f:
        text = f.read()

    print(f"Loaded text ({len(text)} chars, {len(text.split())} words)")
    # Skip printing Chinese text to avoid encoding issues on Windows
    # print("First 500 chars:")
    # print(text[:500])
    print("\n" + "="*80 + "\n")

    # Initialize extractor with Chinese model
    extractor = KnowledgeExtractor(spacy_model='zh_core_web_sm', use_llm=False)

    # Extract knowledge
    print("Extracting knowledge...")
    result = extractor.extract_from_text(text, document_id='2.docx')

    # Print results
    print(f"\nExtraction completed.")
    print(f"Entities found: {len(result['entities'])}")
    print(f"Relationships found: {len(result['relationships'])}")
    print(f"Triplets found: {len(result['triplets'])}")

    # Print entity details
    if result['entities']:
        print("\nTop entities:")
        for i, entity in enumerate(result['entities'][:20]):
            print(f"  {i+1}. '{entity.text}' ({entity.entity_type})")

    # Print relationship details
    if result['relationships']:
        print("\nTop relationships:")
        for i, rel in enumerate(result['relationships'][:10]):
            print(f"  {i+1}. '{rel.subject.text}' -> {rel.predicate} -> '{rel.object.text}'")

    # Print statistics
    stats = result['statistics']
    print(f"\nStatistics:")
    print(f"  Entity types: {stats.get('entity_types', {})}")
    print(f"  Relationship types: {stats.get('relationship_types', {})}")
    print(f"  Processing time: {stats.get('processing_time_seconds', 0):.2f}s")

if __name__ == "__main__":
    main()
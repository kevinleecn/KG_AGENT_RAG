"""
Document Parsing System Demo
Shows how to use the parsers with the existing file upload system.
"""

import os
import sys
import tempfile

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.document_parser.parser_factory import ParserFactory


def demo_parsing_workflow():
    """Demonstrate complete parsing workflow"""
    print("=== Knowledge Graph QA Demo - Phase 2: Document Parsing System ===")
    print()

    # Create a sample text file
    sample_content = """Knowledge Graph Document QA System - Sample Document

This is a sample document for testing the parsing system.
It contains multiple paragraphs with different content.

Section 1: Introduction
The Knowledge Graph QA system helps extract information from documents
and answer questions based on the content.

Section 2: Features
- Document parsing for multiple formats
- Text extraction and normalization
- Entity recognition and relationship extraction
- Question answering interface

Section 3: Supported Formats
The system supports TXT, DOCX, PDF, and PPTX files.
Each format is handled by a specialized parser.

End of document."""

    print("1. Creating sample text file...")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', encoding='utf-8', delete=False) as f:
        f.write(sample_content)
        file_path = f.name
        print(f"   Created: {file_path}")
        print(f"   Size: {len(sample_content)} characters")

    try:
        print("\n2. Getting appropriate parser...")
        factory = ParserFactory()
        parser = factory.get_parser(file_path)
        print(f"   Parser type: {type(parser).__name__}")

        print("\n3. Validating file...")
        is_valid, message = parser.validate(file_path)
        print(f"   Valid: {is_valid}")
        print(f"   Message: {message}")

        print("\n4. Parsing document...")
        result = parser.parse(file_path)

        if result['success']:
            print(f"   Success: {result['success']}")
            print(f"   Content extracted: {len(result['content'])} characters")
            print(f"   Metadata: {list(result['metadata'].keys())}")

            # Show first 200 characters of content
            preview = result['content'][:200] + "..." if len(result['content']) > 200 else result['content']
            print(f"\n5. Content preview:\n{'-'*50}")
            print(preview)
            print(f"{'-'*50}")

            # Show metadata details
            print(f"\n6. Metadata details:")
            metadata = result['metadata']
            for key in ['file_size', 'encoding', 'line_count', 'word_count']:
                if key in metadata:
                    print(f"   {key}: {metadata[key]}")

        else:
            print(f"   Error: {result['error']}")

    finally:
        os.unlink(file_path)
        print(f"\n7. Cleanup: Removed temporary file")

    print("\n" + "="*60)
    print("Document parsing system is ready for integration!")
    print(f"Supported formats: {', '.join(factory.get_supported_extensions())}")
    print("="*60)


def demo_error_handling():
    """Demonstrate error handling scenarios"""
    print("\n\n=== Error Handling Examples ===")

    factory = ParserFactory()

    print("\n1. Unsupported file format:")
    try:
        parser = factory.get_parser('document.exe')
    except ValueError as e:
        print(f"   Error: {e}")

    print("\n2. File without extension:")
    try:
        parser = factory.get_parser('document')
    except ValueError as e:
        print(f"   Error: {e}")

    print("\n3. Non-existent file:")
    parser = factory.get_parser('test.txt')
    result = parser.parse('non_existent_file.txt')
    print(f"   Success: {result['success']}")
    print(f"   Error: {result['error'][:80]}...")


if __name__ == '__main__':
    demo_parsing_workflow()
    demo_error_handling()
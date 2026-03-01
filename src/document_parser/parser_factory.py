"""
Parser factory for creating appropriate document parsers based on file extension.
"""

import os
from typing import Dict, Type
from .base_parser import BaseParser
from .txt_parser import TxtParser
from .docx_parser import DocxParser
from .pdf_parser import PdfParser
from .pptx_parser import PptxParser


class ParserFactory:
    """Factory class for creating document parsers"""

    # Registry of supported parsers by file extension
    _parser_registry: Dict[str, Type[BaseParser]] = {
        '.txt': TxtParser,
        '.docx': DocxParser,
        '.pdf': PdfParser,
        '.pptx': PptxParser,
    }

    @classmethod
    def get_parser(cls, file_path: str) -> BaseParser:
        """
        Get appropriate parser for the given file.

        Args:
            file_path: Path to the document file

        Returns:
            Instance of appropriate parser class

        Raises:
            ValueError: If file extension is not supported
        """
        # Extract file extension
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()

        # Check if file has an extension
        if not ext:
            raise ValueError(f"File has no extension: {file_path}")

        # Check if extension is supported
        if ext not in cls._parser_registry:
            supported = ', '.join(cls._parser_registry.keys())
            raise ValueError(
                f"Unsupported file extension: {ext}. "
                f"Supported extensions: {supported}"
            )

        # Create and return parser instance
        parser_class = cls._parser_registry[ext]
        return parser_class()

    @classmethod
    def get_supported_extensions(cls) -> list:
        """
        Get list of supported file extensions.

        Returns:
            List of supported file extensions
        """
        return list(cls._parser_registry.keys())

    @classmethod
    def is_supported(cls, file_path: str) -> bool:
        """
        Check if file extension is supported.

        Args:
            file_path: Path to the file

        Returns:
            True if file extension is supported, False otherwise
        """
        _, ext = os.path.splitext(file_path)
        return ext.lower() in cls._parser_registry

    @classmethod
    def register_parser(cls, extension: str, parser_class: Type[BaseParser]) -> None:
        """
        Register a new parser for a file extension.

        Args:
            extension: File extension (e.g., '.md', '.rtf')
            parser_class: Parser class to handle this extension

        Raises:
            ValueError: If parser_class is not a subclass of BaseParser
        """
        if not issubclass(parser_class, BaseParser):
            raise ValueError(f"Parser class must be a subclass of BaseParser")

        cls._parser_registry[extension.lower()] = parser_class
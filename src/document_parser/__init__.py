"""
Document Parser Module for Knowledge Graph QA Demo System.
Provides parsers for various document formats.
"""

from .base_parser import BaseParser
from .txt_parser import TxtParser
from .docx_parser import DocxParser
from .pdf_parser import PdfParser
from .pptx_parser import PptxParser
from .parser_factory import ParserFactory

__all__ = [
    'BaseParser',
    'TxtParser',
    'DocxParser',
    'PdfParser',
    'PptxParser',
    'ParserFactory',
]

__version__ = '1.0.0'
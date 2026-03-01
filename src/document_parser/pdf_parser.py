"""
PDF file parser for Adobe PDF documents.
Uses PyPDF2 and pdfplumber for text extraction.
"""

import os
from typing import Tuple
from .base_parser import BaseParser


class PdfParser(BaseParser):
    """Parser for PDF (.pdf) files"""

    def __init__(self):
        """Initialize PDF parser"""
        self.supported_extensions = {'.pdf'}

    def parse(self, file_path: str) -> dict:
        """
        Parse PDF file and extract text content.

        Args:
            file_path: Path to the PDF file

        Returns:
            Dictionary with parsing results
        """
        # Validate file first
        is_valid, message = self.validate(file_path)
        if not is_valid:
            return {
                'success': False,
                'content': '',
                'metadata': {'file_path': file_path, 'error': message},
                'error': message
            }

        try:
            # Try pdfplumber first (better text extraction)
            try:
                import pdfplumber
                return self._parse_with_pdfplumber(file_path)
            except ImportError:
                # Fall back to PyPDF2
                return self._parse_with_pypdf2(file_path)

        except Exception as e:
            return {
                'success': False,
                'content': '',
                'metadata': {'file_path': file_path},
                'error': f"Error parsing PDF file: {str(e)}"
            }

    def _parse_with_pdfplumber(self, file_path: str) -> dict:
        """Parse PDF using pdfplumber library"""
        import pdfplumber

        all_text = []
        metadata = self.get_metadata(file_path)

        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                try:
                    text = page.extract_text()
                    if text:
                        all_text.append(text)
                except Exception as e:
                    # Log error but continue with other pages
                    if 'errors' not in metadata:
                        metadata['errors'] = []
                    metadata['errors'].append(f"Page {page_num}: {str(e)}")

        content = '\n\n'.join(all_text)

        return {
            'success': True,
            'content': content,
            'metadata': metadata,
            'error': None
        }

    def _parse_with_pypdf2(self, file_path: str) -> dict:
        """Parse PDF using PyPDF2 library (fallback)"""
        from PyPDF2 import PdfReader

        all_text = []
        metadata = self.get_metadata(file_path)

        with open(file_path, 'rb') as file:
            pdf_reader = PdfReader(file)

            for page_num, page in enumerate(pdf_reader.pages, 1):
                try:
                    text = page.extract_text()
                    if text:
                        all_text.append(text)
                except Exception as e:
                    # Log error but continue with other pages
                    if 'errors' not in metadata:
                        metadata['errors'] = []
                    metadata['errors'].append(f"Page {page_num}: {str(e)}")

        content = '\n\n'.join(all_text)

        return {
            'success': True,
            'content': content,
            'metadata': metadata,
            'error': None
        }

    def get_metadata(self, file_path: str) -> dict:
        """
        Get metadata about the PDF file.

        Args:
            file_path: Path to the PDF file

        Returns:
            Dictionary with file metadata
        """
        metadata = self._get_basic_metadata(file_path)

        try:
            # Try PyPDF2 first for metadata
            from PyPDF2 import PdfReader

            with open(file_path, 'rb') as file:
                pdf_reader = PdfReader(file)

                # Get PDF metadata
                pdf_metadata = {}
                if pdf_reader.metadata:
                    for key, value in pdf_reader.metadata.items():
                        # Remove leading slash from metadata keys
                        clean_key = key.lstrip('/')
                        pdf_metadata[clean_key] = value

                # Get page count
                page_count = len(pdf_reader.pages)

                metadata.update({
                    'page_count': page_count,
                    'pdf_metadata': pdf_metadata,
                    'is_encrypted': pdf_reader.is_encrypted,
                    'has_outline': len(pdf_reader.outline) > 0 if hasattr(pdf_reader, 'outline') else False,
                })

                # Try to get more detailed info with pdfplumber if available
                try:
                    import pdfplumber
                    with pdfplumber.open(file_path) as pdf:
                        # Get dimensions of first page
                        if pdf.pages:
                            first_page = pdf.pages[0]
                            metadata.update({
                                'page_width': first_page.width,
                                'page_height': first_page.height,
                            })
                except ImportError:
                    pass  # pdfplumber not installed, skip

        except ImportError:
            metadata['error'] = "PyPDF2 library not installed"
        except Exception as e:
            metadata['error'] = f"Error reading PDF metadata: {str(e)}"

        return metadata

    def validate(self, file_path: str) -> Tuple[bool, str]:
        """
        Validate if file is a valid PDF file.

        Args:
            file_path: Path to the file

        Returns:
            Tuple of (is_valid: bool, message: str)
        """
        # Check if file exists and is readable
        file_valid, file_message = self._validate_file_exists(file_path)
        if not file_valid:
            return False, file_message

        # Check file extension
        _, ext = os.path.splitext(file_path)
        if ext.lower() not in self.supported_extensions:
            return False, f"File extension {ext} is not supported. Expected .pdf"

        # Check PDF signature
        # Only check if file is large enough
        try:
            if os.path.getsize(file_path) >= 5:
                with open(file_path, 'rb') as f:
                    header = f.read(5)
                    # PDF files start with "%PDF-"
                    if not header.startswith(b'%PDF-'):
                        return False, "File does not appear to be a valid PDF (missing PDF header)"
        except (IOError, OSError):
            pass  # Skip signature check if we can't read file

        return True, "Valid PDF file"
"""
PDF file parser for Adobe PDF documents.
Uses PyPDF2 and pdfplumber for text extraction.
"""

import os
import time
from typing import Tuple, Optional, Callable
from .base_parser import BaseParser


class PdfParser(BaseParser):
    """Parser for PDF (.pdf) files"""

    def __init__(self):
        """Initialize PDF parser"""
        self.supported_extensions = {'.pdf'}

    def parse(self, file_path: str, timeout: int = 60, max_pages: int = 0) -> dict:
        """
        Parse PDF file and extract text content.

        Args:
            file_path: Path to the PDF file
            timeout: Maximum parsing time in seconds (default: 60)
            max_pages: Maximum number of pages to parse (0 = all pages, default: 0)

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
                return self._parse_with_pdfplumber(file_path, timeout=timeout, max_pages=max_pages)
            except ImportError:
                # Fall back to PyPDF2
                return self._parse_with_pypdf2(file_path, timeout=timeout, max_pages=max_pages)

        except Exception as e:
            return {
                'success': False,
                'content': '',
                'metadata': {'file_path': file_path},
                'error': f"Error parsing PDF file: {str(e)}"
            }

    def _parse_with_pdfplumber(self, file_path: str, timeout: int = 60, max_pages: int = 0) -> dict:
        """Parse PDF using pdfplumber library

        Args:
            file_path: Path to PDF file
            timeout: Maximum parsing time in seconds (default: 60)
            max_pages: Maximum number of pages to parse (0 = all pages, default: 0)
        """
        import pdfplumber
        import time

        all_text = []
        metadata = self.get_metadata(file_path)
        start_time = time.time()
        pages_parsed = 0
        timeout_reached = False

        try:
            with pdfplumber.open(file_path) as pdf:
                total_pages = len(pdf.pages)
                metadata['page_count'] = total_pages

                # Determine how many pages to parse
                if max_pages > 0 and max_pages < total_pages:
                    pages_to_parse = max_pages
                    metadata['pages_parsed'] = pages_to_parse
                    metadata['pages_skipped'] = total_pages - pages_to_parse
                else:
                    pages_to_parse = total_pages

                for page_num in range(pages_to_parse):
                    # Check timeout
                    if time.time() - start_time > timeout:
                        timeout_reached = True
                        metadata['timeout_reached'] = True
                        metadata['timeout_seconds'] = timeout
                        break

                    try:
                        page = pdf.pages[page_num]
                        text = page.extract_text()
                        if text:
                            all_text.append(text)
                            pages_parsed += 1
                        else:
                            # Still count as parsed even if no text
                            pages_parsed += 1
                            if 'empty_pages' not in metadata:
                                metadata['empty_pages'] = []
                            metadata['empty_pages'].append(page_num + 1)
                    except Exception as e:
                        # Log error but continue with other pages
                        pages_parsed += 1
                        if 'errors' not in metadata:
                            metadata['errors'] = []
                        metadata['errors'].append(f"Page {page_num + 1}: {str(e)}")

                metadata['pages_parsed'] = pages_parsed
                metadata['parsing_time_seconds'] = time.time() - start_time

        except Exception as e:
            return {
                'success': False,
                'content': '',
                'metadata': metadata,
                'error': f"Error opening PDF with pdfplumber: {str(e)}"
            }

        content = '\n\n'.join(all_text)

        # Check if we got any content
        if not content.strip():
            return {
                'success': False,
                'content': '',
                'metadata': metadata,
                'error': 'No text content extracted from PDF. File may contain only images or have unsupported format.'
            }

        result = {
            'success': True,
            'content': content,
            'metadata': metadata,
            'error': None
        }

        if timeout_reached:
            result['warning'] = f'Parsing stopped after timeout ({timeout} seconds). Parsed {pages_parsed} of {total_pages} pages.'
            metadata['partial_parse'] = True

        return result

    def _parse_with_pypdf2(self, file_path: str, timeout: int = 60, max_pages: int = 0) -> dict:
        """Parse PDF using PyPDF2 library (fallback)

        Args:
            file_path: Path to PDF file
            timeout: Maximum parsing time in seconds (default: 60)
            max_pages: Maximum number of pages to parse (0 = all pages, default: 0)
        """
        from PyPDF2 import PdfReader
        import time

        all_text = []
        metadata = self.get_metadata(file_path)
        start_time = time.time()
        pages_parsed = 0
        timeout_reached = False

        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PdfReader(file)
                total_pages = len(pdf_reader.pages)
                metadata['page_count'] = total_pages

                # Determine how many pages to parse
                if max_pages > 0 and max_pages < total_pages:
                    pages_to_parse = max_pages
                    metadata['pages_parsed'] = pages_to_parse
                    metadata['pages_skipped'] = total_pages - pages_to_parse
                else:
                    pages_to_parse = total_pages

                for page_num in range(pages_to_parse):
                    # Check timeout
                    if time.time() - start_time > timeout:
                        timeout_reached = True
                        metadata['timeout_reached'] = True
                        metadata['timeout_seconds'] = timeout
                        break

                    try:
                        page = pdf_reader.pages[page_num]
                        text = page.extract_text()
                        if text:
                            all_text.append(text)
                            pages_parsed += 1
                        else:
                            # Still count as parsed even if no text
                            pages_parsed += 1
                            if 'empty_pages' not in metadata:
                                metadata['empty_pages'] = []
                            metadata['empty_pages'].append(page_num + 1)
                    except Exception as e:
                        # Log error but continue with other pages
                        pages_parsed += 1
                        if 'errors' not in metadata:
                            metadata['errors'] = []
                        metadata['errors'].append(f"Page {page_num + 1}: {str(e)}")

                metadata['pages_parsed'] = pages_parsed
                metadata['parsing_time_seconds'] = time.time() - start_time

        except Exception as e:
            return {
                'success': False,
                'content': '',
                'metadata': metadata,
                'error': f"Error opening PDF with PyPDF2: {str(e)}"
            }

        content = '\n\n'.join(all_text)

        # Check if we got any content
        if not content.strip():
            return {
                'success': False,
                'content': '',
                'metadata': metadata,
                'error': 'No text content extracted from PDF. File may contain only images or have unsupported format.'
            }

        result = {
            'success': True,
            'content': content,
            'metadata': metadata,
            'error': None
        }

        if timeout_reached:
            result['warning'] = f'Parsing stopped after timeout ({timeout} seconds). Parsed {pages_parsed} of {total_pages} pages.'
            metadata['partial_parse'] = True

        return result

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

    def parse_with_progress(self, file_path: str, progress_callback: Optional[Callable] = None,
                           timeout: int = 60, max_pages: int = 0) -> dict:
        """
        Parse PDF file with progress updates.

        Args:
            file_path: Path to the PDF file
            progress_callback: Callback function for progress updates.
                Signature: callback(step, total, description, message)
            timeout: Maximum parsing time in seconds (default: 60)
            max_pages: Maximum number of pages to parse (0 = all pages, default: 0)

        Returns:
            Dictionary with parsing results
        """
        # Validate file first
        is_valid, message = self.validate(file_path)
        if not is_valid:
            if progress_callback:
                progress_callback(0, 1, "Validation failed", message)
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
                if progress_callback:
                    progress_callback(1, 100, "Starting parsing", "Using pdfplumber for text extraction")
                return self._parse_with_pdfplumber_with_progress(
                    file_path, progress_callback, timeout=timeout, max_pages=max_pages
                )
            except ImportError:
                # Fall back to PyPDF2
                if progress_callback:
                    progress_callback(1, 100, "Starting parsing", "Using PyPDF2 for text extraction (pdfplumber not available)")
                return self._parse_with_pypdf2_with_progress(
                    file_path, progress_callback, timeout=timeout, max_pages=max_pages
                )

        except Exception as e:
            error_msg = f"Error parsing PDF file: {str(e)}"
            if progress_callback:
                progress_callback(0, 1, "Parsing failed", error_msg)
            return {
                'success': False,
                'content': '',
                'metadata': {'file_path': file_path},
                'error': error_msg
            }

    def _parse_with_pdfplumber_with_progress(self, file_path: str,
                                           progress_callback: Optional[Callable] = None,
                                           timeout: int = 60, max_pages: int = 0) -> dict:
        """Parse PDF using pdfplumber library with progress updates

        Args:
            file_path: Path to PDF file
            progress_callback: Callback function for progress updates
            timeout: Maximum parsing time in seconds (default: 60)
            max_pages: Maximum number of pages to parse (0 = all pages, default: 0)
        """
        import pdfplumber

        all_text = []
        metadata = self.get_metadata(file_path)
        start_time = time.time()
        pages_parsed = 0
        timeout_reached = False

        # Get page count for progress tracking
        try:
            with pdfplumber.open(file_path) as pdf:
                total_pages = len(pdf.pages)
                metadata['page_count'] = total_pages

                if progress_callback:
                    progress_callback(5, 100, "Getting page count",
                                    f"Found {total_pages} pages in PDF")

                # Determine how many pages to parse
                if max_pages > 0 and max_pages < total_pages:
                    pages_to_parse = max_pages
                    metadata['pages_parsed'] = pages_to_parse
                    metadata['pages_skipped'] = total_pages - pages_to_parse
                else:
                    pages_to_parse = total_pages

                for page_num in range(pages_to_parse):
                    # Check timeout
                    if time.time() - start_time > timeout:
                        timeout_reached = True
                        metadata['timeout_reached'] = True
                        metadata['timeout_seconds'] = timeout
                        if progress_callback:
                            progress_callback(95, 100, "Timeout reached",
                                            f"Parsing stopped after {timeout} seconds")
                        break

                    # Update progress
                    if progress_callback:
                        progress_percent = 5 + int((page_num + 1) * 90 / pages_to_parse)
                        progress_callback(
                            progress_percent, 100,
                            f"Parsing page {page_num + 1}/{pages_to_parse}",
                            f"Extracting text from page {page_num + 1}"
                        )

                    try:
                        page = pdf.pages[page_num]
                        text = page.extract_text()
                        if text:
                            all_text.append(text)
                            pages_parsed += 1
                        else:
                            # Still count as parsed even if no text
                            pages_parsed += 1
                            if 'empty_pages' not in metadata:
                                metadata['empty_pages'] = []
                            metadata['empty_pages'].append(page_num + 1)
                    except Exception as e:
                        # Log error but continue with other pages
                        pages_parsed += 1
                        if 'errors' not in metadata:
                            metadata['errors'] = []
                        metadata['errors'].append(f"Page {page_num + 1}: {str(e)}")

                metadata['pages_parsed'] = pages_parsed
                metadata['parsing_time_seconds'] = time.time() - start_time

        except Exception as e:
            if progress_callback:
                progress_callback(0, 100, "Error opening PDF", str(e))
            return {
                'success': False,
                'content': '',
                'metadata': metadata,
                'error': f"Error opening PDF with pdfplumber: {str(e)}"
            }

        content = '\n\n'.join(all_text)

        # Check if we got any content
        if not content.strip():
            if progress_callback:
                progress_callback(0, 100, "No text extracted",
                                "File may contain only images or have unsupported format")
            return {
                'success': False,
                'content': '',
                'metadata': metadata,
                'error': 'No text content extracted from PDF. File may contain only images or have unsupported format.'
            }

        result = {
            'success': True,
            'content': content,
            'metadata': metadata,
            'error': None
        }

        if timeout_reached:
            result['warning'] = f'Parsing stopped after timeout ({timeout} seconds). Parsed {pages_parsed} of {total_pages} pages.'
            metadata['partial_parse'] = True

        if progress_callback:
            progress_callback(100, 100, "Parsing completed",
                            f"Successfully parsed {pages_parsed} pages")

        return result

    def _parse_with_pypdf2_with_progress(self, file_path: str,
                                        progress_callback: Optional[Callable] = None,
                                        timeout: int = 60, max_pages: int = 0) -> dict:
        """Parse PDF using PyPDF2 library with progress updates (fallback)

        Args:
            file_path: Path to PDF file
            progress_callback: Callback function for progress updates
            timeout: Maximum parsing time in seconds (default: 60)
            max_pages: Maximum number of pages to parse (0 = all pages, default: 0)
        """
        from PyPDF2 import PdfReader

        all_text = []
        metadata = self.get_metadata(file_path)
        start_time = time.time()
        pages_parsed = 0
        timeout_reached = False

        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PdfReader(file)
                total_pages = len(pdf_reader.pages)
                metadata['page_count'] = total_pages

                if progress_callback:
                    progress_callback(5, 100, "Getting page count",
                                    f"Found {total_pages} pages in PDF")

                # Determine how many pages to parse
                if max_pages > 0 and max_pages < total_pages:
                    pages_to_parse = max_pages
                    metadata['pages_parsed'] = pages_to_parse
                    metadata['pages_skipped'] = total_pages - pages_to_parse
                else:
                    pages_to_parse = total_pages

                for page_num in range(pages_to_parse):
                    # Check timeout
                    if time.time() - start_time > timeout:
                        timeout_reached = True
                        metadata['timeout_reached'] = True
                        metadata['timeout_seconds'] = timeout
                        if progress_callback:
                            progress_callback(95, 100, "Timeout reached",
                                            f"Parsing stopped after {timeout} seconds")
                        break

                    # Update progress
                    if progress_callback:
                        progress_percent = 5 + int((page_num + 1) * 90 / pages_to_parse)
                        progress_callback(
                            progress_percent, 100,
                            f"Parsing page {page_num + 1}/{pages_to_parse}",
                            f"Extracting text from page {page_num + 1}"
                        )

                    try:
                        page = pdf_reader.pages[page_num]
                        text = page.extract_text()
                        if text:
                            all_text.append(text)
                            pages_parsed += 1
                        else:
                            # Still count as parsed even if no text
                            pages_parsed += 1
                            if 'empty_pages' not in metadata:
                                metadata['empty_pages'] = []
                            metadata['empty_pages'].append(page_num + 1)
                    except Exception as e:
                        # Log error but continue with other pages
                        pages_parsed += 1
                        if 'errors' not in metadata:
                            metadata['errors'] = []
                        metadata['errors'].append(f"Page {page_num + 1}: {str(e)}")

                metadata['pages_parsed'] = pages_parsed
                metadata['parsing_time_seconds'] = time.time() - start_time

        except Exception as e:
            if progress_callback:
                progress_callback(0, 100, "Error opening PDF", str(e))
            return {
                'success': False,
                'content': '',
                'metadata': metadata,
                'error': f"Error opening PDF with PyPDF2: {str(e)}"
            }

        content = '\n\n'.join(all_text)

        # Check if we got any content
        if not content.strip():
            if progress_callback:
                progress_callback(0, 100, "No text extracted",
                                "File may contain only images or have unsupported format")
            return {
                'success': False,
                'content': '',
                'metadata': metadata,
                'error': 'No text content extracted from PDF. File may contain only images or have unsupported format.'
            }

        result = {
            'success': True,
            'content': content,
            'metadata': metadata,
            'error': None
        }

        if timeout_reached:
            result['warning'] = f'Parsing stopped after timeout ({timeout} seconds). Parsed {pages_parsed} of {total_pages} pages.'
            metadata['partial_parse'] = True

        if progress_callback:
            progress_callback(100, 100, "Parsing completed",
                            f"Successfully parsed {pages_parsed} pages")

        return result
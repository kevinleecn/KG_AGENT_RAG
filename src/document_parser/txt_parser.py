"""
TXT file parser for plain text documents.
Handles various encodings and provides text extraction.
"""

import os
import chardet
from typing import Tuple
from .base_parser import BaseParser


class TxtParser(BaseParser):
    """Parser for plain text (.txt) files"""

    def __init__(self):
        """Initialize TXT parser"""
        self.supported_extensions = {'.txt'}

    def parse(self, file_path: str) -> dict:
        """
        Parse TXT file and extract text content.

        Args:
            file_path: Path to the TXT file

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
            # Detect encoding and read file
            encoding = self._detect_encoding(file_path)
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                content = f.read()

            # Get metadata
            metadata = self.get_metadata(file_path)
            metadata['encoding'] = encoding

            return {
                'success': True,
                'content': content,
                'metadata': metadata,
                'error': None
            }

        except Exception as e:
            return {
                'success': False,
                'content': '',
                'metadata': {'file_path': file_path},
                'error': f"Error parsing TXT file: {str(e)}"
            }

    def get_metadata(self, file_path: str) -> dict:
        """
        Get metadata about the TXT file.

        Args:
            file_path: Path to the TXT file

        Returns:
            Dictionary with file metadata
        """
        metadata = self._get_basic_metadata(file_path)

        try:
            # Add TXT-specific metadata
            encoding = self._detect_encoding(file_path)
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                content = f.read()

            # Count lines and words
            lines = content.splitlines()
            words = content.split()

            metadata.update({
                'encoding': encoding,
                'line_count': len(lines),
                'word_count': len(words),
                'character_count': len(content),
                'has_content': len(content.strip()) > 0
            })

        except Exception as e:
            metadata['error'] = f"Error reading metadata: {str(e)}"

        return metadata

    def validate(self, file_path: str) -> Tuple[bool, str]:
        """
        Validate if file is a valid TXT file.

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
        ext = ext.lower()
        if ext not in self.supported_extensions:
            return False, f"File is not a .txt file (extension: {ext})"

        # Check if file is not empty (optional, empty files are valid TXT files)
        try:
            if os.path.getsize(file_path) == 0:
                return True, "Valid text file (empty)"
        except OSError:
            pass

        return True, "Valid text file"

    def _detect_encoding(self, file_path: str) -> str:
        """
        Detect file encoding using chardet.

        Args:
            file_path: Path to the file

        Returns:
            Detected encoding string
        """
        try:
            # Read a sample of the file for encoding detection
            with open(file_path, 'rb') as f:
                raw_data = f.read(10000)  # Read first 10KB for detection

            if not raw_data:
                return 'utf-8'  # Default for empty files

            # Detect encoding
            result = chardet.detect(raw_data)
            encoding = result.get('encoding', 'utf-8')

            # Fallback to utf-8 if detection failed or confidence is low
            if encoding is None or result.get('confidence', 0) < 0.5:
                encoding = 'utf-8'

            # Common encoding aliases and normalization
            encoding = encoding.lower()

            encoding_map = {
                'ascii': 'utf-8',  # ASCII is subset of UTF-8
                'iso-8859-1': 'latin-1',
                'iso-8859-2': 'latin-1',
                'windows-1252': 'cp1252',
                'utf-8-sig': 'utf-8',  # UTF-8 with BOM
            }

            return encoding_map.get(encoding, encoding)

        except Exception:
            # Default to utf-8 if detection fails
            return 'utf-8'
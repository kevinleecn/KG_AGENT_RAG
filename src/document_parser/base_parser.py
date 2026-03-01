"""
Base parser abstract class for document parsing system.
Defines the interface that all concrete parsers must implement.
"""

from abc import ABC, abstractmethod
import os


class BaseParser(ABC):
    """Abstract base class for all document parsers"""

    @abstractmethod
    def parse(self, file_path: str) -> dict:
        """
        Parse the document and extract text content.

        Args:
            file_path: Path to the document file

        Returns:
            Dictionary with:
                - success: bool indicating if parsing succeeded
                - content: str containing extracted text (empty if failed)
                - metadata: dict with file metadata
                - error: str error message (only if success=False)
        """
        pass

    @abstractmethod
    def get_metadata(self, file_path: str) -> dict:
        """
        Get metadata about the document without parsing content.

        Args:
            file_path: Path to the document file

        Returns:
            Dictionary with file metadata
        """
        pass

    @abstractmethod
    def validate(self, file_path: str) -> tuple[bool, str]:
        """
        Validate if the file can be parsed by this parser.

        Args:
            file_path: Path to the document file

        Returns:
            Tuple of (is_valid: bool, message: str)
        """
        pass

    def _get_basic_metadata(self, file_path: str) -> dict:
        """
        Helper method to get basic file metadata.

        Args:
            file_path: Path to the file

        Returns:
            Dictionary with basic metadata
        """
        try:
            stat = os.stat(file_path)
            return {
                'file_path': file_path,
                'file_size': stat.st_size,
                'modified_time': stat.st_mtime,
                'created_time': stat.st_ctime
            }
        except (OSError, IOError) as e:
            return {
                'file_path': file_path,
                'error': str(e)
            }

    def _validate_file_exists(self, file_path: str) -> tuple[bool, str]:
        """
        Helper method to validate file exists and is readable.

        Args:
            file_path: Path to the file

        Returns:
            Tuple of (is_valid: bool, message: str)
        """
        if not os.path.exists(file_path):
            return False, f"File not found: {file_path}"

        if not os.path.isfile(file_path):
            return False, f"Path is not a file: {file_path}"

        if not os.access(file_path, os.R_OK):
            return False, f"File is not readable: {file_path}"

        return True, "File exists and is readable"
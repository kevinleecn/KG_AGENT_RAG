#!/usr/bin/env python3
"""
Clean Python bytecode files to prevent sensitive data leakage.

Run this before publishing to version control or deploying to production.

Usage:
    python clean_bytecode.py

Or add to pre-commit hook:
    python clean_bytecode.py && git add -A
"""

import os
import shutil
from pathlib import Path


def clean_bytecode(root_dir: str = ".") -> tuple[int, int]:
    """
    Remove all __pycache__ directories and .pyc files.

    Args:
        root_dir: Root directory to search from

    Returns:
        Tuple of (directories_removed, files_removed)
    """
    root = Path(root_dir).resolve()
    directories_removed = 0
    files_removed = 0

    # Remove __pycache__ directories
    for cache_dir in root.rglob("__pycache__"):
        if cache_dir.is_dir():
            shutil.rmtree(cache_dir)
            directories_removed += 1
            print(f"  Removed: {cache_dir.relative_to(root)}")

    # Remove .pyc files (in case any exist outside __pycache__)
    for pyc_file in root.rglob("*.pyc"):
        pyc_file.unlink()
        files_removed += 1
        print(f"  Removed: {pyc_file.relative_to(root)}")

    # Remove .pyo files (optimized bytecode)
    for pyo_file in root.rglob("*.pyo"):
        pyo_file.unlink()
        files_removed += 1
        print(f"  Removed: {pyo_file.relative_to(root)}")

    return directories_removed, files_removed


def main():
    print("=" * 60)
    print("Python Bytecode Cleaner")
    print("=" * 60)
    print()
    print("Scanning for bytecode files...")
    print()

    dirs, files = clean_bytecode()

    print()
    print("=" * 60)
    print(f"Cleanup complete!")
    print(f"  Directories removed: {dirs}")
    print(f"  Files removed: {files}")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    exit(main())

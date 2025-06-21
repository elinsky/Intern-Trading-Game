#!/usr/bin/env python3
"""
Pre-commit hook to check for reStructuredText math directives in Python files.

This script scans Python files for the pattern '.. math::' which indicates
a reStructuredText math directive. These should be replaced with MathJax syntax
using $$ delimiters for proper rendering in MkDocs documentation.
"""

import argparse
import re
import sys
from pathlib import Path
from typing import List, Tuple


def check_file(file_path: str) -> List[Tuple[int, str]]:
    """
    Check a file for reStructuredText math directives.

    Parameters
    ----------
    file_path : str
        Path to the file to check.

    Returns
    -------
    List[Tuple[int, str]]
        List of tuples containing line number and line content for each match.
    """
    matches = []
    with open(file_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            if re.search(r"\.\.[\s]*math::", line):
                matches.append((i, line.strip()))
    return matches


def should_check_file(file_path: str) -> bool:
    """
    Determine if a file should be checked for math directives.

    Parameters
    ----------
    file_path : str
        Path to the file to check.

    Returns
    -------
    bool
        True if the file should be checked, False otherwise.
    """
    if not Path(file_path).exists():
        return False

    # Skip the pre-commit hook itself to avoid false positives
    if file_path.endswith("check_math_directives.py"):
        return False

    # Only check Python files
    if not file_path.endswith(".py"):
        return False

    return True


def print_match_details(line_num: int, line: str) -> None:
    """
    Print details about a found math directive match.

    Parameters
    ----------
    line_num : int
        The line number where the match was found.
    line : str
        The content of the line with the match.
    """
    print(f"  Line {line_num}: {line}")
    print(
        "  Found reStructuredText math directive. Please use MathJax syntax instead:"
    )
    print("  Replace:")
    print("    .. math::")
    print("")
    print("        Priority = (Price, Time)")
    print("  With:")
    print("    $$\\text{Priority} = (\\text{Price}, \\text{Time})$$")
    print(
        "  See docs/contributing/docstring-math-guide.md for more information."
    )
    print()


def process_files(files: List[str]) -> int:
    """
    Process a list of files and check for math directives.

    Parameters
    ----------
    files : List[str]
        List of file paths to check.

    Returns
    -------
    int
        Exit code (0 if no issues found, 1 if issues found).
    """
    exit_code = 0

    for file_path in files:
        if not should_check_file(file_path):
            continue

        matches = check_file(file_path)
        if matches:
            exit_code = 1
            print(f"\n{file_path}:")
            for line_num, line in matches:
                print_match_details(line_num, line)

    return exit_code


def main():
    """Run the pre-commit hook."""
    parser = argparse.ArgumentParser(
        description="Check for reStructuredText math directives in Python files."
    )
    parser.add_argument(
        "files", nargs="+", help="Files to check for math directives."
    )
    args = parser.parse_args()

    exit_code = process_files(args.files)

    if exit_code == 0:
        print("No reStructuredText math directives found.")
    else:
        print(
            "\nPlease replace reStructuredText math directives with MathJax syntax."
        )
        print(
            "See docs/contributing/docstring-math-guide.md for more information."
        )

    sys.exit(exit_code)


if __name__ == "__main__":
    main()

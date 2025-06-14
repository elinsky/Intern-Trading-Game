"""Constants module for the Intern Trading Game.

This module contains all application constants including error codes,
error messages, and other shared constants to prevent string duplication
and ensure consistency across the codebase.
"""

from .errors import ErrorCodes, ErrorMessages

__all__ = ["ErrorCodes", "ErrorMessages"]
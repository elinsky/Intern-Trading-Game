"""Phase management for the exchange domain.

This package contains components for managing market phases and
their associated trading rules.
"""

from .interfaces import PhaseManagerInterface
from .manager import ConfigDrivenPhaseManager

__all__ = ["PhaseManagerInterface", "ConfigDrivenPhaseManager"]

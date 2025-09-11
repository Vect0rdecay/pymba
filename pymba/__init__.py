"""
Pymba - Python Firmware Security Analyzer

A Python port of the EMBA (Embedded Linux Analyzer) firmware security analysis tool.
"""

__version__ = "0.1.0"
__author__ = "Pymba Development Team"
__license__ = "GPL-3.0"

from .core.engine import PymbaEngine
from .core.config import PymbaConfig

__all__ = ["PymbaEngine", "PymbaConfig"]


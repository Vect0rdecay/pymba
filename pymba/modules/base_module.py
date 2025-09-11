#!/usr/bin/env python3
"""
Base module class for all Pymba analysis modules.

This module provides the base class and common functionality
for all analysis modules in Pymba.
"""

from abc import ABC, abstractmethod
from typing import Optional


class BaseModule(ABC):
    """Base class for all Pymba analysis modules."""
    
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.module_name = self.__class__.__name__
        self.exit_code = 0
    
    @abstractmethod
    def run(self) -> int:
        """
        Main module execution method.
        
        Returns:
            int: Exit code (0 for success, non-zero for failure)
        """
        pass
    
    def pre_module_reporter(self):
        """Called before module execution (placeholder for future functionality)."""
        pass
    
    def module_log_init(self):
        """Initialize module-specific logging."""
        self.logger.module_start_log(self.module_name)
    
    def module_end_log(self, exit_code: int = None):
        """Finalize module logging."""
        if exit_code is not None:
            self.exit_code = exit_code
        self.logger.module_end_log(self.module_name, self.exit_code)
    
    def print_output(self, message: str, log_type: str = "main"):
        """Print output with module context."""
        self.logger.print_output(f"[{self.module_name}] {message}", log_type)
    
    def print_error(self, message: str):
        """Print error message."""
        self.logger.error(f"[{self.module_name}] {message}")
    
    def print_success(self, message: str):
        """Print success message."""
        self.logger.success(f"[{self.module_name}] {message}")


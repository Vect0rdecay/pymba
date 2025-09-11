#!/usr/bin/env python3
"""
Base module class for Pymba analysis modules.

This module provides the base class that all analysis modules (P, S, L, F, Q, D)
inherit from, replacing the bash-based module system from EMBA.
"""

import os
import sys
import time
import threading
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from dataclasses import dataclass

from ..helpers.logging_utils import LogManager


@dataclass
class ModuleConfig:
    """Configuration for a module."""
    firmware_path: str
    log_dir: str
    output_dir: str
    temp_dir: str
    verbose: bool = False
    debug: bool = False
    timeout: Optional[int] = None
    max_threads: int = 1


class BaseModule(ABC):
    """Base class for all Pymba analysis modules."""
    
    # Module metadata - should be defined by subclasses
    MODULE_INFO = {
        'name': 'BaseModule',
        'description': 'Base module class',
        'version': '1.0.0',
        'author': 'Pymba Team',
        'category': 'Base',
        'priority': 0,
        'dependencies': [],
        'can_run_parallel': True,
        'max_threads': 1,
        'timeout': None,
        'enabled': True
    }
    
    def __init__(self, config: ModuleConfig, log_manager: LogManager):
        self.config = config
        self.log_manager = log_manager
        
        # Module identification
        self.module_name = self.__class__.__name__
        self.category = self.MODULE_INFO.get('category', 'Unknown')
        self.priority = self.MODULE_INFO.get('priority', 0)
        
        # Execution state
        self.start_time = None
        self.end_time = None
        self.duration = 0.0
        self.exit_code = 0
        self.status = "pending"
        
        # Threading
        self._lock = threading.Lock()
        self._thread_local = threading.local()
        
        # Module-specific paths
        self.module_log_file = None
        self.temp_files: List[str] = []
        
        # Initialize module
        self._initialize_module()
    
    def _initialize_module(self):
        """Initialize module-specific settings."""
        # Create module-specific log file
        if self.config.log_dir:
            log_dir = Path(self.config.log_dir)
            log_dir.mkdir(parents=True, exist_ok=True)
            self.module_log_file = log_dir / f"{self.module_name.lower()}.txt"
        
        # Set up module-specific temporary directory
        if self.config.temp_dir:
            temp_dir = Path(self.config.temp_dir) / self.module_name.lower()
            temp_dir.mkdir(parents=True, exist_ok=True)
            self.temp_dir = str(temp_dir)
        else:
            self.temp_dir = None
    
    @abstractmethod
    def run(self) -> int:
        """
        Main module execution method.
        
        Returns:
            int: Exit code (0 for success, non-zero for failure)
        """
        pass
    
    def pre_run(self) -> bool:
        """
        Pre-execution setup and validation.
        
        Returns:
            bool: True if module should run, False to skip
        """
        return True
    
    def post_run(self) -> None:
        """Post-execution cleanup and finalization."""
        self._cleanup_temp_files()
    
    def module_log_init(self):
        """Initialize module logging."""
        if self.module_log_file:
            self.log_manager.log_file = self.module_log_file
        
        self.log_manager.module_start_log(self.module_name)
        self.log_manager.module_title(f"{self.module_name} - {self.MODULE_INFO.get('description', '')}")
    
    def module_end_log(self, exit_code: int = 0):
        """Finalize module logging."""
        self.log_manager.module_end_log(self.module_name, exit_code)
    
    def print_output(self, message: str, log_type: str = "log"):
        """Print output using the log manager."""
        self.log_manager.print_output(message, log_type)
    
    def print_error(self, message: str):
        """Print error message."""
        self.log_manager.print_error(message)
    
    def print_warning(self, message: str):
        """Print warning message."""
        self.log_manager.print_warning(message)
    
    def print_success(self, message: str):
        """Print success message."""
        self.log_manager.print_success(message)
    
    def print_info(self, message: str):
        """Print info message."""
        self.log_manager.print_info(message)
    
    def print_debug(self, message: str):
        """Print debug message."""
        self.log_manager.print_debug(message)
    
    def sub_module_title(self, title: str):
        """Print sub-module title."""
        self.log_manager.sub_module_title(title)
    
    def write_link(self, filepath: str, text: Optional[str] = None):
        """Write file link to log."""
        self.log_manager.write_link(filepath, text)
    
    def write_anchor(self, anchor: str, text: str):
        """Write anchor reference to log."""
        self.log_manager.write_anchor(anchor, text)
    
    def write_log(self, message: str, log_file: Optional[str] = None):
        """Write message to specific log file."""
        self.log_manager.write_log(message, log_file)
    
    def create_temp_file(self, suffix: str = ".tmp") -> str:
        """Create a temporary file for this module."""
        if not self.temp_dir:
            import tempfile
            temp_file = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
            temp_path = temp_file.name
            temp_file.close()
        else:
            temp_path = os.path.join(self.temp_dir, f"temp_{len(self.temp_files)}{suffix}")
        
        self.temp_files.append(temp_path)
        return temp_path
    
    def _cleanup_temp_files(self):
        """Clean up temporary files created by this module."""
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except OSError as e:
                self.log_manager.print_warning(f"Failed to remove temp file {temp_file}: {e}")
        
        self.temp_files.clear()
    
    def run_command(self, command: Union[str, List[str]], 
                   cwd: Optional[str] = None,
                   timeout: Optional[int] = None,
                   capture_output: bool = True) -> tuple[int, str, str]:
        """
        Run a system command.
        
        Args:
            command: Command to run
            cwd: Working directory
            timeout: Command timeout
            capture_output: Whether to capture output
            
        Returns:
            tuple: (exit_code, stdout, stderr)
        """
        from ..helpers.system_utils import run_command
        return run_command(command, cwd, timeout, capture_output)
    
    def check_command_exists(self, command: str) -> bool:
        """Check if a command exists in PATH."""
        from ..helpers.system_utils import check_command_exists
        return check_command_exists(command)
    
    def get_file_size(self, filepath: str) -> int:
        """Get file size in bytes."""
        from ..helpers.file_utils import get_file_size
        return get_file_size(filepath)
    
    def is_binary_file(self, filepath: str) -> bool:
        """Check if file is binary."""
        from ..helpers.file_utils import is_binary_file
        return is_binary_file(filepath)
    
    def find_files(self, directory: str, pattern: str = "*", recursive: bool = True) -> List[str]:
        """Find files matching pattern."""
        from ..helpers.file_utils import find_files
        return find_files(directory, pattern, recursive)
    
    def get_file_hash(self, filepath: str, algorithm: str = 'sha256') -> Optional[str]:
        """Calculate file hash."""
        from ..helpers.file_utils import get_file_hash
        return get_file_hash(filepath, algorithm)
    
    def execute_with_timeout(self, func, timeout: int, *args, **kwargs):
        """Execute a function with timeout."""
        import signal
        import threading
        
        class TimeoutError(Exception):
            pass
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Operation timed out")
        
        # Set up timeout
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout)
        
        try:
            result = func(*args, **kwargs)
            signal.alarm(0)  # Cancel the alarm
            return result
        except TimeoutError:
            self.log_manager.print_error(f"Module {self.module_name} timed out after {timeout} seconds")
            return None
        finally:
            signal.signal(signal.SIGALRM, old_handler)
    
    def run_module(self) -> int:
        """Execute the module with proper setup and cleanup."""
        self.start_time = time.time()
        self.status = "running"
        
        try:
            # Pre-run validation
            if not self.pre_run():
                self.log_manager.print_info(f"Module {self.module_name} skipped (pre-run validation failed)")
                self.status = "skipped"
                return 0
            
            # Initialize logging
            self.module_log_init()
            
            # Execute main module logic
            self.exit_code = self.run()
            
            # Post-run cleanup
            self.post_run()
            
            # Finalize logging
            self.module_end_log(self.exit_code)
            
            self.status = "completed" if self.exit_code == 0 else "failed"
            
        except Exception as e:
            self.log_manager.print_error(f"Module {self.module_name} failed with exception: {e}")
            self.exit_code = 1
            self.status = "failed"
            
            # Ensure cleanup happens even on exception
            try:
                self.post_run()
            except:
                pass
        
        finally:
            self.end_time = time.time()
            self.duration = self.end_time - self.start_time
        
        return self.exit_code
    
    def get_module_stats(self) -> Dict[str, Any]:
        """Get module execution statistics."""
        return {
            'name': self.module_name,
            'category': self.category,
            'status': self.status,
            'exit_code': self.exit_code,
            'duration': self.duration,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'temp_files_count': len(self.temp_files)
        }
    
    def __repr__(self):
        return f"{self.__class__.__name__}(name={self.module_name}, category={self.category})"
    
    def __str__(self):
        return f"{self.module_name} ({self.category}) - {self.status}"


class PModule(BaseModule):
    """Base class for P-Modules (Pre-checking/Extraction)."""
    
    MODULE_INFO = {
        'name': 'PModule',
        'description': 'Pre-checking/Extraction module',
        'category': 'P',
        'can_run_parallel': True
    }
    
    def __init__(self, config: ModuleConfig, log_manager: LogManager):
        super().__init__(config, log_manager)
        self.category = "P"
        self.firmware_path = config.firmware_path
        self.extracted_paths: List[str] = []
        self.extraction_success = False


class SModule(BaseModule):
    """Base class for S-Modules (Security Analysis)."""
    
    MODULE_INFO = {
        'name': 'SModule',
        'description': 'Security analysis module',
        'category': 'S',
        'can_run_parallel': True
    }
    
    def __init__(self, config: ModuleConfig, log_manager: LogManager):
        super().__init__(config, log_manager)
        self.category = "S"
        self.firmware_path = config.firmware_path
        self.vulnerabilities: List[Dict[str, Any]] = []
        self.security_issues: List[Dict[str, Any]] = []


class LModule(BaseModule):
    """Base class for L-Modules (Live Emulation)."""
    
    MODULE_INFO = {
        'name': 'LModule',
        'description': 'Live emulation module',
        'category': 'L',
        'can_run_parallel': False  # Emulation modules typically can't run in parallel
    }
    
    def __init__(self, config: ModuleConfig, log_manager: LogManager):
        super().__init__(config, log_manager)
        self.category = "L"
        self.emulation_results: List[Dict[str, Any]] = []


class FModule(BaseModule):
    """Base class for F-Modules (Final Reporting)."""
    
    MODULE_INFO = {
        'name': 'FModule',
        'description': 'Final reporting module',
        'category': 'F',
        'can_run_parallel': True
    }
    
    def __init__(self, config: ModuleConfig, log_manager: LogManager):
        super().__init__(config, log_manager)
        self.category = "F"
        self.report_data: Dict[str, Any] = {}


class QModule(BaseModule):
    """Base class for Q-Modules (AI-powered Analysis)."""
    
    MODULE_INFO = {
        'name': 'QModule',
        'description': 'AI-powered analysis module',
        'category': 'Q',
        'can_run_parallel': True
    }
    
    def __init__(self, config: ModuleConfig, log_manager: LogManager):
        super().__init__(config, log_manager)
        self.category = "Q"
        self.ai_results: List[Dict[str, Any]] = []


class DModule(BaseModule):
    """Base class for D-Modules (Differential Analysis)."""
    
    MODULE_INFO = {
        'name': 'DModule',
        'description': 'Differential analysis module',
        'category': 'D',
        'can_run_parallel': True
    }
    
    def __init__(self, config: ModuleConfig, log_manager: LogManager):
        super().__init__(config, log_manager)
        self.category = "D"
        self.diff_results: List[Dict[str, Any]] = []

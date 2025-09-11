"""
Helper functions and utilities for Pymba.

This module contains utility functions ported from EMBA's helper scripts
for file operations, system utilities, and analysis helpers.
"""

from .file_utils import *
from .system_utils import *
# Optional helper modules (may not be implemented yet)
try:
    from .extraction_utils import *  # type: ignore
except Exception:
    pass

try:
    from .analysis_utils import *  # type: ignore
except Exception:
    pass

__all__ = [
    # File utilities
    'abs_path', 'check_path_valid', 'create_log_dir',
    'get_file_size', 'get_file_hash', 'is_binary_file',
    
    # System utilities
    'run_command', 'check_dependencies', 'get_system_info',
    'setup_environment', 'cleanup_environment',
    
    # Extraction utilities (if available)
    # 'extract_archive', 'detect_archive_type', 'mount_filesystem',
    # 'unmount_filesystem', 'find_root_directory',
    
    # Analysis utilities (if available)
    # 'detect_os_type', 'detect_architecture', 'find_binaries',
    # 'analyze_binary', 'search_strings', 'extract_strings'
]

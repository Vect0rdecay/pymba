#!/usr/bin/env python3
"""
Base class for P-Modules (Pre-checking/Extraction modules).

This module provides the base class and common functionality
for all P-modules in Pymba.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from base_module import BaseModule
from typing import Dict, List, Optional


class BasePModule(BaseModule):
    """Base class for all P-Modules (Pre-checking/Extraction)."""
    
    def __init__(self, config, logger):
        super().__init__(config, logger)
        self.category = "P"
        
        # Common P-module attributes
        self.firmware_path = config.firmware_path
        self.output_dir = config.output_dir
        self.log_dir = config.log_dir
        
        # Extraction results
        self.extracted_paths: List[str] = []
        self.extraction_success = False
        self.root_directories: List[str] = []
    
    def run(self) -> int:
        """Default implementation - should be overridden by subclasses."""
        self.module_log_init()
        self.print_output(f"Running {self.module_name}")
        self.pre_module_reporter()
        
        # Default implementation - just report success
        self.print_success(f"{self.module_name} completed")
        return 0
    
    def detect_root_directory(self, firmware_path: str) -> Optional[str]:
        """
        Detect root directory in extracted firmware.
        
        This is a simplified implementation of the root directory
        detection logic from EMBA.
        """
        import os
        from pathlib import Path
        
        # Common root directory patterns
        root_patterns = [
            'rootfs', 'root', 'filesystem', 'fs',
            'squashfs-root', 'extracted', 'firmware'
        ]
        
        firmware_dir = Path(firmware_path)
        if not firmware_dir.exists():
            return None
        
        # Look for directories matching root patterns
        for pattern in root_patterns:
            for item in firmware_dir.iterdir():
                if item.is_dir() and pattern in item.name.lower():
                    return str(item)
        
        # Look for directories with typical Linux structure
        for item in firmware_dir.iterdir():
            if item.is_dir():
                # Check for common Linux directories
                linux_dirs = {'bin', 'sbin', 'etc', 'usr', 'lib', 'var', 'tmp'}
                if any((item / d).exists() for d in linux_dirs):
                    return str(item)
        
        # If no specific pattern found, return the first directory
        for item in firmware_dir.iterdir():
            if item.is_dir():
                return str(item)
        
        return None
    
    def find_extracted_firmware(self) -> List[str]:
        """Find extracted firmware directories."""
        import os
        from pathlib import Path
        
        extracted_paths = []
        output_path = Path(self.output_dir)
        
        if not output_path.exists():
            return extracted_paths
        
        # Look for common extraction directories
        extraction_patterns = [
            'squashfs-root', 'extracted', 'firmware', 'rootfs',
            'filesystem', 'fs', 'root'
        ]
        
        for item in output_path.iterdir():
            if item.is_dir():
                # Check if directory name matches extraction pattern
                if any(pattern in item.name.lower() for pattern in extraction_patterns):
                    extracted_paths.append(str(item))
                
                # Check if directory contains Linux-like structure
                elif self._is_linux_filesystem(str(item)):
                    extracted_paths.append(str(item))
        
        return extracted_paths
    
    def _is_linux_filesystem(self, path: str) -> bool:
        """Check if path contains a Linux-like filesystem structure."""
        import os
        
        # Common Linux directories
        linux_dirs = {'bin', 'sbin', 'etc', 'usr', 'lib', 'var', 'tmp', 'proc', 'sys'}
        
        try:
            for dirname in linux_dirs:
                if os.path.exists(os.path.join(path, dirname)):
                    return True
        except (OSError, PermissionError):
            pass
        
        return False
    
    def check_firmware_type(self) -> Dict[str, bool]:
        """Check firmware type and characteristics."""
        import os
        from pathlib import Path
        
        firmware_path = Path(self.firmware_path)
        results = {
            'is_directory': firmware_path.is_dir(),
            'is_file': firmware_path.is_file(),
            'is_archive': False,
            'is_linux': False,
            'is_rtos': False,
            'is_windows': False,
            'is_uefi': False
        }
        
        if results['is_file']:
            # Check file extension for archive types
            archive_extensions = {
                '.bin', '.img', '.iso', '.tar', '.tar.gz', '.tgz',
                '.tar.bz2', '.tbz2', '.zip', '.7z', '.rar', '.gz',
                '.bz2', '.xz', '.lzma', '.cpio', '.squashfs'
            }
            
            ext = firmware_path.suffix.lower()
            if ext in archive_extensions:
                results['is_archive'] = True
            
            # Try to detect firmware type by content
            results.update(self._detect_firmware_type_by_content())
        
        elif results['is_directory']:
            # Check if directory contains Linux filesystem
            results['is_linux'] = self._is_linux_filesystem(self.firmware_path)
        
        return results
    
    def _detect_firmware_type_by_content(self) -> Dict[str, bool]:
        """Detect firmware type by analyzing file content."""
        import os
        
        results = {
            'is_linux': False,
            'is_rtos': False,
            'is_windows': False,
            'is_uefi': False
        }
        
        try:
            with open(self.firmware_path, 'rb') as f:
                # Read first 1MB for analysis
                header = f.read(1024 * 1024)
                
                # Check for Linux kernel signatures
                linux_signatures = [b'Linux version', b'Booting Linux', b'vmlinux']
                if any(sig in header for sig in linux_signatures):
                    results['is_linux'] = True
                
                # Check for RTOS signatures
                rtos_signatures = [b'VxWorks', b'eCos', b'FreeRTOS', b'ThreadX']
                if any(sig in header for sig in rtos_signatures):
                    results['is_rtos'] = True
                
                # Check for Windows signatures
                windows_signatures = [b'MZ', b'PE\x00\x00', b'This program cannot be run in DOS mode']
                if any(sig in header for sig in windows_signatures):
                    results['is_windows'] = True
                
                # Check for UEFI signatures
                uefi_signatures = [b'UEFI', b'EFI System Partition', b'_EFI_']
                if any(sig in header for sig in uefi_signatures):
                    results['is_uefi'] = True
        
        except (OSError, PermissionError):
            pass
        
        return results
    
    def get_firmware_size(self) -> int:
        """Get firmware size in bytes."""
        import os
        
        try:
            if os.path.isfile(self.firmware_path):
                return os.path.getsize(self.firmware_path)
            elif os.path.isdir(self.firmware_path):
                total_size = 0
                for dirpath, dirnames, filenames in os.walk(self.firmware_path):
                    for filename in filenames:
                        filepath = os.path.join(dirpath, filename)
                        try:
                            total_size += os.path.getsize(filepath)
                        except (OSError, PermissionError):
                            continue
                return total_size
        except (OSError, PermissionError):
            pass
        
        return 0
    
    def format_size(self, size_bytes: int) -> str:
        """Format size in human readable format."""
        if size_bytes == 0:
            return "0 B"
        
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        unit_index = 0
        size = float(size_bytes)
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        
        return f"{size:.1f} {units[unit_index]}"

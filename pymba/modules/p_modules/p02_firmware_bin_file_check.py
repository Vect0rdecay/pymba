#!/usr/bin/env python3
"""
P02 - Firmware Binary File Check

This module performs initial analysis of the firmware file to determine
its type, size, and basic characteristics before extraction.
"""

import os
import hashlib
import sys
sys.path.append(os.path.dirname(__file__))
from base_p_module import BasePModule


class P02_firmware_bin_file_check(BasePModule):
    """P02 - Firmware binary file check module."""
    
    def __init__(self, config, logger):
        super().__init__(config, logger)
        self.module_name = "P02_firmware_bin_file_check"
    
    def run(self) -> int:
        """Main execution method."""
        self.module_log_init()
        self.print_output("Firmware binary file check")
        self.pre_module_reporter()
        
        try:
            # Check if firmware path exists
            if not os.path.exists(self.firmware_path):
                self.print_error(f"Firmware path does not exist: {self.firmware_path}")
                return 1
            
            # Get basic file information
            self._analyze_firmware_file()
            
            # Detect firmware type
            firmware_type = self.check_firmware_type()
            self._report_firmware_type(firmware_type)
            
            # Calculate file hash
            self._calculate_file_hash()
            
            self.print_success("Firmware file analysis completed")
            return 0
            
        except Exception as e:
            self.print_error(f"Error in firmware file check: {e}")
            return 1
        finally:
            self.module_end_log()
    
    def _analyze_firmware_file(self):
        """Analyze basic firmware file properties."""
        self.print_output("Analyzing firmware file properties...")
        
        # Get file size
        size_bytes = self.get_firmware_size()
        size_formatted = self.format_size(size_bytes)
        
        self.print_output(f"Firmware size: {size_formatted} ({size_bytes} bytes)")
        
        # Get file permissions
        try:
            stat_info = os.stat(self.firmware_path)
            permissions = oct(stat_info.st_mode)[-3:]
            self.print_output(f"File permissions: {permissions}")
        except OSError:
            self.print_output("Could not determine file permissions")
        
        # Check if file is readable
        if os.access(self.firmware_path, os.R_OK):
            self.print_success("Firmware file is readable")
        else:
            self.print_error("Firmware file is not readable")
        
        # Check if it's a regular file or directory
        if os.path.isfile(self.firmware_path):
            self.print_output("Firmware type: Single file")
        elif os.path.isdir(self.firmware_path):
            self.print_output("Firmware type: Directory")
        else:
            self.print_output("Firmware type: Unknown")
    
    def _report_firmware_type(self, firmware_type: dict):
        """Report detected firmware type."""
        self.print_output("Detected firmware characteristics:")
        
        for key, value in firmware_type.items():
            if value:
                status = "✓" if value else "✗"
                self.print_output(f"  {status} {key.replace('_', ' ').title()}")
        
        # Determine primary type
        if firmware_type.get('is_linux', False):
            self.print_output("Primary type: Linux-based firmware")
        elif firmware_type.get('is_rtos', False):
            self.print_output("Primary type: RTOS-based firmware")
        elif firmware_type.get('is_windows', False):
            self.print_output("Primary type: Windows-based firmware")
        elif firmware_type.get('is_uefi', False):
            self.print_output("Primary type: UEFI firmware")
        else:
            self.print_output("Primary type: Unknown")
    
    def _calculate_file_hash(self):
        """Calculate and report file hash."""
        if not os.path.isfile(self.firmware_path):
            self.print_output("Skipping hash calculation (not a file)")
            return
        
        self.print_output("Calculating file hash...")
        
        try:
            # Calculate SHA256 hash
            sha256_hash = self._calculate_hash('sha256')
            if sha256_hash:
                self.print_output(f"SHA256: {sha256_hash}")
            
            # Calculate MD5 hash
            md5_hash = self._calculate_hash('md5')
            if md5_hash:
                self.print_output(f"MD5: {md5_hash}")
            
            self.print_success("Hash calculation completed")
            
        except Exception as e:
            self.print_error(f"Error calculating hash: {e}")
    
    def _calculate_hash(self, algorithm: str) -> str:
        """Calculate hash using specified algorithm."""
        try:
            hash_obj = hashlib.new(algorithm)
            
            with open(self.firmware_path, 'rb') as f:
                # Read in chunks to handle large files
                while chunk := f.read(8192):
                    hash_obj.update(chunk)
            
            return hash_obj.hexdigest()
            
        except Exception as e:
            self.print_error(f"Error calculating {algorithm} hash: {e}")
            return ""

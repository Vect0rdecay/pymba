#!/usr/bin/env python3
"""
P01 - Test Module

A simple test module to demonstrate the Pymba framework functionality.
"""

import os
import sys
sys.path.append(os.path.dirname(__file__))
from base_p_module import BasePModule


class P01_test_module(BasePModule):
    """P01 - Test module for demonstration."""
    
    def __init__(self, config, logger):
        super().__init__(config, logger)
        self.module_name = "P01_test_module"
    
    def run(self) -> int:
        """Main execution method."""
        self.module_log_init()
        self.print_output("Test module for Pymba framework demonstration")
        self.pre_module_reporter()
        
        try:
            # Basic firmware analysis
            self.print_output("Analyzing firmware...")
            
            # Check firmware path
            if os.path.exists(self.firmware_path):
                self.print_success(f"Firmware path exists: {self.firmware_path}")
                
                # Get basic information
                if os.path.isdir(self.firmware_path):
                    self.print_output("Firmware type: Directory")
                    self._analyze_directory()
                elif os.path.isfile(self.firmware_path):
                    self.print_output("Firmware type: File")
                    self._analyze_file()
                else:
                    self.print_output("Firmware type: Unknown")
                
                # Check firmware characteristics
                firmware_type = self.check_firmware_type()
                self._report_firmware_type(firmware_type)
                
            else:
                self.print_error(f"Firmware path does not exist: {self.firmware_path}")
                return 1
            
            self.print_success("Test module completed successfully")
            return 0
            
        except Exception as e:
            self.print_error(f"Error in test module: {e}")
            return 1
        finally:
            self.module_end_log()
    
    def _analyze_directory(self):
        """Analyze firmware directory."""
        try:
            # Count files and directories
            file_count = 0
            dir_count = 0
            
            for root, dirs, files in os.walk(self.firmware_path):
                dir_count += len(dirs)
                file_count += len(files)
                
                # Stop after first level for demo
                break
            
            self.print_output(f"Found {dir_count} directories and {file_count} files in root")
            
            # List top-level contents
            try:
                items = os.listdir(self.firmware_path)
                self.print_output("Top-level contents:")
                for item in items[:10]:  # Show first 10 items
                    item_path = os.path.join(self.firmware_path, item)
                    if os.path.isdir(item_path):
                        self.print_output(f"  [DIR]  {item}")
                    else:
                        size = os.path.getsize(item_path)
                        self.print_output(f"  [FILE] {item} ({self.format_size(size)})")
                
                if len(items) > 10:
                    self.print_output(f"  ... and {len(items) - 10} more items")
                    
            except (OSError, PermissionError):
                self.print_output("Could not list directory contents")
                
        except Exception as e:
            self.print_error(f"Error analyzing directory: {e}")
    
    def _analyze_file(self):
        """Analyze firmware file."""
        try:
            # Get file size
            size = os.path.getsize(self.firmware_path)
            self.print_output(f"File size: {self.format_size(size)}")
            
            # Get file permissions
            stat_info = os.stat(self.firmware_path)
            permissions = oct(stat_info.st_mode)[-3:]
            self.print_output(f"File permissions: {permissions}")
            
        except Exception as e:
            self.print_error(f"Error analyzing file: {e}")
    
    def _report_firmware_type(self, firmware_type: dict):
        """Report detected firmware type."""
        self.print_output("Detected firmware characteristics:")
        
        for key, value in firmware_type.items():
            if value:
                self.print_output(f"  ✓ {key.replace('_', ' ').title()}")
        
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


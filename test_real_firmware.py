#!/usr/bin/env python3
"""
Test script for Pymba framework with real firmware.

This script tests the Pymba framework with the real Alpine Linux firmware
provided in /home/admin/firmware/.
"""

import os
import sys
import tempfile
from pathlib import Path

# Add pymba to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'pymba'))

from pymba.core.config import PymbaConfig
from pymba.core.engine import PymbaEngine
from pymba.core.logger import PymbaLogger


def main():
    """Main test function."""
    print("Pymba Real Firmware Test")
    print("========================")
    
    # Use real firmware
    firmware_path = "/home/admin/firmware/alpine-minirootfs-3.22.0-x86_64.tar.gz"
    extracted_path = "/home/admin/firmware"  # Already extracted content
    
    print(f"Firmware file: {firmware_path}")
    print(f"Extracted content: {extracted_path}")
    
    # Check if firmware exists
    if not os.path.exists(firmware_path):
        print(f"Error: Firmware file not found: {firmware_path}")
        return 1
    
    if not os.path.exists(extracted_path):
        print(f"Error: Extracted content not found: {extracted_path}")
        return 1
    
    # Create temporary log directory
    log_dir = tempfile.mkdtemp(prefix="pymba_real_test_")
    print(f"Log directory: {log_dir}")
    
    try:
        # Create configuration
        config = PymbaConfig()
        config.firmware_path = firmware_path  # Use the compressed file
        config.log_dir = log_dir
        config.output_dir = extracted_path    # Use the extracted content
        config.threaded = True
        config.html_report = False  # Disable for test
        config.rtos = False  # Test with Linux-like firmware
        
        # Set firmware metadata
        config.fw_vendor = "Alpine Linux"
        config.fw_version = "3.22.0"
        config.fw_device = "x86_64"
        config.fw_notes = "Alpine Linux minirootfs for testing"
        
        # Enable some modules for testing
        config.module_blacklist = [
            # Enable P01 test module
            # Enable P02 firmware check (should work with extracted content)
            # Enable P50 binwalk extractor for testing
            "P55_unblob_extractor",         # Requires unblob
            "P60_deep_extractor",           # Requires additional tools
            "P99_prepare_analyzer",         # Not fully implemented
            "base_p_module"                 # Base class, not a runnable module
        ]
        
        print("\nConfiguration:")
        print(f"  Firmware: {config.firmware_path}")
        print(f"  Output Dir: {config.output_dir}")
        print(f"  Log Dir: {config.log_dir}")
        print(f"  Threading: {config.threaded}")
        print(f"  RTOS Mode: {config.rtos}")
        
        # Validate configuration
        issues = config.validate()
        if issues:
            print("Configuration issues:")
            for issue in issues:
                print(f"  - {issue}")
            return 1
        
        print("\nStarting Pymba analysis...")
        
        # Create and run engine
        engine = PymbaEngine(config)
        engine.run_analysis()
        
        print("\nAnalysis completed successfully!")
        print(f"Results available in: {log_dir}")
        
        # List generated files
        log_path = Path(log_dir)
        if log_path.exists():
            print("\nGenerated files:")
            for item in log_path.iterdir():
                if item.is_file():
                    size = item.stat().st_size
                    print(f"  {item.name} ({size} bytes)")
        
        return 0
        
    except Exception as e:
        print(f"\nError during analysis: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())


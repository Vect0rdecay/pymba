#!/usr/bin/env python3
"""
Test script for Pymba framework.

This script demonstrates the basic functionality of Pymba
by running a simple analysis with the P-modules.
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


def create_test_firmware():
    """Create a simple test firmware structure."""
    # Create a persistent temporary directory
    temp_dir = tempfile.mkdtemp(prefix="pymba_test_firmware_")
    
    # Create a simple firmware directory structure
    firmware_dir = Path(temp_dir) / "test_firmware"
    firmware_dir.mkdir()
    
    # Create basic Linux-like structure
    (firmware_dir / "bin").mkdir()
    (firmware_dir / "sbin").mkdir()
    (firmware_dir / "etc").mkdir()
    (firmware_dir / "usr").mkdir()
    (firmware_dir / "lib").mkdir()
    
    # Create some test files
    (firmware_dir / "bin" / "sh").write_text("#!/bin/sh\necho 'test shell'")
    (firmware_dir / "bin" / "sh").chmod(0o755)
    
    (firmware_dir / "etc" / "passwd").write_text("root:x:0:0:root:/root:/bin/sh")
    (firmware_dir / "etc" / "hostname").write_text("test-device")
    
    # Create a simple binary file
    test_binary = firmware_dir / "test.bin"
    test_binary.write_bytes(b"ELF\x7fELF\x02\x01\x01\x00" + b"\x00" * 100)
    
    return str(firmware_dir), temp_dir


def main():
    """Main test function."""
    print("Pymba Test Script")
    print("================")
    
    # Create test firmware
    print("Creating test firmware...")
    firmware_path, temp_dir = create_test_firmware()
    print(f"Test firmware created at: {firmware_path}")
    
    # Create temporary log directory
    log_dir = tempfile.mkdtemp(prefix="pymba_test_")
    print(f"Log directory: {log_dir}")
    
    try:
        # Create configuration
        config = PymbaConfig()
        config.firmware_path = firmware_path
        config.log_dir = log_dir
        config.output_dir = firmware_path
        config.threaded = True
        config.html_report = False  # Disable for test
        config.rtos = False  # Test with Linux-like firmware
        
        # Set firmware metadata
        config.fw_vendor = "Test Vendor"
        config.fw_version = "1.0.0"
        config.fw_device = "Test Device"
        config.fw_notes = "Test firmware for Pymba"
        
        # Disable modules that require external tools or are not fully implemented
        config.module_blacklist = [
            "P02_firmware_bin_file_check",  # Not fully implemented
            "P50_binwalk_extractor",        # Requires binwalk
            "P55_unblob_extractor",         # Requires unblob
            "P60_deep_extractor",           # Requires additional tools
            "P99_prepare_analyzer",         # Not fully implemented
            "base_p_module"                 # Base class, not a runnable module
        ]
        
        print("\nConfiguration:")
        print(f"  Firmware: {config.firmware_path}")
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
    
    finally:
        # Cleanup
        print(f"\nCleaning up test firmware...")
        import shutil
        try:
            shutil.rmtree(temp_dir)
        except:
            pass


if __name__ == "__main__":
    sys.exit(main())

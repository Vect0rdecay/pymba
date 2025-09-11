#!/usr/bin/env python3
"""
P55 - Unblob Extractor

This module extracts firmware using unblob, which is an alternative
extraction method to binwalk. Unblob is preferred for system emulation
as it handles symbolic links better.
"""

import os
import subprocess
import sys
from pathlib import Path
sys.path.append(os.path.dirname(__file__))
from base_p_module import BasePModule


class P55_unblob_extractor(BasePModule):
    """P55 - Unblob extractor module."""
    
    def __init__(self, config, logger):
        super().__init__(config, logger)
        self.module_name = "P55_unblob_extractor"
        self.pre_thread_ena = 0  # Disable threading for extraction
        self.extraction_dir = os.path.join(config.log_dir, "firmware", "unblob_extracted")
    
    def run(self) -> int:
        """Main execution method."""
        self.module_log_init()
        self.print_output("Unblob firmware extractor")
        self.pre_module_reporter()
        try:
            if not self._check_unblob_available():
                self.print_output("Unblob not available, skipping extraction")
                return 0
            
            if not self._should_extract():
                self.print_output("Extraction not needed, skipping")
                return 0
            
            self._create_extraction_dir()
            self._run_unblob_extraction()
            self._post_process_extraction()
            self.print_success("Unblob extraction completed")
            return 0
        except Exception as e:
            self.print_error(f"Error in unblob extraction: {e}")
            return 1
        finally:
            self.module_end_log()

    def _check_unblob_available(self) -> bool:
        """Check if unblob is available on the system."""
        try:
            result = subprocess.run(['unblob', '--version'],
                                    capture_output=True,
                                    text=True,
                                    timeout=10)
            if result.returncode == 0:
                version = result.stdout.strip() or result.stderr.strip()
                self.print_output(f"Unblob available: {version}")
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        self.print_output("Unblob not found on system")
        return False

    def _should_extract(self) -> bool:
        """Determine if extraction is needed."""
        if os.path.isdir(self.firmware_path):
            self.print_output("Firmware is already a directory, skipping extraction")
            return False
        if self.config.kernel:
            self.print_output("Kernel configuration mode, skipping extraction")
            return False
        if os.path.exists(self.extraction_dir) and os.listdir(self.extraction_dir):
            self.print_output("Firmware already extracted with unblob")
            return False
        return os.path.isfile(self.firmware_path)

    def _create_extraction_dir(self):
        """Create extraction directory."""
        try:
            Path(self.extraction_dir).mkdir(parents=True, exist_ok=True)
            self.print_output(f"Created extraction directory: {self.extraction_dir}")
        except OSError as e:
            raise Exception(f"Failed to create extraction directory: {e}")

    def _run_unblob_extraction(self):
        """Run unblob extraction."""
        self.print_output("Running unblob extraction...")
        cmd = [
            'unblob',
            '--output', self.extraction_dir,
            self.firmware_path
        ]
        try:
            self.print_output(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,
                cwd=self.extraction_dir
            )
            if result.returncode == 0:
                self.print_success("Unblob extraction completed successfully")
                if result.stdout:
                    self.print_output(f"Unblob output: {result.stdout}")
            else:
                self.print_error(f"Unblob extraction failed with return code {result.returncode}")
                if result.stderr:
                    self.print_error(f"Unblob error: {result.stderr}")
                if result.stdout:
                    self.print_output(f"Unblob output: {result.stdout}")
        except subprocess.TimeoutExpired:
            self.print_error("Unblob extraction timed out")
            raise
        except Exception as e:
            self.print_error(f"Error running unblob: {e}")
            raise

    def _post_process_extraction(self):
        """Post-process extraction results."""
        self.print_output("Post-processing extraction results...")
        extracted_items = []
        try:
            for item in Path(self.extraction_dir).iterdir():
                extracted_items.append(str(item))
        except (OSError, PermissionError):
            self.print_error("Could not access extraction directory")
            return
        if not extracted_items:
            self.print_error("No files extracted")
            return
        self.print_output(f"Found {len(extracted_items)} extracted items")
        root_dir = self.detect_root_directory(self.extraction_dir)
        if root_dir:
            self.print_success(f"Found root directory: {root_dir}")
            self.root_directories.append(root_dir)
            self.extraction_success = True
        else:
            self.print_output("No root directory found in extraction")
        for item in extracted_items:
            item_path = Path(item)
            if item_path.is_file():
                size = item_path.stat().st_size
                self.print_output(f"  File: {item_path.name} ({self.format_size(size)})")
            elif item_path.is_dir():
                self.print_output(f"  Directory: {item_path.name}")
        self.extracted_paths.extend(extracted_items)

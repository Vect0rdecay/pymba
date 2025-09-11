#!/usr/bin/env python3
"""
P50 - Binwalk Extractor

This module extracts firmware using binwalk, which is one of the primary
extraction methods in EMBA. This is a fallback module for cases where
other extraction methods fail.
"""

import os
import subprocess
import sys
from pathlib import Path
sys.path.append(os.path.dirname(__file__))
from base_p_module import BasePModule


class P50_binwalk_extractor(BasePModule):
    """P50 - Binwalk extractor module."""
    
    def __init__(self, config, logger):
        super().__init__(config, logger)
        self.module_name = "P50_binwalk_extractor"
        
        # Module settings
        self.pre_thread_ena = 0  # Disable threading for extraction
        self.extraction_dir = os.path.join(config.log_dir, "firmware", "binwalk_extracted")
        self.use_docker = False  # Will be set by _check_binwalk_available
    
    def run(self) -> int:
        """Main execution method."""
        self.module_log_init()
        self.print_output("Binwalk firmware extractor")
        self.pre_module_reporter()
        
        try:
            # Check if binwalk is available
            if not self._check_binwalk_available():
                self.print_output("Binwalk not available, skipping extraction")
                return 0
            
            # Check if extraction is needed
            if not self._should_extract():
                self.print_output("Extraction not needed, skipping")
                return 0
            
            # Create extraction directory
            self._create_extraction_dir()
            
            # Run binwalk extraction
            self._run_binwalk_extraction()
            
            # Post-process extraction results
            self._post_process_extraction()
            
            self.print_success("Binwalk extraction completed")
            return 0
            
        except Exception as e:
            self.print_error(f"Error in binwalk extraction: {e}")
            return 1
        finally:
            self.module_end_log()
    
    def _check_binwalk_available(self) -> bool:
        """Check if binwalk is available on the system or via Docker."""
        import shutil
        
        # First check if binwalk is in PATH and working
        binwalk_path = shutil.which('binwalk')
        if binwalk_path:
            try:
                result = subprocess.run(['binwalk', '--version'], 
                                      capture_output=True, 
                                      text=True, 
                                      timeout=10)
                if result.returncode == 0:
                    version = result.stdout.strip() or result.stderr.strip()
                    self.print_output(f"Binwalk available: {version}")
                    return True
                else:
                    self.print_output(f"Binwalk found at {binwalk_path} but not working (Python 3.13 issue)")
            except (subprocess.TimeoutExpired, FileNotFoundError):
                self.print_output(f"Binwalk found at {binwalk_path} but version check failed")
        
        # Fallback: Check if Docker is available for binwalk
        if shutil.which('docker'):
            try:
                result = subprocess.run(['docker', 'run', '--rm', 'reversemode/binwalk', '--version'], 
                                      capture_output=True, 
                                      text=True, 
                                      timeout=15)
                if result.returncode == 0:
                    self.print_output("Binwalk available via Docker (reversemode/binwalk)")
                    self.use_docker = True
                    return True
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
        
        self.print_output("Binwalk not available (neither local nor Docker)")
        return False
    
    def _should_extract(self) -> bool:
        """Determine if extraction is needed."""
        # Don't extract if we already have a directory
        if os.path.isdir(self.firmware_path):
            self.print_output("Firmware is already a directory, skipping extraction")
            return False
        
        # Don't extract if it's a kernel config
        if self.config.kernel:
            self.print_output("Kernel configuration mode, skipping extraction")
            return False
        
        # Don't extract if already extracted
        if os.path.exists(self.extraction_dir) and os.listdir(self.extraction_dir):
            self.print_output("Firmware already extracted with binwalk")
            return False
        
        # Check if it's an archive file
        if not self._is_archive_file():
            self.print_output("File does not appear to be an archive, skipping extraction")
            return False
        
        return True
    
    def _is_archive_file(self) -> bool:
        """Check if file appears to be an archive."""
        if not os.path.isfile(self.firmware_path):
            return False
        
        # Check file extension
        archive_extensions = {
            '.bin', '.img', '.iso', '.tar', '.tar.gz', '.tgz',
            '.tar.bz2', '.tbz2', '.zip', '.7z', '.rar', '.gz',
            '.bz2', '.xz', '.lzma', '.cpio'
        }
        
        ext = Path(self.firmware_path).suffix.lower()
        if ext in archive_extensions:
            return True
        
        # Check file magic/header
        try:
            with open(self.firmware_path, 'rb') as f:
                header = f.read(512)
                
                # Common archive magic numbers
                magic_signatures = [
                    b'PK\x03\x04',  # ZIP
                    b'PK\x05\x06',  # ZIP (empty)
                    b'PK\x07\x08',  # ZIP (spanned)
                    b'\x1f\x8b',    # GZIP
                    b'BZ',          # BZIP2
                    b'\xfd7zXZ\x00', # XZ
                    b'7z\xbc\xaf\x27\x1c', # 7Z
                    b'ustar',       # TAR
                ]
                
                for magic in magic_signatures:
                    if header.startswith(magic):
                        return True
        
        except (OSError, PermissionError):
            pass
        
        return False
    
    def _create_extraction_dir(self):
        """Create extraction directory."""
        try:
            Path(self.extraction_dir).mkdir(parents=True, exist_ok=True)
            self.print_output(f"Created extraction directory: {self.extraction_dir}")
        except OSError as e:
            raise Exception(f"Failed to create extraction directory: {e}")
    
    def _run_binwalk_extraction(self):
        """Run binwalk extraction."""
        self.print_output("Running binwalk extraction...")
        
        if self.use_docker:
            # Docker-based extraction
            cmd = [
                'docker', 'run', '--rm',
                '-v', f'{self.firmware_path}:/input/firmware.bin:ro',
                '-v', f'{self.extraction_dir}:/output',
                'reversemode/binwalk',
                '--extract',
                '--directory', '/output',
                '--quiet',
                '/input/firmware.bin'
            ]
        else:
            # Local binwalk extraction
            cmd = [
                'binwalk',
                '--extract',           # Extract files
                '--directory', self.extraction_dir,  # Output directory
                '--run-as=root',       # Run as root (may be needed for some extractions)
                '--quiet',             # Reduce output
                self.firmware_path     # Input file
            ]
        
        try:
            self.print_output(f"Running command: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                cwd=self.extraction_dir
            )
            
            if result.returncode == 0:
                self.print_success("Binwalk extraction completed successfully")
                if result.stdout:
                    self.print_output(f"Binwalk output: {result.stdout}")
            else:
                self.print_error(f"Binwalk extraction failed with return code {result.returncode}")
                if result.stderr:
                    self.print_error(f"Binwalk error: {result.stderr}")
                if result.stdout:
                    self.print_output(f"Binwalk output: {result.stdout}")
        
        except subprocess.TimeoutExpired:
            self.print_error("Binwalk extraction timed out")
            raise
        except Exception as e:
            self.print_error(f"Error running binwalk: {e}")
            raise
    
    def _post_process_extraction(self):
        """Post-process extraction results."""
        self.print_output("Post-processing extraction results...")
        
        # Find extracted files and directories
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
        
        # Look for root filesystem
        root_dir = self.detect_root_directory(self.extraction_dir)
        if root_dir:
            self.print_success(f"Found root directory: {root_dir}")
            self.root_directories.append(root_dir)
            self.extraction_success = True
        else:
            self.print_output("No root directory found in extraction")
        
        # List extracted items
        for item in extracted_items:
            item_path = Path(item)
            if item_path.is_file():
                size = item_path.stat().st_size
                self.print_output(f"  File: {item_path.name} ({self.format_size(size)})")
            elif item_path.is_dir():
                self.print_output(f"  Directory: {item_path.name}")
        
        # Update extracted paths
        self.extracted_paths.extend(extracted_items)

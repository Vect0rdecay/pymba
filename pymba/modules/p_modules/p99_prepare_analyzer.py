#!/usr/bin/env python3
"""
P99 - Prepare Analyzer

This module is the final P-module that prepares the extracted firmware
for the main security analysis phase. It sets up paths, validates
extraction results, and prepares the analysis environment.
"""

import os
import sys
from pathlib import Path
sys.path.append(os.path.dirname(__file__))
from base_p_module import BasePModule


class P99_prepare_analyzer(BasePModule):
    """P99 - Prepare analyzer module."""
    
    def __init__(self, config, logger):
        super().__init__(config, logger)
        self.module_name = "P99_prepare_analyzer"
        self.pre_thread_ena = 1  # High priority
    
    def run(self) -> int:
        """Main execution method."""
        self.module_log_init()
        self.print_output("Prepare analyzer")
        self.pre_module_reporter()
        
        try:
            # Determine firmware extraction status
            self._analyze_extraction_results()
            
            # Setup analysis paths
            self._setup_analysis_paths()
            
            # Validate firmware structure
            self._validate_firmware_structure()
            
            # Prepare for security analysis
            self._prepare_security_analysis()
            
            self.print_success("Analyzer preparation completed")
            return 0
            
        except Exception as e:
            self.print_error(f"Error preparing analyzer: {e}")
            return 1
        finally:
            self.module_end_log()
    
    def _analyze_extraction_results(self):
        """Analyze results from previous extraction modules."""
        self.print_output("Analyzing extraction results...")
        
        # Check for extracted firmware directories
        extracted_paths = self.find_extracted_firmware()
        
        if not extracted_paths:
            if os.path.isdir(self.firmware_path):
                self.print_output("Using firmware directory directly")
                extracted_paths = [self.firmware_path]
            else:
                self.print_error("No extracted firmware found")
                return
        
        self.print_output(f"Found {len(extracted_paths)} extracted firmware paths:")
        for path in extracted_paths:
            self.print_output(f"  {path}")
        
        self.extracted_paths = extracted_paths
    
    def _setup_analysis_paths(self):
        """Setup paths for analysis."""
        self.print_output("Setting up analysis paths...")
        
        # Create analysis subdirectories
        analysis_dirs = [
            'binaries',
            'configs', 
            'scripts',
            'logs',
            'reports'
        ]
        
        for dir_name in analysis_dirs:
            dir_path = os.path.join(self.log_dir, dir_name)
            Path(dir_path).mkdir(exist_ok=True)
            self.print_output(f"Created analysis directory: {dir_name}")
    
    def _validate_firmware_structure(self):
        """Validate firmware filesystem structure."""
        self.print_output("Validating firmware structure...")
        
        valid_firmware_found = False
        
        for firmware_path in self.extracted_paths:
            if self._is_valid_firmware_structure(firmware_path):
                valid_firmware_found = True
                self.print_success(f"Valid firmware structure found: {firmware_path}")
                
                # Detect root directory
                root_dir = self.detect_root_directory(firmware_path)
                if root_dir:
                    self.root_directories.append(root_dir)
                    self.print_output(f"Root directory: {root_dir}")
            else:
                self.print_output(f"Invalid firmware structure: {firmware_path}")
        
        if not valid_firmware_found:
            self.print_error("No valid firmware structure found")
            return
        
        self.extraction_success = True
    
    def _is_valid_firmware_structure(self, path: str) -> bool:
        """Check if path contains valid firmware structure."""
        # Check for Linux-like structure
        if self._is_linux_filesystem(path):
            return True
        
        # Check for common firmware indicators
        firmware_indicators = [
            'bin', 'sbin', 'etc', 'usr', 'lib', 'var',
            'boot', 'dev', 'proc', 'sys', 'tmp', 'opt'
        ]
        
        found_indicators = 0
        for indicator in firmware_indicators:
            if os.path.exists(os.path.join(path, indicator)):
                found_indicators += 1
        
        # Consider valid if at least 3 common directories found
        return found_indicators >= 3
    
    def _prepare_security_analysis(self):
        """Prepare for security analysis phase."""
        self.print_output("Preparing for security analysis...")
        
        # Count binaries for analysis
        binary_count = self._count_binaries()
        self.print_output(f"Found {binary_count} binaries for analysis")
        
        # Check for configuration files
        config_count = self._count_config_files()
        self.print_output(f"Found {config_count} configuration files")
        
        # Check for scripts
        script_count = self._count_scripts()
        self.print_output(f"Found {script_count} scripts")
        
        # Estimate analysis time
        estimated_time = self._estimate_analysis_time(binary_count, config_count, script_count)
        self.print_output(f"Estimated analysis time: {estimated_time}")
    
    def _count_binaries(self) -> int:
        """Count executable binaries in firmware."""
        binary_count = 0
        binary_paths = ['bin', 'sbin', 'usr/bin', 'usr/sbin', 'usr/local/bin']
        
        for firmware_path in self.extracted_paths:
            for binary_path in binary_paths:
                full_path = os.path.join(firmware_path, binary_path)
                if os.path.exists(full_path):
                    try:
                        for item in Path(full_path).iterdir():
                            if item.is_file() and os.access(str(item), os.X_OK):
                                binary_count += 1
                    except (OSError, PermissionError):
                        continue
        
        return binary_count
    
    def _count_config_files(self) -> int:
        """Count configuration files in firmware."""
        config_count = 0
        config_extensions = ['.conf', '.cfg', '.ini', '.yaml', '.yml', '.json', '.xml']
        
        for firmware_path in self.extracted_paths:
            try:
                for root, dirs, files in os.walk(firmware_path):
                    for file in files:
                        if any(file.endswith(ext) for ext in config_extensions):
                            config_count += 1
            except (OSError, PermissionError):
                continue
        
        return config_count
    
    def _count_scripts(self) -> int:
        """Count scripts in firmware."""
        script_count = 0
        script_extensions = ['.sh', '.py', '.pl', '.rb', '.lua', '.php']
        
        for firmware_path in self.extracted_paths:
            try:
                for root, dirs, files in os.walk(firmware_path):
                    for file in files:
                        if any(file.endswith(ext) for ext in script_extensions):
                            script_count += 1
            except (OSError, PermissionError):
                continue
        
        return script_count
    
    def _estimate_analysis_time(self, binary_count: int, config_count: int, script_count: int) -> str:
        """Estimate analysis time based on content."""
        total_items = binary_count + config_count + script_count
        
        # Rough estimation: 1 second per binary, 0.5 seconds per config/script
        estimated_seconds = binary_count * 1 + (config_count + script_count) * 0.5
        
        # Add overhead for setup and reporting
        estimated_seconds *= 1.5
        
        # Convert to human readable format
        if estimated_seconds < 60:
            return f"{int(estimated_seconds)} seconds"
        elif estimated_seconds < 3600:
            return f"{int(estimated_seconds // 60)} minutes"
        else:
            hours = int(estimated_seconds // 3600)
            minutes = int((estimated_seconds % 3600) // 60)
            return f"{hours}h {minutes}m"

#!/usr/bin/env python3
"""
Main orchestration engine for Pymba.

This module provides the core engine that coordinates the entire
firmware analysis pipeline following the EMBA architecture.
"""

import os
import sys
import time
from pathlib import Path
from typing import Optional, List
from .config import PymbaConfig
from .logger import PymbaLogger
from .module_manager import ModuleManager
from ..helpers.system_utils import ensure_tools


class PymbaEngine:
    """Main orchestration engine for Pymba firmware analysis."""
    
    def __init__(self, config: PymbaConfig):
        self.config = config
        self.logger = PymbaLogger(config.log_dir)
        self.module_manager = ModuleManager(self.logger, config)
        self.start_time = time.time()
        self.testing_done = False
        
        # Validate configuration
        self._validate_config()
        
        # Initialize engine
        self._initialize()
    
    def _validate_config(self):
        """Validate configuration and exit if invalid."""
        issues = self.config.validate()
        if issues:
            self.logger.error("Configuration validation failed:")
            for issue in issues:
                self.logger.error(f"  - {issue}")
            sys.exit(1)
    
    def _initialize(self):
        """Initialize the engine."""
        self.logger.info("Initializing Pymba engine...")
        
        # Ensure external tools are available when needed
        self._ensure_external_tools()

        # Load modules
        self.module_manager.discover_modules()
        
        # Print welcome message
        self._print_welcome()
        
        # Print configuration summary
        self._print_config_summary()
        
        self.logger.info("Pymba engine initialized successfully")

    def _ensure_external_tools(self):
        """Check and auto-install external tools if required by enabled modules."""
        # Only ensure extractors if they are not blacklisted
        tools_to_check = []
        if 'P50_binwalk_extractor' not in self.config.module_blacklist:
            tools_to_check.append('binwalk')
        if 'P55_unblob_extractor' not in self.config.module_blacklist:
            tools_to_check.append('unblob')
        if not tools_to_check:
            return
        self.logger.info(f"Ensuring external tools are available: {', '.join(tools_to_check)}")
        results = ensure_tools(tools_to_check)
        for tool, ok in results.items():
            if ok:
                self.logger.success(f"Tool available: {tool}")
            else:
                self.logger.warning(f"Tool missing: {tool}. Related modules may be skipped or fail.")
    
    def _print_welcome(self):
        """Print welcome message."""
        welcome_text = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║                    PYMBA - Python EMBA                       ║
║              Firmware Security Analyzer v0.1.0               ║
║                                                              ║
║    A Python port of the EMBA firmware analysis framework    ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
        """
        self.logger.console.print(welcome_text, style="bold blue")
    
    def _print_config_summary(self):
        """Print configuration summary."""
        summary = f"""
Configuration Summary:
  Firmware Path: {self.config.firmware_path}
  Log Directory: {self.config.log_dir}
  Threading: {'Enabled' if self.config.threaded else 'Disabled'}
  Max Threads: {self.config.max_threads}
  HTML Report: {'Enabled' if self.config.html_report else 'Disabled'}
  RTOS Mode: {'Enabled' if self.config.rtos else 'Disabled'}
        """
        self.logger.info(summary)
    
    def run_analysis(self):
        """Run the complete firmware analysis pipeline."""
        try:
            self.logger.info("Starting Pymba firmware analysis")
            self.logger.write_notification("Pymba analysis started")
            
            # Phase 1: Pre-checking and Extraction (P-modules)
            if not self.config.rescan_sbom:
                self._run_pre_checking_phase()
            
            # Phase 2: Security Analysis (S-modules) - Only if firmware was extracted
            if self.testing_done and not self.config.rescan_sbom:
                self._run_security_analysis_phase()
            
            # Phase 3: Live Emulation (L-modules) - Optional
            if self.config.full_emulation and not self.config.rescan_sbom:
                self._run_emulation_phase()
            
            # Phase 4: Final Reporting (F-modules)
            self._run_reporting_phase()
            
            # Analysis complete
            self._finalize_analysis()
            
        except KeyboardInterrupt:
            self.logger.warning("Analysis interrupted by user")
            self._cleanup()
            sys.exit(1)
        except Exception as e:
            self.logger.error(f"Analysis failed: {e}")
            self._cleanup()
            sys.exit(1)
    
    def _run_pre_checking_phase(self):
        """Run the pre-checking and extraction phase (P-modules)."""
        self.logger.print_bar()
        self.logger.info("Pre-checking phase started")
        self.logger.write_notification("Pre-checking phase started")
        
        phase_start = time.time()
        
        # Run P-modules
        exit_codes = self.module_manager.run_module_group('P', self.config.threaded)
        
        phase_end = time.time()
        phase_duration = phase_end - phase_start
        
        self.logger.info(f"Pre-checking phase completed in {phase_duration:.2f} seconds")
        self.logger.write_notification("Pre-checking phase completed")
        
        # Check if any modules failed critically
        critical_failures = [code for code in exit_codes if code != 0]
        if critical_failures:
            self.logger.warning(f"{len(critical_failures)} modules failed in pre-checking phase")
        
        # Set testing_done if firmware was successfully extracted
        # This would be determined by checking if extraction modules succeeded
        self.testing_done = True  # Simplified for now
    
    def _run_security_analysis_phase(self):
        """Run the security analysis phase (S-modules)."""
        self.logger.print_bar()
        self.logger.info("Security analysis phase started")
        self.logger.write_notification("Security analysis phase started")
        
        phase_start = time.time()
        
        # Run S-modules
        exit_codes = self.module_manager.run_module_group('S', self.config.threaded)
        
        phase_end = time.time()
        phase_duration = phase_end - phase_start
        
        self.logger.info(f"Security analysis phase completed in {phase_duration:.2f} seconds")
        self.logger.write_notification("Security analysis phase completed")
    
    def _run_emulation_phase(self):
        """Run the live emulation phase (L-modules)."""
        self.logger.print_bar()
        self.logger.info("Live emulation phase started")
        self.logger.write_notification("Live emulation phase started")
        
        phase_start = time.time()
        
        # Run L-modules (not threaded by default due to emulation complexity)
        exit_codes = self.module_manager.run_module_group('L', threaded=False)
        
        phase_end = time.time()
        phase_duration = phase_end - phase_start
        
        self.logger.info(f"Live emulation phase completed in {phase_duration:.2f} seconds")
        self.logger.write_notification("Live emulation phase completed")
    
    def _run_reporting_phase(self):
        """Run the final reporting phase (F-modules)."""
        self.logger.print_bar()
        self.logger.info("Reporting phase started")
        self.logger.write_notification("Reporting phase started")
        
        phase_start = time.time()
        
        # Run F-modules (not threaded to ensure proper ordering)
        exit_codes = self.module_manager.run_module_group('F', threaded=False)
        
        phase_end = time.time()
        phase_duration = phase_end - phase_start
        
        self.logger.info(f"Reporting phase completed in {phase_duration:.2f} seconds")
        self.logger.write_notification("Reporting phase completed")
    
    def _finalize_analysis(self):
        """Finalize the analysis and print summary."""
        total_time = time.time() - self.start_time
        
        self.logger.print_bar()
        self.logger.success(f"Analysis completed successfully in {total_time:.2f} seconds")
        self.logger.write_notification("Pymba analysis completed")
        
        # Print summary
        summary = f"""
Analysis Summary:
  Total Duration: {total_time:.2f} seconds
  Firmware: {self.config.firmware_path}
  Log Directory: {self.config.log_dir}
        """
        
        if self.config.html_report:
            html_path = os.path.join(self.config.log_dir, "html-report", "index.html")
            if os.path.exists(html_path):
                summary += f"  HTML Report: {html_path}\n"
        
        self.logger.info(summary)
    
    def _cleanup(self):
        """Cleanup resources."""
        self.logger.info("Cleaning up resources...")
        # Add cleanup logic here if needed
    
    def show_runtime(self) -> str:
        """Get formatted runtime duration."""
        runtime = time.time() - self.start_time
        hours = int(runtime // 3600)
        minutes = int((runtime % 3600) // 60)
        seconds = int(runtime % 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"

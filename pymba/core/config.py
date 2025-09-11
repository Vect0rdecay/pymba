#!/usr/bin/env python3
"""
Configuration management for Pymba.

This module handles loading and managing configuration settings,
scan profiles, and runtime parameters.
"""

import os
import yaml
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


@dataclass
class PymbaConfig:
    """Main configuration class for Pymba."""
    
    # Version and metadata
    version: str = "0.1.0"
    release: bool = True
    
    # Core paths
    firmware_path: str = ""
    log_dir: str = ""
    output_dir: str = ""
    config_dir: str = "config"
    scan_profiles_dir: str = "scan_profiles"
    
    # Analysis settings
    threaded: bool = True
    max_threads: int = 0  # Auto-detect if 0
    max_module_threads: int = 0  # Auto-detect if 0
    html_report: bool = True
    format_log: bool = True
    short_path: bool = True
    
    # Firmware analysis settings
    rtos: bool = True  # Testing RTOS based OS
    binary_extended: bool = False
    max_ext_check_bins: int = 20
    container_extract: bool = False
    disable_deep: bool = False
    deep_extractor: str = "unblob"  # binwalk/unblob
    deep_ext_depth: int = 4
    
    # Security analysis settings
    yara_enabled: bool = True
    cwe_checker_enabled: bool = True
    capa_enabled: bool = True
    ghidra_enabled: bool = False  # Disabled by default (heavy)
    radare2_enabled: bool = True
    
    # Emulation settings
    qemulation: bool = False  # User-mode emulation
    full_emulation: bool = False  # System emulation
    
    # Module settings
    module_blacklist: List[str] = field(default_factory=list)
    selected_modules: List[str] = field(default_factory=list)
    
    # Docker settings
    use_docker: bool = True
    in_docker: bool = False
    
    # VEX metrics
    vex_metrics: bool = True
    
    # GPT integration
    gpt_option: bool = False
    
    # Rescan SBOM mode
    rescan_sbom: bool = False
    
    # Firmware metadata
    fw_vendor: str = ""
    fw_version: str = ""
    fw_device: str = ""
    fw_notes: str = ""
    
    def __post_init__(self):
        """Initialize computed fields after object creation."""
        if self.max_threads == 0:
            import multiprocessing
            self.max_threads = max(1, multiprocessing.cpu_count() // 2 + 1)
        
        if self.max_module_threads == 0:
            import multiprocessing
            self.max_module_threads = multiprocessing.cpu_count() * 2
    
    @classmethod
    def load_from_profile(cls, profile_path: str) -> "PymbaConfig":
        """Load configuration from a scan profile file."""
        config = cls()
        
        if not os.path.exists(profile_path):
            raise FileNotFoundError(f"Profile file not found: {profile_path}")
        
        with open(profile_path, 'r') as f:
            if profile_path.endswith('.yaml') or profile_path.endswith('.yml'):
                profile_data = yaml.safe_load(f)
            else:
                # Handle .emba files (bash-style exports)
                profile_data = cls._parse_emba_profile(f.read())
        
        # Update config with profile settings
        for key, value in profile_data.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        return config
    
    @staticmethod
    def _parse_emba_profile(content: str) -> Dict[str, Any]:
        """Parse EMBA-style profile files (bash exports)."""
        config = {}
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('export ') and '=' in line:
                # Remove 'export ' prefix
                line = line[7:]
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    
                    # Convert common values
                    if value.lower() in ('true', '1', 'yes'):
                        value = True
                    elif value.lower() in ('false', '0', 'no'):
                        value = False
                    elif value.isdigit():
                        value = int(value)
                    elif value.startswith('(') and value.endswith(')'):
                        # Handle arrays like ("module1" "module2")
                        value = [item.strip('"') for item in value[1:-1].split()]
                    
                    config[key] = value
        
        return config
    
    def save_to_file(self, filepath: str):
        """Save configuration to a YAML file."""
        config_dict = {}
        for key, value in self.__dict__.items():
            if not key.startswith('_'):
                config_dict[key] = value
        
        with open(filepath, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False, indent=2)
    
    def get_config_file_path(self, filename: str) -> str:
        """Get full path to a config file."""
        return os.path.join(self.config_dir, filename)
    
    def get_scan_profile_path(self, filename: str) -> str:
        """Get full path to a scan profile."""
        return os.path.join(self.scan_profiles_dir, filename)
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of issues."""
        issues = []
        
        if not self.firmware_path:
            issues.append("Firmware path is required")
        elif not os.path.exists(self.firmware_path):
            issues.append(f"Firmware path does not exist: {self.firmware_path}")
        
        if not self.log_dir:
            issues.append("Log directory is required")
        
        if self.max_threads < 1:
            issues.append("Max threads must be at least 1")
        
        if self.max_module_threads < 1:
            issues.append("Max module threads must be at least 1")
        
        return issues

#!/usr/bin/env python3
"""
Configuration Manager for Pymba.

This module provides configuration management functionality, replacing
the bash-based configuration system from EMBA.
"""

import os
import yaml
import json
import configparser
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum

from ..helpers.logging_utils import LogManager


class ConfigFormat(Enum):
    """Supported configuration file formats."""
    YAML = "yaml"
    JSON = "json"
    INI = "ini"
    PY = "py"


@dataclass
class PymbaConfig:
    """Main Pymba configuration class."""
    
    # Core paths
    firmware_path: str = ""
    log_dir: str = ""
    output_dir: str = ""
    temp_dir: str = ""
    
    # Analysis settings
    verbose: bool = False
    debug: bool = False
    quiet: bool = False
    force: bool = False
    
    # Module execution
    max_parallel_modules: int = 4
    max_threads_per_module: int = 2
    use_multiprocessing: bool = False
    module_timeout: Optional[int] = None
    
    # Architecture and platform
    target_architecture: str = ""
    force_architecture: bool = False
    exclude_paths: List[str] = None
    
    # Output formats
    generate_html: bool = False
    generate_json: bool = False
    generate_csv: bool = False
    generate_sbom: bool = False
    
    # Security settings
    enable_emulation: bool = False
    enable_system_emulation: bool = False
    sandbox_mode: bool = True
    
    # Docker settings
    use_docker: bool = True
    docker_image: str = "embeddedanalyzer/emba"
    
    # Database settings
    update_databases: bool = False
    cve_database_path: str = ""
    
    # Firmware metadata
    firmware_vendor: str = ""
    firmware_version: str = ""
    firmware_device: str = ""
    firmware_notes: str = ""
    
    def __post_init__(self):
        if self.exclude_paths is None:
            self.exclude_paths = []


class ConfigManager:
    """Manages configuration loading, saving, and validation."""
    
    def __init__(self, log_manager: LogManager):
        self.log_manager = log_manager
        self.config: Optional[PymbaConfig] = None
        self.config_files: List[Path] = []
        self.config_dir = Path.home() / ".pymba"
        
        # Default configuration paths
        self.default_config_paths = [
            Path("pymba.conf"),
            Path("~/.pymba/config.yaml"),
            Path("~/.pymba/config.json"),
            Path("/etc/pymba/config.yaml")
        ]
    
    def load_default_config(self) -> PymbaConfig:
        """Load default configuration."""
        self.config = PymbaConfig()
        
        # Set default paths
        if not self.config.log_dir:
            self.config.log_dir = str(Path.cwd() / "pymba_logs")
        
        if not self.config.output_dir:
            self.config.output_dir = str(Path.cwd() / "pymba_output")
        
        if not self.config.temp_dir:
            self.config.temp_dir = str(Path.cwd() / "pymba_temp")
        
        return self.config
    
    def load_config_file(self, config_path: Union[str, Path]) -> bool:
        """Load configuration from a file."""
        config_path = Path(config_path).expanduser().resolve()
        
        if not config_path.exists():
            self.log_manager.print_warning(f"Configuration file not found: {config_path}")
            return False
        
        try:
            config_format = self._detect_config_format(config_path)
            
            if config_format == ConfigFormat.YAML:
                config_data = self._load_yaml_config(config_path)
            elif config_format == ConfigFormat.JSON:
                config_data = self._load_json_config(config_path)
            elif config_format == ConfigFormat.INI:
                config_data = self._load_ini_config(config_path)
            elif config_format == ConfigFormat.PY:
                config_data = self._load_python_config(config_path)
            else:
                self.log_manager.print_error(f"Unsupported configuration format: {config_format}")
                return False
            
            # Merge with existing config
            if self.config:
                self._merge_config_data(config_data)
            else:
                self.config = PymbaConfig(**config_data)
            
            self.config_files.append(config_path)
            self.log_manager.print_success(f"Loaded configuration from: {config_path}")
            return True
            
        except Exception as e:
            self.log_manager.print_error(f"Failed to load configuration from {config_path}: {e}")
            return False
    
    def _detect_config_format(self, config_path: Path) -> ConfigFormat:
        """Detect configuration file format."""
        suffix = config_path.suffix.lower()
        
        if suffix in ['.yaml', '.yml']:
            return ConfigFormat.YAML
        elif suffix == '.json':
            return ConfigFormat.JSON
        elif suffix in ['.ini', '.cfg', '.conf']:
            return ConfigFormat.INI
        elif suffix == '.py':
            return ConfigFormat.PY
        else:
            # Try to detect by content
            try:
                with open(config_path, 'r') as f:
                    content = f.read(100).strip()
                    if content.startswith('{'):
                        return ConfigFormat.JSON
                    elif content.startswith('---') or ':' in content:
                        return ConfigFormat.YAML
                    elif '=' in content:
                        return ConfigFormat.INI
            except:
                pass
            
            return ConfigFormat.INI  # Default fallback
    
    def _load_yaml_config(self, config_path: Path) -> Dict[str, Any]:
        """Load YAML configuration file."""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f) or {}
    
    def _load_json_config(self, config_path: Path) -> Dict[str, Any]:
        """Load JSON configuration file."""
        with open(config_path, 'r') as f:
            return json.load(f)
    
    def _load_ini_config(self, config_path: Path) -> Dict[str, Any]:
        """Load INI configuration file."""
        config_parser = configparser.ConfigParser()
        config_parser.read(config_path)
        
        config_data = {}
        for section_name in config_parser.sections():
            section_data = {}
            for key, value in config_parser[section_name].items():
                # Try to convert to appropriate type
                section_data[key] = self._convert_config_value(value)
            config_data[section_name] = section_data
        
        return config_data
    
    def _load_python_config(self, config_path: Path) -> Dict[str, Any]:
        """Load Python configuration file."""
        import importlib.util
        
        spec = importlib.util.spec_from_file_location("config", config_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Extract configuration from module
        config_data = {}
        for attr_name in dir(module):
            if not attr_name.startswith('_'):
                attr_value = getattr(module, attr_name)
                if isinstance(attr_value, (str, int, float, bool, list, dict)):
                    config_data[attr_name] = attr_value
        
        return config_data
    
    def _convert_config_value(self, value: str) -> Any:
        """Convert string configuration value to appropriate type."""
        value = value.strip()
        
        # Boolean values
        if value.lower() in ['true', 'yes', 'on', '1']:
            return True
        elif value.lower() in ['false', 'no', 'off', '0']:
            return False
        
        # Numeric values
        try:
            if '.' in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            pass
        
        # List values (comma-separated)
        if ',' in value:
            return [self._convert_config_value(item.strip()) for item in value.split(',')]
        
        # String value
        return value
    
    def _merge_config_data(self, new_data: Dict[str, Any]):
        """Merge new configuration data with existing config."""
        if not self.config:
            return
        
        config_dict = asdict(self.config)
        
        # Recursive merge
        self._recursive_update(config_dict, new_data)
        
        # Update config object
        self.config = PymbaConfig(**config_dict)
    
    def _recursive_update(self, base_dict: Dict[str, Any], update_dict: Dict[str, Any]):
        """Recursively update dictionary."""
        for key, value in update_dict.items():
            if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                self._recursive_update(base_dict[key], value)
            else:
                base_dict[key] = value
    
    def save_config(self, config_path: Union[str, Path], 
                   format: Optional[ConfigFormat] = None) -> bool:
        """Save current configuration to file."""
        if not self.config:
            self.log_manager.print_error("No configuration to save")
            return False
        
        config_path = Path(config_path).expanduser().resolve()
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            if format is None:
                format = self._detect_config_format(config_path)
            
            config_data = asdict(self.config)
            
            if format == ConfigFormat.YAML:
                self._save_yaml_config(config_path, config_data)
            elif format == ConfigFormat.JSON:
                self._save_json_config(config_path, config_data)
            elif format == ConfigFormat.INI:
                self._save_ini_config(config_path, config_data)
            else:
                self.log_manager.print_error(f"Cannot save to format: {format}")
                return False
            
            self.log_manager.print_success(f"Configuration saved to: {config_path}")
            return True
            
        except Exception as e:
            self.log_manager.print_error(f"Failed to save configuration to {config_path}: {e}")
            return False
    
    def _save_yaml_config(self, config_path: Path, config_data: Dict[str, Any]):
        """Save configuration as YAML."""
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f, default_flow_style=False, indent=2)
    
    def _save_json_config(self, config_path: Path, config_data: Dict[str, Any]):
        """Save configuration as JSON."""
        with open(config_path, 'w') as f:
            json.dump(config_data, f, indent=2)
    
    def _save_ini_config(self, config_path: Path, config_data: Dict[str, Any]):
        """Save configuration as INI."""
        config_parser = configparser.ConfigParser()
        
        # Flatten nested dictionaries
        flat_data = self._flatten_dict(config_data)
        
        # Create sections
        sections = {}
        for key, value in flat_data.items():
            section = 'DEFAULT'
            if '_' in key:
                section, option = key.split('_', 1)
            else:
                option = key
            
            if section not in sections:
                sections[section] = {}
            sections[section][option] = str(value)
        
        # Add sections to parser
        for section_name, section_data in sections.items():
            config_parser[section_name] = section_data
        
        with open(config_path, 'w') as f:
            config_parser.write(f)
    
    def _flatten_dict(self, data: Dict[str, Any], prefix: str = '') -> Dict[str, Any]:
        """Flatten nested dictionary."""
        result = {}
        for key, value in data.items():
            new_key = f"{prefix}_{key}" if prefix else key
            if isinstance(value, dict):
                result.update(self._flatten_dict(value, new_key))
            else:
                result[new_key] = value
        return result
    
    def validate_config(self) -> List[str]:
        """Validate current configuration and return list of issues."""
        issues = []
        
        if not self.config:
            return ["No configuration loaded"]
        
        # Validate required paths
        if not self.config.firmware_path:
            issues.append("Firmware path is required")
        elif not Path(self.config.firmware_path).exists():
            issues.append(f"Firmware path does not exist: {self.config.firmware_path}")
        
        if not self.config.log_dir:
            issues.append("Log directory is required")
        
        # Validate numeric values
        if self.config.max_parallel_modules < 1:
            issues.append("max_parallel_modules must be at least 1")
        
        if self.config.max_threads_per_module < 1:
            issues.append("max_threads_per_module must be at least 1")
        
        # Validate architecture
        if self.config.target_architecture:
            valid_archs = ['mips', 'arm', 'x86', 'x64', 'ppc', 'aarch64']
            if self.config.target_architecture.lower() not in valid_archs:
                issues.append(f"Invalid target architecture: {self.config.target_architecture}")
        
        return issues
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key."""
        if not self.config:
            return default
        
        # Support dot notation for nested keys
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if hasattr(value, k):
                value = getattr(value, k)
            else:
                return default
        
        return value
    
    def set_config_value(self, key: str, value: Any) -> bool:
        """Set configuration value by key."""
        if not self.config:
            return False
        
        try:
            # Support dot notation for nested keys
            keys = key.split('.')
            obj = self.config
            
            for k in keys[:-1]:
                if not hasattr(obj, k):
                    return False
                obj = getattr(obj, k)
            
            setattr(obj, keys[-1], value)
            return True
            
        except Exception:
            return False
    
    def load_scan_profile(self, profile_path: Union[str, Path]) -> bool:
        """Load scan profile configuration."""
        profile_path = Path(profile_path).expanduser().resolve()
        
        if not profile_path.exists():
            self.log_manager.print_error(f"Scan profile not found: {profile_path}")
            return False
        
        try:
            # Load profile as YAML or JSON
            if profile_path.suffix.lower() in ['.yaml', '.yml']:
                with open(profile_path, 'r') as f:
                    profile_data = yaml.safe_load(f)
            elif profile_path.suffix.lower() == '.json':
                with open(profile_path, 'r') as f:
                    profile_data = json.load(f)
            else:
                self.log_manager.print_error(f"Unsupported profile format: {profile_path.suffix}")
                return False
            
            # Apply profile settings
            if self.config:
                self._merge_config_data(profile_data)
            else:
                self.config = PymbaConfig(**profile_data)
            
            self.log_manager.print_success(f"Loaded scan profile: {profile_path}")
            return True
            
        except Exception as e:
            self.log_manager.print_error(f"Failed to load scan profile {profile_path}: {e}")
            return False
    
    def create_scan_profile(self, profile_path: Union[str, Path], 
                          profile_name: str, description: str = "") -> bool:
        """Create a new scan profile."""
        profile_path = Path(profile_path).expanduser().resolve()
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        
        if not self.config:
            self.log_manager.print_error("No configuration to create profile from")
            return False
        
        try:
            profile_data = {
                'profile_name': profile_name,
                'description': description,
                'created_by': 'pymba',
                **asdict(self.config)
            }
            
            with open(profile_path, 'w') as f:
                yaml.dump(profile_data, f, default_flow_style=False, indent=2)
            
            self.log_manager.print_success(f"Created scan profile: {profile_path}")
            return True
            
        except Exception as e:
            self.log_manager.print_error(f"Failed to create scan profile {profile_path}: {e}")
            return False
    
    def list_scan_profiles(self, profiles_dir: Union[str, Path]) -> List[Path]:
        """List available scan profiles."""
        profiles_dir = Path(profiles_dir).expanduser().resolve()
        
        if not profiles_dir.exists():
            return []
        
        profiles = []
        for pattern in ['*.yaml', '*.yml', '*.json']:
            profiles.extend(profiles_dir.glob(pattern))
        
        return sorted(profiles)
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get configuration summary."""
        if not self.config:
            return {"status": "No configuration loaded"}
        
        issues = self.validate_config()
        
        return {
            "status": "valid" if not issues else "invalid",
            "issues": issues,
            "firmware_path": self.config.firmware_path,
            "log_dir": self.config.log_dir,
            "max_parallel_modules": self.config.max_parallel_modules,
            "target_architecture": self.config.target_architecture,
            "enabled_features": {
                "verbose": self.config.verbose,
                "debug": self.config.debug,
                "emulation": self.config.enable_emulation,
                "docker": self.config.use_docker,
                "html_report": self.config.generate_html,
                "json_output": self.config.generate_json
            },
            "config_files": [str(f) for f in self.config_files]
        }

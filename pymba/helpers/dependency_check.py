#!/usr/bin/env python3
"""
Dependency checking utilities for Pymba.

This module provides dependency checking functionality ported from 
EMBA's helpers_emba_dependency_check.sh.
"""

import os
import sys
import subprocess
import shutil
import psutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from .logging_utils import LogManager, Colors


class DependencyChecker:
    """Checks and validates dependencies for Pymba."""
    
    def __init__(self, log_manager: LogManager, use_docker: bool = True):
        self.log_manager = log_manager
        self.use_docker = use_docker
        self.dep_error = False
        self.dep_exit = False
        
        # External tools directory (similar to EMBA's EXT_DIR)
        self.ext_dir = Path("external")
        
        # Tool paths
        self.binwalk_bin = None
        self.cyclonedx_bin = None
        self.cwe_checker_bin = None
        self.cve_bin_tool_bin = None
        
    def check_dep_file(self, file_name: str, file_path: str) -> bool:
        """Check if a file exists."""
        self.log_manager.print_output(f"    {file_name} - ", "no_log")
        
        if not os.path.isfile(file_path):
            self.log_manager.print_output(f"{Colors.RED}not ok{Colors.NC}\n")
            self.log_manager.print_error(f"    Missing {file_name} - check your installation")
            self.dep_error = True
            return False
        else:
            self.log_manager.print_output(f"{Colors.GREEN}ok{Colors.NC}\n")
            return True
    
    def check_dep_tool(self, tool_name: str, tool_command: Optional[str] = None) -> bool:
        """Check if a tool command exists in PATH."""
        if tool_command is None:
            tool_command = tool_name
            
        self.log_manager.print_output(f"    {tool_name} - ", "no_log")
        
        if not shutil.which(tool_command):
            self.log_manager.print_output(f"{Colors.RED}not ok{Colors.NC}\n")
            self.log_manager.print_error(f"    Missing {tool_name} - check your installation")
            self.dep_error = True
            return False
        else:
            self.log_manager.print_output(f"{Colors.GREEN}ok{Colors.NC}\n")
            return True
    
    def check_dep_tool_warning(self, tool_name: str, tool_command: Optional[str] = None) -> bool:
        """Check if a tool command exists in PATH (warning only)."""
        if tool_command is None:
            tool_command = tool_name
            
        self.log_manager.print_output(f"    {tool_name} - ", "no_log")
        
        if not shutil.which(tool_command):
            self.log_manager.print_output(f"{Colors.ORANGE}not ok{Colors.NC}\n")
            self.log_manager.print_warning(f"    Missing {tool_name} - check your installation")
            return False
        else:
            self.log_manager.print_output(f"{Colors.GREEN}ok{Colors.NC}\n")
            return True
    
    def check_dep_port(self, tool_name: str, port_num: int) -> bool:
        """Check if a port is in use."""
        self.log_manager.print_output(f"    {tool_name} - ", "no_log")
        
        try:
            # Check if port is in use
            result = subprocess.run(
                ["netstat", "-anpt"], 
                capture_output=True, 
                text=True, 
                check=False
            )
            
            if str(port_num) in result.stdout:
                self.log_manager.print_output(f"{Colors.GREEN}ok{Colors.NC}\n")
                return True
            else:
                self.log_manager.print_output(f"{Colors.RED}not ok{Colors.NC}\n")
                self.log_manager.print_error(f"    Missing {tool_name} - check your installation")
                self.dep_error = True
                return False
                
        except (OSError, subprocess.SubprocessError):
            self.log_manager.print_output(f"{Colors.RED}not ok{Colors.NC}\n")
            self.log_manager.print_error(f"    Error checking port {port_num}")
            self.dep_error = True
            return False
    
    def setup_tool_paths(self):
        """Setup paths for external tools."""
        if not self.use_docker:
            # Check for binwalk
            if shutil.which("binwalk"):
                self.binwalk_bin = shutil.which("binwalk")
            else:
                binwalk_path = self.ext_dir / "binwalk" / "target" / "release" / "binwalk"
                if binwalk_path.exists():
                    self.binwalk_bin = str(binwalk_path)
            
            # Check for cyclonedx
            if shutil.which("cyclonedx"):
                self.cyclonedx_bin = shutil.which("cyclonedx")
            else:
                # Check in homebrew path (like EMBA does)
                homebrew_path = Path("/home/linuxbrew/.linuxbrew/bin/cyclonedx")
                if homebrew_path.exists():
                    self.cyclonedx_bin = str(homebrew_path)
            
            # Check for cwe_checker
            if shutil.which("cwe_checker"):
                self.cwe_checker_bin = shutil.which("cwe_checker")
            else:
                cwe_path = self.ext_dir / "cwe_checker" / "cwe_checker"
                if cwe_path.exists():
                    self.cwe_checker_bin = str(cwe_path)
            
            # Check for cve_bin_tool
            if shutil.which("cve-bin-tool"):
                self.cve_bin_tool_bin = shutil.which("cve-bin-tool")
            else:
                cve_path = self.ext_dir / "cve_bin_tool" / "bin" / "cve-bin-tool"
                if cve_path.exists():
                    self.cve_bin_tool_bin = str(cve_path)
    
    def check_docker_environment(self) -> bool:
        """Check Docker environment setup."""
        self.log_manager.sub_module_title("Docker environment check")
        
        # Check if running in Docker
        if os.path.exists("/.dockerenv"):
            self.log_manager.print_info("Running inside Docker container")
            return True
        
        # Check if Docker is available
        if not self.check_dep_tool("docker", "docker"):
            return False
        
        # Check if docker compose is available
        docker_compose_available = (
            self.check_dep_tool_warning("docker compose", "docker compose") or
            self.check_dep_tool_warning("docker-compose", "docker-compose")
        )
        
        if not docker_compose_available:
            self.log_manager.print_warning("Docker Compose not available - some features may not work")
        
        return True
    
    def check_basic_tools(self) -> bool:
        """Check basic required tools."""
        self.log_manager.sub_module_title("Basic tools check")
        
        basic_tools = [
            "python3",
            "git",
            "curl",
            "wget",
            "unzip",
            "tar",
            "gzip",
            "file",
            "strings",
            "hexdump",
            "objdump",
            "readelf",
            "nm",
            "ldd",
            "find",
            "grep",
            "sed",
            "awk",
            "sort",
            "uniq",
            "wc",
            "head",
            "tail",
            "cut",
            "tr",
            "xargs"
        ]
        
        all_ok = True
        for tool in basic_tools:
            if not self.check_dep_tool(tool):
                all_ok = False
        
        return all_ok
    
    def check_analysis_tools(self) -> bool:
        """Check firmware analysis tools."""
        self.log_manager.sub_module_title("Analysis tools check")
        
        analysis_tools = [
            ("binwalk", "binwalk"),
            ("unblob", "unblob"),
            ("7zip", "7z"),
            ("sasquatch", "sasquatch"),
            ("yaffshiv", "yaffshiv"),
            ("jefferson", "jefferson"),
            ("ubireader", "ubireader_extract_images"),
            ("cramfs", "cramfsck"),
            ("romfs", "romfs"),
            ("squashfs", "unsquashfs"),
            ("cpio", "cpio"),
            ("ar", "ar"),
            ("nm", "nm"),
            ("objdump", "objdump"),
            ("readelf", "readelf"),
            ("hexdump", "hexdump"),
            ("strings", "strings"),
            ("file", "file")
        ]
        
        all_ok = True
        for tool_name, tool_cmd in analysis_tools:
            if not self.check_dep_tool_warning(tool_name, tool_cmd):
                all_ok = False
        
        return all_ok
    
    def check_python_dependencies(self) -> bool:
        """Check Python dependencies."""
        self.log_manager.sub_module_title("Python dependencies check")
        
        python_packages = [
            "psutil",
            "requests",
            "yara-python",
            "python-magic",
            "cryptography",
            "pillow",
            "jinja2",
            "lxml",
            "beautifulsoup4",
            "matplotlib",
            "numpy",
            "scapy",
            "capstone",
            "keystone-engine",
            "unicorn"
        ]
        
        all_ok = True
        for package in python_packages:
            try:
                __import__(package.replace("-", "_"))
                self.log_manager.print_output(f"    {package} - {Colors.GREEN}ok{Colors.NC}\n")
            except ImportError:
                self.log_manager.print_output(f"    {package} - {Colors.ORANGE}not ok{Colors.NC}\n")
                self.log_manager.print_warning(f"    Missing Python package: {package}")
                all_ok = False
        
        return all_ok
    
    def check_system_requirements(self) -> bool:
        """Check system requirements."""
        self.log_manager.sub_module_title("System requirements check")
        
        # Check memory
        memory = psutil.virtual_memory()
        memory_gb = memory.total / (1024**3)
        
        self.log_manager.print_output(f"    Available memory - ", "no_log")
        if memory_gb >= 4:
            self.log_manager.print_output(f"{Colors.GREEN}{memory_gb:.1f} GB{Colors.NC}\n")
        else:
            self.log_manager.print_output(f"{Colors.ORANGE}{memory_gb:.1f} GB{Colors.NC}\n")
            self.log_manager.print_warning("    Low memory - at least 4GB recommended")
        
        # Check disk space
        disk_usage = psutil.disk_usage("/")
        free_gb = disk_usage.free / (1024**3)
        
        self.log_manager.print_output(f"    Available disk space - ", "no_log")
        if free_gb >= 20:
            self.log_manager.print_output(f"{Colors.GREEN}{free_gb:.1f} GB{Colors.NC}\n")
        else:
            self.log_manager.print_output(f"{Colors.ORANGE}{free_gb:.1f} GB{Colors.NC}\n")
            self.log_manager.print_warning("    Low disk space - at least 20GB recommended")
        
        # Check CPU cores
        cpu_count = psutil.cpu_count()
        self.log_manager.print_output(f"    CPU cores - ", "no_log")
        if cpu_count >= 2:
            self.log_manager.print_output(f"{Colors.GREEN}{cpu_count}{Colors.NC}\n")
        else:
            self.log_manager.print_output(f"{Colors.ORANGE}{cpu_count}{Colors.NC}\n")
            self.log_manager.print_warning("    Low CPU count - at least 2 cores recommended")
        
        return True
    
    def prepare_docker_home_dir(self):
        """Prepare Docker home directory for tools that need it."""
        if not self.use_docker:
            return
        
        # Create .config directory if needed
        config_dir = Path.home() / ".config"
        if not config_dir.exists():
            config_dir.mkdir(parents=True)
        
        # Copy cwe_checker config if available
        cwe_config_src = self.ext_dir / "cwe_checker" / ".config"
        if cwe_config_src.exists():
            import shutil
            try:
                shutil.copytree(cwe_config_src, config_dir / "cwe_checker", dirs_exist_ok=True)
            except (OSError, shutil.Error):
                pass
        
        # Copy .local/share if available
        local_share_src = self.ext_dir / "cwe_checker" / ".local" / "share"
        local_share_dst = Path.home() / ".local" / "share"
        if local_share_src.exists():
            import shutil
            try:
                shutil.copytree(local_share_src, local_share_dst, dirs_exist_ok=True)
            except (OSError, shutil.Error):
                pass
    
    def run_full_dependency_check(self, only_dep: int = 0) -> bool:
        """Run complete dependency check."""
        self.log_manager.module_title("Dependency Check")
        
        if only_dep == 0:
            self.log_manager.print_info("Running full dependency check...")
        elif only_dep == 1:
            self.log_manager.print_info("Running host dependency check...")
        elif only_dep == 2:
            self.log_manager.print_info("Running container dependency check...")
        
        # Setup tool paths
        self.setup_tool_paths()
        
        # Check Docker environment (if not only checking container)
        if only_dep != 2:
            if not self.check_docker_environment():
                self.dep_error = True
        
        # Check basic tools
        if not self.check_basic_tools():
            self.dep_error = True
        
        # Check analysis tools
        if not self.check_analysis_tools():
            self.dep_error = True
        
        # Check Python dependencies
        if not self.check_python_dependencies():
            self.dep_error = True
        
        # Check system requirements
        if not self.check_system_requirements():
            self.dep_error = True
        
        # Prepare Docker environment
        self.prepare_docker_home_dir()
        
        # Summary
        self.log_manager.print_ln()
        if self.dep_error:
            self.log_manager.print_error("Dependency check failed - some required tools are missing")
            return False
        else:
            self.log_manager.print_success("All dependencies satisfied")
            return True


def check_dependencies(log_manager: LogManager, use_docker: bool = True, only_dep: int = 0) -> bool:
    """Convenience function to run dependency check."""
    checker = DependencyChecker(log_manager, use_docker)
    return checker.run_full_dependency_check(only_dep)

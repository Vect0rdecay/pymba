#!/usr/bin/env python3
"""
Parameter parsing utilities for Pymba.

This module provides command-line parameter parsing functionality ported from 
EMBA's helpers_emba_parameter_parser.sh.
"""

import argparse
import os
import sys
import re
from typing import Dict, List, Optional, Any
from .logging_utils import LogManager, Colors


class ParameterParser:
    """Parses command-line parameters for Pymba."""
    
    def __init__(self):
        self.args = None
        self.parser = None
        
        # Parameter defaults (similar to EMBA)
        self.defaults = {
            'firmware_path': '',
            'log_dir': '',
            'arch': '',
            'arch_check': 1,
            'binary_extended': 0,
            'only_dep': 0,
            'container_extract': 0,
            'container_id': '',
            'exclude_paths': [],
            'qemulation': 0,
            'force': 0,
            'kernel_path': '',
            'log_level': 1,
            'modules': [],
            'threads': 1,
            'profile': '',
            'quick': 0,
            'quiet': 0,
            'reset': 0,
            'scan_profile': '',
            'test': 0,
            'update_db': 0,
            'vendor': '',
            'version': '',
            'web_report': 0,
            'xss': 0,
            'yara': 0,
            'zip': 0,
            'zap': 0,
            'use_docker': 1,
            'full_emulation': 0,
            'disable_status_bar': 1,
            'silent': 0,
            'verbose': 0,
            'debug': 0,
            'html': 0,
            'json': 0,
            'csv': 0,
            'short_path': 0,
            'disable_notifications': 0
        }
        
        self._setup_parser()
    
    def _setup_parser(self):
        """Setup argument parser."""
        self.parser = argparse.ArgumentParser(
            description='Pymba - Python Firmware Security Analyzer',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  pymba -f firmware.bin -l ./logs
  pymba -f firmware.bin -l ./logs -p ./scan-profiles/default-scan.pymba
  pymba -f firmware.bin -l ./logs -E -Q
  pymba -d 2  # Dependency check only
            """
        )
        
        # Core parameters
        self.parser.add_argument('-f', '--firmware', 
                               help='Firmware file or directory to analyze')
        self.parser.add_argument('-l', '--log-dir', 
                               help='Output directory for logs and reports')
        
        # Architecture
        self.parser.add_argument('-a', '--arch', 
                               help='Target architecture (e.g., mips, arm, x86)')
        self.parser.add_argument('-A', '--arch-no-check', 
                               help='Target architecture without verification')
        
        # Analysis options
        self.parser.add_argument('-c', '--extended', action='store_true',
                               help='Extended binary analysis')
        self.parser.add_argument('-E', '--emulation', action='store_true',
                               help='Enable system emulation')
        self.parser.add_argument('-F', '--force', action='store_true',
                               help='Force analysis even if issues detected')
        self.parser.add_argument('-Q', '--quick', action='store_true',
                               help='Quick analysis mode')
        self.parser.add_argument('-q', '--quiet', action='store_true',
                               help='Quiet mode (minimal output)')
        
        # Exclusions
        self.parser.add_argument('-e', '--exclude', action='append',
                               help='Exclude path from analysis (can be used multiple times)')
        
        # Kernel
        self.parser.add_argument('-k', '--kernel',
                               help='Kernel file for analysis')
        
        # Modules
        self.parser.add_argument('-m', '--modules', action='append',
                               help='Specific modules to run (can be used multiple times)')
        
        # Threading
        self.parser.add_argument('-t', '--threads', type=int, default=1,
                               help='Number of threads for parallel execution')
        
        # Profiles
        self.parser.add_argument('-p', '--profile',
                               help='Scan profile to use')
        self.parser.add_argument('-P', '--scan-profile',
                               help='Alternative scan profile parameter')
        
        # Output formats
        self.parser.add_argument('-H', '--html', action='store_true',
                               help='Generate HTML report')
        self.parser.add_argument('-j', '--json', action='store_true',
                               help='Generate JSON output')
        self.parser.add_argument('-C', '--csv', action='store_true',
                               help='Generate CSV output')
        
        # Docker options
        self.parser.add_argument('-D', '--no-docker', action='store_true',
                               help='Run without Docker (development mode)')
        self.parser.add_argument('--container',
                               help='Docker container ID for extraction')
        
        # Dependency check
        self.parser.add_argument('-d', '--dep-check', type=int, choices=[1, 2],
                               help='Dependency check mode (1=host+container, 2=container only)')
        
        # Reset and cleanup
        self.parser.add_argument('-r', '--reset', action='store_true',
                               help='Reset and cleanup previous analysis')
        
        # Testing
        self.parser.add_argument('-T', '--test', action='store_true',
                               help='Test mode')
        
        # Database update
        self.parser.add_argument('-U', '--update-db', action='store_true',
                               help='Update vulnerability databases')
        
        # Vendor/Version
        self.parser.add_argument('--vendor',
                               help='Firmware vendor')
        self.parser.add_argument('-V', '--version',
                               help='Firmware version')
        
        # Web report
        self.parser.add_argument('-W', '--web-report', action='store_true',
                               help='Generate web-based report')
        
        # YARA
        self.parser.add_argument('-y', '--yara', action='store_true',
                               help='Enable YARA scanning')
        
        # ZIP
        self.parser.add_argument('-z', '--zip', action='store_true',
                               help='Create ZIP archive of results')
        
        # Zap
        self.parser.add_argument('-Z', '--zap', action='store_true',
                               help='Enable ZAP security testing')
        
        # XSS
        self.parser.add_argument('-X', '--xss', action='store_true',
                               help='Enable XSS testing')
        
        # Verbosity
        self.parser.add_argument('-v', '--verbose', action='store_true',
                               help='Verbose output')
        self.parser.add_argument('--debug', action='store_true',
                               help='Debug mode')
        
        # Short paths
        self.parser.add_argument('-s', '--short-path', action='store_true',
                               help='Use short paths in output')
        
        # Disable features
        self.parser.add_argument('-B', '--no-status-bar', action='store_true',
                               help='Disable status bar')
        self.parser.add_argument('--no-notifications', action='store_true',
                               help='Disable notifications')
        
        # Help
        # Help is automatically provided by argparse
        
        # Banner
        self.parser.add_argument('-b', '--banner', action='store_true',
                               help='Show banner and exit')
    
    def parse_args(self, args: Optional[List[str]] = None) -> argparse.Namespace:
        """Parse command-line arguments."""
        self.args = self.parser.parse_args(args)
        return self.args
    
    def validate_args(self) -> bool:
        """Validate parsed arguments."""
        if not self.args:
            return False
        
        # Check required parameters
        if not self.args.firmware and not self.args.dep_check and not self.args.banner:
            print(f"{Colors.RED}Error: Firmware path (-f) is required{Colors.NC}")
            return False
        
        if not self.args.log_dir and not self.args.dep_check and not self.args.banner:
            print(f"{Colors.RED}Error: Log directory (-l) is required{Colors.NC}")
            return False
        
        # Validate paths
        if self.args.firmware and not self._check_path_input(self.args.firmware):
            return False
        
        if self.args.log_dir and not self._check_path_input(self.args.log_dir):
            return False
        
        if self.args.kernel and not self._check_path_input(self.args.kernel):
            return False
        
        if self.args.exclude:
            for exclude_path in self.args.exclude:
                if not self._check_path_input(exclude_path):
                    return False
        
        # Validate architecture
        if self.args.arch and not self._check_alnum(self.args.arch):
            return False
        
        if self.args.arch_no_check and not self._check_alnum(self.args.arch_no_check):
            return False
        
        # Validate container ID
        if self.args.container and not self._check_alnum(self.args.container):
            return False
        
        # Validate vendor/version
        if self.args.vendor and not self._check_alnum(self.args.vendor):
            return False
        
        if self.args.version and not self._check_alnum(self.args.version):
            return False
        
        return True
    
    def _check_path_input(self, path: str) -> bool:
        """Check if path input is valid."""
        if not path:
            return False
        
        # Check for dangerous characters
        dangerous_chars = [';', '&', '|', '`', '$', '(', ')', '<', '>']
        for char in dangerous_chars:
            if char in path:
                print(f"{Colors.RED}Error: Invalid character '{char}' in path: {path}{Colors.NC}")
                return False
        
        return True
    
    def _check_alnum(self, text: str) -> bool:
        """Check if text contains only alphanumeric characters."""
        if not text:
            return False
        
        # Allow alphanumeric, hyphens, underscores, dots
        if not re.match(r'^[a-zA-Z0-9._-]+$', text):
            print(f"{Colors.RED}Error: Invalid characters in: {text}{Colors.NC}")
            return False
        
        return True
    
    def get_parsed_args(self) -> Dict[str, Any]:
        """Get parsed arguments as dictionary."""
        if not self.args:
            return {}
        
        args_dict = vars(self.args).copy()
        
        # Set defaults for missing values
        for key, default_value in self.defaults.items():
            if key not in args_dict or args_dict[key] is None:
                args_dict[key] = default_value
        
        # Handle special cases
        if args_dict.get('arch_no_check'):
            args_dict['arch'] = args_dict['arch_no_check']
            args_dict['arch_check'] = 0
        
        if args_dict.get('dep_check'):
            args_dict['only_dep'] = args_dict['dep_check']
        
        if args_dict.get('no_docker'):
            args_dict['use_docker'] = 0
        
        if args_dict.get('no_status_bar'):
            args_dict['disable_status_bar'] = 0
        
        if args_dict.get('extended'):
            args_dict['binary_extended'] = 1
        
        if args_dict.get('emulation'):
            args_dict['qemulation'] = 1
        
        if args_dict.get('container'):
            args_dict['container_extract'] = 1
            args_dict['container_id'] = args_dict['container']
        
        if args_dict.get('exclude'):
            args_dict['exclude_paths'] = args_dict['exclude']
        
        # Set log level based on verbosity
        if args_dict.get('debug'):
            args_dict['log_level'] = 3
            args_dict['verbose'] = 1
        elif args_dict.get('verbose'):
            args_dict['log_level'] = 2
        elif args_dict.get('quiet'):
            args_dict['log_level'] = 0
            args_dict['silent'] = 1
        
        return args_dict
    
    def print_help(self):
        """Print help message."""
        self.parser.print_help()
    
    def print_banner(self):
        """Print Pymba banner."""
        banner = f"""
{Colors.BOLD}╔═══════════════════════════════════════════════════════════════╗{Colors.NC}
{Colors.BOLD}║{Colors.BLUE}{Colors.BOLD}{Colors.ITALIC}                            P Y M B A                            {Colors.NC}{Colors.BOLD}║{Colors.NC}
{Colors.BOLD}║                   PYTHON FIRMWARE ANALYZER                  {Colors.NC}{Colors.BOLD}║{Colors.NC}
{Colors.BOLD}║                                                               {Colors.NC}{Colors.BOLD}║{Colors.NC}
{Colors.BOLD}║  A comprehensive firmware security analysis framework        {Colors.NC}{Colors.BOLD}║{Colors.NC}
{Colors.BOLD}║  Port of EMBA (Embedded Linux Analyzer)                      {Colors.NC}{Colors.BOLD}║{Colors.NC}
{Colors.BOLD}╚═══════════════════════════════════════════════════════════════╝{Colors.NC}

{Colors.CYAN}Usage:{Colors.NC} pymba [OPTIONS] -f FIRMWARE -l LOG_DIR

{Colors.CYAN}Examples:{Colors.NC}
  pymba -f firmware.bin -l ./logs
  pymba -f firmware.bin -l ./logs -p ./scan-profiles/default-scan.pymba
  pymba -f firmware.bin -l ./logs -E -Q
  pymba -d 2  # Dependency check only

{Colors.CYAN}For more information, visit:{Colors.NC} https://github.com/pymba/pymba
"""
        print(banner)


def parse_parameters(args: Optional[List[str]] = None) -> Dict[str, Any]:
    """Convenience function to parse parameters."""
    parser = ParameterParser()
    
    # Handle banner request
    if args and '-b' in args:
        parser.print_banner()
        sys.exit(0)
    
    parsed_args = parser.parse_args(args)
    
    if not parser.validate_args():
        sys.exit(1)
    
    return parser.get_parsed_args()


def escape_echo(text: str) -> str:
    """Escape text for safe echo (similar to EMBA's escape_echo function)."""
    if not text:
        return ""
    
    # Escape special characters
    escaped = text.replace('\\', '\\\\')
    escaped = escaped.replace('"', '\\"')
    escaped = escaped.replace("'", "\\'")
    escaped = escaped.replace('`', '\\`')
    escaped = escaped.replace('$', '\\$')
    
    return escaped


def check_int(value: str) -> bool:
    """Check if value is a valid integer."""
    try:
        int(value)
        return True
    except ValueError:
        return False


def check_alnum(value: str) -> bool:
    """Check if value contains only alphanumeric characters."""
    if not value:
        return False
    
    return re.match(r'^[a-zA-Z0-9._-]+$', value) is not None


def check_path_input(value: str) -> bool:
    """Check if path input is valid."""
    if not value:
        return False
    
    # Check for dangerous characters
    dangerous_chars = [';', '&', '|', '`', '$', '(', ')', '<', '>']
    for char in dangerous_chars:
        if char in value:
            return False
    
    return True

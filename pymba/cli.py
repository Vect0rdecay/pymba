#!/usr/bin/env python3
"""
Command-line interface for Pymba.

This module provides the CLI interface compatible with EMBA's
command-line arguments and options.
"""

import os
import sys
import argparse
from pathlib import Path
from .core.config import PymbaConfig
from .core.engine import PymbaEngine
from .core.logger import PymbaLogger


def create_argument_parser():
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        description="Pymba - Python Firmware Security Analyzer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  pymba -f firmware.bin -l logs/
  pymba -f firmware.bin -l logs/ -p default-scan.yaml
  pymba -f firmware.bin -l logs/ -m S10,S20,S30
        """
    )
    
    # Required arguments
    parser.add_argument(
        '-f', '--firmware',
        required=True,
        help='Firmware binary or directory to analyze'
    )
    
    parser.add_argument(
        '-l', '--log-dir',
        required=True,
        help='Directory for log files and reports'
    )
    
    # Optional arguments
    parser.add_argument(
        '-p', '--profile',
        help='Scan profile configuration file'
    )
    
    parser.add_argument(
        '-m', '--modules',
        help='Comma-separated list of specific modules to run'
    )
    
    parser.add_argument(
        '-o', '--output-dir',
        help='Output directory (defaults to firmware path)'
    )
    
    parser.add_argument(
        '-k', '--kernel-config',
        help='Kernel configuration file for analysis'
    )
    
    # Analysis options
    parser.add_argument(
        '--rtos',
        action='store_true',
        help='Enable RTOS analysis mode'
    )
    
    parser.add_argument(
        '--no-threading',
        action='store_true',
        help='Disable multi-threading'
    )
    
    parser.add_argument(
        '--no-html',
        action='store_true',
        help='Disable HTML report generation'
    )
    
    parser.add_argument(
        '--emulation',
        action='store_true',
        help='Enable system emulation (L-modules)'
    )
    
    parser.add_argument(
        '--qemulation',
        action='store_true',
        help='Enable user-mode emulation'
    )
    
    # Firmware metadata
    parser.add_argument(
        '--vendor',
        help='Firmware vendor name'
    )
    
    parser.add_argument(
        '--fw-version',
        help='Firmware version'
    )
    
    parser.add_argument(
        '--device',
        help='Target device name'
    )
    
    parser.add_argument(
        '--notes',
        help='Additional firmware notes'
    )
    
    # Advanced options
    parser.add_argument(
        '--max-threads',
        type=int,
        default=0,
        help='Maximum number of parallel threads (0=auto)'
    )
    
    parser.add_argument(
        '--max-module-threads',
        type=int,
        default=0,
        help='Maximum threads per module (0=auto)'
    )
    
    parser.add_argument(
        '--blacklist',
        help='Comma-separated list of modules to blacklist'
    )
    
    parser.add_argument(
        '--yara-disable',
        action='store_true',
        help='Disable YARA analysis'
    )
    
    parser.add_argument(
        '--binary-extended',
        action='store_true',
        help='Enable extended binary analysis'
    )
    
    parser.add_argument(
        '--max-ext-check-bins',
        type=int,
        default=20,
        help='Maximum binaries for extended analysis'
    )
    
    # Mode options
    parser.add_argument(
        '--diff-mode',
        help='Second firmware file for differential analysis'
    )
    
    parser.add_argument(
        '--kernel-only',
        action='store_true',
        help='Analyze kernel configuration only'
    )
    
    parser.add_argument(
        '--container-extract',
        action='store_true',
        help='Extract from Docker container'
    )
    
    parser.add_argument(
        '--rescan-sbom',
        action='store_true',
        help='Rescan existing SBOM for CVE analysis'
    )
    
    # Debug and development
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode'
    )
    
    parser.add_argument(
        '--no-docker',
        action='store_true',
        help='Disable Docker support'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='Pymba 0.1.0'
    )
    
    return parser


def create_config_from_args(args) -> PymbaConfig:
    """Create configuration from command line arguments."""
    config = PymbaConfig()
    
    # Required arguments
    config.firmware_path = os.path.abspath(args.firmware)
    config.log_dir = os.path.abspath(args.log_dir)
    
    # Optional arguments
    if args.output_dir:
        config.output_dir = os.path.abspath(args.output_dir)
    else:
        config.output_dir = config.firmware_path
    
    if args.kernel_config:
        config.kernel_config = os.path.abspath(args.kernel_config)
        config.kernel = True
    
    # Analysis options
    config.rtos = args.rtos
    config.threaded = not args.no_threading
    config.html_report = not args.no_html
    config.full_emulation = args.emulation
    config.qemulation = args.qemulation
    
    # Firmware metadata
    config.fw_vendor = args.vendor or ""
    config.fw_version = getattr(args, 'fw_version', None) or ""
    config.fw_device = args.device or ""
    config.fw_notes = args.notes or ""
    
    # Advanced options
    if args.max_threads > 0:
        config.max_threads = args.max_threads
    
    if args.max_module_threads > 0:
        config.max_module_threads = args.max_module_threads
    
    if args.blacklist:
        config.module_blacklist = [m.strip() for m in args.blacklist.split(',')]
    
    config.yara_enabled = not args.yara_disable
    config.binary_extended = args.binary_extended
    config.max_ext_check_bins = args.max_ext_check_bins
    
    # Mode options
    if args.diff_mode:
        config.diff_mode = True
        config.firmware_path1 = os.path.abspath(args.diff_mode)
    
    config.kernel = args.kernel_only
    config.container_extract = args.container_extract
    config.rescan_sbom = args.rescan_sbom
    
    # Debug options
    config.debug = args.debug
    config.use_docker = not args.no_docker
    
    # Module selection
    if args.modules:
        config.selected_modules = [m.strip() for m in args.modules.split(',')]
    
    return config


def main():
    """Main entry point for Pymba CLI."""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    try:
        # Create configuration
        config = create_config_from_args(args)
        
        # Load scan profile if specified
        if args.profile:
            if not os.path.exists(args.profile):
                print(f"Error: Profile file not found: {args.profile}")
                sys.exit(1)
            
            profile_config = PymbaConfig.load_from_profile(args.profile)
            # Merge profile config with CLI config
            for key, value in profile_config.__dict__.items():
                if not key.startswith('_') and value is not None:
                    setattr(config, key, value)
        
        # Create and run engine
        engine = PymbaEngine(config)
        engine.run_analysis()
        
    except KeyboardInterrupt:
        print("\nAnalysis interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

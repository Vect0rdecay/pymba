#!/usr/bin/env python3
"""
Main CLI interface for Pymba.

This module provides the command-line interface for Pymba, replacing
the bash-based emba script from EMBA.
"""

import sys
import os
from pathlib import Path
from typing import Optional, List

# Add pymba to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from pymba.core.config_manager import ConfigManager, PymbaConfig
from pymba.core.module_manager import ModuleManager, ModuleCategory
from pymba.helpers.logging_utils import LogManager
from pymba.helpers.parameter_parser import parse_parameters


class PymbaCLI:
    """Main CLI class for Pymba."""
    
    def __init__(self):
        self.config_manager = None
        self.log_manager = None
        self.module_manager = None
        self.args = None
    
    def run(self, args: Optional[List[str]] = None) -> int:
        """Main entry point for Pymba CLI."""
        try:
            # Parse command line arguments
            self.args = parse_parameters(args)
            
            # Handle special commands that don't need full initialization
            if self._handle_special_commands():
                return 0
            
            # Initialize components
            self._initialize_components()
            
            # Validate configuration
            if not self._validate_configuration():
                return 1
            
            # Run analysis
            return self._run_analysis()
            
        except KeyboardInterrupt:
            print("\n\nOperation cancelled by user")
            return 130
        except Exception as e:
            print(f"\nFatal error: {e}")
            if self.log_manager:
                self.log_manager.print_error(f"Fatal error: {e}")
            return 1
    
    def _initialize_components(self):
        """Initialize core components."""
        # Initialize configuration manager
        self.config_manager = ConfigManager(None)  # Will set log_manager later
        
        # Initialize log manager
        log_dir = self.args.get('log_dir', './pymba_logs')
        verbose = self.args.get('verbose', False)
        quiet = self.args.get('quiet', False)
        
        self.log_manager = LogManager(
            log_dir=log_dir,
            enable_colors=not quiet,
            verbose=verbose
        )
        
        # Update config manager with log manager
        self.config_manager.log_manager = self.log_manager
        
        # Initialize module manager
        self.module_manager = ModuleManager(self.log_manager, None)  # Will set config later
    
    def _handle_special_commands(self) -> bool:
        """Handle special commands that don't require full initialization."""
        
        # Show banner
        if self.args.get('banner'):
            self._show_banner()
            return True
        
        # Dependency check
        if self.args.get('only_dep'):
            return self._run_dependency_check()
        
        # Version information
        if self.args.get('version'):
            self._show_version()
            return True
        
        # Help
        if self.args.get('help'):
            self._show_help()
            return True
        
        return False
    
    def _show_banner(self):
        """Show Pymba banner."""
        banner = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║  ██████╗ ██╗   ██╗███╗   ███╗██████╗  █████╗                               ║
║  ██╔══██╗╚██╗ ██╔╝████╗ ████║██╔══██╗██╔══██╗                              ║
║  ██████╔╝ ╚████╔╝ ██╔████╔██║██████╔╝███████║                              ║
║  ██╔═══╝   ╚██╔╝  ██║╚██╔╝██║██╔══██╗██╔══██║                              ║
║  ██║        ██║   ██║ ╚═╝ ██║██████╔╝██║  ██║                              ║
║  ╚═╝        ╚═╝   ╚═╝     ╚═╝╚═════╝ ╚═╝  ╚═╝                              ║
║                                                                              ║
║  Python Firmware Security Analyzer                                          ║
║  A Python port of EMBA (Embedded Linux Analyzer)                            ║
║                                                                              ║
║  Version: 0.1.0                                                             ║
║  Author: Pymba Development Team                                             ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
        print(banner)
    
    def _run_dependency_check(self) -> bool:
        """Run dependency check."""
        from pymba.helpers.dependency_check import check_dependencies
        from pymba.helpers.logging_utils import LogManager
        
        # Initialize a temporary log manager for dependency check
        temp_log_manager = LogManager(
            log_dir='./temp_logs',
            enable_colors=True,
            verbose=self.args.get('verbose', False)
        )
        
        temp_log_manager.print_info("Running dependency check...")
        
        only_dep = self.args.get('dep_check', 1)
        use_docker = not self.args.get('no_docker', False)
        
        success = check_dependencies(
            log_manager=temp_log_manager,
            use_docker=use_docker,
            only_dep=only_dep
        )
        
        if success:
            temp_log_manager.print_success("All dependencies are satisfied")
        else:
            temp_log_manager.print_error("Some dependencies are missing")
        
        return success
    
    def _show_version(self):
        """Show version information."""
        version_info = {
            'pymba_version': '1.0.0',
            'python_version': sys.version,
            'platform': sys.platform
        }
        
        print("Pymba - Python Firmware Security Analyzer")
        print("=" * 50)
        for key, value in version_info.items():
            print(f"{key}: {value}")
    
    def _show_help(self):
        """Show help information."""
        from pymba.helpers.parameter_parser import ParameterParser
        parser = ParameterParser()
        parser.print_help()
    
    def _validate_configuration(self) -> bool:
        """Validate configuration and setup."""
        # Load default configuration
        self.config_manager.load_default_config()
        
        # Update configuration from command line arguments
        self._update_config_from_args()
        
        # Validate configuration
        issues = self.config_manager.validate_config()
        if issues:
            self.log_manager.print_error("Configuration validation failed:")
            for issue in issues:
                self.log_manager.print_error(f"  - {issue}")
            return False
        
        # Create necessary directories
        self._create_directories()
        
        # Update module manager with configuration
        self.module_manager.config = self.config_manager.config
        
        return True
    
    def _update_config_from_args(self):
        """Update configuration from command line arguments."""
        config = self.config_manager.config
        
        # Core paths
        if self.args.get('firmware'):
            config.firmware_path = self.args['firmware']
        if self.args.get('log_dir'):
            config.log_dir = self.args['log_dir']
        
        # Analysis settings
        config.verbose = self.args.get('verbose', False)
        config.debug = self.args.get('debug', False)
        config.quiet = self.args.get('quiet', False)
        config.force = self.args.get('force', False)
        
        # Module execution
        config.max_parallel_modules = self.args.get('threads', 4)
        config.use_multiprocessing = self.args.get('use_multiprocessing', False)
        
        # Architecture
        if self.args.get('arch'):
            config.target_architecture = self.args['arch']
            config.force_architecture = self.args.get('arch_check', 1) == 0
        
        # Exclusions
        if self.args.get('exclude_paths'):
            config.exclude_paths = self.args['exclude_paths']
        
        # Output formats
        config.generate_html = self.args.get('html', False)
        config.generate_json = self.args.get('json', False)
        config.generate_csv = self.args.get('csv', False)
        
        # Security settings
        config.enable_emulation = self.args.get('qemulation', False)
        config.enable_system_emulation = self.args.get('full_emulation', False)
        
        # Docker settings
        config.use_docker = self.args.get('use_docker', True)
        
        # Firmware metadata
        if self.args.get('vendor'):
            config.firmware_vendor = self.args['vendor']
        if self.args.get('version'):
            config.firmware_version = self.args['version']
    
    def _create_directories(self):
        """Create necessary directories."""
        config = self.config_manager.config
        
        directories = [
            config.log_dir,
            config.output_dir,
            config.temp_dir
        ]
        
        for directory in directories:
            if directory:
                Path(directory).mkdir(parents=True, exist_ok=True)
                self.log_manager.print_debug(f"Created directory: {directory}")
    
    def _run_analysis(self) -> int:
        """Run the main analysis."""
        self.log_manager.welcome()
        
        # Discover and load modules
        self.log_manager.print_info("Discovering analysis modules...")
        self.module_manager.discover_modules()
        
        # Load scan profile if specified
        if self.args.get('profile'):
            profile_path = self.args['profile']
            if not self.config_manager.load_scan_profile(profile_path):
                self.log_manager.print_error(f"Failed to load scan profile: {profile_path}")
                return 1
        
        # Determine modules to run
        modules_to_run = self._determine_modules_to_run()
        
        if not modules_to_run:
            self.log_manager.print_error("No modules to run")
            return 1
        
        # Execute modules
        self.log_manager.print_info(f"Running {len(modules_to_run)} modules...")
        
        # Group modules by execution requirements
        sequential_modules = []
        parallel_modules = []
        
        for module_name in modules_to_run:
            module_info = self.module_manager.get_module_info(module_name)
            if module_info and module_info.can_run_parallel:
                parallel_modules.append(module_name)
            else:
                sequential_modules.append(module_name)
        
        # Execute sequential modules first
        if sequential_modules:
            self.log_manager.print_info(f"Running {len(sequential_modules)} sequential modules...")
            results = self.module_manager.execute_module_sequence(sequential_modules)
            self._log_module_results(results)
        
        # Execute parallel modules
        if parallel_modules:
            self.log_manager.print_info(f"Running {len(parallel_modules)} parallel modules...")
            results = self.module_manager.execute_modules_parallel(parallel_modules)
            self._log_module_results(results)
        
        # Generate reports
        self._generate_reports()
        
        # Print summary
        self._print_summary()
        
        return 0
    
    def _determine_modules_to_run(self) -> List[str]:
        """Determine which modules to run based on configuration."""
        # Get all available modules
        all_modules = self.module_manager.list_modules()
        
        # Filter by specific modules if requested
        if self.args.get('modules'):
            requested_modules = self.args['modules']
            modules_to_run = []
            
            for module in requested_modules:
                # Support category selection (e.g., 'p' for all P-modules)
                if len(module) == 1 and module.upper() in ['P', 'S', 'L', 'F', 'Q', 'D']:
                    category = ModuleCategory(module.upper())
                    category_modules = self.module_manager.list_modules(category)
                    modules_to_run.extend(category_modules)
                else:
                    # Specific module
                    if module in all_modules:
                        modules_to_run.append(module)
                    else:
                        self.log_manager.print_warning(f"Module not found: {module}")
            
            return modules_to_run
        
        # Return all modules if no specific selection
        return all_modules
    
    def _log_module_results(self, results: dict):
        """Log module execution results."""
        for module_name, result in results.items():
            if result.status.value == "completed":
                self.log_manager.print_success(f"Module {module_name} completed successfully")
            elif result.status.value == "failed":
                self.log_manager.print_error(f"Module {module_name} failed: {result.error}")
            else:
                self.log_manager.print_warning(f"Module {module_name} status: {result.status.value}")
    
    def _generate_reports(self):
        """Generate output reports."""
        config = self.config_manager.config
        
        if config.generate_html:
            self.log_manager.print_info("Generating HTML report...")
            # TODO: Implement HTML report generation
        
        if config.generate_json:
            self.log_manager.print_info("Generating JSON output...")
            # TODO: Implement JSON output generation
        
        if config.generate_csv:
            self.log_manager.print_info("Generating CSV output...")
            # TODO: Implement CSV output generation
    
    def _print_summary(self):
        """Print execution summary."""
        summary = self.module_manager.get_execution_summary()
        
        self.log_manager.print_info("Analysis Summary")
        self.log_manager.print_info("=" * 50)
        self.log_manager.print_info(f"Total modules: {summary['total']}")
        self.log_manager.print_info(f"Completed: {summary['completed']}")
        self.log_manager.print_info(f"Failed: {summary['failed']}")
        self.log_manager.print_info(f"Skipped: {summary['skipped']}")
        self.log_manager.print_info(f"Total duration: {summary['total_duration']:.2f}s")
        self.log_manager.print_info(f"Average duration: {summary['average_duration']:.2f}s")


def main():
    """Main entry point."""
    cli = PymbaCLI()
    sys.exit(cli.run())


if __name__ == "__main__":
    main()

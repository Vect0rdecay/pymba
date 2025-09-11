#!/usr/bin/env python3
"""
Logging system for Pymba.

This module provides comprehensive logging functionality including
file logging, console output, and web report generation.
"""

import os
import sys
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, Any, Dict
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.text import Text


class PymbaLogger:
    """Enhanced logging system for Pymba with rich console output."""
    
    def __init__(self, log_dir: str, module_name: Optional[str] = None):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup console for rich output
        self.console = Console()
        
        # Main log file
        self.main_log_file = self.log_dir / "pymba.log"
        self.error_log_file = self.log_dir / "pymba_error.log"
        
        # Module-specific log file
        if module_name:
            self.module_log_file = self.log_dir / f"{module_name}.log"
        else:
            self.module_log_file = None
        
        # Setup logging
        self._setup_logging()
        
        # Progress tracking
        self._progress_lock = threading.Lock()
        self._active_progress: Optional[Progress] = None
    
    def _setup_logging(self):
        """Setup logging configuration."""
        # Create formatters
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_formatter = logging.Formatter('%(message)s')
        
        # Setup root logger
        self.logger = logging.getLogger('pymba')
        self.logger.setLevel(logging.DEBUG)
        
        # Clear any existing handlers
        self.logger.handlers.clear()
        
        # File handler for main log
        file_handler = logging.FileHandler(self.main_log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
        
        # File handler for errors
        error_handler = logging.FileHandler(self.error_log_file)
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        self.logger.addHandler(error_handler)
        
        # Module-specific file handler
        if self.module_log_file:
            module_handler = logging.FileHandler(self.module_log_file)
            module_handler.setLevel(logging.DEBUG)
            module_handler.setFormatter(file_formatter)
            self.logger.addHandler(module_handler)
        
        # Console handler with rich formatting
        console_handler = RichHandler(
            console=self.console,
            show_time=True,
            show_path=False,
            rich_tracebacks=True
        )
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
    
    def info(self, message: str, no_log: bool = False):
        """Log info message."""
        if not no_log:
            self.logger.info(message)
        else:
            # Only output to console, not to file
            self.console.print(f"[blue]INFO[/blue]: {message}")
    
    def warning(self, message: str, no_log: bool = False):
        """Log warning message."""
        if not no_log:
            self.logger.warning(message)
        else:
            self.console.print(f"[yellow]WARNING[/yellow]: {message}")
    
    def error(self, message: str, no_log: bool = False):
        """Log error message."""
        if not no_log:
            self.logger.error(message)
        else:
            self.console.print(f"[red]ERROR[/red]: {message}")
    
    def debug(self, message: str, no_log: bool = False):
        """Log debug message."""
        if not no_log:
            self.logger.debug(message)
        else:
            self.console.print(f"[dim]DEBUG[/dim]: {message}")
    
    def success(self, message: str, no_log: bool = False):
        """Log success message."""
        formatted_message = f"[green]SUCCESS[/green]: {message}"
        if not no_log:
            self.logger.info(formatted_message)
        else:
            self.console.print(formatted_message)
    
    def print_output(self, message: str, log_type: str = "main"):
        """Print output with formatting (compatible with EMBA style)."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if log_type == "main":
            formatted = f"[{timestamp}] {message}"
            self.info(formatted)
        elif log_type == "no_log":
            self.console.print(message)
        else:
            formatted = f"[{timestamp}] [{log_type}] {message}"
            self.info(formatted)
    
    def print_bar(self, no_log: bool = False):
        """Print a separator bar."""
        bar = "=" * 65
        if no_log:
            self.console.print(bar)
        else:
            self.info(bar)
    
    def print_ln(self, no_log: bool = False):
        """Print a new line."""
        if no_log:
            self.console.print()
        else:
            self.info("")
    
    def indent(self, text: str, level: int = 1) -> str:
        """Indent text for formatting."""
        indent_str = "    " * level
        return f"{indent_str}{text}"
    
    def print_date(self) -> str:
        """Get formatted current date/time."""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def module_start_log(self, module_name: str):
        """Log module start."""
        self.print_bar()
        self.info(f"Starting module: {module_name}")
        self.print_bar()
    
    def module_end_log(self, module_name: str, exit_code: int = 0):
        """Log module end."""
        status = "completed" if exit_code == 0 else "failed"
        self.info(f"Module {module_name} {status} with exit code {exit_code}")
        self.print_bar()
    
    def start_progress(self, description: str):
        """Start a progress indicator."""
        with self._progress_lock:
            if self._active_progress:
                self._active_progress.stop()
            
            self._active_progress = Progress(
                SpinnerColumn(),
                TextColumn(f"[blue]{description}[/blue]"),
                console=self.console
            )
            self._active_progress.start()
    
    def stop_progress(self):
        """Stop the progress indicator."""
        with self._progress_lock:
            if self._active_progress:
                self._active_progress.stop()
                self._active_progress = None
    
    def print_firmware_info(self, vendor: str, version: str, device: str, notes: str):
        """Print firmware information."""
        info_panel = Panel(
            f"[bold]Vendor:[/bold] {vendor or 'Unknown'}\n"
            f"[bold]Version:[/bold] {version or 'Unknown'}\n"
            f"[bold]Device:[/bold] {device or 'Unknown'}\n"
            f"[bold]Notes:[/bold] {notes or 'None'}",
            title="Firmware Information",
            border_style="blue"
        )
        self.console.print(info_panel)
    
    def write_notification(self, message: str):
        """Write notification (placeholder for future desktop notifications)."""
        self.info(f"NOTIFICATION: {message}")
    
    def strip_color_tags(self, text: str) -> str:
        """Strip ANSI color codes from text."""
        import re
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', text)
    
    def orange(self, text: str) -> str:
        """Format text in orange color."""
        return f"[orange1]{text}[/orange1]"
    
    def green(self, text: str) -> str:
        """Format text in green color."""
        return f"[green]{text}[/green]"
    
    def red(self, text: str) -> str:
        """Format text in red color."""
        return f"[red]{text}[/red]"
    
    def yellow(self, text: str) -> str:
        """Format text in yellow color."""
        return f"[yellow]{text}[/yellow]"
    
    def blue(self, text: str) -> str:
        """Format text in blue color."""
        return f"[blue]{text}[/blue]"
    
    def magenta(self, text: str) -> str:
        """Format text in magenta color."""
        return f"[magenta]{text}[/magenta]"


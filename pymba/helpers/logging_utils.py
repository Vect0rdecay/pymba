#!/usr/bin/env python3
"""
Logging utility functions for Pymba.

This module provides logging functionality ported from EMBA's helpers_emba_print.sh.
It handles colored terminal output, module logging, and status tracking.
"""

import os
import sys
import time
import logging
from typing import Optional, Union, List
from pathlib import Path
from datetime import datetime


class Colors:
    """ANSI color codes for terminal output."""
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    ORANGE = "\033[0;33m"
    BLUE = "\033[0;34m"
    MAGENTA = "\033[0;35m"
    CYAN = "\033[0;36m"
    NC = "\033[0m"  # no color
    
    # Alternative color codes
    RED_ = "\x1b[31m"
    GREEN_ = "\x1b[32m"
    ORANGE_ = "\x1b[33m"
    BLUE_ = "\x1b[34m"
    MAGENTA_ = "\x1b[35m"
    CYAN_ = "\x1b[36m"
    NC_ = "\x1b[0m"


class Attributes:
    """Text attributes for terminal output."""
    BOLD = "\033[1m"
    ITALIC = "\033[3m"


class LogManager:
    """Manages logging for Pymba modules."""
    
    def __init__(self, log_dir: str, module_name: str = "", 
                 enable_colors: bool = True, verbose: bool = False):
        self.log_dir = Path(log_dir)
        self.module_name = module_name
        self.enable_colors = enable_colors
        self.verbose = verbose
        
        # Create log directory if it doesn't exist
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize module-specific log file
        self.log_file = None
        if module_name:
            self.log_file = self.log_dir / f"{module_name.lower().replace(' ', '_')}.txt"
        
        # Status tracking
        self.module_start_time = None
        self.sub_module_count = 0
        
        # Setup logging
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging configuration."""
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Setup root logger
        self.logger = logging.getLogger('pymba')
        self.logger.setLevel(logging.DEBUG if self.verbose else logging.INFO)
        
        # Remove existing handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # File handler (if module name provided)
        if self.log_file:
            file_handler = logging.FileHandler(self.log_file)
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
    
    def welcome(self):
        """Print welcome banner."""
        banner = f"""
{Attributes.BOLD}╔═══════════════════════════════════════════════════════════════╗{Colors.NC}
{Attributes.BOLD}║{Colors.BLUE}{Attributes.BOLD}{Attributes.ITALIC}                            P Y M B A                            {Colors.NC}{Attributes.BOLD}║{Colors.NC}
{Attributes.BOLD}║                   PYTHON FIRMWARE ANALYZER                  {Colors.NC}{Attributes.BOLD}║{Colors.NC}
{Attributes.BOLD}╚═══════════════════════════════════════════════════════════════╝{Colors.NC}
"""
        self.print_output(banner, "no_log")
    
    def print_output(self, message: str, log_type: str = "log"):
        """Print colored output with optional logging."""
        if not self.enable_colors:
            # Strip color codes if colors disabled
            message = self.strip_colors(message)
        
        # Print to console
        print(message, end='', flush=True)
        
        # Log to file if specified
        if log_type != "no_log" and self.log_file:
            # Strip colors for file logging
            clean_message = self.strip_colors(message)
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(clean_message)
    
    def print_ln(self, count: int = 1):
        """Print line breaks."""
        for _ in range(count):
            self.print_output("\n", "no_log")
    
    def print_dot(self):
        """Print a dot for progress indication."""
        self.print_output(".", "no_log")
        sys.stdout.flush()
    
    def print_error(self, message: str):
        """Print error message in red."""
        colored_message = f"{Colors.RED}{message}{Colors.NC}\n"
        self.print_output(colored_message)
    
    def print_warning(self, message: str):
        """Print warning message in orange."""
        colored_message = f"{Colors.ORANGE}{message}{Colors.NC}\n"
        self.print_output(colored_message)
    
    def print_success(self, message: str):
        """Print success message in green."""
        colored_message = f"{Colors.GREEN}{message}{Colors.NC}\n"
        self.print_output(colored_message)
    
    def print_info(self, message: str):
        """Print info message in cyan."""
        colored_message = f"{Colors.CYAN}{message}{Colors.NC}\n"
        self.print_output(colored_message)
    
    def print_debug(self, message: str):
        """Print debug message in blue."""
        if self.verbose:
            colored_message = f"{Colors.BLUE}{message}{Colors.NC}\n"
            self.print_output(colored_message)
    
    def module_title(self, title: str):
        """Print module title with formatting."""
        formatted_title = f"""
{Attributes.BOLD}[{Colors.BLUE}+{Colors.NC}] {Colors.CYAN}{Attributes.BOLD}{title}{Colors.NC}
{Attributes.BOLD}{'='*64}{Colors.NC}
"""
        self.print_output(formatted_title)
        self.sub_module_count = 0
    
    def sub_module_title(self, title: str):
        """Print sub-module title."""
        self.sub_module_count += 1
        formatted_title = f"\n[{Colors.BLUE}+{Colors.NC}] {Colors.CYAN}{self.sub_module_count}. {title}{Colors.NC}\n"
        self.print_output(formatted_title)
    
    def module_start_log(self, module_name: str):
        """Start module logging."""
        self.module_start_time = time.time()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        start_msg = f"\n[{timestamp}] Starting module: {module_name}\n"
        self.print_output(start_msg)
    
    def module_end_log(self, module_name: str, exit_code: int = 0):
        """End module logging."""
        if self.module_start_time:
            duration = time.time() - self.module_start_time
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            status = "SUCCESS" if exit_code == 0 else "FAILED"
            color = Colors.GREEN if exit_code == 0 else Colors.RED
            
            end_msg = f"\n[{timestamp}] Module {module_name} finished: {color}{status}{Colors.NC} (Duration: {duration:.2f}s)\n"
            self.print_output(end_msg)
    
    def write_link(self, filepath: str, text: Optional[str] = None):
        """Write file link to log."""
        if text is None:
            text = filepath
        
        link_msg = f"[REF] {text} -> {filepath}\n"
        self.print_output(link_msg)
    
    def write_anchor(self, anchor: str, text: str):
        """Write anchor reference to log."""
        anchor_msg = f"[ANC] {anchor} -> {text}\n"
        self.print_output(anchor_msg)
    
    def write_log(self, message: str, log_file: Optional[str] = None):
        """Write message to specific log file."""
        target_file = log_file if log_file else self.log_file
        
        if target_file:
            # Strip colors for file logging
            clean_message = self.strip_colors(message)
            with open(target_file, 'a', encoding='utf-8') as f:
                f.write(clean_message)
    
    def format_log(self, message: str) -> str:
        """Format message for logging (strip colors)."""
        return self.strip_colors(message)
    
    def strip_colors(self, text: str) -> str:
        """Strip ANSI color codes from text."""
        import re
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', text)
    
    def create_backup(self, filepath: str) -> Optional[str]:
        """Create backup of existing file."""
        path = Path(filepath)
        if path.exists():
            backup_path = path.with_suffix(f"{path.suffix}.bak.{int(time.time())}")
            try:
                import shutil
                shutil.copy2(path, backup_path)
                return str(backup_path)
            except (OSError, shutil.Error):
                return None
        return None


class StatusBar:
    """Simple status bar for progress indication."""
    
    def __init__(self, total: int, width: int = 50):
        self.total = total
        self.current = 0
        self.width = width
        self.start_time = time.time()
    
    def update(self, current: int, status: str = ""):
        """Update progress bar."""
        self.current = current
        percent = self.current / self.total if self.total > 0 else 0
        filled = int(self.width * percent)
        bar = "█" * filled + "░" * (self.width - filled)
        
        # Calculate ETA
        if self.current > 0:
            elapsed = time.time() - self.start_time
            eta = (elapsed / self.current) * (self.total - self.current)
            eta_str = f"ETA: {eta:.0f}s"
        else:
            eta_str = "ETA: --"
        
        # Print progress bar
        progress_line = f"\r[{bar}] {percent:.1%} ({self.current}/{self.total}) {eta_str}"
        if status:
            progress_line += f" - {status}"
        
        print(progress_line, end='', flush=True)
    
    def finish(self):
        """Finish progress bar."""
        elapsed = time.time() - self.start_time
        print(f"\nCompleted in {elapsed:.2f}s")


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format."""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"


def format_duration(seconds: float) -> str:
    """Format duration in human readable format."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def truncate_string(text: str, max_length: int = 50) -> str:
    """Truncate string to maximum length."""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."

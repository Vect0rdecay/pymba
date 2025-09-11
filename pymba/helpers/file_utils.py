#!/usr/bin/env python3
"""
File utility functions for Pymba.

This module provides file system operations and utilities
ported from EMBA's helper functions.
"""

import os
import hashlib
import mimetypes
from pathlib import Path
from typing import List, Optional, Union


def abs_path(path: str) -> str:
    """Get absolute path from relative path."""
    return os.path.abspath(path)


def check_path_valid(path: str) -> bool:
    """Check if a path is valid and accessible."""
    try:
        return os.path.exists(path) and os.access(path, os.R_OK)
    except (OSError, TypeError):
        return False


def create_log_dir(log_dir: str) -> bool:
    """Create log directory and subdirectories."""
    try:
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        
        # Create common subdirectories
        subdirs = ['firmware', 'html-report', 'json', 'csv', 'txt']
        for subdir in subdirs:
            Path(log_dir, subdir).mkdir(exist_ok=True)
        
        return True
    except OSError as e:
        print(f"Error creating log directory {log_dir}: {e}")
        return False


def get_file_size(filepath: str) -> int:
    """Get file size in bytes."""
    try:
        return os.path.getsize(filepath)
    except OSError:
        return 0


def get_file_hash(filepath: str, algorithm: str = 'sha256') -> Optional[str]:
    """Calculate file hash."""
    try:
        hash_obj = hashlib.new(algorithm)
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()
    except (OSError, ValueError):
        return None


def is_binary_file(filepath: str) -> bool:
    """Check if file is binary."""
    try:
        # Check file extension first
        text_extensions = {
            '.txt', '.log', '.cfg', '.conf', '.ini', '.yaml', '.yml',
            '.json', '.xml', '.html', '.css', '.js', '.py', '.sh',
            '.c', '.h', '.cpp', '.hpp', '.java', '.php', '.rb',
            '.go', '.rs', '.sql', '.md', '.rst'
        }
        
        ext = Path(filepath).suffix.lower()
        if ext in text_extensions:
            return False
        
        # Check MIME type
        mime_type, _ = mimetypes.guess_type(filepath)
        if mime_type and mime_type.startswith('text/'):
            return False
        
        # Check file content
        with open(filepath, 'rb') as f:
            chunk = f.read(1024)
            if b'\0' in chunk:
                return True
        
        # Try to decode as text
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                f.read(1024)
            return False
        except UnicodeDecodeError:
            return True
            
    except (OSError, UnicodeDecodeError):
        return True


def find_files(directory: str, pattern: str = "*", recursive: bool = True) -> List[str]:
    """Find files matching pattern in directory."""
    path = Path(directory)
    if not path.exists():
        return []
    
    try:
        if recursive:
            return [str(p) for p in path.rglob(pattern) if p.is_file()]
        else:
            return [str(p) for p in path.glob(pattern) if p.is_file()]
    except (OSError, PermissionError):
        return []


def find_directories(directory: str, pattern: str = "*", recursive: bool = True) -> List[str]:
    """Find directories matching pattern."""
    path = Path(directory)
    if not path.exists():
        return []
    
    try:
        if recursive:
            return [str(p) for p in path.rglob(pattern) if p.is_dir()]
        else:
            return [str(p) for p in path.glob(pattern) if p.is_dir()]
    except (OSError, PermissionError):
        return []


def copy_file(src: str, dst: str, preserve_attributes: bool = True) -> bool:
    """Copy file with optional attribute preservation."""
    try:
        import shutil
        if preserve_attributes:
            shutil.copy2(src, dst)
        else:
            shutil.copy(src, dst)
        return True
    except (OSError, shutil.Error):
        return False


def move_file(src: str, dst: str) -> bool:
    """Move file to new location."""
    try:
        import shutil
        shutil.move(src, dst)
        return True
    except (OSError, shutil.Error):
        return False


def delete_file(filepath: str) -> bool:
    """Delete file."""
    try:
        os.remove(filepath)
        return True
    except OSError:
        return False


def get_file_permissions(filepath: str) -> Optional[str]:
    """Get file permissions in octal format."""
    try:
        stat_info = os.stat(filepath)
        return oct(stat_info.st_mode)[-3:]
    except OSError:
        return None


def is_executable(filepath: str) -> bool:
    """Check if file is executable."""
    try:
        return os.access(filepath, os.X_OK)
    except OSError:
        return False


def get_file_owner(filepath: str) -> Optional[str]:
    """Get file owner."""
    try:
        import pwd
        stat_info = os.stat(filepath)
        return pwd.getpwuid(stat_info.st_uid).pw_name
    except (OSError, KeyError):
        return None


def get_file_group(filepath: str) -> Optional[str]:
    """Get file group."""
    try:
        import grp
        stat_info = os.stat(filepath)
        return grp.getgrgid(stat_info.st_gid).gr_name
    except (OSError, KeyError):
        return None


def strip_color_tags(text: str) -> str:
    """Strip ANSI color codes from text."""
    import re
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)


def safe_filename(filename: str) -> str:
    """Create safe filename by removing/replacing invalid characters."""
    import re
    # Remove or replace invalid characters
    safe_name = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove leading/trailing spaces and dots
    safe_name = safe_name.strip(' .')
    # Limit length
    if len(safe_name) > 255:
        name, ext = os.path.splitext(safe_name)
        safe_name = name[:255-len(ext)] + ext
    return safe_name


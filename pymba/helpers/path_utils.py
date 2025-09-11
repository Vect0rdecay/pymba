#!/usr/bin/env python3
"""
Path manipulation utilities for Pymba.

This module provides path handling functionality ported from 
EMBA's helpers_emba_path.sh.
"""

import os
import re
from pathlib import Path
from typing import List, Optional, Union


def check_path_valid(path: str) -> bool:
    """Check if a path is valid in the context of pymba."""
    if not path:
        return False
    
    # Check if path starts with valid prefixes
    if not (path.startswith('/') or path.startswith('./') or path.startswith('../')):
        return False
    
    return True


def abs_path(path: str) -> str:
    """Get absolute path from relative path."""
    if not path:
        return path
    
    try:
        return os.path.abspath(path)
    except (OSError, ValueError):
        return path


def print_path(path: str) -> str:
    """Format path for display with attributes."""
    if not path:
        return ""
    
    abs_path_str = abs_path(path)
    return f"{cut_path(path)}{path_attr(path)}"


def cut_path(path: str, short_path: bool = False, log_dir: str = "") -> str:
    """Cut path to appropriate length for display."""
    if not path:
        return ""
    
    abs_path_str = abs_path(path)
    
    if short_path and log_dir:
        # Remove log directory prefix for shorter display
        log_parent = str(Path(log_dir).parent)
        if abs_path_str.startswith(log_parent):
            short_path_str = abs_path_str[len(log_parent):]
            if short_path_str.startswith('/'):
                return f".{short_path_str}"
            else:
                return f"./{short_path_str}"
    
    # Handle double slashes
    if abs_path_str.startswith('//'):
        return abs_path_str[1:]
    
    return abs_path_str


def path_attr(path: str) -> str:
    """Get path attributes (permissions, owner, group)."""
    if not path or not os.path.exists(path):
        return ""
    
    try:
        stat_info = os.stat(path)
        mode = oct(stat_info.st_mode)[-3:]
        owner = get_file_owner(path) or "unknown"
        group = get_file_group(path) or "unknown"
        
        if os.path.islink(path):
            try:
                target = os.readlink(path)
                return f" ({mode} {owner} {group}) -> {target}"
            except OSError:
                return f" ({mode} {owner} {group}) -> [broken link]"
        else:
            return f" ({mode} {owner} {group})"
    except OSError:
        return " (access denied)"


def permission_clean(path: str) -> str:
    """Get clean permission string."""
    if not path or not os.path.exists(path):
        return ""
    
    try:
        stat_info = os.stat(path)
        return oct(stat_info.st_mode)[-3:]
    except OSError:
        return ""


def owner_clean(path: str) -> str:
    """Get clean owner string."""
    return get_file_owner(path) or ""


def group_clean(path: str) -> str:
    """Get clean group string."""
    return get_file_group(path) or ""


def get_file_owner(path: str) -> Optional[str]:
    """Get file owner."""
    try:
        import pwd
        stat_info = os.stat(path)
        return pwd.getpwuid(stat_info.st_uid).pw_name
    except (OSError, KeyError, ImportError):
        return None


def get_file_group(path: str) -> Optional[str]:
    """Get file group."""
    try:
        import grp
        stat_info = os.stat(path)
        return grp.getgrgid(stat_info.st_gid).gr_name
    except (OSError, KeyError, ImportError):
        return None


def set_etc_paths(firmware_path: str, exclude_paths: List[str] = None) -> List[str]:
    """Find all /etc directories in firmware."""
    if not firmware_path or not os.path.exists(firmware_path):
        return []
    
    etc_paths = []
    firmware_path_obj = Path(firmware_path)
    
    try:
        # Find all directories named 'etc' or containing 'etc'
        for path in firmware_path_obj.rglob("*"):
            if path.is_dir():
                path_str = str(path)
                path_name = path.name.lower()
                
                # Check if it's an etc directory
                if (path_name == "etc" or 
                    (path_name.startswith("etc") and "etc" in path_name)):
                    
                    # Apply exclusions
                    if exclude_paths:
                        excluded = False
                        for exclude in exclude_paths:
                            if path_str.startswith(exclude):
                                excluded = True
                                break
                        if excluded:
                            continue
                    
                    etc_paths.append(path_str)
    except (OSError, PermissionError):
        pass
    
    return sorted(etc_paths)


def set_excluded_paths(exclude_list: List[str]) -> List[str]:
    """Process exclude list and return absolute paths."""
    excluded_paths = []
    
    for exclude_entry in exclude_list:
        if exclude_entry:
            abs_exclude = abs_path(exclude_entry)
            if abs_exclude:
                excluded_paths.append(abs_exclude)
    
    return excluded_paths


def get_excluded_find(excluded_paths: List[str]) -> str:
    """Generate find command exclusions."""
    if not excluded_paths:
        return ""
    
    exclusion_parts = []
    for path in excluded_paths:
        exclusion_parts.append(f"-path {path}")
    
    if exclusion_parts:
        return f"-not ( {' -prune -o '.join(exclusion_parts)} -prune )"
    
    return ""


def remove_proc_binary(binaries: List[str], firmware_path: str) -> List[str]:
    """Remove /proc/ binaries from binary list."""
    if not binaries:
        return []
    
    proc_prefix = os.path.join(firmware_path, "proc", "")
    filtered_binaries = []
    removed_count = 0
    
    for binary in binaries:
        if not binary.startswith(proc_prefix):
            filtered_binaries.append(binary)
        else:
            removed_count += 1
    
    if removed_count > 0:
        print(f"[!] {removed_count} executable/s removed (./proc/*)")
    
    return filtered_binaries


def mod_path(path_template: str, etc_paths: List[str] = None, exclude_paths: List[str] = None) -> List[str]:
    """Modify path template with etc paths and exclusions."""
    if not path_template:
        return []
    
    result_paths = []
    
    # Handle ETC_PATHS replacement
    if "/ETC_PATHS" in path_template:
        if etc_paths:
            for etc_path in etc_paths:
                new_path = path_template.replace("/ETC_PATHS", etc_path)
                result_paths.append(new_path)
    else:
        result_paths.append(path_template)
    
    # Apply exclusions
    if exclude_paths:
        filtered_paths = []
        for path in result_paths:
            excluded = False
            for exclude in exclude_paths:
                if path.startswith(exclude):
                    excluded = True
                    break
            if not excluded:
                filtered_paths.append(path)
        result_paths = filtered_paths
    
    return result_paths


def mod_path_array(path_templates: List[str], etc_paths: List[str] = None, exclude_paths: List[str] = None) -> List[str]:
    """Modify array of path templates."""
    result_paths = []
    
    for template in path_templates:
        result_paths.extend(mod_path(template, etc_paths, exclude_paths))
    
    return result_paths


def create_log_dir(log_dir: str) -> bool:
    """Create log directory structure."""
    try:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        
        # Create common subdirectories
        subdirs = ['firmware', 'html-report', 'json', 'csv', 'txt', 'etc']
        for subdir in subdirs:
            (log_path / subdir).mkdir(exist_ok=True)
        
        return True
    except OSError:
        return False


def config_list(config_file: str) -> List[str]:
    """Read configuration list from file."""
    if not config_file or not os.path.isfile(config_file):
        return []
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f if line.strip()]
        return sorted(set(lines))
    except (OSError, UnicodeDecodeError):
        return []


def config_find(config_file: str, firmware_path: str, exclude_paths: List[str] = None) -> List[str]:
    """Find files matching patterns in config file."""
    if not config_file or not os.path.isfile(config_file) or not firmware_path:
        return []
    
    patterns = config_list(config_file)
    if not patterns:
        return []
    
    results = []
    firmware_path_obj = Path(firmware_path)
    
    try:
        for pattern in patterns:
            # Convert pattern to glob format
            if not pattern.startswith('**/'):
                pattern = f"**/{pattern}"
            
            for path in firmware_path_obj.glob(pattern):
                if path.is_file():
                    path_str = str(path)
                    
                    # Handle symlinks
                    if path.is_symlink():
                        try:
                            real_path = path.resolve()
                            if real_path.is_file():
                                path_str = str(real_path)
                        except OSError:
                            pass
                    
                    # Apply exclusions
                    if exclude_paths:
                        excluded = False
                        for exclude in exclude_paths:
                            if path_str.startswith(exclude):
                                excluded = True
                                break
                        if excluded:
                            continue
                    
                    results.append(path_str)
    except (OSError, PermissionError):
        pass
    
    return sorted(set(results))


def config_grep(config_file: str, target_paths: List[str]) -> List[str]:
    """Grep patterns from config file in target files."""
    if not config_file or not os.path.isfile(config_file):
        return []
    
    patterns = config_list(config_file)
    if not patterns or not target_paths:
        return []
    
    results = []
    
    try:
        for target_path in target_paths:
            if not os.path.isfile(target_path):
                continue
            
            # Read file content (for binary files, use strings command)
            try:
                with open(target_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            except (OSError, UnicodeDecodeError):
                # Try using strings command for binary files
                try:
                    import subprocess
                    result = subprocess.run(
                        ['strings', target_path], 
                        capture_output=True, 
                        text=True, 
                        check=False
                    )
                    content = result.stdout
                except (OSError, subprocess.SubprocessError):
                    continue
            
            # Search for patterns
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    results.append(f"{target_path}: {pattern}")
    
    except Exception:
        pass
    
    return results


def config_grep_string(config_file: str, text: str) -> List[str]:
    """Grep patterns from config file in text string."""
    if not config_file or not os.path.isfile(config_file) or not text:
        return []
    
    patterns = config_list(config_file)
    if not patterns:
        return []
    
    results = []
    
    try:
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                results.append(pattern)
    except Exception:
        pass
    
    return results


def safe_filename(filename: str) -> str:
    """Create safe filename by removing/replacing invalid characters."""
    if not filename:
        return "unknown"
    
    # Remove or replace invalid characters
    safe_name = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove leading/trailing spaces and dots
    safe_name = safe_name.strip(' .')
    
    # Handle empty result
    if not safe_name:
        safe_name = "unknown"
    
    # Limit length
    if len(safe_name) > 255:
        name_part, ext_part = os.path.splitext(safe_name)
        max_name_len = 255 - len(ext_part)
        safe_name = name_part[:max_name_len] + ext_part
    
    return safe_name


def get_relative_path(path: str, base_path: str) -> str:
    """Get relative path from base path."""
    try:
        path_obj = Path(path)
        base_obj = Path(base_path)
        return str(path_obj.relative_to(base_obj))
    except ValueError:
        return path


def is_path_relative_to(path: str, base_path: str) -> bool:
    """Check if path is relative to base path."""
    try:
        path_obj = Path(path)
        base_obj = Path(base_path)
        path_obj.relative_to(base_obj)
        return True
    except ValueError:
        return False


def expand_path(path: str) -> str:
    """Expand path with environment variables and user home."""
    if not path:
        return path
    
    # Expand environment variables
    path = os.path.expandvars(path)
    
    # Expand user home
    path = os.path.expanduser(path)
    
    return path


def normalize_path(path: str) -> str:
    """Normalize path by resolving .. and . components."""
    if not path:
        return path
    
    return os.path.normpath(path)


def path_exists(path: str) -> bool:
    """Check if path exists (file or directory)."""
    return os.path.exists(path) if path else False


def is_file(path: str) -> bool:
    """Check if path is a file."""
    return os.path.isfile(path) if path else False


def is_directory(path: str) -> bool:
    """Check if path is a directory."""
    return os.path.isdir(path) if path else False


def is_symlink(path: str) -> bool:
    """Check if path is a symbolic link."""
    return os.path.islink(path) if path else False


def get_file_size(path: str) -> int:
    """Get file size in bytes."""
    try:
        return os.path.getsize(path) if path else 0
    except OSError:
        return 0


def get_directory_size(path: str) -> int:
    """Get total size of directory in bytes."""
    if not path or not os.path.isdir(path):
        return 0
    
    total_size = 0
    try:
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                try:
                    total_size += os.path.getsize(filepath)
                except OSError:
                    pass
    except OSError:
        pass
    
    return total_size

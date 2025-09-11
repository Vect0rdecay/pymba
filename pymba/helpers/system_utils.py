#!/usr/bin/env python3
"""
System utility functions for Pymba.

This module provides system-level operations and utilities
for process management, dependency checking, and system information.
"""

import os
import sys
import subprocess
import platform
import multiprocessing
import psutil
import shutil
from typing import List, Dict, Optional, Tuple, Union


def run_command(command: Union[str, List[str]], 
                cwd: Optional[str] = None,
                timeout: Optional[int] = None,
                capture_output: bool = True) -> Tuple[int, str, str]:
    """
    Run system command and return exit code, stdout, stderr.
    
    Args:
        command: Command to run (string or list)
        cwd: Working directory
        timeout: Command timeout in seconds
        capture_output: Whether to capture stdout/stderr
        
    Returns:
        Tuple of (exit_code, stdout, stderr)
    """
    try:
        if capture_output:
            result = subprocess.run(
                command,
                cwd=cwd,
                timeout=timeout,
                capture_output=True,
                text=True,
                check=False
            )
            return result.returncode, result.stdout, result.stderr
        else:
            result = subprocess.run(
                command,
                cwd=cwd,
                timeout=timeout,
                check=False
            )
            return result.returncode, "", ""
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except (OSError, FileNotFoundError) as e:
        return -1, "", str(e)


def check_command_exists(command: str) -> bool:
    """Check if command exists in PATH."""
    try:
        return shutil.which(command) is not None
    except Exception:
        return False


def _pip_install(package_name: str) -> Tuple[int, str, str]:
    """Attempt to install a Python package into the current interpreter env."""
    try:
        cmd = [sys.executable, '-m', 'pip', 'install', package_name]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return result.returncode, result.stdout, result.stderr
    except Exception as exc:
        return -1, '', str(exc)


def ensure_tools(tools: List[str]) -> Dict[str, bool]:
    """Ensure required external tools are available.

    Checks for system availability first (PATH). If missing, tries to install
    via pip for tools that are available as Python packages.

    Returns a dict mapping tool name to boolean availability after attempts.
    """
    tool_to_pip = {
        'binwalk': 'binwalk',
        'unblob': 'unblob',
    }

    results: Dict[str, bool] = {}
    for tool in tools:
        if check_command_exists(tool):
            results[tool] = True
            continue

        pkg = tool_to_pip.get(tool)
        if pkg:
            code, _, _ = _pip_install(pkg)
            # Re-check PATH; some console scripts are added to the venv bin
            available = (code == 0) and check_command_exists(tool)
            results[tool] = available
        else:
            results[tool] = False

    return results


def get_system_info() -> Dict[str, str]:
    """Get system information."""
    info = {
        'platform': platform.platform(),
        'system': platform.system(),
        'release': platform.release(),
        'version': platform.version(),
        'machine': platform.machine(),
        'processor': platform.processor(),
        'python_version': platform.python_version(),
        'cpu_count': str(multiprocessing.cpu_count()),
        'memory_total': str(psutil.virtual_memory().total),
        'memory_available': str(psutil.virtual_memory().available)
    }
    return info


def get_available_memory() -> int:
    """Get available memory in bytes."""
    return psutil.virtual_memory().available


def get_cpu_count() -> int:
    """Get number of CPU cores."""
    return multiprocessing.cpu_count()


def check_dependencies(dependencies: List[str]) -> Dict[str, bool]:
    """Check if required dependencies are available."""
    results = {}
    for dep in dependencies:
        results[dep] = check_command_exists(dep)
    return results


def setup_environment():
    """Setup environment for analysis."""
    # Set environment variables for analysis tools
    env_vars = {
        'DEBIAN_FRONTEND': 'noninteractive',
        'PYTHONUNBUFFERED': '1',
        'LANG': 'C.UTF-8',
        'LC_ALL': 'C.UTF-8'
    }
    
    for key, value in env_vars.items():
        os.environ[key] = value


def cleanup_environment():
    """Cleanup environment after analysis."""
    # Remove any temporary environment variables if needed
    pass


def is_root() -> bool:
    """Check if running as root."""
    return os.geteuid() == 0


def get_process_info(pid: int) -> Optional[Dict]:
    """Get process information."""
    try:
        process = psutil.Process(pid)
        return {
            'pid': pid,
            'name': process.name(),
            'status': process.status(),
            'cpu_percent': process.cpu_percent(),
            'memory_info': process.memory_info(),
            'create_time': process.create_time()
        }
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return None


def kill_process(pid: int, force: bool = False) -> bool:
    """Kill process by PID."""
    try:
        process = psutil.Process(pid)
        if force:
            process.kill()
        else:
            process.terminate()
        return True
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False


def get_disk_usage(path: str) -> Dict[str, int]:
    """Get disk usage for path."""
    try:
        usage = psutil.disk_usage(path)
        return {
            'total': usage.total,
            'used': usage.used,
            'free': usage.free
        }
    except OSError:
        return {'total': 0, 'used': 0, 'free': 0}


def get_mount_points() -> List[Dict[str, str]]:
    """Get system mount points."""
    mounts = []
    try:
        for mount in psutil.disk_partitions():
            mounts.append({
                'device': mount.device,
                'mountpoint': mount.mountpoint,
                'fstype': mount.fstype,
                'opts': mount.opts
            })
    except OSError:
        pass
    return mounts


def is_wsl() -> bool:
    """Check if running in WSL (Windows Subsystem for Linux)."""
    try:
        with open('/proc/version', 'r') as f:
            version_info = f.read().lower()
            return 'microsoft' in version_info or 'wsl' in version_info
    except (OSError, FileNotFoundError):
        return False


def get_user_info() -> Dict[str, str]:
    """Get current user information."""
    info = {}
    try:
        import pwd
        user = pwd.getpwuid(os.getuid())
        info['username'] = user.pw_name
        info['uid'] = str(user.pw_uid)
        info['gid'] = str(user.pw_gid)
        info['home'] = user.pw_dir
        info['shell'] = user.pw_shell
    except (OSError, KeyError):
        info['username'] = os.environ.get('USER', 'unknown')
        info['uid'] = str(os.getuid())
        info['gid'] = str(os.getgid())
    
    # Check if running with sudo
    info['sudo_user'] = os.environ.get('SUDO_USER', '')
    info['is_sudo'] = bool(info['sudo_user'])
    
    return info


def check_port_available(port: int) -> bool:
    """Check if port is available."""
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(('localhost', port))
            return True
    except OSError:
        return False


def find_free_port(start_port: int = 8000, max_port: int = 65535) -> Optional[int]:
    """Find a free port starting from start_port."""
    import socket
    for port in range(start_port, max_port + 1):
        if check_port_available(port):
            return port
    return None


def get_network_interfaces() -> List[Dict[str, str]]:
    """Get network interface information."""
    interfaces = []
    try:
        for interface, addrs in psutil.net_if_addrs().items():
            for addr in addrs:
                if addr.family == psutil.AF_INET:  # IPv4
                    interfaces.append({
                        'interface': interface,
                        'address': addr.address,
                        'netmask': addr.netmask,
                        'broadcast': addr.broadcast
                    })
                    break
    except OSError:
        pass
    return interfaces


def cleanup_processes(process_list: List[int]):
    """Cleanup list of processes."""
    for pid in process_list:
        kill_process(pid, force=True)


def store_kill_pids(pid: int):
    """Store PID for later cleanup (placeholder for future implementation)."""
    # This would maintain a list of PIDs to cleanup
    pass


def max_pids_protection(max_pids: int, wait_pids: List[int]):
    """Limit number of concurrent processes."""
    while len(wait_pids) >= max_pids:
        # Wait for one process to complete
        # This is a simplified implementation
        import time
        time.sleep(0.1)

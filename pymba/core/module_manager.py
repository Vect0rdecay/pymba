#!/usr/bin/env python3
"""
Module Manager for Pymba.

This module provides the core functionality for loading, managing, and executing
analysis modules in Pymba. It replaces the bash-based module execution system
from EMBA.
"""

import os
import sys
import importlib
import inspect
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Type, Any, Callable
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from enum import Enum

from ..helpers.logging_utils import LogManager
from ..helpers.system_utils import get_cpu_count


class ModuleCategory(Enum):
    """Module categories matching EMBA's structure."""
    P = "Pre-checking/Extraction"
    S = "Security Analysis"
    L = "Live Emulation"
    F = "Final Reporting"
    Q = "AI-powered Analysis"
    D = "Differential Analysis"


class ModuleStatus(Enum):
    """Module execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ModuleInfo:
    """Information about a module."""
    name: str
    category: ModuleCategory
    priority: int
    dependencies: List[str]
    can_run_parallel: bool
    max_threads: int
    timeout: Optional[int]
    enabled: bool
    description: str


class ModuleResult:
    """Result of module execution."""
    
    def __init__(self, module_name: str, status: ModuleStatus, 
                 exit_code: int = 0, output: str = "", error: str = "", 
                 duration: float = 0.0):
        self.module_name = module_name
        self.status = status
        self.exit_code = exit_code
        self.output = output
        self.error = error
        self.duration = duration
        self.start_time = None
        self.end_time = None
        self.thread_id = None


class ModuleManager:
    """Manages loading and execution of analysis modules."""
    
    def __init__(self, log_manager: LogManager, config: Any):
        self.log_manager = log_manager
        self.config = config
        
        # Module registry
        self.modules: Dict[str, Type] = {}
        self.module_info: Dict[str, ModuleInfo] = {}
        self.module_results: Dict[str, ModuleResult] = {}
        
        # Execution control
        self.max_parallel_modules = getattr(config, 'max_parallel_modules', 4)
        self.max_threads_per_module = getattr(config, 'max_threads_per_module', 2)
        self.use_multiprocessing = getattr(config, 'use_multiprocessing', False)
        
        # Module paths
        self.module_paths = {
            ModuleCategory.P: Path(__file__).parent.parent / "modules" / "p_modules",
            ModuleCategory.S: Path(__file__).parent.parent / "modules" / "s_modules", 
            ModuleCategory.L: Path(__file__).parent.parent / "modules" / "l_modules",
            ModuleCategory.F: Path(__file__).parent.parent / "modules" / "f_modules",
            ModuleCategory.Q: Path(__file__).parent.parent / "modules" / "q_modules",
            ModuleCategory.D: Path(__file__).parent.parent / "modules" / "d_modules"
        }
        
        # Execution state
        self._execution_lock = threading.Lock()
        self._running_modules: Dict[str, threading.Thread] = {}
        
    def discover_modules(self) -> Dict[str, ModuleInfo]:
        """Discover all available modules in the module directories."""
        self.log_manager.info("Discovering available modules...")
        
        discovered_modules = {}
        
        for category, module_path in self.module_paths.items():
            if not module_path.exists():
                self.log_manager.warning(f"Module path does not exist: {module_path}")
                continue
            
            # Look for Python module files
            for module_file in module_path.glob("*.py"):
                if module_file.name.startswith("__"):
                    continue
                
                module_name = module_file.stem
                
                try:
                    # Import the module
                    module_class = self._load_module_class(module_path, module_file)
                    if module_class:
                        # Use the actual class name instead of file name
                        class_name = module_class.__name__
                        # Extract module information
                        module_info = self._extract_module_info(module_class, category, class_name)
                        discovered_modules[class_name] = module_info
                        self.modules[class_name] = module_class
                        self.module_info[class_name] = module_info
                        
                        self.log_manager.debug(f"Discovered module: {class_name}")
                
                except Exception as e:
                    self.log_manager.warning(f"Failed to load module {module_name}: {e}")
        
        self.log_manager.success(f"Discovered {len(discovered_modules)} modules")
        return discovered_modules
    
    def _load_module_class(self, module_path: Path, module_file: Path) -> Optional[Type]:
        """Load a module class from a Python file."""
        try:
            # Add pymba root to Python path
            pymba_root = str(module_path.parent.parent.parent)
            if pymba_root not in sys.path:
                sys.path.insert(0, pymba_root)
            
            # Import the module using correct path
            module_name = f"pymba.modules.{module_path.name}.{module_file.stem}"
            module = importlib.import_module(module_name)
            
            # Find the module class (should be the main class in the module)
            for name, obj in inspect.getmembers(module, inspect.isclass):
                # Look for classes that have a 'run' method and are defined in this module
                # Skip base classes and imported classes
                if (hasattr(obj, 'run') and 
                    obj.__module__ == module_name and
                    not name.startswith('Base') and
                    name != 'Path'):
                    return obj
            
            return None
            
        except Exception as e:
            self.log_manager.debug(f"Error loading module class from {module_file}: {e}")
            return None
    
    def _extract_module_info(self, module_class: Type, category: ModuleCategory, 
                           full_name: str) -> ModuleInfo:
        """Extract module information from a module class."""
        
        # Default values
        priority = 100
        dependencies = []
        can_run_parallel = True
        max_threads = 1
        timeout = None
        enabled = True
        description = ""
        
        # Try to extract information from class attributes or metadata
        if hasattr(module_class, 'MODULE_INFO'):
            info = module_class.MODULE_INFO
            priority = info.get('priority', priority)
            dependencies = info.get('dependencies', dependencies)
            can_run_parallel = info.get('can_run_parallel', can_run_parallel)
            max_threads = info.get('max_threads', max_threads)
            timeout = info.get('timeout', timeout)
            enabled = info.get('enabled', enabled)
            description = info.get('description', description)
        
        # Extract from docstring
        if not description and module_class.__doc__:
            description = module_class.__doc__.strip().split('\n')[0]
        
        # Extract from module number in name (e.g., P02, S10)
        if full_name[1:].isdigit():
            priority = int(full_name[1:])
        
        return ModuleInfo(
            name=full_name,
            category=category,
            priority=priority,
            dependencies=dependencies,
            can_run_parallel=can_run_parallel,
            max_threads=max_threads,
            timeout=timeout,
            enabled=enabled,
            description=description
        )
    
    def register_module(self, name: str, module_class: Type, module_info: ModuleInfo):
        """Register a module manually."""
        self.modules[name] = module_class
        self.module_info[name] = module_info
        self.log_manager.debug(f"Registered module: {name}")
    
    def get_module(self, name: str) -> Optional[Type]:
        """Get a module class by name."""
        return self.modules.get(name)
    
    def get_module_info(self, name: str) -> Optional[ModuleInfo]:
        """Get module information by name."""
        return self.module_info.get(name)
    
    def list_modules(self, category: Optional[ModuleCategory] = None) -> List[str]:
        """List available modules, optionally filtered by category."""
        blacklist = getattr(self.config, 'module_blacklist', [])
        
        if category:
            result = [name for name, info in self.module_info.items() 
                     if info.category == category and info.enabled and name not in blacklist]
            self.log_manager.debug(f"list_modules({category.name}): found {len(result)} modules, blacklist={blacklist}")
            return result
        return [name for name, info in self.module_info.items() 
               if info.enabled and name not in blacklist]
    
    def execute_module(self, module_name: str, **kwargs) -> ModuleResult:
        """Execute a single module."""
        if module_name not in self.modules:
            return ModuleResult(
                module_name, ModuleStatus.FAILED, 
                error=f"Module {module_name} not found"
            )
        
        module_class = self.modules[module_name]
        module_info = self.module_info[module_name]
        
        self.log_manager.info(f"Executing module: {module_name}")
        
        # Create module instance
        try:
            module_instance = module_class(self.config, self.log_manager)
        except Exception as e:
            return ModuleResult(
                module_name, ModuleStatus.FAILED,
                error=f"Failed to create module instance: {e}"
            )
        
        # Execute module
        start_time = time.time()
        result = ModuleResult(module_name, ModuleStatus.RUNNING)
        result.start_time = start_time
        result.thread_id = threading.current_thread().ident
        
        try:
            # Set timeout if specified
            if module_info.timeout:
                # This would need to be implemented with threading or subprocess
                pass
            
            # Execute the module
            exit_code = module_instance.run(**kwargs)
            result.exit_code = exit_code
            result.status = ModuleStatus.COMPLETED if exit_code == 0 else ModuleStatus.FAILED
            
        except Exception as e:
            result.status = ModuleStatus.FAILED
            result.error = str(e)
            self.log_manager.error(f"Module {module_name} failed: {e}")
        
        finally:
            result.end_time = time.time()
            result.duration = result.end_time - start_time
            self.module_results[module_name] = result
        
        return result
    
    def execute_modules_parallel(self, module_names: List[str], 
                               max_workers: Optional[int] = None) -> Dict[str, ModuleResult]:
        """Execute multiple modules in parallel."""
        if not module_names:
            return {}
        
        # Filter to only enabled modules
        enabled_modules = [name for name in module_names 
                          if name in self.module_info and self.module_info[name].enabled]
        
        if not enabled_modules:
            self.log_manager.warning("No enabled modules to execute")
            return {}
        
        self.log_manager.info(f"Executing {len(enabled_modules)} modules in parallel")
        
        # Determine execution strategy
        if self.use_multiprocessing:
            return self._execute_modules_multiprocess(enabled_modules, max_workers)
        else:
            return self._execute_modules_multithread(enabled_modules, max_workers)
    
    def _execute_modules_multithread(self, module_names: List[str], 
                                   max_workers: Optional[int] = None) -> Dict[str, ModuleResult]:
        """Execute modules using threading."""
        if max_workers is None:
            max_workers = min(self.max_parallel_modules, len(module_names))
        
        results = {}
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all modules
            future_to_module = {
                executor.submit(self.execute_module, name): name 
                for name in module_names
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_module):
                module_name = future_to_module[future]
                try:
                    result = future.result()
                    results[module_name] = result
                    self.log_manager.debug(f"Module {module_name} completed with status: {result.status}")
                except Exception as e:
                    results[module_name] = ModuleResult(
                        module_name, ModuleStatus.FAILED,
                        error=f"Execution failed: {e}"
                    )
        
        return results
    
    def _execute_modules_multiprocess(self, module_names: List[str], 
                                    max_workers: Optional[int] = None) -> Dict[str, ModuleResult]:
        """Execute modules using multiprocessing."""
        if max_workers is None:
            max_workers = min(self.max_parallel_modules, len(module_names))
        
        results = {}
        
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Submit all modules
            future_to_module = {
                executor.submit(self._execute_module_process, name): name 
                for name in module_names
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_module):
                module_name = future_to_module[future]
                try:
                    result = future.result()
                    results[module_name] = result
                    self.log_manager.debug(f"Module {module_name} completed with status: {result.status}")
                except Exception as e:
                    results[module_name] = ModuleResult(
                        module_name, ModuleStatus.FAILED,
                        error=f"Execution failed: {e}"
                    )
        
        return results
    
    def _execute_module_process(self, module_name: str) -> ModuleResult:
        """Execute a module in a separate process."""
        # This would need to be implemented to handle process isolation
        # For now, fall back to thread execution
        return self.execute_module(module_name)
    
    def execute_module_sequence(self, module_names: List[str]) -> Dict[str, ModuleResult]:
        """Execute modules sequentially in order."""
        results = {}
        
        for module_name in module_names:
            if module_name in self.module_info and not self.module_info[module_name].enabled:
                self.log_manager.debug(f"Skipping disabled module: {module_name}")
                continue
            
            result = self.execute_module(module_name)
            results[module_name] = result
            
            # Stop on critical failure
            if result.status == ModuleStatus.FAILED and result.exit_code != 0:
                self.log_manager.error(f"Critical failure in module {module_name}, stopping sequence")
                break
        
        return results
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get summary of module execution results."""
        if not self.module_results:
            return {"total": 0, "completed": 0, "failed": 0, "duration": 0.0}
        
        total = len(self.module_results)
        completed = sum(1 for r in self.module_results.values() 
                       if r.status == ModuleStatus.COMPLETED)
        failed = sum(1 for r in self.module_results.values() 
                    if r.status == ModuleStatus.FAILED)
        total_duration = sum(r.duration for r in self.module_results.values())
        
        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "skipped": total - completed - failed,
            "total_duration": total_duration,
            "average_duration": total_duration / total if total > 0 else 0.0
        }
    
    def clear_results(self):
        """Clear all module execution results."""
        self.module_results.clear()
    
    def get_module_result(self, module_name: str) -> Optional[ModuleResult]:
        """Get execution result for a specific module."""
        return self.module_results.get(module_name)
    
    def run_module_group(self, category: str, threaded: bool = True) -> List[int]:
        """Run all modules in a specific category."""
        # Map category letters to full names
        category_map = {
            'P': ModuleCategory.P,
            'S': ModuleCategory.S,
            'L': ModuleCategory.L,
            'F': ModuleCategory.F,
            'Q': ModuleCategory.Q,
            'D': ModuleCategory.D
        }
        
        if category not in category_map:
            self.log_manager.error(f"Invalid category: {category}")
            return []
        
        category_enum = category_map[category]
        module_names = self.list_modules(category_enum)
        
        if not module_names:
            self.log_manager.warning(f"No modules found for category {category}")
            return []
        
        # Sort modules by priority
        module_names.sort(key=lambda name: self.module_info[name].priority)
        
        self.log_manager.info(f"Running {len(module_names)} modules in category {category}")
        
        if threaded:
            # Run modules in parallel
            results = self.execute_modules_parallel(module_names)
        else:
            # Run modules sequentially
            results = self.execute_module_sequence(module_names)
        
        # Return exit codes
        return [results[name].exit_code for name in module_names if name in results]
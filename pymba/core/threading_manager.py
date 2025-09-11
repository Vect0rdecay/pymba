#!/usr/bin/env python3
"""
Threading Manager for Pymba.

This module provides advanced threading and multiprocessing management
for parallel module execution, replacing the bash-based parallel execution
from EMBA.
"""

import os
import sys
import time
import threading
import multiprocessing
import queue
import signal
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass
from enum import Enum
import psutil

from ..helpers.logging_utils import LogManager


class ExecutionMode(Enum):
    """Execution modes for modules."""
    SEQUENTIAL = "sequential"
    THREADING = "threading"
    MULTIPROCESSING = "multiprocessing"
    HYBRID = "hybrid"


@dataclass
class ExecutionConfig:
    """Configuration for module execution."""
    mode: ExecutionMode = ExecutionMode.THREADING
    max_workers: Optional[int] = None
    max_threads_per_module: int = 1
    timeout: Optional[int] = None
    retry_count: int = 0
    retry_delay: float = 1.0
    resource_limits: Optional[Dict[str, Any]] = None


@dataclass
class ExecutionResult:
    """Result of module execution."""
    module_name: str
    success: bool
    exit_code: int = 0
    output: str = ""
    error: str = ""
    duration: float = 0.0
    retry_count: int = 0
    worker_id: Optional[str] = None


class ResourceMonitor:
    """Monitor system resources during execution."""
    
    def __init__(self, log_manager: LogManager):
        self.log_manager = log_manager
        self.monitoring = False
        self.monitor_thread = None
        self.resource_data = []
        
    def start_monitoring(self, interval: float = 1.0):
        """Start resource monitoring."""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval,),
            daemon=True
        )
        self.monitor_thread.start()
        self.log_manager.print_debug("Resource monitoring started")
    
    def stop_monitoring(self):
        """Stop resource monitoring."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2.0)
        self.log_manager.print_debug("Resource monitoring stopped")
    
    def _monitor_loop(self, interval: float):
        """Resource monitoring loop."""
        while self.monitoring:
            try:
                # Get system resource usage
                cpu_percent = psutil.cpu_percent(interval=0.1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                
                resource_data = {
                    'timestamp': time.time(),
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'memory_available': memory.available,
                    'disk_percent': disk.percent,
                    'disk_free': disk.free
                }
                
                self.resource_data.append(resource_data)
                
                # Keep only last 1000 entries
                if len(self.resource_data) > 1000:
                    self.resource_data = self.resource_data[-1000:]
                
                time.sleep(interval)
                
            except Exception as e:
                self.log_manager.print_warning(f"Resource monitoring error: {e}")
                time.sleep(interval)
    
    def get_resource_summary(self) -> Dict[str, Any]:
        """Get resource usage summary."""
        if not self.resource_data:
            return {}
        
        cpu_values = [d['cpu_percent'] for d in self.resource_data]
        memory_values = [d['memory_percent'] for d in self.resource_data]
        
        return {
            'cpu_avg': sum(cpu_values) / len(cpu_values),
            'cpu_max': max(cpu_values),
            'memory_avg': sum(memory_values) / len(memory_values),
            'memory_max': max(memory_values),
            'samples': len(self.resource_data)
        }


class ThreadingManager:
    """Manages threading and multiprocessing for module execution."""
    
    def __init__(self, log_manager: LogManager):
        self.log_manager = log_manager
        self.execution_config = ExecutionConfig()
        self.resource_monitor = ResourceMonitor(log_manager)
        
        # Execution state
        self.active_executors: Dict[str, Union[ThreadPoolExecutor, ProcessPoolExecutor]] = {}
        self.execution_results: Dict[str, ExecutionResult] = {}
        self.execution_lock = threading.Lock()
        
        # Performance tracking
        self.performance_stats = {
            'total_executions': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'total_duration': 0.0,
            'average_duration': 0.0
        }
    
    def configure_execution(self, config: ExecutionConfig):
        """Configure execution parameters."""
        self.execution_config = config
        
        # Set default max_workers if not specified
        if config.max_workers is None:
            if config.mode == ExecutionMode.THREADING:
                config.max_workers = min(4, multiprocessing.cpu_count())
            elif config.mode == ExecutionMode.MULTIPROCESSING:
                config.max_workers = multiprocessing.cpu_count()
        
        self.log_manager.print_info(f"Configured execution: {config.mode.value}, max_workers={config.max_workers}")
    
    def execute_modules(self, modules: List[str], 
                       module_executor: Callable[[str], ExecutionResult]) -> Dict[str, ExecutionResult]:
        """Execute multiple modules using configured execution mode."""
        if not modules:
            return {}
        
        self.log_manager.print_info(f"Executing {len(modules)} modules using {self.execution_config.mode.value}")
        
        # Start resource monitoring
        if self.execution_config.mode in [ExecutionMode.THREADING, ExecutionMode.MULTIPROCESSING]:
            self.resource_monitor.start_monitoring()
        
        try:
            if self.execution_config.mode == ExecutionMode.SEQUENTIAL:
                results = self._execute_sequential(modules, module_executor)
            elif self.execution_config.mode == ExecutionMode.THREADING:
                results = self._execute_threading(modules, module_executor)
            elif self.execution_config.mode == ExecutionMode.MULTIPROCESSING:
                results = self._execute_multiprocessing(modules, module_executor)
            elif self.execution_config.mode == ExecutionMode.HYBRID:
                results = self._execute_hybrid(modules, module_executor)
            else:
                raise ValueError(f"Unknown execution mode: {self.execution_config.mode}")
            
            # Update performance stats
            self._update_performance_stats(results)
            
            return results
            
        finally:
            # Stop resource monitoring
            self.resource_monitor.stop_monitoring()
    
    def _execute_sequential(self, modules: List[str], 
                          module_executor: Callable[[str], ExecutionResult]) -> Dict[str, ExecutionResult]:
        """Execute modules sequentially."""
        results = {}
        
        for module_name in modules:
            self.log_manager.print_debug(f"Executing module sequentially: {module_name}")
            
            result = self._execute_with_retry(module_name, module_executor)
            results[module_name] = result
            
            # Stop on critical failure if configured
            if not result.success and result.exit_code != 0:
                self.log_manager.print_error(f"Critical failure in module {module_name}, stopping execution")
                break
        
        return results
    
    def _execute_threading(self, modules: List[str], 
                         module_executor: Callable[[str], ExecutionResult]) -> Dict[str, ExecutionResult]:
        """Execute modules using threading."""
        results = {}
        executor_id = f"threading_{int(time.time())}"
        
        with ThreadPoolExecutor(max_workers=self.execution_config.max_workers) as executor:
            self.active_executors[executor_id] = executor
            
            try:
                # Submit all modules
                future_to_module = {
                    executor.submit(self._execute_with_retry, module_name, module_executor): module_name
                    for module_name in modules
                }
                
                # Collect results as they complete
                for future in as_completed(future_to_module):
                    module_name = future_to_module[future]
                    try:
                        result = future.result(timeout=self.execution_config.timeout)
                        results[module_name] = result
                        self.log_manager.print_debug(f"Module {module_name} completed with threading")
                    except Exception as e:
                        results[module_name] = ExecutionResult(
                            module_name=module_name,
                            success=False,
                            error=f"Threading execution failed: {e}"
                        )
                        self.log_manager.print_error(f"Module {module_name} failed in threading: {e}")
            
            finally:
                if executor_id in self.active_executors:
                    del self.active_executors[executor_id]
        
        return results
    
    def _execute_multiprocessing(self, modules: List[str], 
                               module_executor: Callable[[str], ExecutionResult]) -> Dict[str, ExecutionResult]:
        """Execute modules using multiprocessing."""
        results = {}
        executor_id = f"multiprocessing_{int(time.time())}"
        
        with ProcessPoolExecutor(max_workers=self.execution_config.max_workers) as executor:
            self.active_executors[executor_id] = executor
            
            try:
                # Submit all modules
                future_to_module = {
                    executor.submit(self._execute_module_process, module_name, module_executor): module_name
                    for module_name in modules
                }
                
                # Collect results as they complete
                for future in as_completed(future_to_module):
                    module_name = future_to_module[future]
                    try:
                        result = future.result(timeout=self.execution_config.timeout)
                        results[module_name] = result
                        self.log_manager.print_debug(f"Module {module_name} completed with multiprocessing")
                    except Exception as e:
                        results[module_name] = ExecutionResult(
                            module_name=module_name,
                            success=False,
                            error=f"Multiprocessing execution failed: {e}"
                        )
                        self.log_manager.print_error(f"Module {module_name} failed in multiprocessing: {e}")
            
            finally:
                if executor_id in self.active_executors:
                    del self.active_executors[executor_id]
        
        return results
    
    def _execute_hybrid(self, modules: List[str], 
                       module_executor: Callable[[str], ExecutionResult]) -> Dict[str, ExecutionResult]:
        """Execute modules using hybrid threading/multiprocessing approach."""
        # Group modules by resource requirements
        cpu_intensive = []
        io_intensive = []
        
        for module_name in modules:
            # Simple heuristic - can be improved with module metadata
            if any(keyword in module_name.lower() for keyword in ['extract', 'analyze', 'scan']):
                cpu_intensive.append(module_name)
            else:
                io_intensive.append(module_name)
        
        results = {}
        
        # Execute CPU-intensive modules with multiprocessing
        if cpu_intensive:
            self.log_manager.print_info(f"Executing {len(cpu_intensive)} CPU-intensive modules with multiprocessing")
            cpu_results = self._execute_multiprocessing(cpu_intensive, module_executor)
            results.update(cpu_results)
        
        # Execute I/O-intensive modules with threading
        if io_intensive:
            self.log_manager.print_info(f"Executing {len(io_intensive)} I/O-intensive modules with threading")
            io_results = self._execute_threading(io_intensive, module_executor)
            results.update(io_results)
        
        return results
    
    def _execute_with_retry(self, module_name: str, 
                           module_executor: Callable[[str], ExecutionResult]) -> ExecutionResult:
        """Execute module with retry logic."""
        last_result = None
        
        for attempt in range(self.execution_config.retry_count + 1):
            if attempt > 0:
                self.log_manager.print_info(f"Retrying module {module_name} (attempt {attempt + 1})")
                time.sleep(self.execution_config.retry_delay * attempt)
            
            start_time = time.time()
            result = module_executor(module_name)
            result.duration = time.time() - start_time
            result.retry_count = attempt
            
            if result.success:
                return result
            
            last_result = result
            
            # Don't retry on certain types of failures
            if result.exit_code in [1, 2, 126, 127]:  # Common failure codes
                break
        
        return last_result or ExecutionResult(
            module_name=module_name,
            success=False,
            error="Execution failed after all retries"
        )
    
    def _execute_module_process(self, module_name: str, 
                              module_executor: Callable[[str], ExecutionResult]) -> ExecutionResult:
        """Execute module in separate process."""
        # This is a simplified implementation
        # In a real implementation, you'd need to handle process isolation
        # and serialization of the module_executor function
        
        try:
            result = module_executor(module_name)
            result.worker_id = f"process_{os.getpid()}"
            return result
        except Exception as e:
            return ExecutionResult(
                module_name=module_name,
                success=False,
                error=f"Process execution failed: {e}",
                worker_id=f"process_{os.getpid()}"
            )
    
    def _update_performance_stats(self, results: Dict[str, ExecutionResult]):
        """Update performance statistics."""
        with self.execution_lock:
            total_duration = sum(result.duration for result in results.values())
            successful = sum(1 for result in results.values() if result.success)
            failed = len(results) - successful
            
            self.performance_stats['total_executions'] += len(results)
            self.performance_stats['successful_executions'] += successful
            self.performance_stats['failed_executions'] += failed
            self.performance_stats['total_duration'] += total_duration
            
            if self.performance_stats['total_executions'] > 0:
                self.performance_stats['average_duration'] = (
                    self.performance_stats['total_duration'] / 
                    self.performance_stats['total_executions']
                )
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        with self.execution_lock:
            stats = self.performance_stats.copy()
        
        # Add resource usage stats
        resource_summary = self.resource_monitor.get_resource_summary()
        stats['resource_usage'] = resource_summary
        
        return stats
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get execution summary."""
        return {
            'active_executors': len(self.active_executors),
            'execution_mode': self.execution_config.mode.value,
            'max_workers': self.execution_config.max_workers,
            'performance_stats': self.get_performance_stats()
        }
    
    def cancel_all_executions(self):
        """Cancel all active executions."""
        self.log_manager.print_warning("Cancelling all active executions...")
        
        for executor_id, executor in self.active_executors.items():
            try:
                executor.shutdown(wait=False)
                self.log_manager.print_debug(f"Cancelled executor: {executor_id}")
            except Exception as e:
                self.log_manager.print_error(f"Error cancelling executor {executor_id}: {e}")
        
        self.active_executors.clear()
    
    def cleanup(self):
        """Cleanup resources."""
        self.cancel_all_executions()
        self.resource_monitor.stop_monitoring()
        self.log_manager.print_debug("Threading manager cleaned up")


class ProcessManager:
    """Manages process lifecycle and resource limits."""
    
    def __init__(self, log_manager: LogManager):
        self.log_manager = log_manager
        self.process_limits = {}
    
    def set_process_limits(self, limits: Dict[str, Any]):
        """Set process resource limits."""
        self.process_limits = limits
        self.log_manager.print_debug(f"Set process limits: {limits}")
    
    def apply_process_limits(self, pid: int):
        """Apply resource limits to a process."""
        try:
            process = psutil.Process(pid)
            
            if 'memory_limit' in self.process_limits:
                # Set memory limit (requires appropriate privileges)
                memory_limit = self.process_limits['memory_limit']
                self.log_manager.print_debug(f"Setting memory limit for PID {pid}: {memory_limit}")
            
            if 'cpu_limit' in self.process_limits:
                # Set CPU affinity
                cpu_limit = self.process_limits['cpu_limit']
                if isinstance(cpu_limit, int):
                    cpu_affinity = list(range(min(cpu_limit, psutil.cpu_count())))
                    process.cpu_affinity(cpu_affinity)
                    self.log_manager.print_debug(f"Set CPU affinity for PID {pid}: {cpu_affinity}")
        
        except (psutil.NoSuchProcess, psutil.AccessDenied, OSError) as e:
            self.log_manager.print_warning(f"Could not apply limits to PID {pid}: {e}")
    
    def monitor_process(self, pid: int, callback: Optional[Callable] = None):
        """Monitor a process and execute callback on completion."""
        def monitor_loop():
            try:
                process = psutil.Process(pid)
                process.wait()
                if callback:
                    callback(pid, process.returncode)
            except psutil.NoSuchProcess:
                self.log_manager.print_debug(f"Process {pid} no longer exists")
            except Exception as e:
                self.log_manager.print_error(f"Error monitoring process {pid}: {e}")
        
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
        return monitor_thread

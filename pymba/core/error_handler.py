#!/usr/bin/env python3
"""
Error Handling System for Pymba.

This module provides comprehensive error handling and recovery mechanisms
for Pymba, replacing the bash-based error handling from EMBA.
"""

import os
import sys
import traceback
import logging
import signal
import threading
import time
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import functools

from ..helpers.logging_utils import LogManager


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories."""
    CONFIGURATION = "configuration"
    DEPENDENCY = "dependency"
    MODULE = "module"
    SYSTEM = "system"
    NETWORK = "network"
    PERMISSION = "permission"
    RESOURCE = "resource"
    TIMEOUT = "timeout"
    VALIDATION = "validation"
    UNKNOWN = "unknown"


@dataclass
class ErrorInfo:
    """Information about an error."""
    error_type: str
    message: str
    severity: ErrorSeverity
    category: ErrorCategory
    module_name: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    traceback: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    recoverable: bool = True
    retry_count: int = 0
    max_retries: int = 3


class ErrorRecoveryStrategy:
    """Base class for error recovery strategies."""
    
    def can_recover(self, error: ErrorInfo) -> bool:
        """Check if this strategy can recover from the error."""
        return False
    
    def recover(self, error: ErrorInfo, context: Dict[str, Any]) -> bool:
        """Attempt to recover from the error."""
        return False


class RetryStrategy(ErrorRecoveryStrategy):
    """Retry strategy for recoverable errors."""
    
    def __init__(self, max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
        self.max_retries = max_retries
        self.delay = delay
        self.backoff = backoff
    
    def can_recover(self, error: ErrorInfo) -> bool:
        """Check if error is retryable."""
        return (error.recoverable and 
                error.retry_count < self.max_retries and
                error.severity in [ErrorSeverity.LOW, ErrorSeverity.MEDIUM])
    
    def recover(self, error: ErrorInfo, context: Dict[str, Any]) -> bool:
        """Retry the operation."""
        if not self.can_recover(error):
            return False
        
        # Calculate delay with exponential backoff
        delay = self.delay * (self.backoff ** error.retry_count)
        
        # Get the original function and arguments
        original_func = context.get('function')
        args = context.get('args', ())
        kwargs = context.get('kwargs', {})
        
        if original_func:
            try:
                time.sleep(delay)
                result = original_func(*args, **kwargs)
                return True
            except Exception as e:
                error.retry_count += 1
                return False
        
        return False


class FallbackStrategy(ErrorRecoveryStrategy):
    """Fallback strategy for module failures."""
    
    def can_recover(self, error: ErrorInfo) -> bool:
        """Check if fallback is available."""
        return (error.category == ErrorCategory.MODULE and
                error.module_name and
                'fallback_module' in error.context)
    
    def recover(self, error: ErrorInfo, context: Dict[str, Any]) -> bool:
        """Use fallback module."""
        fallback_module = error.context.get('fallback_module')
        if fallback_module:
            try:
                # Execute fallback module
                fallback_func = context.get('fallback_function')
                if fallback_func:
                    fallback_func()
                    return True
            except Exception:
                pass
        
        return False


class ResourceCleanupStrategy(ErrorRecoveryStrategy):
    """Resource cleanup strategy for resource-related errors."""
    
    def can_recover(self, error: ErrorInfo) -> bool:
        """Check if resource cleanup can help."""
        return error.category == ErrorCategory.RESOURCE
    
    def recover(self, error: ErrorInfo, context: Dict[str, Any]) -> bool:
        """Clean up resources and retry."""
        cleanup_func = context.get('cleanup_function')
        if cleanup_func:
            try:
                cleanup_func()
                return True
            except Exception:
                pass
        
        return False


class ErrorHandler:
    """Main error handling system for Pymba."""
    
    def __init__(self, log_manager: LogManager):
        self.log_manager = log_manager
        self.error_history: List[ErrorInfo] = []
        self.recovery_strategies: List[ErrorRecoveryStrategy] = []
        self.error_callbacks: List[Callable[[ErrorInfo], None]] = []
        
        # Initialize default recovery strategies
        self._initialize_default_strategies()
        
        # Setup signal handlers
        self._setup_signal_handlers()
        
        # Error statistics
        self.error_stats = {
            'total_errors': 0,
            'errors_by_severity': {severity.value: 0 for severity in ErrorSeverity},
            'errors_by_category': {category.value: 0 for category in ErrorCategory},
            'recovery_attempts': 0,
            'successful_recoveries': 0
        }
    
    def _initialize_default_strategies(self):
        """Initialize default error recovery strategies."""
        self.add_recovery_strategy(RetryStrategy())
        self.add_recovery_strategy(FallbackStrategy())
        self.add_recovery_strategy(ResourceCleanupStrategy())
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            self.log_manager.print_warning(f"Received signal {signum}, initiating graceful shutdown...")
            self.handle_critical_error(
                f"Received signal {signum}",
                ErrorCategory.SYSTEM,
                ErrorSeverity.CRITICAL,
                context={'signal': signum, 'frame': str(frame)}
            )
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def add_recovery_strategy(self, strategy: ErrorRecoveryStrategy):
        """Add a recovery strategy."""
        self.recovery_strategies.append(strategy)
        self.log_manager.print_debug(f"Added recovery strategy: {strategy.__class__.__name__}")
    
    def add_error_callback(self, callback: Callable[[ErrorInfo], None]):
        """Add an error callback."""
        self.error_callbacks.append(callback)
        self.log_manager.print_debug(f"Added error callback: {callback.__name__}")
    
    def handle_error(self, error: Exception, 
                    category: ErrorCategory = ErrorCategory.UNKNOWN,
                    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                    module_name: Optional[str] = None,
                    context: Optional[Dict[str, Any]] = None) -> bool:
        """Handle an error and attempt recovery."""
        error_info = self._create_error_info(
            error, category, severity, module_name, context
        )
        
        return self.handle_error_info(error_info)
    
    def handle_error_info(self, error_info: ErrorInfo) -> bool:
        """Handle an error info object and attempt recovery."""
        # Log the error
        self._log_error(error_info)
        
        # Record in history
        self.error_history.append(error_info)
        
        # Update statistics
        self._update_error_stats(error_info)
        
        # Notify callbacks
        for callback in self.error_callbacks:
            try:
                callback(error_info)
            except Exception as e:
                self.log_manager.print_warning(f"Error callback failed: {e}")
        
        # Attempt recovery
        return self._attempt_recovery(error_info)
    
    def _create_error_info(self, error: Exception,
                          category: ErrorCategory,
                          severity: ErrorSeverity,
                          module_name: Optional[str],
                          context: Optional[Dict[str, Any]]) -> ErrorInfo:
        """Create ErrorInfo object from exception."""
        error_type = type(error).__name__
        message = str(error)
        traceback_str = traceback.format_exc()
        
        # Determine if error is recoverable based on type
        recoverable = not isinstance(error, (SystemExit, KeyboardInterrupt, MemoryError))
        
        # Auto-categorize based on error type
        if category == ErrorCategory.UNKNOWN:
            if isinstance(error, (FileNotFoundError, PermissionError)):
                category = ErrorCategory.PERMISSION
            elif isinstance(error, (ConnectionError, TimeoutError)):
                category = ErrorCategory.NETWORK
            elif isinstance(error, (ValueError, TypeError)):
                category = ErrorCategory.VALIDATION
            elif isinstance(error, MemoryError):
                category = ErrorCategory.RESOURCE
        
        return ErrorInfo(
            error_type=error_type,
            message=message,
            severity=severity,
            category=category,
            module_name=module_name,
            traceback=traceback_str,
            context=context or {},
            recoverable=recoverable
        )
    
    def _log_error(self, error_info: ErrorInfo):
        """Log error information."""
        if error_info.severity == ErrorSeverity.CRITICAL:
            self.log_manager.print_error(f"CRITICAL ERROR: {error_info.message}")
        elif error_info.severity == ErrorSeverity.HIGH:
            self.log_manager.print_error(f"HIGH ERROR: {error_info.message}")
        elif error_info.severity == ErrorSeverity.MEDIUM:
            self.log_manager.print_warning(f"MEDIUM ERROR: {error_info.message}")
        else:
            self.log_manager.print_info(f"LOW ERROR: {error_info.message}")
        
        if error_info.module_name:
            self.log_manager.print_debug(f"Module: {error_info.module_name}")
        
        self.log_manager.print_debug(f"Category: {error_info.category.value}")
        
        if error_info.traceback and self.log_manager.verbose:
            self.log_manager.print_debug(f"Traceback:\n{error_info.traceback}")
    
    def _update_error_stats(self, error_info: ErrorInfo):
        """Update error statistics."""
        self.error_stats['total_errors'] += 1
        self.error_stats['errors_by_severity'][error_info.severity.value] += 1
        self.error_stats['errors_by_category'][error_info.category.value] += 1
    
    def _attempt_recovery(self, error_info: ErrorInfo) -> bool:
        """Attempt to recover from error using available strategies."""
        if not error_info.recoverable:
            return False
        
        for strategy in self.recovery_strategies:
            if strategy.can_recover(error_info):
                self.error_stats['recovery_attempts'] += 1
                
                try:
                    success = strategy.recover(error_info, error_info.context)
                    if success:
                        self.error_stats['successful_recoveries'] += 1
                        self.log_manager.print_success(f"Successfully recovered from error using {strategy.__class__.__name__}")
                        return True
                except Exception as e:
                    self.log_manager.print_warning(f"Recovery strategy {strategy.__class__.__name__} failed: {e}")
        
        return False
    
    def handle_critical_error(self, message: str,
                            category: ErrorCategory = ErrorCategory.SYSTEM,
                            context: Optional[Dict[str, Any]] = None) -> None:
        """Handle critical error that may require shutdown."""
        error_info = ErrorInfo(
            error_type="CriticalError",
            message=message,
            severity=ErrorSeverity.CRITICAL,
            category=category,
            context=context or {},
            recoverable=False
        )
        
        self.handle_error_info(error_info)
        
        # For critical errors, we might want to initiate shutdown
        if not self._attempt_recovery(error_info):
            self.log_manager.print_error("Critical error could not be recovered, initiating shutdown...")
            sys.exit(1)
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get error handling summary."""
        return {
            'total_errors': self.error_stats['total_errors'],
            'errors_by_severity': self.error_stats['errors_by_severity'],
            'errors_by_category': self.error_stats['errors_by_category'],
            'recovery_attempts': self.error_stats['recovery_attempts'],
            'successful_recoveries': self.error_stats['successful_recoveries'],
            'recovery_rate': (
                self.error_stats['successful_recoveries'] / self.error_stats['recovery_attempts']
                if self.error_stats['recovery_attempts'] > 0 else 0.0
            ),
            'recent_errors': [
                {
                    'type': error.error_type,
                    'message': error.message,
                    'severity': error.severity.value,
                    'category': error.category.value,
                    'timestamp': error.timestamp,
                    'module': error.module_name
                }
                for error in self.error_history[-10:]  # Last 10 errors
            ]
        }
    
    def clear_error_history(self):
        """Clear error history."""
        self.error_history.clear()
        self.log_manager.print_debug("Error history cleared")


def error_handler(category: ErrorCategory = ErrorCategory.UNKNOWN,
                 severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                 recoverable: bool = True):
    """Decorator for automatic error handling."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Try to get error handler from context
            error_handler_instance = None
            for arg in args:
                if hasattr(arg, 'error_handler'):
                    error_handler_instance = arg.error_handler
                    break
            
            if not error_handler_instance:
                # Fallback to default error handling
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    print(f"Error in {func.__name__}: {e}")
                    raise
            
            try:
                return func(*args, **kwargs)
            except Exception as e:
                module_name = getattr(args[0], 'module_name', None) if args else None
                success = error_handler_instance.handle_error(
                    e, category, severity, module_name,
                    context={'function': func, 'args': args, 'kwargs': kwargs}
                )
                
                if not success:
                    raise
        
        return wrapper
    return decorator


class SafeExecutor:
    """Safe executor that handles errors gracefully."""
    
    def __init__(self, error_handler: ErrorHandler):
        self.error_handler = error_handler
    
    def execute_safely(self, func: Callable, *args, **kwargs) -> tuple[bool, Any]:
        """Execute function safely and return (success, result)."""
        try:
            result = func(*args, **kwargs)
            return True, result
        except Exception as e:
            success = self.error_handler.handle_error(
                e, ErrorCategory.MODULE, ErrorSeverity.MEDIUM,
                context={'function': func, 'args': args, 'kwargs': kwargs}
            )
            return success, None
    
    def execute_with_timeout(self, func: Callable, timeout: float, *args, **kwargs) -> tuple[bool, Any]:
        """Execute function with timeout."""
        import threading
        import queue
        
        result_queue = queue.Queue()
        exception_queue = queue.Queue()
        
        def target():
            try:
                result = func(*args, **kwargs)
                result_queue.put(result)
            except Exception as e:
                exception_queue.put(e)
        
        thread = threading.Thread(target=target, daemon=True)
        thread.start()
        thread.join(timeout=timeout)
        
        if thread.is_alive():
            # Timeout occurred
            error = TimeoutError(f"Function {func.__name__} timed out after {timeout} seconds")
            self.error_handler.handle_error(error, ErrorCategory.TIMEOUT, ErrorSeverity.HIGH)
            return False, None
        
        if not exception_queue.empty():
            error = exception_queue.get()
            success = self.error_handler.handle_error(error, ErrorCategory.MODULE, ErrorSeverity.MEDIUM)
            return success, None
        
        if not result_queue.empty():
            return True, result_queue.get()
        
        return False, None

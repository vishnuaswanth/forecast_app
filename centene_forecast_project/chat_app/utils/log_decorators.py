"""
Logging Decorators for LLM Workflow

Provides convenient decorators for adding logging to LLM-related functions:
- @log_llm_call: Wraps LLM API calls with timing and token logging
- @log_with_context: Adds correlation context to function
- @log_async_timing: Async-safe timing decorator
"""

import time
import functools
import asyncio
from typing import Any, Callable, Optional, TypeVar, Union
import logging

from chat_app.utils.llm_logger import (
    get_llm_logger,
    get_correlation_id,
    CorrelationContext,
    create_correlation_id
)


F = TypeVar('F', bound=Callable[..., Any])

logger = logging.getLogger(__name__)


def log_llm_call(
    operation_name: Optional[str] = None,
    log_request: bool = True,
    log_response: bool = True
) -> Callable[[F], F]:
    """
    Decorator to wrap LLM API calls with timing and token logging.

    Args:
        operation_name: Name of the operation for logging (defaults to function name)
        log_request: Whether to log the request details
        log_response: Whether to log the response details

    Usage:
        @log_llm_call(operation_name='intent_classification')
        async def categorize_intent(self, user_text: str) -> dict:
            ...
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            llm_logger = get_llm_logger()
            correlation_id = get_correlation_id() or create_correlation_id()
            op_name = operation_name or func.__name__

            start_time = time.time()

            try:
                # Log request if enabled
                if log_request:
                    llm_logger._log(
                        logging.DEBUG,
                        f'{op_name}_started',
                        {
                            'operation': op_name,
                            'args_count': len(args),
                            'kwargs_keys': list(kwargs.keys()),
                        },
                        correlation_id=correlation_id
                    )

                # Execute the function
                result = await func(*args, **kwargs)

                # Calculate duration
                duration_ms = (time.time() - start_time) * 1000

                # Log response if enabled
                if log_response:
                    result_summary = {}
                    if isinstance(result, dict):
                        result_summary['keys'] = list(result.keys())
                        if 'category' in result:
                            result_summary['category'] = result['category']
                        if 'confidence' in result:
                            result_summary['confidence'] = result['confidence']
                        if 'success' in result:
                            result_summary['success'] = result['success']

                    llm_logger._log(
                        logging.INFO,
                        f'{op_name}_completed',
                        {
                            'operation': op_name,
                            'duration_ms': round(duration_ms, 2),
                            'result_summary': result_summary,
                        },
                        correlation_id=correlation_id
                    )

                return result

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                llm_logger.log_error(
                    correlation_id=correlation_id,
                    error=e,
                    stage=op_name,
                    context={'duration_ms': round(duration_ms, 2)}
                )
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            llm_logger = get_llm_logger()
            correlation_id = get_correlation_id() or create_correlation_id()
            op_name = operation_name or func.__name__

            start_time = time.time()

            try:
                if log_request:
                    llm_logger._log(
                        logging.DEBUG,
                        f'{op_name}_started',
                        {
                            'operation': op_name,
                            'args_count': len(args),
                            'kwargs_keys': list(kwargs.keys()),
                        },
                        correlation_id=correlation_id
                    )

                result = func(*args, **kwargs)

                duration_ms = (time.time() - start_time) * 1000

                if log_response:
                    result_summary = {}
                    if isinstance(result, dict):
                        result_summary['keys'] = list(result.keys())

                    llm_logger._log(
                        logging.INFO,
                        f'{op_name}_completed',
                        {
                            'operation': op_name,
                            'duration_ms': round(duration_ms, 2),
                            'result_summary': result_summary,
                        },
                        correlation_id=correlation_id
                    )

                return result

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                llm_logger.log_error(
                    correlation_id=correlation_id,
                    error=e,
                    stage=op_name,
                    context={'duration_ms': round(duration_ms, 2)}
                )
                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def log_with_context(
    conversation_id_arg: Optional[str] = 'conversation_id',
    message_id_arg: Optional[str] = None,
    user_id_arg: Optional[str] = None
) -> Callable[[F], F]:
    """
    Decorator to add correlation context to a function.

    Extracts conversation_id from function arguments and creates a correlation context.
    The correlation ID will be available to all nested calls via context variable.

    Args:
        conversation_id_arg: Name of the argument containing conversation ID
        message_id_arg: Name of the argument containing message ID
        user_id_arg: Name of the argument containing user ID

    Usage:
        @log_with_context(conversation_id_arg='conversation_id')
        async def process_message(self, user_text: str, conversation_id: str) -> dict:
            ...
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            # Extract IDs from kwargs or args
            conv_id = kwargs.get(conversation_id_arg) if conversation_id_arg else None
            msg_id = kwargs.get(message_id_arg) if message_id_arg else None
            user_id = kwargs.get(user_id_arg) if user_id_arg else None

            # Create correlation context
            correlation_id = create_correlation_id(conv_id, msg_id)
            context = CorrelationContext(
                correlation_id=correlation_id,
                conversation_id=conv_id,
                message_id=msg_id,
                user_id=user_id
            )

            async with context:
                return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            conv_id = kwargs.get(conversation_id_arg) if conversation_id_arg else None
            msg_id = kwargs.get(message_id_arg) if message_id_arg else None
            user_id = kwargs.get(user_id_arg) if user_id_arg else None

            correlation_id = create_correlation_id(conv_id, msg_id)
            context = CorrelationContext(
                correlation_id=correlation_id,
                conversation_id=conv_id,
                message_id=msg_id,
                user_id=user_id
            )

            with context:
                return func(*args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def log_async_timing(
    operation_name: Optional[str] = None,
    log_level: int = logging.INFO
) -> Callable[[F], F]:
    """
    Async-safe timing decorator for performance logging.

    Args:
        operation_name: Name of the operation (defaults to function name)
        log_level: Logging level for timing messages

    Usage:
        @log_async_timing(operation_name='fetch_forecast_data')
        async def fetch_data(params: dict) -> dict:
            ...
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            llm_logger = get_llm_logger()
            correlation_id = get_correlation_id()
            op_name = operation_name or func.__name__

            start_time = time.time()

            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000

                llm_logger._log(
                    log_level,
                    'timing',
                    {
                        'operation': op_name,
                        'duration_ms': round(duration_ms, 2),
                        'success': True,
                    },
                    correlation_id=correlation_id
                )

                return result

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                llm_logger._log(
                    logging.WARNING,
                    'timing',
                    {
                        'operation': op_name,
                        'duration_ms': round(duration_ms, 2),
                        'success': False,
                        'error': str(e),
                    },
                    correlation_id=correlation_id
                )
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            llm_logger = get_llm_logger()
            correlation_id = get_correlation_id()
            op_name = operation_name or func.__name__

            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000

                llm_logger._log(
                    log_level,
                    'timing',
                    {
                        'operation': op_name,
                        'duration_ms': round(duration_ms, 2),
                        'success': True,
                    },
                    correlation_id=correlation_id
                )

                return result

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                llm_logger._log(
                    logging.WARNING,
                    'timing',
                    {
                        'operation': op_name,
                        'duration_ms': round(duration_ms, 2),
                        'success': False,
                        'error': str(e),
                    },
                    correlation_id=correlation_id
                )
                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


class LoggingContextManager:
    """
    Context manager for logging a block of code with correlation ID.

    Usage:
        async with LoggingContextManager(conversation_id, user_id=user.id) as ctx:
            # All logging in this block will have the correlation ID
            result = await process_something()
    """

    def __init__(
        self,
        conversation_id: Optional[str] = None,
        message_id: Optional[str] = None,
        user_id: Optional[str] = None,
        operation_name: str = 'operation'
    ):
        self.conversation_id = conversation_id
        self.message_id = message_id
        self.user_id = user_id
        self.operation_name = operation_name
        self.correlation_id = create_correlation_id(conversation_id, message_id)
        self.context = CorrelationContext(
            correlation_id=self.correlation_id,
            conversation_id=conversation_id,
            message_id=message_id,
            user_id=user_id
        )
        self.start_time = None
        self.llm_logger = get_llm_logger()

    def __enter__(self):
        self.start_time = time.time()
        self.context.__enter__()
        self.llm_logger._log(
            logging.DEBUG,
            f'{self.operation_name}_started',
            {'operation': self.operation_name},
            correlation_id=self.correlation_id
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start_time) * 1000

        if exc_type is not None:
            self.llm_logger.log_error(
                correlation_id=self.correlation_id,
                error=exc_val,
                stage=self.operation_name,
                context={'duration_ms': round(duration_ms, 2)}
            )
        else:
            self.llm_logger._log(
                logging.INFO,
                f'{self.operation_name}_completed',
                {
                    'operation': self.operation_name,
                    'duration_ms': round(duration_ms, 2),
                },
                correlation_id=self.correlation_id
            )

        return self.context.__exit__(exc_type, exc_val, exc_tb)

    async def __aenter__(self):
        self.start_time = time.time()
        await self.context.__aenter__()
        self.llm_logger._log(
            logging.DEBUG,
            f'{self.operation_name}_started',
            {'operation': self.operation_name},
            correlation_id=self.correlation_id
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start_time) * 1000

        if exc_type is not None:
            self.llm_logger.log_error(
                correlation_id=self.correlation_id,
                error=exc_val,
                stage=self.operation_name,
                context={'duration_ms': round(duration_ms, 2)}
            )
        else:
            self.llm_logger._log(
                logging.INFO,
                f'{self.operation_name}_completed',
                {
                    'operation': self.operation_name,
                    'duration_ms': round(duration_ms, 2),
                },
                correlation_id=self.correlation_id
            )

        return await self.context.__aexit__(exc_type, exc_val, exc_tb)

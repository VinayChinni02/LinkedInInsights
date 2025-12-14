"""
Retry utilities for resilient external service calls.
Implements exponential backoff for transient failures.
"""
import asyncio
import logging
from typing import Callable, TypeVar, Optional, List
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')


async def retry_async(
    func: Callable[..., T],
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: tuple = (Exception,),
    on_retry: Optional[Callable] = None
) -> T:
    """
    Retry an async function with exponential backoff.
    
    Args:
        func: Async function to retry
        max_attempts: Maximum number of attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff
        exceptions: Tuple of exceptions to catch and retry
        on_retry: Optional callback function called on each retry
        
    Returns:
        Result of the function call
        
    Raises:
        Last exception if all retries fail
    """
    last_exception = None
    
    for attempt in range(1, max_attempts + 1):
        try:
            if asyncio.iscoroutinefunction(func):
                return await func()
            else:
                return func()
        except exceptions as e:
            last_exception = e
            
            if attempt == max_attempts:
                logger.error(
                    f"Function {func.__name__} failed after {max_attempts} attempts: {e}"
                )
                raise
            
            # Calculate delay with exponential backoff
            delay = min(
                initial_delay * (exponential_base ** (attempt - 1)),
                max_delay
            )
            
            logger.warning(
                f"Attempt {attempt}/{max_attempts} failed for {func.__name__}: {e}. "
                f"Retrying in {delay:.2f}s..."
            )
            
            if on_retry:
                on_retry(attempt, delay, e)
            
            await asyncio.sleep(delay)
    
    # Should never reach here, but just in case
    if last_exception:
        raise last_exception


def retry_decorator(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Decorator for retrying async functions.
    
    Usage:
        @retry_decorator(max_attempts=3, initial_delay=1.0)
        async def my_function():
            # Your code here
            pass
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            async def retry_func():
                return await func(*args, **kwargs)
            
            return await retry_async(
                retry_func,
                max_attempts=max_attempts,
                initial_delay=initial_delay,
                max_delay=max_delay,
                exponential_base=exponential_base,
                exceptions=exceptions
            )
        return wrapper
    return decorator

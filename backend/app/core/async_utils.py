"""Async utilities for wrapping sync operations"""
import asyncio
from functools import wraps
from typing import TypeVar, Callable, Any
from concurrent.futures import ThreadPoolExecutor

T = TypeVar('T')

# Shared thread pool for CPU-bound and blocking IO operations
_executor = ThreadPoolExecutor(max_workers=10)
_akshare_executor = ThreadPoolExecutor(max_workers=1)


async def run_sync(func: Callable[..., T], *args, **kwargs) -> T:
    """
    Run a synchronous function in a thread pool to avoid blocking the event loop.

    Usage:
        result = await run_sync(some_sync_function, arg1, arg2, kwarg1=value)
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        _executor,
        lambda: func(*args, **kwargs)
    )


async def run_akshare(func: Callable[..., T], *args, **kwargs) -> T:
    """
    Run AKShare-related sync functions in a single-threaded executor to avoid
    py_mini_racer/V8 crashes on concurrent calls.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        _akshare_executor,
        lambda: func(*args, **kwargs)
    )


def async_wrap(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator to wrap a synchronous function to be async.

    Usage:
        @async_wrap
        def sync_function(x):
            return x * 2

        # Now can be called as:
        result = await sync_function(5)
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        return await run_sync(func, *args, **kwargs)
    return wrapper

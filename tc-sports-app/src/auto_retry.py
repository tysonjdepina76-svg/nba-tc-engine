"""Auto-retry with exponential backoff.

Wraps any function call with N retries. Critical for flaky APIs.
"""
import time
import logging
import random
from typing import Callable, Any, Tuple, Type

logger = logging.getLogger(__name__)


def retry_with_backoff(
    func: Callable,
    *args,
    max_retries: int = 3,
    initial_delay_sec: float = 1.0,
    backoff_factor: float = 2.0,
    max_delay_sec: float = 30.0,
    retry_on: Tuple[Type[Exception], ...] = (Exception,),
    jitter: bool = True,
    on_retry: Callable = None,
    **kwargs,
) -> Any:
    """Call func with exponential backoff retries.

    Args:
        func: function to call
        max_retries: max number of retry attempts (not counting first call)
        initial_delay_sec: delay before first retry
        backoff_factor: multiply delay by this each retry
        max_delay_sec: cap on delay
        retry_on: tuple of exception types to retry on
        jitter: add random jitter to delay (prevents thundering herd)
        on_retry: optional callback(retry_num, exception, delay) called before each retry
    """
    last_exception = None
    delay = initial_delay_sec
    for attempt in range(max_retries + 1):
        try:
            return func(*args, **kwargs)
        except retry_on as e:
            last_exception = e
            if attempt >= max_retries:
                logger.error(f"Failed after {max_retries + 1} attempts: {e}")
                raise
            actual_delay = delay
            if jitter:
                actual_delay = delay * (0.5 + random.random() * 0.5)
            actual_delay = min(actual_delay, max_delay_sec)
            logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {actual_delay:.2f}s")
            if on_retry:
                on_retry(attempt + 1, e, actual_delay)
            time.sleep(actual_delay)
            delay *= backoff_factor
    if last_exception:
        raise last_exception

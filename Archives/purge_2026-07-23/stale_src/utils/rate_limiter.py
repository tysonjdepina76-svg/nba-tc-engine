"""rate_limiter.py — Token-bucket rate limiter for API calls."""
import time
import threading
from collections import deque
from typing import Optional


class RateLimiter:
    """Thread-safe token-bucket rate limiter.

    Usage:
        rl = RateLimiter(calls_per_minute=60)
        rl.wait()  # blocks until a token is available
    """

    def __init__(self, calls_per_minute: int = 60, burst: Optional[int] = None):
        self.rate = calls_per_minute / 60.0
        self.capacity = burst or calls_per_minute
        self.tokens = float(self.capacity)
        self.last = time.monotonic()
        self._lock = threading.Lock()

    def _refill(self):
        now = time.monotonic()
        elapsed = now - self.last
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last = now

    def wait(self, tokens: int = 1) -> float:
        with self._lock:
            while True:
                self._refill()
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return 0.0
                needed = (tokens - self.tokens) / self.rate
                time.sleep(min(needed, 1.0))
                return needed

    def try_acquire(self, tokens: int = 1) -> bool:
        with self._lock:
            self._refill()
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False


if __name__ == "__main__":
    rl = RateLimiter(calls_per_minute=10)
    for i in range(12):
        t = rl.wait()
        print(f"call {i+1} after {t:.3f}s wait")

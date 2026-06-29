"""Circuit breaker - stops calling a dead API after repeated failures.

States: CLOSED (normal) -> OPEN (blocking) -> HALF_OPEN (testing) -> CLOSED
"""
import time
import threading
from typing import Callable, Any, Optional
from datetime import datetime, timedelta


class CircuitState:
    CLOSED = "closed"      # normal, calls go through
    OPEN = "open"          # blocking, calls fail fast
    HALF_OPEN = "half_open"  # testing if recovered


class CircuitBreaker:
    def __init__(self, name: str, failure_threshold: int = 5, recovery_timeout_sec: int = 60, half_open_max_calls: int = 1):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout_sec = recovery_timeout_sec
        self.half_open_max_calls = half_open_max_calls
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.opened_at: Optional[datetime] = None
        self.half_open_calls = 0
        self._lock = threading.Lock()
        self.call_log: list = []

    def call(self, func: Callable, *args, **kwargs) -> Any:
        with self._lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_calls = 0
                else:
                    raise CircuitOpenError(f"Circuit '{self.name}' is OPEN. Retry after {self._seconds_until_retry():.0f}s")
            if self.state == CircuitState.HALF_OPEN:
                if self.half_open_calls >= self.half_open_max_calls:
                    raise CircuitOpenError(f"Circuit '{self.name}' HALF_OPEN limit reached")
                self.half_open_calls += 1
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure(e)
            raise

    def _on_success(self):
        with self._lock:
            self.success_count += 1
            self.call_log.append({"time": datetime.now().isoformat(), "result": "success", "state": self.state})
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.opened_at = None

    def _on_failure(self, error: Exception):
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = datetime.now()
            self.call_log.append({"time": datetime.now().isoformat(), "result": "failure", "error": str(error), "state": self.state})
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
                self.opened_at = datetime.now()
            elif self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                self.opened_at = datetime.now()

    def _should_attempt_reset(self) -> bool:
        if self.opened_at is None:
            return True
        return datetime.now() >= self.opened_at + timedelta(seconds=self.recovery_timeout_sec)

    def _seconds_until_retry(self) -> float:
        if self.opened_at is None:
            return 0
        elapsed = (datetime.now() - self.opened_at).total_seconds()
        return max(0, self.recovery_timeout_sec - elapsed)

    def get_status(self) -> dict:
        with self._lock:
            return {
                "name": self.name,
                "state": self.state,
                "failure_count": self.failure_count,
                "success_count": self.success_count,
                "last_failure": self.last_failure_time.isoformat() if self.last_failure_time else None,
                "seconds_until_retry": self._seconds_until_retry(),
                "opened_at": self.opened_at.isoformat() if self.opened_at else None,
            }

    def force_open(self):
        with self._lock:
            self.state = CircuitState.OPEN
            self.opened_at = datetime.now()

    def force_close(self):
        with self._lock:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.opened_at = None


class CircuitOpenError(Exception):
    pass


class CircuitBreakerRegistry:
    _breakers: dict = {}
    _lock = threading.Lock()

    @classmethod
    def get(cls, name: str, **kwargs) -> CircuitBreaker:
        with cls._lock:
            if name not in cls._breakers:
                cls._breakers[name] = CircuitBreaker(name, **kwargs)
            return cls._breakers[name]

    @classmethod
    def get_all_status(cls) -> dict:
        with cls._lock:
            return {name: b.get_status() for name, b in cls._breakers.items()}

    @classmethod
    def reset_all(cls):
        with cls._lock:
            for b in cls._breakers.values():
                b.force_close()

"""
Network Resilience and Circuit Breaker Implementation
Provides robust network handling with exponential backoff, circuit breakers, and rate limiting
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, Callable, TypeVar, Awaitable
from dataclasses import dataclass, field
from enum import Enum
import httpx
from tenacity import (
    retry, 
    stop_after_attempt, 
    wait_exponential, 
    retry_if_exception_type,
    before_sleep_log
)

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, blocking requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    failure_threshold: int = 5
    recovery_timeout: int = 60  # seconds
    expected_exception: type = Exception
    name: str = "default"


@dataclass
class CircuitBreakerStats:
    """Statistics for circuit breaker monitoring"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    circuit_opens: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    current_failure_count: int = 0


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open"""
    pass


class RateLimitError(Exception):
    """Raised when rate limit is exceeded"""
    pass


class CircuitBreaker:
    """Circuit breaker implementation for network resilience"""
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitState.CLOSED
        self.stats = CircuitBreakerStats()
        self._last_failure_time: Optional[float] = None
        self._failure_count = 0
        
    def __call__(self, func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        """Decorator interface for circuit breaker"""
        async def wrapper(*args, **kwargs) -> T:
            return await self.call(func, *args, **kwargs)
        return wrapper
    
    async def call(self, func: Callable[..., Awaitable[T]], *args, **kwargs) -> T:
        """Execute function with circuit breaker protection"""
        self.stats.total_requests += 1
        
        # Check if circuit should be opened
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.info(f"Circuit breaker {self.config.name} transitioning to HALF_OPEN")
            else:
                raise CircuitBreakerError(
                    f"Circuit breaker {self.config.name} is OPEN. "
                    f"Last failure: {self.stats.last_failure_time}"
                )
        
        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
            
        except self.config.expected_exception as e:
            await self._on_failure(e)
            raise
        except Exception as e:
            # Unexpected exceptions don't count as circuit breaker failures
            logger.warning(f"Unexpected exception in circuit breaker {self.config.name}: {e}")
            raise
    
    async def _on_success(self):
        """Handle successful execution"""
        self.stats.successful_requests += 1
        self.stats.last_success_time = datetime.utcnow()
        self._failure_count = 0
        self.stats.current_failure_count = 0
        
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            logger.info(f"Circuit breaker {self.config.name} reset to CLOSED")
    
    async def _on_failure(self, exception: Exception):
        """Handle failed execution"""
        self.stats.failed_requests += 1
        self.stats.last_failure_time = datetime.utcnow()
        self._last_failure_time = time.time()
        self._failure_count += 1
        self.stats.current_failure_count = self._failure_count
        
        logger.warning(
            f"Circuit breaker {self.config.name} failure {self._failure_count}/{self.config.failure_threshold}: {exception}"
        )
        
        if self._failure_count >= self.config.failure_threshold:
            self.state = CircuitState.OPEN
            self.stats.circuit_opens += 1
            logger.error(f"Circuit breaker {self.config.name} OPENED after {self._failure_count} failures")
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt reset"""
        if self._last_failure_time is None:
            return True
        return time.time() - self._last_failure_time >= self.config.recovery_timeout
    
    def get_stats(self) -> CircuitBreakerStats:
        """Get current circuit breaker statistics"""
        return self.stats
    
    def reset(self):
        """Manually reset circuit breaker"""
        self.state = CircuitState.CLOSED
        self._failure_count = 0
        self.stats.current_failure_count = 0
        logger.info(f"Circuit breaker {self.config.name} manually reset")


class RateLimiter:
    """Token bucket rate limiter"""
    
    def __init__(self, max_requests: int, time_window: int):
        self.max_requests = max_requests
        self.time_window = time_window
        self.tokens = max_requests
        self.last_refill = time.time()
        self._lock = asyncio.Lock()
    
    async def acquire(self) -> bool:
        """Acquire a token from the rate limiter"""
        async with self._lock:
            now = time.time()
            
            # Refill tokens based on elapsed time
            elapsed = now - self.last_refill
            tokens_to_add = elapsed * (self.max_requests / self.time_window)
            self.tokens = min(self.max_requests, self.tokens + tokens_to_add)
            self.last_refill = now
            
            if self.tokens >= 1:
                self.tokens -= 1
                return True
            return False
    
    async def wait_for_token(self):
        """Wait until a token is available"""
        while not await self.acquire():
            await asyncio.sleep(0.1)


class NetworkResilientClient:
    """HTTP client with comprehensive network resilience"""
    
    def __init__(self, 
                 base_url: str = "",
                 timeout: float = 30.0,
                 rate_limit_requests: int = 100,
                 rate_limit_window: int = 60,
                 circuit_breaker_config: Optional[CircuitBreakerConfig] = None):
        
        self.base_url = base_url
        self.client = httpx.AsyncClient(
            timeout=timeout,
            headers={'User-Agent': 'BaseballSimulation/2.0'}
        )
        
        # Rate limiting
        self.rate_limiter = RateLimiter(rate_limit_requests, rate_limit_window)
        
        # Circuit breaker
        if circuit_breaker_config is None:
            circuit_breaker_config = CircuitBreakerConfig(
                failure_threshold=5,
                recovery_timeout=60,
                expected_exception=(httpx.RequestError, httpx.HTTPStatusError),
                name="http_client"
            )
        self.circuit_breaker = CircuitBreaker(circuit_breaker_config)
        
        # Statistics
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'rate_limited_requests': 0,
            'circuit_breaker_rejections': 0
        }
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def _make_request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Make HTTP request with retries"""
        full_url = f"{self.base_url}{url}" if not url.startswith('http') else url
        
        response = await self.client.request(method, full_url, **kwargs)
        response.raise_for_status()
        return response
    
    async def get(self, url: str, **kwargs) -> httpx.Response:
        """GET request with full resilience"""
        return await self._resilient_request("GET", url, **kwargs)
    
    async def post(self, url: str, **kwargs) -> httpx.Response:
        """POST request with full resilience"""
        return await self._resilient_request("POST", url, **kwargs)
    
    async def _resilient_request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Execute request with all resilience features"""
        self.stats['total_requests'] += 1
        
        # Rate limiting
        if not await self.rate_limiter.acquire():
            self.stats['rate_limited_requests'] += 1
            logger.warning(f"Rate limit exceeded for {method} {url}")
            await self.rate_limiter.wait_for_token()
        
        # Circuit breaker protection
        try:
            response = await self.circuit_breaker.call(self._make_request, method, url, **kwargs)
            self.stats['successful_requests'] += 1
            return response
            
        except CircuitBreakerError:
            self.stats['circuit_breaker_rejections'] += 1
            raise
        except Exception:
            self.stats['failed_requests'] += 1
            raise
    
    async def get_json(self, url: str, **kwargs) -> Dict[str, Any]:
        """GET request returning JSON with resilience"""
        response = await self.get(url, **kwargs)
        return response.json()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics"""
        stats = self.stats.copy()
        stats['circuit_breaker'] = self.circuit_breaker.get_stats().__dict__
        return stats
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


# Global circuit breakers for different services
MLB_API_CIRCUIT_BREAKER = CircuitBreaker(CircuitBreakerConfig(
    failure_threshold=5,
    recovery_timeout=300,  # 5 minutes for external API
    expected_exception=(httpx.RequestError, httpx.HTTPStatusError),
    name="mlb_api"
))

DATABASE_CIRCUIT_BREAKER = CircuitBreaker(CircuitBreakerConfig(
    failure_threshold=3,
    recovery_timeout=60,   # 1 minute for database
    expected_exception=(Exception,),
    name="database"
))


def with_circuit_breaker(breaker: CircuitBreaker):
    """Decorator for applying circuit breaker to any async function"""
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        return breaker(func)
    return decorator


async def test_network_resilience():
    """Test function for network resilience components"""
    logger.info("Testing network resilience components...")
    
    # Test circuit breaker
    @with_circuit_breaker(MLB_API_CIRCUIT_BREAKER)
    async def failing_function():
        raise httpx.RequestError("Simulated failure")
    
    # Test rate limiter
    rate_limiter = RateLimiter(max_requests=2, time_window=1)
    
    try:
        for i in range(5):
            await failing_function()
    except CircuitBreakerError:
        logger.info("Circuit breaker correctly opened after failures")
    
    # Test rate limiting
    for i in range(3):
        can_proceed = await rate_limiter.acquire()
        logger.info(f"Rate limit attempt {i+1}: {'allowed' if can_proceed else 'blocked'}")
    
    logger.info("Network resilience test completed")


if __name__ == "__main__":
    asyncio.run(test_network_resilience())
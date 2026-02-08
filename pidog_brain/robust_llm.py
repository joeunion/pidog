"""Robust LLM wrapper with timeout, retry, and caching

Wraps the Anthropic LLM client with:
- Request timeout (configurable, default 30s)
- Retry with exponential backoff (configurable, default 3 attempts)
- Optional response caching for repeated queries
- Error handling and logging
"""

import time
import hashlib
import json
from typing import Optional, Dict, Any, Callable
from functools import wraps


class RetryConfig:
    """Configuration for retry behavior"""

    def __init__(self,
                 max_retries: int = 3,
                 base_delay: float = 1.0,
                 max_delay: float = 30.0,
                 exponential_base: float = 2.0):
        """
        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Initial delay between retries in seconds
            max_delay: Maximum delay between retries
            exponential_base: Base for exponential backoff
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base

    def get_delay(self, attempt: int) -> float:
        """Get delay for a given attempt number"""
        delay = self.base_delay * (self.exponential_base ** attempt)
        return min(delay, self.max_delay)


class ResponseCache:
    """Simple LRU cache for responses"""

    def __init__(self, max_size: int = 100, ttl: float = 300.0):
        """
        Args:
            max_size: Maximum number of cached responses
            ttl: Time-to-live in seconds for cached entries
        """
        self.max_size = max_size
        self.ttl = ttl
        self._cache: Dict[str, tuple] = {}  # key -> (response, timestamp)

    def _make_key(self, prompt: str, **kwargs) -> str:
        """Create cache key from prompt and kwargs"""
        data = json.dumps({'prompt': prompt, **kwargs}, sort_keys=True)
        return hashlib.md5(data.encode()).hexdigest()

    def get(self, prompt: str, **kwargs) -> Optional[str]:
        """Get cached response if available and not expired"""
        key = self._make_key(prompt, **kwargs)

        if key not in self._cache:
            return None

        response, timestamp = self._cache[key]

        if time.time() - timestamp > self.ttl:
            del self._cache[key]
            return None

        return response

    def set(self, prompt: str, response: str, **kwargs):
        """Cache a response"""
        key = self._make_key(prompt, **kwargs)

        # Evict oldest if at capacity
        if len(self._cache) >= self.max_size:
            oldest_key = min(self._cache.keys(),
                           key=lambda k: self._cache[k][1])
            del self._cache[oldest_key]

        self._cache[key] = (response, time.time())

    def clear(self):
        """Clear the cache"""
        self._cache.clear()


class RobustLLM:
    """Wrapper that adds robustness to any LLM client

    Usage:
        from pidog_os.anthropic_llm import Anthropic

        base_llm = Anthropic(api_key=key)
        llm = RobustLLM(base_llm, timeout=30, max_retries=3)

        # Use like normal
        response = llm.prompt("Hello!")
    """

    def __init__(self,
                 base_llm,
                 timeout: float = 30.0,
                 retry_config: Optional[RetryConfig] = None,
                 enable_cache: bool = False,
                 cache_ttl: float = 300.0,
                 on_retry: Optional[Callable[[int, Exception], None]] = None,
                 on_error: Optional[Callable[[Exception], None]] = None,
                 output_format: Optional[Dict[str, Any]] = None):
        """
        Args:
            base_llm: The underlying LLM client
            timeout: Request timeout in seconds
            retry_config: Retry configuration (default: 3 retries with exponential backoff)
            enable_cache: Whether to cache responses
            cache_ttl: Cache entry time-to-live in seconds
            on_retry: Callback when retrying (attempt_num, exception)
            on_error: Callback when all retries exhausted
            output_format: Structured output format schema for guaranteed JSON responses
        """
        self.base_llm = base_llm
        self.timeout = timeout
        self.retry_config = retry_config or RetryConfig()
        self.cache = ResponseCache(ttl=cache_ttl) if enable_cache else None
        self.on_retry = on_retry
        self.on_error = on_error
        self.output_format = output_format

        # Statistics
        self.stats = {
            'calls': 0,
            'cache_hits': 0,
            'retries': 0,
            'errors': 0,
            'total_time': 0.0
        }

    def prompt(self, text: str, stream: bool = False, image_path: Optional[str] = None,
               use_cache: bool = True, **kwargs) -> str:
        """Send prompt with retry and timeout

        Args:
            text: Prompt text
            stream: Whether to stream response
            image_path: Optional image path
            use_cache: Whether to use cache for this request
            **kwargs: Additional arguments for LLM

        Returns:
            Response text

        Raises:
            Exception: If all retries exhausted
        """
        start_time = time.time()
        self.stats['calls'] += 1

        # Check cache
        if self.cache and use_cache and not stream and not image_path:
            cached = self.cache.get(text, **kwargs)
            if cached:
                self.stats['cache_hits'] += 1
                return cached

        # Try with retries
        last_exception = None

        for attempt in range(self.retry_config.max_retries + 1):
            try:
                response = self._make_request(text, stream, image_path, **kwargs)

                # Cache successful response
                if self.cache and use_cache and not stream and not image_path:
                    self.cache.set(text, response, **kwargs)

                self.stats['total_time'] += time.time() - start_time
                return response

            except Exception as e:
                last_exception = e

                if attempt < self.retry_config.max_retries:
                    self.stats['retries'] += 1

                    if self.on_retry:
                        self.on_retry(attempt + 1, e)
                    else:
                        print(f"LLM retry {attempt + 1}/{self.retry_config.max_retries}: {e}")

                    delay = self.retry_config.get_delay(attempt)
                    time.sleep(delay)

        # All retries exhausted
        self.stats['errors'] += 1
        self.stats['total_time'] += time.time() - start_time

        if self.on_error:
            self.on_error(last_exception)

        raise last_exception

    def _make_request(self, text: str, stream: bool, image_path: Optional[str],
                      **kwargs) -> str:
        """Make a single request with timeout"""
        import requests

        # Add message
        self.base_llm.add_message("user", text, image_path=image_path)

        # Make request with timeout
        # Note: We need to patch the base_llm's chat method to use timeout
        # For now, we'll use requests directly if possible

        try:
            # Try to use base_llm's prompt method with our timeout
            if hasattr(self.base_llm, 'chat'):
                # Get the chat method and patch timeout
                original_post = requests.post

                def timeout_post(*args, **kw):
                    kw['timeout'] = self.timeout
                    return original_post(*args, **kw)

                requests.post = timeout_post
                try:
                    response = self.base_llm.chat(
                        stream=stream,
                        output_format=self.output_format,
                        **kwargs
                    )
                finally:
                    requests.post = original_post

                if stream:
                    return self._handle_stream(response)
                else:
                    return self.base_llm._non_stream_response(response)
            else:
                # Fallback to direct prompt
                return self.base_llm.prompt(text, stream=stream, image_path=image_path)

        except requests.Timeout:
            raise TimeoutError(f"Request timed out after {self.timeout}s")

    def _handle_stream(self, response) -> str:
        """Handle streaming response"""
        full_response = []

        for line in response.iter_lines():
            if line:
                decoded = self.base_llm.decode_stream_response(line.decode('utf-8'))
                if decoded:
                    full_response.append(decoded)

        # Add assistant message to history
        text = ''.join(full_response)
        self.base_llm.add_message("assistant", text)

        return text

    def set_instructions(self, instructions: str):
        """Set system instructions"""
        self.base_llm.set_instructions(instructions)

    def clear_history(self):
        """Clear conversation history"""
        if hasattr(self.base_llm, 'messages'):
            self.base_llm.messages = []
        if self.cache:
            self.cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get usage statistics"""
        stats = self.stats.copy()
        if stats['calls'] > 0:
            stats['cache_hit_rate'] = stats['cache_hits'] / stats['calls']
            stats['retry_rate'] = stats['retries'] / stats['calls']
            stats['error_rate'] = stats['errors'] / stats['calls']
            stats['avg_time'] = stats['total_time'] / stats['calls']
        return stats


def with_retry(max_retries: int = 3, base_delay: float = 1.0):
    """Decorator to add retry logic to any function

    Usage:
        @with_retry(max_retries=3)
        def call_api():
            return api.request()
    """
    config = RetryConfig(max_retries=max_retries, base_delay=base_delay)

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(config.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < config.max_retries:
                        delay = config.get_delay(attempt)
                        time.sleep(delay)

            raise last_exception

        return wrapper
    return decorator

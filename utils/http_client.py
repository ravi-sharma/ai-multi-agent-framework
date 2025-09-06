"""HTTP client utilities with connection pooling and retry logic."""

import asyncio
import aiohttp
import time
from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass
from contextlib import asynccontextmanager

from .common_mixins import LoggerMixin


@dataclass
class HTTPConfig:
    """Configuration for HTTP client."""
    timeout: float = 30.0
    max_connections: int = 100
    max_connections_per_host: int = 30
    keepalive_timeout: int = 30
    enable_cleanup_closed: bool = True
    retry_attempts: int = 3
    retry_delay: float = 1.0
    retry_backoff: float = 2.0
    retry_on_status: List[int] = None
    
    def __post_init__(self):
        if self.retry_on_status is None:
            self.retry_on_status = [429, 500, 502, 503, 504]


@dataclass
class HTTPResponse:
    """HTTP response wrapper."""
    status: int
    headers: Dict[str, str]
    text: str
    json_data: Optional[Dict[str, Any]] = None
    request_time: float = 0.0
    attempt: int = 1


class HTTPClientManager(LoggerMixin):
    """Manages HTTP client sessions with connection pooling."""
    
    _instance = None
    _session = None
    _config = None
    
    def __new__(cls, config: Optional[HTTPConfig] = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config: Optional[HTTPConfig] = None):
        if not self._initialized:
            self._config = config or HTTPConfig()
            self._session = None
            self._session_lock = asyncio.Lock()
            self._initialized = True
    
    async def _create_session(self) -> aiohttp.ClientSession:
        """Create a new HTTP session with connection pooling."""
        connector = aiohttp.TCPConnector(
            limit=self._config.max_connections,
            limit_per_host=self._config.max_connections_per_host,
            keepalive_timeout=self._config.keepalive_timeout,
            enable_cleanup_closed=self._config.enable_cleanup_closed
        )
        
        timeout = aiohttp.ClientTimeout(total=self._config.timeout)
        
        session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                'User-Agent': 'AI-Agent-Framework/1.0'
            }
        )
        
        self.log_info("Created new HTTP session with connection pooling",
                     max_connections=self._config.max_connections,
                     timeout=self._config.timeout)
        
        return session
    
    async def get_session(self) -> aiohttp.ClientSession:
        """Get the shared HTTP session, creating it if necessary."""
        if self._session is None or self._session.closed:
            async with self._session_lock:
                if self._session is None or self._session.closed:
                    if self._session and not self._session.closed:
                        await self._session.close()
                    self._session = await self._create_session()
        
        return self._session
    
    async def close(self):
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self.log_info("Closed HTTP session")
    
    async def request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[Union[str, bytes]] = None,
        retry_config: Optional[HTTPConfig] = None
    ) -> HTTPResponse:
        """
        Make an HTTP request with retry logic.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            headers: Optional headers
            params: Optional query parameters
            json_data: Optional JSON data
            data: Optional raw data
            retry_config: Optional retry configuration override
            
        Returns:
            HTTPResponse object
            
        Raises:
            aiohttp.ClientError: If all retry attempts fail
        """
        config = retry_config or self._config
        session = await self.get_session()
        
        request_headers = headers or {}
        last_exception = None
        
        for attempt in range(1, config.retry_attempts + 1):
            start_time = time.time()
            
            try:
                self.log_debug(f"HTTP {method} request to {url}",
                              attempt=attempt,
                              max_attempts=config.retry_attempts)
                
                async with session.request(
                    method=method,
                    url=url,
                    headers=request_headers,
                    params=params,
                    json=json_data,
                    data=data
                ) as response:
                    
                    request_time = time.time() - start_time
                    response_text = await response.text()
                    
                    # Try to parse JSON if possible
                    json_response = None
                    if response.headers.get('content-type', '').startswith('application/json'):
                        try:
                            json_response = await response.json()
                        except Exception:
                            pass
                    
                    http_response = HTTPResponse(
                        status=response.status,
                        headers=dict(response.headers),
                        text=response_text,
                        json_data=json_response,
                        request_time=request_time,
                        attempt=attempt
                    )
                    
                    # Check if we should retry based on status code
                    if response.status in config.retry_on_status and attempt < config.retry_attempts:
                        self.log_warning(f"HTTP {response.status} received, retrying",
                                       url=url,
                                       attempt=attempt,
                                       status=response.status)
                        
                        # Wait before retry with exponential backoff
                        delay = config.retry_delay * (config.retry_backoff ** (attempt - 1))
                        await asyncio.sleep(delay)
                        continue
                    
                    # Log successful request
                    self.log_debug(f"HTTP request completed",
                                  url=url,
                                  status=response.status,
                                  time=request_time,
                                  attempt=attempt)
                    
                    return http_response
            
            except asyncio.TimeoutError as e:
                last_exception = e
                self.log_warning(f"HTTP request timeout",
                               url=url,
                               attempt=attempt,
                               timeout=config.timeout)
                
                if attempt < config.retry_attempts:
                    delay = config.retry_delay * (config.retry_backoff ** (attempt - 1))
                    await asyncio.sleep(delay)
                    continue
            
            except aiohttp.ClientError as e:
                last_exception = e
                self.log_warning(f"HTTP client error",
                               url=url,
                               attempt=attempt,
                               error=str(e))
                
                if attempt < config.retry_attempts:
                    delay = config.retry_delay * (config.retry_backoff ** (attempt - 1))
                    await asyncio.sleep(delay)
                    continue
            
            except Exception as e:
                last_exception = e
                self.log_error(f"Unexpected error in HTTP request",
                              url=url,
                              attempt=attempt,
                              error=e)
                
                if attempt < config.retry_attempts:
                    delay = config.retry_delay * (config.retry_backoff ** (attempt - 1))
                    await asyncio.sleep(delay)
                    continue
        
        # All attempts failed
        self.log_error(f"All HTTP retry attempts failed",
                      url=url,
                      attempts=config.retry_attempts)
        
        if last_exception:
            raise last_exception
        else:
            raise aiohttp.ClientError(f"HTTP request failed after {config.retry_attempts} attempts")
    
    async def get(self, url: str, **kwargs) -> HTTPResponse:
        """Make a GET request."""
        return await self.request('GET', url, **kwargs)
    
    async def post(self, url: str, **kwargs) -> HTTPResponse:
        """Make a POST request."""
        return await self.request('POST', url, **kwargs)
    
    async def put(self, url: str, **kwargs) -> HTTPResponse:
        """Make a PUT request."""
        return await self.request('PUT', url, **kwargs)
    
    async def delete(self, url: str, **kwargs) -> HTTPResponse:
        """Make a DELETE request."""
        return await self.request('DELETE', url, **kwargs)
    
    async def patch(self, url: str, **kwargs) -> HTTPResponse:
        """Make a PATCH request."""
        return await self.request('PATCH', url, **kwargs)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get HTTP client statistics."""
        if self._session and hasattr(self._session, '_connector'):
            connector = self._session._connector
            return {
                'session_closed': self._session.closed,
                'total_connections': len(connector._conns),
                'available_connections': sum(len(conns) for conns in connector._conns.values()),
                'config': {
                    'max_connections': self._config.max_connections,
                    'max_connections_per_host': self._config.max_connections_per_host,
                    'timeout': self._config.timeout,
                    'retry_attempts': self._config.retry_attempts
                }
            }
        
        return {
            'session_closed': True,
            'total_connections': 0,
            'available_connections': 0,
            'config': {
                'max_connections': self._config.max_connections,
                'max_connections_per_host': self._config.max_connections_per_host,
                'timeout': self._config.timeout,
                'retry_attempts': self._config.retry_attempts
            }
        }


# Global HTTP client manager
_http_client = None


def get_http_client(config: Optional[HTTPConfig] = None) -> HTTPClientManager:
    """Get the global HTTP client manager."""
    global _http_client
    if _http_client is None:
        _http_client = HTTPClientManager(config)
    return _http_client


@asynccontextmanager
async def http_session(config: Optional[HTTPConfig] = None):
    """Context manager for HTTP session."""
    client = get_http_client(config)
    try:
        yield client
    finally:
        # Don't close the session here as it's shared
        pass


# Convenience functions
async def http_get(url: str, **kwargs) -> HTTPResponse:
    """Make a GET request using the global client."""
    client = get_http_client()
    return await client.get(url, **kwargs)


async def http_post(url: str, **kwargs) -> HTTPResponse:
    """Make a POST request using the global client."""
    client = get_http_client()
    return await client.post(url, **kwargs)


async def http_put(url: str, **kwargs) -> HTTPResponse:
    """Make a PUT request using the global client."""
    client = get_http_client()
    return await client.put(url, **kwargs)


async def http_delete(url: str, **kwargs) -> HTTPResponse:
    """Make a DELETE request using the global client."""
    client = get_http_client()
    return await client.delete(url, **kwargs)


async def http_patch(url: str, **kwargs) -> HTTPResponse:
    """Make a PATCH request using the global client."""
    client = get_http_client()
    return await client.patch(url, **kwargs)


async def close_http_client():
    """Close the global HTTP client."""
    global _http_client
    if _http_client:
        await _http_client.close()
        _http_client = None


def get_http_stats() -> Dict[str, Any]:
    """Get HTTP client statistics."""
    client = get_http_client()
    return client.get_stats()


# Utility functions for common HTTP patterns
async def download_file(url: str, file_path: str, chunk_size: int = 8192) -> bool:
    """
    Download a file from URL.
    
    Args:
        url: URL to download from
        file_path: Local file path to save to
        chunk_size: Chunk size for streaming download
        
    Returns:
        True if successful, False otherwise
    """
    try:
        client = get_http_client()
        session = await client.get_session()
        
        async with session.get(url) as response:
            if response.status == 200:
                with open(file_path, 'wb') as f:
                    async for chunk in response.content.iter_chunked(chunk_size):
                        f.write(chunk)
                return True
            else:
                return False
    
    except Exception:
        return False


async def upload_file(url: str, file_path: str, field_name: str = 'file') -> HTTPResponse:
    """
    Upload a file to URL.
    
    Args:
        url: URL to upload to
        file_path: Local file path to upload
        field_name: Form field name for the file
        
    Returns:
        HTTPResponse object
    """
    client = get_http_client()
    
    with open(file_path, 'rb') as f:
        data = aiohttp.FormData()
        data.add_field(field_name, f, filename=file_path)
        
        return await client.post(url, data=data)

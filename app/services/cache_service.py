"""Cache service for storing CO2 forecast data using Python's built-in functionality."""

import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from threading import RLock

from app.config import settings
from app.utils.exceptions import CacheError

logger = logging.getLogger(__name__)


class SimpleCache:
    """A thread-safe in-memory cache with expiration."""
    
    def __init__(self):
        """Initialize the cache."""
        self._cache: Dict[str, Tuple[Any, Optional[float]]] = {}
        self._lock = RLock()  # Reentrant lock for thread safety
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.
        
        Args:
            key: The cache key
            
        Returns:
            The cached value, or None if not found or expired
        """
        with self._lock:
            if key not in self._cache:
                return None
            
            value, expiry = self._cache[key]
            
            # Check if expired
            if expiry is not None and expiry < time.time():
                del self._cache[key]
                return None
            
            logger.debug(f"Cache hit for {key}")
            return value
    
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        """
        Set a value in the cache.
        
        Args:
            key: The cache key
            value: The value to cache
            ttl_seconds: Time-to-live in seconds, or None for no expiry
            
        Returns:
            True if successful
        """
        with self._lock:
            expiry = None
            if ttl_seconds is not None:
                expiry = time.time() + ttl_seconds
            
            self._cache[key] = (value, expiry)
            return True
    
    def delete(self, key: str) -> bool:
        """
        Delete a value from the cache.
        
        Args:
            key: The cache key
            
        Returns:
            True if deleted, False if key not found
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    def clear_expired(self) -> int:
        """
        Clear all expired entries from the cache.
        
        Returns:
            Number of entries cleared
        """
        with self._lock:
            now = time.time()
            expired_keys = [
                key for key, (_, expiry) in self._cache.items()
                if expiry is not None and expiry < now
            ]
            
            for key in expired_keys:
                del self._cache[key]
            
            return len(expired_keys)
    
    def clear_all(self) -> int:
        """
        Clear all entries from the cache regardless of expiration.
        
        Returns:
            Number of entries cleared
        """
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return count



class CacheService:
    """Service for caching CO2 forecast data."""
    
    def __init__(self):
        """Initialize the cache service."""
        self._cache = SimpleCache()
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.
        
        Args:
            key: The cache key
            
        Returns:
            The cached value, or None if not found
        """
        try:
            return self._cache.get(key)
        except Exception as e:
            logger.error(f"Error getting value from cache: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        """
        Set a value in the cache.
        
        Args:
            key: The cache key
            value: The value to cache
            ttl_seconds: Time-to-live in seconds, or None for default TTL
            
        Returns:
            True if successful, False otherwise
        """
        if ttl_seconds is None:
            ttl_seconds = settings.CACHE_TTL
            
        try:
            return self._cache.set(key, value, ttl_seconds)
        except Exception as e:
            logger.error(f"Error setting value in cache: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Delete a value from the cache.
        
        Args:
            key: The cache key
            
        Returns:
            True if successful, False otherwise
        """
        try:
            return self._cache.delete(key)
        except Exception as e:
            logger.error(f"Error deleting value from cache: {e}")
            return False
    
    async def clear_all(self) -> bool:
        """
        Clear all values from the cache.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            cleared_count = self._cache.clear_all()
            logger.info(f"Cleared {cleared_count} entries from cache")
            return True
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return False
    
    @staticmethod
    def get_carbon_forecast_key(date: str, periods: Optional[List[int]] = None) -> str:
        """
        Generate a cache key for carbon forecast data.
        
        Args:
            date: Date in YYYY-MM-DD format
            periods: Optional list of specific periods to include in the key
            
        Returns:
            Cache key string
        """
        if periods:
            periods_str = "-".join(str(p) for p in sorted(periods))
            return f"carbon_forecast:{date}:{periods_str}"
        else:
            return f"carbon_forecast:{date}:all"


# Create a global instance of the cache service
cache_service = CacheService()
"""
Cache Manager Module

Implements memory-aware LRU caching and tiered caching strategy for handling
large microscopy datasets efficiently.

Based on System Architect's specifications for memory-aware caching with
psutil integration and LRU eviction policy.
"""

import os
import pickle
import hashlib
import threading
from pathlib import Path
from typing import Any, Optional, Dict, Tuple
from collections import OrderedDict
from datetime import datetime, timedelta

import psutil


class MemoryAwareLRUCache:
    """
    Memory-aware LRU (Least Recently Used) cache implementation.
    
    This cache monitors system memory usage using psutil and automatically
    evicts least recently used items when memory usage exceeds the threshold.
    
    Attributes:
        max_memory_threshold (float): Maximum memory usage percentage (default: 80%)
        cache (OrderedDict): Ordered dictionary maintaining LRU order
        lock (threading.Lock): Thread-safe access to cache
        _memory_check_interval (int): Number of operations between memory checks
        _operation_count (int): Counter for memory check optimization
    """
    
    def __init__(self, max_memory_threshold: float = 80.0):
        """
        Initialize the memory-aware LRU cache.
        
        Args:
            max_memory_threshold: Maximum memory usage percentage before eviction (0-100)
        """
        if not 0 < max_memory_threshold < 100:
            raise ValueError("max_memory_threshold must be between 0 and 100")
            
        self.max_memory_threshold = max_memory_threshold
        self.cache: OrderedDict = OrderedDict()
        self.lock = threading.RLock()
        self._memory_check_interval = 10  # Check memory every N operations
        self._operation_count = 0
        
        # Statistics
        self.hits = 0
        self.misses = 0
        self.evictions = 0
    
    def _check_memory_pressure(self) -> bool:
        """
        Check if system memory usage exceeds the threshold.
        
        Returns:
            bool: True if memory pressure is high, False otherwise
        """
        try:
            mem = psutil.virtual_memory()
            return mem.percent >= self.max_memory_threshold
        except Exception:
            # Fallback: assume no pressure if psutil fails
            return False
    
    def _estimate_size(self, value: Any) -> int:
        """
        Estimate memory size of a cached value.
        
        Args:
            value: The value to estimate size for
            
        Returns:
            int: Estimated size in bytes
        """
        try:
            return len(pickle.dumps(value))
        except Exception:
            # Fallback estimation
            return len(str(value).encode('utf-8'))
    
    def _evict_until_safe(self) -> None:
        """
        Evict LRU items until memory usage is below threshold.
        Implements the LRU eviction policy as specified by System Architect.
        """
        while self._check_memory_pressure() and self.cache:
            # Remove least recently used item (first in OrderedDict)
            key, value = self.cache.popitem(last=False)
            self.evictions += 1
    
    def get(self, key: Any) -> Optional[Any]:
        """
        Retrieve a value from the cache.
        
        Args:
            key: The cache key
            
        Returns:
            The cached value or None if not found
        """
        with self.lock:
            if key in self.cache:
                # Move to end (most recently used)
                value = self.cache.pop(key)
                self.cache[key] = value
                self.hits += 1
                return value
            else:
                self.misses += 1
                return None
    
    def put(self, key: Any, value: Any) -> None:
        """
        Store a value in the cache.
        
        Args:
            key: The cache key
            value: The value to cache
        """
        with self.lock:
            self._operation_count += 1
            
            # Check memory pressure periodically
            if self._operation_count % self._memory_check_interval == 0:
                self._evict_until_safe()
            
            # If key exists, update and move to end
            if key in self.cache:
                self.cache.pop(key)
            
            # Add new item (most recently used)
            self.cache[key] = value
            
            # Immediate memory check if we just added a large item
            if self._operation_count % self._memory_check_interval != 0:
                self._evict_until_safe()
    
    def remove(self, key: Any) -> bool:
        """
        Remove a value from the cache.
        
        Args:
            key: The cache key
            
        Returns:
            bool: True if key was removed, False if not found
        """
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False
    
    def clear(self) -> None:
        """Clear all items from the cache."""
        with self.lock:
            self.cache.clear()
            self.hits = 0
            self.misses = 0
            self.evictions = 0
    
    def size(self) -> int:
        """Return the number of items in the cache."""
        with self.lock:
            return len(self.cache)
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with hit, miss, eviction counts and size
        """
        with self.lock:
            return {
                'size': len(self.cache),
                'hits': self.hits,
                'misses': self.misses,
                'evictions': self.evictions,
                'hit_rate': self.hits / (self.hits + self.misses) if (self.hits + self.misses) > 0 else 0.0
            }


class ImageCacheManager:
    """
    Tiered caching manager for microscopy images.
    
    Implements a three-tier caching strategy:
    1. Memory cache (fastest, limited by system memory)
    2. Disk cache (persistent, limited by disk space)
    3. API fetch (slowest, unlimited but network-dependent)
    
    This manager handles serialization of image bytes to disk and retrieval
    back into memory, providing seamless access across all tiers.
    
    Attributes:
        memory_cache (MemoryAwareLRUCache): In-memory LRU cache
        disk_cache_dir (Path): Directory for disk cache
        max_disk_cache_size (int): Maximum disk cache size in bytes
        disk_cache_ttl (int): Time-to-live for disk cache entries in seconds
        lock (threading.Lock): Thread-safe operations
    """
    
    def __init__(
        self,
        disk_cache_dir: Optional[str] = None,
        max_disk_cache_size: int = 10 * 1024 * 1024 * 1024,  # 10 GB default
        disk_cache_ttl: int = 7 * 24 * 60 * 60,  # 7 days default
        memory_threshold: float = 80.0
    ):
        """
        Initialize the image cache manager.
        
        Args:
            disk_cache_dir: Directory for disk cache (default: ~/.idr_cache)
            max_disk_cache_size: Maximum disk cache size in bytes
            disk_cache_ttl: Time-to-live for disk cache entries in seconds
            memory_threshold: Memory threshold for memory cache
        """
        self.memory_cache = MemoryAwareLRUCache(max_memory_threshold=memory_threshold)
        self.disk_cache_dir = Path(disk_cache_dir or os.path.expanduser("~/.idr_cache"))
        self.max_disk_cache_size = max_disk_cache_size
        self.disk_cache_ttl = disk_cache_ttl
        self.lock = threading.RLock()
        
        # Create disk cache directory
        self.disk_cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Metadata file for tracking disk cache entries
        self.metadata_file = self.disk_cache_dir / "cache_metadata.pkl"
        self.metadata: Dict[str, Dict] = self._load_metadata()
    
    def _generate_cache_key(self, identifier: str) -> str:
        """
        Generate a unique cache key from an identifier.
        
        Args:
            identifier: Unique identifier (e.g., image ID, URL)
            
        Returns:
            str: Hash-based cache key
        """
        return hashlib.sha256(identifier.encode('utf-8')).hexdigest()
    
    def _get_disk_path(self, cache_key: str) -> Path:
        """
        Get the disk file path for a cache key.
        
        Args:
            cache_key: The cache key
            
        Returns:
            Path: File path for cached data
        """
        # Use first 2 characters of hash for subdirectory structure
        subdir = cache_key[:2]
        (self.disk_cache_dir / subdir).mkdir(exist_ok=True)
        return self.disk_cache_dir / subdir / f"{cache_key}.cache"
    
    def _load_metadata(self) -> Dict[str, Dict]:
        """Load cache metadata from disk."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'rb') as f:
                    return pickle.load(f)
            except Exception:
                return {}
        return {}
    
    def _save_metadata(self) -> None:
        """Save cache metadata to disk."""
        with self.lock:
            with open(self.metadata_file, 'wb') as f:
                pickle.dump(self.metadata, f)
    
    def _is_expired(self, entry_metadata: Dict) -> bool:
        """
        Check if a disk cache entry has expired.
        
        Args:
            entry_metadata: Metadata dictionary for the entry
            
        Returns:
            bool: True if expired, False otherwise
        """
        if 'timestamp' not in entry_metadata:
            return True
        
        age = datetime.now() - entry_metadata['timestamp']
        return age > timedelta(seconds=self.disk_cache_ttl)
    
    def _cleanup_disk_cache(self) -> None:
        """Clean up expired and oversized disk cache entries."""
        with self.lock:
            total_size = 0
            entries_to_remove = []
            
            # Check for expired entries
            for key, metadata in self.metadata.items():
                if self._is_expired(metadata):
                    entries_to_remove.append(key)
                else:
                    total_size += metadata.get('size', 0)
            
            # Remove oversized entries (LRU based on timestamp)
            if total_size > self.max_disk_cache_size:
                sorted_entries = sorted(
                    self.metadata.items(),
                    key=lambda x: x[1].get('timestamp', datetime.min)
                )
                
                for key, metadata in sorted_entries:
                    if total_size <= self.max_disk_cache_size:
                        break
                    if key not in entries_to_remove:
                        entries_to_remove.append(key)
                        total_size -= metadata.get('size', 0)
            
            # Remove entries
            for key in entries_to_remove:
                disk_path = self._get_disk_path(key)
                if disk_path.exists():
                    disk_path.unlink()
                del self.metadata[key]
            
            self._save_metadata()
    
    def get(self, identifier: str, fetch_func: Optional[callable] = None) -> Optional[bytes]:
        """
        Retrieve data from cache, falling back to disk and API as needed.
        
        Implements the tiered caching strategy: Memory -> Disk -> API
        
        Args:
            identifier: Unique identifier for the data
            fetch_func: Optional function to fetch data from API if not cached
            
        Returns:
            Cached data as bytes, or None if not found and no fetch_func provided
        """
        cache_key = self._generate_cache_key(identifier)
        
        # Tier 1: Check memory cache
        data = self.memory_cache.get(cache_key)
        if data is not None:
            return data
        
        # Tier 2: Check disk cache
        with self.lock:
            if cache_key in self.metadata and not self._is_expired(self.metadata[cache_key]):
                disk_path = self._get_disk_path(cache_key)
                if disk_path.exists():
                    try:
                        with open(disk_path, 'rb') as f:
                            data = f.read()
                        
                        # Promote to memory cache
                        self.memory_cache.put(cache_key, data)
                        
                        # Update access time
                        self.metadata[cache_key]['last_access'] = datetime.now()
                        self._save_metadata()
                        
                        return data
                    except Exception:
                        # Disk read failed, remove from metadata
                        if cache_key in self.metadata:
                            del self.metadata[cache_key]
                        self._save_metadata()
        
        # Tier 3: Fetch from API
        if fetch_func is not None:
            try:
                data = fetch_func()
                if data is not None:
                    self.put(identifier, data)
                    return data
            except Exception:
                pass
        
        return None
    
    def put(self, identifier: str, data: bytes) -> None:
        """
        Store data in both memory and disk cache.
        
        Args:
            identifier: Unique identifier for the data
            data: Data to cache (as bytes)
        """
        cache_key = self._generate_cache_key(identifier)
        
        # Store in memory cache
        self.memory_cache.put(cache_key, data)
        
        # Store in disk cache
        with self.lock:
            disk_path = self._get_disk_path(cache_key)
            
            try:
                with open(disk_path, 'wb') as f:
                    f.write(data)
                
                # Update metadata
                self.metadata[cache_key] = {
                    'timestamp': datetime.now(),
                    'last_access': datetime.now(),
                    'size': len(data),
                    'identifier': identifier
                }
                
                self._save_metadata()
                
                # Cleanup if needed
                self._cleanup_disk_cache()
                
            except Exception as e:
                # Disk write failed, but memory cache succeeded
                pass
    
    def invalidate(self, identifier: str) -> None:
        """
        Remove data from all cache tiers.
        
        Args:
            identifier: Unique identifier for the data
        """
        cache_key = self._generate_cache_key(identifier)
        
        # Remove from memory cache
        self.memory_cache.remove(cache_key)
        
        # Remove from disk cache
        with self.lock:
            disk_path = self._get_disk_path(cache_key)
            if disk_path.exists():
                disk_path.unlink()
            
            if cache_key in self.metadata:
                del self.metadata[cache_key]
                self._save_metadata()
    
    def clear_all(self) -> None:
        """Clear all cache tiers."""
        # Clear memory cache
        self.memory_cache.clear()
        
        # Clear disk cache
        with self.lock:
            for file_path in self.disk_cache_dir.rglob("*.cache"):
                try:
                    file_path.unlink()
                except Exception:
                    pass
            
            self.metadata.clear()
            self._save_metadata()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive cache statistics.
        
        Returns:
            Dictionary with statistics for all cache tiers
        """
        memory_stats = self.memory_cache.get_stats()
        
        with self.lock:
            disk_size = sum(m.get('size', 0) for m in self.metadata.values())
            disk_count = len(self.metadata)
            
            return {
                'memory': memory_stats,
                'disk': {
                    'count': disk_count,
                    'size_bytes': disk_size,
                    'size_mb': disk_size / (1024 * 1024),
                    'max_size_mb': self.max_disk_cache_size / (1024 * 1024),
                    'usage_percent': (disk_size / self.max_disk_cache_size * 100) if self.max_disk_cache_size > 0 else 0
                },
                'disk_cache_dir': str(self.disk_cache_dir)
            }

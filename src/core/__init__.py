"""
Core module containing fundamental components.

Includes cache management and IDR API integration.
"""

from .cache_manager import MemoryAwareLRUCache, ImageCacheManager
from .idr_adapter import IDRClientAdapter

__all__ = [
    'MemoryAwareLRUCache',
    'ImageCacheManager',
    'IDRClientAdapter'
]

"""
IDR Adapter Module

Provides integration between the IDR backend API and the application,
with automatic caching support for efficient data retrieval.

Wraps the Bioinformatician's IDRClient and integrates ImageCacheManager
for seamless data access across memory, disk, and API tiers.
"""

import logging
from typing import Optional, List, Dict, Any
from pathlib import Path

from .cache_manager import ImageCacheManager
from .idr_client import IDRClient


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IDRClientAdapter:
    """
    Adapter for IDR (Image Data Resource) client with integrated caching.
    
    This class wraps the IDRClient API and provides automatic caching for
    all image and metadata retrieval operations. It manages the session
    lifecycle and ensures proper cleanup aligned with GUI startup/shutdown.
    
    The adapter implements the tiered caching strategy:
    - Memory cache for frequently accessed data
    - Disk cache for persistent storage
    - API fallback for uncached data
    
    Attributes:
        base_url (str): Base URL for IDR API
        cache_manager (ImageCacheManager): Tiered cache manager
        _client: Internal IDR client instance
        _session_active (bool): Session state flag
    """
    
    def __init__(
        self,
        base_url: str = "https://idr.openmicroscopy.org",
        cache_dir: Optional[str] = None,
        max_disk_cache: int = 10 * 1024 * 1024 * 1024,  # 10 GB
        memory_threshold: float = 80.0
    ):
        """
        Initialize the IDR client adapter.
        
        Args:
            base_url: Base URL for IDR API
            cache_dir: Directory for disk cache
            max_disk_cache: Maximum disk cache size in bytes
            memory_threshold: Memory threshold for memory cache
        """
        self.base_url = base_url
        self.cache_manager = ImageCacheManager(
            disk_cache_dir=cache_dir,
            max_disk_cache_size=max_disk_cache,
            memory_threshold=memory_threshold
        )
        self._client = None
        self._session_active = False
        
        logger.info(f"IDRClientAdapter initialized with base_url: {base_url}")
    
    def connect(self) -> bool:
        """
        Establish connection to IDR API.
        
        Creates and initializes the IDR client session.
        Should be called during GUI startup.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self._client = IDRClient(self.base_url)
            
            self._session_active = True
            logger.info("Successfully connected to IDR API")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to IDR API: {e}")
            self._session_active = False
            return False
    
    def disconnect(self) -> None:
        """
        Close connection to IDR API and cleanup resources.
        
        Should be called during GUI shutdown to ensure proper cleanup.
        """
        if self._client is not None:
            # Close client session if applicable
            # self._client.close()
            self._client = None
        
        self._session_active = False
        logger.info("Disconnected from IDR API")
    
    def is_connected(self) -> bool:
        """
        Check if the adapter is connected to IDR API.
        
        Returns:
            bool: True if connected, False otherwise
        """
        return self._session_active and self._client is not None
    
    def get_screen(self, screen_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve screen metadata with caching.
        
        Args:
            screen_id: The screen identifier
            
        Returns:
            Screen metadata dictionary or None if not found
        """
        if not self.is_connected():
            logger.warning("Not connected to IDR API")
            return None
        
        identifier = f"screen_{screen_id}"
        
        def fetch_func():
            try:
                return self._client.get_screen(screen_id)
            except Exception as e:
                logger.error(f"Failed to fetch screen {screen_id}: {e}")
                return None
        
        return self.cache_manager.get(identifier, fetch_func)
    
    def get_plate(self, plate_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve plate metadata with caching.
        
        Args:
            plate_id: The plate identifier
            
        Returns:
            Plate metadata dictionary or None if not found
        """
        if not self.is_connected():
            logger.warning("Not connected to IDR API")
            return None
        
        identifier = f"plate_{plate_id}"
        
        def fetch_func():
            try:
                return self._client.get_plate(plate_id)
            except Exception as e:
                logger.error(f"Failed to fetch plate {plate_id}: {e}")
                return None
        
        return self.cache_manager.get(identifier, fetch_func)
        
    def get_image_metadata(self, image_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve image dimensional metadata from the API.
        
        Args:
            image_id: Image identifier
            
        Returns:
            Image metadata dictionary or None if not found.
        """
        if not self.is_connected():
            return None
            
        identifier = f"image_meta_{image_id}"
        
        def fetch_func():
            try:
                return self._client.get_image_metadata(image_id)
            except Exception as e:
                logger.error(f"Failed to fetch image meta {image_id}: {e}")
                return None
                
        return self.cache_manager.get(identifier, fetch_func)
    
    def get_image(self, image_id: int, z: int = 0, t: int = 0, high_res: bool = False) -> Optional[bytes]:
        """
        Retrieve image data with caching for specific Z and T indices.
        
        This method automatically utilizes the tiered caching strategy,
        checking memory cache first, then disk cache, and finally the API.
        
        Args:
            image_id: The image identifier
            z: Z-section index (default 0)
            t: Timepoint index (default 0)
            high_res: Whether to fetch at high resolution (default False)
            
        Returns:
            Image data as bytes or None if not found
        """
        if not self.is_connected():
            logger.warning("Not connected to IDR API")
            return None
        
        res_tag = "hires" if high_res else "thumb"
        identifier = f"image_{image_id}_z{z}_t{t}_{res_tag}"
        
        def fetch_func():
            try:
                return self._client.get_image_data(image_id, z, t, high_res=high_res)
            except Exception as e:
                logger.error(f"Failed to fetch image {image_id} (z={z}, t={t}): {e}")
                return None
        
        return self.cache_manager.get(identifier, fetch_func)
    
    def get_image_thumbnail(self, image_id: int, size: tuple = (128, 128)) -> Optional[bytes]:
        """
        Retrieve image thumbnail with caching.
        
        Args:
            image_id: The image identifier
            size: Thumbnail size as (width, height)
            
        Returns:
            Thumbnail image data as bytes or None if not found
        """
        if not self.is_connected():
            logger.warning("Not connected to IDR API")
            return None
        
        identifier = f"thumbnail_{image_id}_{size[0]}x{size[1]}"
        
        def fetch_func():
            try:
                return self._client.get_thumbnail(image_id, size)
            except Exception as e:
                logger.error(f"Failed to fetch thumbnail for image {image_id}: {e}")
                return None
        
        return self.cache_manager.get(identifier, fetch_func)
    
    def list_screens(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        List available screens with caching.
        
        Args:
            limit: Maximum number of screens to return
            
        Returns:
            List of screen metadata dictionaries
        """
        if not self.is_connected():
            logger.warning("Not connected to IDR API")
            return []
        
        identifier = f"screens_list_{limit}"
        
        def fetch_func():
            try:
                return self._client.list_screens(limit=limit)
            except Exception as e:
                logger.error(f"Failed to list screens: {e}")
                return []
        
        result = self.cache_manager.get(identifier, fetch_func)
        return result if result is not None else []
    
    def list_plates(self, screen_id: Optional[int] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        List available plates with caching.
        
        Args:
            screen_id: Optional screen ID to filter plates
            limit: Maximum number of plates to return
            
        Returns:
            List of plate metadata dictionaries
        """
        if not self.is_connected():
            logger.warning("Not connected to IDR API")
            return []
        
        identifier = f"plates_list_{screen_id}_{limit}" if screen_id else f"plates_list_{limit}"
        
        def fetch_func():
            try:
                return self._client.list_plates(screen_id=screen_id, limit=limit)
            except Exception as e:
                logger.error(f"Failed to list plates: {e}")
                return []
        
        result = self.cache_manager.get(identifier, fetch_func)
        return result if result is not None else []
    
    def search_images(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Search for images with caching.
        
        Args:
            query: Search query string
            limit: Maximum number of results to return
            
        Returns:
            List of image metadata dictionaries
        """
        if not self.is_connected():
            logger.warning("Not connected to IDR API")
            return []
        
        # Hash query to create valid cache key
        import hashlib
        query_hash = hashlib.md5(query.encode()).hexdigest()
        identifier = f"search_{query_hash}_{limit}"
        
        def fetch_func():
            try:
                return self._client.search_images(query=query, limit=limit)
            except Exception as e:
                logger.error(f"Failed to search images: {e}")
                return []
        
        result = self.cache_manager.get(identifier, fetch_func)
        return result if result is not None else []
    
    # ------------------------------------------------------------------
    # Study / hierarchy browsing
    # ------------------------------------------------------------------

    def get_study_type(self, study_id: int):
        """Detect whether a study_id is a Screen or Project. Returns (type, name, desc)."""
        if not self.is_connected():
            return None, None, None
        try:
            return self._client.get_study_type(study_id)
        except Exception as e:
            logger.error(f"get_study_type({study_id}): {e}")
            return None, None, None

    def get_screen_plates(self, screen_id: int):
        """Return list of plate dicts for a screen."""
        if not self.is_connected():
            return []
        return self._client.get_screen_plates(screen_id)

    def get_project_datasets(self, project_id: int):
        """Return list of dataset dicts for a project."""
        if not self.is_connected():
            return []
        return self._client.get_project_datasets(project_id)

    def get_dataset_images(self, dataset_id: int):
        """Return list of image dicts for a dataset."""
        if not self.is_connected():
            return []
        return self._client.get_dataset_images(dataset_id)

    def invalidate_cache(self, identifier: Optional[str] = None) -> None:
        """
        Invalidate cached data.
        
        Args:
            identifier: Optional specific identifier to invalidate.
                        If None, clears all cache.
        """
        if identifier:
            self.cache_manager.invalidate(identifier)
            logger.info(f"Invalidated cache for: {identifier}")
        else:
            self.cache_manager.clear_all()
            logger.info("Cleared all cache")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        return self.cache_manager.get_stats()
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()



